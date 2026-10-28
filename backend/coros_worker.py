"""Run a single COROS sync. Credentials belong outside the project tree.

Run with DATABASE_URL explicitly set and a separately installed COROS helper.
A scheduler may call this process; this script never starts a scheduler itself.
"""
import argparse
import fcntl
import json
import os
import stat
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


def secure_path(path: Path, *, directory: bool):
    if path.is_symlink():
        raise ValueError('credential paths must not be symbolic links')
    info = path.stat()
    if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise ValueError('credential directory and token must be private to the current user')
    if directory and not stat.S_ISDIR(info.st_mode):
        raise ValueError('credential directory is invalid')
    if not directory and not stat.S_ISREG(info.st_mode):
        raise ValueError('credential token is invalid')


def restore_missing_token(path: Path, original: bytes):
    """Restore the previous token only if a failed helper removed it.

    Never overwrite a refreshed token. A restored token may still be expired or
    revoked; it does not imply successful authorization.
    """
    fd, name = tempfile.mkstemp(prefix='.token-recovery-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(original)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(name, path, follow_symlinks=False)
        except FileExistsError:
            pass
    finally:
        os.unlink(name)


def query_coros(helper: Path, state_dir: Path, args: dict) -> dict:
    """Caller holds the credential-directory lock; never expose provider output in errors."""
    token_path = state_dir / 'token.json'
    secure_path(token_path, directory=False)
    if token_path.stat().st_size > 65536:
        raise ValueError('credential token is unexpectedly large')
    original_token = token_path.read_bytes()
    cmd = [sys.executable, str(helper), '--issuer', 'https://mcpcn.coros.com',
           '--cache-path', str(token_path),
           '--pending-login-path', str(state_dir / 'pending-login.json'),
           '--tool-catalog-path', str(state_dir / 'tool-catalog.json'),
           'call-tool', '--tool', 'querySportRecords', '--arguments-json', json.dumps(args)]
    token_removed = False
    try:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError('COROS request timed out') from exc
    finally:
        if not token_path.exists():
            token_removed = True
            restore_missing_token(token_path, original_token)
    if token_removed:
        raise RuntimeError('COROS credentials were removed; authorization must be checked')
    secure_path(token_path, directory=False)
    if result.returncode:
        raise RuntimeError('COROS request failed; check authorization and connectivity')
    try:
        return json.loads(result.stdout)
    except ValueError as exc:
        raise RuntimeError('COROS returned invalid JSON') from exc


def run_sync(db, user_id, helper: Path, state_dir: Path, *, days: int = 7, limit: int = 100, today=None,
             recover: bool = False, backfill_start: date | None = None, backfill_end: date | None = None):
    from integrations.source_control import acquire, release
    from models import User
    from sqlalchemy.orm import Session
    if not 1 <= days <= 30 or not 2 <= limit <= 100:
        raise ValueError('days must be 1–30 and limit 2–100')
    if (backfill_start is None) != (backfill_end is None):
        raise ValueError('backfill requires both start and end dates')
    if backfill_start is not None and (not isinstance(backfill_start, date) or isinstance(backfill_start, datetime)
            or not isinstance(backfill_end, date) or isinstance(backfill_end, datetime)
            or backfill_start > backfill_end or (backfill_end - backfill_start).days >= 366):
        raise ValueError('backfill interval must cover at most 366 days')
    if not helper.is_absolute() or not helper.is_file():
        raise ValueError('an absolute path to the COROS helper is required')
    if not state_dir.is_absolute():
        raise ValueError('an absolute private credential directory is required')
    secure_path(state_dir, directory=True)
    secure_path(state_dir / 'token.json', directory=False)
    with Session(bind=db.get_bind()) as reader:
        if not reader.query(User.id).filter_by(id=user_id).first():
            raise ValueError('target user does not exist')
    token, generation = acquire(db.get_bind(), user_id)
    try:
        return _run_sync(db, user_id, helper, state_dir, token, generation,
                         days=days, limit=limit, today=today, recover=recover,
                         backfill_start=backfill_start, backfill_end=backfill_end)
    finally:
        # A failed release leaves only an expiring lease; never release another
        # worker's newer lease. Preserve an in-flight error if cleanup also fails.
        original_failure = sys.exc_info()[0] is not None
        try:
            release(db.get_bind(), user_id, token)
        except Exception:
            if not original_failure:
                raise RuntimeError('source lease release failed') from None


def _run_sync(db, user_id, helper, state_dir, lease_token, generation, *, days, limit, today, recover,
              backfill_start, backfill_end):
    from integrations.coros_sync import import_sport_records
    from integrations.coros_records import CorosResponseError, parse_sport_records
    from integrations.source_control import assert_lease, renew
    from sqlalchemy import text
    from sqlalchemy.orm import Session
    from models import SyncState
    lock_path = state_dir / 'sync.lock'
    flags = os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(lock_path, flags, 0o600)
    try:
        with os.fdopen(fd, 'a+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            token_path = state_dir / 'token.json'
            secure_path(token_path, directory=False)
            if token_path.stat().st_size > 65536:
                raise ValueError('credential token is unexpectedly large')
            today = today or datetime.now(ZoneInfo('Asia/Shanghai')).date()
            with Session(bind=db.get_bind()) as reader:
                state = reader.query(SyncState).filter_by(user_id=user_id, source='coros').first()
                previous_success = state.last_success_date if state else None
            start = today - timedelta(days=days - 1)
            target_end = today
            if previous_success:
                last_success = date.fromisoformat(previous_success)
                if last_success > today:
                    raise RuntimeError('sync checkpoint is in the future')
                start = min(start, last_success)
            if backfill_start is not None:
                if not previous_success or backfill_end > last_success:
                    raise ValueError('backfill must end at or before an existing checkpoint')
                start, target_end = backfill_start, backfill_end
            if (target_end - start).days >= 30 and not recover:
                raise RuntimeError('sync gap exceeds 30 days; manual recovery is required')
            if (target_end - start).days >= 366:
                raise RuntimeError('sync gap exceeds 366 days; manual investigation is required')
            total = {'received': 0, 'inserted': 0, 'suppressed': 0, 'segments': 0}
            end = min(start + timedelta(days=29), target_end)
            while start <= target_end:
                # Network calls happen outside the DB write lock. Pausing may
                # race with a request, but prevents the subsequent commit.
                renew(db.get_bind(), user_id, lease_token, generation)
                args = {'startDate': start.strftime('%Y%m%d'), 'endDate': end.strftime('%Y%m%d'), 'limit': limit}
                response = query_coros(helper, state_dir, args)
                if len(parse_sport_records(response)) >= limit:
                    if end == start:
                        raise CorosResponseError('Single-day result may be truncated')
                    # Retry the first half; never commit a potentially incomplete range.
                    end = start + timedelta(days=(end - start).days // 2)
                    continue
                with Session(bind=db.get_bind()) as writer:
                    writer.execute(text('BEGIN IMMEDIATE'))
                    assert_lease(writer, user_id, lease_token, generation)
                    summary = import_sport_records(writer, user_id, response, requested_limit=limit, commit=False,
                                                   start_date=start, end_date=end)
                    checkpoint = writer.query(SyncState).filter_by(user_id=user_id, source='coros').first()
                    if backfill_start is None:
                        if checkpoint is None:
                            writer.add(SyncState(user_id=user_id, source='coros', last_success_date=end.isoformat()))
                        else:
                            checkpoint.last_success_date = end.isoformat()
                    writer.commit()
                for key in ("received", "inserted", "suppressed"):
                    total[key] += summary[key]
                total["segments"] += 1
                start = end + timedelta(days=1)
                end = min(start + timedelta(days=29), target_end)
            return total
    except BlockingIOError as exc:
        raise RuntimeError('another sync is already running') from exc


def failure_code(exc):
    """Return a non-sensitive code suitable for scheduler logs."""
    from integrations.coros_records import CorosResponseError
    from integrations.source_control import SourceBusy, SourceUnavailable
    if isinstance(exc, SourceBusy):
        return 'sync_already_running'
    if isinstance(exc, SourceUnavailable):
        return 'source_paused_or_changed'
    if isinstance(exc, CorosResponseError):
        return 'invalid_or_incomplete_response'
    if isinstance(exc, FileNotFoundError):
        return 'credential_or_helper_missing'
    if isinstance(exc, PermissionError):
        return 'credential_permission_denied'
    if isinstance(exc, ValueError):
        return 'invalid_configuration'
    if isinstance(exc, RuntimeError):
        return {
            'COROS request timed out': 'request_timeout',
            'COROS request failed; check authorization and connectivity': 'provider_or_authorization_error',
            'COROS credentials were removed; authorization must be checked': 'credentials_need_review',
            'COROS returned invalid JSON': 'invalid_or_incomplete_response',
            'another sync is already running': 'sync_already_running',
            'sync checkpoint is in the future': 'invalid_checkpoint',
            'sync gap exceeds 30 days; manual recovery is required': 'recovery_required',
            'sync gap exceeds 366 days; manual investigation is required': 'recovery_required',
        }.get(str(exc), 'internal_error')
    return 'internal_error'


def main():
    parser = argparse.ArgumentParser(description='Sync recent COROS activity to one local user')
    parser.add_argument('--user-id', type=int, required=True)
    parser.add_argument('--helper', type=Path, required=True)
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--days', type=int, default=7)
    parser.add_argument('--limit', type=int, default=100)
    parser.add_argument('--recover', action='store_true', help='recover a gap longer than 30 days in bounded segments')
    parser.add_argument('--backfill-start', type=date.fromisoformat, help='historical interval start (YYYY-MM-DD)')
    parser.add_argument('--backfill-end', type=date.fromisoformat, help='historical interval end (YYYY-MM-DD)')
    args = parser.parse_args()
    if not os.environ.get('DATABASE_URL'):
        parser.error('DATABASE_URL must be explicitly set')
    from database import SessionLocal
    try:
        with SessionLocal() as db:
            result = run_sync(db, args.user_id, args.helper, args.state_dir, days=args.days, limit=args.limit,
                              recover=args.recover, backfill_start=args.backfill_start, backfill_end=args.backfill_end)
        print(json.dumps(result))
        return 0
    except Exception as exc:
        # No provider output, token, raw records or traceback in scheduler logs.
        print(f'COROS sync failed: {failure_code(exc)}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
