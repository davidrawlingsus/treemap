# Visual Assets Reference

A guide to all visual assets used across the Marketably.ai brand for consistent implementation across domains.

---

## 📦 Asset Locations

**Primary Storage:** Vercel Blob Storage  
**Base URL:** `https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/`

**Local Public Directory:** `/public/images/`

---

## 🎨 Brand Logo

### Logo Construction

The Marketably logo consists of two color segments:

**Text-based Logo:**
```
"market" + "ably"
└─ white/black   └─ #B9F040 (lime green)
```

**With Tagline:**
```
marketably
Feedback-Fueled Marketing
└─ 12px, #B9F040, uppercase, tracked
```

### Logo Specifications

```css
Font: Lato
Weight: 700 (Bold)
Size: 48px (3rem) desktop, 32px (2rem) mobile
Colors: 
  - "market": #FFFFFF (on dark) or #000000 (on light)
  - "ably": #B9F040
Tagline:
  - Size: 12px (0.75rem)
  - Color: #B9F040
  - Transform: uppercase
  - Letter-spacing: 0.1em
```

### Logo Usage Guidelines

**Do:**
- Maintain consistent color scheme (white/black + lime)
- Keep adequate clear space around logo (minimum 16px)
- Use on solid backgrounds (black, white, or navy)
- Maintain aspect ratio

**Don't:**
- Change the lime green color (#B9F040)
- Add effects (shadows, gradients, outlines)
- Rotate or skew the logo
- Place on busy backgrounds without sufficient contrast

### Logo Files

```
File: Logo is text-based, no image file
Implementation: HTML/CSS text styling
Fallback: /public/logo.svg (if needed)
```

---

## 🖼️ Hero Images

### Primary Hero Image

**File:** `replacement hero girl v3.png`  
**URL:** `https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/replacement%20hero%20girl%20v3.png`

**Specifications:**
- Dimensions: 462 × 550px
- Format: PNG with transparency
- Style: Modern, friendly, smiling person
- Background: Transparent
- Use: Homepage hero section
- Alt text: "Smiling person representing friendly, modern analytics brand"

**Responsive Behavior:**
- Mobile: 70vw width, slight upward translate
- Desktop: Max 462px width, translate down 8px for overlap effect

---

## 📊 Charts & Graphics

### A/B Test Results Graphic

**File:** `ab-test-image.png` (or `ab test image.png`)  
**URL:** `https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/graphics/ab-test-image.png`

**Specifications:**
- Shows: "MRR +$17K/m Program Paid For"
- Style: Professional data visualization
- Format: PNG
- Use: CTA sections, case study showcases
- Alt text: "MRR +$17K/m Program Paid For - A/B Test Results"

### Impact Chart (Inline SVG)

**Implementation:** Inline SVG, not an image file  
**Location:** `src/app/(public)/components/ImpactChart.tsx`

**Specifications:**
- ViewBox: 0 0 614 287
- Colors:
  - Baseline bars: #F9FAF2 (off-white), 70% opacity
  - Highlight bars: #B9F040 (lime green), 80% opacity
- Animation: Staggered fade-in on scroll
- Responsive: Scales with container, 1.8x scale on desktop

---

## 👥 Client Logos

### Logo Cloud Assets

All client logos stored in `/public/images/` and Vercel Blob Storage under `/logos/`

**Display Guidelines:**
- Default state: Grayscale with 60% opacity
- Hover state: Full color, 100% opacity
- Transition: 300ms ease
- Aspect ratio: Preserve (object-contain)
- Height: 48px (h-12)
- Grid: 3 columns mobile, 6 columns desktop

### Client Logo List

#### Square Logos (1:1 aspect ratio)
```
katkin_logo_square.png
mous_logo_square.png
hotjar_logo_square.png
look_fabulous_forever_logo_square.png
omlet_logo_square.png
durex_logo_square.png
elvie_logo_square.png
fitness_first_logo_square.png
hux_health_logo_square.png
issa_online_logo_square.png
liforme_logo_square.png
mindful_chef_logo_square.png
modular_closets_logo_square.png
monica_vinader_logo_square.png
neom_organics_logo_square.jpg
o2_logo_square.png
orlebar_brown_logo_square.png
rabbies_logo_square.png
sally_beauty_logo_square.png
sass_and_belle_logo_square.png
sila_logo_square.png
the_whisky_exchange_logo_square.png
united_states_flag_store_logo_square.png
ancient_and_brave_logo_square.png
best_western_square.png
Bupa_logo_square.png
choice_hotels_logo_square.png
conde_nast_logo_square.png
crazy_egg_logo_square.png
hotelissima_logo_square.jpg
msre_logo_square.jpg
```

#### Rectangle Logos (wider aspect ratios)
```
wattbike_logo_rectangle.png
piper_logo_rectangle.png
absolute_reg_logo_rectangle.png
awa_digital_square.png
barbour_logo_rectangle.png
conversion_rate_experts_logo_rectangle.png
dc_cargo_mall_logo_rectangle.png
duffells_logo_rectangle.png
exploring_ireland_logo_rectangle.png
grasshopper_logo_rectangle.png
lily_and_lionel_logo.png
martin_randall_travel_square.png
plastic_place_logo_rectangle.png
prepkitchen_logo_rectangle.png
quicksprout_logo_rectangle.png
the_gluten_free_palace_logo_rectangle.png
the_sewing_studio_logo_rectangle.png
```

---

## 🎬 Video Assets

### Testimonial Videos

**Platform:** Mux Video Hosting

**Mark Morley Review:**
- Video ID: `IJtQaVuEd2CuYuBPpxLwQINIF68RFxtCRRE02drZplv8`
- Thumbnail: Animated GIF (3 seconds, 12fps)
- Duration: Full testimonial
- Embed: Mux Player with custom accent color (#B9F040)
- Autoplay: On modal open only

**Video Player Specifications:**
```
Aspect Ratio: 16:9
Accent Color: #B9F040
Controls: Full controls
Autoplay: User-initiated only
Metadata: Include video title
```

---

## 👤 Team Photos

### Team Member Photos

**Directory:** `/public/images/`

**Current Team Images:**
```
david rawlings.jpg        - David Rawlings headshot
sara_chen.png            - Sara Chen headshot
mark_morley_avatar.jpeg  - Mark Morley avatar
francois du toit.jpeg    - François du Toit headshot
attila szucs.jpeg        - Attila Szucs headshot
```

**Photo Guidelines:**
- Format: JPG or PNG
- Aspect ratio: 1:1 (square)
- Minimum size: 400 × 400px
- Recommended size: 800 × 800px
- Style: Professional headshot
- Background: Clean, uncluttered
- Lighting: Well-lit, professional

**Display:**
- Border radius: 50% (full circle)
- Border: 2px solid (border color)
- Size: 64px - 96px diameter
- Hover: Slight scale or shadow effect

---

## 🎭 Miscellaneous Images

### Favicon

**File:** `favicon.png`  
**URL:** `https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/favicon.png`

**Specifications:**
- Minimum: 32 × 32px
- Recommended: 512 × 512px (for various use cases)
- Format: PNG with transparency
- Design: Simple, recognizable at small sizes

### Background Images & Patterns

**Location:** CSS gradients (no image files)

**Common Patterns:**
```css
/* Navy gradient for CTAs */
background: linear-gradient(to bottom right, #1A2B3C, #0F1B28);

/* Subtle accent overlay */
background: linear-gradient(to right, rgba(185, 240, 64, 0.05), transparent);

/* Light card gradient */
background: linear-gradient(to bottom right, 
  oklch(0.205 0 0 / 0.05), 
  oklch(0.97 0 0 / 0.05)
);
```

---

## 🎨 Image Treatment Guidelines

### Logo Treatment

**For client logos:**
```css
/* Default state */
filter: grayscale(100%);
opacity: 0.6;
transition: all 300ms ease;

/* Hover state */
filter: grayscale(0%);
opacity: 1;
```

### Photo Treatment

**For testimonial photos:**
```css
/* Container */
border-radius: 50%;
overflow: hidden;
border: 2px solid var(--border);
background: white;
padding: 8px;

/* Image */
object-fit: contain;
width: 100%;
height: 100%;
```

### Overlay Effects

**For image containers:**
```css
/* Hover overlay */
position: relative;

::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(to bottom right, 
    rgba(185, 240, 64, 0.05), 
    transparent
  );
  opacity: 0;
  transition: opacity 500ms;
}

:hover::after {
  opacity: 1;
}
```

---

## 📐 Image Sizing Guidelines

### Responsive Image Sizes

**Hero Images:**
```html
<!-- Mobile -->
<img 
  src="hero.png" 
  style="width: 70vw;"
  alt="..."
/>

<!-- Desktop -->
<img 
  src="hero.png" 
  style="max-width: 462px;"
  alt="..."
/>
```

**Logo Cloud:**
```css
.logo-container {
  height: 48px;        /* h-12 */
  width: 100%;
  object-fit: contain;
}
```

**Testimonial Avatars:**
```css
.avatar {
  width: 64px;         /* Mobile */
  height: 64px;
  width: 80px;         /* Desktop */
  height: 80px;
}
```

### Next.js Image Component

**When using Next.js:**
```tsx
import Image from 'next/image'

// Responsive
<Image
  src="/images/hero.png"
  alt="Description"
  width={462}
  height={550}
  className="object-contain"
  priority={true}  // For above-fold images
  sizes="(max-width: 768px) 70vw, 462px"
/>

// Fill container
<Image
  src="/images/logo.png"
  alt="Company logo"
  fill
  className="object-contain"
  sizes="100px"
/>
```

---

## ✅ Image Optimization Checklist

**Before adding new images:**
- [ ] Optimize file size (use tools like TinyPNG, ImageOptim)
- [ ] Use appropriate format (PNG for logos/transparency, JPG for photos, SVG for icons)
- [ ] Provide multiple sizes for responsive display
- [ ] Include descriptive alt text
- [ ] Test on retina/high-DPI displays
- [ ] Ensure fast loading (lazy load below-fold images)
- [ ] Compress without visible quality loss
- [ ] Use WebP format when supported (with fallbacks)

---

## 🔍 Alt Text Guidelines

### Writing Good Alt Text

**Do:**
- Be descriptive and specific
- Keep under 125 characters when possible
- Describe the content and context
- Include text that appears in the image
- Mention important details (colors, emotions, actions)

**Don't:**
- Start with "Image of..." or "Picture of..."
- Use generic descriptions ("photo", "graphic")
- Include "click here" or other instructions
- Repeat information already in surrounding text
- Be overly verbose

### Examples

**Good:**
```html
<img src="hero.png" alt="Smiling person representing friendly, modern analytics brand" />
<img src="chart.png" alt="Bar chart showing 214% improvement in A/B test profitability" />
<img src="logo.png" alt="KatKin company logo" />
```

**Bad:**
```html
<img src="hero.png" alt="Image" />
<img src="chart.png" alt="Chart showing results click here" />
<img src="logo.png" alt="A picture of a logo" />
```

---

## 📤 Exporting New Assets

### For New Images

**Naming Convention:**
```
Format: lowercase_with_underscores
Include dimensions if multiple sizes: logo_large.png, logo_small.png
Include shape descriptor: client_logo_square.png, client_logo_rectangle.png
Be descriptive: ab_test_result_chart.png (not chart1.png)
```

**Export Settings:**
- **PNG:** For logos, graphics, images with transparency
  - Color mode: RGB
  - Transparency: Yes
  - Compression: Maximum without quality loss

- **JPG:** For photographs
  - Color mode: RGB
  - Quality: 85-90%
  - Progressive: Yes

- **SVG:** For icons and simple graphics
  - Minified: Yes
  - Decimal places: 2
  - Remove unused elements: Yes

---

## 🌐 CDN & Storage

### Vercel Blob Storage

**Current base URL:**
```
https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/
```

**Folder structure:**
```
/logos/           - Client logos
/graphics/        - Charts, illustrations
/images/          - General images
```

**Uploading new assets:**
1. Use Vercel Blob Storage dashboard
2. Organize into appropriate folders
3. Use descriptive file names
4. Update this reference document
5. Test URLs in staging before production

### Local Public Directory

**Structure:**
```
/public/
  /images/
    - Team photos
    - Client logos
    - Local assets
  - favicon.png
  - logo.svg
  - robots.txt
```

**Best practices:**
- Keep file size under 500KB when possible
- Use CDN (Vercel Blob) for frequently accessed images
- Keep local public directory for critical above-fold assets
- Version assets if they change frequently

---

## 📞 Asset Resources

**Image Optimization Tools:**
- TinyPNG (https://tinypng.com) - PNG compression
- Squoosh (https://squoosh.app) - Multiple format optimization
- ImageOptim (Mac app) - Bulk optimization

**Stock Photos (if needed):**
- Unsplash (https://unsplash.com)
- Pexels (https://pexels.com)

**Design Tools:**
- Figma - For creating graphics
- Adobe Illustrator - For logos and vectors
- Photoshop - For photo editing

---

## 📋 Quick Reference

### Most Used Assets

```
Hero Image:
neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/replacement%20hero%20girl%20v3.png

A/B Test Graphic:
neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/graphics/ab-test-image.png

Favicon:
neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/favicon.png

Top Client Logos:
- katkin_logo_square.png
- mous_logo_square.png
- hotjar_logo_square.png
- wattbike_logo_rectangle.png
- look_fabulous_forever_logo_square.png
```

---

**Last Updated:** November 23, 2025  
**Maintained By:** Marketably.ai Design Team

