"""
Dimension Sampler service for creating representative cross-sections of data.
Uses topic-stratified sampling to ensure all major categories are represented.
"""

from typing import List, Tuple, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.models.process_voc import ProcessVoc
from app.models.client import Client
from collections import defaultdict
import random


class DimensionSampler:
    """Service to create representative cross-sections of dimension data"""
    
    @staticmethod
    def extract_with_analysis(
        db: Session,
        client_uuid,
        data_source: str,
        dimension_ref: str,
        sample_size: int = 100
    ) -> Tuple[List[ProcessVoc], int, Dict]:
        """
        Extract topic-stratified samples with full dataset analysis.
        
        Returns:
            Tuple of (samples, total_count, full_analysis)
        """
        
        # Analyze full dataset first
        full_analysis = DimensionSampler._analyze_full_dataset(
            db, client_uuid, data_source, dimension_ref
        )
        
        # Get topic-stratified samples
        samples = DimensionSampler._topic_stratified_sample(
            db, client_uuid, data_source, dimension_ref, 
            sample_size, full_analysis
        )
        
        return samples, full_analysis['total_responses'], full_analysis
    
    @staticmethod
    def _analyze_full_dataset(
        db: Session,
        client_uuid,
        data_source: str,
        dimension_ref: str
    ) -> Dict:
        """Analyze topic distribution in the FULL dataset"""
        
        query = db.query(ProcessVoc).filter(
            or_(
                ProcessVoc.client_uuid == client_uuid,
                ProcessVoc.client_name.in_(
                    db.query(Client.name).filter(Client.id == client_uuid)
                )
            ),
            ProcessVoc.dimension_ref == dimension_ref,
            ProcessVoc.value.isnot(None),
            ProcessVoc.value != ''
        )
        
        if data_source and data_source != 'all':
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
                cat: {'count': count, 'percentage': round(count / total_count * 100, 1) if total_count > 0 else 0}
                for cat, count in sorted_categories
            },
            'top_topics': [
                {
                    'category': topic.split('::', 1)[0],
                    'label': topic.split('::', 1)[1],
                    'count': count,
                    'percentage': round(count / total_count * 100, 1) if total_count > 0 else 0
                }
                for topic, count in sorted_topics[:20]
            ],
            'sorted_categories': sorted_categories
        }
    
    @staticmethod
    def _topic_stratified_sample(
        db: Session,
        client_uuid,
        data_source: str,
        dimension_ref: str,
        sample_size: int,
        full_analysis: Dict
    ) -> List[ProcessVoc]:
        """Sample with topic stratification"""
        
        query = db.query(ProcessVoc).filter(
            or_(
                ProcessVoc.client_uuid == client_uuid,
                ProcessVoc.client_name.in_(
                    db.query(Client.name).filter(Client.id == client_uuid)
                )
            ),
            ProcessVoc.dimension_ref == dimension_ref,
            ProcessVoc.value.isnot(None),
            ProcessVoc.value != ''
        )
        
        if data_source and data_source != 'all':
            query = query.filter(ProcessVoc.data_source == data_source)
        
        all_responses = query.all()
        total_count = len(all_responses)
        
        if total_count <= sample_size:
            return all_responses
        
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
        
        return samples[:sample_size]

