from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
import re
from typing import Any
from uuid import UUID

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models import Client
from app.models.widget_survey import (
    WidgetSurvey,
    WidgetSurveyDisplayRule,
    WidgetSurveyHeartbeat,
    WidgetSurveyImpression,
    WidgetSurveyQuestion,
    WidgetSurveyQuestionOrder,
    WidgetSurveyResponse,
    WidgetSurveyResponseAnswer,
    WidgetSurveyVersion,
)
from app.schemas.widget_survey import (
    WidgetRuntimeSurveyResponse,
    WidgetSurveyDetailResponse,
    WidgetSurveyDisplayRuleResponse,
    WidgetSurveyFrequency,
    WidgetSurveyInstallationStatus,
    WidgetSurveyHeartbeatItem,
    WidgetSurveyListItem,
    WidgetSurveyQuestionResponse,
    WidgetSurveyResponseAnswerItem,
    WidgetSurveyResponseIngestRequest,
    WidgetSurveyResponseIngestResponse,
    WidgetSurveyResponseItem,
    WidgetSurveyResponseList,
    WidgetSurveyStats,
    WidgetSurveyTriggerRules,
    WidgetSurveyUpsertRequest,
    WidgetSurveyUrlTargeting,
    WidgetSurveyVersionResponse,
)


def _slugify(value: str) -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    clean = clean.strip("-")
    return clean or "survey"


def _to_question_response(question: WidgetSurveyQuestion, position: int) -> WidgetSurveyQuestionResponse:
    return WidgetSurveyQuestionResponse(
        id=question.id,
        question_key=question.question_key,
        title=question.title,
        answer_type=question.answer_type,
        is_required=bool(question.is_required),
        is_enabled=bool(question.is_enabled),
        position=position,
        options=list(question.options_json or []),
        settings=dict(question.settings_json or {}),
    )


def _extract_version_config(settings: dict[str, Any] | None) -> tuple[
    WidgetSurveyUrlTargeting, WidgetSurveyTriggerRules, WidgetSurveyFrequency
]:
    s = settings or {}
    url_targeting = WidgetSurveyUrlTargeting(**(s.get("url_targeting") or {}))
    trigger_rules = WidgetSurveyTriggerRules(**(s.get("trigger_rules") or {}))
    frequency = WidgetSurveyFrequency(**(s.get("frequency") or {}))
    return url_targeting, trigger_rules, frequency


def _build_version_response(db: Session, version: WidgetSurveyVersion) -> WidgetSurveyVersionResponse:
    orders = (
        db.query(WidgetSurveyQuestionOrder)
        .filter(WidgetSurveyQuestionOrder.survey_version_id == version.id)
        .order_by(WidgetSurveyQuestionOrder.position.asc())
        .all()
    )
    question_ids = [order.question_id for order in orders]
    question_map = {
        row.id: row
        for row in db.query(WidgetSurveyQuestion)
        .filter(WidgetSurveyQuestion.survey_version_id == version.id, WidgetSurveyQuestion.id.in_(question_ids or [-1]))
        .all()
    }
    questions = []
    for order in orders:
        q = question_map.get(order.question_id)
        if q is not None:
            questions.append(_to_question_response(q, order.position))

    rules = (
        db.query(WidgetSurveyDisplayRule)
        .filter(WidgetSurveyDisplayRule.survey_version_id == version.id)
        .order_by(WidgetSurveyDisplayRule.id.asc())
        .all()
    )
    question_key_map = {q.id: q.question_key for q in question_map.values()}
    display_rules = [
        WidgetSurveyDisplayRuleResponse(
            id=rule.id,
            target_question_id=rule.target_question_id,
            target_question_key=question_key_map.get(rule.target_question_id, ""),
            source_question_id=rule.source_question_id,
            source_question_key=question_key_map.get(rule.source_question_id, ""),
            operator=rule.operator,
            comparison_value=rule.comparison_value,
        )
        for rule in rules
    ]

    url_targeting, trigger_rules, frequency = _extract_version_config(version.settings_json)
    # Remove widget-specific keys from generic settings dict
    generic_settings = dict(version.settings_json or {})
    for key in ("url_targeting", "trigger_rules", "frequency"):
        generic_settings.pop(key, None)

    return WidgetSurveyVersionResponse(
        id=version.id,
        version_number=version.version_number,
        status=version.status,
        is_active=bool(version.is_active),
        template_key=version.template_key,
        starts_at=version.starts_at,
        ends_at=version.ends_at,
        published_at=version.published_at,
        settings=generic_settings,
        url_targeting=url_targeting,
        trigger_rules=trigger_rules,
        frequency=frequency,
        questions=questions,
        display_rules=display_rules,
        created_at=version.created_at,
        updated_at=version.updated_at,
    )


def _latest_version(db: Session, survey_id: int, status: str | None = None) -> WidgetSurveyVersion | None:
    query = db.query(WidgetSurveyVersion).filter(WidgetSurveyVersion.survey_id == survey_id)
    if status:
        query = query.filter(WidgetSurveyVersion.status == status)
    return query.order_by(WidgetSurveyVersion.version_number.desc()).first()


# ── CRUD ─────────────────────────────────────────────────────────────


def list_surveys(db: Session, client_id: UUID) -> list[WidgetSurveyListItem]:
    surveys = (
        db.query(WidgetSurvey)
        .filter(WidgetSurvey.client_id == client_id)
        .order_by(WidgetSurvey.updated_at.desc(), WidgetSurvey.id.desc())
        .all()
    )
    result: list[WidgetSurveyListItem] = []
    for survey in surveys:
        active = (
            db.query(WidgetSurveyVersion)
            .filter(WidgetSurveyVersion.survey_id == survey.id, WidgetSurveyVersion.is_active.is_(True))
            .order_by(WidgetSurveyVersion.version_number.desc())
            .first()
        )
        impression_count = 0
        response_count = 0
        if active:
            impression_count = (
                db.query(sa_func.coalesce(sa_func.sum(WidgetSurveyImpression.impression_count), 0))
                .filter(WidgetSurveyImpression.survey_version_id == active.id)
                .scalar()
            ) or 0
            response_count = (
                db.query(sa_func.count(WidgetSurveyResponse.id))
                .filter(WidgetSurveyResponse.survey_id == survey.id)
                .scalar()
            ) or 0

        result.append(
            WidgetSurveyListItem(
                id=survey.id,
                client_id=survey.client_id,
                handle=survey.handle,
                title=survey.title,
                status=survey.status,
                description=survey.description,
                active_version_id=active.id if active else None,
                active_version_number=active.version_number if active else None,
                impression_count=int(impression_count),
                response_count=int(response_count),
                created_at=survey.created_at,
                updated_at=survey.updated_at,
            )
        )
    return result


def upsert_survey_draft(
    db: Session,
    client_id: UUID,
    payload: WidgetSurveyUpsertRequest,
    survey_id: int | None = None,
) -> WidgetSurveyDetailResponse:
    now = datetime.now(timezone.utc)

    if survey_id is None:
        handle = f"{_slugify(payload.title)}-{int(now.timestamp())}"
        survey = WidgetSurvey(
            client_id=client_id,
            handle=handle,
            title=payload.title,
            status=payload.status,
            description=payload.description,
        )
        db.add(survey)
        db.flush()
    else:
        survey = (
            db.query(WidgetSurvey)
            .filter(WidgetSurvey.id == survey_id, WidgetSurvey.client_id == client_id)
            .first()
        )
        if survey is None:
            raise ValueError("Survey not found")
        survey.title = payload.title
        survey.status = payload.status
        survey.description = payload.description

    draft_version = _latest_version(db, survey.id, status="draft")
    if draft_version is None:
        latest = _latest_version(db, survey.id)
        next_number = (latest.version_number + 1) if latest else 1
        draft_version = WidgetSurveyVersion(
            client_id=client_id,
            survey_id=survey.id,
            version_number=next_number,
            status="draft",
            is_active=False,
        )
        db.add(draft_version)
        db.flush()

    draft_version.template_key = payload.draft_version.template_key
    draft_version.starts_at = payload.draft_version.starts_at
    draft_version.ends_at = payload.draft_version.ends_at
    # Store url_targeting, trigger_rules, frequency inside settings_json
    settings = dict(payload.draft_version.settings)
    settings["url_targeting"] = payload.draft_version.url_targeting.model_dump()
    settings["trigger_rules"] = payload.draft_version.trigger_rules.model_dump()
    settings["frequency"] = payload.draft_version.frequency.model_dump()
    draft_version.settings_json = settings

    # Clear existing questions/rules for this draft
    db.query(WidgetSurveyDisplayRule).filter(
        WidgetSurveyDisplayRule.survey_version_id == draft_version.id
    ).delete(synchronize_session=False)
    db.query(WidgetSurveyQuestionOrder).filter(
        WidgetSurveyQuestionOrder.survey_version_id == draft_version.id
    ).delete(synchronize_session=False)
    db.query(WidgetSurveyQuestion).filter(
        WidgetSurveyQuestion.survey_version_id == draft_version.id
    ).delete(synchronize_session=False)
    db.flush()

    question_key_to_id: dict[str, int] = {}
    ordered_questions = sorted(payload.draft_version.questions, key=lambda q: q.position)
    for idx, question in enumerate(ordered_questions):
        row = WidgetSurveyQuestion(
            client_id=client_id,
            survey_version_id=draft_version.id,
            question_key=question.question_key,
            title=question.title,
            answer_type=question.answer_type,
            is_required=question.is_required,
            is_enabled=question.is_enabled,
            options_json=question.options,
            settings_json=question.settings,
        )
        db.add(row)
        db.flush()
        question_key_to_id[question.question_key] = row.id
        db.add(
            WidgetSurveyQuestionOrder(
                client_id=client_id,
                survey_version_id=draft_version.id,
                question_id=row.id,
                position=idx,
            )
        )

    for rule in payload.draft_version.display_rules:
        target_id = question_key_to_id.get(rule.target_question_key)
        source_id = question_key_to_id.get(rule.source_question_key)
        if target_id is None or source_id is None:
            continue
        db.add(
            WidgetSurveyDisplayRule(
                client_id=client_id,
                survey_version_id=draft_version.id,
                target_question_id=target_id,
                source_question_id=source_id,
                operator=rule.operator,
                comparison_value=rule.comparison_value,
            )
        )

    db.commit()
    db.refresh(survey)
    db.refresh(draft_version)
    return get_survey_detail(db, client_id, survey.id)


def publish_survey(db: Session, client_id: UUID, survey_id: int) -> WidgetSurveyDetailResponse:
    survey = (
        db.query(WidgetSurvey)
        .filter(WidgetSurvey.id == survey_id, WidgetSurvey.client_id == client_id)
        .first()
    )
    if survey is None:
        raise ValueError("Survey not found")

    draft_version = _latest_version(db, survey.id, status="draft")
    if draft_version is None:
        raise ValueError("No draft version available to publish")

    # Deactivate all versions for this client (one active survey per client)
    db.query(WidgetSurveyVersion).filter(
        WidgetSurveyVersion.client_id == client_id
    ).update({"is_active": False}, synchronize_session=False)
    draft_version.status = "published"
    draft_version.is_active = True
    draft_version.published_at = datetime.now(timezone.utc)
    survey.status = "active"
    db.commit()

    return get_survey_detail(db, client_id, survey.id)


def unpublish_survey(db: Session, client_id: UUID, survey_id: int) -> WidgetSurveyDetailResponse:
    survey = (
        db.query(WidgetSurvey)
        .filter(WidgetSurvey.id == survey_id, WidgetSurvey.client_id == client_id)
        .first()
    )
    if survey is None:
        raise ValueError("Survey not found")

    db.query(WidgetSurveyVersion).filter(
        WidgetSurveyVersion.survey_id == survey.id,
        WidgetSurveyVersion.is_active.is_(True),
    ).update({"is_active": False}, synchronize_session=False)
    survey.status = "inactive"
    db.commit()
    return get_survey_detail(db, client_id, survey.id)


def get_survey_detail(db: Session, client_id: UUID, survey_id: int) -> WidgetSurveyDetailResponse:
    survey = (
        db.query(WidgetSurvey)
        .filter(WidgetSurvey.id == survey_id, WidgetSurvey.client_id == client_id)
        .first()
    )
    if survey is None:
        raise ValueError("Survey not found")

    draft = _latest_version(db, survey.id, status="draft")
    active = (
        db.query(WidgetSurveyVersion)
        .filter(WidgetSurveyVersion.survey_id == survey.id, WidgetSurveyVersion.is_active.is_(True))
        .order_by(WidgetSurveyVersion.version_number.desc())
        .first()
    )

    # If no draft and no active version, fall back to the latest version
    # (e.g. after unpublish, the published version is deactivated but still
    # holds the questions/settings that should be editable)
    fallback = None
    if not draft and not active:
        fallback = _latest_version(db, survey.id)

    return WidgetSurveyDetailResponse(
        id=survey.id,
        client_id=survey.client_id,
        handle=survey.handle,
        title=survey.title,
        status=survey.status,
        description=survey.description,
        draft_version=_build_version_response(db, draft or fallback) if (draft or fallback) else None,
        active_version=_build_version_response(db, active) if active else None,
        created_at=survey.created_at,
        updated_at=survey.updated_at,
    )


def delete_survey(db: Session, client_id: UUID, survey_id: int) -> None:
    survey = (
        db.query(WidgetSurvey)
        .filter(WidgetSurvey.id == survey_id, WidgetSurvey.client_id == client_id)
        .first()
    )
    if survey is None:
        raise ValueError("Survey not found")

    response_ids = [
        row.id
        for row in db.query(WidgetSurveyResponse.id)
        .filter(WidgetSurveyResponse.survey_id == survey_id)
        .all()
    ]
    if response_ids:
        db.query(WidgetSurveyResponseAnswer).filter(
            WidgetSurveyResponseAnswer.response_id.in_(response_ids)
        ).delete(synchronize_session=False)
        db.query(WidgetSurveyResponse).filter(
            WidgetSurveyResponse.id.in_(response_ids)
        ).delete(synchronize_session=False)

    db.delete(survey)
    db.commit()


# ── Runtime (widget-facing) ─────────────────────────────────────────


def get_active_runtime_survey(db: Session, client_id: UUID) -> WidgetRuntimeSurveyResponse | None:
    now = datetime.now(timezone.utc)
    version = (
        db.query(WidgetSurveyVersion)
        .join(WidgetSurvey, WidgetSurvey.id == WidgetSurveyVersion.survey_id)
        .filter(
            WidgetSurveyVersion.client_id == client_id,
            WidgetSurveyVersion.status == "published",
            WidgetSurveyVersion.is_active.is_(True),
            WidgetSurvey.status == "active",
        )
        .order_by(WidgetSurveyVersion.published_at.desc(), WidgetSurveyVersion.id.desc())
        .first()
    )
    if version is None:
        return None
    if version.starts_at and now < version.starts_at:
        return None
    if version.ends_at and now > version.ends_at:
        return None

    survey = db.query(WidgetSurvey).filter(WidgetSurvey.id == version.survey_id).first()
    if survey is None:
        return None

    version_payload = _build_version_response(db, version)

    # Read clarity_project_id from client settings
    client = db.query(Client).filter(Client.id == client_id).first()
    clarity_project_id = None
    if client and client.settings:
        clarity_project_id = client.settings.get("clarity_project_id")

    settings = version_payload.settings or {}
    return WidgetRuntimeSurveyResponse(
        survey_id=survey.id,
        survey_title=survey.title,
        survey_description=survey.description,
        widget_title=settings.get("widget_title"),
        submit_label=settings.get("submit_label"),
        survey_version_id=version.id,
        survey_version_number=version.version_number,
        starts_at=version.starts_at,
        ends_at=version.ends_at,
        settings=version_payload.settings,
        url_targeting=version_payload.url_targeting,
        trigger_rules=version_payload.trigger_rules,
        frequency=version_payload.frequency,
        clarity_project_id=clarity_project_id,
        questions=version_payload.questions,
        display_rules=version_payload.display_rules,
    )


# ── Response ingest ──────────────────────────────────────────────────


def ingest_survey_response(
    db: Session,
    client_id: UUID,
    payload: WidgetSurveyResponseIngestRequest,
) -> WidgetSurveyResponseIngestResponse:
    existing = (
        db.query(WidgetSurveyResponse)
        .filter(
            WidgetSurveyResponse.client_id == client_id,
            WidgetSurveyResponse.idempotency_key == payload.idempotency_key,
        )
        .first()
    )
    if existing:
        return WidgetSurveyResponseIngestResponse(
            id=existing.id,
            survey_id=existing.survey_id,
            survey_version_id=existing.survey_version_id,
            deduplicated=True,
            submitted_at=existing.submitted_at,
        )

    active = get_active_runtime_survey(db, client_id)
    survey_id = payload.survey_id or (active.survey_id if active else None)
    survey_version_id = payload.survey_version_id or (active.survey_version_id if active else None)

    # Resolve clarity_project_id: payload first, then client settings
    clarity_project_id = payload.clarity_project_id
    if not clarity_project_id and active:
        clarity_project_id = active.clarity_project_id

    response = WidgetSurveyResponse(
        client_id=client_id,
        survey_id=survey_id,
        survey_version_id=survey_version_id,
        idempotency_key=payload.idempotency_key,
        site_domain=payload.site_domain,
        page_url=payload.page_url,
        customer_reference=payload.customer_reference,
        clarity_session_id=payload.clarity_session_id,
        clarity_project_id=clarity_project_id,
        clarity_replay_url=payload.clarity_replay_url,
        submitted_at=payload.submitted_at,
    )
    db.add(response)
    db.flush()

    for answer in payload.answers:
        answer_json = answer.answer_json
        if isinstance(answer_json, (str, int, float, bool)):
            answer_json = {"value": answer_json}
        db.add(
            WidgetSurveyResponseAnswer(
                client_id=client_id,
                response_id=response.id,
                question_id=answer.question_id,
                question_key=answer.question_key,
                answer_text=answer.answer_text,
                answer_json=answer_json,
            )
        )

    db.commit()
    db.refresh(response)
    return WidgetSurveyResponseIngestResponse(
        id=response.id,
        survey_id=response.survey_id,
        survey_version_id=response.survey_version_id,
        deduplicated=False,
        submitted_at=response.submitted_at,
    )


def list_survey_responses(
    db: Session,
    client_id: UUID,
    survey_id: int,
    limit: int,
    offset: int,
) -> WidgetSurveyResponseList:
    query = (
        db.query(WidgetSurveyResponse)
        .filter(
            WidgetSurveyResponse.client_id == client_id,
            WidgetSurveyResponse.survey_id == survey_id,
        )
    )
    total = query.count()
    rows = (
        query.order_by(WidgetSurveyResponse.submitted_at.desc(), WidgetSurveyResponse.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    items: list[WidgetSurveyResponseItem] = []
    for row in rows:
        answers = (
            db.query(WidgetSurveyResponseAnswer)
            .filter(WidgetSurveyResponseAnswer.response_id == row.id)
            .order_by(WidgetSurveyResponseAnswer.id.asc())
            .all()
        )
        items.append(
            WidgetSurveyResponseItem(
                id=row.id,
                survey_id=row.survey_id,
                survey_version_id=row.survey_version_id,
                site_domain=row.site_domain,
                page_url=row.page_url,
                customer_reference=row.customer_reference,
                clarity_session_id=row.clarity_session_id,
                clarity_project_id=row.clarity_project_id,
                submitted_at=row.submitted_at,
                answers=[
                    WidgetSurveyResponseAnswerItem(
                        id=answer.id,
                        question_id=answer.question_id,
                        question_key=answer.question_key,
                        answer_text=answer.answer_text,
                        answer_json=answer.answer_json,
                    )
                    for answer in answers
                ],
            )
        )
    return WidgetSurveyResponseList(items=items, total=total)


# ── Heartbeat / Impression / Stats ──────────────────────────────────


def record_heartbeat(db: Session, client_id: UUID, page_url: str) -> None:
    url_hash = hashlib.sha256(page_url.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)
    stmt = pg_insert(WidgetSurveyHeartbeat).values(
        client_id=client_id,
        page_url=page_url,
        page_url_hash=url_hash,
        last_seen_at=now,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_widget_survey_heartbeats_client_page",
        set_={"last_seen_at": now},
    )
    db.execute(stmt)
    db.commit()


def record_impression(db: Session, survey_version_id: int) -> None:
    today = date.today()
    stmt = pg_insert(WidgetSurveyImpression).values(
        survey_version_id=survey_version_id,
        date=today,
        impression_count=1,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_widget_survey_impressions_version_date",
        set_={"impression_count": WidgetSurveyImpression.impression_count + 1},
    )
    db.execute(stmt)
    db.commit()


def get_installation_status(db: Session, client_id: UUID) -> WidgetSurveyInstallationStatus:
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    heartbeats = (
        db.query(WidgetSurveyHeartbeat)
        .filter(WidgetSurveyHeartbeat.client_id == client_id)
        .order_by(WidgetSurveyHeartbeat.last_seen_at.desc())
        .all()
    )
    pages = [
        WidgetSurveyHeartbeatItem(page_url=hb.page_url, last_seen_at=hb.last_seen_at)
        for hb in heartbeats
    ]
    is_installed = any(hb.last_seen_at >= cutoff for hb in heartbeats)
    return WidgetSurveyInstallationStatus(is_installed=is_installed, pages=pages)


def get_survey_stats(db: Session, client_id: UUID, survey_id: int) -> WidgetSurveyStats:
    survey = (
        db.query(WidgetSurvey)
        .filter(WidgetSurvey.id == survey_id, WidgetSurvey.client_id == client_id)
        .first()
    )
    if survey is None:
        raise ValueError("Survey not found")

    active = (
        db.query(WidgetSurveyVersion)
        .filter(WidgetSurveyVersion.survey_id == survey.id, WidgetSurveyVersion.is_active.is_(True))
        .first()
    )

    impression_count = 0
    if active:
        impression_count = int(
            db.query(sa_func.coalesce(sa_func.sum(WidgetSurveyImpression.impression_count), 0))
            .filter(WidgetSurveyImpression.survey_version_id == active.id)
            .scalar() or 0
        )

    response_count = int(
        db.query(sa_func.count(WidgetSurveyResponse.id))
        .filter(WidgetSurveyResponse.survey_id == survey_id)
        .scalar() or 0
    )

    response_rate = None
    if impression_count > 0:
        response_rate = round(response_count / impression_count * 100, 1)

    # Check if any response has a detected clarity_project_id
    detected = (
        db.query(WidgetSurveyResponse.clarity_project_id)
        .filter(
            WidgetSurveyResponse.survey_id == survey_id,
            WidgetSurveyResponse.clarity_project_id.isnot(None),
        )
        .order_by(WidgetSurveyResponse.id.desc())
        .first()
    )

    return WidgetSurveyStats(
        impression_count=impression_count,
        response_count=response_count,
        response_rate=response_rate,
        detected_clarity_project_id=detected[0] if detected else None,
    )
