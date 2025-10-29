# Quick Start: Growth Ideas Feature

## 🚀 Get Started in 5 Minutes

### Step 1: Install OpenAI Package
```bash
cd backend
source venv/bin/activate  # or your virtual environment
pip install openai>=1.0.0
```

### Step 2: Set Your OpenAI API Key
Create or update `backend/.env`:
```bash
OPENAI_API_KEY=sk-your-actual-key-here
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_MAX_IDEAS=8
```

### Step 3: Run the Database Migration
```bash
cd backend
alembic upgrade head
```

You should see:
```
INFO  [alembic.runtime.migration] Running upgrade 002 -> 003, add growth ideas table
```

### Step 4: Start the Backend
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 5: Test It Out!

1. Open http://localhost:3000 (or your frontend URL)
2. Select a data source that has a **client assigned**
3. Click on any dimension in the treemap
4. Scroll down to see the "💡 AI Growth Ideas" panel
5. Click "Generate Ideas"
6. Wait ~5-10 seconds for AI to analyze
7. Review the ideas and click Accept/Reject
8. Click "View All Ideas Dashboard" to see the master list

## 🎯 What to Test

### Basic Workflow
- [ ] Generate ideas for one dimension
- [ ] Accept 2-3 ideas
- [ ] Reject 1-2 ideas
- [ ] Set priority on accepted ideas
- [ ] View the client dashboard
- [ ] Filter ideas by status

### Edge Cases
- [ ] Try generating ideas without a client (should show error)
- [ ] Try with an invalid OpenAI key (should show error)
- [ ] Generate ideas for multiple dimensions
- [ ] Check that ideas persist after page reload

## 🔧 Troubleshooting

### Error: "OpenAI service not configured"
**Solution:** Make sure OPENAI_API_KEY is set in your environment:
```bash
cd backend
echo $OPENAI_API_KEY  # Should print your key
```

### Error: "Data source must be associated with a client"
**Solution:** Assign a client to your data source first:
1. Make sure you have a client created
2. When uploading data, associate it with a client
3. Or use the API to update the data_source.client_id

### Ideas Not Showing
**Check:**
1. Browser console for JavaScript errors
2. Backend logs for API errors
3. Network tab to see if API calls are failing
4. Verify the dimension has data (ref_key exists in normalized_data)

### Migration Fails
**If you get a conflict:**
```bash
cd backend
alembic downgrade 002  # Go back one version
alembic upgrade head   # Try again
```

## 📝 Example API Calls

### Generate Ideas (Manual Test)
```bash
# Replace with your actual IDs
curl -X POST "http://localhost:8000/api/data-sources/{data_source_id}/dimensions/ref_1/generate-ideas" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Get Ideas for a Dimension
```bash
curl "http://localhost:8000/api/data-sources/{data_source_id}/dimensions/ref_1/ideas"
```

### Get All Ideas for a Client
```bash
curl "http://localhost:8000/api/clients/{client_id}/growth-ideas?status=accepted&sort_by=priority"
```

## 🎨 UI Features

### Growth Ideas Panel (index.html)
- Appears below treemap when you click a dimension
- Collapsible header to save space
- Generate button with loading state
- Accept/Reject buttons for each idea
- Priority dropdown (High/Medium/Low)
- Link to full dashboard

### Client Dashboard (client-dashboard.html)
- URL: `/client-dashboard.html?client_id={uuid}`
- Statistics cards at the top
- Filter by status, data source, priority
- Sort by date or priority
- Manage all ideas for a client
- Responsive on mobile

## 🌐 Production Deployment

### Railway Setup
1. Add environment variables in Railway dashboard:
   - `OPENAI_API_KEY`
   - `OPENAI_MODEL`
   - `OPENAI_MAX_IDEAS`

2. Push to GitHub:
   ```bash
   git add .
   git commit -m "Add Growth Ideas feature"
   git push origin master
   ```

3. Railway auto-deploys and runs migrations

4. Test on production URL

## 💡 Usage Tips

### Best Practices
1. **Generate for Multiple Dimensions**: Get a comprehensive view of all opportunities
2. **Review Regularly**: Set a weekly time to review and accept ideas
3. **Use Priorities**: High = do now, Medium = do this month, Low = nice to have
4. **Track Implementation**: Mark ideas as rejected once implemented (or add a custom status)

### Prompt Quality
- Ideas are better when dimensions have clear names
- More data = better insights (needs at least 10-15 responses)
- Topic diversity helps generate varied ideas

### Cost Management
- GPT-3.5-turbo: ~$0.001 per dimension
- GPT-4: ~$0.03 per dimension
- Each generation analyzes 15 sample responses
- Consider batching generations during off-hours

## 📚 Learn More

See full documentation:
- `Documentation/GROWTH_IDEAS_FEATURE.md` - Complete feature guide
- `GROWTH_IDEAS_IMPLEMENTATION.md` - Technical implementation details

## ✅ You're Ready!

The feature is fully implemented and ready to use. Just:
1. Set your OpenAI key
2. Run the migration
3. Start generating ideas!

Need help? Check the troubleshooting section or the detailed documentation files.

