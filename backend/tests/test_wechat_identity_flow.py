"""HTTP flow uses only fake provider identities and isolated SQLite."""
from identity.bindings import VerifiedIdentity
from identity.wechat import WeChatExchangeError
from main import app
from routers.wechat_identity import config

KEY = b'example-key-for-tests-only-32-bytes-long'


class FakeProvider:
    def exchange(self, code):
        if code == 'bad':
            raise WeChatExchangeError('provider error')
        return VerifiedIdentity('wechat', 'fake-app\0' + code)


def enable_fake_provider():
    app.dependency_overrides[config] = lambda: (FakeProvider(), KEY)


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
    assert client.post('/api/auth/wechat/bind', json={'code': 'alice'}).status_code == 401
    assert client.post('/api/auth/wechat/login', json={'code': 'alice'}).status_code == 401
    assert client.post('/api/auth/wechat/bind', headers=alice, json={'code': 'alice'}).status_code == 200
    assert client.post('/api/auth/wechat/bind', headers=alice, json={'code': 'alice'}).status_code == 200
    assert client.post('/api/auth/wechat/bind', headers=bob, json={'code': 'alice'}).status_code == 409
    assert client.post('/api/auth/wechat/bind', headers=alice, json={'code': 'different'}).status_code == 409
    assert client.post('/api/auth/wechat/bind', headers=bob, json={'code': 'bob'}).status_code == 200
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
    response = client.post('/api/auth/wechat/bind', headers=headers, json={'code': 'bad'})
    assert response.status_code == 401 and 'provider error' not in response.text
    assert client.post('/api/auth/wechat/login', json={'code': ''}).status_code == 422
