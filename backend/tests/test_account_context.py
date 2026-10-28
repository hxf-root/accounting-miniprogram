"""Account status and per-session logout with fictional identities."""
import base64

from identity.bindings import VerifiedIdentity, bind
from identity.sessions import issue
from models import User


def test_capability_reports_configuration_without_exposing_secrets(client, monkeypatch):
    monkeypatch.delenv('BAOBU_WECHAT_EXPERIMENTAL', raising=False)
    disabled = client.get('/api/capabilities')
    assert disabled.status_code == 200
    assert disabled.json()['wechat_identity_configured'] is False
    assert disabled.headers['cache-control'] == 'no-store'
    monkeypatch.setenv('BAOBU_WECHAT_EXPERIMENTAL', '1')
    monkeypatch.setenv('BAOBU_IDENTITY_HMAC_KEY', base64.b64encode(b'fictional-key-for-tests-only-12345').decode())
    monkeypatch.setenv('BAOBU_WECHAT_APP_ID', 'fictional-app-id')
    monkeypatch.setenv('BAOBU_WECHAT_APP_SECRET', 'fictional-app-secret')
    enabled = client.get('/api/capabilities')
    assert enabled.json()['wechat_identity_configured'] is True
    assert 'fictional' not in enabled.text


def test_me_reports_server_binding_and_account_isolation(client, auth_headers, db_session):
    first = client.get('/api/me', headers=auth_headers)
    assert first.status_code == 200
    assert first.headers['cache-control'] == 'no-store'
    assert first.json()['wechat_bound'] is False
    assert first.json()['session_type'] == 'legacy'
    user = db_session.query(User).filter_by(username='testuser').one()
    bind(db_session, user.id, VerifiedIdentity('wechat', 'fictional-subject'), b'fictional-key-for-testing-32bytes')
    assert client.get('/api/me', headers=auth_headers).json()['wechat_bound'] is True
    other = client.post('/api/auth/register', json={'username': 'other-user', 'password': 'pass1234'}).json()
    assert client.get('/api/me', headers={'Authorization': 'Bearer ' + other['token']}).json()['wechat_bound'] is False
    assert client.get('/api/me').status_code == 401


def test_logout_revokes_only_current_opaque_session(client, auth_headers, db_session):
    user = db_session.query(User).filter_by(username='testuser').one()
    first = issue(db_session, user.id)
    second = issue(db_session, user.id)
    h1, h2 = {'Authorization': 'Bearer ' + first}, {'Authorization': 'Bearer ' + second}
    assert client.get('/api/me', headers=h1).json()['session_type'] == 'short'
    response = client.post('/api/auth/logout', headers=h1)
    assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
    assert client.get('/api/me', headers=h1).status_code == 401
    assert client.get('/api/me', headers=h2).status_code == 200
    legacy = client.post('/api/auth/logout', headers=auth_headers)
    assert legacy.status_code == 409
    assert legacy.headers['cache-control'] == 'no-store'
    assert client.get('/api/me', headers=auth_headers).status_code == 200
