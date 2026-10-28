import gzip
import importlib.util
import sqlite3
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('baobu_restore', Path(__file__).resolve().parents[2] / 'deploy' / 'prepare_restore.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def archive_database(tmp_path, *, sessions=True):
    path = tmp_path / 'source.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT)')
        db.execute("INSERT INTO users VALUES (1, 'synthetic')")
        if sessions:
            db.execute('CREATE TABLE access_sessions (id INTEGER PRIMARY KEY, revoked BOOLEAN NOT NULL)')
            db.execute('INSERT INTO access_sessions VALUES (1, 0)')
    archive = tmp_path / 'source.db.gz'
    with gzip.open(archive, 'wb') as f:
        f.write(path.read_bytes())
    return archive


def test_prepare_keeps_original_and_revokes_restored_sessions(tmp_path):
    archive = archive_database(tmp_path)
    before = archive.read_bytes()
    staging = tmp_path / 'staging'
    module.prepare(archive, staging)
    assert archive.read_bytes() == before
    with sqlite3.connect(staging / 'restored.db') as db:
        assert db.execute('SELECT username FROM users').fetchone() == ('synthetic',)
        assert db.execute('SELECT revoked FROM access_sessions').fetchone() == (1,)
        assert db.execute('PRAGMA quick_check').fetchone() == ('ok',)
    assert (staging.stat().st_mode & 0o777) == 0o700
    assert ((staging / 'restored.db').stat().st_mode & 0o777) == 0o600
    assert ((staging / 'jwt-secret').stat().st_mode & 0o777) == 0o600
    assert len((staging / 'jwt-secret').read_text().strip()) >= 32


def test_older_archive_and_existing_staging_are_safe(tmp_path):
    archive = archive_database(tmp_path, sessions=False)
    module.prepare(archive, tmp_path / 'old-stage')
    existing = tmp_path / 'existing'
    existing.mkdir()
    (existing / 'keep').write_text('keep')
    with pytest.raises(FileExistsError):
        module.prepare(archive, existing)
    assert (existing / 'keep').read_text() == 'keep'


def test_restore_pauses_and_fences_existing_source_controls(tmp_path):
    path = tmp_path / 'source.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE users (id INTEGER PRIMARY KEY)')
        db.execute('CREATE TABLE source_controls (status TEXT, generation INTEGER, lease_token TEXT, lease_expires_at INTEGER)')
        db.execute("INSERT INTO source_controls VALUES ('active', 4, 'synthetic-lease', 123456789)")
    archive = tmp_path / 'source.gz'
    with gzip.open(archive, 'wb') as out:
        out.write(path.read_bytes())
    module.prepare(archive, tmp_path / 'stage')
    with sqlite3.connect(tmp_path / 'stage' / 'restored.db') as db:
        assert db.execute('SELECT status, generation, lease_token, lease_expires_at FROM source_controls').fetchone() == ('paused', 5, None, None)


def test_restore_rejects_incompatible_source_control_schema(tmp_path):
    path = tmp_path / 'source.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE users (id INTEGER PRIMARY KEY)')
        db.execute('CREATE TABLE source_controls (status TEXT)')
    archive = tmp_path / 'invalid-source.gz'
    with gzip.open(archive, 'wb') as out:
        out.write(path.read_bytes())
    with pytest.raises(sqlite3.OperationalError):
        module.prepare(archive, tmp_path / 'stage')
    assert not (tmp_path / 'stage').exists()


def test_invalid_and_oversized_archives_are_cleaned_up(tmp_path):
    archive = tmp_path / 'invalid.gz'
    with gzip.open(archive, 'wb') as f:
        f.write(b'not sqlite')
    staging = tmp_path / 'bad-stage'
    with pytest.raises(sqlite3.DatabaseError):
        module.prepare(archive, staging)
    assert not staging.exists()
    archive = archive_database(tmp_path)
    with pytest.raises(ValueError, match='size limit'):
        module.prepare(archive, tmp_path / 'large-stage', max_bytes=10)
    assert not (tmp_path / 'large-stage').exists()


def test_prepared_restore_rejects_old_credentials_and_allows_new_login(client, db_session, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import auth
    from database import get_db
    from identity.sessions import issue
    from main import app

    user = client.post('/api/auth/register', json={'username': 'restore-prepared', 'password': 'pass1234'}).json()
    session = issue(db_session, user['user_id'])
    source_path = Path(db_session.get_bind().url.database)
    archive = tmp_path / 'realistic.db.gz'
    # Use SQLite backup to get a consistent synthetic test snapshot.
    snapshot = tmp_path / 'snapshot.db'
    with sqlite3.connect(source_path) as source, sqlite3.connect(snapshot) as target:
        source.backup(target)
    with gzip.open(archive, 'wb') as out:
        out.write(snapshot.read_bytes())
    stage = tmp_path / 'review'
    module.prepare(archive, stage)
    engine = create_engine(f'sqlite:///{stage / "restored.db"}', connect_args={'check_same_thread': False})
    factory = sessionmaker(bind=engine)
    previous = app.dependency_overrides[get_db]
    def staged_db():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = staged_db
    monkeypatch.setattr(auth, 'SECRET_KEY', (stage / 'jwt-secret').read_text().strip())
    try:
        staged = TestClient(app)
        assert staged.get('/api/memories', headers={'Authorization': 'Bearer ' + user['token']}).status_code == 401
        assert staged.get('/api/memories', headers={'Authorization': 'Bearer ' + session}).status_code == 401
        response = staged.post('/api/auth/login', json={'username': 'restore-prepared', 'password': 'pass1234'})
        assert response.status_code == 200
        assert staged.get('/api/memories', headers={'Authorization': 'Bearer ' + response.json()['token']}).status_code == 200
    finally:
        app.dependency_overrides[get_db] = previous
        engine.dispose()


def test_unexpected_session_view_is_rejected(tmp_path):
    database = tmp_path / 'odd.db'
    with sqlite3.connect(database) as db:
        db.executescript('CREATE TABLE users(id INTEGER); CREATE VIEW access_sessions AS SELECT 0 AS revoked;')
    archive = tmp_path / 'odd.db.gz'
    with gzip.open(archive, 'wb') as f:
        f.write(database.read_bytes())
    with pytest.raises(ValueError, match='not a table'):
        module.prepare(archive, tmp_path / 'odd-stage')
    assert not (tmp_path / 'odd-stage').exists()


def test_cli_prepares_review_copy_without_printing_secret(tmp_path):
    import subprocess
    import sys
    archive = archive_database(tmp_path)
    staging = tmp_path / 'cli-stage'
    script = Path(__file__).resolve().parents[2] / 'deploy' / 'prepare_restore.py'
    result = subprocess.run([sys.executable, str(script), '--archive', str(archive), '--staging', str(staging)],
                            text=True, capture_output=True, timeout=10)
    assert result.returncode == 0
    assert 'not activated' in result.stdout
    assert (staging / 'jwt-secret').read_text().strip() not in result.stdout + result.stderr
