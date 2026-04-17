# Marketably.ai Style Guide Package

**Complete design system documentation for consistent branding across all domains and platforms.**

---

## 📦 What's Included

This package contains everything you need to maintain consistent Marketably.ai branding across different websites, applications, and platforms.

### Documentation Files

| File | Purpose | Best For |
|------|---------|----------|
| **STYLE_GUIDE.md** | Complete design system documentation | Comprehensive reference, onboarding new designers/developers |
| **STYLE_GUIDE_QUICK_REF.md** | Condensed cheat sheet | Quick lookups, day-to-day reference |
| **VISUAL_ASSETS_REFERENCE.md** | Image and media asset guide | Finding correct logos, images, and videos |
| **IMPLEMENTATION_GUIDE.md** | Platform-specific setup instructions | Implementing design on new platforms |
| **portable-design-tokens.css** | CSS variables for all design values | Direct import into any project |

---

## 🚀 Quick Start (3 Steps)

### 1. Choose Your Scenario

- **New website from scratch?** → See [Implementation Guide - New Static Website](#)
- **Adding to WordPress?** → See [Implementation Guide - WordPress](#)
- **React/Next.js app?** → See [Implementation Guide - React](#)
- **Landing page builder?** → See [Implementation Guide - Landing Pages](#)
- **Email template?** → See [Implementation Guide - Email](#)

### 2. Copy Core Assets

```bash
# Minimum required files:
- portable-design-tokens.css
- STYLE_GUIDE_QUICK_REF.md
```

### 3. Load Font & Import Styles

```html
<!-- Add to <head> -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Lato:wght@300;400;700;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="portable-design-tokens.css">
```

**Done!** You now have access to all design tokens via CSS variables.

---

## 📚 File Guide

### STYLE_GUIDE.md
**The Complete Design System**

**Contains:**
- Brand identity and voice
- Complete color palette with usage guidelines
- Typography system (fonts, sizes, weights)
- Spacing and layout patterns
- All component patterns (buttons, forms, cards, etc.)
- Animation and motion guidelines
- Accessibility requirements
- Best practices

**When to use:**
- Onboarding new team members
- Making design decisions
- Creating new components
- Reference for edge cases

**Length:** ~15 pages

---

### STYLE_GUIDE_QUICK_REF.md
**The Cheat Sheet**

**Contains:**
- Color codes (copy-paste ready)
- Typography sizes
- Common spacing values
- Button styles
- Form styles
- Quick code snippets
- Checklist before publishing

**When to use:**
- Quick color lookups
- Finding spacing values
- Copy-paste code snippets
- Daily reference

**Length:** ~3 pages

---

### VISUAL_ASSETS_REFERENCE.md
**The Media Guide**

**Contains:**
- Logo usage guidelines
- Image URLs and specifications
- Client logo inventory
- Video embed codes
- Image optimization guidelines
- Alt text best practices

**When to use:**
- Finding correct logo or image
- Adding client logos to new pages
- Embedding videos
- Optimizing images

**Length:** ~8 pages

---

### IMPLEMENTATION_GUIDE.md
**The Platform Setup Guide**

**Contains:**
- Platform-specific instructions
- WordPress setup
- React/Next.js setup
- Landing page builder setup
- Email template code
- Testing checklist
- Troubleshooting

**When to use:**
- Starting new project on specific platform
- Troubleshooting implementation issues
- Cross-browser testing
- Learning platform-specific quirks

**Length:** ~12 pages

---

### portable-design-tokens.css
**The Code**

**Contains:**
- All colors as CSS variables
- All spacing values
- Typography scales
- Border radius values
- Shadow definitions
- Transition timings
- Pre-built utility classes

**When to use:**
- Every project (required)
- Import at the start of CSS
- Reference for variable names

**Length:** ~400 lines of CSS

---

## 🎨 Core Brand Elements

### Colors

```css
/* Primary Brand Color */
#B9F040  /* Lime Green */

/* Backgrounds */
#000000  /* Black */
#FFFFFF  /* White */
#1A2B3C  /* Navy */
```

### Typography

```css
Font: Lato
Weights: 300, 400, 700, 900
```

### Logo

```
market (white/black) + ably (lime green)
```

---

## 📖 How to Use This Guide

### For Designers

1. **Start with:** STYLE_GUIDE.md
2. **Keep handy:** STYLE_GUIDE_QUICK_REF.md
3. **For assets:** VISUAL_ASSETS_REFERENCE.md
4. **Tools:** Figma, Sketch, Adobe XD with design tokens

### For Developers

1. **Start with:** IMPLEMENTATION_GUIDE.md
2. **Copy file:** portable-design-tokens.css
3. **Reference:** STYLE_GUIDE_QUICK_REF.md
4. **For images:** VISUAL_ASSETS_REFERENCE.md

### For Content Creators

1. **Start with:** VISUAL_ASSETS_REFERENCE.md
2. **Reference:** STYLE_GUIDE_QUICK_REF.md (content guidelines section)
3. **For copywriting:** STYLE_GUIDE.md (brand voice section)

### For Marketing/Landing Pages

1. **Start with:** IMPLEMENTATION_GUIDE.md (landing pages section)
2. **Copy snippets from:** STYLE_GUIDE_QUICK_REF.md
3. **For images:** VISUAL_ASSETS_REFERENCE.md

---

## ✅ Implementation Checklist

Use this checklist when implementing on a new domain:

### Setup Phase
- [ ] Copy portable-design-tokens.css to project
- [ ] Load Lato font (see Quick Start)
- [ ] Import design tokens in main CSS
- [ ] Set up base typography styles
- [ ] Test font loading

### Components Phase
- [ ] Implement header/navigation
- [ ] Style primary buttons
- [ ] Style secondary buttons
- [ ] Create form input styles
- [ ] Create card components
- [ ] Add footer

### Visual Phase
- [ ] Add logo with correct styling
- [ ] Use lime green (#B9F040) for accents
- [ ] Apply correct spacing
- [ ] Use proper border radius
- [ ] Add hover states to interactive elements
- [ ] Implement focus states

### Content Phase
- [ ] Add alt text to all images
- [ ] Use proper heading hierarchy
- [ ] Apply brand voice to copy
- [ ] Add client logos (if applicable)
- [ ] Optimize all images

### Testing Phase
- [ ] Test on mobile (375px)
- [ ] Test on tablet (768px)
- [ ] Test on desktop (1280px+)
- [ ] Check color contrast
- [ ] Test keyboard navigation
- [ ] Test in multiple browsers
- [ ] Validate HTML
- [ ] Check page load speed

### Launch Phase
- [ ] Final visual review
- [ ] Accessibility audit
- [ ] Cross-browser check
- [ ] Mobile device testing
- [ ] Get stakeholder approval

---

## 🔧 Common Use Cases

### "I need the exact lime green color code"
→ **STYLE_GUIDE_QUICK_REF.md** - Colors section  
**Answer:** `#B9F040`

### "How do I set up on WordPress?"
→ **IMPLEMENTATION_GUIDE.md** - Scenario 2  
**Instructions:** Step-by-step WordPress setup

### "What's the logo for a client?"
→ **VISUAL_ASSETS_REFERENCE.md** - Client Logos section  
**Find:** List of all client logos with URLs

### "How much padding should sections have?"
→ **STYLE_GUIDE_QUICK_REF.md** - Spacing section  
**Answer:** 64px mobile, 96px tablet, 128px desktop

### "What font weights are available?"
→ **STYLE_GUIDE.md** - Typography section  
**Answer:** 300 (Light), 400 (Regular), 700 (Bold), 900 (Black)

### "How do I make a primary button?"
→ **STYLE_GUIDE_QUICK_REF.md** - Buttons section  
**Code snippet:** Ready to copy-paste

### "The colors look different on my screen"
→ **IMPLEMENTATION_GUIDE.md** - Common Issues section  
**Solution:** Use exact hex codes, check color profile

---

## 📱 Responsive Breakpoints

```css
Mobile:  0-639px     (default)
Tablet:  640-1023px  (sm, md)
Desktop: 1024px+     (lg, xl, 2xl)
```

Mobile-first approach: Style for mobile by default, add media queries for larger screens.

---

## ♿ Accessibility Standards

**This design system follows WCAG 2.1 Level AA standards:**

- ✅ Minimum 4.5:1 contrast ratio for body text
- ✅ Minimum 3:1 contrast ratio for large text and UI components
- ✅ All interactive elements keyboard accessible
- ✅ Visible focus indicators on all interactive elements
- ✅ Proper heading hierarchy
- ✅ Alt text for all images
- ✅ Minimum 44x44px touch targets for mobile
- ✅ Respects prefers-reduced-motion

---

## 🚨 Brand Rules (Do's and Don'ts)

### ✅ Do

- Use lime green (#B9F040) as the primary accent color
- Use Lato font across all text
- Style logo as "market" (white/black) + "ably" (lime)
- Maintain consistent spacing (4px grid system)
- Include tagline "Feedback-Fueled Marketing" with logo
- Use black or navy backgrounds for impact sections
- Add hover states to all interactive elements
- Include focus states for accessibility

### ❌ Don't

- Don't change the lime green color (use exact #B9F040)
- Don't use different fonts
- Don't separate "market" and "ably" with spacing
- Don't use lime green as a background color for large areas
- Don't place logo on busy/low-contrast backgrounds
- Don't skip focus states (accessibility requirement)
- Don't use lime green for text on white backgrounds (fails contrast)
- Don't add effects to logo (shadows, gradients, outlines)

---

## 🔄 Version History

- **v1.0** (Nov 23, 2025) - Initial release
  - Complete style guide
  - Quick reference guide
  - Visual assets guide
  - Implementation guide
  - Portable CSS design tokens

---

## 🆘 Getting Help

### Documentation Issues

If you find errors or have questions about the style guide:
- **Email:** david@rawlings.us
- **Subject Line:** "Style Guide Question - [Topic]"

### Implementation Help

If you need help implementing on a specific platform:
1. Check **IMPLEMENTATION_GUIDE.md** first
2. Review **Common Issues & Solutions** section
3. Contact david@rawlings.us with:
   - Platform/tech stack
   - What you've tried
   - Screenshots if applicable

### Design Decisions

For questions about design decisions or edge cases:
1. Check **STYLE_GUIDE.md** for guidance
2. Look for similar examples in existing implementation
3. Contact design team for clarification

---

## 📈 Maintaining the Style Guide

### When to Update

Update these documents when:
- New brand colors are added
- New component patterns are created
- Platform-specific issues are discovered
- Common questions arise repeatedly
- Typography scale changes
- New client logos are added

### How to Update

1. Edit the relevant markdown file
2. Update version number
3. Note changes in Version History section
4. Communicate changes to team
5. Update portable-design-tokens.css if needed

### Requesting Changes

To propose changes to the design system:
1. Document the reason for change
2. Show examples of the issue
3. Propose specific solution
4. Submit to design team for review

---

## 📦 File Structure

```
marketably.ai/
├── STYLE_GUIDE_README.md              ← You are here
├── STYLE_GUIDE.md                     ← Complete guide
├── STYLE_GUIDE_QUICK_REF.md           ← Quick reference
├── VISUAL_ASSETS_REFERENCE.md         ← Images & assets
├── IMPLEMENTATION_GUIDE.md            ← Platform setup
└── portable-design-tokens.css         ← CSS variables
```

---

## 🌟 Key Principles

The Marketably.ai design system is built on these principles:

1. **Consistency** - Same look and feel across all platforms
2. **Accessibility** - WCAG 2.1 Level AA compliance
3. **Simplicity** - Clean, modern, professional design
4. **Performance** - Optimized for fast loading
5. **Flexibility** - Works on various platforms and tech stacks
6. **Maintainability** - Easy to update and scale

---

## 🎯 Quick Reference Card

**Print or bookmark this:**

```
Primary Color:    #B9F040 (Lime Green)
Hover State:      #a0d636
Font:             Lato (300, 400, 700, 900)
Black:            #000000
Navy:             #1A2B3C
Button Radius:    8px
Card Radius:      12px
Section Padding:  64px → 128px (mobile → desktop)
Max Width:        1280px
```

---

## 📞 Contact

**Project Owner:** David Rawlings  
**Email:** david@rawlings.us  
**Website:** Marketably.ai  

---

## 📄 License

This style guide is proprietary to Marketably.ai. Internal use only.

---

**Last Updated:** November 23, 2025  
**Version:** 1.0  
**Maintained By:** Marketably.ai Design Team

---

## Getting Started Now

**Ready to implement? Here's your path:**

1. **Read this file** ✅ (You're done!)
2. **Choose your platform** → IMPLEMENTATION_GUIDE.md
3. **Copy design tokens** → portable-design-tokens.css
4. **Keep reference handy** → STYLE_GUIDE_QUICK_REF.md
5. **Find assets** → VISUAL_ASSETS_REFERENCE.md
6. **Build and test** → Use Testing Checklist

**Questions?** Start with IMPLEMENTATION_GUIDE.md - Common Issues section.

Good luck! 🚀

