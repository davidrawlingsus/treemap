from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.auth import get_current_active_founder

client = TestClient(app)


def _override_founder():
    return SimpleNamespace(is_founder=True, email="founder@example.com")


def test_founder_leadgen_runs_list(monkeypatch):
    app.dependency_overrides[get_current_active_founder] = _override_founder

    sample_run = SimpleNamespace(
        run_id="run_abc",
        company_name="Acme",
        company_domain="acme.com",
        work_email="person@acme.com",
        review_count=12,
        coding_enabled=True,
        coding_status="completed",
        generated_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        converted_at=None,
        converted_client_uuid=None,
    )
    monkeypatch.setattr(
        "app.routers.founder_admin.leadgen_voc.list_leadgen_runs",
        lambda db, search=None, limit=100: [sample_run],
    )

    response = client.get("/api/founder-admin/leadgen-runs")
    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["run_id"] == "run_abc"
    assert body["items"][0]["company_domain"] == "acme.com"

    app.dependency_overrides.clear()


def test_founder_leadgen_processed_json(monkeypatch):
    app.dependency_overrides[get_current_active_founder] = _override_founder

    sample_run = SimpleNamespace(run_id="run_abc", payload={"process_voc_rows_import_ready": [{"respondent_id": "tp_1"}]})
    monkeypatch.setattr("app.routers.founder_admin.leadgen_voc.get_leadgen_run", lambda db, run_id: sample_run)

    response = client.get("/api/founder-admin/leadgen-runs/run_abc/processed-json")
    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == "run_abc"
    assert body["payload"]["process_voc_rows_import_ready"][0]["respondent_id"] == "tp_1"

    app.dependency_overrides.clear()


def test_lead_visualization_data_and_summary(monkeypatch):
    app.dependency_overrides[get_current_active_founder] = _override_founder

    monkeypatch.setattr(
        "app.routers.voc_leads.get_leadgen_run",
        lambda db, run_id: SimpleNamespace(run_id=run_id),
    )
    monkeypatch.setattr(
        "app.routers.voc_leads.get_leadgen_rows_as_process_voc_dicts",
        lambda db, run_id: [{"respondent_id": "tp_1", "dimension_ref": "ref_trustpilot_reviews", "topics": []}],
    )
    monkeypatch.setattr(
        "app.routers.voc_leads.build_leadgen_summary_dict",
        lambda db, run_id: {"categories": [{"name": "Delivery", "topics": [{"label": "Fast", "code": "delivery_fast", "verbatim_count": 1, "sample_verbatims": ["Quick"]}]}], "total_verbatims": 1},
    )

    data_resp = client.get("/api/voc/leads/data?run_id=run_abc")
    assert data_resp.status_code == 200
    assert data_resp.json()[0]["respondent_id"] == "tp_1"

    summary_resp = client.get("/api/voc/leads/summary?run_id=run_abc")
    assert summary_resp.status_code == 200
    body = summary_resp.json()
    assert body["total_verbatims"] == 1
    assert body["categories"][0]["topics"][0]["code"] == "delivery_fast"

    app.dependency_overrides.clear()
