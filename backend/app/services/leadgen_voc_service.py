"""
Persistence/query helpers for lead-gen VoC staging tables.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.leadgen_voc import LeadgenVocRun, LeadgenVocRow
from app.models.client import Client
from app.models.process_voc import ProcessVoc
from app.models.authorized_domain import AuthorizedDomain, AuthorizedDomainClient
from app.models.user import User

logger = logging.getLogger(__name__)


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


def _sanitize_slug(domain: str) -> str:
    """Convert a domain like 'butternutbox.com' into a URL-safe slug like 'butternutbox-com'."""
    slug = re.sub(r"[^a-z0-9]+", "-", domain.lower()).strip("-")
    return slug or "lead"


def _unique_name(db: Session, base_name: str) -> str:
    """Return base_name if unique, otherwise append a numeric suffix."""
    if not db.query(Client).filter(Client.name == base_name).first():
        return base_name
    for i in range(2, 100):
        candidate = f"{base_name} ({i})"
        if not db.query(Client).filter(Client.name == candidate).first():
            return candidate
    return f"{base_name} ({datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')})"


def _unique_slug(db: Session, base_slug: str) -> str:
    """Return base_slug if unique, otherwise append a numeric suffix."""
    if not db.query(Client).filter(Client.slug == base_slug).first():
        return base_slug
    for i in range(2, 100):
        candidate = f"{base_slug}-{i}"
        if not db.query(Client).filter(Client.slug == candidate).first():
            return candidate
    return f"{base_slug}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


def _get_default_founder_id(db: Session) -> Optional[UUID]:
    """Get the first founder user's ID as fallback for unauthenticated lead runs."""
    founder = db.query(User).filter(User.is_founder == True, User.is_active == True).first()
    return founder.id if founder else None


def _ensure_authorized_domain(db: Session, domain: str, client: Client) -> None:
    """Find or create an AuthorizedDomain and link it to the client."""
    normalized = domain.lower().strip()
    if not normalized:
        return

    auth_domain = (
        db.query(AuthorizedDomain)
        .filter(AuthorizedDomain.domain == normalized)
        .first()
    )
    if not auth_domain:
        auth_domain = AuthorizedDomain(domain=normalized)
        db.add(auth_domain)
        db.flush()

    # Check if link already exists
    existing_link = (
        db.query(AuthorizedDomainClient)
        .filter(
            AuthorizedDomainClient.domain_id == auth_domain.id,
            AuthorizedDomainClient.client_id == client.id,
        )
        .first()
    )
    if not existing_link:
        db.add(
            AuthorizedDomainClient(
                domain_id=auth_domain.id,
                client_id=client.id,
            )
        )
        db.flush()


def _copy_rows_to_process_voc(
    db: Session, run_id: str, client_uuid: UUID, replace: bool = True
) -> int:
    """Copy ProcessVoc rows from LeadgenVocRow into a client.

    When ``replace`` is True (a lead client we own), existing ProcessVoc rows for
    the client are cleared first so a re-run refreshes cleanly. When False (we are
    merging a lead run into a company that is already a client), existing rows are
    kept and the lead's VoC is appended — never wipe a real client's data.
    """
    from sqlalchemy import text

    # Use session-scoped replica role to bypass triggers (safe with concurrent users)
    db.execute(text("SET LOCAL session_replication_role = 'replica'"))
    try:
        if replace:
            db.query(ProcessVoc).filter(ProcessVoc.client_uuid == client_uuid).delete()

        rows = (
            db.query(LeadgenVocRow)
            .filter(LeadgenVocRow.run_id == run_id)
            .order_by(LeadgenVocRow.id.asc())
            .all()
        )

        # Delete any existing rows with same respondent_ids to avoid unique constraint violations
        respondent_ids = [r.respondent_id for r in rows if r.respondent_id]
        if respondent_ids:
            for i in range(0, len(respondent_ids), 500):
                chunk = respondent_ids[i:i + 500]
                db.query(ProcessVoc).filter(ProcessVoc.respondent_id.in_(chunk)).delete(synchronize_session=False)
            db.flush()

        for row in rows:
            db.add(
                ProcessVoc(
                    respondent_id=row.respondent_id,
                    created=row.created,
                    last_modified=row.last_modified,
                    client_id=row.client_id,
                    client_name=row.client_name,
                    project_id=row.project_id,
                    project_name=row.project_name,
                    total_rows=row.total_rows,
                    data_source=row.data_source,
                    dimension_ref=row.dimension_ref,
                    dimension_name=row.dimension_name,
                    value=row.value,
                    overall_sentiment=row.overall_sentiment,
                    topics=row.topics,
                    survey_metadata=row.survey_metadata,
                    question_text=row.question_text,
                    question_type=row.question_type,
                    processed=row.processed,
                    client_uuid=client_uuid,
                )
            )
        db.flush()
        return len(rows)
    finally:
        db.execute(text("SET LOCAL session_replication_role = 'origin'"))


def _extract_domain(value: Optional[str]) -> str:
    """Normalize a URL or domain to a bare host, e.g. 'https://www.Foo.com/x' -> 'foo.com'."""
    if not value:
        return ""
    v = value.strip().lower()
    v = re.sub(r"^https?://", "", v)
    v = v.split("/")[0].split("?")[0]
    if v.startswith("www."):
        v = v[4:]
    return v.strip()


def _find_existing_client_by_domain(db: Session, run: LeadgenVocRun) -> Optional[Client]:
    """Find a client that already represents this company, matched by domain.

    Prevents the lead-gen flow from spawning a duplicate '(2)' client when the
    company is already a client (or an earlier lead). Non-lead (real) clients are
    preferred over lead clients. Returns None if no confident match.
    """
    target = _extract_domain(run.company_domain) or _extract_domain(run.company_url)
    if not target:
        return None

    # 1. Explicit authorized-domain link (domains are stored normalized/lowercased).
    by_auth = (
        db.query(Client)
        .join(AuthorizedDomainClient, AuthorizedDomainClient.client_id == Client.id)
        .join(AuthorizedDomain, AuthorizedDomain.id == AuthorizedDomainClient.domain_id)
        .filter(AuthorizedDomain.domain == target)
        .order_by(Client.is_lead.asc().nullslast())
        .first()
    )
    if by_auth:
        return by_auth

    # 2. Domain extracted from the client's own URL (handles scheme/www/slash variance).
    candidates = (
        db.query(Client).filter(Client.client_url.isnot(None)).all()
    )
    matches = [c for c in candidates if _extract_domain(c.client_url) == target]
    if matches:
        # Prefer real clients over leads, then the earliest-created.
        matches.sort(key=lambda c: (bool(c.is_lead), c.created_at or datetime.max.replace(tzinfo=timezone.utc)))
        return matches[0]

    return None


def create_or_update_lead_client(
    db: Session,
    run: LeadgenVocRun,
    founder_user_id: Optional[UUID] = None,
) -> Client:
    """
    Create (or reuse) a Client record flagged as a lead from a LeadgenVocRun,
    copy VoC rows into process_voc, and set up domain authorization.
    """
    # 1. Check if a Client already exists for this run, then fall back to matching an
    #    existing client by company domain (so a company that is already a client, or
    #    an earlier lead, receives the ads + VoC instead of spawning a '(2)' duplicate).
    client = None

    if run.converted_client_uuid:
        client = db.query(Client).filter(Client.id == run.converted_client_uuid).first()

    if not client:
        client = (
            db.query(Client)
            .filter(Client.leadgen_run_id == run.run_id)
            .first()
        )

    if not client:
        client = _find_existing_client_by_domain(db, run)

    # 2. Create or update the Client.
    #    treat_as_lead governs the destructive behaviours (flagging is_lead, wiping and
    #    replacing VoC): only true for our own lead clients — never for a pre-existing
    #    real (non-lead) client we merely matched, whose data must be preserved.
    if client:
        treat_as_lead = bool(client.is_lead)
        # Refresh company info; only (re)flag as a lead if it already is one.
        # For a matched real client, don't overwrite an existing URL — only fill gaps.
        if run.company_url and (treat_as_lead or not client.client_url):
            client.client_url = run.company_url
        client.is_active = True
        if treat_as_lead:
            client.is_lead = True
        # Record run linkage for traceability if not already set.
        if not client.leadgen_run_id:
            client.leadgen_run_id = run.run_id
    else:
        treat_as_lead = True
        f_id = founder_user_id or _get_default_founder_id(db)
        client = Client(
            name=_unique_name(db, run.company_name),
            slug=_unique_slug(db, _sanitize_slug(run.company_domain)),
            client_url=run.company_url,
            is_lead=True,
            is_active=True,
            founder_user_id=f_id,
            leadgen_run_id=run.run_id,
        )
        db.add(client)
        db.flush()

    # 3. Set up domain authorization for magic-link access
    _ensure_authorized_domain(db, run.company_domain, client)

    # 4. Copy VoC rows into process_voc. Merging into a pre-existing real client
    #    appends (replace=False) so we never wipe that client's existing VoC.
    count = _copy_rows_to_process_voc(db, run.run_id, client.id, replace=treat_as_lead)
    logger.info(
        "Lead client %s (%s): copied %d rows to process_voc",
        client.name, client.id, count,
    )

    # 5. Update the run's conversion fields
    run.converted_client_uuid = client.id
    run.converted_at = run.converted_at or datetime.now(timezone.utc)
    db.flush()

    return client
