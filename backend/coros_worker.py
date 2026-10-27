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


def run_sync(db, user_id, helper: Path, state_dir: Path, *, days: int = 7, limit: int = 100, today=None):
    from integrations.coros_sync import import_sport_records
    from models import User, SyncState
    if not 1 <= days <= 30 or not 2 <= limit <= 100:
        raise ValueError('days must be 1–30 and limit 2–100')
    if not helper.is_absolute() or not helper.is_file():
        raise ValueError('an absolute path to the COROS helper is required')
    if not state_dir.is_absolute():
        raise ValueError('an absolute private credential directory is required')
    secure_path(state_dir, directory=True)
    secure_path(state_dir / 'token.json', directory=False)
    if not db.query(User.id).filter_by(id=user_id).first():
        raise ValueError('target user does not exist')
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
            original_token = token_path.read_bytes()
            today = today or datetime.now(ZoneInfo('Asia/Shanghai')).date()
            state = db.query(SyncState).filter_by(user_id=user_id, source='coros').first()
            start = today - timedelta(days=days - 1)
            if state:
                last_success = date.fromisoformat(state.last_success_date)
                if last_success > today:
                    raise RuntimeError('sync checkpoint is in the future')
                start = min(start, last_success)
            if (today - start).days >= 30:
                raise RuntimeError('sync gap exceeds 30 days; manual recovery is required')
            args = {'startDate': start.strftime('%Y%m%d'), 'endDate': today.strftime('%Y%m%d'), 'limit': limit}
            cmd = [sys.executable, str(helper), '--issuer', 'https://mcpcn.coros.com',
                   '--cache-path', str(state_dir / 'token.json'),
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
                # Do not log output, which may contain sensitive data or credentials.
                raise RuntimeError('COROS request failed; check authorization and connectivity')
            try:
                response = json.loads(result.stdout)
            except ValueError as exc:
                raise RuntimeError('COROS returned invalid JSON') from exc
            try:
                summary = import_sport_records(db, user_id, response, requested_limit=limit, commit=False,
                                               start_date=start, end_date=today)
                if state is None:
                    state = SyncState(user_id=user_id, source='coros', last_success_date=today.isoformat())
                    db.add(state)
                else:
                    state.last_success_date = today.isoformat()
                db.commit()
            except Exception:
                db.rollback()
                raise
            return summary
    except BlockingIOError as exc:
        raise RuntimeError('another sync is already running') from exc


def failure_code(exc):
    """Return a non-sensitive code suitable for scheduler logs."""
    from integrations.coros_records import CorosResponseError
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
        }.get(str(exc), 'internal_error')
    return 'internal_error'


def main():
    parser = argparse.ArgumentParser(description='Sync recent COROS activity to one local user')
    parser.add_argument('--user-id', type=int, required=True)
    parser.add_argument('--helper', type=Path, required=True)
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--days', type=int, default=7)
    parser.add_argument('--limit', type=int, default=100)
    args = parser.parse_args()
    if not os.environ.get('DATABASE_URL'):
        parser.error('DATABASE_URL must be explicitly set')
    from database import SessionLocal
    try:
        with SessionLocal() as db:
            result = run_sync(db, args.user_id, args.helper, args.state_dir, days=args.days, limit=args.limit)
        print(json.dumps(result))
        return 0
    except Exception as exc:
        # No provider output, token, raw records or traceback in scheduler logs.
        print(f'COROS sync failed: {failure_code(exc)}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
