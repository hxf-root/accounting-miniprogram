"""Tests for safe startup, legacy operations and SQLite backups."""
import gzip
import os
from pathlib import Path
import sqlite3
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def test_import_app_does_not_create_or_change_database(tmp_path):
    db_path = tmp_path / 'existing.db'
    with sqlite3.connect(db_path) as db:
        db.execute('CREATE TABLE sentinel (value TEXT)')
        db.execute("INSERT INTO sentinel VALUES ('untouched')")
    before = db_path.read_bytes()
    env = dict(os.environ, DATABASE_URL=f'sqlite:///{db_path}', JWT_SECRET_KEY='test-only-secret')
    subprocess.run([sys.executable, '-c', 'import main'], cwd=ROOT / 'backend', env=env, check=True)
    assert db_path.read_bytes() == before


def test_initializer_only_creates_new_database(tmp_path):
    db_path = tmp_path / 'new.db'
    script = ROOT / 'backend' / 'init_empty_db.py'
    command = [sys.executable, str(script), '--database', str(db_path)]
    assert subprocess.run(command, capture_output=True).returncode == 0
    before = db_path.read_bytes()
    assert subprocess.run(command, capture_output=True).returncode != 0
    assert db_path.read_bytes() == before


def test_old_deployment_entry_points_fail_before_changes():
    for command in (['make', 'deploy'], ['bash', 'deploy/deploy.sh'], ['bash', 'deploy/install-service.sh']):
        assert subprocess.run(command, cwd=ROOT, capture_output=True).returncode != 0


def test_make_backup_includes_wal_transactions(tmp_path):
    db_path = tmp_path / 'source.db'
    with sqlite3.connect(db_path) as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA wal_autocheckpoint=0')
        db.execute('CREATE TABLE sentinel (value TEXT)')
        db.execute("INSERT INTO sentinel VALUES ('committed-in-wal')")
        db.commit()
        backups = tmp_path / 'archives'
        subprocess.run(['make', 'backup', f'DB_FILE={db_path}', f'BACKUP_DIR={backups}'],
                       cwd=ROOT, check=True, capture_output=True)
        archives = list(backups.glob('*.db.gz'))
        assert len(archives) == 1
        restored = tmp_path / 'restored.db'
        with gzip.open(archives[0], 'rb') as archive:
            restored.write_bytes(archive.read())
        with sqlite3.connect(restored) as result:
            assert result.execute('SELECT value FROM sentinel').fetchone() == ('committed-in-wal',)
