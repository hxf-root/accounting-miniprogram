#!/usr/bin/env python3
"""Prepare a versioned SQLite upgrade and its unchanged rollback snapshot for review.

Offline rehearsal only. Never activate either database or modify the source.
"""
import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from urllib.parse import quote

MANIFEST = Path(__file__).resolve().parent / 'migrations' / '001_initial_schema.json'
VERSION_SQL = ('CREATE TABLE baobu_schema_versions '
               '(version INTEGER NOT NULL PRIMARY KEY, checksum TEXT NOT NULL)')


def _objects(db):
    return {row[1]: (row[0], row[2], ' '.join(row[3].split()) if row[3] else None)
            for row in db.execute("SELECT type, name, tbl_name, sql FROM sqlite_master "
                                  "WHERE name NOT LIKE 'sqlite_%'")}


def _manifest():
    raw = MANIFEST.read_bytes()
    data = json.loads(raw)
    if data['version'] != 1:
        raise ValueError('unsupported migration manifest')
    return data, hashlib.sha256(raw).hexdigest()


def _backup(source, destination):
    with closing(sqlite3.connect(destination)) as target:
        source.backup(target)
        if target.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise ValueError('database integrity check failed')


def _execute(db, statement):
    db.execute(statement)


def _upgrade(db):
    manifest, checksum = _manifest()
    with closing(sqlite3.connect(':memory:')) as expected:
        for table in manifest['tables']:
            for statement in table['statements']:
                expected.execute(statement)
        expected.execute(VERSION_SQL)
        baseline = _objects(expected)

    objects = _objects(db)
    names = {entry['table'] for entry in manifest['tables']}
    if objects.get('users', (None,))[0] != 'table':
        raise ValueError('missing users table')
    version_obj = objects.get('baobu_schema_versions')
    if version_obj is not None:
        if version_obj != baseline['baobu_schema_versions']:
            raise ValueError('invalid version table')
        if db.execute('SELECT version, checksum FROM baobu_schema_versions').fetchall() != [(1, checksum)]:
            raise ValueError('unknown version or migration checksum')
        already_versioned = True
    else:
        already_versioned = False

    # Refuse divergent existing definitions, unexpected indexes, and triggers on
    # application tables; do not guess whether a legacy schema is compatible.
    for name, obj in objects.items():
        kind, table, _ = obj
        if name in baseline:
            if obj != baseline[name]:
                raise ValueError('existing schema differs from migration baseline')
        elif table in names | {'baobu_schema_versions'} and kind in ('index', 'trigger'):
            raise ValueError('unexpected index or trigger on application table')
    for entry in manifest['tables']:
        name = entry['table']
        if name in objects:
            required = {key for key, obj in baseline.items() if obj[1] == name}
            if not required.issubset(objects):
                raise ValueError('existing application table lacks required indexes')
        elif already_versioned:
            raise ValueError('versioned database lacks application table')

    db.execute('BEGIN IMMEDIATE')
    try:
        for entry in manifest['tables']:
            if entry['table'] not in objects:
                for statement in entry['statements']:
                    _execute(db, statement)
        if not already_versioned:
            _execute(db, VERSION_SQL)
            db.execute('INSERT INTO baobu_schema_versions(version, checksum) VALUES (?, ?)', (1, checksum))
        if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise ValueError('upgraded database failed integrity check')
        db.commit()
    except Exception:
        db.rollback()
        raise


def prepare(source: Path, staging: Path) -> None:
    source, staging = Path(source), Path(staging)
    if not source.is_absolute() or not staging.is_absolute():
        raise ValueError('absolute paths required')
    source = source.resolve(strict=True)
    if not source.is_file():
        raise ValueError('source unavailable')
    # mkdir is exclusive and only this new directory is removed on failure.
    staging.mkdir(mode=0o700)
    try:
        original = staging / 'original.db'
        migrated = staging / 'migrated.db'
        for path in (original, migrated):
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        with closing(sqlite3.connect('file:' + quote(str(source), safe='/') + '?mode=ro', uri=True)) as reader:
            _backup(reader, original)
        with closing(sqlite3.connect('file:' + quote(str(original.resolve()), safe='/') + '?mode=ro', uri=True)) as reader:
            _backup(reader, migrated)
        with closing(sqlite3.connect(migrated)) as db:
            _upgrade(db)
    except Exception:
        shutil.rmtree(staging)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--staging', type=Path, required=True)
    args = parser.parse_args()
    try:
        prepare(args.source, args.staging)
    except (OSError, sqlite3.Error, ValueError, KeyError, json.JSONDecodeError):
        print('Migration rehearsal failed; source was not modified.', file=sys.stderr)
        return 1
    print('Prepared original.db and migrated.db for review; neither was activated.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
