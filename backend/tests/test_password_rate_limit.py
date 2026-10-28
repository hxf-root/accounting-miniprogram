"""Exercise opt-in legacy auth limits using isolated SQLite and fake clients."""
import base64

from sqlalchemy.exc import SQLAlchemyError
from identity import password_rate_limit as limiter
from identity.rate_limit import client_address


def configured(monkeypatch):
    monkeypatch.setenv('BAOBU_PASSWORD_RATE_LIMIT', '1')
    monkeypatch.setenv('BAOBU_IDENTITY_HMAC_KEY', base64.b64encode(b'test-key-only-' * 3).decode())
    monkeypatch.delenv('BAOBU_TRUSTED_PROXY_CIDRS', raising=False)
    monkeypatch.setattr(limiter, 'client_address', lambda peer, forwarded, trusted: client_address('8.8.8.8', forwarded, trusted))
    consume = limiter.consume
    monkeypatch.setattr(limiter, 'consume', lambda db, **kwargs: consume(db, now=120, **kwargs))


def test_disabled_preserves_existing_login_and_prevents_caching(client, monkeypatch):
    monkeypatch.delenv('BAOBU_PASSWORD_RATE_LIMIT', raising=False)
    created = client.post('/api/auth/register', json={'username': 'legacy-user', 'password': 'pass1234'})
    assert created.status_code == 200 and created.headers['cache-control'] == 'no-store'
    login = client.post('/api/auth/login', json={'username': 'legacy-user', 'password': 'pass1234'})
    assert login.status_code == 200 and login.headers['cache-control'] == 'no-store'


def test_login_limit_prevents_spoofed_header_bypass(client, monkeypatch):
    configured(monkeypatch)
    for i in range(20):
        response = client.post('/api/auth/login', headers={'X-Forwarded-For': f'1.1.1.{i + 1}'},
                               json={'username': 'missing', 'password': 'wrong'})
        assert response.status_code == 401
    blocked = client.post('/api/auth/login', json={'username': 'missing', 'password': 'wrong'})
    assert blocked.status_code == 429 and blocked.headers['retry-after'] == '60'
    # Separate endpoint has its own bucket.
    assert client.post('/api/auth/register', json={'username': 'another', 'password': 'pass1234'}).status_code == 200


def test_registration_limit_applies_before_account_creation(client, db_session, monkeypatch):
    configured(monkeypatch)
    for i in range(5):
        response = client.post('/api/auth/register', json={'username': 'same-user', 'password': 'pass1234'})
        assert response.status_code == (200 if i == 0 else 400)
    blocked = client.post('/api/auth/register', json={'username': 'blocked-user', 'password': 'pass1234'})
    assert blocked.status_code == 429
    from models import User
    assert db_session.query(User).filter_by(username='blocked-user').first() is None


def test_bad_configuration_and_storage_failure_fail_closed(client, monkeypatch):
    configured(monkeypatch)
    monkeypatch.setenv('BAOBU_IDENTITY_HMAC_KEY', 'invalid')
    assert client.post('/api/auth/login', json={'username': 'user', 'password': 'pass'}).status_code == 503
    monkeypatch.setenv('BAOBU_IDENTITY_HMAC_KEY', base64.b64encode(b'test-key-only-' * 3).decode())
    monkeypatch.setattr(limiter, 'consume', lambda *args, **kwargs: (_ for _ in ()).throw(SQLAlchemyError('secret detail')))
    response = client.post('/api/auth/login', json={'username': 'user', 'password': 'pass'})
    assert response.status_code == 503 and 'secret detail' not in response.text
    monkeypatch.setenv('BAOBU_PASSWORD_RATE_LIMIT', 'true')
    assert client.post('/api/auth/login', json={'username': 'user', 'password': 'pass'}).status_code == 503


def test_clients_are_separate_and_proxy_must_be_configured(client, db_session, monkeypatch):
    configured(monkeypatch)
    for _ in range(20):
        assert client.post('/api/auth/login', json={'username': 'missing', 'password': 'wrong'}).status_code == 401
    monkeypatch.setattr(limiter, 'client_address', lambda peer, forwarded, trusted: client_address('1.1.1.1', forwarded, trusted))
    assert client.post('/api/auth/login', json={'username': 'missing', 'password': 'wrong'}).status_code == 401
    from models import IdentityRateBucket
    for bucket in db_session.query(IdentityRateBucket).all():
        assert '8.8.8.8' not in bucket.key_digest and '1.1.1.1' not in bucket.key_digest
    monkeypatch.setattr(limiter, 'client_address', lambda peer, forwarded, trusted: client_address('127.0.0.1', forwarded, trusted))
    assert client.post('/api/auth/login', json={'username': 'missing', 'password': 'wrong'}).status_code == 503
