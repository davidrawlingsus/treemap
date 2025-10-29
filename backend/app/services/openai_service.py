import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from collections import Counter
from app.config import get_settings


class OpenAIService:
    """Service for generating growth ideas using OpenAI's GPT models."""
    
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.openai_api_key
        self.model = settings.openai_model or "gpt-3.5-turbo"
        self.max_ideas = settings.openai_max_ideas or 8
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured in settings")
        
        self.client = OpenAI(api_key=self.api_key)
    
    def generate_ideas(
        self,
        dimension_data: List[Dict[str, Any]],
        dimension_name: Optional[str],
        ref_key: str,
        data_source_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate growth ideas based on dimension data.
        
        Args:
            dimension_data: List of normalized data rows for this dimension
            dimension_name: Human-readable name of the dimension
            ref_key: Reference key (e.g., "ref_1")
            data_source_name: Optional name of the data source for context
            
        Returns:
            Dictionary containing:
                - ideas: List of generated idea strings
                - prompt: The prompt that was sent to the LLM
                - context: Summary of the data analyzed
        """
        # Prepare context from the data
        context = self._prepare_context(dimension_data, dimension_name, ref_key)
        
        # Build the prompt
        prompt = self._build_prompt(context, dimension_name, ref_key, data_source_name)
        
        # Call OpenAI API
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a growth strategist and business analyst who specializes in customer feedback analysis and generating actionable insights."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.8,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            content = response.choices[0].message.content
            result = json.loads(content)
            ideas = result.get("ideas", [])
            
            return {
                "ideas": ideas[:self.max_ideas],
                "prompt": prompt,
                "context": context
            }
            
        except Exception as e:
            raise Exception(f"Error calling OpenAI API: {str(e)}")
    
    def generate_topic_specific_ideas(
        self,
        dimension_data: List[Dict[str, Any]],
        dimension_name: Optional[str],
        ref_key: str,
        data_source_name: str,
        topic_name: str,
        category_name: Optional[str] = None,
        max_ideas: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate ideas specifically for a topic/category within a dimension"""
        
        # Filter data to only include rows that mention the topic/category
        filtered_data = []
        for row in dimension_data:
            text = row.get("text", "").lower()
            topics = row.get("topics", [])
            
            # Check if text contains the topic name
            topic_in_text = topic_name.lower() in text
            
            # Check if any topic matches
            topic_in_topics = False
            if topics and isinstance(topics, list):
                for topic in topics:
                    if isinstance(topic, dict):
                        topic_label = topic.get("label") or topic.get("category") or str(topic.get("code", ""))
                        if topic_name.lower() in topic_label.lower():
                            topic_in_topics = True
                            break
                    elif isinstance(topic, str) and topic_name.lower() in topic.lower():
                        topic_in_topics = True
                        break
            
            # Check category if provided
            category_match = True
            if category_name:
                categories = row.get("categories", [])
                if categories and isinstance(categories, list):
                    category_match = any(
                        category_name.lower() in (cat.get("label", "") or str(cat.get("code", ""))).lower()
                        for cat in categories
                        if isinstance(cat, dict)
                    ) or any(
                        category_name.lower() in str(cat).lower()
                        for cat in categories
                        if isinstance(cat, str)
                    )
            
            if (topic_in_text or topic_in_topics) and category_match:
                filtered_data.append(row)
        
        if not filtered_data:
            return {
                "ideas": [],
                "context": {"filtered_count": 0, "original_count": len(dimension_data)},
                "prompt": "",
                "error": f"No data found for topic '{topic_name}'" + (f" in category '{category_name}'" if category_name else "")
            }
        
        # Prepare context from filtered data
        context = self._prepare_context(filtered_data, dimension_name, ref_key)
        context["filtered_count"] = len(filtered_data)
        context["original_count"] = len(dimension_data)
        context["topic_name"] = topic_name
        context["category_name"] = category_name
        
        # Create topic-specific prompt
        scope_description = f"topic '{topic_name}'"
        if category_name:
            scope_description += f" in category '{category_name}'"
        
        prompt = f"""You are a business growth strategist analyzing customer feedback data.

CONTEXT:
- Data Source: {data_source_name}
- Dimension: {dimension_name or ref_key}
- Focus: {scope_description}
- Sample Count: {context['sample_count']} relevant responses
- Top Topics: {', '.join([t['topic'] for t in context['top_topics'][:5]])}

SAMPLE FEEDBACK:
{chr(10).join([f'• {text}' for text in context['sample_texts'][:10]])}

TASK:
Generate {max_ideas or self.max_ideas} specific, actionable growth ideas that directly address the feedback and themes related to {scope_description}.

Focus on:
1. Ideas that specifically address issues mentioned in the {scope_description} feedback
2. Solutions that target the root causes of problems in this area
3. Opportunities to improve the customer experience for this specific topic
4. Strategic initiatives that leverage positive feedback about {scope_description}

Each idea should be:
- Specific to {scope_description}
- Actionable and implementable
- Based on the actual feedback patterns you see
- 1-2 sentences long
- Focused on business growth

Return ONLY a JSON array of idea objects with this exact structure:
[
  {{"idea": "Specific idea text here", "priority": 1}},
  {{"idea": "Another specific idea", "priority": 2}}
]

Priority levels: 1=High, 2=Medium, 3=Low
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.7
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                ideas_data = json.loads(content)
                if not isinstance(ideas_data, list):
                    ideas_data = []
            except json.JSONDecodeError:
                ideas_data = []
            
            # Limit to max_ideas
            ideas_data = ideas_data[:max_ideas or self.max_ideas]
            
            return {
                "ideas": ideas_data,
                "context": context,
                "prompt": prompt
            }
            
        except Exception as e:
            return {
                "ideas": [],
                "context": context,
                "prompt": prompt,
                "error": f"OpenAI API error: {str(e)}"
            }
    
    def _prepare_context(
        self,
        dimension_data: List[Dict[str, Any]],
        dimension_name: Optional[str],
        ref_key: str
    ) -> Dict[str, Any]:
        """
        Prepare a summary context from the dimension data.
        Only uses aggregated/sample data, not full customer details.
        """
        if not dimension_data:
            return {
                "sample_count": 0,
                "sample_texts": [],
                "top_topics": [],
                "dimension_name": dimension_name or ref_key
            }
        
        # Collect sample texts (limit to 15 for context window)
        sample_texts = []
        all_topics = []
        
        for row in dimension_data[:50]:  # Look at first 50 rows
            text = row.get("text", "")
            topics = row.get("topics", [])
            
            if text and len(sample_texts) < 15:
                # Truncate long texts
                sample_texts.append(text[:200])
            
            if topics and isinstance(topics, list):
                # Extract topic labels from topic dictionaries
                for topic in topics:
                    if isinstance(topic, dict):
                        # Try to get label, then category, then code
                        topic_label = topic.get("label") or topic.get("category") or str(topic.get("code", "Unknown"))
                        all_topics.append(topic_label)
                    elif isinstance(topic, str):
                        # If it's already a string, use it directly
                        all_topics.append(topic)
        
        # Get top topics
        topic_counts = Counter(all_topics)
        top_topics = [
            {"topic": topic, "count": count}
            for topic, count in topic_counts.most_common(10)
        ]
        
        return {
            "sample_count": len(dimension_data),
            "sample_texts": sample_texts,
            "top_topics": top_topics,
            "dimension_name": dimension_name or ref_key
        }
    
    def _build_prompt(
        self,
        context: Dict[str, Any],
        dimension_name: Optional[str],
        ref_key: str,
        data_source_name: Optional[str]
    ) -> str:
        """Build the prompt for the LLM."""
        
        dimension_label = dimension_name or ref_key
        source_context = f" from {data_source_name}" if data_source_name else ""
        
        prompt = f"""I have customer feedback data{source_context} for the question/dimension: "{dimension_label}"

CONTEXT:
- Total responses analyzed: {context['sample_count']}
- Representative sample responses (first 15):

"""
        
        # Add sample texts
        for i, text in enumerate(context['sample_texts'], 1):
            prompt += f"{i}. {text}\n"
        
        # Add topic distribution if available
        if context['top_topics']:
            prompt += f"\nTOP THEMES/TOPICS (by frequency):\n"
            for topic_info in context['top_topics']:
                prompt += f"- {topic_info['topic']}: {topic_info['count']} mentions\n"
        
        prompt += f"""

TASK:
Based on this customer feedback, generate {self.max_ideas} specific, actionable growth ideas or business improvements. Each idea should:
1. Be specific and actionable (not generic advice)
2. Be directly based on patterns or themes in the feedback
3. Address real customer needs or pain points
4. Be realistic to implement
5. Focus on driving business growth or improving customer experience

Return your response as a JSON object with this exact structure:
{{
  "ideas": [
    "First specific actionable idea...",
    "Second specific actionable idea...",
    ...
  ]
}}

Each idea should be a complete sentence or two, specific enough to act on.
"""
        
        return prompt


# Singleton instance
_openai_service = None


def get_openai_service() -> OpenAIService:
    """Get or create the OpenAI service singleton."""
    global _openai_service
    if _openai_service is None:
        _openai_service = OpenAIService()
    return _openai_service

