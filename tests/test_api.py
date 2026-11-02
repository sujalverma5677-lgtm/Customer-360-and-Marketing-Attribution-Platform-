"""API tests. Run: pip install httpx pytest && pytest tests/test_api.py"""
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_list_customers_pagination():
    r = client.get("/customers?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert len(body["data"]) == 5 and body["total"] >= 5


def test_get_customer_and_404():
    first = client.get("/customers?limit=1").json()["data"][0]["canonical_customer_id"]
    assert client.get(f"/customers/{first}").status_code == 200
    assert client.get("/customers/DOES-NOT-EXIST").status_code == 404


def test_attribution_models_conserve_revenue():
    totals = [client.get(f"/attribution?model={m}").json()["total_attributed_revenue"]
              for m in ["first_touch", "last_touch", "linear", "time_decay", "position_based"]]
    assert max(totals) - min(totals) < 10.0  # all models distribute (approximately) the same total revenue


def test_attribution_invalid_model():
    assert client.get("/attribution?model=bogus").status_code == 422


def test_budget_is_budget_neutral():
    b = client.get("/budget/recommendations").json()
    assert abs(b["total_current_budget"] - b["total_recommended_budget"]) < 1.0