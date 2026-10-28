"""Local source control and fenced worker integration; all data is fictional."""
import json
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from coros_worker import run_sync, failure_code
from integrations.source_control import SourceBusy, SourceUnavailable, acquire, assert_lease, release, set_status
from models import Memory, SourceControl, SyncState, User


def fake_provider():
    record = ('Sport Records (1 records)\n1. Synthetic Run — 2026-10-26\n'
              '   Time Window: startTimestamp=1793011716 | endTimestamp=1793015517\n'
              '   LabelId: 123 | SportType: 100\n')
    return SimpleNamespace(returncode=0, stdout=json.dumps({'content': [{'type': 'text', 'text': json.dumps(record)}]}))


@pytest.fixture
def source_setup(client, auth_headers, db_session, tmp_path):
    uid = db_session.query(User).filter_by(username='testuser').one().id
    db_session.add(SourceControl(user_id=uid, source='coros', status='active', generation=0))
    db_session.commit()
    folder = tmp_path / 'private'
    folder.mkdir(mode=0o700)
    token = folder / 'token.json'
    token.write_text('{}')
    token.chmod(0o600)
    helper = tmp_path / 'helper.py'
    helper.write_text('# fictional helper')
    return uid, helper, folder


def change(engine, uid, status):
    with Session(bind=engine) as db:
        db.execute(text('BEGIN IMMEDIATE'))
        set_status(db, uid, status)
        db.commit()


def test_api_shows_only_owned_state_and_requires_existing_setup(client, auth_headers, db_session, source_setup):
    uid, _, _ = source_setup
    other = client.post('/api/auth/register', json={'username': 'other-source', 'password': 'test1234'}).json()
    other_headers = {'Authorization': 'Bearer ' + other['token']}
    assert client.get('/api/sources/coros', headers=other_headers).json() == {'status': 'unconfigured', 'last_success_date': None}
    assert client.post('/api/sources/coros/resume', headers=other_headers).status_code == 404
    assert client.get('/api/sources/coros').status_code == 401
    response = client.post('/api/sources/coros/pause', headers=auth_headers)
    assert response.status_code == 200 and response.json()['status'] == 'paused'
    assert response.headers['cache-control'] == 'no-store'
    assert client.post('/api/sources/coros/pause', headers=auth_headers).json()['status'] == 'paused'
    db_session.expire_all()
    assert db_session.query(SourceControl).filter_by(user_id=uid).one().generation == 1
    assert client.post('/api/sources/coros/resume', headers=auth_headers).json()['status'] == 'active'
    db_session.expire_all()
    assert db_session.query(SourceControl).filter_by(user_id=uid).one().generation == 2


@pytest.mark.parametrize('resume', [False, True])
def test_pause_during_provider_request_blocks_late_write(db_session, source_setup, resume):
    uid, helper, folder = source_setup
    def paused_during_network(*args, **kwargs):
        change(db_session.get_bind(), uid, 'paused')
        if resume:
            change(db_session.get_bind(), uid, 'active')
        return fake_provider()
    with patch('coros_worker.subprocess.run', side_effect=paused_during_network):
        with pytest.raises(SourceUnavailable):
            run_sync(db_session, uid, helper, folder, today=date(2026, 10, 27))
    db_session.expire_all()
    assert db_session.query(Memory).filter_by(user_id=uid).count() == 0
    assert db_session.query(SyncState).filter_by(user_id=uid).count() == 0
    assert failure_code(SourceUnavailable('fictional-private-info')) == 'source_paused_or_changed'


def test_import_during_provider_request_invalidates_worker(client, auth_headers, db_session, source_setup):
    uid, helper, folder = source_setup
    def import_during_network(*args, **kwargs):
        payload = {'memories': []}
        preview = client.post('/api/data/import/preview', headers=auth_headers, json=payload)
        assert preview.status_code == 200
        committed = client.post('/api/data/import/commit', headers=auth_headers,
                                json={'data': payload, 'preview_token': preview.json()['preview_token']})
        assert committed.status_code == 200
        return fake_provider()
    with patch('coros_worker.subprocess.run', side_effect=import_during_network):
        with pytest.raises(SourceUnavailable):
            run_sync(db_session, uid, helper, folder, today=date(2026, 10, 27))
    db_session.expire_all()
    assert db_session.query(Memory).filter_by(user_id=uid).count() == 0
    assert db_session.query(SyncState).filter_by(user_id=uid).count() == 0


def test_removed_account_cannot_receive_late_worker_data(db_session, source_setup):
    uid, helper, folder = source_setup
    def remove_account(*args, **kwargs):
        with Session(bind=db_session.get_bind()) as db:
            db.query(User).filter_by(id=uid).delete()
            db.commit()
        return fake_provider()
    with patch('coros_worker.subprocess.run', side_effect=remove_account):
        with pytest.raises(SourceUnavailable):
            run_sync(db_session, uid, helper, folder, today=date(2026, 10, 27))
    db_session.expire_all()
    assert db_session.query(Memory).filter_by(user_id=uid).count() == 0
    assert db_session.query(SyncState).filter_by(user_id=uid).count() == 0


def test_lease_blocks_other_credential_directory_and_expired_lease_is_fenced(db_session, source_setup, tmp_path):
    uid, helper, folder = source_setup
    second = tmp_path / 'other-private'
    second.mkdir(mode=0o700)
    (second / 'token.json').write_text('{}')
    (second / 'token.json').chmod(0o600)
    def concurrent_network(*args, **kwargs):
        with pytest.raises(SourceBusy):
            run_sync(db_session, uid, helper, second, today=date(2026, 10, 27))
        return fake_provider()
    with patch('coros_worker.subprocess.run', side_effect=concurrent_network):
        assert run_sync(db_session, uid, helper, folder, today=date(2026, 10, 27))['inserted'] == 1
    first, generation = acquire(db_session.get_bind(), uid, now=100)
    second_token, _ = acquire(db_session.get_bind(), uid, now=220)
    with Session(bind=db_session.get_bind()) as db:
        db.execute(text('BEGIN IMMEDIATE'))
        with pytest.raises(SourceUnavailable):
            assert_lease(db, uid, first, generation, now=221)
    release(db_session.get_bind(), uid, first)
    db_session.expire_all()
    assert db_session.query(SourceControl).filter_by(user_id=uid).one().lease_token == second_token
    release(db_session.get_bind(), uid, second_token)


def test_worker_that_loses_lease_cannot_commit_or_release_replacement(db_session, source_setup):
    uid, helper, folder = source_setup
    replacement = []
    def take_over(*args, **kwargs):
        with Session(bind=db_session.get_bind()) as db:
            db.execute(text('BEGIN IMMEDIATE'))
            db.query(SourceControl).filter_by(user_id=uid).one().lease_expires_at = 1
            db.commit()
        token, _ = acquire(db_session.get_bind(), uid)
        replacement.append(token)
        return fake_provider()
    with patch('coros_worker.subprocess.run', side_effect=take_over):
        with pytest.raises(SourceUnavailable):
            run_sync(db_session, uid, helper, folder, today=date(2026, 10, 27))
    db_session.expire_all()
    assert db_session.query(Memory).filter_by(user_id=uid).count() == 0
    assert db_session.query(SourceControl).filter_by(user_id=uid).one().lease_token == replacement[0]
    release(db_session.get_bind(), uid, replacement[0])


def test_unconfigured_or_paused_worker_never_calls_provider(db_session, source_setup):
    uid, helper, folder = source_setup
    change(db_session.get_bind(), uid, 'paused')
    with patch('coros_worker.subprocess.run') as run:
        with pytest.raises(SourceUnavailable):
            run_sync(db_session, uid, helper, folder, today=date(2026, 10, 27))
        run.assert_not_called()
    with Session(bind=db_session.get_bind()) as db:
        db.query(SourceControl).filter_by(user_id=uid).delete()
        db.commit()
    with patch('coros_worker.subprocess.run') as run:
        with pytest.raises(SourceUnavailable):
            run_sync(db_session, uid, helper, folder, today=date(2026, 10, 27))
        run.assert_not_called()


def test_successful_sync_updates_visible_date(client, auth_headers, db_session, source_setup):
    uid, helper, folder = source_setup
    with patch('coros_worker.subprocess.run', return_value=fake_provider()):
        run_sync(db_session, uid, helper, folder, today=date(2026, 10, 27))
    db_session.expire_all()
    assert client.get('/api/sources/coros', headers=auth_headers).json() == {
        'status': 'active', 'last_success_date': '2026-10-27'}


def test_malformed_existing_lease_fails_closed(db_session, source_setup):
    uid, helper, folder = source_setup
    with Session(bind=db_session.get_bind()) as db:
        row = db.query(SourceControl).filter_by(user_id=uid).one()
        row.lease_token = 'invalid'
        row.lease_expires_at = 1
        db.commit()
    with patch('coros_worker.subprocess.run') as run:
        with pytest.raises(SourceUnavailable):
            run_sync(db_session, uid, helper, folder, today=date(2026, 10, 27))
        run.assert_not_called()
