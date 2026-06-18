"""认证接口测试"""


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
