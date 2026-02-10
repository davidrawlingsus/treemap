"""
Creative MRI: Claude API per-ad for hook, angle, unsupported_claims, what_to_change.
Rules remain source of truth for scores; LLM supplements display fields.
"""
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

CREATIVE_MRI_SYSTEM_PROMPT = """You are a marketing copy analyst. You analyze ad creative (headline + body + CTA) for copy-based effectiveness only. You do NOT predict performance (ROAS, CTR, CPA). All outputs are "copy-based effectiveness diagnostics."

Given one Meta ad (headline, primary_text, cta), output a single JSON object with no markdown or explanation outside the JSON. Use only the keys listed; use null for missing or inapplicable values. Be concise.

Output JSON schema (use exactly these keys):
{
  "hook_type": "pain" | "result" | "curiosity_gap" | "social_proof" | "contrarian" | "new_mechanism" | "offer_price" | "identity" | "comparison" | "story_opener" | "unknown",
  "hook_phrase": "exact quote from the ad that best represents the hook (first line or opening sentence), or null",
  "secondary_hook": "optional second hook type if present, else null",
  "angle": "short human-readable messaging angle in 3–8 words, e.g. 'Pain relief + collagen benefits', or null",
  "unsupported_claims": ["list of specific claim phrases in the ad that have no supporting proof nearby (quote briefly)"],
  "what_to_change": ["1–3 concrete copy edits. Each item: one short sentence describing the edit and where (e.g. 'Add a proof phrase after the claim about results') or suggested wording"]
}"""

VALID_HOOK_TYPES = {
    "pain", "result", "curiosity_gap", "social_proof", "contrarian",
    "new_mechanism", "offer_price", "identity", "comparison", "story_opener", "unknown",
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
        # Normalize hook_type
        if out.get("hook_type") not in VALID_HOOK_TYPES:
            out["hook_type"] = "unknown"
        if out.get("secondary_hook") not in VALID_HOOK_TYPES:
            out["secondary_hook"] = None
        return out
    except json.JSONDecodeError as e:
        logger.warning("Creative MRI LLM response JSON parse failed: %s", e)
        return None


def build_user_message(ad: Dict[str, Any]) -> str:
    """Build user message for Claude: ad headline, primary_text, cta."""
    headline = (ad.get("headline") or "").strip()
    primary_text = (ad.get("primary_text") or "").strip()
    cta = (ad.get("cta") or "").strip() or None
    payload = {
        "headline": headline or "",
        "primary_text": primary_text[:3000] or "",  # cap length
        "cta": cta,
    }
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
