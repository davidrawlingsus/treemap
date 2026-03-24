"""
Creative MRI v2: Per-ad structured classification (LLM Pass 1).
The LLM classifies ad copy into structured elements — sentence-level tagging,
belief clusters, close patterns, social context, emotional scenes, etc.
No subjective 0-100 scores. Scoring happens in LLM Pass 2 (batch synthesis).
"""
import json
import logging

try:
    import json_repair
except ImportError:
    json_repair = None
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.services.creative_mri.analysis_schema import (
    CLOSE_PATTERNS,
    DIMENSION_NAMES,
    DIMENSION_WEIGHTS,
    EMOTIONAL_SCENE_TYPES,
    HOOK_TYPES,
    PROOF_DETAIL_TYPES,
    SENTENCE_TYPES,
    SOCIAL_CONTEXT_TYPES,
)

logger = logging.getLogger(__name__)

# ─── Per-ad system prompt (LLM Pass 1) ───────────────────────────────────────

_SENTENCE_TYPES_STR = ", ".join(SENTENCE_TYPES)
_PROOF_DETAIL_TYPES_STR = ", ".join(PROOF_DETAIL_TYPES)
_CLOSE_PATTERNS_STR = ", ".join(CLOSE_PATTERNS)
_SOCIAL_CONTEXT_TYPES_STR = ", ".join(SOCIAL_CONTEXT_TYPES)
_EMOTIONAL_SCENE_TYPES_STR = ", ".join(EMOTIONAL_SCENE_TYPES)
_HOOK_TYPES_STR = ", ".join(HOOK_TYPES + ["unknown"])

CREATIVE_MRI_SYSTEM_PROMPT = f"""You are a direct-response copywriting analyst. You classify the structural elements of Facebook ad copy. You do NOT score or rate ads — you classify and extract.

Given one Meta ad (headline, primary_text, cta, destination_url, and optionally video_analysis or image_analyses), output a single JSON object. No markdown, no explanation outside the JSON. Be precise — quote exact text from the ad.

The input includes a pre-computed "flesch_kincaid" object with reading level metrics. Include it as-is in your output.

Output JSON schema (use exactly these keys):

{{
  "sentences": [
    {{
      "text": "exact sentence quoted from the ad",
      "type": "{_SENTENCE_TYPES_STR}",
      "proof_detail": {{
        "has_number": true|false,
        "has_named_source": true|false,
        "has_timeline": true|false,
        "proof_type": "{_PROOF_DETAIL_TYPES_STR}"
      }}
    }}
  ],

  "belief_clusters": [
    {{
      "core_argument": "1 sentence summary of the selling argument",
      "supporting_sentences": [0, 3, 5]
    }}
  ],

  "close_pattern": "{_CLOSE_PATTERNS_STR}",
  "close_text": "exact closing CTA / final sentences from the ad",

  "close_anti_patterns": [
    {{
      "pattern": "description of the anti-pattern (e.g. question answerable with no, generic urgency, motivational poster line)",
      "text": "exact quote from ad"
    }}
  ],

  "product_timing": {{
    "first_mention_word_position": 45,
    "first_mention_pct": 0.62,
    "total_words": 73
  }},

  "specificity": {{
    "vague_terms": ["affordable", "quality", "effective"],
    "concrete_terms": ["£89", "2-day delivery", "847 customers"],
    "vague_count": 3,
    "concrete_count": 3
  }},

  "qualifier_density": {{
    "qualifiers_found": ["may", "could help", "possibly"],
    "count": 3,
    "per_100_words": 4.1
  }},

  "social_context_refs": [
    {{
      "text": "exact quote",
      "type": "{_SOCIAL_CONTEXT_TYPES_STR}"
    }}
  ],

  "emotional_scenes": [
    {{
      "text": "exact quote",
      "type": "{_EMOTIONAL_SCENE_TYPES_STR}"
    }}
  ],

  "conversational_markers": {{
    "markers_found": ["here's the thing", "okay"],
    "count": 2,
    "per_100_words": 2.7
  }},

  "pain_benefit_balance": {{
    "pain_pct": 0.40,
    "benefit_pct": 0.45,
    "neutral_pct": 0.15
  }},

  "hook_type": "{_HOOK_TYPES_STR}",
  "funnel_stage": "tofu | mofu | bofu",

  "flesch_kincaid": {{
    "flesch_kincaid_grade": 8.2,
    "sentence_count": 12,
    "word_count": 95,
    "syllable_count": 140
  }}
}}

Classification rules:
- "sentences": Break the ad into individual sentences/statements. Classify each as claim (assertion about product/benefit with no evidence), proof (evidence, number, testimonial, source), pain (acknowledges reader's problem/frustration), benefit (describes positive outcome), neutral (context, brand name, transition), or transition (connects ideas). Include proof_detail ONLY for sentences typed as "proof" — set to null for all other types.
- "belief_clusters": Group sentences that support the same core selling argument. Most ads should have 1-2 clusters. An ad arguing 3+ distinct points is unfocused. supporting_sentences are indices into the sentences array.
- "close_pattern": Classify the ad's closing approach. echo = restates the hook. micro_commitment = small next step. reframe = shifts perspective. future_state = paints life after purchase. social_proof = others are doing it. permission = gives reader permission to act. before_you_decide = frames as pre-decision info. see_how_it_works = curiosity-driven. direct_ask = straightforward buy/shop. scarcity = limited time/quantity. none = no clear close.
- "close_anti_patterns": Flag banned close phrases: questions answerable with "no" ("Are you ready to...?", "Do you want to...?", "Isn't it time...?"), generic urgency ("Don't miss out", "Act now", "Hurry"), motivational poster lines ("What are you waiting for?", "You won't regret it"), feature dumps in the close. Return empty array if no anti-patterns found.
- "product_timing": Find the first mention of the product or brand name. Report its word position and percentage through the total copy. If the brand is never mentioned, set first_mention_word_position and first_mention_pct to null.
- "specificity": List vague marketing words (affordable, fast, easy, quality, effective, amazing, premium, innovative, cutting-edge, world-class, revolutionary, best, leading, powerful, incredible, simple, great, unique) and concrete specifics (numbers with units, prices, timeframes, named features, named sources).
- "qualifier_density": Count hedging words (could, may, might, perhaps, possibly, sometimes, often, generally, usually, typically, arguably, seemingly, potentially, presumably, can help, designed to, up to, as much as, tends to).
- "social_context_refs": Quote any reference to other people, social situations, peer behaviour, status, embarrassment, compliments, or how the reader appears to others.
- "emotional_scenes": Quote any sensory language, scene-setting, present-tense situational descriptions, or "mind movie" moments where the reader can picture themselves in a specific situation.
- "conversational_markers": Count natural speech inflections: "okay", "here's the thing", "but check this out", "look", "listen", "honestly", "real talk", "spoiler", "plot twist", "wait", "get this", "trust me", "no really", sentence-initial "And"/"But"/"So", em-dashes, ellipsis continuations.
- "pain_benefit_balance": Calculate what percentage of the ad's sentences are pain-oriented, benefit-oriented, and neutral/transition. Percentages should sum to 1.0.
- "flesch_kincaid": Copy the pre-computed flesch_kincaid object from the input into your output unchanged."""

DEFAULT_MODEL = "claude-3-5-sonnet-20241022"

# ─── Prompt Engineering lookup ────────────────────────────────────────────────


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


# ─── Validation sets ──────────────────────────────────────────────────────────

VALID_HOOK_TYPES = set(HOOK_TYPES) | {"unknown"}
VALID_SENTENCE_TYPES = set(SENTENCE_TYPES)
VALID_PROOF_DETAIL_TYPES = set(PROOF_DETAIL_TYPES)
VALID_CLOSE_PATTERNS = set(CLOSE_PATTERNS)
VALID_SOCIAL_CONTEXT_TYPES = set(SOCIAL_CONTEXT_TYPES)
VALID_EMOTIONAL_SCENE_TYPES = set(EMOTIONAL_SCENE_TYPES)

MAX_STRING_LEN = 300  # longer for exact quotes


def _truncate(s: Any, max_len: int = MAX_STRING_LEN) -> Optional[str]:
    if s is None:
        return None
    t = str(s).strip()
    return t[:max_len] if len(t) > max_len else t if t else None


def _clamp_float(v: Any, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return 0.0


def _validate_and_normalize(out: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize parsed LLM Pass 1 output."""

    # --- sentences ---
    sentences = out.get("sentences")
    if not isinstance(sentences, list):
        sentences = []
    clean_sentences = []
    for s in sentences[:50]:  # cap at 50 sentences
        if not isinstance(s, dict):
            continue
        stype = (s.get("type") or "").lower().strip()
        if stype not in VALID_SENTENCE_TYPES:
            stype = "neutral"
        entry = {
            "text": _truncate(s.get("text")),
            "type": stype,
            "proof_detail": None,
        }
        if stype == "proof" and isinstance(s.get("proof_detail"), dict):
            pd = s["proof_detail"]
            pt = (pd.get("proof_type") or "").lower().strip()
            entry["proof_detail"] = {
                "has_number": bool(pd.get("has_number")),
                "has_named_source": bool(pd.get("has_named_source")),
                "has_timeline": bool(pd.get("has_timeline")),
                "proof_type": pt if pt in VALID_PROOF_DETAIL_TYPES else "vague_reference",
            }
        clean_sentences.append(entry)
    out["sentences"] = clean_sentences

    # --- belief_clusters ---
    clusters = out.get("belief_clusters")
    if not isinstance(clusters, list):
        clusters = []
    clean_clusters = []
    for c in clusters[:10]:
        if not isinstance(c, dict):
            continue
        clean_clusters.append({
            "core_argument": _truncate(c.get("core_argument")),
            "supporting_sentences": [
                int(i) for i in (c.get("supporting_sentences") or [])
                if isinstance(i, (int, float)) and 0 <= int(i) < len(clean_sentences)
            ][:20],
        })
    out["belief_clusters"] = clean_clusters

    # --- close_pattern ---
    cp = (out.get("close_pattern") or "").lower().strip()
    out["close_pattern"] = cp if cp in VALID_CLOSE_PATTERNS else "none"
    out["close_text"] = _truncate(out.get("close_text"))

    # --- close_anti_patterns ---
    caps = out.get("close_anti_patterns")
    if not isinstance(caps, list):
        caps = []
    out["close_anti_patterns"] = [
        {"pattern": _truncate(c.get("pattern")), "text": _truncate(c.get("text"))}
        for c in caps[:10] if isinstance(c, dict)
    ]

    # --- product_timing ---
    pt = out.get("product_timing")
    if isinstance(pt, dict):
        out["product_timing"] = {
            "first_mention_word_position": pt.get("first_mention_word_position"),
            "first_mention_pct": _clamp_float(pt.get("first_mention_pct"), 0.0, 1.0) if pt.get("first_mention_pct") is not None else None,
            "total_words": int(pt.get("total_words") or 0),
        }
    else:
        out["product_timing"] = {"first_mention_word_position": None, "first_mention_pct": None, "total_words": 0}

    # --- specificity ---
    sp = out.get("specificity")
    if isinstance(sp, dict):
        out["specificity"] = {
            "vague_terms": [_truncate(t) for t in (sp.get("vague_terms") or [])[:30]],
            "concrete_terms": [_truncate(t) for t in (sp.get("concrete_terms") or [])[:30]],
            "vague_count": int(sp.get("vague_count") or 0),
            "concrete_count": int(sp.get("concrete_count") or 0),
        }
    else:
        out["specificity"] = {"vague_terms": [], "concrete_terms": [], "vague_count": 0, "concrete_count": 0}

    # --- qualifier_density ---
    qd = out.get("qualifier_density")
    if isinstance(qd, dict):
        out["qualifier_density"] = {
            "qualifiers_found": [_truncate(q) for q in (qd.get("qualifiers_found") or [])[:30]],
            "count": int(qd.get("count") or 0),
            "per_100_words": round(_clamp_float(qd.get("per_100_words"), 0.0, 100.0), 1),
        }
    else:
        out["qualifier_density"] = {"qualifiers_found": [], "count": 0, "per_100_words": 0.0}

    # --- social_context_refs ---
    scr = out.get("social_context_refs")
    if not isinstance(scr, list):
        scr = []
    out["social_context_refs"] = [
        {
            "text": _truncate(r.get("text")),
            "type": (r.get("type") or "").lower().strip() if (r.get("type") or "").lower().strip() in VALID_SOCIAL_CONTEXT_TYPES else "other_people",
        }
        for r in scr[:20] if isinstance(r, dict)
    ]

    # --- emotional_scenes ---
    es = out.get("emotional_scenes")
    if not isinstance(es, list):
        es = []
    out["emotional_scenes"] = [
        {
            "text": _truncate(r.get("text")),
            "type": (r.get("type") or "").lower().strip() if (r.get("type") or "").lower().strip() in VALID_EMOTIONAL_SCENE_TYPES else "sensory",
        }
        for r in es[:20] if isinstance(r, dict)
    ]

    # --- conversational_markers ---
    cm = out.get("conversational_markers")
    if isinstance(cm, dict):
        out["conversational_markers"] = {
            "markers_found": [_truncate(m) for m in (cm.get("markers_found") or [])[:30]],
            "count": int(cm.get("count") or 0),
            "per_100_words": round(_clamp_float(cm.get("per_100_words"), 0.0, 100.0), 1),
        }
    else:
        out["conversational_markers"] = {"markers_found": [], "count": 0, "per_100_words": 0.0}

    # --- pain_benefit_balance ---
    pbb = out.get("pain_benefit_balance")
    if isinstance(pbb, dict):
        pain = _clamp_float(pbb.get("pain_pct"))
        benefit = _clamp_float(pbb.get("benefit_pct"))
        neutral = _clamp_float(pbb.get("neutral_pct"))
        total = pain + benefit + neutral
        if total > 0:
            pain, benefit, neutral = pain / total, benefit / total, neutral / total
        else:
            pain, benefit, neutral = 0.33, 0.33, 0.34
        out["pain_benefit_balance"] = {
            "pain_pct": round(pain, 2),
            "benefit_pct": round(benefit, 2),
            "neutral_pct": round(neutral, 2),
        }
    else:
        out["pain_benefit_balance"] = {"pain_pct": 0.33, "benefit_pct": 0.33, "neutral_pct": 0.34}

    # --- hook_type ---
    ht = (out.get("hook_type") or "").lower().replace(" ", "_")
    out["hook_type"] = ht if ht in VALID_HOOK_TYPES else "unknown"

    # --- funnel_stage ---
    fs = (out.get("funnel_stage") or "").lower().strip()
    out["funnel_stage"] = fs if fs in ("tofu", "mofu", "bofu") else "tofu"

    # --- flesch_kincaid (pass-through from input) ---
    fk = out.get("flesch_kincaid")
    if isinstance(fk, dict):
        out["flesch_kincaid"] = {
            "flesch_kincaid_grade": round(float(fk.get("flesch_kincaid_grade") or 0), 1),
            "sentence_count": int(fk.get("sentence_count") or 0),
            "word_count": int(fk.get("word_count") or 0),
            "syllable_count": int(fk.get("syllable_count") or 0),
        }
    else:
        out["flesch_kincaid"] = {"flesch_kincaid_grade": 0.0, "sentence_count": 0, "word_count": 0, "syllable_count": 0}

    return out


# ─── Response parsing ─────────────────────────────────────────────────────────


def parse_llm_response(content: str) -> Optional[Dict[str, Any]]:
    """Parse LLM response into Creative MRI v2 JSON; return None on failure."""
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
        return _validate_and_normalize(out)
    except json.JSONDecodeError as e:
        if json_repair:
            try:
                repaired = json_repair.loads(text)
                if isinstance(repaired, dict):
                    return _validate_and_normalize(repaired)
            except Exception:
                pass
        logger.warning("Creative MRI LLM response JSON parse failed: %s", e)
        return None


# ─── User message builder ────────────────────────────────────────────────────


def build_user_message(ad: Dict[str, Any]) -> str:
    """Build user message for Claude: ad copy + flesch_kincaid + optional media analysis."""
    headline = (ad.get("headline") or "").strip()
    primary_text = (ad.get("primary_text") or "").strip()
    cta = (ad.get("cta") or "").strip() or None
    destination_url = (ad.get("destination_url") or "").strip() or None
    payload: Dict[str, Any] = {
        "headline": headline or "",
        "primary_text": primary_text[:3000] or "",
        "cta": cta,
        "destination_url": destination_url,
    }
    # Pre-computed Flesch-Kincaid from Python
    payload["flesch_kincaid"] = ad.get("flesch_kincaid") or {}
    # Include first video analysis if present (from Gemini)
    video_analysis = None
    image_analyses: List[Any] = []
    for m in (ad.get("media_items") or []):
        if m.get("media_type") == "video" and m.get("video_analysis_json"):
            video_analysis = m["video_analysis_json"]
            break
    if video_analysis:
        payload["video_analysis"] = video_analysis
    for m in (ad.get("media_items") or []):
        if m.get("media_type") == "image" and m.get("image_analysis_json"):
            image_analyses.append(m["image_analysis_json"])
    if image_analyses:
        payload["image_analyses"] = image_analyses
    return json.dumps(payload, ensure_ascii=False)


# ─── LLM call ────────────────────────────────────────────────────────────────


def call_creative_mri_llm(
    llm_service: Any,
    ad: Dict[str, Any],
    system_message: Optional[str] = None,
    model: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Call Claude for one ad (LLM Pass 1); return parsed structured classification.
    Returns None on API or parse failure.
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
