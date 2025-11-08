# Font Setup Instructions

The header uses the **Lato** font family. Here's how to set it up:

## Option 1: Google Fonts (Recommended)

Add this to your HTML `<head>` section:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Lato:wght@300;400;700;900&display=swap" rel="stylesheet">
```

## Option 2: Import in CSS

Add this to the top of your `globals.css` file:

```css
@import url('https://fonts.googleapis.com/css2?family=Lato:wght@300;400;700;900&display=swap');
```

## CSS Variable

Make sure you have this CSS variable defined (it's already included in `globals.css`):

```css
:root {
  --font-lato: 'Lato', sans-serif;
}
```

## Verify

The header component uses this font via:
```tsx
className="font-[family-name:var(--font-lato)]"
```

After adding the font, the header logo should display with the Lato font family.

