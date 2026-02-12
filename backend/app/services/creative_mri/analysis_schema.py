"""
Creative LLM analysis schema (creative-llm-analysis.bundle).
Taxonomy and structure for stable outputs used by D3 charts.
Schema version 1.0.0.
"""

SCHEMA_VERSION = "1.0.0"

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
        "proof_types": PROOF_TYPES,
        "objection_types": OBJECTION_TYPES,
        "offer_types": OFFER_TYPES,
        "cta_types": CTA_TYPES,
        "destination_types": DESTINATION_TYPES,
    }
