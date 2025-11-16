# 🧪 Test AI Summary Feature - Quick Start

## ✅ Setup Complete!

- ✅ OpenAI package installed
- ✅ Backend server running on http://localhost:8000
- ✅ Frontend ready with slideout panel
- ✅ API endpoint active

## 🎯 Quick Test (5 minutes)

### Step 1: Add Dimension Tracking (One Line of Code)

Find where dimensions are selected in `index.html` and add this line:

**Search for:** Where treemap sections are clicked or dimensions change
**Add:** `window.AIInsightsPanel.setCurrentDimension('ref_14u6n');`

**Common places to check:**
- Treemap click handlers
- Dimension dropdown change events
- URL parameter parsing

**Example:**
```javascript
// When treemap section is clicked
element.addEventListener('click', function() {
    const dimensionRef = this.getAttribute('data-dimension-ref');
    window.AIInsightsPanel.setCurrentDimension(dimensionRef);  // ADD THIS LINE
    // ... rest of your code
});
```

### Step 2: Test It!

1. **Open** http://localhost:3000 (or your dev URL)
2. **Login** with your credentials
3. **Select a client** (e.g., Wattbike)
4. **Click on a treemap section** (this should set the dimension)
5. **Look for the "💡 AI Insights" tab** on the right edge of your screen
6. **Click the tab** to open the slideout panel
7. **Wait 5-10 seconds** for the first generation
8. **Review the summary!**

### Step 3: Test Caching

1. **Close the panel** (click X or press ESC)
2. **Click "💡 AI Insights" again**
3. **Should load instantly** from cache (< 1 second)
4. **Look for "✓ From cache" badge**

## 🐛 Troubleshooting

### "Please select a dimension first"

**Problem:** You haven't added the `setCurrentDimension()` call yet.

**Solution:** Add this line where dimensions are selected:
```javascript
window.AIInsightsPanel.setCurrentDimension(dimensionRef);
```

**Need help finding it?** Look in your browser console - there should be logs showing where dimensions are being selected.

### "No data found for this dimension"

**Problem:** The selected client/dimension doesn't have data in process_voc table.

**Solution:** Try a different dimension that you know has data (like Wattbike's "Initial motivators").

### Panel doesn't open

**Problem:** JavaScript might have an error.

**Solution:** 
1. Open browser console (F12)
2. Look for error messages
3. Check that `window.AIInsightsPanel` exists

Test in console:
```javascript
console.log(window.AIInsightsPanel);  // Should show object
window.AIInsightsPanel.setCurrentDimension('ref_14u6n');  // Test setting dimension
```

### Can't see the tab

**Problem:** CSS might not have loaded or z-index issues.

**Solution:**
1. Refresh the page
2. Check browser console for CSS errors
3. Verify the tab element exists: `document.getElementById('aiInsightsTab')`

## 📊 Testing Checklist

- [ ] Tab visible on right edge of screen
- [ ] Tab opens panel when clicked
- [ ] Panel slides in smoothly from right
- [ ] Loading spinner shows during generation
- [ ] Summary displays after ~5-10 seconds
- [ ] Summary is readable and insightful
- [ ] "✓ From cache" shows on second load
- [ ] Second load is instant (< 1 second)
- [ ] Close button (X) works
- [ ] Overlay click closes panel
- [ ] ESC key closes panel
- [ ] Regenerate button works
- [ ] Error handling works (try invalid dimension)

## 🎨 What You Should See

### First Load (Generated)
```
💡 AI Insights
┌─────────────────────────────────────┐
│ AI-Generated Insights            × │
├─────────────────────────────────────┤
│ 📝 Summary                          │
│ Winter weather avoidance (38%) and │
│ fitness goals (32%) drive the...   │
│                                     │
│ 💡 Key Insights                     │
│ • Winter training dominates...      │
│ • Fitness goals split between...    │
│                                     │
│ 📊 Category Breakdown               │
│ I'M AVOIDING...: Customers seek...  │
│                                     │
│ ✨ Freshly generated                │
│ Generated 11/15/2025 • 542 tokens   │
│ 98 / 946 responses analyzed         │
│                                     │
│ [🔄 Regenerate Insights]            │
└─────────────────────────────────────┘
```

### Second Load (Cached)
```
✓ From cache
Generated 11/15/2025 • 542 tokens
(Same content, but instant load)
```

## 🚀 Next Steps

### If It Works Great:

1. **Commit your changes:**
```bash
git add .
git commit -m "Add AI dimension summary with slideout panel"
git push
```

2. **Deploy to Railway** (auto-deploys on push)

3. **Verify in production:**
   - Railway will run migration automatically
   - OPENAI_API_KEY already set in your .env

### If You Need Help:

1. **Check browser console** for JavaScript errors
2. **Check server logs** for API errors
3. **Test the API directly:**
```bash
# Replace with your actual values
curl "http://localhost:8000/api/dimensions/CLIENTE_UUID/all/ref_14u6n/summary"
```

4. **Check database** to see if summaries are being saved:
```sql
SELECT * FROM dimension_summaries ORDER BY created_at DESC LIMIT 5;
```

## 💰 Cost Tracking

After testing a few dimensions, check costs:

```sql
SELECT 
  COUNT(*) as total_summaries,
  SUM(tokens_used) as total_tokens,
  SUM(tokens_used) * 0.00015 / 1000 as estimated_cost_usd
FROM dimension_summaries;
```

Expected: ~$0.003 per dimension

## 📝 Integration Point

**Remember:** The only thing you need to add is this one line wherever dimensions are selected:

```javascript
window.AIInsightsPanel.setCurrentDimension(dimensionRef);
```

Everything else is already built and ready!

---

**Happy testing!** 🎉 The AI feature is live and ready to use!

