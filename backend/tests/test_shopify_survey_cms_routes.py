from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _set_secret(monkeypatch):
    monkeypatch.setattr(
        "app.routers.shopify.get_settings",
        lambda: SimpleNamespace(
            shopify_ingest_shared_secret="test-secret",
            shopify_ingest_max_payload_bytes=500000,
        ),
    )


def test_shopify_templates_endpoint(monkeypatch):
    _set_secret(monkeypatch)
    monkeypatch.setattr(
        "app.routers.shopify.public.get_survey_templates",
        lambda: [
            {
                "key": "why_buy_today",
                "name": "Why did you buy today?",
                "description": "test",
                "questions": [],
            }
        ],
    )

    response = client.get(
        "/api/shopify/survey-templates",
        headers={"X-Vizualizd-Shopify-Secret": "test-secret"},
    )
    assert response.status_code == 200
    assert response.json()[0]["key"] == "why_buy_today"


def test_shopify_runtime_active_endpoint(monkeypatch):
    _set_secret(monkeypatch)
    monkeypatch.setattr(
        "app.routers.shopify.public.get_active_runtime_survey",
        lambda _db, _shop_domain: {
            "survey_id": 1,
            "survey_title": "Runtime survey",
            "survey_description": "desc",
            "survey_version_id": 10,
            "survey_version_number": 2,
            "starts_at": None,
            "ends_at": None,
            "settings": {},
            "questions": [],
            "display_rules": [],
        },
    )

    response = client.get(
        "/api/shopify/survey-runtime/active?shop_domain=example-store.myshopify.com",
        headers={"X-Vizualizd-Shopify-Secret": "test-secret"},
    )
    assert response.status_code == 200
    assert response.json()["survey"]["survey_id"] == 1


def test_shopify_create_survey_endpoint(monkeypatch):
    _set_secret(monkeypatch)
    now = datetime.now(timezone.utc).isoformat()
    monkeypatch.setattr(
        "app.routers.shopify.public.upsert_survey_draft",
        lambda _db, _shop, _payload, survey_id=None: {
            "id": 5,
            "shop_domain": "example-store.myshopify.com",
            "handle": "post-purchase",
            "title": "Post-purchase survey",
            "status": "active",
            "description": "desc",
            "draft_version": None,
            "active_version": None,
            "created_at": now,
            "updated_at": now,
        },
    )
    payload = {
        "title": "Post-purchase survey",
        "description": "desc",
        "status": "active",
        "draft_version": {
            "template_key": None,
            "starts_at": None,
            "ends_at": None,
            "settings": {},
            "questions": [],
            "display_rules": [],
        },
    }
    response = client.post(
        "/api/shopify/surveys/example-store.myshopify.com",
        headers={"X-Vizualizd-Shopify-Secret": "test-secret"},
        json=payload,
    )
    assert response.status_code == 201
    assert response.json()["id"] == 5


def test_shopify_normalized_ingest_endpoint(monkeypatch):
    _set_secret(monkeypatch)
    submitted_at = datetime.now(timezone.utc).isoformat()
    monkeypatch.setattr(
        "app.routers.shopify.public.ingest_survey_response",
        lambda _db, _payload: {
            "id": 17,
            "shop_domain": "example-store.myshopify.com",
            "survey_id": 1,
            "survey_version_id": 2,
            "deduplicated": False,
            "submitted_at": submitted_at,
        },
    )

    payload = {
        "shop_domain": "example-store.myshopify.com",
        "idempotency_key": "idem-abcdef12",
        "survey_id": 1,
        "survey_version_id": 2,
        "shopify_order_id": "123",
        "order_gid": "gid://shopify/Order/123",
        "customer_reference": "buyer@example.com",
        "answers": [{"question_key": "q1", "answer_text": "Great"}],
        "extension_context": {"extension_target": "purchase.thank-you.block.render"},
        "submitted_at": submitted_at,
    }
    response = client.post(
        "/api/shopify/survey-responses",
        headers={"X-Vizualizd-Shopify-Secret": "test-secret"},
        json=payload,
    )
    assert response.status_code == 201
    assert response.json()["id"] == 17
