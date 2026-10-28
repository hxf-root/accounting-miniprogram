"""Check one local account and COROS authorization without importing records.

Use an independently reviewed, pinned official helper. This does not create a
connection, prove that the provider account belongs to the local account, or
activate synchronization. Provider calls may refresh local credentials.
"""
import argparse
import fcntl
import hashlib
import json
import os
import re
import sqlite3
import sys
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

from coros_worker import failure_code, query_coros, secure_path
from integrations.coros_records import CorosResponseError, parse_sport_records


def preflight(database: Path, user_id: int, helper: Path, state_dir: Path, helper_sha256: str,
              *, today: date | None = None, limit: int = 20) -> dict:
    if not all(p.is_absolute() for p in (database, helper, state_dir)) or user_id <= 0:
        raise ValueError('absolute paths and positive account id required')
    if not re.fullmatch(r'[0-9a-f]{64}', helper_sha256) or not 2 <= limit <= 100:
        raise ValueError('invalid helper digest or query limit')
    if helper.is_symlink() or not helper.is_file() or helper.stat().st_size > 2_000_000:
        raise ValueError('helper unavailable')
    if hashlib.sha256(helper.read_bytes()).hexdigest() != helper_sha256:
        raise ValueError('helper digest mismatch')
    secure_path(state_dir, directory=True)
    secure_path(state_dir / 'token.json', directory=False)
    if not database.is_file():
        raise ValueError('database unavailable')
    with closing(sqlite3.connect('file:' + quote(str(database.resolve()), safe='/') + '?mode=ro', uri=True)) as db:
        if not db.execute('SELECT 1 FROM users WHERE id = ?', (user_id,)).fetchone():
            raise ValueError('local account unavailable')
        schema = db.execute("SELECT type FROM sqlite_master WHERE name='source_controls'").fetchone()
        if schema is None:
            status = 'schema_missing'
        elif schema != ('table',):
            raise ValueError('invalid source control schema')
        else:
            rows = db.execute("SELECT status FROM source_controls WHERE user_id = ? AND source = 'coros'", (user_id,)).fetchall()
            if len(rows) > 1 or (rows and rows[0][0] not in ('active', 'paused')):
                raise ValueError('invalid source control')
            status = rows[0][0] if rows else 'unconfigured'
    today = today or datetime.now(ZoneInfo('Asia/Shanghai')).date()
    start = today - timedelta(days=6)
    args = {'startDate': start.strftime('%Y%m%d'), 'endDate': today.strftime('%Y%m%d'), 'limit': limit}
    flags = os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(state_dir / 'sync.lock', flags, 0o600)
    try:
        with os.fdopen(fd, 'a+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = query_coros(helper, state_dir, args)
            records = parse_sport_records(result)
    except BlockingIOError as exc:
        raise RuntimeError('another sync is already running') from exc
    for record in records:
        when = datetime.fromisoformat(record['occurred_at']).astimezone(ZoneInfo('Asia/Shanghai')).date()
        if not start <= when <= today:
            raise CorosResponseError('provider response outside requested range')
    return {'account_exists': True, 'source_status': status, 'provider_query': 'ok',
            'coverage': 'may_be_truncated' if len(records) >= limit else 'not_capped'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--user-id', type=int, required=True)
    parser.add_argument('--helper', type=Path, required=True)
    parser.add_argument('--helper-sha256', required=True)
    parser.add_argument('--state-dir', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = preflight(args.database, args.user_id, args.helper, args.state_dir, args.helper_sha256)
    except (OSError, sqlite3.Error, ValueError, RuntimeError) as exc:
        print('COROS preflight failed: ' + failure_code(exc), file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
