# Growth Ideas Feature

## Overview

The Growth Ideas feature uses AI (OpenAI GPT) to analyze customer feedback data and generate actionable growth ideas based on specific dimensions (survey questions).

## Architecture

### Database

- **Table:** `growth_ideas`
- **Key Fields:**
  - `client_id` - Associates idea with a client
  - `data_source_id` - Links to the data source
  - `dimension_ref_key` - The dimension (e.g., "ref_1")
  - `idea_text` - The generated idea
  - `status` - pending, accepted, or rejected
  - `priority` - 1 (high), 2 (medium), 3 (low), or null

### Backend API Endpoints

#### Generation
- `POST /api/data-sources/{data_source_id}/dimensions/{ref_key}/generate-ideas`
  - Generates 8 AI-powered ideas based on dimension data
  - Requires data source to have a client_id
  - Stores ideas with status="pending"

#### Management
- `GET /api/data-sources/{data_source_id}/dimensions/{ref_key}/ideas`
  - Fetches all ideas for a dimension
- `PATCH /api/growth-ideas/{idea_id}`
  - Update idea status or priority
- `DELETE /api/growth-ideas/{idea_id}`
  - Delete an idea

#### Client Dashboard
- `GET /api/clients/{client_id}/growth-ideas`
  - Get all ideas for a client (with filtering & sorting)
- `GET /api/clients/{client_id}/growth-ideas/stats`
  - Get summary statistics for client's ideas

### Frontend Components

#### Admin View (index.html)
- **Growth Ideas Panel**: Appears when user clicks on a dimension in the treemap
- **Features:**
  - Generate Ideas button - triggers AI generation
  - Review generated ideas with Accept/Reject buttons
  - Set priority (High/Medium/Low)
  - View count of accepted ideas
  - Link to client's full dashboard

#### Client Dashboard (client-dashboard.html)
- **URL:** `/client-dashboard.html?client_id={uuid}`
- **Features:**
  - Summary statistics (total, accepted, pending, rejected)
  - Filter by status, data source, priority
  - Sort by date or priority
  - Change status and priority
  - Delete ideas

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install openai>=1.0.0
```

### 2. Configure Environment Variables

Add to your `.env` file:

```
OPENAI_API_KEY=sk-...your-api-key...
OPENAI_MODEL=gpt-3.5-turbo  # or gpt-4
OPENAI_MAX_IDEAS=8
```

### 3. Run Database Migration

```bash
cd backend
alembic upgrade head
```

This will create the `growth_ideas` table.

### 4. Restart Backend

```bash
cd backend
uvicorn app.main:app --reload
```

## Usage Workflow

### For Admin/Owner:

1. Select a data source with a client assigned
2. Click on any dimension in the treemap
3. The Growth Ideas panel appears below the treemap
4. Click "Generate Ideas" to create AI-powered suggestions
5. Review each idea and Accept or Reject it
6. Set priorities for accepted ideas
7. Click "View All Ideas Dashboard" to see all ideas for the client

### For Future Users (Multi-tenant):

Users will be automatically directed to their client's dashboard where they can:
- View all ideas across all dimensions/data sources
- Filter and sort ideas
- Manage status and priorities
- Track progress with summary statistics

## Technical Details

### LLM Prompt Strategy

The OpenAI service sends:
- Dimension name and context
- Top 15 representative text responses
- Topic distribution with frequency counts
- Request for specific, actionable growth ideas

The AI is instructed to generate ideas that are:
- Specific and actionable
- Based on patterns in the feedback
- Address real customer needs
- Realistic to implement
- Focused on growth/improvement

### Data Privacy

- Only aggregated/sample data is sent to OpenAI
- No full customer dataset is transmitted
- Generation prompts are stored for audit purposes
- Each idea includes `context_data` with the analysis snapshot

### Error Handling

- API failures are caught and displayed to users
- Rate limits are handled gracefully
- Users can retry generation if it fails
- All errors are logged for debugging

## Future Enhancements

When user management is implemented:
- Add `user_id` field to track who accepted/rejected ideas
- Implement role-based access (users see only their clients)
- Add collaboration features (comments, assignments)
- Email notifications for new ideas
- Export ideas to CSV/PDF

## Multi-Tenant Considerations

- All ideas are scoped to `client_id`
- Future users will only see their assigned client(s)
- API validates client_id matches data_source.client_id
- Dashboard filters ensure proper data isolation
- Admin (you) can access any client's data

## Troubleshooting

### "OpenAI service not configured"
- Ensure `OPENAI_API_KEY` is set in environment variables
- Restart the backend server after adding the key

### "Data source must be associated with a client"
- Assign a client to the data source first
- Use the client selector in the admin view

### Ideas not appearing
- Check browser console for errors
- Verify the dimension has data (ref_key exists)
- Ensure API is running and accessible

### Rate Limiting
- OpenAI has rate limits per API key
- Consider upgrading your OpenAI plan for higher limits
- Ideas are cached in the database after generation

