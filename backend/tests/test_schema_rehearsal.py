"""Migration rehearsal uses synthetic SQLite files only."""
import hashlib
import importlib.util
import sqlite3
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine
from database import Base
import models  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('schema_check', ROOT / 'deploy/check_schema.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def digest(path):
    return hashlib.sha256(path.read_bytes()).digest()


def fresh_database(path):
    engine = create_engine(f'sqlite:///{path}')
    Base.metadata.create_all(engine)
    engine.dispose()


def test_complete_schema_passes_without_modifying_source(tmp_path):
    path = tmp_path / 'data.db'
    fresh_database(path)
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO users (id, username, password_hash) VALUES (1, 'fake', 'fake')")
    before = digest(path)
    assert module.check(path) == []
    assert digest(path) == before


def test_missing_columns_and_indexes_are_detected_without_source_changes(tmp_path):
    path = tmp_path / 'old.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL, password_hash TEXT NOT NULL)')
        db.execute("INSERT INTO users VALUES (1, 'fake', 'fake')")
    before = digest(path)
    issues = module.check(path)
    assert 'users: missing column created_at' in issues
    assert any(issue.startswith('users: missing index') for issue in issues)
    assert digest(path) == before
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM users').fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM sqlite_master WHERE name='memories'").fetchone()[0] == 0


def test_missing_unique_constraint_detected(tmp_path):
    path = tmp_path / 'data.db'
    fresh_database(path)
    with sqlite3.connect(path) as db:
        db.execute('DROP INDEX ix_users_username')
    assert 'users: missing index username' in module.check(path)


def test_partial_index_does_not_satisfy_full_uniqueness(tmp_path):
    path = tmp_path / 'data.db'
    fresh_database(path)
    with sqlite3.connect(path) as db:
        db.execute('DROP INDEX ix_users_username')
        db.execute('CREATE UNIQUE INDEX partial_users_username ON users(username) WHERE id > 10')
    assert 'users: missing index username' in module.check(path)


def test_invalid_and_missing_database_fail_without_creating_file(tmp_path):
    missing = tmp_path / 'missing.db'
    result = subprocess.run([sys.executable, str(ROOT / 'deploy/check_schema.py'), str(missing)], capture_output=True, text=True)
    assert result.returncode != 0 and not missing.exists()
    assert str(missing) not in result.stderr
    invalid = tmp_path / 'invalid.db'
    invalid.write_text('not sqlite')
    before = digest(invalid)
    result = subprocess.run([sys.executable, str(ROOT / 'deploy/check_schema.py'), str(invalid)], capture_output=True, text=True)
    assert result.returncode != 0 and digest(invalid) == before


def test_old_unsafe_deployment_script_stops_before_changes():
    result = subprocess.run(['bash', str(ROOT / 'deploy/deploy.sh')], capture_output=True, text=True)
    assert result.returncode != 0 and '已暂停' in result.stderr
