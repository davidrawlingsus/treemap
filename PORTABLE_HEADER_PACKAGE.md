# Portable Header Package for Client Area

This package contains all the necessary code to port the header and styles from the frontend app to your client area backend.

## 📦 All Files Are in the `portable-components/` Directory

All the portable files have been created in the `portable-components/` directory. Please refer to `portable-components/README.md` for detailed setup instructions.

## Files Included

1. **Header Component** - Main navigation header (`portable-components/Header.tsx`)
2. **StrategyCallModal Component** - Modal for booking strategy calls (`portable-components/StrategyCallModal.tsx`)
3. **UI Components** - Dialog and Button components (`portable-components/ui/`)
4. **Utils** - Helper functions (`portable-components/lib/utils.ts`)
5. **Styles** - Global CSS stylesheet (`portable-components/styles/globals.css`)
6. **Font Setup** - Instructions for Lato font (`portable-components/FONT_SETUP.md`)

---

## 📦 Dependencies Required

Install these npm packages in your client area repo:

```bash
npm install @radix-ui/react-dialog @radix-ui/react-slot lucide-react class-variance-authority clsx tailwind-merge
```

If you're not using React Router or a similar routing library, you'll also need to adapt the Link components.

---

## 🎨 Font Setup

The header uses the **Lato** font. You can either:

### Option 1: Google Fonts (Recommended)
Add this to your HTML `<head>`:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Lato:wght@300;400;700;900&display=swap" rel="stylesheet">
```

Then add this CSS variable:
```css
:root {
  --font-lato: 'Lato', sans-serif;
}
```

### Option 2: Import in CSS
```css
@import url('https://fonts.googleapis.com/css2?family=Lato:wght@300;400;700;900&display=swap');
```

---

## 📁 File Structure

Create these files in your client area:

```
components/
  Header.tsx
  StrategyCallModal.tsx
  ui/
    dialog.tsx
    button.tsx
lib/
  utils.ts
styles/
  globals.css
```

---

## 🚀 Usage

### 1. Import and use the Header component:

```tsx
import Header from '@/components/Header'

function App() {
  return (
    <div>
      <Header />
      {/* Your app content */}
    </div>
  )
}
```

### 2. Make sure your routing setup matches:

The Header uses hash-based navigation (`#clients`, `#impact`, etc.) and one route (`/challenge`). Adjust the navigation items in the Header component to match your routes.

### 3. API Endpoint:

The StrategyCallModal posts to `/api/strategy-call`. Make sure you have this endpoint set up, or modify the fetch URL in `StrategyCallModal.tsx`.

---

## 🔧 Adaptations Needed

### If Not Using Next.js:

1. **Replace `next/link`** with your router's Link component (e.g., `react-router-dom`'s `Link`)
2. **Replace `next/image`** with regular `<img>` tags or your image component
3. **Replace `usePathname()`** from `next/navigation` with your router's hook (e.g., `useLocation()` from react-router-dom)

### Routing Adaptations:

In `Header.tsx`, find:
- `import Link from 'next/link'` → Replace with your router's Link
- `import { usePathname } from 'next/navigation'` → Replace with your router's pathname hook
- `pathname === '/'` → Adjust to match your home route

### Image Component:

In `StrategyCallModal.tsx`, find:
- `import Image from 'next/image'` → Replace with regular `<img>` or your image component

---

## 📝 Notes

- The header uses Tailwind CSS classes. Make sure Tailwind is configured in your project.
- The color scheme uses:
  - Primary brand color: `#B9F040` (lime green)
  - Background: `black` (`#000000`)
  - Text: `white` and `#B9F040`
- The header is sticky (`sticky top-0 z-50`)
- Mobile menu is responsive (hidden on `lg:` screens and above)

---

## 🎯 Customization

### Navigation Items

Edit the `NAV_ITEMS` array in `Header.tsx`:

```tsx
const NAV_ITEMS = [
  { id: 'clients', label: 'Clients', hash: '#clients' },
  { id: 'impact', label: 'Results', hash: '#impact' },
  // Add or modify items here
]
```

### Logo and Tagline

Edit the logo section in `Header.tsx`:

```tsx
<Link href="/" className="...">
  <span className="text-white">market</span>
  <span className="text-[#B9F040]">ably</span>
</Link>
<span className="text-xs text-[#B9F040] tracking-wide mt-1">
  Feedback-Fueled Marketing
</span>
```

### Colors

The brand color `#B9F040` is used throughout. Search and replace in the files if you want to change it.

---

## ✅ Checklist

- [ ] Install all required npm packages
- [ ] Set up Lato font
- [ ] Copy all component files
- [ ] Copy globals.css
- [ ] Adapt routing imports (Link, usePathname, etc.)
- [ ] Adapt Image component if needed
- [ ] Set up `/api/strategy-call` endpoint
- [ ] Configure Tailwind CSS
- [ ] Test mobile menu functionality
- [ ] Test navigation links
- [ ] Test StrategyCallModal

---

## 🆘 Troubleshooting

**Styles not applying?**
- Make sure Tailwind CSS is configured
- Import globals.css in your main entry file
- Check that PostCSS is processing Tailwind

**Font not loading?**
- Check browser console for font loading errors
- Verify Google Fonts link is in the `<head>`
- Ensure CSS variable `--font-lato` is set

**Modal not working?**
- Verify @radix-ui/react-dialog is installed
- Check that Dialog component is properly imported
- Ensure z-index is high enough (header uses z-50)

**Routing issues?**
- Replace Next.js routing with your router
- Update pathname checks to match your router's API
- Test hash navigation if using hash-based routing

