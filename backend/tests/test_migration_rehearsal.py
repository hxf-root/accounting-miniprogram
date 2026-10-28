"""Offline migration rehearsal with fictional SQLite data only."""
import importlib.util
import json
import os
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('migration_rehearsal', ROOT / 'deploy/rehearse_migration.py')
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)
schema_spec = importlib.util.spec_from_file_location('schema_rehearsal', ROOT / 'deploy/check_schema.py')
schema_check = importlib.util.module_from_spec(schema_spec)
schema_spec.loader.exec_module(schema_check)


def legacy(path):
    manifest = json.loads(migration.MANIFEST.read_text())
    users = next(t for t in manifest['tables'] if t['table'] == 'users')
    db = sqlite3.connect(path)
    for sql in users['statements']:
        db.execute(sql)
    db.execute("INSERT INTO users (id, username, password_hash) VALUES (1, 'fictional', 'test-hash')")
    db.execute('CREATE TABLE unrelated (value TEXT)')
    db.execute("INSERT INTO unrelated VALUES ('preserved')")
    db.commit()
    return db


def objects(db):
    return db.execute("SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY name").fetchall()


def test_migration_uses_one_snapshot_preserves_data_and_repeats(tmp_path):
    source = tmp_path / 'source.db'
    with legacy(source) as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute("INSERT INTO users (id, username, password_hash) VALUES (2, 'wal-user', 'test')")
        db.commit()
        before = objects(db)
        stage = tmp_path / 'stage'
        migration.prepare(source, stage)
        assert objects(db) == before
        with sqlite3.connect(stage / 'original.db') as original, sqlite3.connect(stage / 'migrated.db') as upgraded:
            assert objects(original) == before
            assert original.execute('SELECT id, username FROM users ORDER BY id').fetchall() == [(1, 'fictional'), (2, 'wal-user')]
            assert upgraded.execute('SELECT id, username FROM users ORDER BY id').fetchall() == [(1, 'fictional'), (2, 'wal-user')]
            assert upgraded.execute('SELECT * FROM unrelated').fetchall() == [('preserved',)]
            assert upgraded.execute('SELECT version FROM baobu_schema_versions').fetchall() == [(1,)]
            assert upgraded.execute('SELECT COUNT(*) FROM source_controls').fetchone() == (0,)
            assert upgraded.execute('PRAGMA integrity_check').fetchone() == ('ok',)
        assert os.stat(stage).st_mode & 0o077 == 0
        assert os.stat(stage / 'original.db').st_mode & 0o077 == 0
        assert os.stat(stage / 'migrated.db').st_mode & 0o077 == 0
        assert schema_check.check(stage / 'migrated.db') == []
        migration.prepare(stage / 'migrated.db', tmp_path / 'repeat')
        with sqlite3.connect(tmp_path / 'repeat' / 'migrated.db') as repeated:
            assert repeated.execute('SELECT COUNT(*) FROM baobu_schema_versions').fetchone() == (1,)


def test_incompatible_schema_and_unknown_version_fail_closed(tmp_path):
    source = tmp_path / 'source.db'
    with legacy(source) as db:
        db.execute('CREATE INDEX unexpected_user_idx ON users(username)')
        db.commit()
    with pytest.raises(ValueError):
        migration.prepare(source, tmp_path / 'bad-schema')
    assert not (tmp_path / 'bad-schema').exists()
    with sqlite3.connect(source) as db:
        db.execute('DROP INDEX unexpected_user_idx')
        db.commit()
    migration.prepare(source, tmp_path / 'good')
    migrated = tmp_path / 'good' / 'migrated.db'
    with sqlite3.connect(migrated) as db:
        db.execute("UPDATE baobu_schema_versions SET checksum = 'unknown'")
        db.commit()
    with pytest.raises(ValueError):
        migration.prepare(migrated, tmp_path / 'bad-version')
    assert not (tmp_path / 'bad-version').exists()


def test_failure_rolls_back_and_does_not_remove_existing_folder(tmp_path, monkeypatch):
    source = tmp_path / 'source.db'
    with legacy(source) as db:
        before = objects(db)
    db = sqlite3.connect(source)
    execute = migration._execute
    calls = 0
    def fail(db, statement):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise sqlite3.OperationalError('simulated failure')
        execute(db, statement)
    monkeypatch.setattr(migration, '_execute', fail)
    with pytest.raises(sqlite3.OperationalError):
        migration._upgrade(db)
    assert objects(db) == before
    db.close()
    calls = 0
    with pytest.raises(sqlite3.OperationalError):
        migration.prepare(source, tmp_path / 'failed')
    assert not (tmp_path / 'failed').exists()
    existing = tmp_path / 'existing'
    existing.mkdir()
    marker = existing / 'keep'
    marker.write_text('keep')
    with pytest.raises(FileExistsError):
        migration.prepare(source, existing)
    assert marker.read_text() == 'keep'
