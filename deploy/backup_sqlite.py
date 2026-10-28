#!/usr/bin/env python3
"""Consistent private SQLite snapshots, including databases running in WAL mode."""
import argparse
from contextlib import closing
import gzip
import os
import shutil
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote


def backup(database: Path, destination: Path, *, retention: int = 30) -> Path:
    database, destination = Path(database).resolve(), Path(destination).resolve()
    if not database.is_file():
        raise ValueError('database does not exist')
    if retention < 1:
        raise ValueError('retention must be positive')
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    snapshot_fd, snapshot_path = tempfile.mkstemp(prefix='.sqlite-snapshot-', dir=destination)
    os.close(snapshot_fd)
    archive_fd = None
    archive_temp = None
    try:
        # mode=ro prevents accidentally creating an empty source database.
        source_uri = 'file:' + quote(str(database), safe='/') + '?mode=ro'
        with closing(sqlite3.connect(source_uri, uri=True)) as source, closing(sqlite3.connect(snapshot_path)) as snapshot:
            source.backup(snapshot)
            check = snapshot.execute('PRAGMA quick_check').fetchall()
            if check != [('ok',)]:
                raise ValueError('snapshot integrity check failed')
        archive_fd, archive_temp = tempfile.mkstemp(prefix='.backup-', suffix='.tmp', dir=destination)
        with os.fdopen(archive_fd, 'wb') as raw:
            archive_fd = None
            with gzip.GzipFile(fileobj=raw, mode='wb') as compressed, open(snapshot_path, 'rb') as snapshot:
                shutil.copyfileobj(snapshot, compressed, length=1024 * 1024)
            raw.flush()
            os.fsync(raw.fileno())
        stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
        final = destination / f'baobaoji_{stamp}_{uuid.uuid4().hex}.db.gz'
        os.replace(archive_temp, final)
        archive_temp = None
        # Prune only files of this backup naming convention, retaining newest.
        backups = sorted((p for p in destination.glob('baobaoji_*.db.gz') if p.is_file()),
                         key=lambda p: (p.stat().st_mtime_ns, p.name), reverse=True)
        for old in backups[retention:]:
            old.unlink()
        return final
    finally:
        if archive_fd is not None:
            os.close(archive_fd)
        if archive_temp is not None:
            Path(archive_temp).unlink(missing_ok=True)
        Path(snapshot_path).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description='Create a consistent private SQLite backup')
    parser.add_argument('--database', required=True, type=Path)
    parser.add_argument('--backup-dir', required=True, type=Path)
    parser.add_argument('--retention', type=int, default=30)
    args = parser.parse_args()
    try:
        result = backup(args.database, args.backup_dir, retention=args.retention)
    except (OSError, sqlite3.Error, ValueError):
        print('Backup failed; check backup files before proceeding.', file=__import__('sys').stderr)
        return 1
    print(f'Backup created: {result.name}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
