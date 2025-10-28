# Quick Test Guide - Wattbike Format

## Option 1: Automated Test Script (Recommended)

Run the automated test script that checks everything:

```bash
cd /Users/davidrawlings/treemap
./test_wattbike_local.sh
```

This will:
1. ✅ Check backend setup
2. ✅ Test format detection
3. ✅ Test data transformation
4. ✅ Start backend server (if not running)
5. ✅ Upload Wattbike file via API
6. ✅ Verify normalization worked
7. ✅ Start frontend (if not running)

**Expected output:**
```
✓ Format detection: Passed
✓ Data transformation: Passed
✓ API upload: Passed
✓ Data normalization: Passed
✓ All automated tests passed!
```

Then open http://localhost:3000 and select the Wattbike data source.

---

## Option 2: Manual Step-by-Step Test

### Step 1: Start Backend

```bash
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
```

Keep this terminal open.

### Step 2: Test Format Detection (Optional)

In a new terminal:

```bash
cd backend
source venv/bin/activate
python << 'EOF'
from app.transformers import DataTransformer
import json

with open('../data_sources/Wattbike - Customer Email Survey/rows.json') as f:
    data = json.load(f)[:5]
    
format_type = DataTransformer.detect_format(data)
print(f"Detected format: {format_type}")

normalized = DataTransformer.transform(data)
print(f"Input rows: {len(data)}")
print(f"Output rows: {len(normalized)}")
print(f"\nSample normalized row:")
print(f"  row_id: {normalized[0]['row_id']}")
print(f"  text: {normalized[0]['text'][:80]}...")
print(f"  topics: {len(normalized[0]['topics'])} topics")
EOF
```

**Expected output:**
```
Detected format: DataSourceType.SURVEY_MULTI_REF
Input rows: 5
Output rows: 15-20 (varies based on refs per row)
```

### Step 3: Upload Wattbike File

```bash
curl -X POST http://localhost:8000/api/data-sources/upload \
  -F "file=@data_sources/Wattbike - Customer Email Survey/rows.json" \
  -F "name=Wattbike Test" \
  -F "auto_detect=true"
```

**Expected response:**
```json
{
  "id": "...",
  "name": "Wattbike Test",
  "source_format": "survey_multi_ref",
  "is_normalized": true,
  ...
}
```

Copy the `id` from the response.

### Step 4: Verify Data

```bash
# Replace {id} with the ID from step 3
curl http://localhost:8000/api/data-sources/{id} | python -m json.tool | head -50
```

Check that:
- `"is_normalized": true`
- `"source_format": "survey_multi_ref"`
- `"raw_data"` contains normalized format (not original format)

### Step 5: Start Frontend

In another terminal:

```bash
cd /Users/davidrawlings/treemap
npm start
```

### Step 6: Test in Browser

1. Open http://localhost:3000
2. Select "Wattbike Test" from dropdown
3. Verify visualization loads

---

## What to Check in Frontend

### ✅ Data Loads
- [ ] Dropdown shows "Wattbike Test"
- [ ] Loading indicator appears and disappears
- [ ] No console errors

### ✅ Treemap Visualization
- [ ] Categories display correctly
- [ ] Topics show within categories
- [ ] Colors are distinct
- [ ] Percentages visible
- [ ] Hover effects work

### ✅ Bar Charts
- [ ] "Topics by Category" renders
- [ ] "All Topics" renders
- [ ] Percentages display
- [ ] Click to expand categories works

### ✅ Interactions
- [ ] Click topic opens verbatims modal
- [ ] Modal shows conversation text
- [ ] Sentiment labels display
- [ ] Row IDs visible
- [ ] Close button works
- [ ] ESC key closes modal

### ✅ Data Accuracy
- [ ] Topic names make sense (survey responses)
- [ ] Categories appropriate for survey data
- [ ] Verbatim text shows survey answers
- [ ] Counts seem reasonable

---

## Common Issues

### Backend won't start
```bash
# Check if port is in use
lsof -i :8000

# Kill existing process
kill $(lsof -ti :8000)

# Try again
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
```

### Upload fails
- Check backend is running: `curl http://localhost:8000/health`
- Check file path is correct
- Check file is valid JSON: `python -m json.tool < data_sources/Wattbike\ -\ Customer\ Email\ Survey/rows.json | head`

### Frontend shows no data
- Check data source uploaded: `curl http://localhost:8000/api/data-sources`
- Check browser console for errors (F12)
- Verify API is accessible: `curl http://localhost:8000/api/data-sources/{id}`

### Visualization doesn't render
- Open browser console (F12)
- Look for JavaScript errors
- Check network tab for failed requests
- Verify data has `topics` array

---

## Quick Validation Commands

```bash
# Check if backend is running
curl http://localhost:8000/health

# List all data sources
curl http://localhost:8000/api/data-sources | python -m json.tool

# Check specific data source (replace {id})
curl http://localhost:8000/api/data-sources/{id} | python -m json.tool | grep -E "(is_normalized|source_format|row_id|text)" | head -20

# Count normalized rows
curl -s http://localhost:8000/api/data-sources/{id} | python -c "import sys, json; data = json.load(sys.stdin); print(f\"Normalized rows: {len(data['raw_data'])}\")"
```

---

## Cleanup

```bash
# Stop backend (Ctrl+C in backend terminal)

# Or if running in background
kill $(lsof -ti :8000)

# Stop frontend (Ctrl+C in frontend terminal)

# Or if running in background
kill $(lsof -ti :3000)

# Delete test data source (optional)
curl -X DELETE http://localhost:8000/api/data-sources/{id}
```

---

## Compare with MRT Format

To compare how both formats work:

1. Upload MRT data:
```bash
curl -X POST http://localhost:8000/api/data-sources/upload \
  -F "file=@data_sources/MRT_Intercom/rows_MRT - Intercom chats - Topics in order.json" \
  -F "name=MRT Test"
```

2. In frontend, switch between "MRT Test" and "Wattbike Test"
3. Notice the visualizations work identically despite different source formats

---

## Success Criteria

✅ You'll know it's working when:
1. Upload returns `"is_normalized": true`
2. Upload returns `"source_format": "survey_multi_ref"`
3. Frontend dropdown shows your upload
4. Treemap renders with categories and topics
5. Clicking topics shows survey responses
6. No console errors

---

## Next Steps After Testing

Once local testing passes:

1. ✅ Run migration on existing data (if any):
   ```bash
   cd backend
   python migrate_data_sources.py
   ```

2. ✅ Commit changes:
   ```bash
   git add .
   git commit -m "Add multi-format support for survey data"
   ```

3. ✅ Deploy to Railway (or your platform)

4. ✅ Test on production with sample data

---

## Need Help?

- **Format not detected?** Check `FORMAT_COMPARISON.md`
- **Transformation fails?** Check `MULTI_FORMAT_GUIDE.md`
- **API issues?** Check backend logs
- **Frontend issues?** Check browser console (F12)

Test logs are saved to:
- Backend: `backend.log` (if using automated script)
- Frontend: `frontend.log` (if using automated script)

