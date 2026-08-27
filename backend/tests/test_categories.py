"""分类接口测试"""


def test_filter_categories_by_type(client, auth_headers):
    expense = client.get("/api/categories?type=expense", headers=auth_headers)
    income = client.get("/api/categories?type=income", headers=auth_headers)

    assert expense.status_code == 200
    assert income.status_code == 200
    assert expense.json()
    assert income.json()
    assert all(item["type"] == "expense" for item in expense.json())
    assert all(item["type"] == "income" for item in income.json())
