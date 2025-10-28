# Data Format Comparison

This document compares the two different JSON structures in your project to help understand the refactoring changes.

## Format Overview

| Aspect | MRT Intercom Format | Wattbike Survey Format |
|--------|-------------------|----------------------|
| **File** | `rows_MRT - Intercom chats - Topics in order.json` | `Wattbike - Customer Email Survey/rows.json` |
| **Structure** | Flat array with single topics array | Nested with multiple ref_* fields |
| **Use Case** | Customer service conversations | Multi-question survey responses |
| **Responses per Row** | 1 (one conversation) | Multiple (one per question) |

---

## Side-by-Side Comparison

### MRT Intercom Format

```json
{
  "index": 658,
  "Additional columns conversation_id": "215470661559216",
  "Additional columns created_at": "1756994404",
  "Additional columns updated_at": "1760767520",
  "Additional columns subject": "",
  "Additional columns source_url": "https://www.example.com/tours",
  "Additional columns location_city": "Hackney",
  "Additional columns location_region": "England",
  "Additional columns location_country": "United Kingdom",
  "Additional columns contact_id": "68692a26904fe9e1379805b9",
  "Additional columns browser": "chrome",
  "Additional columns browser_version": "138.0.7204.244",
  "Additional columns browser_language": "en",
  "Additional columns os": "Android 9",
  "Additional columns user_message_count": 2.0,
  "Additional columns total_message_count": 2.0,
  
  "text  Text Text": "<p>Trying to pay but OTP number is being sent to phone...</p>",
  
  "text  Topics": [
    {
      "id": "cd_w989lvo",
      "label": "Technical problem",
      "category": "HELP",
      "code": 101,
      "sentiment": null
    }
  ],
  
  "text  Overall Manually reviewed": false,
  "text  Overall Sentiment": "neutral",
  "text  Overall Text is highlighted": false
}
```

**Key Characteristics:**
- **Flat structure** with prefixed fields
- **Single topics array** per row
- **One text field**: `"text  Text Text"`
- **One sentiment**: `"text  Overall Sentiment"`
- All metadata prefixed with `"Additional columns "`

---

### Wattbike Survey Format

```json
{
  "row_id": "ro_dljyv5q",
  "created_at": "2022-03-27 05:14:34.515000+00:00",
  
  "ref_9y4bi": {
    "text": "",
    "sentiment_overall": "neutral",
    "topics": [
      {
        "label": "Atom",
        "category": "ATOM",
        "sentiment": "any",
        "sentiment_label": "",
        "code": 1,
        "id": "cd_w4d82kn"
      }
    ]
  },
  
  "ref_14u6n": {
    "text": "I wanted to get fitter",
    "sentiment_overall": "neutral",
    "topics": [
      {
        "label": "get fitter",
        "category": "TRAINING GOAL",
        "sentiment": "any",
        "sentiment_label": "",
        "code": 124,
        "id": "cd_weg8j3j"
      }
    ]
  },
  
  "ref_ziplt": {
    "text": "Yes",
    "sentiment_overall": "positive",
    "topics": [
      {
        "label": "Yes",
        "category": "YES",
        "sentiment": "any",
        "sentiment_label": "",
        "code": 1,
        "id": "cd_y79jovk"
      }
    ]
  }
}
```

**Key Characteristics:**
- **Nested structure** with `ref_*` fields
- **Multiple responses** per row (one per survey question)
- Each ref has its own:
  - `text` field
  - `sentiment_overall`
  - `topics` array
- Represents multi-question survey with separate answers

---

## Normalized Format (Target)

Both formats are transformed into this common structure:

```json
{
  "row_id": "unique_id",
  "text": "The feedback text",
  "topics": [
    {
      "label": "Topic Label",
      "category": "CATEGORY",
      "code": 123,
      "sentiment": "positive"
    }
  ],
  "sentiment": "neutral",
  "metadata": {
    "country": "United Kingdom",
    "city": "London",
    "created_at": "timestamp",
    "source_type": "intercom"
  }
}
```

---

## Transformation Examples

### MRT → Normalized

**Input (1 row):**
```json
{
  "index": 1,
  "text  Text Text": "What is the price?",
  "text  Topics": [
    {"label": "Pricing", "category": "BOOKING", "code": 30}
  ],
  "text  Overall Sentiment": "neutral",
  "Additional columns location_country": "UK"
}
```

**Output (1 normalized row):**
```json
{
  "row_id": "1",
  "text": "What is the price?",
  "topics": [
    {"label": "Pricing", "category": "BOOKING", "code": 30}
  ],
  "sentiment": "neutral",
  "metadata": {
    "country": "UK",
    "source_type": "intercom"
  }
}
```

**Transformation:**
- `index` → `row_id`
- `"text  Text Text"` → `text`
- `"text  Topics"` → `topics`
- `"text  Overall Sentiment"` → `sentiment`
- All `"Additional columns *"` → `metadata`

---

### Wattbike → Normalized

**Input (1 row with 3 refs):**
```json
{
  "row_id": "ro_abc",
  "created_at": "2022-03-27",
  "ref_q1": {
    "text": "I wanted to get fitter",
    "sentiment_overall": "positive",
    "topics": [{"label": "fitness", "category": "GOAL", "code": 1}]
  },
  "ref_q2": {
    "text": "Yes",
    "sentiment_overall": "positive",
    "topics": [{"label": "Yes", "category": "YES", "code": 2}]
  },
  "ref_q3": {
    "text": "Very satisfied",
    "sentiment_overall": "positive",
    "topics": [{"label": "satisfied", "category": "SATISFACTION", "code": 3}]
  }
}
```

**Output (3 normalized rows):**
```json
[
  {
    "row_id": "ro_abc_ref_q1",
    "text": "I wanted to get fitter",
    "topics": [{"label": "fitness", "category": "GOAL", "code": 1}],
    "sentiment": "positive",
    "metadata": {
      "original_row_id": "ro_abc",
      "ref_key": "ref_q1",
      "created_at": "2022-03-27",
      "source_type": "survey"
    }
  },
  {
    "row_id": "ro_abc_ref_q2",
    "text": "Yes",
    "topics": [{"label": "Yes", "category": "YES", "code": 2}],
    "sentiment": "positive",
    "metadata": {
      "original_row_id": "ro_abc",
      "ref_key": "ref_q2",
      "created_at": "2022-03-27",
      "source_type": "survey"
    }
  },
  {
    "row_id": "ro_abc_ref_q3",
    "text": "Very satisfied",
    "topics": [{"label": "satisfied", "category": "SATISFACTION", "code": 3}],
    "sentiment": "positive",
    "metadata": {
      "original_row_id": "ro_abc",
      "ref_key": "ref_q3",
      "created_at": "2022-03-27",
      "source_type": "survey"
    }
  }
]
```

**Transformation:**
- **1 row becomes 3 rows** (one per ref)
- Each ref's data becomes a separate normalized row
- `row_id` becomes `{original_id}_{ref_key}`
- Each ref's `text`, `topics`, `sentiment_overall` extracted
- Original `row_id` preserved in `metadata.original_row_id`

---

## Key Differences

| Aspect | MRT Format | Wattbike Format | Normalized |
|--------|-----------|----------------|-----------|
| **Rows per original row** | 1 | 1 → N (one per ref) | Variable |
| **Text field** | `"text  Text Text"` | `ref_*.text` | `text` |
| **Topics field** | `"text  Topics"` | `ref_*.topics` | `topics` |
| **Sentiment field** | `"text  Overall Sentiment"` | `ref_*.sentiment_overall` | `sentiment` |
| **Metadata** | Prefixed with `"Additional columns "` | Base row fields | `metadata` object |
| **ID field** | `index` | `row_id` + `ref_key` | `row_id` |

---

## Why This Matters

### Before Refactoring
- Frontend hardcoded to expect MRT format
- Couldn't handle Wattbike or other formats
- Would need separate visualization code for each format

### After Refactoring
- All formats converted to common structure
- Single visualization codebase
- Easy to add new formats
- Original data preserved

---

## Impact on Visualization

### Frontend Changes

**Before (MRT-specific):**
```javascript
const topics = row['text  Topics'] || [];
const text = row['text  Text Text'];
const sentiment = row['text  Overall Sentiment'];
const country = row['Additional columns location_country'];
```

**After (Normalized):**
```javascript
const topics = row.topics || [];
const text = row.text;
const sentiment = row.sentiment;
const country = row.metadata?.country;
```

### Data Processing

**Before:**
- Only worked with MRT format
- Field names hardcoded

**After:**
- Works with any normalized data
- Format-agnostic processing
- Same visualization for all sources

---

## Data Volume Comparison

### Sample File Sizes

| File | Original Rows | Normalized Rows | Ratio |
|------|--------------|-----------------|-------|
| MRT Intercom | ~728 | ~728 | 1:1 |
| Wattbike Survey | ~2,500 | ~7,500+ | ~1:3 |

**Note:** Wattbike creates multiple normalized rows per original row because each ref (survey question) becomes its own row.

---

## Benefits of Normalization

1. **Unified Processing**: Single codebase for all formats
2. **Extensibility**: Easy to add new formats
3. **Clarity**: Clearer field names without prefixes
4. **Flexibility**: Can switch between formats seamlessly
5. **Preservation**: Original data still available for reference

---

## Migration Strategy

1. **Phase 1**: Add transformer system ✓
2. **Phase 2**: Update database schema ✓
3. **Phase 3**: Run migration on existing data
4. **Phase 4**: Update frontend to use normalized data ✓
5. **Phase 5**: Test with both formats

---

## Questions to Consider

1. **Should we preserve the ref_key information?**
   - Yes, stored in `metadata.ref_key` for survey data

2. **How do we handle missing fields?**
   - Use defaults (`''` for text, `'neutral'` for sentiment)

3. **What about new formats?**
   - Create new transformer class following the pattern

4. **Can we go back to raw data?**
   - Yes, `raw_data` is preserved in database

