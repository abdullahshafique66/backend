from app.deps import today

from .conftest import API, auth


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_requires_auth(client):
    assert client.get(f"{API}/expenses").status_code == 401
    assert client.get(f"{API}/expenses", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_demo_dashboard_numbers(client):
    h = auth(client)
    s = client.get(f"{API}/dashboard/stats", headers=h).json()
    assert s["today"] == 1250
    assert s["yesterday"] == 780
    assert s["week"] == 8450
    if today().day >= 28:  # whole seeded month falls inside the current month
        assert s["month"] == 32450 and s["total_entries"] == 48
    assert s["budget"]["amount"] == 50000


def test_signup_crud_and_auto_totals(client):
    r = client.post(f"{API}/auth/signup", json={"name": "Bilal Ahmed", "email": "bilal@example.pk", "password": "strongpass1"})
    assert r.status_code == 201, r.text
    h = {"Authorization": f"Bearer {r.json()['token']}"}
    assert client.post(f"{API}/auth/signup", json={"name": "X Y", "email": "bilal@example.pk", "password": "strongpass1"}).status_code == 409

    cats = {c["icon"]: c["id"] for c in client.get(f"{API}/categories", headers=h).json()}
    assert len(cats) == 10
    t = today().isoformat()
    items = [("Doodh", 180, "dairy"), ("Aloo", 120, "vegetables"), ("Tamatar", 150, "vegetables"), ("Chicken", 650, "meat")]
    ids = {}
    for name, amt, cat in items:
        r = client.post(f"{API}/expenses", headers=h, json={"item_name": name, "amount": amt, "category_id": cats[cat], "date": t, "quantity": None, "unit": None, "note": None})
        assert r.status_code == 201, r.text
        ids[name] = r.json()["id"]

    day = client.get(f"{API}/expenses", headers=h, params={"from": t, "to": t, "page_size": 100}).json()
    assert day["total"] == 4 and day["total_amount"] == 1100

    # Aloo 120 → 150 : total 1,100 → 1,130 everywhere
    assert client.patch(f"{API}/expenses/{ids['Aloo']}", headers=h, json={"amount": 150}).json()["amount"] == 150
    assert client.get(f"{API}/dashboard/stats", headers=h).json()["today"] == 1130
    a = client.get(f"{API}/analytics", headers=h, params={"from": t, "to": t}).json()
    assert a["total"] == 1130 and a["from"] == t
    veg = next(c for c in a["by_category"] if c["name"] == "Vegetables")
    assert veg["total"] == 300 and veg["count"] == 2
    rep = client.get(f"{API}/reports", headers=h, params={"from": t, "to": t}).json()
    assert rep["total_expense"] == 1130 and rep["total_items"] == 4

    # search / filter / sort / pagination
    s = client.get(f"{API}/expenses", headers=h, params={"search": "doo"}).json()
    assert [e["item_name"] for e in s["items"]] == ["Doodh"]
    s = client.get(f"{API}/expenses", headers=h, params={"search": "vegetables"}).json()
    assert s["total"] == 2
    s = client.get(f"{API}/expenses", headers=h, params={"sort": "amount_desc", "page_size": 2, "page": 1}).json()
    assert [e["item_name"] for e in s["items"]] == ["Chicken", "Doodh"] and s["total"] == 4
    s = client.get(f"{API}/expenses", headers=h, params={"min_amount": 160}).json()
    assert s["total_amount"] == 180 + 650

    # validation messages
    bad = client.post(f"{API}/expenses", headers=h, json={"item_name": "X", "amount": 0, "category_id": cats["other"], "date": t})
    assert bad.status_code == 422 and "amount" in bad.json()["detail"]

    # delete
    assert client.delete(f"{API}/expenses/{ids['Tamatar']}", headers=h).status_code == 204
    assert client.get(f"{API}/dashboard/stats", headers=h).json()["today"] == 980

    # other users can't touch this data
    demo = auth(client)
    assert client.patch(f"{API}/expenses/{ids['Doodh']}", headers=demo, json={"amount": 1}).status_code == 404
    assert client.post(f"{API}/expenses", headers=demo, json={"item_name": "X", "amount": 5, "category_id": cats["dairy"], "date": t}).status_code == 400


def test_categories_and_budget(client):
    h = auth(client, "bilal@example.pk", "strongpass1")
    c = client.post(f"{API}/categories", headers=h, json={"name": "School Fees", "icon": "education", "color": "#3F6E9E"})
    assert c.status_code == 201
    cid = c.json()["id"]
    assert client.post(f"{API}/categories", headers=h, json={"name": "school fees"}).status_code == 409
    e = client.post(f"{API}/expenses", headers=h, json={"item_name": "Fees", "amount": 4000, "category_id": cid, "date": today().isoformat()}).json()
    assert client.delete(f"{API}/categories/{cid}", headers=h).status_code == 204
    moved = client.get(f"{API}/expenses", headers=h, params={"search": "fees"}).json()["items"][0]
    other = next(x for x in client.get(f"{API}/categories", headers=h).json() if x["icon"] == "other")
    assert moved["id"] == e["id"] and moved["category_id"] == other["id"]

    t = today()
    assert client.get(f"{API}/budgets/current", headers=h).json() is None
    assert client.put(f"{API}/budgets/{t.year}/{t.month}", headers=h, json={"amount": 40000}).json()["amount"] == 40000
    assert client.put(f"{API}/budgets/{t.year}/{t.month}", headers=h, json={"amount": 45000}).json()["amount"] == 45000
    assert client.get(f"{API}/dashboard/stats", headers=h).json()["budget"]["amount"] == 45000


def test_exports_and_suggestions(client):
    h = auth(client)
    for fmt, sig in [("csv", b"\xef\xbb\xbfDate"), ("excel", b"PK"), ("pdf", b"%PDF")]:
        r = client.get(f"{API}/reports/export", headers=h, params={"format": fmt})
        assert r.status_code == 200 and r.content.startswith(sig), fmt
        assert "attachment" in r.headers["content-disposition"]
    sug = client.get(f"{API}/expenses/suggestions", headers=h).json()
    assert sug[0]["item_name"] == "Doodh"
    data = client.get(f"{API}/export", headers=h).json()
    assert len(data["categories"]) == 10 and len(data["expenses"]) > 48
    g = client.get(f"{API}/analytics", headers=h, params={"granularity": "monthly", "from": "2026-06-01", "to": today().isoformat()}).json()
    assert len(g["series"]) >= 3


def test_account_flows(client):
    r = client.post(f"{API}/auth/signup", json={"name": "Temp User", "email": "temp@example.pk", "password": "strongpass1"})
    h = {"Authorization": f"Bearer {r.json()['token']}"}
    assert client.post(f"{API}/auth/login", json={"email": "temp@example.pk", "password": "wrong"}).status_code == 401
    assert client.post(f"{API}/auth/change-password", headers=h, json={"current": "wrong", "next": "newpass123"}).status_code == 400
    assert client.post(f"{API}/auth/change-password", headers=h, json={"current": "strongpass1", "next": "newpass123"}).status_code == 204
    assert client.patch(f"{API}/me", headers=h, json={"name": "Temp Two"}).json()["name"] == "Temp Two"
    assert client.post(f"{API}/auth/forgot-password", json={"email": "temp@example.pk"}).status_code == 204
    assert client.post(f"{API}/auth/forgot-password", json={"email": "nobody@example.pk"}).status_code == 204
    h2 = auth(client, "temp@example.pk", "newpass123")
    assert client.delete(f"{API}/me", headers=h2).status_code == 204
    assert client.get(f"{API}/me", headers=h2).status_code == 401
