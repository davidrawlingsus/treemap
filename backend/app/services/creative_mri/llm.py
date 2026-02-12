"""
Creative MRI: Claude API per-ad for creative-llm-analysis.bundle schema.
Full schema output for D3 charts: hook scores, cta_type, destination_type.
Prompts are loaded from Prompt Engineering (prompt_purpose=ad_creative_mri) when available;
otherwise falls back to built-in CREATIVE_MRI_SYSTEM_PROMPT.
"""
import json
import logging
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.services.creative_mri.analysis_schema import CTA_TYPES, DESTINATION_TYPES

logger = logging.getLogger(__name__)

_CTA_LIST = ", ".join(CTA_TYPES)
_DEST_LIST = ", ".join(DESTINATION_TYPES)

CREATIVE_MRI_SYSTEM_PROMPT = f"""You are a marketing copy analyst. You analyze ad creative (headline + body + CTA + destination_url, and when provided, video analysis) for copy-based effectiveness only. You do NOT predict performance (ROAS, CTR, CPA). All outputs are "copy-based effectiveness diagnostics."

The input may include an optional "video_analysis" object with: transcript, visual_scenes, on_screen_text, proof_shown_visually, emotional_cues. Use this to inform proof detection and what's shown vs claimed in the video.

Given one Meta ad (headline, primary_text, cta, destination_url, and optionally video_analysis), output a single JSON object with no markdown or explanation outside the JSON. Use only the keys listed; use null for missing or inapplicable values. Be concise.

Hook types: direct_benefit, pain_agitation, authority, social_proof, ranking, newness, contrarian, identity, instructional, urgency_scarcity, story, offer_led, question, curiosity_gap, comparison, mechanism_tease, unknown.
CTA types (use for cta_type): {_CTA_LIST}
Destination types (use for destination_type, infer from URL path): {_DEST_LIST}

Output JSON schema (use exactly these keys):
{{
  "hook_type": "string from hook types",
  "hook_phrase": "exact quote from the ad that best represents the hook, or null",
  "secondary_hook": "optional second hook type if present, else null",
  "angle": "short human-readable messaging angle in 3–8 words, or null",
  "funnel_stage": "tofu | mofu | bofu",
  "stage_rationale": ["1-3 short bullet reasons for funnel stage"],
  "proof_claimed": [{{"type": "proof type e.g. clinical_study", "strength_0_1": 0.8, "text_evidence": "brief quote"}}],
  "proof_shown": [{{"type": "proof type", "strength_0_1": 0.5, "text_evidence": "what is shown"}}],
  "proof_gap": [{{"proof_type": "string", "severity": "low|medium|high", "reason": "brief"}}],
  "objections_addressed": [{{"type": "e.g. price", "coverage_strength_0_1": 0.7, "how_addressed": "explicit_claim or proof or guarantee etc", "text_evidence": "quote"}}],
  "objections_unaddressed": [{{"type": "string", "importance": "low|medium|high"}}],
  "offer_present": true|false,
  "offer_types": [{{"type": "e.g. percent_off", "weight": 0.8}}],
  "hook_scores": {{
    "clarity": 0-100,
    "specificity": 0-100,
    "novelty": 0-100,
    "emotional_pull": 0-100,
    "pattern_interrupt": 0-100,
    "audience_specificity": 0-100,
    "credibility": 0-100,
    "overall": 0-100
  }},
  "cta_type": "string from CTA types list or null",
  "destination_type": "string from destination types list or null",
  "unsupported_claims": ["claim phrases with no proof nearby"],
  "what_to_change": ["1–3 concrete copy edits"]
}}"""

DEFAULT_MODEL = "claude-3-5-sonnet-20241022"


def get_creative_mri_prompts(db: Session) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch Creative MRI system prompt + linked helper from Prompt Engineering.
    Returns (combined_system_message, model) or (None, None) if not configured.
    Use prompt_purpose "ad_creative_mri" on the Ad Creative MRI system prompt.
    """
    from app.models import Prompt, PromptHelperPrompt

    prompt = (
        db.query(Prompt)
        .filter(
            Prompt.prompt_purpose == "ad_creative_mri",
            Prompt.status == "live",
            Prompt.prompt_type == "system",
        )
        .order_by(Prompt.version.desc())
        .first()
    )
    if not prompt or not prompt.system_message:
        return None, None

    parts = [prompt.system_message]
    helper_links = db.query(PromptHelperPrompt).filter(
        PromptHelperPrompt.system_prompt_id == prompt.id
    ).all()
    for link in helper_links:
        helper = db.query(Prompt).filter(Prompt.id == link.helper_prompt_id).first()
        if helper and helper.prompt_message:
            parts.append(helper.prompt_message)
    combined = "\n\n".join(parts)
    model = prompt.llm_model or DEFAULT_MODEL
    return combined, model

VALID_HOOK_TYPES = {
    "direct_benefit", "pain_agitation", "authority", "social_proof", "ranking",
    "newness", "contrarian", "identity", "instructional", "urgency_scarcity",
    "story", "offer_led", "question", "curiosity_gap", "comparison",
    "mechanism_tease", "unknown",
}
VALID_CTA_TYPES = set(CTA_TYPES)
VALID_DESTINATION_TYPES = set(DESTINATION_TYPES)


def parse_llm_response(content: str) -> Optional[Dict[str, Any]]:
    """Parse LLM response into Creative MRI JSON; return None on failure."""
    if not (content or "").strip():
        return None
    text = content.strip()
    # Strip markdown code block if present
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    try:
        out = json.loads(text)
        if not isinstance(out, dict):
            return None
        # Normalize hook_type to taxonomy
        if out.get("hook_type") not in VALID_HOOK_TYPES:
            ht = (out.get("hook_type") or "").lower().replace(" ", "_")
            out["hook_type"] = ht if ht in VALID_HOOK_TYPES else "unknown"
        if out.get("secondary_hook") not in VALID_HOOK_TYPES:
            out["secondary_hook"] = None
        if out.get("cta_type") not in VALID_CTA_TYPES:
            out["cta_type"] = None
        if out.get("destination_type") not in VALID_DESTINATION_TYPES:
            out["destination_type"] = None
        # Ensure all 8 hook_scores present; fill missing or invalid with 50
        hs = dict(out.get("hook_scores") or {})
        for k in ("clarity", "specificity", "novelty", "emotional_pull", "pattern_interrupt", "audience_specificity", "credibility", "overall"):
            v = hs.get(k)
            if not isinstance(v, (int, float)):
                hs[k] = 50
            else:
                hs[k] = max(0, min(100, float(v)))
        out["hook_scores"] = hs
        return out
    except json.JSONDecodeError as e:
        logger.warning("Creative MRI LLM response JSON parse failed: %s", e)
        return None


def build_user_message(ad: Dict[str, Any]) -> str:
    """Build user message for Claude: ad copy + optional video analysis."""
    headline = (ad.get("headline") or "").strip()
    primary_text = (ad.get("primary_text") or "").strip()
    cta = (ad.get("cta") or "").strip() or None
    destination_url = (ad.get("destination_url") or "").strip() or None
    payload = {
        "headline": headline or "",
        "primary_text": primary_text[:3000] or "",
        "cta": cta,
        "destination_url": destination_url,
    }
    # Include first video analysis if present (from Gemini)
    video_analysis = None
    for m in (ad.get("media_items") or []):
        if m.get("media_type") == "video" and m.get("video_analysis_json"):
            video_analysis = m["video_analysis_json"]
            break
    if video_analysis:
        payload["video_analysis"] = video_analysis
    return json.dumps(payload, ensure_ascii=False)


def call_creative_mri_llm(
    llm_service: Any,
    ad: Dict[str, Any],
    system_message: Optional[str] = None,
    model: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Call Claude for one ad; return parsed JSON (hook_type, hook_phrase, angle, unsupported_claims, what_to_change).
    Returns None on API or parse failure.
    Uses system_message from Prompt Engineering when provided; else CREATIVE_MRI_SYSTEM_PROMPT.
    """
    sys_msg = system_message or CREATIVE_MRI_SYSTEM_PROMPT
    model_to_use = model or DEFAULT_MODEL
    user_message = build_user_message(ad)
    try:
        result = llm_service.execute_prompt(
            system_message=sys_msg,
            user_message=user_message,
            model=model_to_use,
        )
        content = (result or {}).get("content") or ""
        return parse_llm_response(content)
    except Exception as e:
        logger.warning("Creative MRI LLM call failed for ad %s: %s", ad.get("id"), e)
        return None
