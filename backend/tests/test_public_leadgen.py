from fastapi.testclient import TestClient

from app.main import app
from app.config import get_settings
from app.services.trustpilot_processor_service import (
    build_pre_llm_process_voc_rows,
    infer_company_url_from_domain,
    parse_domain_from_work_email,
)
from app.services.trustpilot_apify_service import normalize_apify_review

client = TestClient(app)


class _DummyLeadgenRun:
    def __init__(self, run_id: str):
        self.run_id = run_id


def _mock_upsert_leadgen_run_with_rows(db, **kwargs):
    return _DummyLeadgenRun(kwargs["run_id"])


def test_parse_domain_from_work_email():
    assert parse_domain_from_work_email("person@company.com") == "company.com"


def test_parse_domain_invalid_email():
    try:
        parse_domain_from_work_email("not-an-email")
        assert False, "Expected ValueError for invalid email"
    except ValueError:
        assert True


def test_infer_company_url_from_domain():
    assert infer_company_url_from_domain("company.com") == "https://company.com"


def test_build_pre_llm_process_voc_rows():
    reviews = [
        {
            "review_id": "abc",
            "rating": 5,
            "title": "Great",
            "text": "Loved it",
            "published_at": "2026-01-01T00:00:00Z",
            "country": "GB",
            "language": "en",
            "reviewer_name": "Alex",
            "review_url": "https://example.com/review/abc",
        }
    ]
    rows = build_pre_llm_process_voc_rows(
        normalized_reviews=reviews,
        company_name="Acme",
        company_domain="acme.com",
    )

    assert len(rows) == 1
    assert rows[0]["respondent_id"] == "tp_abc"
    assert rows[0]["client_uuid"] is None
    assert rows[0]["dimension_ref"] == "ref_trustpilot_reviews"
    assert rows[0]["topics"] == []
    assert rows[0]["overall_sentiment"] is None
    assert rows[0]["survey_metadata"]["rating"] == 5
    assert rows[0]["project_name"].startswith("Trustpilot Acme ")
    assert rows[0]["project_id"].startswith("tp_acme_")


def test_normalize_apify_review_with_trustpilot_actor_shape():
    raw_item = {
        "reviewId": "69609ada71a8404ed09faf57",
        "reviewUrl": "https://www.trustpilot.com/reviews/69609ada71a8404ed09faf57",
        "reviewDate": "2026-01-09T08:06:18.000Z",
        "reviewRatingScore": 4,
        "reviewer": "Ms Marsh",
        "reviewersCountry": "GB",
        "reviewTitle": "Tasty meals",
        "reviewDescription": "Tasty meals and varied selection.",
        "reviewLanguage": "en",
    }
    normalized = normalize_apify_review(raw_item)

    assert normalized["review_id"] == "69609ada71a8404ed09faf57"
    assert normalized["rating"] == 4
    assert normalized["title"] == "Tasty meals"
    assert normalized["text"] == "Tasty meals and varied selection."
    assert normalized["published_at"] == "2026-01-09T08:06:18.000Z"
    assert normalized["language"] == "en"
    assert normalized["country"] == "GB"
    assert normalized["reviewer_name"] == "Ms Marsh"


def test_public_leadgen_invalid_email_returns_400():
    response = client.post(
        "/api/public/trustpilot-leadgen",
        json={"work_email": "invalid-email", "max_reviews": 10},
    )
    assert response.status_code == 400


def test_public_leadgen_rejects_personal_email():
    response = client.post(
        "/api/public/trustpilot-leadgen",
        json={"work_email": "person@gmail.com", "max_reviews": 10},
    )
    assert response.status_code == 400


def test_public_leadgen_success(monkeypatch):
    app.state.llm_service = object()

    def mock_extract_context(db, llm_service, url):
        return {
            "name": "Acme",
            "context_text": "Acme makes premium coffee gear.",
            "source_url": url,
        }

    def mock_fetch_reviews(settings, domain, max_reviews):
        return [
            {
                "review_id": "r1",
                "rating": 4,
                "title": "Good service",
                "text": "Shipping was quick and support was helpful.",
                "published_at": "2026-03-01T12:00:00Z",
                "language": "en",
                "country": "GB",
                "review_url": "https://www.trustpilot.com/reviews/r1",
                "reviewer_name": "Sam",
                "source": "trustpilot_apify",
                "raw_item": {},
            }
        ]

    monkeypatch.setattr(
        "app.routers.public_leadgen.extract_product_context_from_url_service",
        mock_extract_context,
    )
    monkeypatch.setattr(
        "app.routers.public_leadgen.fetch_trustpilot_reviews_by_domain",
        mock_fetch_reviews,
    )
    monkeypatch.setattr(
        "app.routers.public_leadgen.upsert_leadgen_run_with_rows",
        _mock_upsert_leadgen_run_with_rows,
    )
    monkeypatch.setattr(get_settings(), "voc_coding_enabled", False)

    response = client.post(
        "/api/public/trustpilot-leadgen",
        json={"work_email": "person@acme.com", "max_reviews": 10},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["company_domain"] == "acme.com"
    assert body["review_count"] == 1
    assert body["file_name"].startswith("trustpilot_llm_input_acme.com_")
    assert "payload" in body
    assert "process_voc_rows_import_ready" in body["payload"]
    assert len(body["payload"]["process_voc_rows_import_ready"]) == 1
    assert body["payload"]["process_voc_rows_import_ready"][0]["processed"] is False
    assert "pre_llm_process_voc_rows" not in body["payload"]
    assert "trustpilot_reviews_normalized" not in body["payload"]


def test_public_leadgen_success_with_debug_payload(monkeypatch):
    app.state.llm_service = object()

    def mock_extract_context(db, llm_service, url):
        return {
            "name": "Acme",
            "context_text": "Acme makes premium coffee gear.",
            "source_url": url,
        }

    def mock_fetch_reviews(settings, domain, max_reviews):
        return [
            {
                "review_id": "r1",
                "rating": 4,
                "title": "Good service",
                "text": "Shipping was quick and support was helpful.",
                "published_at": "2026-03-01T12:00:00Z",
                "language": "en",
                "country": "GB",
                "review_url": "https://www.trustpilot.com/reviews/r1",
                "reviewer_name": "Sam",
                "source": "trustpilot_apify",
                "raw_item": {},
            }
        ]

    monkeypatch.setattr(
        "app.routers.public_leadgen.extract_product_context_from_url_service",
        mock_extract_context,
    )
    monkeypatch.setattr(
        "app.routers.public_leadgen.fetch_trustpilot_reviews_by_domain",
        mock_fetch_reviews,
    )
    monkeypatch.setattr(
        "app.routers.public_leadgen.upsert_leadgen_run_with_rows",
        _mock_upsert_leadgen_run_with_rows,
    )
    monkeypatch.setattr(get_settings(), "voc_coding_enabled", False)

    response = client.post(
        "/api/public/trustpilot-leadgen",
        json={"work_email": "person@acme.com", "max_reviews": 10, "include_debug_data": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert "trustpilot_reviews_normalized" in body["payload"]
    assert "pre_llm_process_voc_rows" in body["payload"]
    assert "processing_instructions" in body["payload"]


def test_public_leadgen_coding_enabled_success(monkeypatch):
    app.state.llm_service = object()

    def mock_extract_context(db, llm_service, url):
        return {
            "name": "Acme",
            "context_text": "Acme makes premium coffee gear.",
            "source_url": url,
        }

    def mock_fetch_reviews(settings, domain, max_reviews):
        return [
            {
                "review_id": "r1",
                "rating": 4,
                "title": "Good service",
                "text": "Shipping was quick and support was helpful.",
                "published_at": "2026-03-01T12:00:00Z",
                "language": "en",
                "country": "GB",
                "review_url": "https://www.trustpilot.com/reviews/r1",
                "reviewer_name": "Sam",
                "source": "trustpilot_apify",
                "raw_item": {},
            }
        ]

    def mock_run_chain(settings, reviews, product_context, resume_run_id, strict_mode):
        return {
            "run_id": "run_123",
            "coded_reviews": [
                {
                    "respondent_id": "tp_r1",
                    "overall_sentiment": "positive",
                    "status": "CODED",
                    "emotional_intensity": "medium",
                    "topics": [
                        {
                            "category": "Delivery",
                            "label": "Fast shipping",
                            "code": "delivery_fast",
                            "sentiment": "positive",
                            "headline": "Shipping was quick",
                            "emotional_intensity": "medium",
                            "confidence": 0.92,
                        }
                    ],
                }
            ],
            "final_codebook": {"categories": []},
            "no_matches": [],
            "changelog": [],
            "stats": {"v1": {}, "final": {}, "improvement": {}},
        }

    monkeypatch.setattr(
        "app.routers.public_leadgen.extract_product_context_from_url_service",
        mock_extract_context,
    )
    monkeypatch.setattr(
        "app.routers.public_leadgen.fetch_trustpilot_reviews_by_domain",
        mock_fetch_reviews,
    )
    monkeypatch.setattr(
        "app.routers.public_leadgen.upsert_leadgen_run_with_rows",
        _mock_upsert_leadgen_run_with_rows,
    )
    monkeypatch.setattr("app.routers.public_leadgen.run_voc_coding_chain", mock_run_chain)
    monkeypatch.setattr(get_settings(), "voc_coding_enabled", True)

    response = client.post(
        "/api/public/trustpilot-leadgen",
        json={"work_email": "person@acme.com", "max_reviews": 10},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == "run_123"
    rows = body["payload"]["process_voc_rows_import_ready"]
    assert len(rows) == 1
    assert rows[0]["processed"] is True
    assert rows[0]["overall_sentiment"] == "positive"
    assert rows[0]["topics"][0]["code"] == "delivery_fast"


def test_public_leadgen_coding_failure_returns_502(monkeypatch):
    app.state.llm_service = object()

    def mock_extract_context(db, llm_service, url):
        return {
            "name": "Acme",
            "context_text": "Acme makes premium coffee gear.",
            "source_url": url,
        }

    def mock_fetch_reviews(settings, domain, max_reviews):
        return [
            {
                "review_id": "r1",
                "rating": 4,
                "title": "Good service",
                "text": "Shipping was quick and support was helpful.",
                "published_at": "2026-03-01T12:00:00Z",
                "language": "en",
                "country": "GB",
                "review_url": "https://www.trustpilot.com/reviews/r1",
                "reviewer_name": "Sam",
                "source": "trustpilot_apify",
                "raw_item": {},
            }
        ]

    def mock_run_chain(settings, reviews, product_context, resume_run_id, strict_mode):
        raise RuntimeError("upstream timeout")

    monkeypatch.setattr(
        "app.routers.public_leadgen.extract_product_context_from_url_service",
        mock_extract_context,
    )
    monkeypatch.setattr(
        "app.routers.public_leadgen.fetch_trustpilot_reviews_by_domain",
        mock_fetch_reviews,
    )
    monkeypatch.setattr("app.routers.public_leadgen.run_voc_coding_chain", mock_run_chain)
    monkeypatch.setattr(get_settings(), "voc_coding_enabled", True)

    response = client.post(
        "/api/public/trustpilot-leadgen",
        json={"work_email": "person@acme.com", "max_reviews": 10},
    )

    assert response.status_code == 502
    assert "[coding]" in response.json()["detail"]
