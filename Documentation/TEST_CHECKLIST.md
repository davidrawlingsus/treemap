# Multi-Format Testing Checklist

Use this checklist to verify the refactoring works correctly with both data formats.

---

## Pre-Testing Setup

- [ ] Backend dependencies installed (`pip install -r requirements.txt`)
- [ ] Database running and accessible
- [ ] Frontend dependencies installed (`npm install`)
- [ ] Environment variables configured

---

## Step 1: Run Migration (If Existing Data)

```bash
cd backend
python migrate_data_sources.py
```

**Expected Output:**
```
✓ Database columns added/verified
Found X data sources to migrate
Migrating: [name]
  Detected format: [format_type]
  Transformed N raw rows → M normalized rows
  ✓ Migration successful
✓ MIGRATION SUCCESSFUL
```

**Checklist:**
- [ ] Migration script runs without errors
- [ ] All existing data sources migrated
- [ ] Database has new columns (source_format, normalized_data, is_normalized)

---

## Step 2: Backend Unit Tests

### Test 1: Format Detection

```bash
cd backend
python -c "
from app.transformers import DataTransformer, DataSourceType
import json

# Test MRT detection
print('Testing MRT format detection...')
with open('../data_sources/MRT_Intercom/rows_MRT - Intercom chats - Topics in order.json') as f:
    data = json.load(f)[:10]
    detected = DataTransformer.detect_format(data)
    assert detected == DataSourceType.INTERCOM_MRT, f'Expected INTERCOM_MRT, got {detected}'
    print(f'✓ MRT format detected correctly: {detected}')

# Test Wattbike detection
print('\nTesting Wattbike format detection...')
with open('../data_sources/Wattbike - Customer Email Survey/rows.json') as f:
    data = json.load(f)[:10]
    detected = DataTransformer.detect_format(data)
    assert detected == DataSourceType.SURVEY_MULTI_REF, f'Expected SURVEY_MULTI_REF, got {detected}'
    print(f'✓ Wattbike format detected correctly: {detected}')

print('\n✓ All format detection tests passed')
"
```

**Checklist:**
- [ ] MRT format detected as `INTERCOM_MRT`
- [ ] Wattbike format detected as `SURVEY_MULTI_REF`
- [ ] No errors thrown

---

### Test 2: MRT Transformation

```bash
python -c "
from app.transformers import DataTransformer, DataSourceType
import json

print('Testing MRT transformation...')
with open('../data_sources/MRT_Intercom/rows_MRT - Intercom chats - Topics in order.json') as f:
    data = json.load(f)[:5]
    normalized = DataTransformer.transform(data, DataSourceType.INTERCOM_MRT)
    
    print(f'Input rows: {len(data)}')
    print(f'Output rows: {len(normalized)}')
    assert len(normalized) == len(data), 'Row count should be 1:1'
    
    # Check first normalized row
    first = normalized[0]
    assert 'row_id' in first, 'Missing row_id'
    assert 'text' in first, 'Missing text'
    assert 'topics' in first, 'Missing topics'
    assert 'sentiment' in first, 'Missing sentiment'
    assert 'metadata' in first, 'Missing metadata'
    
    print('✓ MRT transformation successful')
    print(f'Sample normalized row keys: {list(first.keys())}')
"
```

**Checklist:**
- [ ] Row count is 1:1 (same number in and out)
- [ ] Normalized structure has all required fields
- [ ] Topics array preserved
- [ ] Metadata extracted correctly

---

### Test 3: Wattbike Transformation

```bash
python -c "
from app.transformers import DataTransformer, DataSourceType
import json

print('Testing Wattbike transformation...')
with open('../data_sources/Wattbike - Customer Email Survey/rows.json') as f:
    data = json.load(f)[:5]
    normalized = DataTransformer.transform(data, DataSourceType.SURVEY_MULTI_REF)
    
    print(f'Input rows: {len(data)}')
    print(f'Output rows: {len(normalized)}')
    assert len(normalized) > len(data), 'Should expand (multiple refs per row)'
    
    # Check structure
    first = normalized[0]
    assert 'row_id' in first, 'Missing row_id'
    assert 'text' in first, 'Missing text'
    assert 'topics' in first, 'Missing topics'
    assert 'metadata' in first, 'Missing metadata'
    assert 'ref_key' in first['metadata'], 'Missing ref_key in metadata'
    
    print('✓ Wattbike transformation successful')
    print(f'Expansion ratio: {len(normalized) / len(data):.2f}x')
"
```

**Checklist:**
- [ ] Row count expands (more normalized rows than input)
- [ ] Each ref creates separate normalized row
- [ ] ref_key preserved in metadata
- [ ] All refs processed

---

## Step 3: API Tests

### Start Backend

```bash
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
```

**Checklist:**
- [ ] Backend starts without errors
- [ ] API available at http://localhost:8000
- [ ] Health check passes: `curl http://localhost:8000/health`

---

### Test 4: Upload MRT Format

```bash
curl -X POST http://localhost:8000/api/data-sources/upload \
  -F "file=@data_sources/MRT_Intercom/rows_MRT - Intercom chats - Topics in order.json" \
  -F "name=MRT Test Upload" \
  -F "auto_detect=true"
```

**Expected Response:**
```json
{
  "id": "...",
  "name": "MRT Test Upload",
  "source_type": "generic",
  "source_format": "intercom_mrt",
  "is_normalized": true,
  "created_at": "...",
  "updated_at": null
}
```

**Checklist:**
- [ ] Upload returns 200 status
- [ ] `source_format` is `"intercom_mrt"`
- [ ] `is_normalized` is `true`
- [ ] Response includes ID

---

### Test 5: Upload Wattbike Format

```bash
curl -X POST http://localhost:8000/api/data-sources/upload \
  -F "file=@data_sources/Wattbike - Customer Email Survey/rows.json" \
  -F "name=Wattbike Test Upload" \
  -F "auto_detect=true"
```

**Expected Response:**
```json
{
  "id": "...",
  "name": "Wattbike Test Upload",
  "source_type": "generic",
  "source_format": "survey_multi_ref",
  "is_normalized": true,
  "created_at": "...",
  "updated_at": null
}
```

**Checklist:**
- [ ] Upload returns 200 status
- [ ] `source_format` is `"survey_multi_ref"`
- [ ] `is_normalized` is `true`
- [ ] Response includes ID

---

### Test 6: Retrieve Data Sources

```bash
# List all sources
curl http://localhost:8000/api/data-sources | jq

# Get specific source (replace ID)
curl http://localhost:8000/api/data-sources/{ID} | jq .raw_data[0]
```

**Checklist:**
- [ ] List endpoint returns all sources
- [ ] Each source has correct format type
- [ ] Get endpoint returns normalized data as `raw_data`
- [ ] Data structure matches normalized format

---

## Step 4: Frontend Tests

### Start Frontend

```bash
# In another terminal
npm start
```

**Checklist:**
- [ ] Frontend starts at http://localhost:3000
- [ ] No console errors on load

---

### Test 7: Data Source Selection

**Actions:**
1. Open http://localhost:3000
2. Check the data source dropdown

**Checklist:**
- [ ] Dropdown shows "Loading..." initially
- [ ] Dropdown populates with available sources
- [ ] Both MRT and Wattbike sources appear
- [ ] First source loads automatically

---

### Test 8: MRT Visualization

**Actions:**
1. Select MRT data source from dropdown
2. Wait for data to load

**Checklist:**
- [ ] Loading indicator appears
- [ ] Loading indicator disappears
- [ ] Treemap renders successfully
- [ ] Categories display with percentages
- [ ] Topics show within categories
- [ ] Colors are distinct
- [ ] No console errors

---

### Test 9: Wattbike Visualization

**Actions:**
1. Select Wattbike data source from dropdown
2. Wait for data to load

**Checklist:**
- [ ] Loading indicator appears
- [ ] Loading indicator disappears
- [ ] Treemap renders successfully
- [ ] Categories display correctly
- [ ] Topics show within categories
- [ ] Data reflects survey structure
- [ ] No console errors

---

### Test 10: Treemap Interaction

**For both data sources:**

**Actions:**
1. Hover over topic rectangles
2. Click on a topic with verbatims

**Checklist:**
- [ ] Hover shows brightness change
- [ ] Click opens verbatims modal
- [ ] Modal shows correct topic name
- [ ] Modal shows correct category
- [ ] Verbatim count is correct
- [ ] Verbatim cards display
- [ ] Sentiment labels show correct colors
- [ ] Location data displays
- [ ] Row IDs display
- [ ] Close button works
- [ ] Clicking backdrop closes modal
- [ ] ESC key closes modal

---

### Test 11: Bar Charts

**For both data sources:**

**Actions:**
1. Scroll to "Topics by Category" chart
2. Click expand (+) on a category
3. Click on a topic

**Checklist:**
- [ ] Chart renders with categories
- [ ] Percentages display
- [ ] Bars animate on load
- [ ] Total count is correct
- [ ] Expand button works
- [ ] Topics show when expanded
- [ ] Collapse button works (−)
- [ ] Clicking topic opens verbatims modal
- [ ] Modal shows correct data

---

### Test 12: All Topics Chart

**For both data sources:**

**Actions:**
1. Scroll to "All Topics" chart
2. Click on a topic

**Checklist:**
- [ ] Chart renders all topics
- [ ] Topics sorted by frequency
- [ ] Percentages display
- [ ] Bars animate
- [ ] Clicking topic opens verbatims
- [ ] Colors match categories

---

### Test 13: Responsiveness (Mobile)

**Actions:**
1. Open browser dev tools
2. Switch to mobile view (375px width)
3. Test all interactions

**Checklist:**
- [ ] Layout adapts to mobile
- [ ] Treemap scales properly
- [ ] Text is readable
- [ ] Charts are usable
- [ ] Modal fills screen
- [ ] Touch interactions work
- [ ] No horizontal scroll

---

### Test 14: Cross-Format Switching

**Actions:**
1. Select MRT source
2. Interact with visualizations
3. Switch to Wattbike source
4. Verify visualization updates
5. Switch back to MRT

**Checklist:**
- [ ] Data switches immediately
- [ ] Visualizations update correctly
- [ ] No data bleeding between sources
- [ ] No console errors during switch
- [ ] State resets properly

---

## Step 5: Data Validation

### Test 15: Data Integrity

**For MRT:**
```bash
# Check row counts match
python -c "
import json

with open('data_sources/MRT_Intercom/rows_MRT - Intercom chats - Topics in order.json') as f:
    raw = json.load(f)
    
# Get from API
import requests
sources = requests.get('http://localhost:8000/api/data-sources').json()
mrt_id = [s['id'] for s in sources if 'MRT' in s['name']][0]
normalized = requests.get(f'http://localhost:8000/api/data-sources/{mrt_id}').json()['raw_data']

print(f'Raw rows: {len(raw)}')
print(f'Normalized rows: {len(normalized)}')
assert len(raw) == len(normalized), 'Row count mismatch!'
print('✓ Row counts match')
"
```

**For Wattbike:**
```bash
# Check expansion ratio
python -c "
import json
import requests

with open('data_sources/Wattbike - Customer Email Survey/rows.json') as f:
    raw = json.load(f)
    
sources = requests.get('http://localhost:8000/api/data-sources').json()
wb_id = [s['id'] for s in sources if 'Wattbike' in s['name']][0]
normalized = requests.get(f'http://localhost:8000/api/data-sources/{wb_id}').json()['raw_data']

print(f'Raw rows: {len(raw)}')
print(f'Normalized rows: {len(normalized)}')
print(f'Expansion: {len(normalized) / len(raw):.2f}x')
assert len(normalized) > len(raw), 'Should have more normalized rows!'
print('✓ Expansion ratio correct')
"
```

**Checklist:**
- [ ] MRT: 1:1 row mapping
- [ ] Wattbike: Correct expansion (1:N)
- [ ] No data loss
- [ ] All topics preserved

---

## Step 6: Performance Tests

### Test 16: Large File Upload

**Actions:**
1. Upload full Wattbike file (~2MB)
2. Time the upload and transformation

**Checklist:**
- [ ] Upload completes in < 5 seconds
- [ ] No timeout errors
- [ ] Transformation successful
- [ ] Backend logs show row counts

---

### Test 17: Visualization Performance

**Actions:**
1. Load large data source
2. Check render time
3. Test interactions

**Checklist:**
- [ ] Treemap renders in < 2 seconds
- [ ] Charts render in < 1 second
- [ ] Interactions are smooth (no lag)
- [ ] Memory usage is reasonable

---

## Step 7: Error Handling

### Test 18: Invalid JSON

```bash
echo "invalid json" > /tmp/invalid.json
curl -X POST http://localhost:8000/api/data-sources/upload \
  -F "file=@/tmp/invalid.json" \
  -F "name=Invalid Test"
```

**Checklist:**
- [ ] Returns 400 error
- [ ] Error message says "Invalid JSON file"

---

### Test 19: Empty File

```bash
echo "[]" > /tmp/empty.json
curl -X POST http://localhost:8000/api/data-sources/upload \
  -F "file=@/tmp/empty.json" \
  -F "name=Empty Test"
```

**Checklist:**
- [ ] Upload succeeds (200)
- [ ] Format detected as GENERIC
- [ ] Frontend handles empty data gracefully

---

### Test 20: Malformed Format

```bash
echo '[{"wrong": "format"}]' > /tmp/malformed.json
curl -X POST http://localhost:8000/api/data-sources/upload \
  -F "file=@/tmp/malformed.json" \
  -F "name=Malformed Test"
```

**Checklist:**
- [ ] Format detected as GENERIC
- [ ] No crash
- [ ] Data stored
- [ ] Frontend handles missing fields

---

## Final Verification

### All Systems Check

- [ ] Backend running without errors
- [ ] Frontend running without errors
- [ ] Database contains all test uploads
- [ ] Both formats visualize correctly
- [ ] Switching between formats works
- [ ] All interactions functional
- [ ] Performance is acceptable
- [ ] Error handling works

---

## Cleanup (Optional)

```bash
# Remove test uploads
curl -X DELETE http://localhost:8000/api/data-sources/{ID}

# Or clean database
psql -d your_database -c "DELETE FROM data_sources WHERE name LIKE '%Test%';"
```

---

## Success Criteria

✅ **All Tests Pass:**
- Format detection works for both types
- Transformation produces correct structure
- API uploads and retrieves data correctly
- Frontend visualizes both formats
- Switching between formats is seamless
- Performance is acceptable
- Error handling is robust

---

## Issues Found

Use this section to track any issues discovered during testing:

### Issue 1:
- **Description:** 
- **Steps to Reproduce:** 
- **Expected:** 
- **Actual:** 
- **Severity:** 
- **Status:** 

---

## Sign-Off

- [ ] Backend tests passed
- [ ] API tests passed
- [ ] Frontend tests passed
- [ ] Performance tests passed
- [ ] Error handling tests passed
- [ ] Cross-format switching tested
- [ ] Ready for production

**Tester:** _______________  
**Date:** _______________  
**Notes:** _______________

