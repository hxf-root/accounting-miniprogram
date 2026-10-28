import json
import pytest
from integrations.coros_records import CorosResponseError, parse_sport_records


def response(text):
    return {'content': [{'type': 'text', 'text': json.dumps(text)}], 'isError': False}


SAMPLE = '''Sport Records — 2026-10-20 to 2026-10-27 (1 records)
========================

1. Outdoor Run — 2026-10-26
   Time Window: startTimestamp=1793011716 | endTimestamp=1793015517
   LabelId: 123456789 | SportType: 100
'''


def test_convert_utc_and_stable_id():
    result = parse_sport_records(response(SAMPLE))
    assert result == [{'source': 'coros', 'source_id': '123456789',
                       'occurred_at': '2026-10-26T10:48:36.000000+00:00',
                       'text': 'Outdoor Run — 2026-10-26', 'sport_type': 100}]


def test_empty_result_and_fail_closed():
    assert parse_sport_records(response('Sport Records (0 records)\n')) == []
    for invalid in (SAMPLE.replace('LabelId:', 'Missing:'), SAMPLE.replace('(1 records)', '(2 records)')):
        with pytest.raises(CorosResponseError):
            parse_sport_records(response(invalid))
    with pytest.raises(CorosResponseError):
        parse_sport_records({'isError': True, 'content': []})


def test_idempotent_import_and_deleted_record_stays_deleted(client, auth_headers, db_session):
    from integrations.coros_sync import import_sport_records
    from models import User
    user_id = db_session.query(User).filter_by(username='testuser').one().id
    assert import_sport_records(db_session, user_id, response(SAMPLE), requested_limit=20)['inserted'] == 1
    assert import_sport_records(db_session, user_id, response(SAMPLE), requested_limit=20)['inserted'] == 0
    entry = client.get('/api/memories', headers=auth_headers).json()[0]
    assert client.delete(f"/api/memories/{entry['id']}", headers=auth_headers).status_code == 200
    assert import_sport_records(db_session, user_id, response(SAMPLE), requested_limit=20)['suppressed'] == 1
    assert client.get('/api/memories', headers=auth_headers).json() == []
    backup = client.get('/api/data/export', headers=auth_headers).json()
    assert len(backup['memory_suppressions']) == 1
    assert client.delete('/api/data', headers=auth_headers).status_code == 503
    assert client.post('/api/data/import', headers=auth_headers, json=backup).status_code == 200
    assert import_sport_records(db_session, user_id, response(SAMPLE), requested_limit=20)['suppressed'] == 1


def test_truncated_result_does_not_import(client, auth_headers, db_session):
    from integrations.coros_sync import import_sport_records
    from models import User
    user_id = db_session.query(User).filter_by(username='testuser').one().id
    with pytest.raises(CorosResponseError):
        import_sport_records(db_session, user_id, response(SAMPLE), requested_limit=1)
    assert client.get('/api/memories', headers=auth_headers).json() == []


def test_import_failure_leaves_existing_data_and_old_backup_preserves_suppression(client, auth_headers, db_session):
    from integrations.coros_sync import import_sport_records
    from models import User
    user_id = db_session.query(User).filter_by(username='testuser').one().id
    import_sport_records(db_session, user_id, response(SAMPLE), requested_limit=20)
    entry = client.get('/api/memories', headers=auth_headers).json()[0]
    client.delete(f"/api/memories/{entry['id']}", headers=auth_headers)
    # Pre-suppression backups must not resurrect a deleted record.
    legacy = {'bills': [], 'fitness': [], 'settings': {}, 'memories': [{
        'source': 'coros', 'source_id': '123456789',
        'occurred_at': '2026-10-26T10:48:36+00:00', 'text': 'old', 'hidden': False}]}
    assert client.post('/api/data/import', headers=auth_headers, json=legacy).status_code == 200
    assert client.get('/api/memories', headers=auth_headers).json() == []
    assert import_sport_records(db_session, user_id, response(SAMPLE), requested_limit=20)['suppressed'] == 1


def test_import_pre_deletion_v2_backup_preserves_newer_suppression(client, auth_headers, db_session):
    from integrations.coros_sync import import_sport_records
    from models import User
    user_id = db_session.query(User).filter_by(username='testuser').one().id
    import_sport_records(db_session, user_id, response(SAMPLE), requested_limit=20)
    backup = client.get('/api/data/export', headers=auth_headers).json()
    item = client.get('/api/memories', headers=auth_headers).json()[0]
    assert client.delete(f"/api/memories/{item['id']}", headers=auth_headers).status_code == 200
    assert client.post('/api/data/import', headers=auth_headers, json=backup).status_code == 200
    assert client.get('/api/memories', headers=auth_headers).json() == []
    assert import_sport_records(db_session, user_id, response(SAMPLE), requested_limit=20)['suppressed'] == 1
    assert client.post('/api/data/import', headers=auth_headers, json={**backup, 'version': 99}).status_code == 422
    # A corrupt partial backup is rejected before replacing any data.
    broken = {'bills': [], 'memory_suppressions': [{'source': 'coros', 'source_id': '123456789'}]}
    assert client.post('/api/data/import', headers=auth_headers, json=broken).status_code == 422
    assert import_sport_records(db_session, user_id, response(SAMPLE), requested_limit=20)['suppressed'] == 1
