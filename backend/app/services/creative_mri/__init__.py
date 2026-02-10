"""
Creative MRI: copy-based effectiveness report pipeline.
Rules + Claude API per-ad; scores and spans from rules, LLM supplements hook/angle/claims/what_to_change.
"""
from app.services.creative_mri.pipeline import run_creative_mri_pipeline

__all__ = ["run_creative_mri_pipeline"]
