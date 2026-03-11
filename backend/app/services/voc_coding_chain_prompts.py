"""
Prompt and schema constants for the Trustpilot VoC coding chain.
"""

CREATIVE_LANES = [
    "Surprise",
    "Story",
    "Curiosity",
    "Guidance",
    "Instructional",
    "Hyperbole",
    "Newness",
    "Ranking",
]

EMAIL_OBJECTIONS = [
    "price_sensitivity",
    "urgency",
    "product_fit",
    "comparison_paralysis",
    "buyers_remorse",
    "distraction",
    "none",
]

SENTIMENT_VALUES = ["positive", "negative", "mixed"]
EMOTIONAL_INTENSITY_VALUES = ["low", "medium", "high"]


DISCOVER_SYSTEM_PROMPT = """
You are a qualitative VoC (Voice of Customer) researcher specializing in customer insight extraction for direct-response advertising.
Read customer reviews and produce a practical codebook in customer language for ads and emails.

Rules:
- Use customer-language labels, not jargon.
- Keep negative themes; they are useful for objection handling.
- Group into 4-7 categories and ~8-15 themes when possible.
- Include exact review quotes in example_verbatims.
""".strip()


DISCOVER_USER_PROMPT = """
PRODUCT CONTEXT:
{product_context}

---

CUSTOMER REVIEWS ({review_count} total):
{reviews}

---

TASK:
Build the initial VoC codebook.
""".strip()


CODE_SYSTEM_PROMPT = """
You are a content coder. Code each review against the given codebook.

Rules:
- Return every review in output.
- Assign 1-3 topics per review when possible.
- If a review does not fit any existing codebook theme, mark status as NO_MATCH.
- Headlines must be verbatim from review text.
""".strip()


CODE_USER_PROMPT = """
CODEBOOK:
{codebook}

---

REVIEWS TO CODE:
{reviews}
""".strip()


REFINE_SYSTEM_PROMPT = """
You are a senior qualitative researcher refining a VoC codebook.
Produce a complete updated codebook (not recommendations) from:
- current codebook
- coding stats
- no-match reviews

Use conservative edits that materially improve coding quality.
""".strip()


REFINE_USER_PROMPT = """
PRODUCT CONTEXT:
{product_context}

---

CURRENT CODEBOOK:
{codebook}

---

CODING STATS:
{stats}

---

NO_MATCH REVIEWS:
{no_matches}
""".strip()


_THEME_PROPERTIES = {
    "label": {"type": "string"},
    "code": {"type": "string"},
    "description": {"type": "string"},
    "sentiment_direction": {"type": "string", "enum": SENTIMENT_VALUES},
    "emotional_dimension": {"type": "string"},
    "primary_creative_lane": {"type": "string", "enum": CREATIVE_LANES},
    "secondary_creative_lane": {"type": ["string", "null"], "enum": CREATIVE_LANES + [None]},
    "primary_email_objection": {"type": "string", "enum": EMAIL_OBJECTIONS},
    "example_verbatims": {"type": "array", "items": {"type": "string"}},
    "review_count": {"type": "integer"},
    "confidence": {"type": "number"},
}

_THEME_REQUIRED = [
    "label",
    "code",
    "description",
    "sentiment_direction",
    "emotional_dimension",
    "primary_creative_lane",
    "primary_email_objection",
    "example_verbatims",
    "review_count",
    "confidence",
]


DISCOVER_SCHEMA = {
    "type": "object",
    "properties": {
        "codebook_version": {"type": "string"},
        "review_count_analyzed": {"type": "integer"},
        "categories": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "category_code": {"type": "string"},
                    "themes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": _THEME_PROPERTIES,
                            "required": _THEME_REQUIRED,
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["category", "category_code", "themes"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["codebook_version", "review_count_analyzed", "categories"],
    "additionalProperties": False,
}


CODE_SCHEMA = {
    "type": "object",
    "properties": {
        "coded_reviews": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "respondent_id": {"type": "string"},
                    "overall_sentiment": {"type": "string", "enum": SENTIMENT_VALUES},
                    "emotional_intensity": {"type": "string", "enum": EMOTIONAL_INTENSITY_VALUES},
                    "status": {"type": "string", "enum": ["CODED", "NO_MATCH"]},
                    "topics": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "category": {"type": "string"},
                                "label": {"type": "string"},
                                "code": {"type": "string"},
                                "sentiment": {"type": "string", "enum": SENTIMENT_VALUES},
                                "headline": {"type": "string"},
                                "emotional_intensity": {"type": "string", "enum": EMOTIONAL_INTENSITY_VALUES},
                                "confidence": {"type": "number"},
                            },
                            "required": [
                                "category",
                                "label",
                                "code",
                                "sentiment",
                                "headline",
                                "emotional_intensity",
                                "confidence",
                            ],
                            "additionalProperties": False,
                        },
                    },
                    "no_match_reason": {"type": ["string", "null"]},
                },
                "required": [
                    "respondent_id",
                    "overall_sentiment",
                    "emotional_intensity",
                    "status",
                    "topics",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["coded_reviews"],
    "additionalProperties": False,
}


REFINE_SCHEMA = {
    "type": "object",
    "properties": {
        "codebook_version": {"type": "string"},
        "refined_from": {"type": "string"},
        "review_count_analyzed": {"type": "integer"},
        "health_assessment": {"type": "object"},
        "categories": DISCOVER_SCHEMA["properties"]["categories"],
        "changelog": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["MERGE", "SPLIT", "ADD", "RENAME", "REMAP", "SUNSET", "NO_CHANGE"],
                    },
                    "target_codes": {"type": "array", "items": {"type": "string"}},
                    "result_code": {"type": ["string", "null"]},
                    "rationale": {"type": "string"},
                },
                "required": ["action", "target_codes", "rationale"],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "codebook_version",
        "refined_from",
        "review_count_analyzed",
        "health_assessment",
        "categories",
        "changelog",
    ],
    "additionalProperties": False,
}

