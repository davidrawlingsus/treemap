#!/bin/bash
# MapTheGap Public Extension — API Flow Tests
# Tests the backend endpoints that underpin all extension functionality.
# Run: bash chrome-extension-public/test-flows.sh
#
# Requires: FOUNDER_TOKEN env var (JWT from founder extension)
# Get it: open founder extension DevTools console → (await chrome.storage.local.get("vzd_token")).vzd_token

set -u

API="https://api.mapthegap.ai"
# API="http://localhost:8000"  # uncomment for local

PASS=0
FAIL=0
TOTAL=0

pass() { echo "  ✅ $1"; ((PASS++)); ((TOTAL++)); }
fail() { echo "  ❌ $1"; ((FAIL++)); ((TOTAL++)); }
header() { echo ""; echo "━━━ $1 ━━━"; }

# Check for founder token
if [ -z "${FOUNDER_TOKEN:-}" ]; then
  echo "❌ Set FOUNDER_TOKEN env var first:"
  echo '  export FOUNDER_TOKEN="eyJ..."'
  echo "  Get it from founder extension DevTools: (await chrome.storage.local.get('vzd_token')).vzd_token"
  exit 1
fi

# ═══════════════════════════════════════════════════════════
header "CLEANUP: Delete any existing test clients"
# ═══════════════════════════════════════════════════════════

for domain in "testflow.example.com" "ritual.com" "cellexialabs.com"; do
  CID=$(curl -s -X POST "$API/api/extension/check-domain" \
    -H "Content-Type: application/json" \
    -d "{\"destination_url\": \"https://$domain\"}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('client_id',''))" 2>/dev/null)
  if [ -n "$CID" ]; then
    curl -s -X DELETE "$API/api/extension/lead-client/$CID" \
      -H "Authorization: Bearer $FOUNDER_TOKEN" > /dev/null 2>&1 || true
    echo "  Cleaned up $domain ($CID)"
  fi
done

# ═══════════════════════════════════════════════════════════
header "TEST 1: Lead Webhook (creates client from Zapier)"
# ═══════════════════════════════════════════════════════════

RES=$(curl -s -X POST "$API/api/extension/lead-webhook" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Flow Co", "email": "test@testflow.example.com", "website_url": "https://www.testflow.example.com"}')

CREATED=$(echo "$RES" | python3 -c "import sys,json; print(json.load(sys.stdin).get('created', False))" 2>/dev/null)
CLIENT_ID=$(echo "$RES" | python3 -c "import sys,json; print(json.load(sys.stdin).get('client_id', ''))" 2>/dev/null)

if [ "$CREATED" = "True" ]; then
  pass "Lead webhook created client ($CLIENT_ID)"
else
  fail "Lead webhook did not create client: $RES"
fi

# ═══════════════════════════════════════════════════════════
header "TEST 2: Check Domain (warm lead detection)"
# ═══════════════════════════════════════════════════════════

# Exact domain
RES=$(curl -s -X POST "$API/api/extension/check-domain" \
  -H "Content-Type: application/json" \
  -d '{"destination_url": "https://testflow.example.com/page"}')
EXISTS=$(echo "$RES" | python3 -c "import sys,json; print(json.load(sys.stdin).get('exists', False))" 2>/dev/null)
if [ "$EXISTS" = "True" ]; then
  pass "check-domain: exact domain match"
else
  fail "check-domain: exact domain not found: $RES"
fi

# Subdomain match
RES=$(curl -s -X POST "$API/api/extension/check-domain" \
  -H "Content-Type: application/json" \
  -d '{"destination_url": "https://lp.testflow.example.com/landing"}')
EXISTS=$(echo "$RES" | python3 -c "import sys,json; print(json.load(sys.stdin).get('exists', False))" 2>/dev/null)
if [ "$EXISTS" = "True" ]; then
  pass "check-domain: subdomain (lp.) matches parent"
else
  fail "check-domain: subdomain not matched: $RES"
fi

# Non-existent domain
RES=$(curl -s -X POST "$API/api/extension/check-domain" \
  -H "Content-Type: application/json" \
  -d '{"destination_url": "https://doesnotexist12345.com"}')
EXISTS=$(echo "$RES" | python3 -c "import sys,json; print(json.load(sys.stdin).get('exists', False))" 2>/dev/null)
if [ "$EXISTS" = "False" ]; then
  pass "check-domain: non-existent domain returns false"
else
  fail "check-domain: non-existent domain should be false: $RES"
fi

# ═══════════════════════════════════════════════════════════
header "TEST 3: Register Lead (domain-matched email)"
# ═══════════════════════════════════════════════════════════

# Matching domain
RES=$(curl -s -X POST "$API/api/extension/register-lead" \
  -H "Content-Type: application/json" \
  -d '{"email": "jane@testflow.example.com", "destination_url": "https://lp.testflow.example.com/page"}')
TOKEN=$(echo "$RES" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)
if [ -n "$TOKEN" ] && [ "$TOKEN" != "None" ]; then
  pass "register-lead: domain match → got JWT token"
  LEAD_TOKEN="$TOKEN"
else
  fail "register-lead: no token returned: $RES"
  LEAD_TOKEN=""
fi

# Mismatched domain
RES=$(curl -s -w "\n%{http_code}" -X POST "$API/api/extension/register-lead" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@gmail.com", "destination_url": "https://testflow.example.com"}')
HTTP=$(echo "$RES" | tail -1)
if [ "$HTTP" = "400" ]; then
  pass "register-lead: domain mismatch → rejected (400)"
else
  fail "register-lead: domain mismatch should be 400, got $HTTP"
fi

# ═══════════════════════════════════════════════════════════
header "TEST 4: Whitelist Override"
# ═══════════════════════════════════════════════════════════

RES=$(curl -s -X POST "$API/api/extension/register-lead" \
  -H "Content-Type: application/json" \
  -d '{"email": "david@rawlings.us", "destination_url": "https://somerandomsite.com"}')
TOKEN=$(echo "$RES" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)
if [ -n "$TOKEN" ] && [ "$TOKEN" != "None" ]; then
  pass "whitelist: david@rawlings.us bypasses domain match"
else
  DETAIL=$(echo "$RES" | python3 -c "import sys,json; print(json.load(sys.stdin).get('detail', ''))" 2>/dev/null)
  if echo "$DETAIL" | grep -q "must match"; then
    fail "whitelist: david@rawlings.us was rejected — is EXTENSION_WHITELIST_EMAILS set on Railway?"
  else
    fail "whitelist: unexpected error: $RES"
  fi
fi

# ═══════════════════════════════════════════════════════════
header "TEST 5: Token Validity (register-lead JWT works with API)"
# ═══════════════════════════════════════════════════════════

if [ -n "${LEAD_TOKEN:-}" ]; then
  RES=$(curl -s -w "\n%{http_code}" "$API/api/auth/me" \
    -H "Authorization: Bearer $LEAD_TOKEN")
  HTTP=$(echo "$RES" | tail -1)
  BODY=$(echo "$RES" | head -1)
  if [ "$HTTP" = "200" ]; then
    EMAIL=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('email', ''))" 2>/dev/null)
    pass "JWT from register-lead is valid (user: $EMAIL)"
  else
    fail "JWT from register-lead failed /api/auth/me: HTTP $HTTP"
  fi
else
  fail "JWT validity: skipped (no token from test 3)"
fi

# ═══════════════════════════════════════════════════════════
header "TEST 6: Client Matching (authenticated)"
# ═══════════════════════════════════════════════════════════

if [ -n "${LEAD_TOKEN:-}" ]; then
  RES=$(curl -s -X POST "$API/api/extension/match-client" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $LEAD_TOKEN" \
    -d '{"destination_url": "https://lp.testflow.example.com/page"}')
  MATCHED=$(echo "$RES" | python3 -c "import sys,json; print(json.load(sys.stdin).get('matched', False))" 2>/dev/null)
  if [ "$MATCHED" = "True" ]; then
    pass "match-client: authenticated user matches their client"
  else
    fail "match-client: should match but didn't: $RES"
  fi
else
  fail "match-client: skipped (no token)"
fi

# ═══════════════════════════════════════════════════════════
header "TEST 7: Analytics Tracking"
# ═══════════════════════════════════════════════════════════

RES=$(curl -s -w "\n%{http_code}" -X POST "$API/api/extension/track" \
  -H "Content-Type: application/json" \
  -d '{"event": "extension_opened", "session_id": "test-session-123", "advertiser_domain": "testflow.example.com"}')
HTTP=$(echo "$RES" | tail -1)
if [ "$HTTP" = "200" ]; then
  pass "track: extension_opened event recorded"
else
  fail "track: HTTP $HTTP"
fi

# Invalid event
RES=$(curl -s -w "\n%{http_code}" -X POST "$API/api/extension/track" \
  -H "Content-Type: application/json" \
  -d '{"event": "fake_event", "session_id": "test-session-123"}')
HTTP=$(echo "$RES" | tail -1)
if [ "$HTTP" = "400" ]; then
  pass "track: invalid event rejected (400)"
else
  fail "track: invalid event should be 400, got $HTTP"
fi

# ═══════════════════════════════════════════════════════════
header "TEST 8: Analysis Endpoints (anonymous access)"
# ═══════════════════════════════════════════════════════════

# detect-reviews without auth
RES=$(curl -s -w "\n%{http_code}" -X POST "$API/api/extension/detect-reviews" \
  -H "Content-Type: application/json" \
  -d '{"destination_url": "https://ritual.com"}')
HTTP=$(echo "$RES" | tail -1)
if [ "$HTTP" = "200" ]; then
  pass "detect-reviews: works without auth"
else
  fail "detect-reviews: HTTP $HTTP (should work anonymously)"
fi

# ═══════════════════════════════════════════════════════════
header "TEST 9: Cached Analysis"
# ═══════════════════════════════════════════════════════════

if [ -n "${LEAD_TOKEN:-}" ]; then
  # Should return not cached (no import exists yet)
  RES=$(curl -s "$API/api/extension/cached-analysis?advertiser_url=https://testflow.example.com" \
    -H "Authorization: Bearer $LEAD_TOKEN")
  CACHED=$(echo "$RES" | python3 -c "import sys,json; print(json.load(sys.stdin).get('cached', True))" 2>/dev/null)
  if [ "$CACHED" = "False" ]; then
    pass "cached-analysis: returns false when no import exists"
  else
    fail "cached-analysis: should be false: $RES"
  fi
else
  fail "cached-analysis: skipped (no token)"
fi

# ═══════════════════════════════════════════════════════════
header "TEST 10: Marketing Subdomain Stripping"
# ═══════════════════════════════════════════════════════════

# detect-reviews with lp. subdomain should strip to root
RES=$(curl -s -X POST "$API/api/extension/detect-reviews" \
  -H "Content-Type: application/json" \
  -d '{"destination_url": "https://lp.ritual.com/landing"}')
DOMAIN=$(echo "$RES" | python3 -c "import sys,json; print(json.load(sys.stdin).get('company_domain', ''))" 2>/dev/null)
if [ "$DOMAIN" = "ritual.com" ]; then
  pass "subdomain stripping: lp.ritual.com → ritual.com"
else
  fail "subdomain stripping: expected ritual.com, got $DOMAIN"
fi

# ═══════════════════════════════════════════════════════════
header "CLEANUP: Delete test clients"
# ═══════════════════════════════════════════════════════════

for domain in "testflow.example.com" "somerandomsite.com"; do
  CID=$(curl -s -X POST "$API/api/extension/check-domain" \
    -H "Content-Type: application/json" \
    -d "{\"destination_url\": \"https://$domain\"}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('client_id',''))" 2>/dev/null)
  if [ -n "$CID" ]; then
    curl -s -X DELETE "$API/api/extension/lead-client/$CID" \
      -H "Authorization: Bearer $FOUNDER_TOKEN" > /dev/null 2>&1 || true
    echo "  Cleaned up $domain"
  fi
done

# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Results: $PASS passed, $FAIL failed, $TOTAL total"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
