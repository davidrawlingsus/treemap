# Interactive Hierarchical Treemap Visualization

An interactive treemap visualization for exploring Intercom chat data with drill-down capabilities to verbatims.

## Features

### 📊 **Hierarchical Visualization**
- **Level 1**: Categories (e.g., ACCOMMODATION, GENERAL INFORMATION, BOOKING/PRICE)
- **Level 2**: Specific topics within each category
- **Level 3**: Individual customer verbatims

### 🎨 **Visual Design**
- Modern, clean interface with gradient backgrounds
- Color-coded categories for easy identification
- Responsive grid layout for verbatim cards
- Beautiful card-based UI with hover effects

### 🖱️ **Interactive Features**
- **Click to drill down**: Click any category or topic to explore deeper
- **Breadcrumb navigation**: Easy navigation back to previous levels
- **Hover effects**: Visual feedback on interactive elements
- **Statistics dashboard**: Quick overview of data metrics

### 📝 **Verbatim Display**
- Grid of cards showing individual customer messages
- Sentiment indicators (positive, neutral, negative)
- Location information (city, country)
- Message index for reference

## How to Use

### 1. **Open the Visualization**
Simply open `index.html` in a modern web browser (Chrome, Firefox, Safari, Edge).

### 2. **Navigation**
- **View Categories**: The initial view shows all categories as colored rectangles
- **Drill into Category**: Click any category to see topics within it
- **View Verbatims**: Click a topic to see individual customer messages
- **Navigate Back**: Use the breadcrumb trail at the top to go back to previous levels
- **Return to Root**: Click "All Categories" in breadcrumbs to start over

### 3. **Understanding the Display**

**Treemap View:**
- Rectangle size = number of conversations
- Colors = different categories
- Labels show category/topic names and count

**Verbatim Cards:**
- Full customer message text
- Sentiment badge (colored by sentiment)
- Location information
- Conversation index number

## Technical Details

### Technologies Used
- **D3.js v7**: For treemap layout and data visualization
- **Vanilla JavaScript**: For interaction logic
- **Modern CSS**: For styling and animations

### Data Structure
The visualization processes the JSON data into a three-level hierarchy:

```
Root
├── Category 1
│   ├── Topic A (value: count of verbatims)
│   │   └── [Verbatim 1, Verbatim 2, ...]
│   └── Topic B (value: count of verbatims)
│       └── [Verbatim 1, Verbatim 2, ...]
└── Category 2
    └── Topic C (value: count of verbatims)
        └── [Verbatim 1, Verbatim 2, ...]
```

### Browser Requirements
- Modern browser with ES6+ support
- JavaScript enabled
- SVG support

## Statistics Shown

- **Total Conversations**: Total number of chat records
- **Categories**: Number of unique topic categories
- **Unique Topics**: Number of distinct topics across all categories

## File Structure

```
treemap/
├── index.html                                    # Main visualization file
├── rows_MRT - Intercom chats - Topics in order.json  # Data file
└── README.md                                     # This file
```

## Customization

You can customize the visualization by modifying these variables in `index.html`:

- `width` and `height`: Treemap dimensions
- `colorSchemes`: Color palettes for categories and topics
- Grid layout in `.verbatim-container`: Card layout configuration

## Notes

- The visualization loads data asynchronously
- Large datasets are handled efficiently with D3's treemap algorithm
- Cards are scrollable when verbatim text is long
- Responsive design adapts to different screen sizes

