"""
Persistence/query helpers for lead-gen VoC staging tables.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.leadgen_voc import LeadgenVocRun, LeadgenVocRow


def _to_dt(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def upsert_leadgen_run_with_rows(
    db: Session,
    *,
    run_id: str,
    work_email: str,
    company_domain: str,
    company_url: str,
    company_name: str,
    review_count: int,
    coding_enabled: bool,
    coding_status: Optional[str],
    generated_at: Optional[datetime],
    payload: Dict[str, Any],
    rows: List[Dict[str, Any]],
) -> LeadgenVocRun:
    run = db.query(LeadgenVocRun).filter(LeadgenVocRun.run_id == run_id).first()
    if run is None:
        run = LeadgenVocRun(run_id=run_id)
        db.add(run)

    run.work_email = work_email
    run.company_domain = company_domain
    run.company_url = company_url
    run.company_name = company_name
    run.review_count = review_count
    run.coding_enabled = coding_enabled
    run.coding_status = coding_status
    run.generated_at = generated_at or datetime.now(timezone.utc)
    run.payload = payload

    db.flush()

    db.query(LeadgenVocRow).filter(LeadgenVocRow.run_id == run_id).delete()
    for row in rows:
        db.add(
            LeadgenVocRow(
                run_id=run_id,
                respondent_id=row.get("respondent_id", ""),
                created=_to_dt(row.get("created")),
                last_modified=_to_dt(row.get("last_modified")),
                client_id=row.get("client_id"),
                client_name=row.get("client_name"),
                project_id=row.get("project_id"),
                project_name=row.get("project_name"),
                total_rows=row.get("total_rows"),
                data_source=row.get("data_source"),
                dimension_ref=row.get("dimension_ref", ""),
                dimension_name=row.get("dimension_name"),
                value=row.get("value"),
                overall_sentiment=row.get("overall_sentiment"),
                topics=row.get("topics"),
                survey_metadata=row.get("survey_metadata"),
                question_text=row.get("question_text"),
                question_type=row.get("question_type"),
                processed=bool(row.get("processed", False)),
            )
        )

    db.flush()
    return run


def list_leadgen_runs(
    db: Session,
    *,
    search: Optional[str] = None,
    limit: int = 100,
) -> List[LeadgenVocRun]:
    query = db.query(LeadgenVocRun)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            LeadgenVocRun.company_name.ilike(term)
            | LeadgenVocRun.company_domain.ilike(term)
            | LeadgenVocRun.work_email.ilike(term)
        )
    return query.order_by(LeadgenVocRun.created_at.desc()).limit(limit).all()


def get_leadgen_run(db: Session, run_id: str) -> Optional[LeadgenVocRun]:
    return db.query(LeadgenVocRun).filter(LeadgenVocRun.run_id == run_id).first()


def delete_leadgen_run(db: Session, run_id: str) -> bool:
    run = get_leadgen_run(db, run_id)
    if run is None:
        return False
    db.delete(run)
    db.flush()
    return True


def get_leadgen_rows_as_process_voc_dicts(db: Session, run_id: str) -> List[Dict[str, Any]]:
    rows = (
        db.query(LeadgenVocRow)
        .filter(LeadgenVocRow.run_id == run_id)
        .order_by(LeadgenVocRow.id.asc())
        .all()
    )
    return [
        {
            "respondent_id": row.respondent_id,
            "client_uuid": None,
            "client_name": row.client_name,
            "project_name": row.project_name,
            "project_id": row.project_id,
            "data_source": row.data_source,
            "dimension_ref": row.dimension_ref,
            "dimension_name": row.dimension_name,
            "question_text": row.question_text,
            "question_type": row.question_type,
            "value": row.value,
            "overall_sentiment": row.overall_sentiment,
            "topics": row.topics or [],
            "survey_metadata": row.survey_metadata,
            "created": row.created.isoformat() if row.created else None,
            "last_modified": row.last_modified.isoformat() if row.last_modified else None,
            "processed": bool(row.processed),
        }
        for row in rows
    ]


def build_leadgen_summary_dict(db: Session, run_id: str) -> Dict[str, Any]:
    rows = (
        db.query(LeadgenVocRow)
        .filter(LeadgenVocRow.run_id == run_id, LeadgenVocRow.value.isnot(None), LeadgenVocRow.value != "")
        .all()
    )

    category_map: Dict[str, Dict[str, Dict[str, Any]]] = {}
    total_verbatims = 0
    for row in rows:
        value = (row.value or "").strip()
        if not value:
            continue
        total_verbatims += 1
        for topic in row.topics or []:
            if not isinstance(topic, dict):
                continue
            category = (topic.get("category") or "").strip()
            label = (topic.get("label") or "").strip()
            if not category or not label:
                continue
            if category not in category_map:
                category_map[category] = {}
            if label not in category_map[category]:
                category_map[category][label] = {"code": topic.get("code"), "verbatims": []}
            category_map[category][label]["verbatims"].append(value)

    categories: List[Dict[str, Any]] = []
    for category_name in sorted(category_map.keys()):
        topics: List[Dict[str, Any]] = []
        for label in sorted(category_map[category_name].keys()):
            data = category_map[category_name][label]
            verbatims = data["verbatims"]
            topics.append(
                {
                    "label": label,
                    "code": data.get("code"),
                    "verbatim_count": len(verbatims),
                    "sample_verbatims": verbatims[:10],
                }
            )
        categories.append({"name": category_name, "topics": topics})
    return {"categories": categories, "total_verbatims": total_verbatims}
