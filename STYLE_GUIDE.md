# Marketably.ai Design System & Style Guide

**Version 1.0**  
Last Updated: November 23, 2025

---

## Table of Contents

1. [Brand Identity](#brand-identity)
2. [Color Palette](#color-palette)
3. [Typography](#typography)
4. [Spacing & Layout](#spacing--layout)
5. [Component Patterns](#component-patterns)
6. [Buttons & CTAs](#buttons--ctas)
7. [Forms & Inputs](#forms--inputs)
8. [Cards & Containers](#cards--containers)
9. [Navigation](#navigation)
10. [Animation & Motion](#animation--motion)
11. [Accessibility Guidelines](#accessibility-guidelines)
12. [Best Practices](#best-practices)

---

## Brand Identity

### Brand Name
- **Primary:** `marketably`
- **Stylized:** `market` (white) + `ably` (lime green)
- **Tagline:** "Feedback-Fueled Marketing"

### Brand Voice
- Professional yet approachable
- Data-driven and results-focused
- Customer-centric
- Confident without being aggressive

---

## Color Palette

### Primary Colors

```css
/* Brand Lime Green - Primary Accent */
--brand-lime: #B9F040;
--brand-lime-hover: #a0d636;
--brand-lime-glow: rgba(185, 240, 64, 0.5); /* For glow effects */
```

**Usage:**
- Primary CTAs and important actions
- Brand logo accent
- Key highlights and emphasis
- Active states in navigation
- Success indicators

### Background Colors

```css
/* Light Mode */
--background: oklch(1 0 0);              /* White */
--card: oklch(1 0 0);                    /* White */
--secondary: oklch(0.97 0 0);            /* Light gray */
--muted: oklch(0.97 0 0);                /* Light gray */

/* Dark Mode / Sections */
--background-dark: #000000;              /* Pure black */
--background-navy: #1A2B3C;              /* Dark navy blue */
--background-navy-darker: #0F1B28;       /* Darker navy */
```

**Usage:**
- White backgrounds for main content areas
- Black backgrounds for impact sections (charts, testimonials)
- Navy backgrounds for CTAs and hero cards
- Light gray for subtle sections and muted elements

### Text Colors

```css
/* Light Mode */
--foreground: oklch(0.145 0 0);          /* Near black */
--muted-foreground: oklch(0.556 0 0);    /* Gray text */

/* On Dark Backgrounds */
--text-white: #FFFFFF;
--text-neutral-300: rgb(212, 212, 212);  /* Slightly muted white */
--text-neutral-600: rgb(82, 82, 82);     /* Medium gray */
```

**Usage:**
- Near-black for body text on light backgrounds
- Pure white for text on dark/black backgrounds
- Muted colors for secondary information
- Neutral grays for less important text

### Border & Divider Colors

```css
--border: oklch(0.922 0 0);              /* Light gray border */
--border-dark: rgb(38, 38, 38);          /* Dark mode borders */
--border-accent: rgba(185, 240, 64, 0.3); /* Lime green borders */
```

### Chart Colors

```css
--chart-1: oklch(0.646 0.222 41.116);    /* Orange */
--chart-2: oklch(0.6 0.118 184.704);     /* Teal */
--chart-3: oklch(0.398 0.07 227.392);    /* Blue */
--chart-4: oklch(0.828 0.189 84.429);    /* Yellow-green */
--chart-5: oklch(0.769 0.188 70.08);     /* Yellow */
```

### Utility Colors

```css
--destructive: oklch(0.577 0.245 27.325); /* Red for errors */
--ring: oklch(0.708 0 0);                 /* Focus ring */
--input: oklch(0.922 0 0);                /* Input borders */
```

---

## Typography

### Font Family

```css
/* Primary Font */
--font-lato: 'Lato', sans-serif;

/* Available Weights */
font-weight: 300;  /* Light */
font-weight: 400;  /* Regular */
font-weight: 700;  /* Bold */
font-weight: 900;  /* Black */
```

**Setup:**
```html
<!-- Google Fonts CDN -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Lato:wght@300;400;700;900&display=swap" rel="stylesheet">
```

### Font Sizes & Hierarchy

#### Headlines

```css
/* H1 - Hero/Main Headlines */
font-size: 2.25rem;      /* 36px mobile */
font-size: 3.75rem;      /* 60px desktop */
font-weight: 600;        /* Semibold */
line-height: 1.2;

/* H2 - Section Headlines */
font-size: 2.25rem;      /* 36px mobile */
font-size: 3rem;         /* 48px tablet */
font-size: 3.75rem;      /* 60px desktop */
font-weight: 700;        /* Bold */
line-height: 1.2;

/* H3 - Subsection Headlines */
font-size: 1.875rem;     /* 30px mobile */
font-size: 2.25rem;      /* 36px desktop */
font-weight: 600;        /* Semibold */

/* H4 - Card Headers */
font-size: 1.5rem;       /* 24px */
font-weight: 600;        /* Semibold */
```

#### Body Text

```css
/* Large Body */
font-size: 1.125rem;     /* 18px mobile */
font-size: 1.25rem;      /* 20px desktop */
line-height: 1.5;

/* Regular Body */
font-size: 1rem;         /* 16px */
line-height: 1.5;

/* Small Body */
font-size: 0.875rem;     /* 14px */
line-height: 1.5;
```

#### Labels & UI Text

```css
/* Button Text */
font-size: 0.875rem;     /* 14px */
font-weight: 600;        /* Semibold */
text-transform: uppercase;
letter-spacing: 0.05em;

/* Form Labels */
font-size: 0.875rem;     /* 14px */
font-weight: 500;        /* Medium */

/* Small Labels/Captions */
font-size: 0.75rem;      /* 12px */
text-transform: uppercase;
letter-spacing: 0.1em;
```

### Typography Best Practices

- **Hierarchy:** Always use clear visual hierarchy with size, weight, and color
- **Line Length:** Keep body text between 60-80 characters per line
- **Contrast:** Ensure minimum 4.5:1 contrast ratio for body text
- **Tracking:** Use letter-spacing on uppercase text for readability

---

## Spacing & Layout

### Spacing Scale

```css
/* Base unit: 0.25rem (4px) */
--spacing-1: 0.25rem;    /* 4px */
--spacing-2: 0.5rem;     /* 8px */
--spacing-3: 0.75rem;    /* 12px */
--spacing-4: 1rem;       /* 16px */
--spacing-5: 1.25rem;    /* 20px */
--spacing-6: 1.5rem;     /* 24px */
--spacing-8: 2rem;       /* 32px */
--spacing-10: 2.5rem;    /* 40px */
--spacing-12: 3rem;      /* 48px */
--spacing-16: 4rem;      /* 64px */
--spacing-20: 5rem;      /* 80px */
--spacing-24: 6rem;      /* 96px */
--spacing-32: 8rem;      /* 128px */
```

### Layout Patterns

#### Max Width Containers

```css
/* Standard content width */
max-width: 1280px;       /* 1280px */
padding: 0 1.5rem;       /* 24px mobile */
padding: 0 2rem;         /* 32px desktop */

/* Narrow content (forms, text) */
max-width: 672px;        /* 42rem */

/* Wide content (full sections) */
max-width: 1536px;       /* 96rem */
```

#### Section Spacing

```css
/* Mobile */
padding-top: 4rem;       /* 64px */
padding-bottom: 4rem;    /* 64px */

/* Tablet */
padding-top: 6rem;       /* 96px */
padding-bottom: 6rem;    /* 96px */

/* Desktop */
padding-top: 8rem;       /* 128px */
padding-bottom: 8rem;    /* 128px */
```

#### Grid Patterns

```css
/* Two-column layout */
.grid {
  display: grid;
  grid-template-columns: repeat(1, 1fr);  /* Mobile */
  gap: 3rem;  /* 48px */
}

@media (min-width: 768px) {
  .grid {
    grid-template-columns: repeat(2, 1fr);  /* Tablet+ */
    gap: 4rem;  /* 64px */
  }
}
```

### Border Radius

```css
--radius: 0.625rem;      /* 10px - Base */
--radius-sm: 0.375rem;   /* 6px - Small */
--radius-md: 0.5rem;     /* 8px - Medium */
--radius-lg: 0.625rem;   /* 10px - Large */
--radius-xl: 0.75rem;    /* 12px - Extra Large */
--radius-full: 9999px;   /* Full round (pills/circles) */
```

**Usage:**
- Cards and containers: `--radius-lg` (10px)
- Buttons: `rounded-lg` (8px) or `rounded-full` (pill shape)
- Form inputs: `rounded-lg` (8px)
- Images: `rounded-md` (6px) to `rounded-lg` (10px)

---

## Component Patterns

### Logo

```tsx
// Standard logo implementation
<div className="flex flex-col">
  <Link href="/" className="font-bold text-3xl font-[family-name:var(--font-lato)] hover:opacity-80 transition-opacity">
    <span className="text-white">market</span>
    <span className="text-[#B9F040]">ably</span>
  </Link>
  <span className="text-xs text-[#B9F040] tracking-wide mt-1">
    Feedback-Fueled Marketing
  </span>
</div>
```

**Variations:**
- **Full Logo:** Brand name + tagline
- **Compact Logo:** Brand name only (for smaller spaces)
- **Colors:** White + Lime on dark backgrounds, Black + Lime on light backgrounds

### Section Headers

```tsx
// Standard section header pattern
<div className="mb-16">
  {/* Eyebrow Label */}
  <p className="text-sm uppercase tracking-widest text-neutral-300 mb-4">
    Section Eyebrow Text
  </p>
  
  {/* Main Headline */}
  <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold leading-tight">
    Your Headline with <span className="text-[#B9F040]">Accent</span>
  </h2>
</div>
```

### Social Proof / Logo Clouds

```tsx
// Client logo grid
<div className="grid grid-cols-3 md:grid-cols-6 gap-6 items-center">
  {logos.map((logo, index) => (
    <div
      key={index}
      className="relative h-12 w-full grayscale opacity-60 hover:grayscale-0 hover:opacity-100 transition-all duration-300"
    >
      <img src={logo.src} alt={logo.alt} className="object-contain" />
    </div>
  ))}
</div>
```

**Pattern Notes:**
- Use grayscale by default for unified appearance
- Add hover effects to show color
- Maintain consistent height (48px)
- Use object-contain for aspect ratio preservation

---

## Buttons & CTAs

### Primary Button (Lime Green)

```tsx
<button className="bg-[#B9F040] text-black px-6 py-2 rounded-lg font-semibold text-sm uppercase hover:bg-[#a0d636] transition-colors">
  BUTTON TEXT
</button>
```

**Usage:**
- Primary actions (Book a call, Submit forms, Main CTAs)
- Maximum one primary button per section
- High contrast against dark backgrounds

### Secondary Button (White Outline)

```tsx
<button className="border-2 border-white text-white px-6 py-2 rounded-lg font-semibold text-sm uppercase hover:bg-white hover:text-[#1A2B3C] transition-colors">
  BUTTON TEXT
</button>
```

**Usage:**
- Secondary actions
- Alternative options when primary CTA is present
- Best on dark backgrounds

### Tertiary Button (Outline on Light)

```tsx
<button className="border-2 border-neutral-300 text-neutral-700 px-6 py-2 rounded-lg font-semibold hover:border-neutral-400 hover:text-neutral-900 transition-colors">
  Button Text
</button>
```

**Usage:**
- Tertiary actions on light backgrounds
- Less emphasis than primary/secondary
- Good for "Learn more" or "View details"

### Pill-Shaped Buttons

```tsx
<button className="px-6 h-12 rounded-full font-semibold bg-[#B9F040] text-black hover:bg-[#a0d636] transition-colors">
  Button Text
</button>
```

**Usage:**
- Hero sections
- Modern, friendly appearance
- Better for shorter text

### Button States

```css
/* Default */
background: #B9F040;
color: #000000;

/* Hover */
background: #a0d636;
transform: none; /* Subtle or no transform */

/* Active/Pressed */
background: #90c026;

/* Disabled */
opacity: 0.5;
cursor: not-allowed;
pointer-events: none;

/* Focus (Accessibility) */
outline: 2px solid #B9F040;
outline-offset: 2px;
```

### Button Size Variants

```css
/* Small */
padding: 0.5rem 1rem;    /* 8px 16px */
font-size: 0.875rem;     /* 14px */
height: 36px;

/* Medium (Default) */
padding: 0.5rem 1.5rem;  /* 8px 24px */
font-size: 0.875rem;     /* 14px */
height: 40px;

/* Large */
padding: 0.75rem 2rem;   /* 12px 32px */
font-size: 1rem;         /* 16px */
height: 48px;
```

### Button Best Practices

- **Text:** Use action-oriented text (Book, Get, Start, Download)
- **Case:** Use uppercase for emphasis, sentence case for friendlier tone
- **Icons:** Add arrow icons for navigation/forward actions
- **Loading States:** Show spinner and "Loading..." text during async actions
- **Mobile:** Ensure minimum 44x44px touch target

---

## Forms & Inputs

### Text Input

```tsx
<input
  type="text"
  className="w-full px-4 py-3 text-base bg-white border-2 border-neutral-300 rounded-lg text-black placeholder:text-neutral-400 focus:border-[#B9F040] focus:outline-none transition-colors"
  placeholder="Placeholder text"
/>
```

**Specifications:**
- Border: 2px solid, neutral-300
- Focus state: Border changes to lime green (#B9F040)
- Padding: 16px horizontal, 12px vertical
- Border radius: 8px (rounded-lg)
- Font size: 16px (prevents zoom on mobile)

### Select Dropdown

```tsx
<select
  className="w-full px-4 py-3 text-base bg-white border-2 border-neutral-300 rounded-lg text-black focus:border-[#B9F040] focus:outline-none transition-colors"
>
  <option value="">Select an option...</option>
  <option value="1">Option 1</option>
</select>
```

### Textarea

```tsx
<textarea
  rows={4}
  className="w-full px-4 py-3 text-base bg-white border-2 border-neutral-300 rounded-lg text-black placeholder:text-neutral-400 focus:border-[#B9F040] focus:outline-none transition-colors resize-none"
  placeholder="Your message..."
/>
```

### Form Label

```tsx
<label htmlFor="input-id" className="block text-sm font-medium mb-2 text-black">
  Label Text *
</label>
```

**Best Practices:**
- Always include labels (use aria-label if hidden visually)
- Mark required fields with asterisk (*)
- Use placeholder text as examples, not labels
- Show validation errors below inputs
- Use 16px font size minimum to prevent zoom on iOS

### Input States

```css
/* Default */
border: 2px solid rgb(212, 212, 212);

/* Focus */
border: 2px solid #B9F040;
outline: none;

/* Error */
border: 2px solid oklch(0.577 0.245 27.325);

/* Disabled */
opacity: 0.5;
cursor: not-allowed;
background: rgb(250, 250, 250);
```

### Form Layout

```tsx
// Two-column form layout
<div className="grid md:grid-cols-2 gap-4">
  <div>
    <label>First Name</label>
    <input type="text" />
  </div>
  <div>
    <label>Last Name</label>
    <input type="text" />
  </div>
</div>

// Full-width field
<div>
  <label>Email Address</label>
  <input type="email" className="w-full" />
</div>
```

---

## Cards & Containers

### Basic Card

```tsx
<div className="bg-white border border-border rounded-xl p-6 shadow-sm">
  {/* Card content */}
</div>
```

### Testimonial Card

```tsx
<div className="h-[280px] md:h-[320px] w-[309px] md:w-[525px] rounded-md bg-gradient-to-br from-primary/5 to-accent/5 border border-border px-6 py-8 md:p-10 transition-all duration-300 hover:scale-[0.98] hover:shadow-xl cursor-pointer">
  <p className="text-xl md:text-2xl lg:text-3xl leading-[140%] tracking-tight">
    "{quote}"
  </p>
  
  <div className="flex items-center gap-6 mt-8">
    <div className="h-16 w-16 md:h-20 md:w-20 rounded-full overflow-hidden bg-white border-2 border-border">
      <img src={imageSrc} alt={name} className="object-contain" />
    </div>
    <div>
      <p className="font-semibold text-base md:text-lg">{name}</p>
      <p className="text-sm md:text-base font-medium text-muted-foreground">{company}</p>
    </div>
  </div>
</div>
```

### CTA Card (Dark Background)

```tsx
<div className="rounded-3xl bg-gradient-to-br from-[#1A2B3C] to-[#0F1B28] border border-neutral-800 p-8 md:p-12 lg:p-16">
  <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold text-white">
    Headline
  </h2>
  <p className="text-lg md:text-xl text-neutral-300 mt-4">
    Supporting text
  </p>
  {/* CTA Button */}
</div>
```

### Card Patterns

**Hover Effects:**
```css
/* Subtle scale on hover */
transition: all 0.3s ease;
hover: scale-[0.98];
hover: shadow-xl;

/* Gradient overlay on hover */
hover: bg-gradient-to-br from-primary/5 to-transparent;
```

**Shadows:**
```css
/* Subtle shadow */
box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);

/* Medium shadow */
box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);

/* Large shadow */
box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1);
```

---

## Navigation

### Header/Navigation Bar

```tsx
<nav className="sticky top-0 z-50 bg-black px-4 lg:px-8 py-4 border-b border-neutral-800/50">
  <div className="max-w-7xl mx-auto flex items-center justify-between">
    {/* Logo */}
    <div className="flex flex-col">
      <Link href="/" className="font-bold text-3xl">
        <span className="text-white">market</span>
        <span className="text-[#B9F040]">ably</span>
      </Link>
      <span className="text-xs text-[#B9F040] tracking-wide mt-1">
        Feedback-Fueled Marketing
      </span>
    </div>

    {/* Desktop Navigation */}
    <div className="hidden lg:flex items-center space-x-8">
      {/* Nav links and CTAs */}
    </div>

    {/* Mobile Menu Button */}
    <div className="lg:hidden">
      <button className="text-[#B9F040]">
        {/* Menu icon */}
      </button>
    </div>
  </div>
</nav>
```

**Specifications:**
- Position: Sticky (stays at top on scroll)
- Z-index: 50
- Background: Black (#000000)
- Bottom border: Semi-transparent neutral-800
- Mobile breakpoint: lg (1024px)

### Navigation Links

```tsx
<Link
  href="/page"
  className="text-white hover:text-[#B9F040] cursor-pointer transition-colors"
>
  Link Text
</Link>
```

**Active State:**
```tsx
<Link
  href="/page"
  className="relative text-[#B9F040] font-semibold"
>
  Link Text
  <span className="absolute -bottom-[6px] left-0 right-0 h-[2px] bg-[#B9F040]" />
</Link>
```

### Mobile Menu

```tsx
{isMobileMenuOpen && (
  <div className="lg:hidden mt-4 pb-4">
    <div className="flex flex-col space-y-4">
      {/* Mobile nav links */}
      {/* Mobile CTAs */}
    </div>
  </div>
)}
```

**Mobile Menu Characteristics:**
- Full-width overlay below header
- Vertical stacked layout
- Close on navigation
- Include CTAs at bottom

### Footer

```tsx
<footer className="bg-black py-12 md:py-16">
  <div className="max-w-7xl mx-auto px-6 md:px-8">
    <div className="text-center space-y-4">
      <div className="text-white">
        <span className="font-bold text-xl">
          Market<span className="text-[#B9F040]">ably</span>
        </span>
      </div>
      <div className="text-neutral-400 text-sm">
        <p>© {currentYear} All rights reserved</p>
      </div>
    </div>
  </div>
</footer>
```

---

## Animation & Motion

### Animation Principles

1. **Purposeful:** Animations should guide attention and provide feedback
2. **Subtle:** Avoid distracting or excessive motion
3. **Fast:** Keep durations between 0.2s - 0.6s
4. **Smooth:** Use appropriate easing functions
5. **Respect Preferences:** Honor `prefers-reduced-motion`

### Common Animations

#### Fade Up (Scroll Trigger)

```tsx
// Using Framer Motion
<motion.div
  initial={{ opacity: 0, y: 20 }}
  whileInView={{ opacity: 1, y: 0 }}
  viewport={{ amount: 0.3, once: true }}
  transition={{ duration: 0.6, ease: "easeOut" }}
>
  {/* Content */}
</motion.div>
```

#### Stagger Children

```tsx
<motion.div
  initial="hidden"
  whileInView="visible"
  viewport={{ amount: 0.3, once: true }}
  variants={{
    hidden: {},
    visible: {
      transition: { staggerChildren: 0.1 }
    }
  }}
>
  {children.map((child) => (
    <motion.div
      variants={{
        hidden: { opacity: 0, y: 20 },
        visible: { opacity: 1, y: 0 }
      }}
    >
      {child}
    </motion.div>
  ))}
</motion.div>
```

#### Hover Effects

```css
/* Scale down slightly on hover */
.hover-scale {
  transition: transform 0.3s ease;
}
.hover-scale:hover {
  transform: scale(0.98);
}

/* Fade opacity */
.hover-fade {
  transition: opacity 0.3s ease;
}
.hover-fade:hover {
  opacity: 0.8;
}

/* Color transition */
.hover-color {
  transition: color 0.2s ease, background-color 0.2s ease;
}
```

### Easing Functions

```css
/* Standard */
ease-out: cubic-bezier(0, 0, 0.2, 1);

/* Smooth deceleration */
custom: cubic-bezier(0.25, 0.46, 0.45, 0.94);

/* Bounce */
spring: cubic-bezier(0.68, -0.55, 0.265, 1.55);
```

### Reduced Motion Support

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

**Always include reduced motion support for accessibility.**

---

## Accessibility Guidelines

### Color Contrast

- **Body text:** Minimum 4.5:1 contrast ratio
- **Large text (18px+):** Minimum 3:1 contrast ratio
- **UI components:** Minimum 3:1 contrast ratio

**Passing Combinations:**
- White text on black background: ✅ 21:1
- Black text on white background: ✅ 21:1
- #B9F040 on black: ✅ 15.8:1
- Black text on #B9F040: ✅ 15.8:1

### Keyboard Navigation

```tsx
// Ensure all interactive elements are keyboard accessible
<button
  className="..."
  tabIndex={0}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      handleClick()
    }
  }}
>
  Button Text
</button>
```

### Focus States

```css
/* Always include visible focus indicators */
:focus-visible {
  outline: 2px solid #B9F040;
  outline-offset: 2px;
}

/* Or with ring utility */
.focus-visible:ring-2 .focus-visible:ring-[#B9F040] .focus-visible:ring-offset-2
```

### ARIA Labels

```tsx
// Descriptive labels for screen readers
<button aria-label="Book a strategy call">
  <CalendarIcon />
</button>

// Landmark regions
<nav aria-label="Main navigation">
  {/* Navigation content */}
</nav>

<section aria-labelledby="section-heading">
  <h2 id="section-heading">Heading</h2>
</section>
```

### Semantic HTML

- Use proper heading hierarchy (h1 → h2 → h3)
- Use `<button>` for actions, `<a>` for navigation
- Use `<nav>`, `<main>`, `<article>`, `<section>`, `<footer>` appropriately
- Always include alt text for images

### Mobile Accessibility

- Minimum touch target size: 44x44px
- Use 16px font size for inputs (prevents iOS zoom)
- Ensure sufficient spacing between interactive elements
- Test with screen readers (VoiceOver, TalkBack)

---

## Best Practices

### Performance

1. **Images:**
   - Use Next.js Image component for automatic optimization
   - Provide appropriate sizes and srcsets
   - Use lazy loading for below-fold images
   - Add priority to above-fold images

2. **Fonts:**
   - Use `font-display: swap` for web fonts
   - Preconnect to font providers
   - Consider using variable fonts for fewer requests

3. **Animations:**
   - Use CSS transforms and opacity (GPU accelerated)
   - Avoid animating layout properties (width, height, margin)
   - Use will-change sparingly

### Responsive Design

**Breakpoints:**
```css
/* Mobile first approach */
/* Default: 0-639px */

sm: 640px;   /* Small tablets */
md: 768px;   /* Tablets */
lg: 1024px;  /* Small desktops */
xl: 1280px;  /* Large desktops */
2xl: 1536px; /* Extra large */
```

**Pattern:**
```tsx
<div className="text-base md:text-lg lg:text-xl">
  {/* Mobile: 16px, Tablet: 18px, Desktop: 20px */}
</div>
```

### Cross-Browser Testing

Test on:
- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
- Mobile Safari (iOS)
- Chrome Mobile (Android)

### Content Guidelines

1. **Headlines:**
   - Keep concise and action-oriented
   - Use sentence case unless specific brand requirements
   - Highlight key words with lime green color

2. **Body Copy:**
   - Write in active voice
   - Keep paragraphs short (3-4 sentences)
   - Use bullet points for lists
   - Focus on benefits over features

3. **CTAs:**
   - Use action verbs (Book, Get, Start, Download)
   - Create urgency when appropriate (Limited spots, Free for limited time)
   - Be specific (not "Click here" but "Book Your Free Call")

### Consistency Checklist

- [ ] Colors match the defined palette
- [ ] Typography uses Lato font family
- [ ] Spacing follows the 4px grid system
- [ ] All buttons have hover states
- [ ] All interactive elements have focus states
- [ ] Images have alt text
- [ ] Forms have proper labels
- [ ] Animations respect reduced motion
- [ ] Mobile touch targets are at least 44x44px
- [ ] Color contrast meets WCAG AA standards

---

## Quick Reference

### Common Patterns

```tsx
// Primary CTA Button
<button className="bg-[#B9F040] text-black px-6 py-3 rounded-lg font-semibold text-sm uppercase hover:bg-[#a0d636] transition-colors">
  ACTION TEXT
</button>

// Section Header
<div className="mb-16">
  <p className="text-sm uppercase tracking-widest text-neutral-300 mb-4">EYEBROW</p>
  <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold">
    Headline with <span className="text-[#B9F040]">Accent</span>
  </h2>
</div>

// Text Input
<input
  type="text"
  className="w-full px-4 py-3 border-2 border-neutral-300 rounded-lg focus:border-[#B9F040] focus:outline-none"
/>

// Card Container
<div className="bg-white border border-border rounded-xl p-6 shadow-sm hover:shadow-lg transition-shadow">
  {/* Content */}
</div>
```

---

## Version History

- **v1.0** (Nov 23, 2025): Initial style guide created based on marketably.ai production codebase

---

## Contact

For questions about this style guide or design system decisions, contact:
- **Email:** david@rawlings.us
- **Project:** Marketably.ai

---

*This style guide is a living document and should be updated as the design system evolves.*

