"""
Creative LLM analysis schema (creative-llm-analysis.bundle).
Taxonomy and structure for stable outputs used by D3 charts.
Schema version 2.0.0 — 13 direct-response dimensions.
"""

SCHEMA_VERSION = "2.0.0"

# --- Hook & funnel (kept from v1, still used by charts 5-6) ---

HOOK_TYPES = [
    "direct_benefit",
    "pain_agitation",
    "authority",
    "social_proof",
    "ranking",
    "newness",
    "contrarian",
    "identity",
    "instructional",
    "urgency_scarcity",
    "story",
    "offer_led",
    "question",
    "curiosity_gap",
    "comparison",
    "mechanism_tease",
]

FUNNEL_STAGES = ["tofu", "mofu", "bofu"]

# --- v2: sentence-level classification ---

SENTENCE_TYPES = [
    "claim",
    "proof",
    "pain",
    "benefit",
    "neutral",
    "transition",
]

# --- v2: proof detail types (used in sentence proof_detail) ---

PROOF_DETAIL_TYPES = [
    "testimonial",
    "statistic",
    "case_study",
    "expert",
    "demo",
    "guarantee",
    "social_metrics",
    "before_after",
    "certification",
    "vague_reference",
]

# --- v2: close patterns (per-ad, from LLM Pass 1) ---

CLOSE_PATTERNS = [
    "echo",
    "micro_commitment",
    "reframe",
    "future_state",
    "social_proof",
    "permission",
    "before_you_decide",
    "see_how_it_works",
    "direct_ask",
    "scarcity",
    "none",
]

# --- v2: social context reference types ---

SOCIAL_CONTEXT_TYPES = [
    "other_people",
    "social_situation",
    "status",
    "embarrassment",
    "compliment",
    "comparison_to_peers",
]

# --- v2: emotional scene types ---

EMOTIONAL_SCENE_TYPES = [
    "sensory",
    "scene_setting",
    "present_tense_situation",
    "mind_movie",
    "visceral",
]

# --- v2: 13 direct-response dimensions ---

DIMENSION_NAMES = [
    "reading_level",
    "claim_to_proof_ratio",
    "proof_specificity",
    "belief_count",
    "product_timing",
    "specificity_score",
    "close_pattern_variety",
    "close_anti_patterns",
    "qualifier_density",
    "social_context_density",
    "emotional_dimensionality",
    "conversational_markers",
    "pain_benefit_balance",
]

# Weights for LLM Pass 2 prompt — how heavily each dimension
# should influence the overall score and narrative.
DIMENSION_WEIGHTS = {
    "specificity_score": 0.15,
    "claim_to_proof_ratio": 0.12,
    "proof_specificity": 0.12,
    "belief_count": 0.10,
    "close_anti_patterns": 0.10,
    "pain_benefit_balance": 0.08,
    "reading_level": 0.07,
    "emotional_dimensionality": 0.07,
    "qualifier_density": 0.05,
    "social_context_density": 0.04,
    "product_timing": 0.04,
    "conversational_markers": 0.03,
    "close_pattern_variety": 0.03,
}

# Human-readable labels for frontend display
DIMENSION_LABELS = {
    "reading_level": "Reading Level",
    "claim_to_proof_ratio": "Claim-to-Proof Ratio",
    "proof_specificity": "Proof Specificity",
    "belief_count": "Belief Count",
    "product_timing": "Product Timing",
    "specificity_score": "Specificity",
    "close_pattern_variety": "Close Variety",
    "close_anti_patterns": "Close Anti-Patterns",
    "qualifier_density": "Qualifier Density",
    "social_context_density": "Social Context",
    "emotional_dimensionality": "Emotional Dimensionality",
    "conversational_markers": "Conversational Markers",
    "pain_benefit_balance": "Pain/Benefit Balance",
}

# --- Legacy v1 types (kept for backward compat with old reports) ---

MOFU_JOB_TYPES = ["awareness", "consideration", "intent", "unknown", "not_applicable"]
REPLACE_REFINE_DECISION = ["replace", "refine", "unknown"]
FIRST2S_HOOK_QUALITY = ["strong", "weak", "missing", "unknown"]

PROOF_TYPES = [
    "quantitative_stat",
    "clinical_study",
    "testimonial",
    "ugc",
    "expert_authority",
    "demo_visual",
    "before_after",
    "comparison_chart",
    "press_award",
    "guarantee",
    "social_metrics",
    "ingredient_spec",
    "manufacturing_origin",
    "third_party_certification",
]

OBJECTION_TYPES = [
    "price",
    "trust",
    "efficacy",
    "safety",
    "time_to_results",
    "ease_of_use",
    "taste_smell",
    "side_effects",
    "fit_for_me",
    "shipping_returns",
    "subscription_lock_in",
    "skepticism_science",
    "ethical_sourcing",
    "compatibility",
    "risk_regret",
]

CTA_TYPES = [
    "shop_now",
    "learn_more",
    "sign_up",
    "get_offer",
    "download",
    "watch_more",
    "send_message",
    "apply_now",
    "book_now",
    "start_trial",
    "take_quiz",
]

DESTINATION_TYPES = [
    "pdp",
    "collection",
    "landing_page",
    "quiz",
    "blog_article",
    "home",
    "lead_form",
    "amazon",
    "app_store",
    "unknown",
]

OFFER_TYPES = [
    "percent_off",
    "money_off",
    "bundle_save",
    "bogo",
    "free_shipping",
    "free_gift",
    "trial_sample",
    "subscription_discount",
    "limited_time",
    "limited_quantity",
    "guarantee",
    "price_lock",
    "financing",
]


def build_taxonomy() -> dict:
    """Return taxonomy object for analysis bundle."""
    return {
        "hook_types": HOOK_TYPES,
        "funnel_stages": FUNNEL_STAGES,
        "sentence_types": SENTENCE_TYPES,
        "proof_detail_types": PROOF_DETAIL_TYPES,
        "close_patterns": CLOSE_PATTERNS,
        "social_context_types": SOCIAL_CONTEXT_TYPES,
        "emotional_scene_types": EMOTIONAL_SCENE_TYPES,
        "dimension_names": DIMENSION_NAMES,
        "dimension_weights": DIMENSION_WEIGHTS,
        "dimension_labels": DIMENSION_LABELS,
        # Legacy
        "proof_types": PROOF_TYPES,
        "objection_types": OBJECTION_TYPES,
        "offer_types": OFFER_TYPES,
        "cta_types": CTA_TYPES,
        "destination_types": DESTINATION_TYPES,
    }
