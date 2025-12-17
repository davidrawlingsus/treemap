# Marketably.ai Style Guide - Quick Reference

A condensed reference for maintaining consistent design across domains.

---

## 🎨 Brand Colors

```
Primary Brand: #B9F040 (Lime Green)
Hover State: #a0d636

Backgrounds:
- White: #FFFFFF
- Black: #000000
- Navy: #1A2B3C
- Navy Dark: #0F1B28

Text Colors:
- On Light: Near-black (oklch(0.145 0 0))
- On Dark: White (#FFFFFF)
- Muted: Gray (oklch(0.556 0 0))

Borders:
- Light: oklch(0.922 0 0)
- Dark: rgb(38, 38, 38)
- Accent: rgba(185, 240, 64, 0.3)
```

---

## 🔤 Typography

**Font:** Lato (weights: 300, 400, 700, 900)

```
H1 (Hero): 36px → 60px, weight: 600
H2 (Section): 36px → 60px, weight: 700
H3 (Subsection): 30px → 36px, weight: 600
Body Large: 18px → 20px
Body Regular: 16px
Body Small: 14px
Labels/Buttons: 14px, weight: 600, uppercase
```

---

## 📏 Spacing

```
Base unit: 4px

Common values:
1rem  = 16px  (spacing-4)
1.5rem = 24px  (spacing-6)
2rem  = 32px  (spacing-8)
3rem  = 48px  (spacing-12)
4rem  = 64px  (spacing-16)
6rem  = 96px  (spacing-24)

Section padding:
Mobile: 64px vertical
Tablet: 96px vertical
Desktop: 128px vertical

Max widths:
Standard: 1280px
Narrow: 672px
Wide: 1536px
```

---

## 🎯 Buttons

### Primary (Lime Green)
```css
background: #B9F040;
color: #000000;
padding: 8px 24px;
border-radius: 8px;
font-weight: 600;
text-transform: uppercase;
font-size: 14px;
hover: background #a0d636;
```

### Secondary (White Outline)
```css
border: 2px solid white;
color: white;
background: transparent;
hover: background white, color #1A2B3C;
```

### Pill Shape
```css
border-radius: 9999px;
height: 48px;
padding: 0 24px;
```

**Touch target minimum:** 44x44px

---

## 📝 Forms

### Input Fields
```css
border: 2px solid rgb(212, 212, 212);
padding: 12px 16px;
border-radius: 8px;
font-size: 16px; /* Prevents iOS zoom */
focus: border-color #B9F040;
```

### Labels
```css
font-size: 14px;
font-weight: 500;
margin-bottom: 8px;
```

### Required Fields
Mark with asterisk (*) after label

---

## 🎴 Cards

### Basic Card
```css
background: white;
border: 1px solid border-color;
border-radius: 12px;
padding: 24px;
box-shadow: subtle;
```

### Testimonial Card
```css
background: gradient subtle;
border-radius: 8px;
padding: 32px 40px;
hover: scale(0.98), shadow-xl;
transition: 300ms;
```

### CTA Card
```css
background: gradient from #1A2B3C to #0F1B28;
border: 1px solid rgb(38, 38, 38);
border-radius: 24px;
padding: 48px 64px;
```

---

## 🧭 Navigation

### Header
```css
position: sticky;
top: 0;
z-index: 50;
background: black;
border-bottom: 1px solid rgba(38, 38, 38, 0.5);
padding: 16px 32px;
```

### Nav Links
```css
color: white;
hover: color #B9F040;
transition: 200ms;

Active state:
color: #B9F040;
font-weight: 600;
border-bottom: 2px solid #B9F040;
```

---

## ✨ Animations

### Fade Up (Scroll trigger)
```
initial: opacity 0, translateY 20px
animate: opacity 1, translateY 0
duration: 400-600ms
easing: easeOut
viewport: 30% visible, once
```

### Hover Effects
```css
/* Scale */
transform: scale(0.98);
transition: 300ms ease;

/* Fade */
opacity: 0.8;
transition: 300ms ease;

/* Color */
transition: color 200ms, background 200ms;
```

### Reduced Motion
Always include:
```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## ♿ Accessibility

### Contrast Requirements
- Body text: 4.5:1 minimum
- Large text (18px+): 3:1 minimum
- UI components: 3:1 minimum

### Focus States
```css
outline: 2px solid #B9F040;
outline-offset: 2px;
```

### ARIA Labels
- Add aria-label to icon-only buttons
- Use semantic HTML (nav, main, article, section)
- Proper heading hierarchy (h1 → h2 → h3)
- Alt text for all images

---

## 📱 Responsive Breakpoints

```
Default: 0-639px (Mobile)
sm: 640px (Small tablet)
md: 768px (Tablet)
lg: 1024px (Desktop)
xl: 1280px (Large desktop)
2xl: 1536px (Extra large)
```

Mobile-first approach: style mobile first, add breakpoints for larger screens.

---

## 🎯 Logo Usage

### Standard
```
market (white) + ably (lime green)
Tagline: "Feedback-Fueled Marketing" (lime green, 12px, uppercase, tracked)
```

### Compact
Brand name only (for tight spaces)

### Color Combinations
- Dark background: White + Lime
- Light background: Black + Lime

---

## 📋 Content Guidelines

### Headlines
- Action-oriented
- Sentence case (unless specific styling)
- Highlight key words with lime green

### Body Copy
- Active voice
- Short paragraphs (3-4 sentences)
- Bullet points for lists
- Benefits over features

### CTAs
- Action verbs (Book, Get, Start, Download)
- Specific (not "Click here")
- Create urgency when appropriate

---

## ✅ Quick Checklist

**Before publishing:**
- [ ] Colors match palette
- [ ] Font is Lato
- [ ] Spacing uses 4px grid
- [ ] Buttons have hover states
- [ ] Interactive elements have focus states
- [ ] Images have alt text
- [ ] Forms have labels
- [ ] Animations respect reduced motion
- [ ] Touch targets ≥ 44x44px
- [ ] Color contrast meets WCAG AA

---

## 🔗 Common Code Snippets

### Primary Button
```html
<button class="bg-[#B9F040] text-black px-6 py-3 rounded-lg font-semibold text-sm uppercase hover:bg-[#a0d636] transition-colors">
  ACTION TEXT
</button>
```

### Section Header
```html
<p class="text-sm uppercase tracking-widest text-neutral-300 mb-4">EYEBROW</p>
<h2 class="text-4xl md:text-5xl lg:text-6xl font-bold">
  Headline with <span class="text-[#B9F040]">Accent</span>
</h2>
```

### Input Field
```html
<input type="text" class="w-full px-4 py-3 border-2 border-neutral-300 rounded-lg focus:border-[#B9F040] focus:outline-none" />
```

### Card
```html
<div class="bg-white border border-gray-200 rounded-xl p-6 shadow-sm hover:shadow-lg transition-shadow">
  <!-- Content -->
</div>
```

---

**For full details, see STYLE_GUIDE.md**

