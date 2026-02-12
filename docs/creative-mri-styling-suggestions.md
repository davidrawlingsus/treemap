# Creative MRI Styling Suggestions

Comparison of the **Visualizations tab** (prompt engineering slideout) vs **Creative MRI**, with concrete CSS changes to make the MRI feel less "systemy" and more polished.

---

## Reference: What Works Well in Visualizations Tab

The slideout uses these patterns that add polish:

| Element | Current styling |
|--------|------------------|
| **Blockquote / callouts** | `border-left: 4px solid var(--brand-color)`, `background: rgba(185, 240, 64, 0.08)`, `border-radius: 0 6px 6px 0` |
| **Tables** | Header `background: rgba(185, 240, 64, 0.1)`, `border-bottom: 2px solid var(--brand-color)` on th |
| **Content cards** | `box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06)` on idea cards |
| **Code blocks** | `box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08)` |
| **Result content** | `border-radius: 10px`, `border: 1px solid var(--border)` |
| **H1** | `border-bottom: 2px solid var(--brand-color)`, `padding-bottom: 10px` |

---

## Suggested Changes for Creative MRI

### 1. Command Center Sections (Health Summary, Impact Scoreboard)

**Current:** Flat white, thin border  
**Suggested:** Add soft shadow and slight brand accent on header

```css
.command-center-section {
  background: var(--surface, #fff);
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}
.command-center-section h3 {
  margin: 0 0 12px 0;
  font-size: 1rem;
  font-weight: 600;
  padding-bottom: 10px;
  border-bottom: 2px solid var(--brand-color, #b9f040);
}
```

### 2. Health Summary Blocks (Core diagnosis, Key Observations, etc.)

**Current:** Plain paragraphs with minimal separation  
**Suggested:** Match the blockquote/callout style from prompt results

```css
.mri-summary-block {
  margin-bottom: 16px;
  padding: 12px 16px;
  background: rgba(185, 240, 64, 0.06);
  border-left: 4px solid var(--brand-color, #b9f040);
  border-radius: 0 8px 8px 0;
}
.mri-summary-block:last-child {
  margin-bottom: 0;
}
.mri-summary-meta {
  /* Keep as-is but consider a subtle pill/badge feel */
  font-size: 13px;
  color: var(--muted, #718096);
  margin: 0 0 16px 0;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border, #e2e8f0);
}
```

### 3. Impact Scoreboard Cells

**Current:** Flat grey background, sharp corners  
**Suggested:** Soft shadow, subtle hover, brand accent

```css
.impact-scoreboard-cell {
  background: var(--surface, #fff);
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 10px;
  padding: 14px 16px;
  font-size: 13px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
}
.impact-scoreboard-cell:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border-color: rgba(185, 240, 64, 0.4);
}
.impact-scoreboard-cell .mri-action-header strong {
  border-left: 3px solid var(--brand-color, #b9f040);
  padding-left: 8px;
  margin-left: -4px;
}
```

### 4. Chart Containers

**Current:** Plain white card, thin border  
**Suggested:** Add shadow and slightly more padding

```css
.mri-chart {
  background: var(--surface, #fff);
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}
.mri-chart-title {
  margin: 0 0 14px 0;
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text, #1a202c);
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border, #e2e8f0);
}
```

### 5. Bar Charts (Subscores, Hooks, Funnel)

**Current:** Flat fills, no depth  
**Suggested:** Slightly rounded, softer track background

```css
.mri-bar-track {
  flex: 1;
  min-width: 0;
  height: 22px;
  background: var(--bg, #f5f7fb);
  border-radius: 6px;
  overflow: hidden;
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.04);
}
.mri-bar-fill {
  height: 100%;
  border-radius: 6px;
  background: var(--brand-color, #b9f040);
  transition: width 0.3s ease;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
}
.mri-bar-fill--hook {
  background: linear-gradient(135deg, #74c7e8 0%, #5bb8db 100%);
}
.mri-bar-fill--funnel {
  background: linear-gradient(135deg, #6fd4a1 0%, #4ec289 100%);
}
```

### 6. Ad Cards

**Current:** Flat cards with minimal border  
**Suggested:** Match the pe-fb-ad style with subtle shadow

```css
.mri-ad-card {
  background: var(--surface, #fff);
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  transition: box-shadow 0.2s ease;
}
.mri-ad-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
```

### 7. Subheadings

**Current:** Plain text with thin grey underline  
**Suggested:** Match prompt-result-content h4 style

```css
.mri-summary-subheading {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text, #1a202c);
  margin: 0 0 12px 0;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--brand-color, #b9f040);
}
```

### 8. Charts Section Header

**Current:** Bare "Charts" h3  
**Suggested:** Add a subtle accent

```css
.mri-results h3 {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text, #1a202c);
  margin: 0 0 16px 0;
  padding-bottom: 10px;
  border-bottom: 2px solid var(--brand-color, #b9f040);
}
```

### 9. 90-Day Roadmap Cell

**Current:** Same as other cells  
**Suggested:** Slightly different treatment to emphasize it’s a roadmap

```css
.impact-scoreboard-cell.mri-roadmap-cell {
  background: linear-gradient(135deg, rgba(185, 240, 64, 0.08) 0%, rgba(185, 240, 64, 0.03) 100%);
  border-left: 4px solid var(--brand-color, #b9f040);
}
```

---

## Summary

| Change | Effect |
|--------|--------|
| **Soft shadows** | Depth without heaviness |
| **Brand accent** | Left border / underline on headers and callouts |
| **Bar gradients** | Less flat, more modern |
| **Hover states** | Subtle feedback on interactive elements |
| **Rounded corners** | More friendly, less harsh |

These changes align Creative MRI with the existing patterns in the prompt engineering slideout and add a light “CSS touch” without an overhaul.
