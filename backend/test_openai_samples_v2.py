"""
Enhanced OpenAI testing script with TOPIC-AWARE sampling.
This ensures proper representation of all topic categories in the sample.

Key improvements:
1. Stratified sampling by topics (not just sentiment)
2. Topic distribution included in prompt
3. Explicit guidance to OpenAI about key categories

Usage:
    python test_openai_samples_v2.py --client "Wattbike" --dimension "ref_14u6n" --output test_v2
"""

import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict
import random

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, func, or_
from sqlalchemy.orm import sessionmaker
from app.models.process_voc import ProcessVoc
from app.models.client import Client
from app.config import get_settings


class TopicAwareOpenAITester:
    """Enhanced tester with topic-aware sampling"""
    
    def __init__(self):
        settings = get_settings()
        database_url = settings.get_database_url()
        
        if database_url.startswith('postgresql://') and '+psycopg' not in database_url:
            database_url = database_url.replace('postgresql://', 'postgresql+psycopg://')
        
        self.engine = create_engine(database_url)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
    
    def analyze_full_dataset(self, client_uuid, dimension_ref, data_source=None):
        """Analyze topic distribution in the FULL dataset"""
        
        query = self.db.query(ProcessVoc).filter(
            or_(
                ProcessVoc.client_uuid == client_uuid,
                ProcessVoc.client_name.in_(
                    self.db.query(Client.name).filter(Client.id == client_uuid)
                )
            ),
            ProcessVoc.dimension_ref == dimension_ref,
            ProcessVoc.value.isnot(None),
            ProcessVoc.value != ''
        )
        
        if data_source:
            query = query.filter(ProcessVoc.data_source == data_source)
        
        all_responses = query.all()
        total_count = len(all_responses)
        
        # Analyze topics
        category_counts = defaultdict(int)
        topic_detail_counts = defaultdict(int)
        
        for response in all_responses:
            if response.topics:
                for topic in response.topics:
                    category = topic.get('category', 'Unknown')
                    label = topic.get('label', 'Unknown')
                    category_counts[category] += 1
                    topic_detail_counts[f"{category}::{label}"] += 1
        
        # Sort by frequency
        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        sorted_topics = sorted(topic_detail_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'total_responses': total_count,
            'category_distribution': {
                cat: {'count': count, 'percentage': round(count / total_count * 100, 1)}
                for cat, count in sorted_categories
            },
            'top_topics': [
                {
                    'category': topic.split('::', 1)[0],
                    'label': topic.split('::', 1)[1],
                    'count': count,
                    'percentage': round(count / total_count * 100, 1)
                }
                for topic, count in sorted_topics[:20]
            ],
            'sorted_categories': sorted_categories
        }
    
    def topic_stratified_sample(
        self,
        client_uuid,
        dimension_ref,
        data_source,
        sample_size,
        full_analysis
    ):
        """Sample with topic stratification"""
        
        query = self.db.query(ProcessVoc).filter(
            or_(
                ProcessVoc.client_uuid == client_uuid,
                ProcessVoc.client_name.in_(
                    self.db.query(Client.name).filter(Client.id == client_uuid)
                )
            ),
            ProcessVoc.dimension_ref == dimension_ref,
            ProcessVoc.value.isnot(None),
            ProcessVoc.value != ''
        )
        
        if data_source:
            query = query.filter(ProcessVoc.data_source == data_source)
        
        all_responses = query.all()
        total_count = len(all_responses)
        
        if total_count <= sample_size:
            return all_responses, {}
        
        # Group responses by primary topic category
        category_responses = defaultdict(list)
        
        for response in all_responses:
            if response.topics and len(response.topics) > 0:
                primary_category = response.topics[0].get('category', 'Unknown')
                category_responses[primary_category].append(response)
            else:
                category_responses['NO_TOPIC'].append(response)
        
        # Sample proportionally from each category
        samples = []
        samples_taken_ids = set()
        
        for category, target_count in full_analysis['sorted_categories']:
            if category not in category_responses:
                continue
            
            # Calculate proportional sample size
            proportion = target_count / total_count
            samples_needed = max(1, int(sample_size * proportion))
            
            available = [r for r in category_responses[category] if r.id not in samples_taken_ids]
            
            if not available:
                continue
            
            # Within category, diversify by sentiment and length
            by_sentiment = defaultdict(list)
            for r in available:
                by_sentiment[r.overall_sentiment or 'unknown'].append(r)
            
            category_samples = []
            for sent, responses in by_sentiment.items():
                take = max(1, samples_needed // len(by_sentiment))
                
                if len(responses) <= take:
                    category_samples.extend(responses)
                else:
                    # Sort by length for variety
                    responses.sort(key=lambda x: len(x.value or ''))
                    step = max(1, len(responses) // take)
                    category_samples.extend(responses[::step][:take])
            
            # Add to samples
            for sample in category_samples[:samples_needed]:
                if sample.id not in samples_taken_ids:
                    samples.append(sample)
                    samples_taken_ids.add(sample.id)
        
        # Fill remaining slots if needed
        if len(samples) < sample_size:
            remaining = [r for r in all_responses if r.id not in samples_taken_ids]
            additional = min(sample_size - len(samples), len(remaining))
            samples.extend(random.sample(remaining, additional) if remaining else [])
        
        # Analyze actual sample distribution
        sample_category_counts = defaultdict(int)
        for sample in samples:
            if sample.topics:
                for topic in sample.topics:
                    sample_category_counts[topic.get('category', 'Unknown')] += 1
        
        sample_distribution = {
            cat: {
                'count': count,
                'percentage': round(count / len(samples) * 100, 1)
            }
            for cat, count in sorted(sample_category_counts.items(), key=lambda x: x[1], reverse=True)
        }
        
        return samples[:sample_size], sample_distribution
    
    def extract_samples(self, client_name, dimension_ref, data_source=None, sample_size=100):
        """Extract topic-stratified samples"""
        
        client = self.db.query(Client).filter(Client.name.ilike(f"%{client_name}%")).first()
        
        if not client:
            print(f"❌ Client '{client_name}' not found")
            return None
        
        print(f"\n✓ Found client: {client.name} ({client.id})")
        
        # Analyze full dataset
        print("✓ Analyzing full dataset topic distribution...")
        full_analysis = self.analyze_full_dataset(client.id, dimension_ref, data_source)
        
        print(f"✓ Total responses: {full_analysis['total_responses']:,}")
        print(f"\n📊 FULL DATASET TOPIC DISTRIBUTION:")
        for cat, data in list(full_analysis['category_distribution'].items())[:10]:
            print(f"    {cat:30} {data['count']:5} ({data['percentage']:5.1f}%)")
        
        # Extract topic-stratified sample
        print(f"\n✓ Extracting topic-stratified sample of {sample_size}...")
        samples, sample_dist = self.topic_stratified_sample(
            client.id,
            dimension_ref,
            data_source,
            sample_size,
            full_analysis
        )
        
        print(f"✓ Extracted {len(samples)} samples")
        
        if sample_dist:
            print(f"\n📊 SAMPLE TOPIC DISTRIBUTION:")
            for cat, data in list(sample_dist.items())[:10]:
                print(f"    {cat:30} {data['count']:5} ({data['percentage']:5.1f}%)")
        
        dimension_name = samples[0].dimension_name if samples and samples[0].dimension_name else dimension_ref
        
        # Get sentiment distribution
        sentiment_counts = defaultdict(int)
        for s in samples:
            sentiment_counts[s.overall_sentiment or 'unknown'] += 1
        
        return {
            "metadata": {
                "client_name": client.name,
                "client_id": str(client.id),
                "dimension_ref": dimension_ref,
                "dimension_name": dimension_name,
                "data_source": data_source or "all",
                "total_responses": full_analysis['total_responses'],
                "sample_size": len(samples),
                "sampling_strategy": "topic-stratified",
                "full_dataset_distribution": full_analysis['category_distribution'],
                "sample_distribution": sample_dist,
                "sentiment_distribution": dict(sentiment_counts),
                "top_topics_in_dataset": full_analysis['top_topics'][:10]
            },
            "samples": [
                {
                    "id": s.id,
                    "text": s.value,
                    "sentiment": s.overall_sentiment or "unknown",
                    "topics": s.topics[:3] if s.topics else [],
                    "length": len(s.value) if s.value else 0
                }
                for s in samples
            ]
        }
    
    def generate_enhanced_prompt(self, data: Dict, output_prefix: str):
        """Generate prompt with topic distribution guidance"""
        
        meta = data['metadata']
        
        # Format topic distribution for prompt
        topic_dist_text = "\n".join([
            f"  - {cat}: {info['count']} responses ({info['percentage']}%)"
            for cat, info in list(meta['full_dataset_distribution'].items())[:8]
        ])
        
        # Format top specific topics
        top_topics_text = "\n".join([
            f"  - {t['category']} → {t['label']}: {t['count']} ({t['percentage']}%)"
            for t in meta['top_topics_in_dataset'][:10]
        ])
        
        # Format samples with metadata
        sample_text = "\n".join([
            f"{i+1}. \"{s['text']}\" [Sentiment: {s['sentiment']}" + 
            (f", Topics: {', '.join([t.get('category', '') for t in s['topics']])}" if s['topics'] else "") +
            "]"
            for i, s in enumerate(data['samples'][:50])
        ])
        
        # Get top 3 categories for the prompt
        top_3_cats = list(meta['full_dataset_distribution'].keys())[:3]
        top_3_text = ", ".join(top_3_cats)
        
        user_message = f"""Analyze customer feedback for "{meta['dimension_name']}" from {meta['client_name']}.

📊 FULL DATASET CONTEXT (THIS IS CRITICAL):
Total Responses: {meta['total_responses']:,}
Sample Size: {meta['sample_size']} (topic-stratified for accuracy)

TOPIC CATEGORY DISTRIBUTION (Full Dataset):
{topic_dist_text}

TOP SPECIFIC TOPICS (Full Dataset):
{top_topics_text}

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
        
        prompt = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert customer insights analyst. You specialize in voice-of-customer analysis and always weight your insights by the statistical distribution of topics in the full dataset."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            "temperature": 0.7,
            "max_tokens": 800
        }
        
        # Save files
        samples_file = f"{output_prefix}_samples_v2.json"
        with open(samples_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\n✓ Saved raw samples: {samples_file}")
        
        prompt_file = f"{output_prefix}_prompt_enhanced.json"
        with open(prompt_file, 'w') as f:
            json.dump(prompt, f, indent=2)
        print(f"✓ Saved enhanced prompt: {prompt_file}")
        
        print(f"\n📝 This enhanced prompt includes:")
        print(f"  ✓ Full dataset topic distribution")
        print(f"  ✓ Top 10 specific topics with percentages")
        print(f"  ✓ Explicit instruction to weight by distribution")
        print(f"  ✓ Topic-stratified sample (not just sentiment)")
    
    def close(self):
        self.db.close()


def main():
    parser = argparse.ArgumentParser(description="Topic-aware OpenAI sample extraction")
    parser.add_argument('--client', required=True, help='Client name')
    parser.add_argument('--dimension', required=True, help='Dimension reference')
    parser.add_argument('--data-source', help='Data source filter (optional)')
    parser.add_argument('--sample-size', type=int, default=100, help='Sample size')
    parser.add_argument('--output', default='openai_v2', help='Output prefix')
    
    args = parser.parse_args()
    
    tester = TopicAwareOpenAITester()
    
    try:
        data = tester.extract_samples(
            client_name=args.client,
            dimension_ref=args.dimension,
            data_source=args.data_source,
            sample_size=args.sample_size
        )
        
        if data:
            tester.generate_enhanced_prompt(data, args.output)
    finally:
        tester.close()


if __name__ == "__main__":
    main()

