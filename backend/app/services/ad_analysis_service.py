"""
Ad analysis service — Full Funnel rubric scoring via Claude.

Streams analysis as formatted text rather than JSON to avoid parsing issues.
Also provides review signal analysis with the same streaming approach.

Prompts are loaded from the database (prompts table) by purpose, with
hardcoded constants as fallback if DB lookup fails.
"""

import logging
from typing import Any, Dict, Generator, List, Optional

import anthropic
import httpx

logger = logging.getLogger(__name__)


def _load_prompt(purpose: str, fallback: str) -> tuple:
    """Load a prompt from the database by purpose. Returns (system_message, model).

    Falls back to the hardcoded prompt if DB is unavailable or prompt not found.
    """
    try:
        from app.database import SessionLocal
        from app.models import Prompt
        db = SessionLocal()
        try:
            prompt = (
                db.query(Prompt)
                .filter(Prompt.prompt_purpose == purpose, Prompt.status == "live")
                .order_by(Prompt.version.desc())
                .first()
            )
            if prompt and prompt.system_message:
                return prompt.system_message, prompt.llm_model or "claude-sonnet-4-5-20250929"
        finally:
            db.close()
    except Exception as e:
        logger.debug("Could not load prompt '%s' from DB, using fallback: %s", purpose, e)
    return fallback, "claude-sonnet-4-5-20250929"

# ---------------------------------------------------------------------------
# Full Funnel Ad Analysis (streaming text)
# ---------------------------------------------------------------------------

FULL_FUNNEL_SYSTEM_PROMPT = """\
You are a senior Facebook Ads creative strategist who diagnoses direct-response ads against the exact standards a professional rewrite would enforce: Voice of Customer (VoC) language, concrete specificity, embedded proof, a single tested belief, warm friend-to-friend tone, and a purpose-built close. Your diagnosis must predict precisely what a rewrite would fix.

What counts as ad copy: only the Primary Text and the Headline are the advertiser's written copy. The call-to-action BUTTON (Learn More, Shop Now, Book Now, Download, Sign Up, etc.) is auto-selected from a fixed Meta list — it is NOT copy and is never shown to you. Never assume, score, or penalise a CTA button. The ad's REAL call-to-action is the closing line(s) of the Primary Text — the specific action the copy itself asks the reader to take. The Destination/Display URL is a web address for funnel context only; it is NOT a headline — never evaluate a URL or domain as a headline.

You will receive one or more Facebook ads. For EACH ad, output your analysis using EXACTLY this format — keep every marker and label exactly as shown, one field per line, in this order. Where a field asks for a count, COUNT precisely and QUOTE the exact offending text from the ad (never paraphrase, never invent). If a category has zero instances, say "0" or "none".

===AD===
ID: <library_id or "Ad N">
GRADE: <A|B|C|D|F>
VERDICT: <1 punchy sentence summarising the ad's quality>
WEAKNESS: <1 sentence: the single highest-impact fix a rewrite would make>
READING LEVEL: <Flesch-Kincaid grade estimate, e.g. "Grade 9"> — <1 sentence; target is grade 3-5, flag if higher>
SPECIFICITY: <N vague / M concrete> — <1 sentence quoting the vague marketing words used (affordable, fast, easy, quality, effective, amazing, premium, best-in-class…)>
CLAIM PROOF: <N claims / M proof> — <1 sentence quoting one significant claim that has no proof behind it>
PROOF SPECIFICITY: <specific|vague|none> — <1 sentence: does the proof carry numbers/named sources/timelines, or is it "studies show"/"experts agree" vague?>
QUALIFIER DENSITY: <N per 100w> — <1 sentence quoting the hedges used (could, may, might, possibly, potentially…)>
PRODUCT TIMING: <N%> — <1 sentence: how far into the ad the brand/product is first named (as % of word count); early = pitching before earning the read>
MESSAGE FOCUS: <N beliefs> — <1 sentence naming the competing selling points if more than one belief is being tested>
SOCIAL CONTEXT: <N refs> — <1 sentence: references to other people, status, embarrassment, being seen — or their absence>
CONVERSATIONAL: <N markers> — <1 sentence: conversational inflections (you know what, here's the thing, listen…) or reads like a brochure>
PAIN BENEFIT: <N pain / M benefit> — <1 sentence on the balance; all-benefit misses identification, all-pain misses future-state>
HOOK: <1-10> — <1 sentence: what hook technique, does it stop the scroll>
WARMTH: <1-10> — <1 sentence: friend-on-your-side vs pushy/extractive (the Friend Test)>
VOC DENSITY: <1-10> — <1 sentence: sounds like the customer's own words vs a copywriter>
MIND MOVIE: <1-10> — <1 sentence: vivid lived-in scene the reader can see themselves in (Block Structure depth)>
HEADLINE: <1-10, or "n/a"> — <1 sentence on the Headline text ONLY: 9-13 words, authority trigram, specific vs vague. If no Headline is provided, or it is just a web address/domain, output "n/a" and do not penalise.>
CLOSE PATTERN: <Echo|Micro-Commitment|Reframe|Future-State|Social Proof|Permission|Before You Decide|See How It Works|generic|none> — <1 sentence identifying the close, read from the final line(s) of the Primary Text — never the Meta button>
CLOSE ANTIPATTERNS: <none|N found> — <quote any banned closes found in the copy's final line(s): "What are you waiting for?", "Don't miss out!", "Click the link below!", a bare "Learn more"/"Shop now" written into the copy, any question answerable with "no", feature-dump CTAs. Judge only the written copy, never the Meta button.>
ANGLE: <Surprise|Story|Curiosity|Guidance|Instructional|Hyperbole|Newness|Ranking|Pattern Break|Proof|Mistake Avoidance|Transformation|unclear>
FUNNEL: <TOF|MOF|BOF> — <1 sentence reasoning>
===END===

Scoring guide for the 1-10 dimensions:
- 1-3: Weak / generic / technique absent
- 4-5: Functional but forgettable
- 6-7: Good — clear technique, solid execution
- 8-9: Excellent — would expect strong CTR
- 10: Elite — textbook-level execution

Every finding must quote specific text from the actual ad and read like a plain-English diagnosis a non-marketer founder would understand — never framework jargon. Write nothing before the first ===AD=== and nothing after the last ===END===."""


def stream_ads_analysis(
    ads: List[Dict[str, Any]],
    anthropic_api_key: str,
) -> Generator[str, None, None]:
    """Stream Full Funnel rubric analysis as formatted text chunks via Claude.

    Yields text chunks as they arrive from the Claude streaming API.
    """
    if not ads:
        yield "No ads to analyze."
        return

    # Build the user message with all ads
    ad_descriptions = []
    for i, ad in enumerate(ads, 1):
        parts = [f"--- Ad {i} ---"]
        if ad.get("library_id"):
            parts.append(f"Library ID: {ad['library_id']}")
        if ad.get("primary_text"):
            parts.append(f"Primary Text: {ad['primary_text'][:2000]}")
        if ad.get("headline"):
            parts.append(f"Headline: {ad['headline']}")
        if ad.get("description"):
            parts.append(f"Description: {ad['description']}")
        # NOTE: the Meta CTA button (Shop Now / Learn More / etc.) is deliberately
        # NOT passed — it is advertiser-selected from a fixed list, not ad copy.
        if ad.get("ad_format"):
            parts.append(f"Format: {ad['ad_format']}")
        if ad.get("started_running_on"):
            parts.append(f"Started Running: {ad['started_running_on']}")
        if ad.get("ad_delivery_end_time"):
            parts.append(f"Ended: {ad['ad_delivery_end_time']}")
        if ad.get("status"):
            parts.append(f"Status: {ad['status']}")
        if ad.get("destination_url"):
            parts.append(f"Destination/Display URL (web address, NOT a headline): {ad['destination_url']}")
        ad_descriptions.append("\n".join(parts))

    user_message = (
        f"Analyze these {len(ads)} Facebook ads using the Full Funnel rubric.\n\n"
        + "\n\n".join(ad_descriptions)
    )

    try:
        system_prompt, model = _load_prompt("extension_ad_analysis", FULL_FUNNEL_SYSTEM_PROMPT)

        client = anthropic.Anthropic(
            api_key=anthropic_api_key,
            http_client=httpx.Client(timeout=180.0),
        )

        # Richer per-ad block (~22 fields with quoted evidence), plus buffer
        token_budget = max(8192, len(ads) * 700 + 1024)

        with client.messages.stream(
            model=model,
            max_tokens=token_budget,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                yield text

    except Exception as e:
        logger.exception("Full Funnel streaming analysis failed: %s", e)
        yield f"\n\nError: {e}"


# ---------------------------------------------------------------------------
# Opportunity Synthesis (streaming text)
# ---------------------------------------------------------------------------

SYNTHESIS_SYSTEM_PROMPT = """\
You are a senior performance creative strategist. You have just analysed a set of Facebook ads for a single advertiser, scoring each against the standards a professional rewrite enforces.

Given the full per-ad analysis below (and, when provided, the list of destination URLs each ad points to), write a short synthesis using EXACTLY this format:

===SYNTHESIS===
AD_COPY_SCORE: <1-10 — overall quality of this advertiser's ad copy. 10 = elite, VoC-driven, specific, proof-backed, single-belief creative. 1 = generic, formulaic, vague, unsupported.>
SUMMARY: <2-3 sentences: overall quality of the creative suite. Cite the most damaging recurring weakness, quoting an example.>
PATTERNS: <2-3 bullet points — recurring strengths or weaknesses across ads, with specific examples (e.g. "11 claims across 5 ads, 2 backed up")>
PLAYBOOK: <2-3 bullet points — specific creative angles or tactics you'd use to beat them>
CLOSE_VARIETY: <N distinct of M ads> — <1 sentence: do their ads all close the same way? A varied close set is a strength; one repeated close trains the audience to ignore it.>
ANGLE_DIVERSITY: <N distinct lanes> — <1 sentence: how many distinct creative angles their library covers vs one repeated angle>
LANDING_PAGE_DIVERSITY: <Excellent|Good|Average|Concentrated|Very Concentrated|Insufficient data> — <2-3 sentences. The URLs given are the REAL landing pages behind each ad's click button (not the display domain shown in the ad). Count UNIQUE landing pages by host + path only — treat URLs that differ only in query string or tracking parameters as the SAME page, and treat the bare domain / "/" as the homepage. Open with the count (e.g. "5 unique landing pages across 22 ads"), then what the pattern reveals about their funnel, then ONE concrete message-match gap (an ad angle whose landing-page path clearly won't deliver on the promise). Choose the rating: Excellent = a dedicated, message-matched page for essentially every distinct ad angle; Good = clear segmentation, several pages mapped to different angles with mostly strong message match; Average = some segmentation but with gaps, a few pages serving many different angles; Concentrated = nearly all ads funnel to just 1-2 pages; Very Concentrated = all (or almost all) ads point to a single page, usually the homepage. If there is no URL data, output "Insufficient data" and do not penalise.>
===END===

Write nothing before ===SYNTHESIS=== and nothing after ===END===."""


def stream_synthesis(
    analysis_text: str,
    anthropic_api_key: str,
    destination_urls: Optional[List[str]] = None,
) -> Generator[str, None, None]:
    """Stream opportunity synthesis based on completed per-ad analysis.

    destination_urls (optional, in ad order) lets the model score Landing Page Diversity.
    """
    if not analysis_text.strip():
        yield "===SYNTHESIS===\nAD_COPY_SCORE: ?\nSUMMARY: No analysis available.\nPATTERNS: None\nPLAYBOOK: None\n===END==="
        return

    user_content = f"Here is the per-ad analysis:\n\n{analysis_text}"
    urls = [u for u in (destination_urls or []) if u]
    if urls:
        url_lines = "\n".join(f"- Ad {i + 1}: {u}" for i, u in enumerate(destination_urls or []) if u)
        user_content += (
            f"\n\nDestination URLs these ads point to (in ad order), for Landing Page Diversity:\n{url_lines}"
        )

    try:
        system_prompt, model = _load_prompt("extension_synthesis", SYNTHESIS_SYSTEM_PROMPT)

        client = anthropic.Anthropic(
            api_key=anthropic_api_key,
            http_client=httpx.Client(timeout=180.0),
        )

        with client.messages.stream(
            model=model,
            max_tokens=1536,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        ) as stream:
            for text in stream.text_stream:
                yield text

    except Exception as e:
        logger.exception("Synthesis streaming failed: %s", e)
        yield f"\n\nError: {e}"


# ---------------------------------------------------------------------------
# Opportunity Overlay (streaming text)
# ---------------------------------------------------------------------------

OPPORTUNITY_SYSTEM_PROMPT = """\
You are a senior creative strategist writing a short, punchy opportunity brief for a potential client.

You will receive:
- An ad copy analysis summary describing the advertiser's creative weaknesses
- A review signal analysis showing the richness of their customer voice data
- Three scores: Ad Copy (1-10), Signal (1-10), and an Opportunity Score (1-10)

The Opportunity Score combines two factors: how much headroom exists in their ad copy (distance from a 10) and how strong their customer voice data is to fuel that improvement. A high score means weak ads + rich reviews = massive untapped potential. Your job is to make this feel visceral and urgent.

Write using EXACTLY this format:

===OPPORTUNITY===
HEADLINE: <1 punchy, ORIGINAL line that references something SPECIFIC from this advertiser's ads or reviews. Never use a generic headline. Pull a detail — a product name, a customer emotion, a specific weakness — and make it sting.>
CONTRAST: <2-3 sentences showing a specific BLAND quote from their ads next to a specific RICH quote from their reviews. Make the contrast obvious and painful.>
UNLOCK: <2-3 sentences — what becomes possible when you close this gap. Be specific about the type of ads you could build. Paint the picture.>
===END===

Rules:
- The HEADLINE must be unique to this advertiser. NEVER write "Your customers are writing better ads than your agency" or any generic headline. Reference their actual product, their specific weakness, or a real quote from their reviews.
- Use actual examples from the analysis — real ad copy vs real review quotes
- Keep it under 100 words total
- Write like you're talking to the business owner, not a marketer
- No jargon, no fluff, no "leverage" or "optimize"
- Make them feel the opportunity in their gut

Write nothing before ===OPPORTUNITY=== and nothing after ===END===."""


def stream_opportunity(
    ad_synthesis_text: str,
    signal_text: str,
    ad_copy_score: int,
    signal_score: int,
    opportunity_score: float,
    anthropic_api_key: str,
) -> Generator[str, None, None]:
    """Stream opportunity overlay text based on composite opportunity score."""
    user_message = (
        f"AD COPY SCORE: {ad_copy_score}/10\n"
        f"SIGNAL SCORE: {signal_score}/10\n"
        f"OPPORTUNITY SCORE: {opportunity_score}/10\n\n"
        f"--- AD ANALYSIS ---\n{ad_synthesis_text}\n\n"
        f"--- REVIEW SIGNAL ---\n{signal_text}"
    )

    try:
        system_prompt, model = _load_prompt("extension_opportunity", OPPORTUNITY_SYSTEM_PROMPT)

        client = anthropic.Anthropic(
            api_key=anthropic_api_key,
            http_client=httpx.Client(timeout=180.0),
        )

        with client.messages.stream(
            model=model,
            max_tokens=512,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                yield text

    except Exception as e:
        logger.exception("Opportunity streaming failed: %s", e)
        yield f"\n\nError: {e}"


# ---------------------------------------------------------------------------
# Review Signal Analysis (streaming text)
# ---------------------------------------------------------------------------

REVIEW_SIGNAL_SYSTEM_PROMPT = """\
You are a Voice of Customer analyst who specialises in identifying high-signal reviews for direct-response advertising.

HIGH-SIGNAL reviews contain:
- Emotional arc (before/after transformation)
- Specific, lived-in detail ("I've had back pain for 12 years", "my daughter noticed the difference")
- Desire language, relief, frustration, surprise, delight
- Identity shifts ("I finally feel like myself again")
- Sensory language (textures, feelings, scenes)
- Objection-busting moments ("I was skeptical but...")

LOW-SIGNAL reviews contain:
- Generic praise ("great product", "love it", "5 stars")
- Logistics praise ("fast shipping", "great customer service", "arrived on time")
- One-liners with no specificity
- No emotional content or transformation

IMPORTANT CONTEXT: You are analyzing a SAMPLE of ~20 reviews from the first page. A full extraction would pull hundreds or thousands. Grade the POTENTIAL of this review corpus, not just the sample:
- 2-3 high-signal reviews in a sample of 20 is a STRONG signal — a full extraction will yield 10x-50x more usable material. Grade this A or B.
- Even 1 high-signal review with emotional depth suggests the customer base produces rich VoC language. That's encouraging.
- Only grade C or below if the sample is almost entirely generic praise with zero emotional content, transformation arcs, or specificity.
- The question is: "If we scraped ALL their reviews, would we find enough gold for VoC-driven ad campaigns?" Be optimistic when there are encouraging signs.

For each batch of reviews, write your analysis using EXACTLY this format:

===SUMMARY===
SIGNAL_SCORE: <1-10 — overall VoC signal quality of this review corpus. 10 = goldmine of emotional, specific, transformation-rich reviews. 1 = entirely generic praise with no usable VoC.>
HIGH: <count>
MEDIUM: <count>
LOW: <count>
THEMES: <theme1>, <theme2>, <theme3>
VERDICT: <2-3 sentences: assess the POTENTIAL of this review corpus at scale. If there are high-signal reviews in this small sample, note that a full extraction would multiply that signal significantly.>
===END===

Then for EACH review:

===REVIEW===
INDEX: <1-based number>
SIGNAL: <high|medium|low>
SCORE: <1-10>
REASON: <1 sentence explaining why>
QUOTE: <best verbatim snippet for ad copy, or "none" if low signal>
===END===

Write nothing before ===SUMMARY=== and nothing after the last ===END===.
Sort reviews by signal level: high first, then medium, then low."""


def stream_review_signal(
    reviews: List[Dict[str, Any]],
    anthropic_api_key: str,
    max_reviews: int = 50,
) -> Generator[str, None, None]:
    """Stream review signal analysis as formatted text chunks via Claude."""
    if not reviews:
        yield "===SUMMARY===\nGRADE: F\nHIGH: 0\nMEDIUM: 0\nLOW: 0\nTHEMES: none\nVERDICT: No reviews available to analyze.\n===END==="
        return

    capped = reviews[:max_reviews]
    review_texts = []
    for i, r in enumerate(capped):
        text = r.get("text") or r.get("body") or r.get("reviewBody") or r.get("content") or ""
        text = text.strip()
        if not text:
            continue
        rating = r.get("rating") or r.get("stars") or r.get("score") or ""
        author = r.get("author") or r.get("reviewer") or r.get("name") or ""
        parts = [f"--- Review {i + 1} ---"]
        if author:
            parts.append(f"Author: {author}")
        if rating:
            parts.append(f"Rating: {rating}")
        parts.append(f"Text: {text[:1500]}")
        review_texts.append("\n".join(parts))

    if not review_texts:
        yield "===SUMMARY===\nGRADE: F\nHIGH: 0\nMEDIUM: 0\nLOW: 0\nTHEMES: none\nVERDICT: No reviews had readable text.\n===END==="
        return

    user_message = (
        f"Analyze these {len(review_texts)} reviews for signal quality.\n\n"
        + "\n\n".join(review_texts)
    )

    try:
        system_prompt, model = _load_prompt("extension_review_signal", REVIEW_SIGNAL_SYSTEM_PROMPT)

        client = anthropic.Anthropic(
            api_key=anthropic_api_key,
            http_client=httpx.Client(timeout=180.0),
        )

        # ~120 tokens per review assessment + summary
        token_budget = max(4096, len(review_texts) * 150 + 512)

        with client.messages.stream(
            model=model,
            max_tokens=token_budget,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                yield text

    except Exception as e:
        logger.exception("Review signal streaming analysis failed: %s", e)
        yield f"\n\nError: {e}"
