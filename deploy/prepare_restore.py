#!/usr/bin/env python3
"""Prepare an offline SQLite restore for review; never modify a live database.

The prepared database revokes stored short-lived sessions, pauses source controls and the accompanying
new JWT secret invalidates old JWTs only if every service uses the new secret.
This tool does not stop services, activate the result, or change identity HMAC keys.
"""
import argparse
import gzip
import os
import secrets
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

MAX_DATABASE_BYTES = 1024 * 1024 * 1024


def prepare(archive: Path, staging: Path, *, max_bytes: int = MAX_DATABASE_BYTES) -> None:
    archive, staging = Path(archive), Path(staging)
    if not archive.is_absolute() or not staging.is_absolute():
        raise ValueError('archive and staging paths must be absolute')
    if not archive.is_file() or not 1 <= max_bytes <= MAX_DATABASE_BYTES:
        raise ValueError('invalid archive or size limit')
    # Never replace an existing folder or file. Parent must already exist.
    staging.mkdir(mode=0o700)
    try:
        database = staging / 'restored.db'
        fd = os.open(database, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        total = 0
        with os.fdopen(fd, 'wb') as target, gzip.open(archive, 'rb') as source:
            while True:
                chunk = source.read(min(1024 * 1024, max_bytes + 1 - total))
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError('archive exceeds restore size limit')
                target.write(chunk)
            target.flush()
            os.fsync(target.fileno())
        with closing(sqlite3.connect(database)) as db:
            if db.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
                raise ValueError('restored database failed integrity check')
            objects = {name: kind for name, kind in db.execute("SELECT name, type FROM sqlite_master WHERE name IN ('users', 'access_sessions', 'source_controls')")}
            if objects.get('users') != 'table':
                raise ValueError('restored database is missing the user table')
            if 'access_sessions' in objects:
                if objects['access_sessions'] != 'table':
                    raise ValueError('session storage is not a table')
                # If the schema is incompatible, fail rather than retaining credentials.
                db.execute('UPDATE access_sessions SET revoked = 1')
                if db.execute('SELECT COUNT(*) FROM access_sessions WHERE revoked IS NULL OR revoked != 1').fetchone()[0]:
                    raise ValueError('unable to revoke restored sessions')
                db.commit()
            if 'source_controls' in objects:
                if objects['source_controls'] != 'table':
                    raise ValueError('source controls are not a table')
                db.execute("UPDATE source_controls SET status = 'paused', generation = generation + 1, "
                           "lease_token = NULL, lease_expires_at = NULL")
                if db.execute("SELECT COUNT(*) FROM source_controls WHERE status IS NULL OR status != 'paused' "
                              "OR generation IS NULL OR lease_token IS NOT NULL OR lease_expires_at IS NOT NULL").fetchone()[0]:
                    raise ValueError('unable to pause restored sources')
                db.commit()
            if db.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
                raise ValueError('prepared database failed integrity check')
        secret = secrets.token_urlsafe(48)
        key_fd = os.open(staging / 'jwt-secret', os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(key_fd, 'w') as key_file:
            key_file.write(secret + '\n')
            key_file.flush()
            os.fsync(key_file.fileno())
    except Exception:
        # staging was created by this invocation; no existing files are removed.
        shutil.rmtree(staging)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description='Prepare a non-live SQLite restore and new JWT secret')
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--staging', type=Path, required=True)
    args = parser.parse_args()
    try:
        prepare(args.archive, args.staging)
    except (OSError, sqlite3.Error, EOFError, ValueError):
        print('Restore preparation failed; live data has not been modified.', file=__import__('sys').stderr)
        return 1
    print('Restore prepared for review; not activated. Existing JWTs require the new secret to be invalidated.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
