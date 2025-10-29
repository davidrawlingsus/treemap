# Growth Ideas Feature - Corrected Workflow

## How It Actually Works

### Architecture Understanding

1. **Dimensions = Survey Questions**: Each dimension (ref_1, ref_2, etc.) represents a different survey question in your JSON data
2. **Multiple Dimensions per Data Source**: A single JSON file can contain 10+ survey questions
3. **Dropdown Selection**: Users select which dimension to visualize using dropdowns, not by clicking on the treemap
4. **Treemap Shows ONE Dimension**: The treemap visualizes data for the currently SELECTED dimension

### User Workflow

#### Step 1: Select Client
- Use the **Client dropdown** at the top
- This filters data sources to show only those belonging to the selected client

#### Step 2: Select Data Source  
- Use the **Data Source dropdown**
- This loads the JSON file with all its dimensions

#### Step 3: Select Dimension (Survey Question)
- Use the **Dimension dropdown** (appears after data source loads)
- Options show "All Dimensions" or individual questions (ref_1, ref_2, etc.)
- When you select a specific dimension, the treemap updates to show THAT dimension's data

#### Step 4: Growth Ideas Panel Appears
- **Automatically appears** when you select a specific dimension (not "All Dimensions")
- Panel shows below the treemap
- Initially collapsed - click to expand

#### Step 5: Generate or View Ideas
- **If ideas exist**: They load automatically for this dimension
- **To generate new ideas**: Click "Generate Ideas" button
- **Wait ~10 seconds**: AI analyzes the dimension's feedback data
- **Review ideas**: Accept, reject, or set priorities

#### Step 6: View Master Dashboard
- Click **"View All Ideas Dashboard →"** button
- Opens a new page showing ALL ideas for the entire client
- Filter by dimension, status, priority, or data source

## Technical Flow

### When User Selects Data Source:
```javascript
// 1. Load data source from API
loadDataSource(dataSourceId)
  ↓
// 2. Extract and store client_id
currentClientId = dataSource.client_id
  ↓
// 3. Detect available dimensions
detectAndSetupQuestionFilter()
  ↓
// 4. Show dimension dropdown
```

### When User Selects Dimension:
```javascript
// 1. Dimension dropdown changes
questionSelect.onchange
  ↓
// 2. Store dimension info
currentDimensionRefKey = "ref_1"
currentDimensionName = "Customer Satisfaction" (if named)
  ↓
// 3. Show Growth Ideas panel
showGrowthIdeasPanel()
  ↓
// 4. Load existing ideas for this dimension
loadDimensionIdeas()
  ↓
// 5. Update treemap to show this dimension's data
filterByQuestion(selectedRefKey)
```

### When User Generates Ideas:
```javascript
// 1. Click "Generate Ideas" button
generateGrowthIdeas()
  ↓
// 2. API call to OpenAI service
POST /api/data-sources/{id}/dimensions/{ref_key}/generate-ideas
  ↓
// 3. AI analyzes dimension data:
   - Sample responses (top 15)
   - Topic distribution
   - Frequency patterns
  ↓
// 4. Return 8-15 actionable ideas
  ↓
// 5. Store in database with status="pending"
  ↓
// 6. Display in panel for review
```

## Key Differences from Original Plan

### ❌ What I Initially Got Wrong:
- **Clicking treemap boxes** to select dimensions → This isn't how it works
- **One page per dimension** → Actually one dashboard per client showing all dimensions
- **Ideas attached to treemap clicks** → Ideas are attached to dimension selection

### ✅ How It Actually Works:
- **Dimension dropdown selection** triggers the ideas panel
- **One dashboard per client** with filtering by dimension/data source
- **Ideas stored per dimension** but viewed collectively on client dashboard
- **Panel shows/hides** based on dimension selection state

## Data Relationships

```
Client (e.g., "Acme Corp")
  └── Data Source 1 (e.g., "Q4 2024 Survey")
       ├── Dimension: ref_1 ("Customer Satisfaction")
       │    └── Growth Ideas (5 ideas)
       ├── Dimension: ref_2 ("Product Quality")
       │    └── Growth Ideas (7 ideas)
       └── Dimension: ref_3 ("Support Experience")
            └── Growth Ideas (4 ideas)
  └── Data Source 2 (e.g., "Trustpilot Reviews")
       └── Dimension: ref_1 (only one dimension)
            └── Growth Ideas (6 ideas)

Total ideas for client: 22 ideas
Client Dashboard shows all 22 with filters
```

## UI States

### Panel Hidden:
- No data source selected, OR
- "All Dimensions" view selected

### Panel Visible (Collapsed):
- Specific dimension selected
- Shows count of accepted ideas in badge

### Panel Visible (Expanded):
- User clicked to expand
- Shows:
  - Generate Ideas button
  - List of existing ideas (if any)
  - Accept/Reject buttons
  - Priority dropdowns
  - Link to dashboard

### Panel Loading:
- User clicked "Generate Ideas"
- Shows spinner and "Generating..." message
- Disabled generate button

## Best Practices

1. **Always assign clients to data sources** before generating ideas
2. **Name your dimensions** for better AI context (e.g., "Customer Satisfaction" instead of "ref_1")
3. **Review ideas immediately** after generation while context is fresh
4. **Use priorities** to organize implementation order
5. **Check the dashboard regularly** to track progress across all dimensions

## Future Enhancements

When user management is implemented:
- Users see only their client's data
- Track who accepted/rejected each idea
- Notifications for new ideas
- Collaboration features
- Progress tracking and analytics

