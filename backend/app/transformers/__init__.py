"""
Data transformers for converting various data source formats to a common structure.
"""

from typing import List, Dict, Any, Optional
from enum import Enum


class DataSourceType(str, Enum):
    """Supported data source types"""
    INTERCOM_MRT = "intercom_mrt"  # Martin Randall Travel Intercom data
    SURVEY_MULTI_REF = "survey_multi_ref"  # Multi-reference survey data (like Wattbike)
    GENERIC = "generic"  # Generic format


class NormalizedRow:
    """
    Normalized data structure that all formats are converted to.
    This represents a single feedback/conversation item with its associated topics.
    """
    def __init__(
        self,
        row_id: str,
        text: str,
        topics: List[Dict[str, Any]],
        sentiment: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.row_id = row_id
        self.text = text
        self.topics = topics  # List of {label, category, code, sentiment}
        self.sentiment = sentiment
        self.metadata = metadata or {}  # Additional fields like location, date, etc.
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'row_id': self.row_id,
            'text': self.text,
            'topics': self.topics,
            'sentiment': self.sentiment,
            'metadata': self.metadata
        }


class DataTransformer:
    """Base class for data transformers"""
    
    @staticmethod
    def detect_format(data: List[Dict[str, Any]]) -> DataSourceType:
        """
        Detect the format of the data source.
        
        Args:
            data: Raw data array
            
        Returns:
            DataSourceType enum value
        """
        if not data or len(data) == 0:
            return DataSourceType.GENERIC
        
        sample = data[0]
        
        # Check for Intercom MRT format
        if 'text  Topics' in sample and 'text  Text Text' in sample:
            return DataSourceType.INTERCOM_MRT
        
        # Check for multi-ref survey format (has ref_* keys)
        ref_keys = [k for k in sample.keys() if k.startswith('ref_')]
        if ref_keys and isinstance(sample[ref_keys[0]], dict):
            # Verify it has the expected structure
            first_ref = sample[ref_keys[0]]
            if 'text' in first_ref and 'topics' in first_ref:
                return DataSourceType.SURVEY_MULTI_REF
        
        return DataSourceType.GENERIC
    
    @staticmethod
    def transform(data: List[Dict[str, Any]], source_type: Optional[DataSourceType] = None) -> List[Dict[str, Any]]:
        """
        Transform raw data to normalized format.
        
        Args:
            data: Raw data array
            source_type: Optional data source type (will auto-detect if not provided)
            
        Returns:
            List of normalized row dictionaries
        """
        if source_type is None:
            source_type = DataTransformer.detect_format(data)
        
        if source_type == DataSourceType.INTERCOM_MRT:
            return IntercomMRTTransformer.transform(data)
        elif source_type == DataSourceType.SURVEY_MULTI_REF:
            return SurveyMultiRefTransformer.transform(data)
        else:
            # Generic passthrough
            return data


class IntercomMRTTransformer:
    """Transformer for Intercom MRT format"""
    
    @staticmethod
    def transform(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform Intercom MRT format to normalized format.
        
        Structure:
        - Flat rows with "text  Topics", "text  Text Text", "Additional columns *"
        - One conversation per row
        """
        normalized_rows = []
        
        for i, row in enumerate(data):
            # Extract topics
            topics = row.get('text  Topics', [])
            
            # Skip rows with no topics
            if not topics:
                continue
            
            # Create normalized row
            normalized = NormalizedRow(
                row_id=str(row.get('index', i)),
                text=row.get('text  Text Text', ''),
                topics=topics,
                sentiment=row.get('text  Overall Sentiment'),
                metadata={
                    'conversation_id': row.get('Additional columns conversation_id'),
                    'created_at': row.get('Additional columns created_at'),
                    'country': row.get('Additional columns location_country'),
                    'city': row.get('Additional columns location_city'),
                    'browser': row.get('Additional columns browser'),
                    'source_url': row.get('Additional columns source_url'),
                    'manually_reviewed': row.get('text  Overall Manually reviewed', False),
                    'source_type': 'intercom'
                }
            )
            
            normalized_rows.append(normalized.to_dict())
        
        return normalized_rows


class SurveyMultiRefTransformer:
    """Transformer for multi-reference survey format (e.g., Wattbike)"""
    
    @staticmethod
    def transform(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform multi-ref survey format to normalized format.
        
        Structure:
        - Each row has multiple ref_* fields
        - Each ref contains {text, sentiment_overall, topics[]}
        - We flatten this by creating one normalized row per ref
        """
        normalized_rows = []
        
        for i, row in enumerate(data):
            # Extract base row_id
            base_row_id = row.get('row_id', f'row_{i}')
            created_at = row.get('created_at')
            
            # Find all ref_* fields
            ref_keys = [k for k in row.keys() if k.startswith('ref_')]
            
            # Process each ref as a separate response
            for ref_key in ref_keys:
                ref_data = row[ref_key]
                
                # Skip if not a dict or missing required fields
                if not isinstance(ref_data, dict):
                    continue
                
                topics = ref_data.get('topics', [])
                text = ref_data.get('text', '')
                
                # Skip empty responses
                if not topics and not text:
                    continue
                
                # Create normalized row for this ref
                normalized = NormalizedRow(
                    row_id=f"{base_row_id}_{ref_key}",
                    text=text,
                    topics=topics,
                    sentiment=ref_data.get('sentiment_overall'),
                    metadata={
                        'original_row_id': base_row_id,
                        'ref_key': ref_key,
                        'created_at': created_at,
                        'source_type': 'survey'
                    }
                )
                
                normalized_rows.append(normalized.to_dict())
        
        return normalized_rows

