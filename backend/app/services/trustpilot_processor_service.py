"""
Processing utilities for Trustpilot leadgen pipeline.
Builds pre-LLM templates and final import-ready payload wrappers.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List
import re


FREE_EMAIL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "icloud.com",
    "proton.me",
    "protonmail.com",
    "aol.com",
    "live.com",
}


def parse_domain_from_work_email(work_email: str) -> str:
    clean_email = (work_email or "").strip().lower()
    if not clean_email or "@" not in clean_email:
        raise ValueError("Please provide a valid work email address")

    parts = clean_email.split("@")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("Please provide a valid work email address")

    domain = parts[1].strip()
    if "." not in domain:
        raise ValueError("Email domain is invalid")
    return domain


def is_likely_work_email_domain(domain: str) -> bool:
    clean_domain = (domain or "").strip().lower()
    if not clean_domain:
        return False
    return clean_domain not in FREE_EMAIL_DOMAINS


def infer_company_url_from_domain(domain: str) -> str:
    clean_domain = (domain or "").strip().lower()
    clean_domain = clean_domain.replace("https://", "").replace("http://", "")
    clean_domain = clean_domain.strip("/")
    return f"https://{clean_domain}"


def infer_company_name_from_domain(domain: str) -> str:
    clean_domain = (domain or "").strip().lower()
    base = clean_domain.split(".")[0]
    words = re.split(r"[-_]+", base)
    readable = " ".join(word.capitalize() for word in words if word)
    return readable or "Unknown Company"


def _company_slug(company_name: str) -> str:
    base = (company_name or "").strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", base)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "company"


def build_pre_llm_process_voc_rows(
    normalized_reviews: List[Dict[str, Any]],
    company_name: str,
    company_domain: str,
) -> List[Dict[str, Any]]:
    timestamp = datetime.now(timezone.utc).isoformat()
    slug = _company_slug(company_name)

    project_name = "Initial Research"
    project_id = f"lead_{slug}"

    rows: List[Dict[str, Any]] = []
    for idx, review in enumerate(normalized_reviews):
        review_id = review.get("review_id") or f"{company_domain}_{idx}"
        text = (review.get("text") or "").strip()
        title = (review.get("title") or "").strip()
        review_body = text or title

        # Detect source per review (supports mixed-source lists)
        source_hint = (review.get("source") or "").lower()
        if "yotpo" in source_hint:
            source_name, source_key, prefix = "Yotpo", "yotpo", "yp"
        elif "reviews_io" in source_hint or "reviews.io" in source_hint or "reviewsio" in source_hint:
            source_name, source_key, prefix = "Reviews.io", "reviewsio", "rio"
        elif "google" in source_hint:
            source_name, source_key, prefix = "Google Reviews", "google_reviews", "gr"
        else:
            source_name, source_key, prefix = "Trustpilot", "trustpilot", "tp"

        rows.append(
            {
                "respondent_id": f"{prefix}_{review_id}",
                "client_uuid": None,
                "client_name": company_name,
                "project_name": project_name,
                "project_id": project_id,
                "data_source": source_name,
                "dimension_ref": f"ref_{source_key}_reviews",
                "dimension_name": "Reviews",
                "question_text": f"Public {source_name} review text",
                "question_type": "open_text",
                "value": review_body,
                "overall_sentiment": None,
                "topics": [],
                "survey_metadata": {
                    "review_id": review.get("review_id"),
                    "review_url": review.get("review_url"),
                    "rating": review.get("rating"),
                    "review_title": review.get("title"),
                    "review_date": review.get("published_at"),
                    "country": review.get("country"),
                    "language": review.get("language"),
                    "reviewer_name": review.get("reviewer_name"),
                    "source": source_name,
                },
                "created": review.get("published_at") or timestamp,
                "last_modified": timestamp,
                "processed": False,
            }
        )

    return rows


def build_processing_instructions() -> str:
    return (
        "You are given normalized Trustpilot review data and pre-LLM process_voc row templates.\n"
        "Task: return a JSON array of process_voc-compatible rows where each row has:\n"
        "- topics: array of { category, label, code?, sentiment?, confidence? }\n"
        "- overall_sentiment set to one of: positive, neutral, negative, mixed\n"
        "- value preserved as customer verbatim text\n"
        "Rules:\n"
        "1) Do not invent fields outside schema.\n"
        "2) Keep respondent_id, dimension_ref, data_source, project_name unchanged.\n"
        "3) Provide at least one topic for each non-empty review text.\n"
        "4) Use concise, reusable topic labels and consistent category taxonomy.\n"
        "5) Set processed=true when enrichment is complete.\n"
    )


def build_trustpilot_llm_input_payload(
    work_email: str,
    company_domain: str,
    company_url: str,
    company_name: str,
    company_context: Dict[str, Any],
    normalized_reviews: List[Dict[str, Any]],
    process_voc_rows_import_ready: List[Dict[str, Any]],
    run_id: str | None = None,
    coding_result: Dict[str, Any] | None = None,
    include_debug_data: bool = False,
) -> Dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    payload = {
        "version": "trustpilot-import-ready-v2",
        "generated_at": now_iso,
        "input": {
            "work_email": work_email,
            "company_domain": company_domain,
            "company_url": company_url,
            "company_name": company_name,
            "run_id": run_id,
        },
        "company_context": company_context,
        "process_voc_rows_import_ready": process_voc_rows_import_ready,
    }

    if include_debug_data:
        payload["trustpilot_reviews_normalized"] = normalized_reviews
        payload["pre_llm_process_voc_rows"] = build_pre_llm_process_voc_rows(
            normalized_reviews=normalized_reviews,
            company_name=company_name,
            company_domain=company_domain,
        )
        payload["processing_instructions"] = build_processing_instructions()
        if coding_result:
            payload["coding"] = coding_result

    return payload
