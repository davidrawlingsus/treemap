"""
Standalone script to extract sample data and generate JSON for OpenAI testing.
This file can be deleted after testing - it doesn't modify any existing code.

Usage:
    python test_openai_samples.py --list-clients
    python test_openai_samples.py --client "Wattbike" --list-dimensions
    python test_openai_samples.py --client "Wattbike" --dimension "ref_14u6n" --output samples.json
    python test_openai_samples.py --client "Wattbike" --dimension "ref_14u6n" --format openai
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


class OpenAITester:
    """Extract and format data for OpenAI testing"""
    
    def __init__(self):
        settings = get_settings()
        database_url = settings.get_database_url()
        
        # Replace 'postgresql://' with 'postgresql+psycopg://' to use psycopg3
        if database_url.startswith('postgresql://') and '+psycopg' not in database_url:
            database_url = database_url.replace('postgresql://', 'postgresql+psycopg://')
        
        self.engine = create_engine(database_url)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        
    def list_clients(self):
        """List all available clients"""
        clients = self.db.query(Client).order_by(Client.name).all()
        
        print("\n📊 Available Clients:")
        print("=" * 60)
        for client in clients:
            # Count responses
            count = self.db.query(ProcessVoc).filter(
                or_(
                    ProcessVoc.client_uuid == client.id,
                    ProcessVoc.client_name == client.name
                )
            ).count()
            print(f"  • {client.name} (ID: {client.id}) - {count:,} responses")
        print()
        
    def list_dimensions(self, client_name: str, data_source: Optional[str] = None):
        """List available dimensions for a client"""
        client = self.db.query(Client).filter(
            Client.name.ilike(f"%{client_name}%")
        ).first()
        
        if not client:
            print(f"❌ Client '{client_name}' not found")
            return
        
        print(f"\n📊 Dimensions for {client.name}:")
        print("=" * 60)
        
        query = self.db.query(
            ProcessVoc.dimension_ref,
            ProcessVoc.dimension_name,
            func.count(ProcessVoc.id).label('count')
        ).filter(
            or_(
                ProcessVoc.client_uuid == client.id,
                ProcessVoc.client_name == client.name
            ),
            ProcessVoc.value.isnot(None),
            ProcessVoc.value != ''
        )
        
        if data_source:
            query = query.filter(ProcessVoc.data_source == data_source)
        
        dimensions = query.group_by(
            ProcessVoc.dimension_ref,
            ProcessVoc.dimension_name
        ).order_by(func.count(ProcessVoc.id).desc()).all()
        
        for dim_ref, dim_name, count in dimensions:
            name_display = dim_name or "Unnamed"
            print(f"  • {dim_ref}: {name_display} ({count:,} responses)")
        print()
    
    def extract_samples(
        self,
        client_name: str,
        dimension_ref: str,
        data_source: Optional[str] = None,
        sample_size: int = 100,
        strategy: str = "smart"
    ) -> Optional[Dict]:
        """Extract sample data for testing"""
        
        # Get client
        client = self.db.query(Client).filter(
            Client.name.ilike(f"%{client_name}%")
        ).first()
        
        if not client:
            print(f"❌ Client '{client_name}' not found")
            return None
        
        print(f"\n✓ Found client: {client.name} ({client.id})")
        
        # Build base query
        query = self.db.query(ProcessVoc).filter(
            or_(
                ProcessVoc.client_uuid == client.id,
                ProcessVoc.client_name == client.name
            ),
            ProcessVoc.dimension_ref == dimension_ref,
            ProcessVoc.value.isnot(None),
            ProcessVoc.value != ''
        )
        
        if data_source:
            query = query.filter(ProcessVoc.data_source == data_source)
        
        total_count = query.count()
        print(f"✓ Found {total_count:,} total responses")
        
        if total_count == 0:
            print("❌ No data found with those filters")
            return None
        
        # Get sentiment distribution
        sentiment_dist = self.db.query(
            ProcessVoc.overall_sentiment,
            func.count(ProcessVoc.id).label('count')
        ).filter(
            or_(
                ProcessVoc.client_uuid == client.id,
                ProcessVoc.client_name == client.name
            ),
            ProcessVoc.dimension_ref == dimension_ref,
            ProcessVoc.value.isnot(None),
            ProcessVoc.value != ''
        )
        
        if data_source:
            sentiment_dist = sentiment_dist.filter(ProcessVoc.data_source == data_source)
        
        sentiment_dist = sentiment_dist.group_by(
            ProcessVoc.overall_sentiment
        ).all()
        
        print(f"✓ Sentiment distribution:")
        for sent, count in sentiment_dist:
            print(f"    {sent or 'unknown'}: {count:,} ({count/total_count*100:.1f}%)")
        
        # Sample data using chosen strategy
        if strategy == "smart":
            samples = self._smart_sample(query, sentiment_dist, sample_size, total_count)
        else:
            samples = query.order_by(func.random()).limit(sample_size).all()
        
        print(f"✓ Extracted {len(samples)} samples using '{strategy}' strategy")
        
        # Get dimension name
        dimension_name = samples[0].dimension_name if samples and samples[0].dimension_name else dimension_ref
        
        return {
            "metadata": {
                "client_name": client.name,
                "client_id": str(client.id),
                "dimension_ref": dimension_ref,
                "dimension_name": dimension_name,
                "data_source": data_source or "all",
                "total_responses": total_count,
                "sample_size": len(samples),
                "sampling_strategy": strategy,
                "sentiment_distribution": {
                    str(k) if k else 'unknown': v 
                    for k, v in sentiment_dist
                }
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
    
    def _smart_sample(self, query, sentiment_dist, sample_size, total_count):
        """Smart sampling that balances sentiments proportionally"""
        samples = []
        
        for sentiment, count in sentiment_dist:
            # Calculate proportional sample size
            proportion = count / total_count
            samples_needed = max(1, int(sample_size * proportion))
            
            # Query for this sentiment
            if sentiment is None:
                sentiment_query = query.filter(ProcessVoc.overall_sentiment.is_(None))
            else:
                sentiment_query = query.filter(ProcessVoc.overall_sentiment == sentiment)
            
            # Get samples with variety in length
            all_items = sentiment_query.all()
            
            if len(all_items) <= samples_needed:
                samples.extend(all_items)
            else:
                # Sort by length to get variety
                all_items.sort(key=lambda x: len(x.value or ''))
                step = max(1, len(all_items) // samples_needed)
                selected = all_items[::step][:samples_needed]
                samples.extend(selected)
        
        return samples[:sample_size]
    
    def generate_openai_files(self, data: Dict, output_prefix: str):
        """Generate multiple OpenAI-ready files with different prompt styles"""
        
        # 1. Raw samples JSON
        samples_file = f"{output_prefix}_samples.json"
        with open(samples_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\n✓ Saved raw samples: {samples_file}")
        
        # 2. Simple prompt format
        simple_prompt = self._create_simple_prompt(data)
        simple_file = f"{output_prefix}_prompt_simple.json"
        with open(simple_file, 'w') as f:
            json.dump(simple_prompt, f, indent=2)
        print(f"✓ Saved simple prompt: {simple_file}")
        
        # 3. Detailed prompt format
        detailed_prompt = self._create_detailed_prompt(data)
        detailed_file = f"{output_prefix}_prompt_detailed.json"
        with open(detailed_file, 'w') as f:
            json.dump(detailed_prompt, f, indent=2)
        print(f"✓ Saved detailed prompt: {detailed_file}")
        
        # 4. Structured output prompt
        structured_prompt = self._create_structured_prompt(data)
        structured_file = f"{output_prefix}_prompt_structured.json"
        with open(structured_file, 'w') as f:
            json.dump(structured_prompt, f, indent=2)
        print(f"✓ Saved structured prompt: {structured_file}")
        
        print(f"\n📝 Next steps:")
        print(f"  1. Open https://platform.openai.com/playground")
        print(f"  2. Copy content from any *_prompt_*.json file")
        print(f"  3. Test with different models (gpt-4o, gpt-4o-mini, gpt-3.5-turbo)")
        print(f"  4. Compare quality vs cost")
    
    def _create_simple_prompt(self, data: Dict) -> Dict:
        """Create a simple prompt format"""
        meta = data['metadata']
        
        # Format samples (limit to 50 to avoid token limits)
        sample_text = "\n".join([
            f"{i+1}. \"{s['text']}\""
            for i, s in enumerate(data['samples'][:50])
        ])
        
        user_message = f"""Analyze customer feedback for "{meta['dimension_name']}" from {meta['client_name']}.

Sample: {meta['sample_size']} responses from {meta['total_responses']:,} total.

RESPONSES:
{sample_text}

Provide:
1. Summary (2-3 sentences)
2. 3-5 key insights"""
        
        return {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert at analyzing customer feedback and identifying actionable insights."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
    
    def _create_detailed_prompt(self, data: Dict) -> Dict:
        """Create a detailed prompt with metadata"""
        meta = data['metadata']
        
        # Format samples with metadata (limit to 50)
        sample_text = "\n".join([
            f"{i+1}. \"{s['text']}\" [Sentiment: {s['sentiment']}" + 
            (f", Topics: {', '.join([t.get('category', t.get('label', '')) for t in s['topics']])}" if s['topics'] else "") +
            "]"
            for i, s in enumerate(data['samples'][:50])
        ])
        
        user_message = f"""Analyze customer feedback for "{meta['dimension_name']}" from {meta['client_name']}'s {meta['data_source']}.

CONTEXT:
- Sample: {meta['sample_size']} responses from {meta['total_responses']:,} total
- Sentiment Distribution: {json.dumps(meta['sentiment_distribution'])}
- Sampling Method: {meta['sampling_strategy']} (ensures representative coverage)

RESPONSES:
{sample_text}

Please provide:
1. SUMMARY: A concise overview (2-3 sentences) of the main themes and overall sentiment
2. KEY INSIGHTS: 3-5 specific, actionable insights for the business
3. PATTERNS: Any notable patterns in sentiment or topics"""
        
        return {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert customer experience analyst specializing in voice-of-customer data. Your role is to identify patterns, themes, and actionable insights that help businesses improve their products and services."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            "temperature": 0.7,
            "max_tokens": 600
        }
    
    def _create_structured_prompt(self, data: Dict) -> Dict:
        """Create a prompt that requests structured JSON output"""
        meta = data['metadata']
        
        # Format samples
        sample_text = "\n".join([
            f"{i+1}. \"{s['text']}\" [Sentiment: {s['sentiment']}]"
            for i, s in enumerate(data['samples'][:50])
        ])
        
        user_message = f"""Analyze customer feedback for "{meta['dimension_name']}" from {meta['client_name']}.

Sample: {meta['sample_size']} responses from {meta['total_responses']:,} total

RESPONSES:
{sample_text}

Provide analysis in this JSON format:
{{
  "summary": "2-3 sentence overview",
  "overall_sentiment": "positive/negative/mixed/neutral",
  "key_insights": [
    {{"insight": "specific finding", "priority": "high/medium/low"}},
    ...
  ],
  "themes": ["theme1", "theme2", ...],
  "recommendations": ["actionable recommendation 1", ...]
}}"""
        
        return {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a customer insights analyst. Always respond with valid JSON in the requested format."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            "temperature": 0.7,
            "max_tokens": 600,
            "response_format": {"type": "json_object"}
        }
    
    def close(self):
        """Clean up database connection"""
        self.db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Extract data samples for OpenAI testing"
    )
    parser.add_argument(
        '--list-clients',
        action='store_true',
        help='List all available clients'
    )
    parser.add_argument(
        '--list-dimensions',
        action='store_true',
        help='List dimensions for a client'
    )
    parser.add_argument(
        '--client',
        type=str,
        help='Client name (partial match ok)'
    )
    parser.add_argument(
        '--dimension',
        type=str,
        help='Dimension reference (e.g., ref_14u6n)'
    )
    parser.add_argument(
        '--data-source',
        type=str,
        help='Filter by data source (optional)'
    )
    parser.add_argument(
        '--sample-size',
        type=int,
        default=100,
        help='Number of samples to extract (default: 100)'
    )
    parser.add_argument(
        '--strategy',
        type=str,
        default='smart',
        choices=['smart', 'random'],
        help='Sampling strategy (default: smart)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='openai_test',
        help='Output file prefix (default: openai_test)'
    )
    
    args = parser.parse_args()
    
    tester = OpenAITester()
    
    try:
        if args.list_clients:
            tester.list_clients()
        
        elif args.list_dimensions:
            if not args.client:
                print("❌ --client required when using --list-dimensions")
                return
            tester.list_dimensions(args.client, args.data_source)
        
        elif args.client and args.dimension:
            # Extract samples and generate OpenAI files
            data = tester.extract_samples(
                client_name=args.client,
                dimension_ref=args.dimension,
                data_source=args.data_source,
                sample_size=args.sample_size,
                strategy=args.strategy
            )
            
            if data:
                tester.generate_openai_files(data, args.output)
        
        else:
            parser.print_help()
    
    finally:
        tester.close()


if __name__ == "__main__":
    main()

