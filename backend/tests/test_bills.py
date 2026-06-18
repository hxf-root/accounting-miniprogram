"""账单接口测试"""


def test_list_bills_empty(client, auth_headers):
    resp = client.get("/api/bills", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_bill(client, auth_headers):
    resp = client.post("/api/bills", json={
        "type": "expense",
        "amount": 29.9,
        "category_id": 1,
        "category_name": "餐饮",
        "payment_method": "wechat",
        "remark": "午餐",
        "date": "2026-06-18",
        "time": "12:30",
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["amount"] == 29.9
    assert data["type"] == "expense"
    assert data["category_name"] == "餐饮"
    assert data["id"] > 0


def test_list_bills_pagination(client, auth_headers):
    # 创建 5 条账单
    for i in range(5):
        client.post("/api/bills", json={
            "type": "expense" if i % 2 == 0 else "income",
            "amount": 10.0 + i,
            "category_id": 1,
            "category_name": "餐饮",
            "payment_method": "wechat",
            "remark": f"test {i}",
            "date": "2026-06-18",
            "time": "12:00",
        }, headers=auth_headers)

    resp = client.get("/api/bills?page=1&page_size=3", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_filter_by_type(client, auth_headers):
    client.post("/api/bills", json={
        "type": "expense", "amount": 10, "category_id": 1,
        "category_name": "餐饮", "payment_method": "wechat",
        "remark": "", "date": "2026-06-18", "time": "12:00",
    }, headers=auth_headers)
    client.post("/api/bills", json={
        "type": "income", "amount": 100, "category_id": 2,
        "category_name": "工资", "payment_method": "bankcard",
        "remark": "", "date": "2026-06-18", "time": "12:00",
    }, headers=auth_headers)

    resp = client.get("/api/bills?type=expense", headers=auth_headers)
    assert resp.status_code == 200
    assert all(b["type"] == "expense" for b in resp.json())


def test_update_bill(client, auth_headers):
    # 先创建
    create = client.post("/api/bills", json={
        "type": "expense", "amount": 10, "category_id": 1,
        "category_name": "餐饮", "payment_method": "cash",
        "remark": "旧备注", "date": "2026-06-18", "time": "12:00",
    }, headers=auth_headers)
    bill_id = create.json()["id"]

    # 更新
    resp = client.put(f"/api/bills/{bill_id}", json={
        "amount": 20,
        "remark": "新备注",
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["amount"] == 20
    assert resp.json()["remark"] == "新备注"


def test_delete_bill(client, auth_headers):
    create = client.post("/api/bills", json={
        "type": "expense", "amount": 10, "category_id": 1,
        "category_name": "餐饮", "payment_method": "wechat",
        "remark": "", "date": "2026-06-18", "time": "12:00",
    }, headers=auth_headers)
    bill_id = create.json()["id"]

    resp = client.delete(f"/api/bills/{bill_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # 确认已删除
    resp = client.get("/api/bills", headers=auth_headers)
    assert len(resp.json()) == 0


def test_bills_isolation(client, auth_headers):
    """不同用户的账单互不干扰"""
    client.post("/api/bills", json={
        "type": "expense", "amount": 10, "category_id": 1,
        "category_name": "餐饮", "payment_method": "wechat",
        "remark": "", "date": "2026-06-18", "time": "12:00",
    }, headers=auth_headers)

    # 另一个用户
    client.post("/api/auth/register", json={
        "username": "user2", "password": "pass1234",
    })
    resp2 = client.post("/api/auth/login", json={
        "username": "user2", "password": "pass1234",
    })
    token2 = resp2.json()["token"]

    resp = client.get("/api/bills", headers={"Authorization": f"Bearer {token2}"})
    assert resp.json() == []
