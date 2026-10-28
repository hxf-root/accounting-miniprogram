"""数据备份、恢复和清空测试"""


def _create_bill(client, auth_headers, category):
    response = client.post("/api/bills", headers=auth_headers, json={
        "type": category["type"],
        "amount": 28.5,
        "category_id": category["id"],
        "category_name": category["name"],
        "payment_method": "wechat",
        "remark": "备份测试",
        "date": "2026-07-20",
        "time": "12:00",
    })
    assert response.status_code == 200


def test_export_import_round_trip_includes_categories(client, auth_headers):
    categories = client.get("/api/categories?type=expense", headers=auth_headers).json()
    _create_bill(client, auth_headers, categories[0])

    exported = client.get("/api/data/export", headers=auth_headers).json()
    assert exported["version"] == 2
    assert exported["categories"]

    imported = client.post("/api/data/import", headers=auth_headers, json=exported)
    assert imported.status_code == 200

    restored_categories = client.get("/api/categories?type=expense", headers=auth_headers).json()
    restored_bills = client.get("/api/bills", headers=auth_headers).json()
    assert restored_categories
    assert len(restored_bills) == 1
    assert restored_bills[0]["category_id"] in {item["id"] for item in restored_categories}


def test_clear_data_is_unavailable_until_sync_can_be_paused_safely(client, auth_headers):
    categories = client.get("/api/categories?type=expense", headers=auth_headers).json()
    _create_bill(client, auth_headers, categories[0])
    client.put("/api/settings", headers=auth_headers, json={"monthly_budget": 3000})

    response = client.delete("/api/data", headers=auth_headers)
    assert response.status_code == 503

    exported = client.get("/api/data/export", headers=auth_headers).json()
    settings = client.get("/api/settings", headers=auth_headers).json()
    assert len(exported["bills"]) == 1
    assert exported["fitness"] == []
    assert exported["categories"]
    assert settings["monthly_budget"] == 3000


def test_legacy_import_without_categories_preserves_categories(client, auth_headers):
    before = client.get("/api/categories", headers=auth_headers).json()
    response = client.post("/api/data/import", headers=auth_headers, json={
        "bills": [],
        "fitness": [],
        "settings": {},
    })
    after = client.get("/api/categories", headers=auth_headers).json()

    assert response.status_code == 200
    assert after == before
