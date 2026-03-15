# Shopify Survey Integration (MapTheGap)

This folder contains the Shopify-side runtime for the MapTheGap post-purchase survey:

- Checkout UI extension(s) shown on Thank You / Order Status pages
- App service used for OAuth install, webhook handling, and survey ingestion forwarding
- Config used by Shopify CLI deploy/release commands

This README is a handoff + build-on context doc for continuing work.

## Current architecture

1. Merchant installs app via OAuth (`/auth` -> `/auth/callback`).
2. App service exchanges OAuth code for offline token.
3. App service syncs shop/token state into vizualizd backend.
4. Merchant adds and configures `thank-you-survey` extension block in Checkout editor.
5. Customer submits survey in checkout extension UI.
6. App service validates session token, optionally enriches order context via Admin API, then forwards raw payload to backend.
7. Backend stores response in `shopify_survey_responses_raw`, linked to mapped client when available.

## Deployment topology (current)

- Public marketing/app handoff page: `https://vizualizd.mapthegap.ai/connect-shopify.html`
- Shopify app service (OAuth + ingest): `https://connect.mapthegap.ai`
- Vizualizd backend API: `https://api.mapthegap.ai`

## Files and responsibilities

- `shopify.app.toml`: Shopify app config (app URL, redirect URLs, scopes, API version)
- `extensions/thank-you-survey/`: checkout extension code + extension settings schema
- `server/index.js`: app service entrypoint that wires middleware and routes
- `server/routes/auth-routes.js`: OAuth install/callback endpoints
- `server/routes/webhook-routes.js`: webhook endpoints (app uninstall)
- `server/routes/checkout-routes.js`: checkout extension submit endpoint
- `server/middleware/cors.js`: CORS middleware
- `server/services/checkout/survey-runtime-service.js`: checkout submit orchestration (token verify, enrichment, forward)
- `server/services/fastapi/store-connection-service.js`: backend store sync/token access wrapper
- `server/services/shopify/oauth-service.js`: Shopify OAuth service wrapper
- `server/services/shopify/webhook-service.js`: Shopify webhook service wrapper
- `server/lib/`: low-level helpers retained for compatibility and shared logic (`verify-session-token`, `forward-to-vizualizd`, `enrich-order-context`, `shopify-oauth`, `verify-webhook-hmac`, `vizualizd-shopify-connection`)

Related backend files (outside this folder):

- `backend/app/routers/shopify/public.py`
- `backend/app/routers/shopify/__init__.py`
- `backend/app/routers/founder_admin/shopify/routes.py`
- `backend/app/routers/founder_admin/shopify/__init__.py`
- `backend/app/models/shopify/store_connection.py`
- `backend/app/models/shopify/survey_response_raw.py`
- `backend/app/schemas/shopify/__init__.py`
- `backend/app/services/shopify/security.py`
- `backend/alembic/versions/062_add_shopify_survey_tables.py`
- `backend/alembic/versions/063_add_shopify_offline_tokens.py`

## Public/merchant flows

### OAuth install flow

- `GET /auth?shop={shop}.myshopify.com`
  - Validates shop format
  - Generates state cookie
  - Redirects to Shopify authorize URL
- `GET /auth/callback`
  - Verifies state + Shopify HMAC
  - Exchanges code for offline token
  - Calls backend sync endpoint to upsert `shopify_store_connections` with token/scope/status

### Uninstall flow

- `POST /webhooks/app/uninstalled`
  - Verifies webhook HMAC
  - Marks shop as `uninstalled`
  - Clears offline token in backend store connection

### Survey submission flow

- Extension POSTs to `/api/checkout-survey/submit`
- App service:
  - verifies session JWT against `SHOPIFY_API_SECRET`
  - fetches per-shop offline token from backend
  - enriches order context (best effort)
  - forwards normalized payload to backend `/api/shopify/survey-responses/raw`

## Data model summary (backend)

### `shopify_store_connections`

- `shop_domain` (unique)
- optional `client_uuid` mapping
- install status/timestamps
- offline token fields:
  - `offline_access_token`
  - `offline_access_scopes`
  - `token_updated_at`

### `shopify_survey_responses_raw`

- one row per idempotent survey submit
- `answers_json` (raw answer payload)
- `extension_context_json` (source context + enrichment flags)
- optional linked `client_uuid`

## Environment variables

Copy `.env.example` to `.env` and configure values.

### Required

- `SHOPIFY_API_KEY`
- `SHOPIFY_API_SECRET`
- `SHOPIFY_APP_URL`
- `SHOPIFY_SCOPES` (currently `read_orders`)
- `VIZUALIZD_BACKEND_URL`
- `VIZUALIZD_SHOPIFY_INGEST_SECRET`

### Optional/tuning

- `SHOPIFY_SURVEY_FORWARD_TIMEOUT_MS` (default `10000`)
- `SHOPIFY_ADMIN_API_VERSION` (default `2026-01`)
- `SHOPIFY_ADMIN_ACCESS_TOKEN` (fallback only)
- `SHOPIFY_ADMIN_ACCESS_TOKENS_JSON` (legacy map fallback)
- `SHOPIFY_ADMIN_LOOKUP_TIMEOUT_MS` (default `7000`)
- `SHOPIFY_STORE_SYNC_TIMEOUT_MS` (default `10000`)

Example JSON map:

```json
{"store-a.myshopify.com":"shpat_xxx","store-b.myshopify.com":"shpat_yyy"}
```

## Commands

### Local dev

```bash
npm install
npm run dev
```

### Deploy Shopify config + extension

```bash
shopify app deploy --force
```

### Deploy app service to Railway

```bash
railway up --service shopify-app
```

## Connect page (no-store-name handoff helper)

The public page at `https://vizualizd.mapthegap.ai/connect-shopify.html`:

- accepts shop slug or full `.myshopify.com` domain
- redirects to app service `/auth?shop=...`
- gives a simple "Install app" entry point for testing/onboarding

Implementation is outside this folder:

- `connect-shopify.html`
- `styles/connect-shopify.css`
- `js/controllers/connect-shopify-controller.js`

## Security notes

- Ingest to backend is protected by `X-Vizualizd-Shopify-Secret`.
- OAuth callback validates state and HMAC.
- Uninstall webhook verifies HMAC.
- Checkout extension no longer sends client-side customer email; email enrichment is server-side best effort.

## Known constraints / current status

- Shopify extension version creation can show:
  - "New version created, but not released"
  - "Network access must be requested and approved"
  This is a Shopify review/approval gate for extension network access.

- App URL + redirect URL are intentionally neutral and do not include "shopify":
  - `https://connect.mapthegap.ai`
  - `https://connect.mapthegap.ai/auth/callback`

## Build-on checklist (next iteration)

1. Confirm Partner Dashboard distribution settings (unlisted/listed strategy).
2. Add richer merchant-facing install success page.
3. Add observability for OAuth/token sync failures (structured logs + alerts).
4. Add automated E2E test script for install -> submit -> DB verify.
5. Add downstream transformation from raw survey rows into analytics dimensions.
