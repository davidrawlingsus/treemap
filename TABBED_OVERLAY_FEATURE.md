# Tabbed Overlay Feature - Ideas Integration

## Overview

The feedback overlay now includes a **tabbed interface** showing both customer feedback and AI-generated growth ideas for the selected topic/category.

## What Changed

### Before
- Click on a topic/category → See only customer feedback in overlay

### After
- Click on a topic/category → See tabbed overlay with:
  - **📝 Feedback Tab**: Customer verbatims (existing functionality)
  - **💡 Ideas Tab**: AI-generated growth ideas filtered for that topic/category

## User Experience

### Step 1: Select Dimension
- Choose Client → Data Source → Dimension from dropdowns
- Generate ideas if you haven't already (scroll down to Growth Ideas panel)

### Step 2: Click on a Topic
- Click any topic/category in the:
  - Treemap visualization
  - Topics by Category chart
  - All Topics chart

### Step 3: View Feedback
- Overlay opens showing the **Feedback** tab by default
- See customer verbatims related to that topic
- Same cards as before (no change to existing UX)

### Step 4: Switch to Ideas Tab
- Click the **💡 Ideas** tab
- See growth ideas filtered for that topic/category
- Ideas displayed in matching card format
- Accept/Reject buttons and priority dropdowns

### Step 5: Manage Ideas
- **Accept/Reject** ideas directly in the overlay
- **Set Priority** (High/Medium/Low) using dropdown
- Changes save immediately
- Ideas update in real-time

## Technical Details

### Idea Filtering Logic

When you click on a topic, the system:

1. **Fetches all ideas** for the current dimension
2. **Filters ideas** that mention:
   - The topic name (e.g., "Contacting for 3rd Party")
   - The category name (e.g., "OTHER BLOCKERS")
   - Related terms (customer, feedback, improve, experience)
3. **Shows filtered ideas** in the Ideas tab
4. **Falls back to all ideas** if no matches found

### Card Styling

Ideas cards match the verbatim card style:
- Same hover effects
- Same rounded corners
- Same spacing and shadows
- Consistent color scheme

### State Management

- **Current context stored**: Topic name, category name, verbatims
- **Tab state persists**: During accept/reject actions
- **Real-time updates**: Ideas reload after status changes
- **Overlay state**: Closes on backdrop click or Escape key

## UI Components

### Tab Navigation
```
┌─────────────────────────────────────┐
│  📝 Feedback  │  💡 Ideas           │
└─────────────────────────────────────┘
```

### Feedback Tab Content
- Customer verbatim cards (existing design)
- Sentiment indicators
- Location data (if available)
- Index numbers

### Ideas Tab Content
- Idea cards with:
  - Status badge (pending/accepted/rejected)
  - Priority badge (if set)
  - Idea text
  - Accept/Reject buttons
  - Priority dropdown
  - Metadata (dimension, date created)

### Empty States
- **No ideas**: "No ideas found for [topic name]"
- **Suggestion**: "Try generating ideas for this dimension first"

## Benefits

1. **Contextual Insights**: See ideas relevant to the specific topic you're analyzing
2. **Side-by-Side**: Compare customer feedback with AI-generated ideas
3. **Quick Actions**: Accept/reject ideas without leaving the overlay
4. **Better UX**: All information in one place, tabbed for clarity
5. **Consistent Design**: Ideas cards match verbatim card styling

## Example Workflow

### Scenario: Analyzing "Contacting for 3rd Party" Topic

1. **Generate Ideas**: First, generate ideas for the dimension
2. **Click Topic**: Click "Contacting for 3rd Party" in visualization
3. **View Feedback**: See 5 customer verbatims about 3rd party contacts
4. **Switch to Ideas**: Click Ideas tab
5. **Review Ideas**: See 3 ideas filtered for this topic:
   - "Implement a dedicated 3rd party inquiry form..."
   - "Add FAQ section explaining 3rd party service..."
   - "Create referral system for 3rd party leads..."
6. **Take Action**: Accept first two ideas, set priority to High
7. **Close**: Ideas saved, ready to view in dashboard

## API Integration

### Endpoint Used
```
GET /api/data-sources/{id}/dimensions/{ref_key}/ideas
```

### Filtering
- Client-side filtering based on topic/category keywords
- Smart matching for related terms
- Fallback to showing all dimension ideas

### Actions
```
PATCH /api/growth-ideas/{id}
- Update status (accepted/rejected)
- Update priority (1=High, 2=Medium, 3=Low)
```

## Future Enhancements

### Potential Improvements:
1. **Generate from overlay**: "Generate ideas for this topic" button
2. **Better filtering**: Use AI to match ideas to topics more intelligently
3. **Idea tagging**: Tag ideas with specific topics/categories
4. **Link to feedback**: Show which verbatims inspired which ideas
5. **Bulk actions**: Accept/reject multiple ideas at once
6. **Export**: Download feedback + ideas for a topic

## Testing Checklist

- [x] Tabs switch correctly
- [x] Feedback tab shows verbatims
- [x] Ideas tab shows filtered ideas
- [x] Accept/Reject buttons work
- [x] Priority dropdowns work
- [x] Empty state displays correctly
- [x] Ideas update in real-time
- [x] Card styling matches verbatims
- [x] Responsive on mobile
- [x] Escape key closes overlay
- [x] Backdrop click closes overlay

## Mobile Responsiveness

- Tabs stack on small screens
- Cards resize appropriately
- Touch-friendly buttons
- Scrollable content areas
- Maintains functionality on all devices

## Browser Compatibility

- ✅ Chrome/Edge (Chromium)
- ✅ Firefox
- ✅ Safari
- ✅ Mobile browsers

## Summary

This feature seamlessly integrates AI-generated growth ideas into your existing workflow. By showing ideas alongside customer feedback in a tabbed interface, you can quickly understand both what customers are saying AND what actions to take, all in one place.

The matching card design ensures a consistent, professional look, while the filtering logic ensures you see the most relevant ideas for each topic you analyze.

