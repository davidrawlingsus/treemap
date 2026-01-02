"""
OpenAI service for generating dimension summaries.
Uses the refined prompt format with topic-weighted insights.
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
import json
import re

logger = logging.getLogger(__name__)


@dataclass
class DimensionData:
    """Sample data for a dimension"""
    value: str
    sentiment: Optional[str] = None
    topics: Optional[List[Dict]] = None


class OpenAIService:
    """Service for generating AI summaries using OpenAI API"""
    
    def __init__(self, api_key: Optional[str], model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
    
    def is_configured(self) -> bool:
        """Check if OpenAI is properly configured"""
        return bool(self.api_key)
    
    def generate_dimension_summary(
        self,
        dimension_name: str,
        dimension_ref: str,
        samples: List[DimensionData],
        full_analysis: Dict,
        client_name: str = "Client"
    ) -> Dict:
        """
        Generate a summary for a dimension based on sample responses.
        
        Args:
            dimension_name: Human-readable dimension name
            dimension_ref: Technical reference (e.g., "ref_1")
            samples: List of sample responses
            full_analysis: Full dataset analysis with category distribution
            client_name: Client name for context
        
        Returns:
            Dict with summary, key_insights, category_snapshot, patterns, and metadata
        """
        if not self.is_configured():
            raise RuntimeError("OpenAI service is not configured. Set OPENAI_API_KEY.")
        
        # Build the prompt
        prompt = self._build_prompt(
            dimension_name, 
            dimension_ref, 
            samples, 
            full_analysis,
            client_name
        )
        
        try:
            # Use OpenAI API (v1.0+ format)
            from openai import OpenAI
            import httpx
            
            # Create OpenAI client with explicit configuration
            # Avoid proxy issues in Railway environment
            client = OpenAI(
                api_key=self.api_key,
                http_client=httpx.Client(timeout=60.0)
            )
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert customer insights analyst. You specialize in voice-of-customer analysis and always weight your insights by the statistical distribution of topics in the full dataset."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=800
            )
            
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            # Parse the response
            parsed = self._parse_response(content)
            
            return {
                "summary": parsed['summary'],
                "key_insights": parsed['key_insights'],
                "category_snapshot": parsed['category_snapshot'],
                "patterns": parsed['patterns'],
                "tokens_used": tokens_used,
                "model": self.model
            }
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            raise RuntimeError(f"Failed to generate AI summary: {str(e)}")
    
    def execute_prompt(
        self,
        system_message: str,
        user_message: str,
        model: str = None
    ) -> Dict:
        """
        Execute a prompt with system and user messages.
        
        Args:
            system_message: The system prompt message
            user_message: The user input message
            model: LLM model identifier (defaults to self.model)
        
        Returns:
            Dict with content, tokens_used, and model
        """
        if not self.is_configured():
            raise RuntimeError("OpenAI service is not configured. Set OPENAI_API_KEY.")
        
        model_to_use = model or self.model
        
        try:
            # Use OpenAI API (v1.0+ format)
            from openai import OpenAI
            import httpx
            
            # Create OpenAI client with explicit configuration
            # Avoid proxy issues in Railway environment
            client = OpenAI(
                api_key=self.api_key,
                http_client=httpx.Client(timeout=60.0)
            )
            
            # Build request parameters
            request_params = {
                "model": model_to_use,
                "messages": [
                    {
                        "role": "system",
                        "content": system_message
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ]
            }
            
            # Some models don't support certain parameters
            # Models like o1, o1-preview, o1-mini don't support temperature or max_tokens
            # gpt-4o and gpt-4o-mini don't support max_tokens, and may have issues with temperature
            model_lower = model_to_use.lower()
            models_without_params = ['o1', 'o1-preview', 'o1-mini']
            models_without_temperature = ['gpt-4o', 'gpt-4o-mini'] + models_without_params
            models_without_max_tokens = ['gpt-4o', 'gpt-4o-mini'] + models_without_params
            
            # Add temperature for models that support it
            if not any(model_lower.startswith(m) for m in models_without_temperature):
                request_params["temperature"] = 0.7
            
            # Add max_tokens for models that support it
            if not any(model_lower.startswith(m) for m in models_without_max_tokens):
                request_params["max_tokens"] = 4000
            
            # Try the request, and if we get unsupported parameter errors, retry without them
            max_retries = 2
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    response = client.chat.completions.create(**request_params)
                    break  # Success, exit retry loop
                except Exception as e:
                    last_error = e
                    error_str = str(e).lower()
                    
                    # Check for unsupported parameter errors
                    if 'unsupported_parameter' in error_str or 'unsupported_value' in error_str:
                        logger.warning(f"Model {model_to_use} returned unsupported parameter error (attempt {attempt + 1}): {e}")
                        
                        # Remove problematic parameters and retry (check both independently, not elif)
                        removed_any = False
                        if 'max_tokens' in error_str and 'max_tokens' in request_params:
                            logger.info(f"Removing max_tokens parameter for model {model_to_use}")
                            request_params.pop("max_tokens", None)
                            removed_any = True
                        if 'temperature' in error_str and 'temperature' in request_params:
                            logger.info(f"Removing temperature parameter for model {model_to_use}")
                            request_params.pop("temperature", None)
                            removed_any = True
                        
                        # If we couldn't identify the specific parameter but got an unsupported error,
                        # remove all optional parameters
                        if not removed_any:
                            logger.info(f"Removing all optional parameters for model {model_to_use} due to unsupported parameter error")
                            request_params.pop("max_tokens", None)
                            request_params.pop("temperature", None)
                        
                        # Continue to next iteration to retry (if not last attempt)
                        if attempt < max_retries - 1:
                            continue
                        else:
                            # Last attempt failed, raise the error
                            raise
                    else:
                        # Not an unsupported parameter error, don't retry
                        raise
            
            # If we exhausted retries, raise the last error
            if 'response' not in locals():
                raise last_error
            
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            return {
                "content": content,
                "tokens_used": tokens_used,
                "model": model_to_use
            }
            
        except Exception as e:
            logger.error(f"Failed to execute prompt: {e}")
            raise RuntimeError(f"Failed to execute prompt: {str(e)}")
    
    def _build_prompt(
        self,
        dimension_name: str,
        dimension_ref: str,
        samples: List[DimensionData],
        full_analysis: Dict,
        client_name: str
    ) -> str:
        """Build the prompt for OpenAI with topic distribution context"""
        
        total_responses = full_analysis.get('total_responses', len(samples))
        category_dist = full_analysis.get('category_distribution', {})
        top_topics = full_analysis.get('top_topics', [])
        
        # Format category distribution
        category_text = "\n".join([
            f"  - {cat}: {info['count']} responses ({info['percentage']}%)"
            for cat, info in list(category_dist.items())[:8]
        ])
        
        # Format top specific topics
        topics_text = "\n".join([
            f"  - {t['category']} → {t['label']}: {t['count']} ({t['percentage']}%)"
            for t in top_topics[:10]
        ])
        
        # Get top 3 categories for emphasis
        top_3_cats = list(category_dist.keys())[:3]
        top_3_text = ", ".join(top_3_cats) if top_3_cats else "the main categories"
        
        # Format samples (limit to 50 to avoid token limits)
        sample_text = "\n".join([
            f"{i+1}. \"{sample.value}\" [Sentiment: {sample.sentiment or 'unknown'}" + 
            (f", Topics: {', '.join([t.get('category', '') for t in (sample.topics or [])])}" if sample.topics else "") +
            "]"
            for i, sample in enumerate(samples[:50])
        ])
        
        prompt = f"""Analyze customer feedback for "{dimension_name}" from {client_name}.

📊 FULL DATASET CONTEXT (THIS IS CRITICAL):
Total Responses: {total_responses:,}
Sample Size: {len(samples)} (topic-stratified for accuracy)

TOPIC CATEGORY DISTRIBUTION (Full Dataset):
{category_text}

TOP SPECIFIC TOPICS (Full Dataset):
{topics_text}

SAMPLE RESPONSES:
{sample_text}

Provide a concise, insight-rich summary (max 2 short paragraphs) that:

• Reflects the true weighting of the dataset, with emphasis on the top 3 categories (~85%): {top_3_text}
• Captures the core motivations without over-explaining subtopics or long-tail reasons
• Focuses on what matters most statistically, not on anecdotal or rare mentions
• Uses clear, synthesised language rather than enumerating every nuance

Then provide:

1. KEY INSIGHTS (3–5 bullets):
   Actionable insights weighted by category importance (e.g., why certain categories dominate, how they shape purchase intent, what drives the behavior).

2. CATEGORY SNAPSHOT (1 sentence each):
   A crisp line per major category summarising what customers meant.

3. PATTERNS:
   Only the strongest sentiment or behavioural themes — avoid deep dives."""
        
        return prompt
    
    def _parse_response(self, content: str) -> Dict:
        """
        Parse OpenAI response into structured components.
        Extracts summary, key insights, category snapshot, and patterns.
        """
        result = {
            'summary': '',
            'key_insights': [],
            'category_snapshot': {},
            'patterns': ''
        }
        
        # Split content into sections
        sections = content.split('\n\n')
        
        # Find summary (first 1-2 paragraphs before any numbered list)
        summary_parts = []
        for section in sections:
            if section.strip() and not any(marker in section.lower() for marker in ['key insights', 'category snapshot', 'patterns', '1.', '2.', '3.']):
                summary_parts.append(section.strip())
                if len(summary_parts) >= 2:
                    break
        
        result['summary'] = '\n\n'.join(summary_parts) if summary_parts else content[:500]
        
        # Extract key insights (look for bullet points or numbered lists)
        insights_match = re.search(r'KEY INSIGHTS[:\s]*\n(.*?)(?=CATEGORY SNAPSHOT|PATTERNS|$)', content, re.DOTALL | re.IGNORECASE)
        if insights_match:
            insights_text = insights_match.group(1)
            # Extract bullet points
            insights = re.findall(r'[•\-\*]\s*(.+?)(?=\n[•\-\*]|\n\n|$)', insights_text, re.DOTALL)
            result['key_insights'] = [insight.strip() for insight in insights if insight.strip()]
        
        # Extract category snapshot
        snapshot_match = re.search(r'CATEGORY SNAPSHOT[:\s]*\n(.*?)(?=PATTERNS|$)', content, re.DOTALL | re.IGNORECASE)
        if snapshot_match:
            snapshot_text = snapshot_match.group(1)
            # Extract category lines (format: "Category: description")
            categories = re.findall(r'[•\-\*]\s*([^:]+):\s*(.+?)(?=\n[•\-\*]|\n\n|$)', snapshot_text, re.DOTALL)
            result['category_snapshot'] = {cat.strip(): desc.strip() for cat, desc in categories}
        
        # Extract patterns
        patterns_match = re.search(r'PATTERNS[:\s]*\n(.+?)$', content, re.DOTALL | re.IGNORECASE)
        if patterns_match:
            result['patterns'] = patterns_match.group(1).strip()
        
        return result

