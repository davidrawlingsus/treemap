# Plan: MapTheGap Public Chrome Extension — Free-to-Lead Funnel

**Status:** Parked — ready to implement when needed

## Context

The Chrome extension currently requires full authentication before showing any value. We want to convert it into a public lead-gen tool:
- Free install from Chrome Web Store
- Instant value (full ad analysis) with no login
- Email capture positioned as "get this emailed to you" + triggers lead gen pipeline
- Exit-intent popup captures abandoning users

The ad hook: *"Ever wonder how much of your adspend is wasted?"*

## User Journey

1. Install extension, open FB Ads Library, click icon → side panel opens
2. **First visit**: email capture — "Enter your email to grade these ads" (lightweight, one field)
3. Email submitted → account created, magic link sent, **first analysis runs immediately**
4. Full analysis injected on each ad card + synthesis in sidebar
5. Results cached per advertiser — revisiting same advertiser loads instantly
6. **3 free runs total** — tracked server-side per user account
7. After 3 runs: "You've used all 3 free analyses. Want more? Get in touch." with CTA
8. Magic link from email → full authenticated mode (import controls, lead gen pipeline)
9. **Exit-intent popup** on FB page if user tries to leave without entering email
10. **Future**: credit purchase for power users (agencies, consultants)

## Architecture: Open Analysis, Email for Delivery

| | Free (Anonymous) | Full (Authenticated) |
|---|---|---|
| **Analysis** | Full (same as authenticated) | Full |
| **On page** | Full dimension scores | Full dimension scores |
| **Sidebar** | Full analysis + reviews + signal + synthesis + email capture | Same, plus import controls |
| **Rate limit** | 10/day per IP | Unlimited |

**No content gating.** Anonymous users get the full analysis for free — the value IS the lead magnet. The email capture is positioned as "get the full report emailed to you" and "unlock import + lead gen pipeline", not as a wall blocking content they can already see.

Authenticated users additionally get import controls and lead gen pipeline access.

---

## Changes by File

### Backend

**1. `backend/app/middleware/rate_limit.py`** (new file)
- In-memory IP-based rate limiter as a FastAPI `Depends()` function
- 10 requests per IP per 24h window
- Prunes stale entries on each check
- Skipped for authenticated users

**2. `backend/app/routers/extension_analysis.py`**
- Change all 4 analysis endpoints from `get_current_user_flexible` to `get_optional_current_user`
- Add rate limit dependency (applied only when `current_user is None`)
- Existing functionality unchanged for authenticated users

**3. `backend/app/routers/public_leadgen.py`**
- Remove work-email-only restriction (`is_likely_work_email_domain` check)
- Accept any email address for the extension lead capture flow

### Extension

**4. `chrome-extension/popup/popup.html`**
- Add `#emailCaptureCard` below synthesis panel — "Get this report emailed to you" with email input + CTA
- Add `#emailSubmittedCard` — confirmation: "Check your inbox in ~5 minutes"
- Hide import controls (client select, leadgen toggle, import button) when not authenticated
- All existing sections remain

**5. `chrome-extension/popup/popup.js`**
- Refactor `checkAuth()`: if no token + on Ads Library page → `showFreeMode()` (new)
- `showFreeMode()`: same as `showMain()` but skips client loading, hides import controls, shows email capture card
- Runs full existing analysis flow (streaming ad analysis, review detection, signal, synthesis) — same code paths, just no auth header
- `handleEmailCapture()`: calls `/api/public/leadgen/start` + `/api/auth/magic-link/request`, shows confirmation
- After analysis done, sends `setupExitIntent` message to content script with worst grade
- Existing authenticated flow untouched

**6. `chrome-extension/popup/popup.css`**
- Styles for email capture card (prominent, branded CTA)
- Styles for email submitted confirmation

**7. `chrome-extension/content/extractor.js`**
- Add `setupExitIntent(worstGrade)` message handler:
  - Registers `mousemove` listener on document
  - Triggers when `event.clientY < 50` + upward movement
  - Shows once per session (`sessionStorage`)
  - Injects full-viewport overlay with email capture modal
- Add styles for exit-intent popup (inline in injected `<style>` tag)
- Exit popup email submit → `chrome.runtime.sendMessage({ action: "captureLeadEmail", email, companyUrl })`

**8. `chrome-extension/background/service-worker.js`**
- Add handler for `captureLeadEmail` message → calls `/api/public/leadgen/start`

### No Changes Needed
- `manifest.json` — existing permissions cover all required hosts
- `backend/app/auth.py` — `get_optional_current_user` already exists

---

## Implementation Order

1. Backend: rate_limit.py middleware
2. Backend: switch analysis endpoints to `get_optional_current_user` + rate limit
3. Backend: relax email restriction in public_leadgen.py
4. Extension: `checkAuth()` branching + `showFreeMode()` — full analysis, no auth
5. Extension: email capture card + handler + confirmation in sidebar
6. Extension: exit-intent popup in extractor.js + service worker handler

## Verification

1. **Free tier**: Uninstall extension, reinstall, open on FB Ads Library — full analysis should stream with no login, scores injected on page
2. **Rate limit**: Make 11 requests from same browser — 11th should show "rate limit" message
3. **Email capture**: Enter any email → verify `/api/public/leadgen/start` is called (check backend logs), verify magic link email sent
4. **Exit intent**: Move mouse to top of browser window — popup should appear once
5. **Auth upgrade**: Click magic link from email → reopen extension → import controls now visible
6. **No regression**: Log in with existing account → full existing flow works unchanged, import controls visible

## Usage Limits, Caching & Credits

### Usage Limit (3 free runs)

The primary use case is business owners grading their own ads — they only need 1-2 runs. Cap at 3 to control costs.

**Must be server-side** — `chrome.storage.local` is per-device, so users could bypass it by switching machines. Tying it to the authenticated user account means:
- Email capture is required before the first run (not after)
- Run count stored on the User model or a separate `ExtensionUsage` table
- Backend checks run count before allowing analysis endpoints
- Extension shows "You've used 3 of 3 analyses. Want more? Get in touch." with a CTA

**Flow adjustment:**
1. User opens extension → sees email capture first (not analysis)
2. Enters email → account created, magic link sent
3. Analysis runs (1st of 3)
4. On return visits, checks token → shows cached results or allows new run

### Cached Results Per Advertiser

Results cached server-side keyed by advertiser ID (from FB Ads Library URL param). On revisit:
- Extension extracts advertiser ID from URL
- Calls `GET /api/extension/cached-results?advertiser_id=X`
- If cached: restores full analysis instantly (ad grades, synthesis, review signal) — no API cost
- If not cached: runs fresh analysis (costs 1 credit)

**Backend:**
- New model: `ExtensionAnalysisCache` — `advertiser_id`, `user_id`, `ad_grades` (JSONB), `synthesis_text`, `review_detection` (JSONB), `signal_text`, `created_at`
- New endpoints: `GET /api/extension/cached-results`, `POST /api/extension/cache-results`
- Cache saved automatically after analysis completes

**Extension:**
- On open: check cache before starting analysis
- If cached: inject grades on page from cache, render sidebar from cache, show "Cached from [date]" badge
- Re-extract button forces fresh analysis (costs 1 credit)

### Credits (Future — Power Users)

For users who need more than 3 runs (agencies, consultants):
- Stripe Checkout integration — "Buy Credits" button in sidebar
- Backend: `/api/extension/create-checkout-session` → Stripe session URL
- Backend: Stripe webhook credits the account
- Credit packs: 50 analyses for $9, 200 for $29 (placeholder pricing)
- Each run (ad scoring + review signal + synthesis) = 1 credit
- Free tier: 3 lifetime runs, paid: unlimited within credit balance

**Backend files:**
- `backend/app/routers/extension_billing.py` — checkout session, webhook, balance check
- `backend/app/models/extension_usage.py` — run count, credit balance, advertiser cache

## Ad Distribution Strategy

**Tier 1 — High intent:**
- Facebook/Instagram ads targeting "Facebook Ads Manager", "Digital advertising" interests
- Google Search: "facebook ads audit", "ad creative scoring tool"

**Tier 2 — Marketing mindset:**
- YouTube pre-roll on FB ads educator channels
- LinkedIn targeting Marketing Directors, CMOs, DTC Founders

**Tier 3 — Community (free):**
- Reddit: r/PPC, r/facebookads, r/ecommerce
- Twitter/X: marketing community
- Facebook Groups: DTC, Shopify sellers, agency owners

**Hook:** *"We analyzed 10,000 Facebook ads. 73% scored D or below. Grade yours free."*
