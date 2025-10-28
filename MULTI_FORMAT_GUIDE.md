# Multi-Format Data Source Guide

## Overview

The treemap visualization now supports multiple data source formats through a flexible transformer system. This allows you to upload different JSON structures (e.g., Intercom conversations, survey responses, feedback forms) and have them automatically normalized for visualization.

## Supported Formats

### 1. **Intercom MRT Format** (`intercom_mrt`)

**Structure:**
- Flat array of conversation objects
- Each row has `"text  Topics"` array
- Additional columns prefixed with `"Additional columns "`
- Example: Martin Randall Travel Intercom data

**Sample:**
```json
[
  {
    "index": 1,
    "text  Topics": [
      {"label": "Pricing", "category": "BOOKING", "code": 30, "sentiment": "neutral"}
    ],
    "text  Text Text": "What is the price for the tour?",
    "text  Overall Sentiment": "neutral",
    "Additional columns location_country": "United Kingdom",
    "Additional columns created_at": "1234567890"
  }
]
```

### 2. **Survey Multi-Ref Format** (`survey_multi_ref`)

**Structure:**
- Array of response objects
- Each row has multiple `ref_*` fields (one per question)
- Each ref contains `{text, sentiment_overall, topics[]}`
- Example: Wattbike Customer Email Survey

**Sample:**
```json
[
  {
    "row_id": "ro_abc123",
    "created_at": "2022-03-27 05:14:34.515000+00:00",
    "ref_q1": {
      "text": "I wanted to get fitter",
      "sentiment_overall": "positive",
      "topics": [
        {"label": "get fitter", "category": "TRAINING GOAL", "code": 124}
      ]
    },
    "ref_q2": {
      "text": "Yes, very satisfied",
      "sentiment_overall": "positive",
      "topics": [
        {"label": "Yes", "category": "YES", "code": 1}
      ]
    }
  }
]
```

### 3. **Generic Format** (`generic`)

If your format doesn't match the above, you can still upload it, but you may need to create a custom transformer.

## Normalized Data Format

All formats are transformed into a common normalized structure:

```json
[
  {
    "row_id": "unique_identifier",
    "text": "The feedback text",
    "topics": [
      {
        "label": "Topic Label",
        "category": "CATEGORY_NAME",
        "code": 123,
        "sentiment": "positive"
      }
    ],
    "sentiment": "positive",
    "metadata": {
      "country": "United Kingdom",
      "city": "London",
      "created_at": "1234567890",
      "source_type": "intercom"
    }
  }
]
```

## How It Works

### 1. **Upload Flow**

```
Raw JSON File → Format Detection → Transformation → Normalized Storage → Visualization
```

1. **Upload**: POST `/api/data-sources/upload` with JSON file
2. **Detection**: System auto-detects the format by analyzing structure
3. **Transformation**: Data is converted to normalized format
4. **Storage**: Both raw and normalized data are stored
5. **Visualization**: Frontend uses normalized data

### 2. **Data Transformation**

The transformation happens in `/backend/app/transformers/__init__.py`:

- **`DataTransformer.detect_format()`**: Analyzes data structure to identify format
- **`DataTransformer.transform()`**: Converts to normalized format
- **Format-specific transformers**: Handle each format's unique structure

### 3. **Database Schema**

```sql
CREATE TABLE data_sources (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    source_type VARCHAR(50),          -- Business context (e.g., "intercom", "survey")
    source_format VARCHAR(50),        -- Data structure format (e.g., "intercom_mrt")
    raw_data JSONB,                   -- Original uploaded data
    normalized_data JSONB,            -- Transformed data for visualization
    is_normalized BOOLEAN,            -- Transformation status
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## Usage

### Uploading a Data Source

**Via API:**

```bash
# Auto-detect format (recommended)
curl -X POST http://localhost:8000/api/data-sources/upload \
  -F "file=@data.json" \
  -F "name=My Data Source"

# Specify format explicitly
curl -X POST http://localhost:8000/api/data-sources/upload \
  -F "file=@data.json" \
  -F "name=My Data Source" \
  -F "source_type=survey_multi_ref" \
  -F "auto_detect=false"
```

**Via Frontend:**

The frontend automatically loads available data sources from the API and lets you switch between them using the dropdown selector.

### Retrieving Data

```bash
# List all data sources
GET /api/data-sources

# Get specific data source (returns normalized data by default)
GET /api/data-sources/{id}

# Get raw data
GET /api/data-sources/{id}?use_raw=true
```

## Migration

### Migrating Existing Data

If you have existing data sources in the old format, run the migration script:

```bash
cd backend
python migrate_data_sources.py
```

This script will:
1. Add new columns to the database
2. Detect the format of existing data
3. Transform to normalized format
4. Update all records

## Adding a New Format

To add support for a new data format:

### 1. Add Format to Enum

Edit `/backend/app/transformers/__init__.py`:

```python
class DataSourceType(str, Enum):
    INTERCOM_MRT = "intercom_mrt"
    SURVEY_MULTI_REF = "survey_multi_ref"
    YOUR_NEW_FORMAT = "your_new_format"  # Add here
```

### 2. Create Transformer Class

```python
class YourNewFormatTransformer:
    """Transformer for your new format"""
    
    @staticmethod
    def transform(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized_rows = []
        
        for i, row in enumerate(data):
            # Extract data from your format
            topics = row.get('your_topics_field', [])
            
            # Create normalized row
            normalized = NormalizedRow(
                row_id=str(row.get('id', i)),
                text=row.get('your_text_field', ''),
                topics=topics,
                sentiment=row.get('your_sentiment_field'),
                metadata={
                    'your_custom_field': row.get('custom_data'),
                    'source_type': 'your_source_type'
                }
            )
            
            normalized_rows.append(normalized.to_dict())
        
        return normalized_rows
```

### 3. Update Detection Logic

```python
@staticmethod
def detect_format(data: List[Dict[str, Any]]) -> DataSourceType:
    if not data or len(data) == 0:
        return DataSourceType.GENERIC
    
    sample = data[0]
    
    # Add your detection logic
    if 'your_unique_field' in sample:
        return DataSourceType.YOUR_NEW_FORMAT
    
    # ... other checks
```

### 4. Update Transform Router

```python
@staticmethod
def transform(data: List[Dict[str, Any]], source_type: Optional[DataSourceType] = None):
    # ... existing code ...
    
    elif source_type == DataSourceType.YOUR_NEW_FORMAT:
        return YourNewFormatTransformer.transform(data)
```

## Testing

### Test with Sample Data

```bash
# Test MRT format
curl -X POST http://localhost:8000/api/data-sources/upload \
  -F "file=@data_sources/MRT_Intercom/rows_MRT - Intercom chats - Topics in order.json" \
  -F "name=MRT Intercom Test"

# Test Survey format
curl -X POST http://localhost:8000/api/data-sources/upload \
  -F "file=@data_sources/Wattbike - Customer Email Survey/rows.json" \
  -F "name=Wattbike Survey Test"
```

### Verify in Frontend

1. Open `http://localhost:3000`
2. Select data source from dropdown
3. Verify treemap renders correctly
4. Check bar charts and topic drilldowns
5. Click topics to view verbatims

## Architecture

```
┌─────────────────┐
│   JSON Upload   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│   Format Detection      │
│   (Auto or Manual)      │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│   Data Transformation   │
│   Format → Normalized   │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│   Database Storage      │
│   • raw_data            │
│   • normalized_data     │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│   API Response          │
│   (normalized_data)     │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│   Frontend              │
│   • Treemap             │
│   • Bar Charts          │
│   • Verbatims           │
└─────────────────────────┘
```

## Benefits

1. **Flexibility**: Support multiple data formats without changing visualization code
2. **Maintainability**: Centralized transformation logic
3. **Extensibility**: Easy to add new formats
4. **Backward Compatibility**: Existing visualizations work unchanged
5. **Data Preservation**: Original data is preserved alongside normalized version

## Troubleshooting

### Format Not Detected Correctly

- Check the structure of your JSON file
- Verify it matches one of the supported formats
- Use manual format specification in upload

### Transformation Errors

- Check console logs for detailed error messages
- Verify your data has the required fields
- Test with a small sample first

### Visualization Issues

- Verify normalized data structure in database
- Check browser console for JavaScript errors
- Ensure topics array has required fields (label, category)

## Future Enhancements

- [ ] Support for CSV input with configurable mappings
- [ ] UI for custom format configuration
- [ ] Batch upload of multiple files
- [ ] Data validation and quality checks
- [ ] Format conversion tools
- [ ] Export to different formats

## Questions?

See the main README.md or check the inline code documentation in:
- `/backend/app/transformers/__init__.py`
- `/backend/app/main.py`
- `/frontend/index.html`

