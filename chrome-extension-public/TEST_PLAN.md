# MapTheGap Public Extension — Test Plan

Clean slate each test: run `chrome.storage.local.clear()` in the public extension's service worker DevTools between tests.

---

## Test 1: Journey A — Warm Lead (webhook → no gate)

**Setup:**
```bash
# Delete any existing cellexia client first
TOKEN="your_founder_token"
curl -s -X DELETE "https://api.mapthegap.ai/api/extension/lead-client/CLIENT_ID_HERE" -H "Authorization: Bearer $TOKEN"

# Register the lead via webhook
curl -s -X POST https://api.mapthegap.ai/api/extension/lead-webhook \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Warm Lead", "email": "test@cellexialabs.com", "website_url": "https://www.cellexialabs.com"}'
```

**Steps:**
1. Clear extension storage
2. Navigate to Cellexia Labs on FB Ads Library
3. Open the public extension

**Expected:**
- [ ] No gate — analysis starts immediately for all ads
- [ ] Review detection checks `cellexialabs.com` (not `lp.cellexialabs.com`)
- [ ] Review Signal section shows "Analyse Reviews" button (Journey A permission prompt) if permission not yet granted
- [ ] Click "Analyse Reviews" → Chrome dialog says "Read and change your data on cellexialabs.com" → Allow
- [ ] Reviews re-run with fetched HTML
- [ ] Synthesis + scores render
- [ ] Console: `[MTG] Warm lead — client exists, skipping gate`

---

## Test 2: Journey B — Cold User (domain-matched registration)

**Setup:** Use an advertiser you do NOT have a client for (not cellexialabs).

**Steps:**
1. Clear extension storage
2. Navigate to a different advertiser on FB Ads Library
3. Open the public extension

**Expected:**
- [ ] First 2 ads stream and inject on page
- [ ] Gate overlay appears (75% opacity, analysis visible behind)
- [ ] Checkbox: "Analyse my customer reviews on [domain]" — checked by default
- [ ] Hint text: "Your email domain must match the advertiser's domain"
- [ ] Enter an email where domain matches the advertiser (e.g. `test@theirdomain.com`)
- [ ] Click "Unlock Analysis" → Chrome permission dialog (per-domain) → Allow
- [ ] Gate lifts immediately — all buffered ads render + inject on page
- [ ] Reviews run with fetched HTML
- [ ] Console: `[MTG] Registration successful, storing token` → `[MTG] liftGate called`

---

## Test 3: Journey B — Domain Mismatch (rejected)

**Steps:**
1. Clear extension storage
2. Open extension on any advertiser
3. Gate appears → enter `test@gmail.com`
4. Click "Unlock Analysis"

**Expected:**
- [ ] Error message: "Email domain (gmail.com) must match the advertiser domain (example.com)"
- [ ] Gate stays up

---

## Test 4: Whitelist Override

**Setup:** Ensure `EXTENSION_WHITELIST_EMAILS=david@rawlings.us` is set on Railway.

**Steps:**
1. Clear extension storage
2. Open extension on ANY advertiser
3. Gate appears → enter `david@rawlings.us`
4. Click "Unlock Analysis"

**Expected:**
- [ ] No domain mismatch error — gate lifts immediately
- [ ] Works on any advertiser regardless of domain
- [ ] Console: `[MTG] Registration successful`

---

## Test 5: Cached Results (repeat visit)

**Prerequisite:** Complete Test 1 or Test 2 successfully (analysis ran + auto-import fired).

**Steps:**
1. Clear extension storage (NOT the database)
2. Re-register with the same email (via gate or whitelist)
3. Open extension on the same advertiser

**Expected:**
- [ ] "Cached analysis from [date]" appears instead of streaming
- [ ] Scores + synthesis render instantly
- [ ] Per-ad critiques inject on page instantly
- [ ] No loading spinners, no SSE streams
- [ ] Console: `[MTG] Cached results found, restoring from import`

---

## Test 6: Magic Link Auto-Switch

This tests the vizualizd redirect + tab switch. Only applies if you trigger a magic link (e.g. from the founder extension login).

**Steps:**
1. Open FB Ads Library in one tab, vizualizd in another
2. Trigger a magic link (from founder extension or direct)
3. Click the magic link in email

**Expected:**
- [ ] Vizualizd tab shows "You're verified!" briefly
- [ ] Browser auto-switches to the FB Ads Library tab
- [ ] Window focuses

---

## Test 7: Analytics Events

After running any test above, check the `extension_events` table in the database.

**Expected events recorded:**
- [ ] `extension_opened`
- [ ] `analysis_started` (with `cached: true` for Test 5)
- [ ] `client_matched` (Test 1)
- [ ] `gate_shown` (Tests 2, 3, 4)
- [ ] `email_submitted` (Tests 2, 3, 4)
- [ ] `gate_lifted` (Tests 2, 4)
- [ ] `analysis_completed`
- [ ] `auto_import_fired`
- [ ] `opportunity_shown` (if score >= 5)

---

## Test 8: Founder Extension Unchanged

**Steps:**
1. Open the founder extension (not public) on any FB Ads Library page
2. Run analysis

**Expected:**
- [ ] Login required as before
- [ ] Import button visible with client dropdown
- [ ] Full analysis streams
- [ ] No gate, no domain matching
- [ ] Everything works exactly as before
