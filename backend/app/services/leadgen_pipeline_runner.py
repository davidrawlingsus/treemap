"""
Background pipeline runner for lead-gen flows.

Runs the full VoC pipeline in a daemon thread:
scrape → context → extract → taxonomy → validate → classify → generate ads → email.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.database import SessionLocal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Ad generation prompts (moved from frontend js/prompt-studio/main.js)
# ---------------------------------------------------------------------------

GENERATE_SYSTEM_PROMPT = """You are a Senior Facebook Ads Creative Strategist specialising in performance creative grounded in Voice of Customer (VoC) data.

You receive a creative brief containing:
- A VoC topic with verbatim customer quotes
- Assigned creative lanes to write in
- Assigned close patterns for each lane
- Available proof modalities and block structure fuel
- Supporting material from related topics
- Business context including brand and landing page

Your job: produce one production-ready Facebook ad concept per assigned lane.

## CREATIVE RULES

### Voice & Tone
- Warm, human, unmistakably on the reader's side
- Readable at 3rd\u20135th grade level
- Conversational \u2014 like a friend who genuinely understands what they're going through
- Never pushy, never performatively enthusiastic

### The Friend Test
Before finalising any ad: would a genuine friend who cares about this person and happens to know about this product actually say this? If it sounds like it's pushing rather than guiding, rewrite it.

### VoC Integration
- HIGH-rated verbatims: use aggressively. Let customer language drive the narrative.
- MEDIUM-rated verbatims: extract the emotional core. Translate into brand-compliant phrasing.
- Supporting material verbatims: use as secondary proof or texture.
- NEVER invent customer sentiment not present in the VoC data.
- NEVER force verbatim quotes that sound unnatural in context.

### Pain & Benefit Language
- Be specific and concrete. Replace abstract statements with vivid, situational ones.
- Use the Block Structure when building major pain or benefit sections:
  1. Overarching statement
  2. Specific, vivid descriptions (use verbatims here)
  3. Dimensional, lived-in experience (the mind movie)
  4. Emotional recap

### Proof Integration
- Follow every significant claim with a proof element.
- Use the proof modalities specified in the brief.
- Embed proof inside sentences, don't bolt it on after.

### Close Architecture
Each ad must close with the pattern specified in the brief. The close must:
1. Bridge \u2014 connect the ad's emotional payload to the action
2. Direct \u2014 tell them exactly what to do
3. Shrink \u2014 make the action feel tiny relative to the emotional payoff

### Single Variable Testing
Each ad tests ONE clear belief. 1 belief \u2192 1 ad \u2192 1 test variable.

### Headline Mechanics
- 9\u201313 words / ~65 characters
- Authority trigrams where natural: "This is why...", "The reason why...", "What happens when...\""""

GENERATE_USER_PROMPT = """Here is the business context for this brand:

<business_context>
{BUSINESS_CONTEXT}
</business_context>

Here is the Voice of Customer data \u2014 raw Trustpilot reviews from real customers of this brand. Mine these aggressively for emotional truth, pain language, benefit language, and proof.

<voc_data>
{FULL_RAW_REVIEWS_FOR_THIS_TOPIC}
</voc_data>

The VoC analysis identified these as the strongest themes in this data:

<theme_guidance>
Primary theme: {TOPIC_LABEL} ({CATEGORY})
Supporting themes: {LIST_OF_SECONDARY_TOPIC_LABELS_IN_SAME_CATEGORY}

Key VoC signals to mine:
{VERBATIM_BULLETS}

Available proof modalities in this data: {PROOF_TAGS}
Available emotional anchors: {BLOCK_TAGS}
</theme_guidance>

Write ads for the following lanes: {COMMA_SEPARATED_LANE_NAMES}

Each lane should produce 1 ad concept. Use a different close pattern for each ad. Ground every ad in the VoC data above \u2014 no invented sentiment. Return the JSON and nothing else."""


# ---------------------------------------------------------------------------
# Creative selection logic (ported from frontend creative-selection.js)
# ---------------------------------------------------------------------------

LANE_PRIORITY = [
    "LANE:TRANSFORMATION", "LANE:STORY", "LANE:SURPRISE", "LANE:PROOF",
    "LANE:CURIOSITY", "LANE:MISTAKE_AVOIDANCE", "LANE:INSTRUCTIONAL",
]

ALL_LANES = [
    "LANE:SURPRISE", "LANE:STORY", "LANE:CURIOSITY", "LANE:GUIDANCE",
    "LANE:INSTRUCTIONAL", "LANE:HYPERBOLE", "LANE:NEWNESS", "LANE:RANKING",
    "LANE:PATTERN_BREAK", "LANE:PROOF", "LANE:MISTAKE_AVOIDANCE", "LANE:TRANSFORMATION",
]

ALL_LANE_NAMES = ", ".join(l.replace("LANE:", "").replace("_", " ") for l in ALL_LANES)


def _qualifies_for_ads(topic: Dict) -> bool:
    priority = topic.get("creative_priority", "")
    if priority == "PRIMARY":
        return True
    if priority == "SECONDARY":
        cv = topic.get("creative_value_summary", {})
        return (cv.get("HIGH", 0) >= 1) or (cv.get("MEDIUM", 0) >= 3)
    # If creative_priority is not set (schema doesn't enforce it),
    # qualify any topic with a reasonable signal count
    if not priority and topic.get("signal_count", 0) >= 3:
        return True
    return False


def _assemble_full_reviews(review_ids: List[str], reviews: List[Dict]) -> List[Dict]:
    if not review_ids or not reviews:
        return []
    by_respondent = {r.get("respondent_id"): r for r in reviews if r.get("respondent_id")}
    by_positional = {}
    for idx, r in enumerate(reviews):
        by_positional[f"R-{idx + 1:03d}"] = r

    results = []
    seen = set()
    for rid in review_ids:
        if rid in seen:
            continue
        seen.add(rid)
        review = by_respondent.get(rid) or by_positional.get(rid)
        if review:
            results.append({
                "review_id": rid,
                "text": review.get("value", ""),
                "rating": (review.get("survey_metadata") or {}).get("rating"),
            })
    return results


def build_creative_payloads(
    taxonomy: Dict, reviews: List[Dict], business_context: Dict,
) -> List[Dict]:
    """Build rich payloads for ad generation from a validated taxonomy."""
    payloads = []
    categories = taxonomy.get("categories", [])
    singletons = taxonomy.get("singletons", [])

    for cat in categories:
        for topic in cat.get("topics", []):
            if not _qualifies_for_ads(topic):
                continue
            usable_as = topic.get("usable_as", [])
            available_lanes = [t for t in usable_as if t.startswith("LANE:")]
            if available_lanes:
                selected = [l for l in LANE_PRIORITY if l in available_lanes]
                cap = 3 if topic.get("creative_priority") == "PRIMARY" else 2
                selected = selected[:cap]
            else:
                # No usable_as data — default to top 3 lanes
                selected = LANE_PRIORITY[:3]
            if not selected:
                continue

            all_review_ids = set(topic.get("review_ids", []))
            secondary_labels = []
            for t in cat.get("topics", []):
                if t.get("label") != topic.get("label") and t.get("creative_priority") == "SECONDARY":
                    secondary_labels.append(t.get("label", ""))
                    for rid in t.get("review_ids", []):
                        all_review_ids.add(rid)
            for s in singletons:
                if s.get("nearest_category") == cat.get("category") and s.get("review_id"):
                    all_review_ids.add(s["review_id"])

            full_reviews = _assemble_full_reviews(list(all_review_ids), reviews)
            proof_tags = ", ".join(t for t in usable_as if t.startswith("PROOF:"))
            block_tags = ", ".join(t for t in usable_as if t.startswith("BLOCK:"))
            verbatim_bullets = "\n".join(
                f'- "{v.get("text", "")}" ({v.get("review_id", "")})'
                for v in topic.get("verbatims", [])
            )

            payloads.append({
                "topic_label": topic.get("label", ""),
                "category": cat.get("category", ""),
                "creative_priority": topic.get("creative_priority", ""),
                "signal_count": topic.get("signal_count", 0),
                "lanes": selected,
                "lane_names": ", ".join(l.replace("LANE:", "") for l in selected),
                "full_reviews": full_reviews,
                "secondary_labels": secondary_labels,
                "proof_tags": proof_tags,
                "block_tags": block_tags,
                "verbatim_bullets": verbatim_bullets,
                "business_context": business_context,
            })

    # Sort: PRIMARY first, then by signal count
    prio_order = {"PRIMARY": 0, "SECONDARY": 1, "SUPPORTING": 2}
    payloads.sort(key=lambda p: (prio_order.get(p["creative_priority"], 2), -(p.get("signal_count", 0))))

    # Assign all 12 lanes to each payload
    for p in payloads:
        p["lanes"] = ALL_LANES
        p["lane_names"] = ALL_LANE_NAMES

    return payloads[:3]  # Cap at 3 topics


def assemble_user_prompt(template: str, payload: Dict) -> str:
    """Assemble the user prompt for a single topic payload."""
    bc = payload.get("business_context", {})
    parts = [
        f"Brand: {bc['brand']}" if bc.get("brand") else "",
        f"Product/Business Context: {bc['product']}" if bc.get("product") else "",
        f"Category: {bc['category']}" if bc.get("category") else "",
        f"Website: {bc['website']}" if bc.get("website") else "",
        f"Primary Claims: {bc['primary_claims']}" if bc.get("primary_claims") else "",
        f"Target Customer: {bc['target_customer']}" if bc.get("target_customer") else "",
        f"Key Competitors / Alternatives: {bc['competitors']}" if bc.get("competitors") else "",
    ]
    business_context_text = "\n".join(p for p in parts if p)

    reviews_text = "\n\n---\n\n".join(
        f'Review {r["review_id"]} (Rating: {r.get("rating") or "N/A"}):\n"{r["text"]}"'
        for r in payload.get("full_reviews", [])
    )
    secondary_list = ", ".join(payload.get("secondary_labels", [])) or "None"

    return (
        template
        .replace("{BUSINESS_CONTEXT}", business_context_text)
        .replace("{FULL_RAW_REVIEWS_FOR_THIS_TOPIC}", reviews_text)
        .replace("{TOPIC_LABEL}", payload.get("topic_label", ""))
        .replace("{CATEGORY}", payload.get("category", ""))
        .replace("{LIST_OF_SECONDARY_TOPIC_LABELS_IN_SAME_CATEGORY}", secondary_list)
        .replace("{VERBATIM_BULLETS}", payload.get("verbatim_bullets", ""))
        .replace("{PROOF_TAGS}", payload.get("proof_tags") or "None specified")
        .replace("{BLOCK_TAGS}", payload.get("block_tags") or "None specified")
        .replace("{COMMA_SEPARATED_LANE_NAMES}", payload.get("lane_names", ""))
    )


# ---------------------------------------------------------------------------
# Pipeline status helpers
# ---------------------------------------------------------------------------

def _update_status(db, run, status: str):
    """Update the coding_status on a LeadgenVocRun and commit."""
    run.coding_status = status
    db.commit()
    logger.info("[pipeline %s] status -> %s", run.run_id, status)


# ---------------------------------------------------------------------------
# Full pipeline runner (runs in background thread)
# ---------------------------------------------------------------------------

def run_full_pipeline_background(run_id: str) -> None:
    """Launch the full pipeline in a daemon thread."""
    t = threading.Thread(target=_run_full_pipeline, args=(run_id,), daemon=True)
    t.start()
    logger.info("[pipeline %s] Background thread started", run_id)


def _run_full_pipeline(run_id: str) -> None:
    """Execute the full lead-gen pipeline. Runs in a background thread."""
    from app.models.leadgen_voc import LeadgenVocRun, LeadgenVocRow
    from app.models import FacebookAd
    from app.services.leadgen_voc_service import (
        upsert_leadgen_run_with_rows,
        create_or_update_lead_client,
    )
    from app.services.trustpilot_processor_service import (
        build_pre_llm_process_voc_rows,
        infer_company_url_from_domain,
    )
    from app.services.trustpilot_apify_service import fetch_trustpilot_reviews_by_domain
    from app.services.voc_coding_chain_service import call_claude_json_schema
    from app.routers.founder_admin.prompt_studio import (
        EXTRACT_SCHEMA, EXTRACT_SYSTEM_PROMPT_DEFAULT, EXTRACT_USER_PROMPT_DEFAULT,
        TAXONOMY_SCHEMA, TAXONOMY_SYSTEM_PROMPT_DEFAULT, TAXONOMY_USER_PROMPT_DEFAULT,
        VALIDATE_SCHEMA, VALIDATE_SYSTEM_PROMPT_DEFAULT, VALIDATE_USER_PROMPT_DEFAULT,
        CLASSIFY_SCHEMA, CLASSIFY_SYSTEM_PROMPT_DEFAULT, CLASSIFY_USER_PROMPT_DEFAULT,
        GENERATE_AD_SCHEMA, _taxonomy_to_codebook_text,
    )
    from app.services.voc_coding_chain_service import (
        merge_coded_reviews_into_rows,
        _format_reviews_for_coding,
    )
    from app.services.leadgen_voc_service import get_leadgen_rows_as_process_voc_dicts

    db = SessionLocal()
    settings = get_settings()

    try:
        run = db.query(LeadgenVocRun).filter(LeadgenVocRun.run_id == run_id).first()
        if not run:
            logger.error("[pipeline %s] Run not found", run_id)
            return

        company_domain = run.company_domain
        company_url = run.company_url
        company_name = run.company_name

        # ── Step 1: Scrape ──
        _update_status(db, run, "scraping")
        normalized_reviews = fetch_trustpilot_reviews_by_domain(
            settings=settings,
            domain=company_domain,
            max_reviews=200,
        )
        logger.info("[pipeline %s] Scraped %d reviews", run_id, len(normalized_reviews))

        if not normalized_reviews:
            _update_status(db, run, "failed")
            logger.warning("[pipeline %s] No reviews found for %s", run_id, company_domain)
            return

        rows = build_pre_llm_process_voc_rows(
            normalized_reviews=normalized_reviews,
            company_name=company_name,
            company_domain=company_domain,
        )
        upsert_leadgen_run_with_rows(
            db,
            run_id=run_id,
            work_email=run.work_email,
            company_domain=company_domain,
            company_url=company_url,
            company_name=company_name,
            review_count=len(rows),
            coding_enabled=True,
            coding_status="scraping",
            generated_at=datetime.now(timezone.utc),
            payload={"source": "leadgen_pipeline_runner"},
            rows=rows,
        )
        lead_client = create_or_update_lead_client(db, run)
        db.commit()
        logger.info("[pipeline %s] Persisted %d rows, client=%s", run_id, len(rows), lead_client.id)

        # ── Step 2: Context extraction (optional) ──
        _update_status(db, run, "extracting_context")
        context_text = ""
        try:
            from app.services.product_context_service import extract_product_context_from_url_service
            from app.services.llm_service import LLMService
            llm = LLMService(
                openai_api_key=getattr(settings, "openai_api_key", None),
                anthropic_api_key=getattr(settings, "anthropic_api_key", None),
            )
            ctx = extract_product_context_from_url_service(db, llm, company_url)
            context_text = ctx.get("context_text", "") if isinstance(ctx, dict) else ""
            logger.info("[pipeline %s] Context extracted (%d chars)", run_id, len(context_text))
        except Exception as e:
            logger.warning("[pipeline %s] Context extraction failed (continuing): %s", run_id, e)
            context_text = company_name

        # ── Step 3: Extract signals ──
        _update_status(db, run, "extracting")
        reviews_text = "\n\n".join(
            f"Review {r.get('respondent_id', '')}:\n{r.get('value', '')}"
            for r in rows if r.get("value")
        )
        extract_user = (
            EXTRACT_USER_PROMPT_DEFAULT
            .replace("{BUSINESS_CONTEXT}", context_text)
            .replace("{RAW_REVIEWS}", reviews_text)
        )
        extract_output = call_claude_json_schema(
            settings=settings,
            model=getattr(settings, "voc_coding_discover_model", "claude-sonnet-4-5-20250929"),
            system_prompt=EXTRACT_SYSTEM_PROMPT_DEFAULT,
            user_prompt=extract_user,
            schema=EXTRACT_SCHEMA,
            temperature=0.0,
            max_tokens=64000,
        )
        logger.info("[pipeline %s] Extract: %d signals", run_id, len(extract_output.get("signals", [])))

        # ── Step 4: Taxonomy ──
        _update_status(db, run, "building_taxonomy")
        taxonomy_user = (
            TAXONOMY_USER_PROMPT_DEFAULT
            .replace("{BUSINESS_CONTEXT}", context_text)
            .replace("{JSON_OUTPUT_FROM_PROMPT_1}", json.dumps(extract_output, ensure_ascii=False))
            .replace("{REVIEW_COUNT}", str(len(extract_output.get("signals", []))))
        )
        taxonomy_output = call_claude_json_schema(
            settings=settings,
            model=getattr(settings, "voc_coding_discover_model", "claude-sonnet-4-5-20250929"),
            system_prompt=TAXONOMY_SYSTEM_PROMPT_DEFAULT,
            user_prompt=taxonomy_user,
            schema=TAXONOMY_SCHEMA,
            temperature=0.0,
            max_tokens=64000,
        )
        logger.info("[pipeline %s] Taxonomy: %d categories", run_id, len(taxonomy_output.get("categories", [])))

        # ── Step 5: Validate ──
        _update_status(db, run, "validating")
        validate_user = (
            VALIDATE_USER_PROMPT_DEFAULT
            .replace("{BUSINESS_CONTEXT}", context_text)
            .replace("{JSON_OUTPUT_FROM_PROMPT_2}", json.dumps(taxonomy_output, ensure_ascii=False))
            .replace("{JSON_OUTPUT_FROM_PROMPT_1}", json.dumps(extract_output, ensure_ascii=False))
        )
        validate_output = call_claude_json_schema(
            settings=settings,
            model=getattr(settings, "voc_coding_discover_model", "claude-sonnet-4-5-20250929"),
            system_prompt=VALIDATE_SYSTEM_PROMPT_DEFAULT,
            user_prompt=validate_user,
            schema=VALIDATE_SCHEMA,
            temperature=0.0,
            max_tokens=64000,
        )
        logger.info("[pipeline %s] Validate: %d categories", run_id, len(validate_output.get("categories", [])))

        # ── Step 6: Classify (Haiku) ──
        _update_status(db, run, "classifying")
        raw_rows = get_leadgen_rows_as_process_voc_dicts(db, run_id)
        codebook_text = _taxonomy_to_codebook_text(validate_output)
        all_coded: List[Dict] = []
        batch_size = 20

        for start in range(0, len(raw_rows), batch_size):
            batch = raw_rows[start:start + batch_size]
            review_text = _format_reviews_for_coding(batch)
            classify_user = (
                CLASSIFY_USER_PROMPT_DEFAULT
                .replace("{TAXONOMY}", codebook_text)
                .replace("{REVIEWS}", review_text)
            )
            try:
                result = call_claude_json_schema(
                    settings=settings,
                    model="claude-haiku-4-5-20251001",
                    system_prompt=CLASSIFY_SYSTEM_PROMPT_DEFAULT,
                    user_prompt=classify_user,
                    schema=CLASSIFY_SCHEMA,
                    temperature=0.2,
                    max_tokens=8192,
                )
                coded = result.get("coded_reviews", [])
                # Normalize underscores
                for review in coded:
                    for topic in review.get("topics", []):
                        if topic.get("category"):
                            topic["category"] = topic["category"].replace("_", " ")
                        if topic.get("label"):
                            topic["label"] = topic["label"].replace("_", " ")
                all_coded.extend(coded)
            except Exception as e:
                logger.warning("[pipeline %s] Classify batch %d failed: %s", run_id, start // batch_size, e)

        merged_rows = merge_coded_reviews_into_rows(raw_rows, all_coded)
        coded_count = sum(1 for r in merged_rows if r.get("topics"))
        logger.info("[pipeline %s] Classified: %d/%d rows with topics", run_id, coded_count, len(merged_rows))

        # Update leadgen_voc_rows with topics
        coded_map = {r["respondent_id"]: r for r in merged_rows if r.get("respondent_id")}
        db_rows = db.query(LeadgenVocRow).filter(LeadgenVocRow.run_id == run_id).all()
        for db_row in db_rows:
            m = coded_map.get(db_row.respondent_id)
            if m and m.get("topics"):
                db_row.topics = m["topics"]
                db_row.overall_sentiment = m.get("overall_sentiment")
                db_row.processed = True
        db.flush()

        run.coding_enabled = True
        run.coding_status = "classifying"
        db.flush()

        # Re-sync to process_voc
        lead_client = create_or_update_lead_client(db, run)
        db.commit()

        # ── Step 7: Generate ads ──
        _update_status(db, run, "generating_ads")
        business_context = {
            "brand": company_name,
            "product": context_text,
            "website": company_url,
        }
        payloads = build_creative_payloads(validate_output, raw_rows, business_context)
        logger.info("[pipeline %s] Generating ads for %d topics (validate has %d categories, %d total topics)",
                     run_id, len(payloads),
                     len(validate_output.get("categories", [])),
                     sum(len(c.get("topics", [])) for c in validate_output.get("categories", [])))

        total_ads = 0
        MAX_TOTAL_ADS = 36
        for payload in payloads:
            if total_ads >= MAX_TOTAL_ADS:
                break
            user_prompt = assemble_user_prompt(GENERATE_USER_PROMPT, payload)
            try:
                ad_result = call_claude_json_schema(
                    settings=settings,
                    model="claude-opus-4-6",
                    system_prompt=GENERATE_SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    schema=GENERATE_AD_SCHEMA,
                    temperature=0.7,
                    max_tokens=64000,
                )
                ads = ad_result.get("ads", [])
                if isinstance(ads, str):
                    try:
                        ads = json.loads(ads)
                    except (json.JSONDecodeError, ValueError):
                        ads = []

                remaining = MAX_TOTAL_ADS - total_ads
                if len(ads) > remaining:
                    ads = ads[:remaining]
                total_ads += len(ads)

                # Save as FacebookAd records
                for ad in ads:
                    full_json = dict(ad)
                    if full_json.get("testType") and not full_json.get("angle"):
                        full_json["angle"] = full_json.pop("testType")

                    db.add(FacebookAd(
                        client_id=lead_client.id,
                        primary_text=ad.get("primary_text", ""),
                        headline=ad.get("headline", ""),
                        description=ad.get("description", ""),
                        call_to_action=ad.get("call_to_action", "LEARN_MORE"),
                        destination_url=ad.get("destination_url", ""),
                        voc_evidence=ad.get("voc_evidence", []),
                        full_json=full_json,
                        status="draft",
                    ))
                db.flush()
                logger.info("[pipeline %s] Generated %d ads for '%s' (total: %d)",
                            run_id, len(ads), payload.get("topic_label", ""), total_ads)
            except Exception as e:
                logger.error("[pipeline %s] Ad generation failed for '%s': %s",
                             run_id, payload.get("topic_label", ""), e)

        db.commit()

        # ── Step 8: Send completion email ──
        _update_status(db, run, "sending_email")
        try:
            _send_completion_email(db, run, lead_client, settings)
        except Exception as e:
            logger.error("[pipeline %s] Email send failed: %s", run_id, e)

        _update_status(db, run, "completed")
        logger.info("[pipeline %s] Pipeline completed! %d reviews, %d ads", run_id, len(rows), total_ads)

    except Exception as exc:
        logger.error("[pipeline %s] Pipeline failed: %s", run_id, exc, exc_info=True)
        try:
            run = db.query(LeadgenVocRun).filter(LeadgenVocRun.run_id == run_id).first()
            if run:
                run.coding_status = "failed"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def _send_completion_email(db, run, client, settings) -> None:
    """Send the 'your analysis is ready' email with a magic link."""
    from app.auth import generate_magic_link_token
    from app.models.user import User
    from app.models.membership import Membership
    from app.utils import build_email_service
    from urllib.parse import quote

    email = run.work_email
    if not email:
        logger.warning("[pipeline %s] No work_email on run, skipping email", run.run_id)
        return

    # Find or create user for this email
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user:
        user = User(email=email.lower(), name=email.split("@")[0], is_active=True)
        db.add(user)
        db.flush()

    # Ensure membership exists
    existing = db.query(Membership).filter(
        Membership.user_id == user.id, Membership.client_id == client.id
    ).first()
    if not existing:
        now = datetime.now(timezone.utc)
        db.add(Membership(
            user_id=user.id, client_id=client.id,
            role="viewer", status="active",
            provisioned_at=now, provisioned_by=user.id,
            provisioning_method="leadgen_pipeline", joined_at=now,
        ))
        db.flush()

    # Generate magic link
    token, token_hash, expires_at = generate_magic_link_token()
    user.magic_link_token = token_hash
    user.magic_link_expires_at = expires_at
    user.last_magic_link_sent_at = datetime.now(timezone.utc)
    db.commit()

    redirect_path = getattr(settings, "magic_link_redirect_path", "").lstrip("/")
    base_url = getattr(settings, "frontend_base_url", "https://vizualizd.mapthegap.ai").rstrip("/")
    if redirect_path:
        magic_link_url = f"{base_url}/{redirect_path}?token={quote(token)}&email={quote(email)}"
    else:
        magic_link_url = f"{base_url}?token={quote(token)}&email={quote(email)}"

    # Send email
    email_service = build_email_service(settings)
    if not email_service or not email_service.is_configured():
        logger.warning("[pipeline %s] Email service not configured, logging link instead", run.run_id)
        logger.info("[pipeline %s] Magic link for %s: %s", run.run_id, email, magic_link_url)
        return

    company_name = run.company_name or "your company"
    subject = f"Your VoC analysis for {company_name} is ready"

    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f5f5f5;">
    <div style="background-color: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <h1 style="color: #1a1a1a; font-size: 24px; margin-top: 0;">Your analysis is ready</h1>
        <p>We've analyzed the customer reviews for <strong>{company_name}</strong> and generated ad concepts based on your Voice of Customer data.</p>
        <p>Click below to view your:</p>
        <ul>
            <li><strong>Topic treemap</strong> — see what your customers are really saying</li>
            <li><strong>Generated ads</strong> — production-ready ad concepts grounded in real customer language</li>
        </ul>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{magic_link_url}" style="display: inline-block; background-color: #1a73e8; color: #fff; text-decoration: none; padding: 14px 28px; border-radius: 6px; font-weight: 600; font-size: 16px;">View Your Analysis</a>
        </div>
        <p style="color: #666; font-size: 13px;">This link expires on {expires_at.strftime("%B %d, %Y at %I:%M %p UTC")}.</p>
    </div>
</body>
</html>"""

    text_body = (
        f"Your VoC analysis for {company_name} is ready.\n\n"
        f"Click here to view your analysis:\n{magic_link_url}\n\n"
        f"This link expires on {expires_at.strftime('%B %d, %Y at %I:%M %p UTC')}."
    )

    try:
        import requests as req
        resp = req.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {email_service.api_key}"},
            json={
                "from": email_service.from_email,
                "to": [email],
                "subject": subject,
                "html": html_body,
                "text": text_body,
                "reply_to": email_service.reply_to_email or email_service.from_email,
            },
            timeout=15,
        )
        resp.raise_for_status()
        logger.info("[pipeline %s] Completion email sent to %s", run.run_id, email)
    except Exception as e:
        logger.error("[pipeline %s] Failed to send email to %s: %s", run.run_id, email, e)
        raise
