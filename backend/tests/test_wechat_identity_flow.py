"""HTTP flow uses only fake provider identities and isolated SQLite."""
from identity.bindings import VerifiedIdentity
from identity.wechat import WeChatExchangeError
from main import app
from routers.wechat_identity import config, rate_ip, rate_account

KEY = b'example-key-for-tests-only-32-bytes-long'


class FakeProvider:
    def exchange(self, code):
        if code == 'bad':
            raise WeChatExchangeError('provider error')
        return VerifiedIdentity('wechat', 'fake-app\0' + code)


def enable_fake_provider():
    app.dependency_overrides[config] = lambda: (FakeProvider(), KEY)
    app.dependency_overrides[rate_ip] = lambda: None
    app.dependency_overrides[rate_account] = lambda: None


def register(client, name):
    response = client.post('/api/auth/register', json={'username': name, 'password': 'pass1234'})
    assert response.status_code == 200
    return {'Authorization': 'Bearer ' + response.json()['token']}


def test_disabled_without_configuration(client, monkeypatch):
    monkeypatch.delenv('BAOBU_WECHAT_EXPERIMENTAL', raising=False)
    assert client.post('/api/auth/wechat/login', json={'code': 'fake'}).status_code == 503


def test_binding_login_read_unbind_and_revoke(client):
    enable_fake_provider()
    alice, bob = register(client, 'flow-alice'), register(client, 'flow-bob')
    assert client.post('/api/auth/wechat/bind', json={'code': 'alice', 'password': 'pass1234'}).status_code == 401
    assert client.post('/api/auth/wechat/login', json={'code': 'alice'}).status_code == 401
    assert client.post('/api/auth/wechat/bind', headers=alice, json={'code': 'alice', 'password': 'pass1234'}).status_code == 200
    assert client.post('/api/auth/wechat/bind', headers=alice, json={'code': 'alice', 'password': 'pass1234'}).status_code == 200
    assert client.post('/api/auth/wechat/bind', headers=bob, json={'code': 'alice', 'password': 'pass1234'}).status_code == 409
    assert client.post('/api/auth/wechat/bind', headers=alice, json={'code': 'different', 'password': 'pass1234'}).status_code == 409
    assert client.post('/api/auth/wechat/bind', headers=bob, json={'code': 'bob', 'password': 'pass1234'}).status_code == 200
    payload = {'source': 'manual', 'occurred_at': '2026-10-28T10:00:00+08:00', 'text': 'fake record'}
    assert client.post('/api/memories', headers=alice, json=payload).status_code == 201
    response = client.post('/api/auth/wechat/login', json={'code': 'alice'})
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    short = {'Authorization': 'Bearer ' + response.json()['token']}
    assert len(client.get('/api/memories', headers=short).json()) == 1
    bob_short = {'Authorization': 'Bearer ' + client.post('/api/auth/wechat/login', json={'code': 'bob'}).json()['token']}
    assert client.get('/api/memories', headers=bob_short).json() == []
    assert client.delete('/api/auth/wechat/bind', headers=short).status_code == 200
    assert client.get('/api/memories', headers=short).status_code == 401
    assert client.post('/api/auth/wechat/login', json={'code': 'alice'}).status_code == 401
    assert client.get('/api/memories', headers=bob_short).status_code == 200
    assert client.get('/api/memories', headers=alice).status_code == 401
    login = client.post('/api/auth/login', json={'username': 'flow-alice', 'password': 'pass1234'})
    assert login.status_code == 200
    assert len(client.get('/api/memories', headers={'Authorization': 'Bearer ' + login.json()['token']}).json()) == 1
    assert client.get('/api/memories', headers=bob).status_code == 200


def test_provider_failure_and_input_validation(client):
    enable_fake_provider()
    headers = register(client, 'flow-error')
    response = client.post('/api/auth/wechat/bind', headers=headers, json={'code': 'bad', 'password': 'pass1234'})
    assert response.status_code == 401 and 'provider error' not in response.text
    assert client.post('/api/auth/wechat/login', json={'code': ''}).status_code == 422


def test_login_rate_limit_runs_before_provider(client, monkeypatch):
    from routers import wechat_identity
    calls = []
    class CountingProvider:
        def exchange(self, code):
            calls.append(code)
            return VerifiedIdentity('wechat', 'fake-app\0' + code)
    app.dependency_overrides[config] = lambda: (CountingProvider(), KEY)
    monkeypatch.setattr(wechat_identity, 'client_address', lambda peer, forwarded, trusted: '8.8.8.8')
    original_consume = wechat_identity.consume
    monkeypatch.setattr(wechat_identity, 'consume', lambda db, **kwargs: original_consume(db, now=120, **kwargs))
    for _ in range(20):
        assert client.post('/api/auth/wechat/login', json={'code': 'unbound'}).status_code == 401
    blocked = client.post('/api/auth/wechat/login', json={'code': 'unbound'})
    assert blocked.status_code == 429
    assert 1 <= int(blocked.headers['retry-after']) <= 60
    assert len(calls) == 20


def test_binding_rate_limit_and_untrusted_proxy_fail_closed(client, monkeypatch):
    from routers import wechat_identity
    calls = []
    class CountingProvider:
        def exchange(self, code):
            calls.append(code)
            return VerifiedIdentity('wechat', 'fake-app\0' + code)
    app.dependency_overrides[config] = lambda: (CountingProvider(), KEY)
    monkeypatch.setattr(wechat_identity, 'client_address', lambda peer, forwarded, trusted: '8.8.8.8')
    original_consume = wechat_identity.consume
    monkeypatch.setattr(wechat_identity, 'consume', lambda db, **kwargs: original_consume(db, now=120, **kwargs))
    headers = register(client, 'rate-user')
    for _ in range(10):
        assert client.post('/api/auth/wechat/bind', headers=headers, json={'code': 'same', 'password': 'pass1234'}).status_code == 200
    blocked = client.post('/api/auth/wechat/bind', headers=headers, json={'code': 'same', 'password': 'pass1234'})
    assert blocked.status_code == 429 and int(blocked.headers['retry-after']) == 60
    assert len(calls) == 10

    def invalid_proxy(peer, forwarded, trusted):
        from identity.rate_limit import UntrustedAddress
        raise UntrustedAddress('fake-private-ip')
    monkeypatch.setattr(wechat_identity, 'client_address', invalid_proxy)
    result = client.post('/api/auth/wechat/login', json={'code': 'private'})
    assert result.status_code == 503 and 'fake-private-ip' not in result.text
    assert len(calls) == 10


def test_binding_requires_password_before_provider_exchange(client):
    calls = []
    class CountingProvider:
        def exchange(self, code):
            calls.append(code)
            return VerifiedIdentity('wechat', 'fake-app\0' + code)
    app.dependency_overrides[config] = lambda: (CountingProvider(), KEY)
    app.dependency_overrides[rate_ip] = lambda: None
    app.dependency_overrides[rate_account] = lambda: None
    headers = register(client, 'bind-confirm')
    wrong = client.post('/api/auth/wechat/bind', headers=headers, json={'code': 'fake', 'password': 'wrong-password'})
    assert wrong.status_code == 401 and 'wrong-password' not in wrong.text
    assert calls == []
    assert client.post('/api/auth/wechat/bind', headers=headers, json={'code': 'fake'}).status_code == 422
    assert calls == []
    assert client.post('/api/auth/wechat/bind', headers=headers, json={'code': 'fake', 'password': 'pass1234'}).status_code == 200
    assert calls == ['fake']


def test_bind_cannot_reactivate_identity_after_concurrent_revocation(client, db_session):
    from sqlalchemy.orm import Session
    from identity.service import unbind_and_revoke_sessions
    from identity.bindings import resolve

    enable_fake_provider()
    headers = register(client, 'bind-race')
    original = client.post('/api/auth/wechat/bind', headers=headers, json={'code': 'first', 'password': 'pass1234'})
    assert original.status_code == 200
    user = client.post('/api/auth/login', json={'username': 'bind-race', 'password': 'pass1234'}).json()
    headers = {'Authorization': 'Bearer ' + user['token']}
    class ConcurrentRevokeProvider:
        def exchange(self, code):
            with Session(bind=db_session.get_bind()) as separate:
                assert unbind_and_revoke_sessions(separate, user['user_id'], 'wechat')
            return VerifiedIdentity('wechat', 'fake-app\0' + code)
    app.dependency_overrides[config] = lambda: (ConcurrentRevokeProvider(), KEY)
    result = client.post('/api/auth/wechat/bind', headers=headers, json={'code': 'second', 'password': 'pass1234'})
    assert result.status_code == 401
    db_session.expire_all()
    assert resolve(db_session, VerifiedIdentity('wechat', 'fake-app\0second'), KEY) is None


def test_bind_rejects_password_changed_during_provider_exchange(client, db_session):
    from sqlalchemy.orm import Session
    from auth import hash_password
    from models import User
    from identity.bindings import resolve

    enable_fake_provider()
    headers = register(client, 'bind-password-race')
    class ConcurrentPasswordChangeProvider:
        def exchange(self, code):
            with Session(bind=db_session.get_bind()) as separate:
                user = separate.query(User).filter_by(username='bind-password-race').one()
                user.password_hash = hash_password('newpass123')
                separate.commit()
            return VerifiedIdentity('wechat', 'fake-app\0' + code)
    app.dependency_overrides[config] = lambda: (ConcurrentPasswordChangeProvider(), KEY)
    result = client.post('/api/auth/wechat/bind', headers=headers, json={'code': 'late', 'password': 'pass1234'})
    assert result.status_code == 401
    db_session.expire_all()
    assert resolve(db_session, VerifiedIdentity('wechat', 'fake-app\0late'), KEY) is None
    assert client.post('/api/auth/login', json={'username': 'bind-password-race', 'password': 'newpass123'}).status_code == 200
