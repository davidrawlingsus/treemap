"""
Rule dictionaries for Creative MRI: offer, proof, hook, stage signals.
Used for classification and scoring; LLM supplements hook/angle/claims/what_to_change.
"""
import re
from typing import List, Optional

# Hook type detection order: first match wins
HOOK_PATTERNS = [
    ("pain", re.compile(r"\b(pain|struggle|frustrat|annoy|tired of|sick of|problem|issue|worr(y|ied)|stress|overwhelm)\b", re.I)),
    ("result", re.compile(r"\b(result|transform|get\s+you|achieve|look\s+better|feel\s+better|in\s+\d+\s+days|before\s+and\s+after)\b", re.I)),
    ("curiosity_gap", re.compile(r"\b(secret|discover|reveal|what\s+most|here's\s+what|the\s+one\s+thing)\b", re.I)),
    ("social_proof", re.compile(r"\b(customers?|reviews?|rated|trusted|million|thousands?|join|as\s+told\s+by)\b", re.I)),
    ("contrarian", re.compile(r"\b(actually|myth|wrong|stop\s+doing|don't\s+.*\s+until|forget\s+what)\b", re.I)),
    ("new_mechanism", re.compile(r"\b(patent|formula|ingredient|technology|how\s+it\s+works|mechanism|science)\b", re.I)),
    ("offer_price", re.compile(r"\b(\d+%?\s*off|save\s+\$|free\s+shipping|discount|code\s+\w+|deal|offer|price|£|\$)\b", re.I)),
    ("identity", re.compile(r"\b(for\s+people\s+who|if\s+you\s+are|entrepreneurs?|busy\s+parents?)\b", re.I)),
    ("comparison", re.compile(r"\b(vs\.?|versus|compared\s+to|better\s+than|instead\s+of)\b", re.I)),
    ("story_opener", re.compile(r"\b(I\s+used\s+to|when\s+I|years?\s+ago|story|once\s+upon)\b", re.I)),
]

# Proof type detection
PROOF_PATTERNS = {
    "testimonial": re.compile(r"\b(review|testimonial|customer\s+said|rated\s+\d|stars?)\b", re.I),
    "expert": re.compile(r"\b(doctor|expert|study|research|clinical)\b", re.I),
    "data": re.compile(r"\b(\d+%|\d+x|statistics?|proven)\b", re.I),
    "before_after": re.compile(r"\b(before\s+and\s+after|transformation|results?)\b", re.I),
    "press": re.compile(r"\b(featured\s+in|as\s+seen\s+in|press)\b", re.I),
    "authority_badge": re.compile(r"\b(certified|award|approved)\b", re.I),
    "warranty_guarantee": re.compile(r"\b(guarantee|warranty|money[- ]back)\b", re.I),
}

# Offer elements
OFFER_PATTERNS = re.compile(
    r"\b(\d+%?\s*off|save\s+\$|free\s+shipping|free\s+gift|discount|code\s+[A-Z0-9]+|bundle|%\s+off|limited\s+time|offer|deal|subscribe\s+and\s+save|cancel\s+anytime|money[- ]back|guarantee|warranty)\b",
    re.I,
)

# Funnel stage signals (TOFU / MOFU / BOFU)
STAGE_TOFU = re.compile(r"\b(learn|discover|curiosity|secret|what\s+most)\b", re.I)
STAGE_MOFU = re.compile(r"\b(how\s+it\s+works|see\s+results|review|study|proof)\b", re.I)
STAGE_BOFU = re.compile(r"\b(buy|shop|order|subscribe|get\s+\d+%?\s*off|free\s+shipping|add\s+to\s+cart|limited|guarantee)\b", re.I)


def detect_hook_type(text: str) -> str:
    """Return first matching hook type or 'unknown'."""
    if not (text or "").strip():
        return "unknown"
    sample = (text or "")[:500]
    for name, pat in HOOK_PATTERNS:
        if pat.search(sample):
            return name
    return "unknown"


def detect_proof_types(text: str) -> List[str]:
    """Return list of proof types present in text."""
    if not (text or "").strip():
        return []
    found = []
    for name, pat in PROOF_PATTERNS.items():
        if pat.search(text):
            found.append(name)
    return found


def detect_offer_elements(text: str) -> List[str]:
    """Return list of offer-related phrases found (simplified: single list)."""
    if not (text or "").strip():
        return []
    return list(set(OFFER_PATTERNS.findall(text)))


def detect_funnel_stage(text: str) -> str:
    """Weighted: BOFU > MOFU > TOFU by count of matches; tie-break BOFU > MOFU > TOFU."""
    if not (text or "").strip():
        return "TOFU"
    t = (text or "").lower()
    b = len(STAGE_BOFU.findall(t))
    m = len(STAGE_MOFU.findall(t))
    f = len(STAGE_TOFU.findall(t))
    if b >= m and b >= f:
        return "BOFU"
    if m >= f:
        return "MOFU"
    return "TOFU"
