"""Actual WAL-mode SQLite backup and restore verification in temporary paths."""
import gzip
import importlib.util
import sqlite3
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('baobu_backup', Path(__file__).resolve().parents[2] / 'deploy' / 'backup_sqlite.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_wal_backup_can_restore_latest_committed_data(tmp_path):
    database = tmp_path / 'source.db'
    with sqlite3.connect(database) as db:
        assert db.execute('PRAGMA journal_mode=WAL').fetchone()[0] == 'wal'
        db.execute('PRAGMA wal_autocheckpoint=0')
        db.execute('CREATE TABLE samples (value TEXT)')
        db.execute('INSERT INTO samples VALUES (?)', ('synthetic',))
        db.commit()
        wal_file = Path(str(database) + '-wal')
        assert wal_file.exists() and wal_file.stat().st_size > 0
        archive = module.backup(database, tmp_path / 'backups')
        assert archive.stat().st_mode & 0o777 == 0o600
        restored = tmp_path / 'restored.db'
        with gzip.open(archive, 'rb') as data:
            restored.write_bytes(data.read())
        with sqlite3.connect(restored) as recovered:
            assert recovered.execute('PRAGMA quick_check').fetchone() == ('ok',)
            assert recovered.execute('SELECT value FROM samples').fetchall() == [('synthetic',)]


def test_unique_backups_and_retention(tmp_path):
    database = tmp_path / 'source.db'
    with sqlite3.connect(database) as db:
        db.execute('CREATE TABLE samples (value INTEGER)')
    directory = tmp_path / 'backups'
    unrelated = directory / 'unrelated.txt'
    directory.mkdir()
    unrelated.write_text('keep')
    first = module.backup(database, directory, retention=2)
    second = module.backup(database, directory, retention=2)
    third = module.backup(database, directory, retention=2)
    assert len({first.name, second.name, third.name}) == 3
    assert len(list(directory.glob('baobaoji_*.db.gz'))) == 2
    assert unrelated.read_text() == 'keep'


def test_failure_preserves_existing_backup_and_cleans_temporary_files(tmp_path):
    directory = tmp_path / 'backups'
    directory.mkdir()
    existing = directory / 'baobaoji_previous.db.gz'
    existing.write_bytes(b'existing')
    with pytest.raises(ValueError):
        module.backup(tmp_path / 'missing.db', directory)
    broken = tmp_path / 'broken.db'
    broken.write_bytes(b'not a database')
    with pytest.raises(sqlite3.DatabaseError):
        module.backup(broken, directory)
    assert existing.read_bytes() == b'existing'
    assert not list(directory.glob('.sqlite-snapshot-*'))
    assert not list(directory.glob('.backup-*.tmp'))


def test_restore_requires_rotated_jwt_key_and_revoked_sessions(client, db_session, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import auth
    from database import get_db
    from identity.sessions import issue
    from main import app
    from models import AccountAuthEpoch

    user = client.post('/api/auth/register', json={'username': 'restore-test', 'password': 'pass1234'}).json()
    original_jwt = user['token']
    old_session = issue(db_session, user['user_id'])
    original_path = Path(db_session.get_bind().url.database)
    archive = module.backup(original_path, tmp_path / 'restore-test-backups')
    db_session.add(AccountAuthEpoch(user_id=user['user_id'], epoch=1))
    db_session.commit()
    assert client.get('/api/memories', headers={'Authorization': 'Bearer ' + original_jwt}).status_code == 401
    restored_path = tmp_path / 'restore-copy.db'
    with gzip.open(archive, 'rb') as data:
        restored_path.write_bytes(data.read())
    engine = create_engine(f'sqlite:///{restored_path}', connect_args={'check_same_thread': False})
    factory = sessionmaker(bind=engine)
    old_override = app.dependency_overrides[get_db]
    def restored_db():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = restored_db
    try:
        restored_client = TestClient(app)
        # Old backup plus old key would restore old credentials: document the hazard.
        assert restored_client.get('/api/memories', headers={'Authorization': 'Bearer ' + original_jwt}).status_code == 200
        assert restored_client.get('/api/memories', headers={'Authorization': 'Bearer ' + old_session}).status_code == 200
        # Rotation invalidates JWTs; database sessions require separate revocation.
        monkeypatch.setattr(auth, 'SECRET_KEY', 'test-only-rotated-secret-key')
        with engine.begin() as connection:
            from sqlalchemy import text
            connection.execute(text('UPDATE access_sessions SET revoked = 1'))
        assert restored_client.get('/api/memories', headers={'Authorization': 'Bearer ' + original_jwt}).status_code == 401
        assert restored_client.get('/api/memories', headers={'Authorization': 'Bearer ' + old_session}).status_code == 401
        login = restored_client.post('/api/auth/login', json={'username': 'restore-test', 'password': 'pass1234'})
        assert login.status_code == 200
        assert restored_client.get('/api/memories', headers={'Authorization': 'Bearer ' + login.json()['token']}).status_code == 200
    finally:
        app.dependency_overrides[get_db] = old_override
        engine.dispose()


def test_existing_database_migrates_new_identity_tables_without_losing_data(tmp_path):
    from sqlalchemy import create_engine, inspect, text
    from database import Base
    import models  # noqa: F401 - register models with Base metadata

    path = tmp_path / 'pre-identity.db'
    with sqlite3.connect(path) as db:
        db.executescript('''
            CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(50) NOT NULL,
                password_hash VARCHAR(128) NOT NULL, created_at DATETIME);
            CREATE TABLE memories (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL,
                source VARCHAR(32) NOT NULL, source_id VARCHAR(200), occurred_at VARCHAR(32) NOT NULL,
                text TEXT NOT NULL, hidden BOOLEAN NOT NULL);
            INSERT INTO users (id, username, password_hash) VALUES (7, 'synthetic-user', 'synthetic-hash');
            INSERT INTO memories (id, user_id, source, occurred_at, text, hidden)
                VALUES (9, 7, 'manual', '2026-10-28T00:00:00.000000+00:00', 'synthetic-memory', 0);
        ''')
        db.commit()
    engine = create_engine(f'sqlite:///{path}')
    try:
        Base.metadata.create_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        names = set(inspect(engine).get_table_names())
        assert {'account_auth_epochs', 'external_identities', 'access_sessions'} <= names
        with engine.connect() as conn:
            assert conn.execute(text('SELECT id, username FROM users')).all() == [(7, 'synthetic-user')]
            assert conn.execute(text('SELECT id, text FROM memories')).all() == [(9, 'synthetic-memory')]
            assert conn.execute(text('SELECT COUNT(*) FROM account_auth_epochs')).scalar_one() == 0
    finally:
        engine.dispose()
