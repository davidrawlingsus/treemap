"""
Creative MRI v2: Batch synthesis (LLM Pass 2).
Takes all per-ad classifications from Pass 1 and produces:
- 13 dimension scores (0-100) with human-readable findings
- Overall score (weighted composite)
- Bottom-3 and top-3 dimensions with outreach-ready findings
- Close pattern variety analysis
- Executive narrative

This is NOT optional — it's core to the pipeline.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

try:
    import json_repair
except ImportError:
    json_repair = None

from app.services.creative_mri.analysis_schema import (
    DIMENSION_LABELS,
    DIMENSION_NAMES,
    DIMENSION_WEIGHTS,
)

logger = logging.getLogger(__name__)

PROMPT_PURPOSE = "ad_creative_mri_synthesized_summary"

# ─── Batch synthesis system prompt ────────────────────────────────────────────

_DIMENSION_WEIGHT_LINES = "\n".join(
    f"  - {DIMENSION_LABELS.get(name, name)}: {int(weight * 100)}% — "
    + {
        "specificity_score": "Vague copy is the #1 underperformance driver",
        "claim_to_proof_ratio": "Unsupported claims erode trust",
        "proof_specificity": "Vague proof is almost worse than no proof",
        "belief_count": "Multiple arguments dilute the message",
        "close_anti_patterns": "Bad closes actively repel prospects",
        "pain_benefit_balance": "Pain-first copy outperforms benefit-first",
        "reading_level": "Complex copy loses the scroll",
        "emotional_dimensionality": "Mind movies drive action",
        "qualifier_density": "Hedging undermines authority",
        "social_context_density": "Social context boosts relatability",
        "product_timing": "Early brand mentions signal pitch, not value",
        "conversational_markers": "Natural tone builds trust",
        "close_pattern_variety": "Same close across all ads = diminishing returns",
    }.get(name, "")
    for name, weight in sorted(DIMENSION_WEIGHTS.items(), key=lambda x: -x[1])
)

BATCH_SYNTHESIS_SYSTEM_PROMPT = f"""You are a direct-response copywriting strategist. You receive structured classifications of a brand's Facebook ad library (one JSON object per ad) and produce a batch-level synthesis.

Your job is to score the ad library across 13 direct-response dimensions, identify the worst and best dimensions, and generate specific, quantified findings that make the reader feel money is being left on the table. These findings will be used in automated sales outreach — they must be specific to THIS brand's ads, not generic copywriting advice.

## The 13 Dimensions (with weights)

{_DIMENSION_WEIGHT_LINES}

## Scoring Guidance

Score each dimension 0-100. What each score means:

- **Reading Level**: 100 = 3rd-5th grade (ideal for Facebook). 50 = 8th grade. 0 = college-level. Use the flesch_kincaid_grade from the per-ad data.
- **Claim-to-Proof Ratio**: 100 = every claim backed by proof. 50 = half backed. 0 = all claims, no proof.
- **Proof Specificity**: 100 = every proof element has named sources, numbers, and timelines. 0 = all proof is vague ("studies show", "experts agree").
- **Belief Count**: 100 = every ad makes exactly 1 focused argument. 50 = 2 arguments on average. 0 = 4+ competing arguments.
- **Product Timing**: 100 = brand appears in the final third (earns attention first). 50 = appears in the middle. 0 = leads with the brand name.
- **Specificity Score**: 100 = all concrete specifics, no vague words. 50 = even mix. 0 = dominated by "affordable", "quality", "effective".
- **Close Pattern Variety**: 100 = uses many different close patterns across ads. 50 = 2-3 patterns. 0 = every ad uses the same close.
- **Close Anti-Patterns**: 100 = zero banned close patterns. 50 = occasional. 0 = majority of ads use anti-patterns.
- **Qualifier Density**: 100 = zero hedging words. 50 = moderate hedging. 0 = heavy hedging (8+ per 100 words).
- **Social Context Density**: 100 = rich social references throughout. 50 = occasional. 0 = zero social context.
- **Emotional Dimensionality**: 100 = vivid sensory scenes throughout. 50 = some scene-setting. 0 = entirely abstract/generic.
- **Conversational Markers**: 100 = natural friend-voice throughout. 50 = some conversational elements. 0 = reads like a corporate brochure.
- **Pain/Benefit Balance**: 100 = ideal ~60% pain / 30% benefit / 10% neutral. 50 = moderate imbalance. 0 = extreme imbalance (all pain or all benefit).

## Overall Score

Compute the overall score as the weighted average of all 13 dimensions using the weights above. Round to nearest integer.

## Finding Quality Requirements

Each finding MUST:
1. Reference specific numbers from the actual ad data ("11 claims", "2 proofs", "grade 9.2")
2. Be 1-2 sentences maximum
3. Sound like it came from a copywriting expert who read every ad, not a generic rubric
4. Make the reader feel a specific cost — what they're losing, missing, or wasting
5. Never use generic phrases like "consider improving" or "there's room for growth"

## Output JSON Schema

Return a single JSON object, no markdown:

{{
  "dimensions": {{
    "reading_level": {{
      "score": 35,
      "finding": "Your ads average a 9.2 grade reading level on the Flesch-Kincaid scale. The sweet spot for Facebook is 3rd-5th grade. You're losing every reader who isn't willing to concentrate."
    }},
    "claim_to_proof_ratio": {{
      "score": 22,
      "finding": "..."
    }},
    "proof_specificity": {{ "score": 0, "finding": "..." }},
    "belief_count": {{ "score": 0, "finding": "..." }},
    "product_timing": {{ "score": 0, "finding": "..." }},
    "specificity_score": {{ "score": 0, "finding": "..." }},
    "close_pattern_variety": {{ "score": 0, "finding": "..." }},
    "close_anti_patterns": {{ "score": 0, "finding": "..." }},
    "qualifier_density": {{ "score": 0, "finding": "..." }},
    "social_context_density": {{ "score": 0, "finding": "..." }},
    "emotional_dimensionality": {{ "score": 0, "finding": "..." }},
    "conversational_markers": {{ "score": 0, "finding": "..." }},
    "pain_benefit_balance": {{ "score": 0, "finding": "..." }}
  }},
  "overall_score": 38,
  "bottom_3": [
    {{
      "dimension": "proof_specificity",
      "score": 18,
      "finding": "Every piece of evidence in your ads is generic. Not one named source, not one specific number, not one timeline. Generic proof is invisible proof."
    }}
  ],
  "top_3": [
    {{
      "dimension": "conversational_markers",
      "score": 78,
      "finding": "Your tone is genuinely conversational. This is a real strength — most brands sound like brochures."
    }}
  ],
  "close_pattern_variety": {{
    "patterns_used": ["direct_ask", "direct_ask", "direct_ask"],
    "distinct_count": 1,
    "finding": "Every one of your last 8 ads ends the same way. You're training your audience to ignore your close."
  }},
  "executive_narrative": "Short 2-3 sentence overall diagnosis that captures the single biggest opportunity."
}}"""


# ─── Prompt Engineering lookup ────────────────────────────────────────────────


def get_synthesized_summary_prompt(db: Session) -> Optional[tuple]:
    """Fetch prompt from Prompt Engineering. Returns (system_message, model) or None."""
    from sqlalchemy import func
    from app.models import Prompt

    purpose_lower = PROMPT_PURPOSE.lower()
    prompt = (
        db.query(Prompt)
        .filter(
            func.lower(Prompt.prompt_purpose) == purpose_lower,
            Prompt.status == "live",
        )
        .order_by(Prompt.version.desc())
        .first()
    )
    content = (prompt and (prompt.system_message or prompt.prompt_message)) or None
    if not content:
        return None
    model = prompt.llm_model or "claude-3-5-sonnet-20241022"
    return content, model


# ─── Payload builder ──────────────────────────────────────────────────────────


def build_synthesize_payload(ads: List[Dict[str, Any]]) -> str:
    """Build JSON payload for batch synthesis LLM (user message).
    Takes the list of ads with their LLM Pass 1 classifications.
    Trims sentence text to keep payload within token limits.
    """
    per_ad_data = []
    for ad in ads:
        llm = ad.get("llm")
        if not llm:
            continue
        # Include classification summary (not full sentence text) to stay within token limits
        sentences = llm.get("sentences") or []
        sentence_summary = {
            "total": len(sentences),
            "by_type": {},
        }
        for s in sentences:
            t = s.get("type", "neutral")
            sentence_summary["by_type"][t] = sentence_summary["by_type"].get(t, 0) + 1

        # Count proof specificity signals
        proof_sentences = [s for s in sentences if s.get("type") == "proof" and s.get("proof_detail")]
        proof_specificity = {
            "total_proofs": len(proof_sentences),
            "with_number": sum(1 for s in proof_sentences if s["proof_detail"].get("has_number")),
            "with_named_source": sum(1 for s in proof_sentences if s["proof_detail"].get("has_named_source")),
            "with_timeline": sum(1 for s in proof_sentences if s["proof_detail"].get("has_timeline")),
            "types": [s["proof_detail"].get("proof_type") for s in proof_sentences],
        }

        per_ad_data.append({
            "ad_id": ad.get("id"),
            "headline": (ad.get("headline") or "")[:100],
            "primary_text_preview": (ad.get("primary_text") or "")[:200],
            "word_count": ad.get("word_count", 0),
            "sentence_summary": sentence_summary,
            "proof_specificity": proof_specificity,
            "belief_clusters": len(llm.get("belief_clusters") or []),
            "close_pattern": llm.get("close_pattern"),
            "close_anti_patterns": llm.get("close_anti_patterns") or [],
            "product_timing": llm.get("product_timing"),
            "specificity": llm.get("specificity"),
            "qualifier_density": llm.get("qualifier_density"),
            "social_context_refs_count": len(llm.get("social_context_refs") or []),
            "emotional_scenes_count": len(llm.get("emotional_scenes") or []),
            "conversational_markers": llm.get("conversational_markers"),
            "pain_benefit_balance": llm.get("pain_benefit_balance"),
            "hook_type": llm.get("hook_type"),
            "funnel_stage": llm.get("funnel_stage"),
            "flesch_kincaid": llm.get("flesch_kincaid"),
        })

    payload = {"ads": per_ad_data, "total_ads": len(per_ad_data)}
    return json.dumps(payload, ensure_ascii=False, default=str)


# ─── Response parsing ─────────────────────────────────────────────────────────


def _validate_synthesis(out: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize batch synthesis output."""
    # Ensure dimensions dict exists with all 13
    dims = out.get("dimensions")
    if not isinstance(dims, dict):
        dims = {}

    clean_dims = {}
    for name in DIMENSION_NAMES:
        d = dims.get(name)
        if isinstance(d, dict):
            score = d.get("score")
            try:
                score = max(0, min(100, int(float(score))))
            except (TypeError, ValueError):
                score = 50
            clean_dims[name] = {
                "score": score,
                "finding": str(d.get("finding") or "")[:500] or None,
            }
        else:
            clean_dims[name] = {"score": 50, "finding": None}
    out["dimensions"] = clean_dims

    # Overall score
    overall = out.get("overall_score")
    try:
        out["overall_score"] = max(0, min(100, int(float(overall))))
    except (TypeError, ValueError):
        # Compute from dimensions using weights
        weighted = sum(
            clean_dims[name]["score"] * DIMENSION_WEIGHTS.get(name, 0)
            for name in DIMENSION_NAMES
        )
        out["overall_score"] = max(0, min(100, round(weighted)))

    # Bottom 3 and top 3
    for key in ("bottom_3", "top_3"):
        items = out.get(key)
        if not isinstance(items, list):
            items = []
        clean = []
        for item in items[:3]:
            if not isinstance(item, dict):
                continue
            dim = (item.get("dimension") or "").lower().strip()
            score = item.get("score")
            try:
                score = max(0, min(100, int(float(score))))
            except (TypeError, ValueError):
                score = 50
            clean.append({
                "dimension": dim,
                "score": score,
                "finding": str(item.get("finding") or "")[:500] or None,
            })
        out[key] = clean

    # Close pattern variety
    cpv = out.get("close_pattern_variety")
    if isinstance(cpv, dict):
        out["close_pattern_variety"] = {
            "patterns_used": list(cpv.get("patterns_used") or [])[:50],
            "distinct_count": int(cpv.get("distinct_count") or 0),
            "finding": str(cpv.get("finding") or "")[:500] or None,
        }
    else:
        out["close_pattern_variety"] = {"patterns_used": [], "distinct_count": 0, "finding": None}

    # Executive narrative
    out["executive_narrative"] = str(out.get("executive_narrative") or "")[:1000] or None

    return out


def parse_synthesis_response(content: str) -> Optional[Dict[str, Any]]:
    """Parse batch synthesis LLM response."""
    if not (content or "").strip():
        return None
    text = content.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    try:
        out = json.loads(text)
    except json.JSONDecodeError:
        if json_repair:
            try:
                out = json_repair.loads(text)
            except Exception as e:
                logger.warning("Batch synthesis JSON parse + repair failed: %s", e)
                return None
        else:
            return None
    if isinstance(out, dict):
        return _validate_synthesis(out)
    return None


# ─── Main entry point ─────────────────────────────────────────────────────────


def run_batch_synthesis(
    ads: List[Dict[str, Any]],
    llm_service: Any,
    db: Optional[Session] = None,
) -> Optional[Dict[str, Any]]:
    """
    Run LLM Pass 2: batch synthesis over all per-ad classifications.
    Returns validated synthesis dict or None on failure.
    """
    # Try Prompt Engineering first, fall back to built-in prompt
    system_message = None
    model = "claude-3-5-sonnet-20241022"
    if db:
        try:
            prompt_tuple = get_synthesized_summary_prompt(db)
            if prompt_tuple:
                system_message, model = prompt_tuple
                logger.info("Batch synthesis using Prompt Engineering prompt, model=%s", model)
        except Exception as e:
            logger.warning("Prompt Engineering lookup failed (using built-in): %s", e)

    if not system_message:
        system_message = BATCH_SYNTHESIS_SYSTEM_PROMPT
        logger.info("Batch synthesis using built-in prompt")

    user_message = build_synthesize_payload(ads)
    logger.warning("[MRI-SYNTH] === BATCH SYNTHESIS START === ads=%d, payload=%d chars, sys_prompt=%d chars, model=%s, llm_service=%s",
                   len(ads), len(user_message), len(system_message), model, type(llm_service).__name__)

    import time as _time
    t0 = _time.time()
    try:
        logger.warning("[MRI-SYNTH] Calling llm_service.execute_prompt...")
        result = llm_service.execute_prompt(
            system_message=system_message,
            user_message=user_message,
            model=model,
            max_tokens=16384,
        )
        elapsed = _time.time() - t0
        logger.warning("[MRI-SYNTH] LLM returned in %.1fs. Result type=%s, keys=%s",
                       elapsed, type(result).__name__, list((result or {}).keys()))
        content = (result or {}).get("content") or ""
        logger.warning("[MRI-SYNTH] Content length=%d, first 300 chars: %s", len(content), content[:300])
        if not content.strip():
            logger.warning("[MRI-SYNTH] EMPTY CONTENT from LLM. Full result: %s", str(result)[:500])
            return None
        parsed = parse_synthesis_response(content)
        if parsed is None:
            logger.warning("[MRI-SYNTH] PARSE FAILED. First 1000 chars: %s", content[:1000])
        else:
            logger.warning("[MRI-SYNTH] === SUCCESS === overall_score=%s, bottom_3=%d, top_3=%d",
                           parsed.get("overall_score"), len(parsed.get("bottom_3", [])), len(parsed.get("top_3", [])))
        return parsed
    except Exception as e:
        elapsed = _time.time() - t0
        logger.exception("[MRI-SYNTH] === EXCEPTION after %.1fs === %s: %s", elapsed, type(e).__name__, e)
        return None
