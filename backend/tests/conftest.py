"""测试 fixtures：临时文件数据库 + TestClient + 认证 Token"""

import os
import tempfile

pytest_plugins = []

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from main import app


@pytest.fixture
def db_session():
    """每次测试使用独立的临时文件 SQLite 数据库"""
    tmp = tempfile.mktemp(suffix=".db")
    db_url = f"sqlite:///{tmp}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSession()
    yield session
    session.close()
    engine.dispose()
    if os.path.exists(tmp):
        os.unlink(tmp)


@pytest.fixture
def client(db_session):
    """重写 get_db 依赖注入，使用测试数据库"""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    from database import get_db
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def user_token(client):
    """注册并登录一个测试用户，返回 token"""
    resp = client.post("/api/auth/register", json={
        "username": "testuser",
        "password": "test1234",
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


@pytest.fixture
def auth_headers(user_token):
    """认证请求头"""
    return {"Authorization": f"Bearer {user_token}"}
