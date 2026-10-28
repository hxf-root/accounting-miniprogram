"""认证接口测试"""


def test_protected_endpoint_requires_bearer_token(client):
    resp = client.get("/api/bills")
    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == "Bearer"


def test_register(client):
    resp = client.post("/api/auth/register", json={
        "username": "newuser",
        "password": "pass1234",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["username"] == "newuser"
    assert data["user_id"] > 0


def test_register_duplicate(client):
    # 注册两次
    client.post("/api/auth/register", json={
        "username": "dupuser",
        "password": "pass1234",
    })
    resp = client.post("/api/auth/register", json={
        "username": "dupuser",
        "password": "pass1234",
    })
    assert resp.status_code == 400
    assert "已存在" in resp.json()["detail"]


def test_login(client):
    client.post("/api/auth/register", json={
        "username": "loginuser",
        "password": "pass1234",
    })
    resp = client.post("/api/auth/login", json={
        "username": "loginuser",
        "password": "pass1234",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["username"] == "loginuser"


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={
        "username": "failuser",
        "password": "pass1234",
    })
    resp = client.post("/api/auth/login", json={
        "username": "failuser",
        "password": "wrongpass",
    })
    assert resp.status_code == 401


def test_login_nonexistent_user(client):
    resp = client.post("/api/auth/login", json={
        "username": "nobody",
        "password": "pass1234",
    })
    assert resp.status_code == 401


def test_revocable_session_access_and_user_isolation(client, db_session):
    from identity.sessions import issue, revoke
    first = client.post('/api/auth/register', json={'username': 'session-one', 'password': 'pass1234'}).json()
    second = client.post('/api/auth/register', json={'username': 'session-two', 'password': 'pass1234'}).json()
    original = {'Authorization': 'Bearer ' + first['token']}
    payload = {'source': 'manual', 'occurred_at': '2026-10-28T10:00:00+08:00', 'text': 'private'}
    assert client.post('/api/memories', headers=original, json=payload).status_code == 201
    token = issue(db_session, first['user_id'])
    headers = {'Authorization': 'Bearer ' + token}
    assert len(client.get('/api/memories', headers=headers).json()) == 1
    other_token = issue(db_session, second['user_id'])
    assert client.get('/api/memories', headers={'Authorization': 'Bearer ' + other_token}).json() == []
    assert revoke(db_session, first['user_id'], token)
    response = client.get('/api/memories', headers=headers)
    assert response.status_code == 401
    assert response.headers['www-authenticate'] == 'Bearer'
    assert len(client.get('/api/memories', headers=original).json()) == 1


def test_expired_short_session_denied(client, db_session):
    from datetime import datetime, timezone
    from identity.sessions import issue
    user = client.post('/api/auth/register', json={'username': 'expired-session', 'password': 'pass1234'}).json()
    token = issue(db_session, user['user_id'], now=datetime(2020, 1, 1, tzinfo=timezone.utc))
    assert client.get('/api/memories', headers={'Authorization': 'Bearer ' + token}).status_code == 401


def test_legacy_jwt_epoch_revocation_and_new_password_login(client, db_session):
    from datetime import datetime, timedelta, timezone
    from jose import jwt
    from auth import SECRET_KEY, ALGORITHM
    from models import AccountAuthEpoch
    user = client.post('/api/auth/register', json={'username': 'legacy-epoch', 'password': 'pass1234'}).json()
    legacy = jwt.encode({'user_id': user['user_id'], 'username': 'legacy-epoch',
                         'exp': datetime.now(timezone.utc) + timedelta(hours=1)}, SECRET_KEY, algorithm=ALGORITHM)
    headers = {'Authorization': 'Bearer ' + legacy}
    assert client.get('/api/memories', headers=headers).status_code == 200
    db_session.add(AccountAuthEpoch(user_id=user['user_id'], epoch=1))
    db_session.commit()
    assert client.get('/api/memories', headers=headers).status_code == 401
    fresh = client.post('/api/auth/login', json={'username': 'legacy-epoch', 'password': 'pass1234'}).json()['token']
    assert client.get('/api/memories', headers={'Authorization': 'Bearer ' + fresh}).status_code == 200
    missing_exp = jwt.encode({'user_id': user['user_id'], 'username': 'legacy-epoch', 'auth_epoch': 1}, SECRET_KEY, algorithm=ALGORITHM)
    assert client.get('/api/memories', headers={'Authorization': 'Bearer ' + missing_exp}).status_code == 401
