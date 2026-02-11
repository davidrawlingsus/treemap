"""
Creative MRI: Claude API per-ad for hook, angle, unsupported_claims, what_to_change.
Rules remain source of truth for scores; LLM supplements display fields.
"""
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

CREATIVE_MRI_SYSTEM_PROMPT = """You are a marketing copy analyst. You analyze ad creative (headline + body + CTA, and when provided, video analysis) for copy-based effectiveness only. You do NOT predict performance (ROAS, CTR, CPA). All outputs are "copy-based effectiveness diagnostics."

The input may include an optional "video_analysis" object with: transcript, visual_scenes, on_screen_text, proof_shown_visually, emotional_cues. Use this to inform proof detection and what's shown vs claimed in the video.

Given one Meta ad (headline, primary_text, cta, and optionally video_analysis), output a single JSON object with no markdown or explanation outside the JSON. Use only the keys listed; use null for missing or inapplicable values. Be concise.

Output JSON schema (use exactly these keys). For hook_type use one of: direct_benefit, pain_agitation, authority, social_proof, ranking, newness, contrarian, identity, instructional, urgency_scarcity, story, offer_led, question, curiosity_gap, comparison, mechanism_tease, unknown.
For funnel_stage use: tofu, mofu, bofu.
{
  "hook_type": "string from hook_types list above",
  "hook_phrase": "exact quote from the ad that best represents the hook, or null",
  "secondary_hook": "optional second hook type if present, else null",
  "angle": "short human-readable messaging angle in 3–8 words, or null",
  "funnel_stage": "tofu | mofu | bofu",
  "stage_rationale": ["1-3 short bullet reasons for funnel stage"],
  "proof_claimed": [{"type": "proof type e.g. clinical_study", "strength_0_1": 0.8, "text_evidence": "brief quote"}],
  "proof_shown": [{"type": "proof type", "strength_0_1": 0.5, "text_evidence": "what is shown"}],
  "proof_gap": [{"proof_type": "string", "severity": "low|medium|high", "reason": "brief"}],
  "objections_addressed": [{"type": "e.g. price", "coverage_strength_0_1": 0.7, "how_addressed": "explicit_claim or proof or guarantee etc", "text_evidence": "quote"}],
  "objections_unaddressed": [{"type": "string", "importance": "low|medium|high"}],
  "offer_present": true|false,
  "offer_types": [{"type": "e.g. percent_off", "weight": 0.8}],
  "hook_scores": {"clarity": 0-100, "specificity": 0-100, "novelty": 0-100, "emotional_pull": 0-100, "overall": 0-100},
  "unsupported_claims": ["claim phrases with no proof nearby"],
  "what_to_change": ["1–3 concrete copy edits"]
}"""

VALID_HOOK_TYPES = {
    "direct_benefit", "pain_agitation", "authority", "social_proof", "ranking",
    "newness", "contrarian", "identity", "instructional", "urgency_scarcity",
    "story", "offer_led", "question", "curiosity_gap", "comparison",
    "mechanism_tease", "unknown",
}


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
        return out
    except json.JSONDecodeError as e:
        logger.warning("Creative MRI LLM response JSON parse failed: %s", e)
        return None


def build_user_message(ad: Dict[str, Any]) -> str:
    """Build user message for Claude: ad copy + optional video analysis."""
    headline = (ad.get("headline") or "").strip()
    primary_text = (ad.get("primary_text") or "").strip()
    cta = (ad.get("cta") or "").strip() or None
    payload = {
        "headline": headline or "",
        "primary_text": primary_text[:3000] or "",
        "cta": cta,
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
    model: str = "claude-3-5-sonnet-20241022",
) -> Optional[Dict[str, Any]]:
    """
    Call Claude for one ad; return parsed JSON (hook_type, hook_phrase, angle, unsupported_claims, what_to_change).
    Returns None on API or parse failure.
    """
    user_message = build_user_message(ad)
    try:
        result = llm_service.execute_prompt(
            system_message=CREATIVE_MRI_SYSTEM_PROMPT,
            user_message=user_message,
            model=model,
        )
        content = (result or {}).get("content") or ""
        return parse_llm_response(content)
    except Exception as e:
        logger.warning("Creative MRI LLM call failed for ad %s: %s", ad.get("id"), e)
        return None
