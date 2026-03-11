"""
Reusable service for extracting product/company context from a URL.
"""

from typing import Any, Dict
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models import Prompt
from app.services.web_crawler_service import WebCrawlerService


DEFAULT_EXTRACT_SYSTEM_MSG = (
    "You are an expert at extracting product information from e-commerce product detail pages (PDPs).\n\n"
    "You will receive the raw text content of a PDP. Extract the following into a structured, readable format "
    "suitable for use when generating ads and marketing emails:\n\n"
    "1. **Product name** - The main product title/name\n"
    "2. **Pricing** - Price, any discounts, payment options, subscription pricing if applicable\n"
    "3. **Unique features / differentiators** - Key benefits, specs, or selling points that distinguish this product\n"
    "4. **Proof elements** - Reviews, ratings, certifications, awards, guarantees, testimonials\n"
    "5. **Risk reversal** - Return policy, warranty, money-back guarantee, trial period\n\n"
    "Output as clear, concise text that can be used as context for AI-generated ad copy and email content. "
    "Use headers (##) for sections if helpful. Be selective - include only the most relevant information "
    "for marketing purposes. Avoid redundant or overly promotional language from the page."
)


def normalize_url(url: str) -> str:
    clean_url = (url or "").strip()
    if not clean_url:
        return clean_url
    if clean_url.startswith(("http://", "https://")):
        return clean_url
    return f"https://{clean_url}"


def extract_product_name(content: str, url: str) -> str:
    """Extract the product name from LLM-structured markdown output."""
    lines = [line.strip() for line in content.split("\n") if line.strip()]
    if not lines:
        return "Product"

    generic_headers = {"product name", "product", "name", "product title", "title"}

    def clean(text: str) -> str:
        return text.replace("**", "").replace("__", "").strip()

    for idx, line in enumerate(lines):
        stripped = line.lstrip("#").strip()
        if clean(stripped).lower() in generic_headers and idx + 1 < len(lines):
            next_line = lines[idx + 1].lstrip("#").strip()
            cleaned = clean(next_line)
            if cleaned and cleaned.lower() not in generic_headers:
                return cleaned[:255]

    first = clean(lines[0].lstrip("#").strip())
    if first and first.lower() not in generic_headers:
        return first[:255]

    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    if not slug:
        return "Product"
    return slug.replace("-", " ").replace("_", " ").title()[:255]


def extract_product_context_from_url_service(
    db: Session,
    llm_service: Any,
    url: str,
) -> Dict[str, str]:
    """
    Extract product/company context from a URL without persisting to database.
    """
    normalized_url = normalize_url(url)
    if not normalized_url:
        raise ValueError("URL is required")

    prompt = (
        db.query(Prompt)
        .filter(
            Prompt.prompt_purpose == "product_context_extract",
            Prompt.status == "live",
        )
        .order_by(Prompt.version.desc())
        .first()
    )

    system_message = prompt.system_message if prompt else DEFAULT_EXTRACT_SYSTEM_MSG
    llm_model = prompt.llm_model if prompt else "gpt-4o-mini"

    crawler = WebCrawlerService()
    page_content = crawler.fetch_single_page(normalized_url, max_chars=10000)
    if not page_content:
        raise ValueError("Could not fetch or extract content from the URL.")

    result = llm_service.execute_prompt(
        system_message=system_message,
        user_message=page_content,
        model=llm_model,
    )
    content = (result.get("content") or "").strip()
    if not content:
        raise RuntimeError("LLM returned empty extraction")

    return {
        "name": extract_product_name(content, normalized_url),
        "context_text": content,
        "source_url": normalized_url,
    }
