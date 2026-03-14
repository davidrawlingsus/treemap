from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.auth import get_current_active_founder
from app.database import get_db
from app.main import app
from app.models import ShopifyStoreConnection, ShopifySurveyResponseRaw


class FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return list(self._rows)

    def order_by(self, *_args, **_kwargs):
        return self

    def offset(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def count(self):
        return len(self._rows)


class FakeSession:
    def __init__(self):
        self.store_connections = []
        self.raw_rows = []
        self._next_connection_id = 1
        self._next_raw_id = 1

    def query(self, model):
        if model is ShopifyStoreConnection:
            return FakeQuery(self.store_connections)
        if model is ShopifySurveyResponseRaw:
            return FakeQuery(self.raw_rows)
        return FakeQuery([])

    def add(self, item):
        if isinstance(item, ShopifyStoreConnection):
            item.id = self._next_connection_id
            self._next_connection_id += 1
            now = datetime.now(timezone.utc)
            item.created_at = now
            item.updated_at = now
            self.store_connections.append(item)
            return
        if isinstance(item, ShopifySurveyResponseRaw):
            item.id = self._next_raw_id
            self._next_raw_id += 1
            item.created_at = datetime.now(timezone.utc)
            self.raw_rows.append(item)

    def commit(self):
        return None

    def refresh(self, _item):
        return None

    def rollback(self):
        return None

    def delete(self, item):
        if isinstance(item, ShopifyStoreConnection):
            self.store_connections = [row for row in self.store_connections if row is not item]


client = TestClient(app)


def _override_founder():
    return SimpleNamespace(is_founder=True, email="founder@example.com")


def test_shopify_ingest_and_deduplicate(monkeypatch):
    fake_db = FakeSession()
    app.dependency_overrides[get_db] = lambda: fake_db
    monkeypatch.setattr(
        "app.routers.shopify.get_settings",
        lambda: SimpleNamespace(
            shopify_ingest_shared_secret="test-secret",
            shopify_ingest_max_payload_bytes=500000,
        ),
    )

    payload = {
        "shop_domain": "example-store.myshopify.com",
        "idempotency_key": "idem-12345678",
        "shopify_order_id": "123",
        "order_gid": "gid://shopify/Order/123",
        "customer_reference": "buyer@example.com",
        "survey_version": "v1",
        "answers": {"step_1": {"question": "Q1", "answer": "A1"}},
        "extension_context": {"locale": "en"},
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }

    response = client.post(
        "/api/shopify/survey-responses/raw",
        json=payload,
        headers={"X-Vizualizd-Shopify-Secret": "test-secret"},
    )
    assert response.status_code == 201
    assert response.json()["deduplicated"] is False

    second_response = client.post(
        "/api/shopify/survey-responses/raw",
        json=payload,
        headers={"X-Vizualizd-Shopify-Secret": "test-secret"},
    )
    assert second_response.status_code == 201
    assert second_response.json()["deduplicated"] is True

    app.dependency_overrides.clear()


def test_founder_shopify_store_connections_and_raw_list(monkeypatch):
    fake_db = FakeSession()
    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_current_active_founder] = _override_founder
    monkeypatch.setattr(
        "app.routers.shopify.get_settings",
        lambda: SimpleNamespace(
            shopify_ingest_shared_secret="test-secret",
            shopify_ingest_max_payload_bytes=500000,
        ),
    )

    mapping_response = client.post(
        "/api/founder-admin/shopify/store-connections",
        json={
            "shop_domain": "example-store.myshopify.com",
            "client_uuid": None,
            "status": "active",
            "installed_at": None,
            "uninstalled_at": None,
        },
    )
    assert mapping_response.status_code == 201

    list_response = client.get("/api/founder-admin/shopify/store-connections")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    ingest_response = client.post(
        "/api/shopify/survey-responses/raw",
        json={
            "shop_domain": "example-store.myshopify.com",
            "idempotency_key": "idem-abcdef12",
            "shopify_order_id": "123",
            "order_gid": "gid://shopify/Order/123",
            "customer_reference": "buyer@example.com",
            "survey_version": "v1",
            "answers": {"step_1": {"question": "Q1", "answer": "A1"}},
            "extension_context": {"locale": "en"},
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        },
        headers={"X-Vizualizd-Shopify-Secret": "test-secret"},
    )
    assert ingest_response.status_code == 201

    raw_list_response = client.get("/api/founder-admin/shopify/survey-responses/raw?limit=25")
    assert raw_list_response.status_code == 200
    body = raw_list_response.json()
    assert body["total"] == 1
    assert body["items"][0]["shop_domain"] == "example-store.myshopify.com"

    delete_response = client.delete("/api/founder-admin/shopify/store-connections/example-store.myshopify.com")
    assert delete_response.status_code == 204

    app.dependency_overrides.clear()


def test_shopify_store_sync_and_token_fetch(monkeypatch):
    fake_db = FakeSession()
    app.dependency_overrides[get_db] = lambda: fake_db
    monkeypatch.setattr(
        "app.routers.shopify.get_settings",
        lambda: SimpleNamespace(
            shopify_ingest_shared_secret="test-secret",
            shopify_ingest_max_payload_bytes=500000,
        ),
    )

    sync_response = client.post(
        "/api/shopify/store-connections/sync",
        json={
            "shop_domain": "example-store.myshopify.com",
            "status": "active",
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "offline_access_token": "shpat_test",
            "offline_access_scopes": "read_orders",
            "clear_offline_token": False,
        },
        headers={"X-Vizualizd-Shopify-Secret": "test-secret"},
    )
    assert sync_response.status_code == 200
    assert sync_response.json()["has_offline_access_token"] is True

    token_response = client.get(
        "/api/shopify/store-connections/example-store.myshopify.com/offline-token",
        headers={"X-Vizualizd-Shopify-Secret": "test-secret"},
    )
    assert token_response.status_code == 200
    assert token_response.json()["offline_access_token"] == "shpat_test"

    clear_response = client.post(
        "/api/shopify/store-connections/sync",
        json={
            "shop_domain": "example-store.myshopify.com",
            "status": "uninstalled",
            "uninstalled_at": datetime.now(timezone.utc).isoformat(),
            "clear_offline_token": True,
        },
        headers={"X-Vizualizd-Shopify-Secret": "test-secret"},
    )
    assert clear_response.status_code == 200
    assert clear_response.json()["has_offline_access_token"] is False

    app.dependency_overrides.clear()
