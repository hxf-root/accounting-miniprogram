"""统计接口测试"""


def test_monthly_stats(client, auth_headers):
    # 当月添加几条记录
    client.post("/api/bills", json={
        "type": "expense", "amount": 30, "category_id": 1,
        "category_name": "餐饮", "payment_method": "wechat",
        "remark": "午餐", "date": "2026-06-18", "time": "12:00",
    }, headers=auth_headers)
    client.post("/api/bills", json={
        "type": "expense", "amount": 15, "category_id": 1,
        "category_name": "餐饮", "payment_method": "wechat",
        "remark": "早餐", "date": "2026-06-17", "time": "08:00",
    }, headers=auth_headers)
    client.post("/api/bills", json={
        "type": "income", "amount": 5000, "category_id": 2,
        "category_name": "工资", "payment_method": "bankcard",
        "remark": "6月工资", "date": "2026-06-15", "time": "10:00",
    }, headers=auth_headers)

    resp = client.get("/api/stats/monthly?year=2026&month=6", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["expense"] == 45.0
    assert data["income"] == 5000.0
    assert data["balance"] == 4955.0
    assert data["bill_count"] == 2


def test_monthly_stats_other_month(client, auth_headers):
    """上个月的数据不影响本月统计"""
    client.post("/api/bills", json={
        "type": "expense", "amount": 100, "category_id": 1,
        "category_name": "餐饮", "payment_method": "wechat",
        "remark": "", "date": "2026-05-01", "time": "12:00",
    }, headers=auth_headers)

    resp = client.get("/api/stats/monthly?year=2026&month=6", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["expense"] == 0
    assert resp.json()["bill_count"] == 0


def test_today_stats(client, auth_headers):
    from datetime import date
    today = date.today().isoformat()

    client.post("/api/bills", json={
        "type": "expense", "amount": 25, "category_id": 1,
        "category_name": "餐饮", "payment_method": "wechat",
        "remark": "", "date": today, "time": "12:00",
    }, headers=auth_headers)
    client.post("/api/bills", json={
        "type": "income", "amount": 200, "category_id": 2,
        "category_name": "兼职", "payment_method": "cash",
        "remark": "", "date": today, "time": "14:00",
    }, headers=auth_headers)

    resp = client.get("/api/stats/today", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["expense"] == 25.0
    assert data["income"] == 200.0
