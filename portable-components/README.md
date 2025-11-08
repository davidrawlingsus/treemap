# Portable Header Components

This directory contains all the necessary files to port the header and styling from the frontend app to your client area backend.

## 📁 Directory Structure

```
portable-components/
├── Header.tsx              # Main navigation header component
├── StrategyCallModal.tsx  # Modal for booking strategy calls
├── ui/
│   ├── dialog.tsx         # Dialog component (Radix UI)
│   └── button.tsx         # Button component
├── lib/
│   └── utils.ts           # Utility functions (cn helper)
├── styles/
│   └── globals.css        # Global CSS stylesheet with Tailwind setup
├── FONT_SETUP.md          # Instructions for setting up Lato font
└── README.md              # This file
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
npm install @radix-ui/react-dialog @radix-ui/react-slot lucide-react class-variance-authority clsx tailwind-merge
```

### 2. Copy Files

Copy all files from this directory to your client area project, maintaining the directory structure:

- `Header.tsx` → `components/Header.tsx`
- `StrategyCallModal.tsx` → `components/StrategyCallModal.tsx`
- `ui/` → `components/ui/`
- `lib/utils.ts` → `lib/utils.ts`
- `styles/globals.css` → `styles/globals.css` (or where your CSS lives)

### 3. Set Up Font

Follow the instructions in `FONT_SETUP.md` to add the Lato font.

### 4. Import Globals CSS

Make sure to import `globals.css` in your main entry file (e.g., `app.tsx`, `main.tsx`, `index.tsx`):

```tsx
import './styles/globals.css'
```

### 5. Adapt Routing

The components include TODO comments for adapting to your routing setup:

- **Header.tsx**: Replace `Link` and `usePathname` with your router's equivalents
- **StrategyCallModal.tsx**: Update the API endpoint URL if needed

### 6. Use the Header

```tsx
import Header from '@/components/Header'

function App() {
  return (
    <div>
      <Header />
      {/* Your content */}
    </div>
  )
}
```

## 🔧 Key Adaptations Needed

### Routing (Header.tsx)

**If using React Router:**
```tsx
import { Link, useLocation } from 'react-router-dom'

// Replace usePathname with:
const usePathname = () => {
  const location = useLocation()
  return location.pathname
}
```

**If using another router:**
- Replace `Link` import with your router's Link component
- Replace `usePathname` with your router's pathname hook

### Image Component (StrategyCallModal.tsx)

The component includes a basic Image wrapper. If you're using Next.js, you can use the real `next/image`. Otherwise, the wrapper should work fine.

### API Endpoint (StrategyCallModal.tsx)

Update the fetch URL in `handleSubmit`:
```tsx
const response = await fetch('/api/strategy-call', { ... })
```

## 📦 Dependencies

- `@radix-ui/react-dialog` - Dialog/modal component
- `@radix-ui/react-slot` - Slot component for Button
- `lucide-react` - Icons (Menu, X, CheckCircle2)
- `class-variance-authority` - Button variants
- `clsx` - Class name utility
- `tailwind-merge` - Merge Tailwind classes

## 🎨 Styling

The header uses:
- **Tailwind CSS** for styling
- **Lato font** (weights: 300, 400, 700, 900)
- **Brand colors**:
  - Primary: `#B9F040` (lime green)
  - Background: `black`
  - Text: `white` and `#B9F040`

## ✨ Features

- ✅ Responsive mobile menu
- ✅ Active section highlighting (scroll spy)
- ✅ Sticky header
- ✅ Strategy call booking modal
- ✅ Navigation links (hash-based and routes)
- ✅ CTA buttons

## 📝 Notes

- The header is sticky (`sticky top-0 z-50`)
- Mobile menu appears on screens smaller than `lg` (1024px)
- Navigation uses hash-based routing for sections and route-based for pages
- The StrategyCallModal posts to `/api/strategy-call` - make sure this endpoint exists

## 🆘 Troubleshooting

See `PORTABLE_HEADER_PACKAGE.md` in the root directory for detailed troubleshooting tips.

## 📄 License

These components are part of the Marketably.ai frontend and should be used accordingly.

