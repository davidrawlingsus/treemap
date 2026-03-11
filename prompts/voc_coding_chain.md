# VoC Coding Prompt Chain

## Overview

3 prompts, 4 steps. Fully automated — no human review between steps. Takes raw Trustpilot reviews and produces coded topics optimized for the 8-lane Facebook ad engine and email sequence generator.

The key insight: Step 3 (REFINE) outputs the **actual updated codebook**, not recommendations. Then Step 4 just re-runs the CODE prompt with the better codebook. Three prompts do the work of four steps.

Uses Claude API with `output_config.json_schema` for **guaranteed** structured output — no preamble, no markdown fencing, no reasoning text leaking into the response. The schema enforces the exact shape of every response.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  RAW REVIEWS + PRODUCT CONTEXT                                          │
│       │                                                                  │
│       ▼                                                                  │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │  STEP 1: DISCOVER                    [Prompt 1]              │       │
│  │  Model: claude-sonnet-4-5 | Temp: 0.6                        │       │
│  │  Input: All reviews (up to 100) + product context            │       │
│  │  Output: Codebook v1 (categories, themes, codes)             │       │
│  └──────────────────────┬───────────────────────────────────────┘       │
│                         │                                                │
│                    CODEBOOK v1                                           │
│                         │                                                │
│                         ▼                                                │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │  STEP 2: CODE (first pass)           [Prompt 2]              │       │
│  │  Model: claude-haiku-4-5 | Temp: 0.2                         │       │
│  │  Input: Batches of 20 reviews + v1 codebook                  │       │
│  │  Output: topics[] per review + NO_MATCH flags + stats        │       │
│  └──────────────────────┬───────────────────────────────────────┘       │
│                         │                                                │
│              CODED REVIEWS + NO_MATCHES + STATS                          │
│                         │                                                │
│                         ▼                                                │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │  STEP 3: REFINE                      [Prompt 3]              │       │
│  │  Model: claude-sonnet-4-5 | Temp: 0.4                        │       │
│  │  Input: v1 codebook + coding stats + NO_MATCH reviews        │       │
│  │  Output: COMPLETE codebook v1.1 (not recommendations —       │       │
│  │          the actual codebook with merges/splits/adds done)   │       │
│  └──────────────────────┬───────────────────────────────────────┘       │
│                         │                                                │
│                    CODEBOOK v1.1 (complete, ready to use)                │
│                         │                                                │
│                         ▼                                                │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │  STEP 4: RE-CODE (final pass)        [Prompt 2 again]        │       │
│  │  Model: claude-haiku-4-5 | Temp: 0.2                         │       │
│  │  Input: ALL reviews + v1.1 codebook                          │       │
│  │  Output: FINAL topics[] per review — ready for ad engine     │       │
│  └──────────────────────┬───────────────────────────────────────┘       │
│                         │                                                │
│                  FINAL CODED REVIEWS                                     │
│                         │                                                │
│            ┌────────────┴────────────┐                                   │
│            ▼                         ▼                                   │
│    AD GENERATION              EMAIL GENERATION                          │
│    (8 creative lanes)        (6 objection types)                        │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## JSON Schemas (for output_config)

These schemas are passed to the Anthropic API via `output_config.format.json_schema.schema`. The API guarantees the response conforms exactly — no preamble, no reasoning text, just the JSON object.

### DISCOVER Schema

```python
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
                            "properties": {
                                "label": {"type": "string"},
                                "code": {"type": "string"},
                                "description": {"type": "string"},
                                "sentiment_direction": {
                                    "type": "string",
                                    "enum": ["positive", "negative", "mixed"]
                                },
                                "emotional_dimension": {"type": "string"},
                                "primary_creative_lane": {
                                    "type": "string",
                                    "enum": ["Surprise", "Story", "Curiosity", "Guidance",
                                             "Instructional", "Hyperbole", "Newness", "Ranking"]
                                },
                                "secondary_creative_lane": {
                                    "type": ["string", "null"],
                                    "enum": ["Surprise", "Story", "Curiosity", "Guidance",
                                             "Instructional", "Hyperbole", "Newness", "Ranking", None]
                                },
                                "primary_email_objection": {
                                    "type": "string",
                                    "enum": ["price_sensitivity", "urgency", "product_fit",
                                             "comparison_paralysis", "buyers_remorse", "distraction", "none"]
                                },
                                "example_verbatims": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "review_count": {"type": "integer"},
                                "confidence": {"type": "number"}
                            },
                            "required": ["label", "code", "description", "sentiment_direction",
                                         "emotional_dimension", "primary_creative_lane",
                                         "primary_email_objection", "example_verbatims",
                                         "review_count", "confidence"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["category", "category_code", "themes"],
                "additionalProperties": False
            }
        }
    },
    "required": ["codebook_version", "review_count_analyzed", "categories"],
    "additionalProperties": False
}
```

### CODE Schema

```python
CODE_SCHEMA = {
    "type": "object",
    "properties": {
        "coded_reviews": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "respondent_id": {"type": "string"},
                    "overall_sentiment": {
                        "type": "string",
                        "enum": ["positive", "negative", "mixed"]
                    },
                    "emotional_intensity": {
                        "type": "string",
                        "enum": ["low", "medium", "high"]
                    },
                    "status": {
                        "type": "string",
                        "enum": ["CODED", "NO_MATCH"]
                    },
                    "topics": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "category": {"type": "string"},
                                "label": {"type": "string"},
                                "code": {"type": "string"},
                                "sentiment": {
                                    "type": "string",
                                    "enum": ["positive", "negative", "mixed"]
                                },
                                "headline": {"type": "string"},
                                "emotional_intensity": {
                                    "type": "string",
                                    "enum": ["low", "medium", "high"]
                                },
                                "confidence": {"type": "number"}
                            },
                            "required": ["category", "label", "code", "sentiment",
                                         "headline", "emotional_intensity", "confidence"],
                            "additionalProperties": False
                        }
                    },
                    "no_match_reason": {"type": ["string", "null"]}
                },
                "required": ["respondent_id", "overall_sentiment", "emotional_intensity",
                             "status", "topics"],
                "additionalProperties": False
            }
        }
    },
    "required": ["coded_reviews"],
    "additionalProperties": False
}
```

### REFINE Schema

```python
REFINE_SCHEMA = {
    "type": "object",
    "properties": {
        "codebook_version": {"type": "string"},
        "refined_from": {"type": "string"},
        "review_count_analyzed": {"type": "integer"},
        "health_assessment": {
            "type": "object",
            "properties": {
                "overall_score": {"type": "number"},
                "total_themes": {"type": "integer"},
                "themes_with_high_ad_utility": {"type": "integer"},
                "previous_no_match_rate": {"type": "number"},
                "lane_coverage": {
                    "type": "object",
                    "properties": {
                        "Surprise": {"type": "integer"},
                        "Story": {"type": "integer"},
                        "Curiosity": {"type": "integer"},
                        "Guidance": {"type": "integer"},
                        "Instructional": {"type": "integer"},
                        "Hyperbole": {"type": "integer"},
                        "Newness": {"type": "integer"},
                        "Ranking": {"type": "integer"}
                    },
                    "required": ["Surprise", "Story", "Curiosity", "Guidance",
                                 "Instructional", "Hyperbole", "Newness", "Ranking"],
                    "additionalProperties": False
                },
                "lanes_with_zero_coverage": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "objection_coverage": {
                    "type": "object",
                    "properties": {
                        "price_sensitivity": {"type": "integer"},
                        "urgency": {"type": "integer"},
                        "product_fit": {"type": "integer"},
                        "comparison_paralysis": {"type": "integer"},
                        "buyers_remorse": {"type": "integer"},
                        "distraction": {"type": "integer"}
                    },
                    "required": ["price_sensitivity", "urgency", "product_fit",
                                 "comparison_paralysis", "buyers_remorse", "distraction"],
                    "additionalProperties": False
                }
            },
            "required": ["overall_score", "total_themes", "themes_with_high_ad_utility",
                         "previous_no_match_rate", "lane_coverage", "lanes_with_zero_coverage",
                         "objection_coverage"],
            "additionalProperties": False
        },
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
                            "properties": {
                                "label": {"type": "string"},
                                "code": {"type": "string"},
                                "description": {"type": "string"},
                                "sentiment_direction": {
                                    "type": "string",
                                    "enum": ["positive", "negative", "mixed"]
                                },
                                "emotional_dimension": {"type": "string"},
                                "primary_creative_lane": {
                                    "type": "string",
                                    "enum": ["Surprise", "Story", "Curiosity", "Guidance",
                                             "Instructional", "Hyperbole", "Newness", "Ranking"]
                                },
                                "secondary_creative_lane": {
                                    "type": ["string", "null"],
                                    "enum": ["Surprise", "Story", "Curiosity", "Guidance",
                                             "Instructional", "Hyperbole", "Newness", "Ranking", None]
                                },
                                "primary_email_objection": {
                                    "type": "string",
                                    "enum": ["price_sensitivity", "urgency", "product_fit",
                                             "comparison_paralysis", "buyers_remorse", "distraction", "none"]
                                },
                                "example_verbatims": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "review_count": {"type": "integer"},
                                "confidence": {"type": "number"}
                            },
                            "required": ["label", "code", "description", "sentiment_direction",
                                         "emotional_dimension", "primary_creative_lane",
                                         "primary_email_objection", "example_verbatims",
                                         "review_count", "confidence"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["category", "category_code", "themes"],
                "additionalProperties": False
            }
        },
        "changelog": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["MERGE", "SPLIT", "ADD", "RENAME", "REMAP", "SUNSET", "NO_CHANGE"]
                    },
                    "target_codes": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "result_code": {"type": ["string", "null"]},
                    "rationale": {"type": "string"}
                },
                "required": ["action", "target_codes", "rationale"],
                "additionalProperties": False
            }
        }
    },
    "required": ["codebook_version", "refined_from", "review_count_analyzed",
                 "health_assessment", "categories", "changelog"],
    "additionalProperties": False
}
```

---

## Python Orchestration Flow

```python
import json
import anthropic

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env


def run_pipeline(reviews: list[dict], product_context: dict) -> dict:
    """
    Full pipeline: DISCOVER → CODE → REFINE → RE-CODE

    Fully automated — no human review between steps.

    Args:
        reviews: list of process_voc_rows_template objects
        product_context: company_context dict from the JSON

    Returns:
        dict with final_codebook, coded_reviews, changelog, stats
    """

    # --- STEP 1: DISCOVER ---
    # Build the initial codebook from the first 100 reviews
    codebook_v1 = discover_codebook(reviews[:100], product_context)

    # --- STEP 2: CODE (first pass, in batches of 20) ---
    # Code all reviews against v1 codebook
    coded_v1, no_matches_v1 = code_all_reviews(reviews, codebook_v1)

    # --- STEP 3: REFINE ---
    # Produce the complete updated codebook v1.1
    # (not recommendations — the actual ready-to-use codebook)
    stats_v1 = compute_coding_stats(codebook_v1, coded_v1)
    codebook_v1_1 = refine_codebook(codebook_v1, stats_v1, no_matches_v1, product_context)

    # --- STEP 4: RE-CODE ---
    # Re-code ALL reviews against the refined v1.1 codebook
    # This is just Step 2 again with the better codebook
    coded_final, no_matches_final = code_all_reviews(reviews, codebook_v1_1)
    stats_final = compute_coding_stats(codebook_v1_1, coded_final)

    return {
        "codebook_v1": codebook_v1,
        "final_codebook": codebook_v1_1,
        "coded_reviews": coded_final,
        "no_matches": no_matches_final,
        "changelog": codebook_v1_1.get("changelog", []),
        "stats": {
            "v1": stats_v1,
            "final": stats_final,
            "improvement": {
                "no_match_rate_change": stats_v1["no_match_rate"] - stats_final["no_match_rate"],
                "theme_count_change": stats_final.get("total_themes", 0) - stats_v1.get("total_themes", 0)
            }
        }
    }


def code_all_reviews(reviews, codebook):
    """Run Step 2 (CODE) across all reviews in batches of 20. Reused in both passes."""
    coded_reviews = []
    no_matches = []

    for i in range(0, len(reviews), 20):
        batch = reviews[i:i+20]
        batch_results = code_review_batch(batch, codebook)

        for result in batch_results:
            if result.get("status") == "NO_MATCH":
                no_matches.append(result)
            coded_reviews.append(result)

    return coded_reviews, no_matches


def call_claude(*, model: str, system: str, user: str, schema: dict,
                temperature: float = 0.5, max_tokens: int = 8192) -> dict:
    """
    Generic Claude API call with guaranteed JSON output via output_config.

    The schema is enforced at the API level — the response literally cannot
    contain anything outside the schema. No preamble, no reasoning text.
    """
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": schema
            }
        }
    )

    return json.loads(response.content[0].text)


def discover_codebook(reviews, product_context):
    """Step 1: Build codebook from first batch of reviews."""

    review_texts = format_reviews_for_prompt(reviews)
    context_text = product_context.get("context_text", "")

    return call_claude(
        model="claude-sonnet-4-5-20250929",
        temperature=0.6,
        max_tokens=8192,
        system=DISCOVER_SYSTEM_PROMPT,
        user=DISCOVER_USER_PROMPT.format(
            product_context=context_text,
            reviews=review_texts,
            review_count=len(reviews)
        ),
        schema=DISCOVER_SCHEMA
    )


def code_review_batch(reviews, codebook):
    """Step 2: Code a batch of reviews against the codebook."""

    review_texts = format_reviews_for_coding(reviews)
    codebook_text = json.dumps(codebook, indent=2)

    result = call_claude(
        model="claude-haiku-4-5-20251001",
        temperature=0.2,
        max_tokens=4096,
        system=CODE_SYSTEM_PROMPT,
        user=CODE_USER_PROMPT.format(
            codebook=codebook_text,
            reviews=review_texts
        ),
        schema=CODE_SCHEMA
    )

    return result["coded_reviews"]


def refine_codebook(codebook, stats, no_matches, product_context):
    """Step 3: Refine and output the complete updated codebook."""

    return call_claude(
        model="claude-sonnet-4-5-20250929",
        temperature=0.4,
        max_tokens=8192,
        system=REFINE_SYSTEM_PROMPT,
        user=REFINE_USER_PROMPT.format(
            codebook=json.dumps(codebook, indent=2),
            stats=json.dumps(stats, indent=2),
            no_matches=json.dumps(no_matches, indent=2),
            product_context=product_context.get("context_text", "")
        ),
        schema=REFINE_SCHEMA
    )


def format_reviews_for_prompt(reviews):
    """Format reviews for the discovery prompt."""
    lines = []
    for r in reviews:
        rating = r["survey_metadata"]["rating"]
        name = r["survey_metadata"]["reviewer_name"]
        text = r["value"]
        lines.append(f'[{rating}★] {name}: "{text}"')
    return "\n\n".join(lines)


def format_reviews_for_coding(reviews):
    """Format reviews for the coding prompt with IDs."""
    lines = []
    for r in reviews:
        rid = r["respondent_id"]
        rating = r["survey_metadata"]["rating"]
        text = r["value"]
        lines.append(f'ID: {rid}\nRating: {rating}★\nText: "{text}"')
    return "\n\n---\n\n".join(lines)


def compute_coding_stats(codebook, coded_reviews):
    """Compute frequency and distribution stats from coded reviews."""
    theme_counts = {}
    total = len(coded_reviews)
    no_match_count = sum(1 for r in coded_reviews if r.get("status") == "NO_MATCH")

    for r in coded_reviews:
        for t in r.get("topics", []):
            code = t["code"]
            theme_counts[code] = theme_counts.get(code, 0) + 1

    lane_coverage = {}
    for cat in codebook.get("categories", []):
        for theme in cat.get("themes", []):
            lane = theme.get("primary_creative_lane", "Unknown")
            lane_coverage[lane] = lane_coverage.get(lane, 0) + 1

    return {
        "total_reviews": total,
        "no_match_count": no_match_count,
        "no_match_rate": round(no_match_count / max(total, 1), 3),
        "theme_frequency": theme_counts,
        "lane_coverage": lane_coverage
    }
```

---

## STEP 1: DISCOVER PROMPT

### System Prompt

```
You are a qualitative VoC (Voice of Customer) researcher specializing in customer insight extraction for direct-response advertising.

Your job is to read customer reviews for a product or service and identify the NATURAL THEMES that emerge — not from a predefined list, but from what customers actually talk about and how they feel.

Your output will be used to build Facebook ad creative across 8 lanes (Surprise, Story, Curiosity, Guidance, Instructional, Hyperbole, Newness, Ranking) and email sequences that handle 6 objection types (price_sensitivity, urgency, product_fit, comparison_paralysis, buyers_remorse, distraction).

This means your themes must capture:
1. WHAT customers talk about (the topic)
2. HOW they feel about it (the emotion — not just positive/negative, but the specific feeling: relief, delight, frustration, surprise, regret, confidence, anxiety, etc.)
3. WHY it matters for ads (which creative lane or objection type this theme naturally serves)

CRITICAL RULES:

- Theme names must use CUSTOMER LANGUAGE, not marketing jargon
  BAD: "Product Quality Perception" or "Value Proposition Assessment"
  GOOD: "Surprisingly delicious" or "Gave me back my time"

- Every theme needs a clear sentiment direction (positive, negative, or mixed)

- Negative themes are VALUABLE — they become objection-handling ads and abandoned cart emails. Do not ignore or minimize them.

- Each theme must map to at least one of the 8 creative lanes:
  * Surprise — unexpected benefit, reversal, counterintuitive claim
  * Story — narrative arc, transformation, before/after, emotional journey
  * Curiosity — open loop, teaser, "what if," information gap
  * Guidance — how-to, solutions, trusted advisor positioning
  * Instructional — detailed breakdown, demo, tutorial, practical value
  * Hyperbole — bold claims backed by customer language, superlatives
  * Newness — first experience, fresh discovery, "why didn't I try this sooner"
  * Ranking — comparison, vs. competitors, best-in-category claims

- Each theme should also map to one of the 6 email objection types where relevant:
  * price_sensitivity — "Is it worth the money?"
  * urgency — "Why buy now?"
  * product_fit — "Is this right for me?"
  * comparison_paralysis — "Why this vs. competitors?"
  * buyers_remorse — "Will I regret this?"
  * distraction — "I'm busy, why should I care?"

- Aim for 8-15 themes grouped into 4-7 high-level categories
- Each theme needs 2-3 example verbatims quoted EXACTLY from the reviews (not paraphrased)
- Include a confidence score (0.7-1.0) based on how many reviews support the theme
```

### User Prompt

```
PRODUCT CONTEXT:
{product_context}

---

CUSTOMER REVIEWS ({review_count} total):

{reviews}

---

TASK: Read every review above and identify the natural themes that emerge. Group them into high-level categories. For each theme, identify the emotional dimension, the best-fit creative lane for ads, and the best-fit email objection type.

IMPORTANT:
- example_verbatims must be EXACT quotes from the reviews, not paraphrases
- Every review should be covered by at least one theme (no orphans)
- code format: categorycode_sentiment_descriptor (e.g., taste_positive_surprise, delivery_negative_failure)
- If a theme only appears in 1 review, still include it if the emotional intensity is high
- Negative reviews are gold for ads — they reveal objections to handle. Include them.
```

---

## STEP 2: CODE PROMPT

### System Prompt

```
You are a content coder. Your job is to read customer reviews and code each one against a predefined codebook of themes.

For each review, you will:
1. Assign 1-3 topics from the codebook (most reviews will have 1-2)
2. Extract a headline of 3-7 words taken VERBATIM from the review text (not invented, not paraphrased — actual words from the review)
3. Rate the emotional intensity of the review: low (factual/neutral), medium (clear sentiment), high (vivid, emotionally charged language that would stop someone scrolling)
4. Determine overall sentiment: positive, negative, or mixed
5. If the review genuinely doesn't fit ANY theme in the codebook, mark it as NO_MATCH

CRITICAL RULES:

- Headlines must be VERBATIM snippets from the review text. If the review says "Every. Single. Meal, that I have had from Prep Kitchen, I have absolutely loved!!" then a valid headline is "absolutely loved every single meal" — you can reorder slightly for readability but every word must come from the review.

- Emotional intensity matters because the ad engine prioritises high-intensity verbatims:
  * LOW: "Food is tasty" (factual, minimal emotion)
  * MEDIUM: "Really good quality and the delivery was very good" (positive but measured)
  * HIGH: "I cannot tell you how fussy I am about food... Every. Single. Meal... I have absolutely loved!!" (vivid, emphatic, would make good ad copy)

- A review can have topics with DIFFERENT sentiments. Example: "Tasty meals but smaller than expected" = positive taste + negative portions.

- For very short or vague reviews ("Great Taste", "Just Awful"), still code them — assign the closest theme and note low confidence.

- Confidence score per topic: 0.7 = borderline fit, 0.85 = good fit, 0.95+ = perfect fit
```

### User Prompt

```
CODEBOOK:
{codebook}

---

REVIEWS TO CODE:

{reviews}

---

TASK: Code each review against the codebook.

RULES:
- Every review must appear in the output, even if it's a NO_MATCH
- headlines are VERBATIM from the review — do not invent words
- 1-3 topics per review (most will have 1-2)
- Use the exact category, label, and code values from the codebook — do not invent new ones
- If a review covers a topic not in the codebook, mark the REVIEW as NO_MATCH (do not create new themes — that's Step 3's job)
```

---

## STEP 3: REFINE PROMPT

**Purpose:** Takes the v1 codebook + coding stats + NO_MATCH reviews and outputs a **complete, updated codebook v1.1** with all merges, splits, additions, renames, and remaps already applied. No human review — the output IS the new codebook, ready for re-coding in Step 4.

### System Prompt

```
You are a senior qualitative researcher refining a VoC codebook. You will receive:
1. The current codebook (v1)
2. Coding statistics showing how themes were distributed across reviews
3. Any NO_MATCH reviews that didn't fit the v1 codebook

Your job is to PRODUCE A COMPLETE UPDATED CODEBOOK (v1.1) with all improvements applied. Do not output recommendations — output the actual codebook. The downstream system will re-code all reviews against your updated codebook automatically.

The codebook feeds a Facebook ad engine (8 creative lanes) and email sequence engine (6 objection types). A good codebook means:
1. Every theme has clear ad utility — hand the theme + verbatims to a copywriter and they know what ad to write
2. The 8 creative lanes have reasonable coverage — not all themes mapping to one lane
3. Negative themes are preserved — they become objection-handling ads
4. Themes are specific enough to test (one theme = one ad hypothesis) but not so granular they only have 1 review
5. Theme names use customer language, not marketing jargon

OPERATIONS TO APPLY:

MERGE — If two themes share >70% of the same verbatims, or the distinction wouldn't change which ad you'd write → combine them into one theme in the output. Pick the more vivid customer-language label.

SPLIT — If a theme covers >25% of all reviews, or its verbatims describe clearly different experiences → split it into 2-3 more specific themes in the output.

ADD — If 2+ NO_MATCH reviews share a common pattern → create a new theme for them in the output. Name it in customer language. Assign a creative lane and email objection.

RENAME — If the verbatims suggest a more vivid customer-language label → use the better name in the output.

REMAP — If a theme's verbatims better suit a different creative lane or email objection → update the mapping in the output.

SUNSET — If a theme has only 1 review, low confidence, and no emotionally charged content → remove it from the output.

NO-CHANGE — If a theme is healthy, keep it exactly as-is in the output.

IMPORTANT:
- The output must be a COMPLETE codebook — every theme that survives must be in it, with all fields populated
- Merged themes: combine the example_verbatims from both source themes
- Split themes: distribute the example_verbatims appropriately
- Added themes: pull example_verbatims from the NO_MATCH reviews
- The changelog field documents what you did and why (for audit trail)
- If the v1 codebook was already healthy (low NO_MATCH rate, good lane coverage, good specificity), output it with minimal changes and note that in the changelog
```

### User Prompt

```
PRODUCT CONTEXT:
{product_context}

---

CURRENT CODEBOOK (v1):
{codebook}

---

CODING STATISTICS:
{stats}

---

NO_MATCH REVIEWS (reviews that didn't fit any theme):
{no_matches}

---

TASK: Refine this codebook and output the COMPLETE UPDATED codebook v1.1 with all improvements applied.

RULES:
- The categories array IS the complete codebook — not a diff, not recommendations, the ACTUAL codebook
- Every surviving theme must have all fields populated (label, code, description, sentiment_direction, emotional_dimension, primary_creative_lane, primary_email_objection, example_verbatims, review_count, confidence)
- example_verbatims must be EXACT quotes from the original reviews (not paraphrased)
- The changelog must document every operation you performed, including NO_CHANGE for themes you kept as-is (so the system can verify completeness)
- Be conservative: don't reorganise for tidiness. Only change what makes a material difference to ad or email generation quality.
- If the v1 codebook was healthy: output it mostly unchanged, log NO_CHANGE for each theme, and set a high health score
```

---

## Batch Size Logic

```python
def determine_batch_strategy(total_reviews: int) -> dict:
    """Determine how to batch reviews through the pipeline."""

    if total_reviews <= 100:
        return {
            "discovery_sample_size": total_reviews,  # use all
            "coding_batch_size": 20,
            "refine_after_every": total_reviews,     # refine once at end
            "total_coding_batches": (total_reviews + 19) // 20
        }

    elif total_reviews <= 500:
        return {
            "discovery_sample_size": 100,            # first 100
            "coding_batch_size": 20,
            "refine_after_every": total_reviews,     # refine once at end
            "total_coding_batches": (total_reviews + 19) // 20
        }

    else:  # 500+
        return {
            "discovery_sample_size": 100,            # first 100
            "coding_batch_size": 20,
            "refine_after_every": 500,               # refine every 500
            "total_coding_batches": (total_reviews + 19) // 20
        }
```

---

## Estimated Token Usage & Cost

| Step | Model | Input tokens (est.) | Output tokens (est.) | Cost per run |
|------|-------|-------------------|---------------------|-------------|
| DISCOVER (100 reviews) | claude-sonnet-4-5 | ~15,000 | ~3,000 | ~$0.09 |
| CODE (per batch of 20) | claude-haiku-4-5 | ~4,000 | ~2,000 | ~$0.01 |
| REFINE (per run) | claude-sonnet-4-5 | ~8,000 | ~4,000 | ~$0.08 |
| RE-CODE (per batch of 20) | claude-haiku-4-5 | ~4,000 | ~2,000 | ~$0.01 |
| **Total for 100 reviews** | | | | **~$0.27** |
| **Total for 1,000 reviews** | | | | **~$1.17** |

Pricing basis: claude-sonnet-4-5 ($3/M input, $15/M output), claude-haiku-4-5 ($0.80/M input, $4/M output). Step 4 (RE-CODE) doubles the Haiku batches since every review gets coded twice. Haiku is fast enough that the extra pass adds seconds, not minutes.

---

## How the Output Feeds Downstream

### Into the Facebook Ad Engine:

The ad prompt currently needs VoC evidence as verbatim quotes organized by theme. With the codebook, the feed becomes:

```python
def prepare_voc_for_ad_generation(coded_reviews, codebook, target_lane="Story"):
    """
    Select the best verbatims for a specific creative lane.
    Returns top 6 verbatims sorted by emotional intensity.
    """
    relevant_themes = [
        theme for cat in codebook["categories"]
        for theme in cat["themes"]
        if theme["primary_creative_lane"] == target_lane
        or theme.get("secondary_creative_lane") == target_lane
    ]

    relevant_codes = {t["code"] for t in relevant_themes}

    candidates = []
    for review in coded_reviews:
        for topic in review.get("topics", []):
            if topic["code"] in relevant_codes:
                candidates.append({
                    "verbatim": next(r["value"] for r in raw_reviews
                                    if r["respondent_id"] == review["respondent_id"]),
                    "headline": topic["headline"],
                    "theme": topic["label"],
                    "emotional_intensity": topic["emotional_intensity"],
                    "sentiment": topic["sentiment"]
                })

    # Sort: high intensity first, then medium, then low
    intensity_order = {"high": 0, "medium": 1, "low": 2}
    candidates.sort(key=lambda x: intensity_order.get(x["emotional_intensity"], 2))

    return candidates[:6]
```

### Into the Email Sequence Engine:

```python
def prepare_voc_for_email_generation(coded_reviews, codebook, target_objection="product_fit"):
    """
    Select verbatims that address a specific email objection type.
    """
    relevant_themes = [
        theme for cat in codebook["categories"]
        for theme in cat["themes"]
        if theme["primary_email_objection"] == target_objection
    ]

    # Same pattern as above — filter by code, sort by intensity
    ...
```

---

## Integration with Existing ProcessVoc Model

After Step 4 (RE-CODE), update each ProcessVoc row:

```python
def apply_coding_to_process_voc(db_session, coded_reviews):
    """Update ProcessVoc rows with coded topics."""

    for coded in coded_reviews:
        row = db_session.query(ProcessVoc).filter_by(
            respondent_id=coded["respondent_id"]
        ).first()

        if row:
            row.topics = coded["topics"]  # JSONB field
            row.overall_sentiment = coded["overall_sentiment"]
            row.processed = True

    db_session.commit()
```

The existing `voc_summary_service.py` already reads from `ProcessVoc.topics` and builds the category → topic → verbatim hierarchy. As long as the topics array follows the same shape (`category`, `label`, `code`, `sentiment`), everything downstream works — plus now each topic also carries `headline`, `emotional_intensity`, and `confidence` for the ad engine to use.
