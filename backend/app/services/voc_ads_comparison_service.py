"""
VOC vs Ads comparison service.
Keyword/phrase overlap: resonance per ad and overlooked VOC themes.
"""
import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Minimum number of theme words that must appear in ad text to count as "hit"
MIN_WORDS_MATCH = 2
# Minimum word length to consider for matching
MIN_WORD_LEN = 2


def _normalize(text: str) -> str:
    """Lowercase and collapse whitespace."""
    if not text:
        return ""
    return " ".join(re.split(r"\s+", (text or "").lower().strip()))


def _words(text: str, min_len: int = MIN_WORD_LEN) -> List[str]:
    """Tokenize into words (letters/numbers), filter by length."""
    if not text:
        return []
    normalized = _normalize(text)
    tokens = re.findall(r"[a-z0-9]+", normalized)
    return [t for t in tokens if len(t) >= min_len]


def _theme_hits_ad(theme_words: List[str], ad_text: str) -> bool:
    """True if at least MIN_WORDS_MATCH theme words appear in ad text."""
    if not theme_words or not ad_text:
        return False
    ad_norm = _normalize(ad_text)
    ad_word_set = set(_words(ad_norm))
    matches = sum(1 for w in theme_words if w in ad_word_set)
    return matches >= min(MIN_WORDS_MATCH, len(theme_words))


def run_comparison(
    voc_summary: Dict[str, Any],
    ads: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Compare VOC themes to ad copy using keyword overlap.

    Args:
        voc_summary: VOC summary dict with categories[].topics[] each having
                     label, verbatim_count, sample_verbatims.
        ads: List of ad dicts with id, primary_text, headline, description
             (description optional).

    Returns:
        {
          "ads": [ { "id", "resonance_score", "resonance_label", "themes_hit", "themes_missed" } ],
          "overlooked_themes": [ { "category", "topic_label", "verbatim_count", "sample_verbatims" } ],
          "total_themes": int,
        }
    """
    # Build flat list of themes: (category, topic_label, verbatim_count, sample_verbatims, theme_key)
    themes: List[Dict[str, Any]] = []
    for cat in voc_summary.get("categories") or []:
        cat_name = (cat.get("name") or "").strip()
        for topic in cat.get("topics") or []:
            label = (topic.get("label") or "").strip()
            if not label:
                continue
            themes.append({
                "category": cat_name,
                "topic_label": label,
                "verbatim_count": topic.get("verbatim_count", 0),
                "sample_verbatims": topic.get("sample_verbatims") or [],
                "theme_key": f"{cat_name}::{label}",
                "theme_words": _words(label),
            })
    total_themes = len(themes)
    if total_themes == 0:
        return {
            "ads": [],
            "overlooked_themes": [],
            "total_themes": 0,
        }

    # For each ad: full text and which themes hit
    results_ads = []
    for ad in ads:
        ad_id = ad.get("id")
        primary = ad.get("primary_text") or ""
        headline = ad.get("headline") or ""
        description = ad.get("description") or ""
        ad_text = _normalize(f"{primary} {headline} {description}")
        themes_hit = []
        themes_missed = []
        for t in themes:
            if _theme_hits_ad(t["theme_words"], ad_text):
                themes_hit.append(t["theme_key"])
            else:
                themes_missed.append(t["theme_key"])
        score = len(themes_hit) / total_themes if total_themes else 0
        if score < 1 / 3:
            label = "low"
        elif score < 2 / 3:
            label = "medium"
        else:
            label = "high"
        results_ads.append({
            "id": str(ad_id) if ad_id is not None else None,
            "resonance_score": round(score, 4),
            "resonance_label": label,
            "themes_hit": themes_hit,
            "themes_missed": themes_missed,
            "headline": headline[:200] if headline else None,
            "primary_text": primary,
            "description": description,
        })

    # Overlooked = themes that no ad hit
    hit_by_any = set()
    for r in results_ads:
        hit_by_any.update(r["themes_hit"])
    overlooked = [
        {
            "category": t["category"],
            "topic_label": t["topic_label"],
            "verbatim_count": t["verbatim_count"],
            "sample_verbatims": t["sample_verbatims"],
        }
        for t in themes
        if t["theme_key"] not in hit_by_any
    ]

    return {
        "ads": results_ads,
        "overlooked_themes": overlooked,
        "total_themes": total_themes,
    }
