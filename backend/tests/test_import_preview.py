"""Import previews must not change data or permit stale/cross-account commits."""
import sqlite3
from datetime import datetime, timedelta, timezone

from jose import jwt
import pytest

from auth import SECRET_KEY
from services import import_preview


def preview(client, headers, data):
    return client.post('/api/data/import/preview', headers=headers, json=data)


def commit(client, headers, data, token):
    return client.post('/api/data/import/commit', headers=headers,
                       json={'data': data, 'preview_token': token})


def create_memory(client, headers, text='synthetic private text'):
    response = client.post('/api/memories', headers=headers, json={
        'occurred_at': '2026-10-28T00:00:00Z', 'text': text})
    assert response.status_code == 201
    return response.json()


def test_preview_is_read_only_and_legacy_direct_import_is_blocked(client, auth_headers):
    create_memory(client, auth_headers)
    before = client.get('/api/data/export', headers=auth_headers)
    assert before.headers['cache-control'] == 'no-store'
    data = {'version': 2, 'memories': []}
    response = preview(client, auth_headers, data)
    assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
    assert 'synthetic private text' not in response.text
    report = response.json()
    assert report['replacements']['memories'] == {'action': 'replace', 'current': 1, 'incoming': 0}
    assert report['replacements']['bills']['action'] == 'preserve'
    assert client.get('/api/data/export', headers=auth_headers).json() == before.json()
    assert client.post('/api/data/import', headers=auth_headers, json=data).status_code == 409
    assert commit(client, auth_headers, data, report['preview_token']).status_code == 200
    assert client.get('/api/memories', headers=auth_headers).json() == []


def test_stale_changed_payload_and_cross_account_previews_rejected(client, auth_headers):
    data = {'version': 2, 'memories': []}
    p = preview(client, auth_headers, data).json()['preview_token']
    other = client.post('/api/auth/register', json={'username': 'other-import', 'password': 'pass1234'}).json()
    other_headers = {'Authorization': 'Bearer ' + other['token']}
    assert commit(client, other_headers, data, p).status_code == 409
    assert commit(client, auth_headers, {'version': 2, 'memories': [], 'bills': []}, p).status_code == 409
    create_memory(client, auth_headers)
    assert commit(client, auth_headers, data, p).status_code == 409
    assert len(client.get('/api/memories', headers=auth_headers).json()) == 1


def test_expired_and_forged_previews_are_rejected(client, auth_headers):
    data = {'memories': []}
    p = preview(client, auth_headers, data).json()['preview_token']
    claims = jwt.decode(p, SECRET_KEY, algorithms=['HS256'])
    claims['exp'] = datetime.now(timezone.utc) - timedelta(seconds=1)
    expired = jwt.encode(claims, SECRET_KEY, algorithm='HS256')
    assert commit(client, auth_headers, data, expired).status_code == 409
    assert commit(client, auth_headers, data, p + 'x').status_code == 409


def test_suppressed_records_counted_and_not_restored(client, auth_headers, db_session):
    from integrations.coros_sync import import_sport_records
    from tests.test_coros_records import SAMPLE, response
    from models import User
    uid = db_session.query(User).filter_by(username='testuser').one().id
    import_sport_records(db_session, uid, response(SAMPLE), requested_limit=20)
    backup = client.get('/api/data/export', headers=auth_headers).json()
    item = client.get('/api/memories', headers=auth_headers).json()[0]
    client.delete(f"/api/memories/{item['id']}", headers=auth_headers)
    result = preview(client, auth_headers, backup).json()
    assert result['memories_skipped_by_suppression'] == 1
    assert commit(client, auth_headers, backup, result['preview_token']).status_code == 200
    assert client.get('/api/memories', headers=auth_headers).json() == []


def test_bad_shapes_or_category_replacement_without_bills_are_rejected(client, auth_headers):
    categories = client.get('/api/categories?type=expense', headers=auth_headers).json()
    category = categories[0]
    bill = {'type': 'expense', 'amount': 5.0, 'category_id': category['id'],
            'category_name': category['name'], 'date': '2026-10-28', 'time': '12:00'}
    assert client.post('/api/bills', headers=auth_headers, json=bill).status_code == 200
    assert preview(client, auth_headers, {'categories': categories}).status_code == 422
    assert preview(client, auth_headers, {'bills': [{'amount': 4}]}).status_code == 422
    assert preview(client, auth_headers, {'memories': ['wrong type']}).status_code == 422
    assert preview(client, auth_headers, {'memories': [], 'unsupported_media': []}).status_code == 422
    assert len(client.get('/api/bills', headers=auth_headers).json()) == 1


def test_commit_holds_sqlite_write_lock_across_validation_and_replacement(client, auth_headers, db_session, monkeypatch):
    data = {'memories': []}
    p = preview(client, auth_headers, data).json()['preview_token']
    original = import_preview.verify
    def verify_while_competing(db, user_id, candidate, token):
        original(db, user_id, candidate, token)
        with sqlite3.connect(db_session.get_bind().url.database, timeout=0.05) as other:
            with pytest.raises(sqlite3.OperationalError, match='locked'):
                other.execute('BEGIN IMMEDIATE')
    monkeypatch.setattr(import_preview, 'verify', verify_while_competing)
    assert commit(client, auth_headers, data, p).status_code == 200


def test_commit_failure_rolls_back_partial_writes(client, auth_headers, monkeypatch):
    from models import Memory
    from services import data as data_service
    create_memory(client, auth_headers)
    backup = client.get('/api/data/export', headers=auth_headers).json()
    p = preview(client, auth_headers, {'memories': []}).json()['preview_token']
    def fail_after_delete(db, user_id, data):
        db.query(Memory).filter_by(user_id=user_id).delete()
        db.flush()
        raise RuntimeError('synthetic failure')
    monkeypatch.setattr(data_service, 'import_data', fail_after_delete)
    with pytest.raises(RuntimeError, match='synthetic failure'):
        commit(client, auth_headers, {'memories': []}, p)
    assert client.get('/api/data/export', headers=auth_headers).json() == backup
