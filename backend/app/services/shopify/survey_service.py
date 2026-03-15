from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    ShopifySurvey,
    ShopifySurveyDisplayRule,
    ShopifySurveyQuestion,
    ShopifySurveyQuestionOrder,
    ShopifySurveyResponse,
    ShopifySurveyResponseAnswer,
    ShopifySurveyVersion,
)
from app.schemas.shopify import (
    ShopifyRuntimeSurveyResponse,
    ShopifySurveyDetailResponse,
    ShopifySurveyDisplayRuleResponse,
    ShopifySurveyListItem,
    ShopifySurveyQuestionResponse,
    ShopifySurveyResponseAnswerItem,
    ShopifySurveyResponseIngestRequest,
    ShopifySurveyResponseIngestResponse,
    ShopifySurveyResponseItem,
    ShopifySurveyResponseList,
    ShopifySurveyUpsertRequest,
    ShopifySurveyVersionResponse,
)


def _normalize_shop_domain(value: str) -> str:
    return value.strip().lower()


def _slugify(value: str) -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    clean = clean.strip("-")
    return clean or "survey"


def _to_question_response(question: ShopifySurveyQuestion, position: int) -> ShopifySurveyQuestionResponse:
    return ShopifySurveyQuestionResponse(
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


def _build_version_response(db: Session, version: ShopifySurveyVersion) -> ShopifySurveyVersionResponse:
    orders = (
        db.query(ShopifySurveyQuestionOrder)
        .filter(ShopifySurveyQuestionOrder.survey_version_id == version.id)
        .order_by(ShopifySurveyQuestionOrder.position.asc())
        .all()
    )
    question_ids = [order.question_id for order in orders]
    question_map = {
        row.id: row
        for row in db.query(ShopifySurveyQuestion)
        .filter(ShopifySurveyQuestion.survey_version_id == version.id, ShopifySurveyQuestion.id.in_(question_ids or [-1]))
        .all()
    }
    questions = []
    for order in orders:
        q = question_map.get(order.question_id)
        if q is not None:
            questions.append(_to_question_response(q, order.position))

    rules = (
        db.query(ShopifySurveyDisplayRule)
        .filter(ShopifySurveyDisplayRule.survey_version_id == version.id)
        .order_by(ShopifySurveyDisplayRule.id.asc())
        .all()
    )
    question_key_map = {q.id: q.question_key for q in question_map.values()}
    display_rules = [
        ShopifySurveyDisplayRuleResponse(
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

    return ShopifySurveyVersionResponse(
        id=version.id,
        version_number=version.version_number,
        status=version.status,
        is_active=bool(version.is_active),
        template_key=version.template_key,
        starts_at=version.starts_at,
        ends_at=version.ends_at,
        published_at=version.published_at,
        settings=dict(version.settings_json or {}),
        questions=questions,
        display_rules=display_rules,
        created_at=version.created_at,
        updated_at=version.updated_at,
    )


def _latest_version(db: Session, survey_id: int, status: str | None = None) -> ShopifySurveyVersion | None:
    query = db.query(ShopifySurveyVersion).filter(ShopifySurveyVersion.survey_id == survey_id)
    if status:
        query = query.filter(ShopifySurveyVersion.status == status)
    return query.order_by(ShopifySurveyVersion.version_number.desc()).first()


def list_surveys(db: Session, shop_domain: str) -> list[ShopifySurveyListItem]:
    normalized_shop = _normalize_shop_domain(shop_domain)
    surveys = (
        db.query(ShopifySurvey)
        .filter(ShopifySurvey.shop_domain == normalized_shop)
        .order_by(ShopifySurvey.updated_at.desc(), ShopifySurvey.id.desc())
        .all()
    )
    result: list[ShopifySurveyListItem] = []
    for survey in surveys:
        active = (
            db.query(ShopifySurveyVersion)
            .filter(ShopifySurveyVersion.survey_id == survey.id, ShopifySurveyVersion.is_active.is_(True))
            .order_by(ShopifySurveyVersion.version_number.desc())
            .first()
        )
        result.append(
            ShopifySurveyListItem(
                id=survey.id,
                shop_domain=survey.shop_domain,
                handle=survey.handle,
                title=survey.title,
                status=survey.status,
                description=survey.description,
                active_version_id=active.id if active else None,
                active_version_number=active.version_number if active else None,
                created_at=survey.created_at,
                updated_at=survey.updated_at,
            )
        )
    return result


def upsert_survey_draft(
    db: Session,
    shop_domain: str,
    payload: ShopifySurveyUpsertRequest,
    survey_id: int | None = None,
) -> ShopifySurveyDetailResponse:
    normalized_shop = _normalize_shop_domain(shop_domain)
    now = datetime.now(timezone.utc)

    if survey_id is None:
        handle = f"{_slugify(payload.title)}-{int(now.timestamp())}"
        survey = ShopifySurvey(
            shop_domain=normalized_shop,
            handle=handle,
            title=payload.title,
            status=payload.status,
            description=payload.description,
        )
        db.add(survey)
        db.flush()
    else:
        survey = (
            db.query(ShopifySurvey)
            .filter(ShopifySurvey.id == survey_id, ShopifySurvey.shop_domain == normalized_shop)
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
        draft_version = ShopifySurveyVersion(
            shop_domain=normalized_shop,
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
    draft_version.settings_json = payload.draft_version.settings

    db.query(ShopifySurveyDisplayRule).filter(
        ShopifySurveyDisplayRule.survey_version_id == draft_version.id
    ).delete(synchronize_session=False)
    db.query(ShopifySurveyQuestionOrder).filter(
        ShopifySurveyQuestionOrder.survey_version_id == draft_version.id
    ).delete(synchronize_session=False)
    db.query(ShopifySurveyQuestion).filter(
        ShopifySurveyQuestion.survey_version_id == draft_version.id
    ).delete(synchronize_session=False)
    db.flush()

    question_key_to_id: dict[str, int] = {}
    ordered_questions = sorted(payload.draft_version.questions, key=lambda q: q.position)
    for idx, question in enumerate(ordered_questions):
        row = ShopifySurveyQuestion(
            shop_domain=normalized_shop,
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
            ShopifySurveyQuestionOrder(
                shop_domain=normalized_shop,
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
            ShopifySurveyDisplayRule(
                shop_domain=normalized_shop,
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
    return get_survey_detail(db, normalized_shop, survey.id)


def publish_survey(db: Session, shop_domain: str, survey_id: int) -> ShopifySurveyDetailResponse:
    normalized_shop = _normalize_shop_domain(shop_domain)
    survey = (
        db.query(ShopifySurvey)
        .filter(ShopifySurvey.id == survey_id, ShopifySurvey.shop_domain == normalized_shop)
        .first()
    )
    if survey is None:
        raise ValueError("Survey not found")

    draft_version = _latest_version(db, survey.id, status="draft")
    if draft_version is None:
        raise ValueError("No draft version available to publish")

    db.query(ShopifySurveyVersion).filter(
        ShopifySurveyVersion.shop_domain == normalized_shop
    ).update({"is_active": False}, synchronize_session=False)
    draft_version.status = "published"
    draft_version.is_active = True
    draft_version.published_at = datetime.now(timezone.utc)
    survey.status = "active"
    db.commit()

    return get_survey_detail(db, normalized_shop, survey.id)


def unpublish_survey(db: Session, shop_domain: str, survey_id: int) -> ShopifySurveyDetailResponse:
    normalized_shop = _normalize_shop_domain(shop_domain)
    survey = (
        db.query(ShopifySurvey)
        .filter(ShopifySurvey.id == survey_id, ShopifySurvey.shop_domain == normalized_shop)
        .first()
    )
    if survey is None:
        raise ValueError("Survey not found")

    db.query(ShopifySurveyVersion).filter(
        ShopifySurveyVersion.survey_id == survey.id,
        ShopifySurveyVersion.is_active.is_(True),
    ).update({"is_active": False}, synchronize_session=False)
    survey.status = "inactive"
    db.commit()
    return get_survey_detail(db, normalized_shop, survey.id)


def get_survey_detail(db: Session, shop_domain: str, survey_id: int) -> ShopifySurveyDetailResponse:
    normalized_shop = _normalize_shop_domain(shop_domain)
    survey = (
        db.query(ShopifySurvey)
        .filter(ShopifySurvey.id == survey_id, ShopifySurvey.shop_domain == normalized_shop)
        .first()
    )
    if survey is None:
        raise ValueError("Survey not found")

    draft = _latest_version(db, survey.id, status="draft")
    active = (
        db.query(ShopifySurveyVersion)
        .filter(ShopifySurveyVersion.survey_id == survey.id, ShopifySurveyVersion.is_active.is_(True))
        .order_by(ShopifySurveyVersion.version_number.desc())
        .first()
    )

    return ShopifySurveyDetailResponse(
        id=survey.id,
        shop_domain=survey.shop_domain,
        handle=survey.handle,
        title=survey.title,
        status=survey.status,
        description=survey.description,
        draft_version=_build_version_response(db, draft) if draft else None,
        active_version=_build_version_response(db, active) if active else None,
        created_at=survey.created_at,
        updated_at=survey.updated_at,
    )


def get_active_runtime_survey(db: Session, shop_domain: str) -> ShopifyRuntimeSurveyResponse | None:
    normalized_shop = _normalize_shop_domain(shop_domain)
    now = datetime.now(timezone.utc)
    version = (
        db.query(ShopifySurveyVersion)
        .join(ShopifySurvey, ShopifySurvey.id == ShopifySurveyVersion.survey_id)
        .filter(
            ShopifySurveyVersion.shop_domain == normalized_shop,
            ShopifySurveyVersion.status == "published",
            ShopifySurveyVersion.is_active.is_(True),
            ShopifySurvey.status == "active",
        )
        .order_by(ShopifySurveyVersion.published_at.desc(), ShopifySurveyVersion.id.desc())
        .first()
    )
    if version is None:
        return None
    if version.starts_at and now < version.starts_at:
        return None
    if version.ends_at and now > version.ends_at:
        return None

    survey = db.query(ShopifySurvey).filter(ShopifySurvey.id == version.survey_id).first()
    if survey is None:
        return None
    version_payload = _build_version_response(db, version)
    return ShopifyRuntimeSurveyResponse(
        survey_id=survey.id,
        survey_title=survey.title,
        survey_description=survey.description,
        survey_version_id=version.id,
        survey_version_number=version.version_number,
        starts_at=version.starts_at,
        ends_at=version.ends_at,
        settings=version_payload.settings,
        questions=version_payload.questions,
        display_rules=version_payload.display_rules,
    )


def ingest_survey_response(
    db: Session,
    payload: ShopifySurveyResponseIngestRequest,
) -> ShopifySurveyResponseIngestResponse:
    normalized_shop = _normalize_shop_domain(payload.shop_domain)
    existing = (
        db.query(ShopifySurveyResponse)
        .filter(
            ShopifySurveyResponse.shop_domain == normalized_shop,
            ShopifySurveyResponse.idempotency_key == payload.idempotency_key,
        )
        .first()
    )
    if existing:
        return ShopifySurveyResponseIngestResponse(
            id=existing.id,
            shop_domain=existing.shop_domain,
            survey_id=existing.survey_id,
            survey_version_id=existing.survey_version_id,
            deduplicated=True,
            submitted_at=existing.submitted_at,
        )

    active = get_active_runtime_survey(db, normalized_shop)
    survey_id = payload.survey_id or (active.survey_id if active else None)
    survey_version_id = payload.survey_version_id or (active.survey_version_id if active else None)

    response = ShopifySurveyResponse(
        shop_domain=normalized_shop,
        survey_id=survey_id,
        survey_version_id=survey_version_id,
        idempotency_key=payload.idempotency_key,
        shopify_order_id=payload.shopify_order_id,
        order_gid=payload.order_gid,
        customer_reference=payload.customer_reference,
        submitted_at=payload.submitted_at,
        extension_context_json=payload.extension_context,
    )
    db.add(response)
    db.flush()

    for answer in payload.answers:
        answer_json = answer.answer_json
        if isinstance(answer_json, (str, int, float, bool)):
            answer_json = {"value": answer_json}
        db.add(
            ShopifySurveyResponseAnswer(
                shop_domain=normalized_shop,
                response_id=response.id,
                question_id=answer.question_id,
                question_key=answer.question_key,
                answer_text=answer.answer_text,
                answer_json=answer_json,
            )
        )

    db.commit()
    db.refresh(response)
    return ShopifySurveyResponseIngestResponse(
        id=response.id,
        shop_domain=response.shop_domain,
        survey_id=response.survey_id,
        survey_version_id=response.survey_version_id,
        deduplicated=False,
        submitted_at=response.submitted_at,
    )


def list_survey_responses(
    db: Session,
    shop_domain: str,
    survey_id: int,
    limit: int,
    offset: int,
) -> ShopifySurveyResponseList:
    normalized_shop = _normalize_shop_domain(shop_domain)
    query = (
        db.query(ShopifySurveyResponse)
        .filter(
            ShopifySurveyResponse.shop_domain == normalized_shop,
            ShopifySurveyResponse.survey_id == survey_id,
        )
    )
    total = query.count()
    rows = (
        query.order_by(ShopifySurveyResponse.submitted_at.desc(), ShopifySurveyResponse.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    items: list[ShopifySurveyResponseItem] = []
    for row in rows:
        answers = (
            db.query(ShopifySurveyResponseAnswer)
            .filter(ShopifySurveyResponseAnswer.response_id == row.id)
            .order_by(ShopifySurveyResponseAnswer.id.asc())
            .all()
        )
        items.append(
            ShopifySurveyResponseItem(
                id=row.id,
                survey_id=row.survey_id,
                survey_version_id=row.survey_version_id,
                shopify_order_id=row.shopify_order_id,
                customer_reference=row.customer_reference,
                submitted_at=row.submitted_at,
                answers=[
                    ShopifySurveyResponseAnswerItem(
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
    return ShopifySurveyResponseList(items=items, total=total)
