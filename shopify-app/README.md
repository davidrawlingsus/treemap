# Shopify Thank-You Survey App

This folder contains a separate Shopify app service and checkout UI extension scaffold for collecting post-purchase survey answers on the Thank You page.

## What is included

- `server/`: App service API for receiving extension submissions and forwarding normalized payloads to vizualizd backend.
- `extensions/thank-you-survey/`: Checkout UI extension scaffold targeting `purchase.thank-you.block.render`.
- `shopify.app.toml`: Shopify app config scaffold.

## Environment variables

Copy `.env.example` to `.env` and configure:

- `SHOPIFY_API_KEY`
- `SHOPIFY_API_SECRET`
- `SHOPIFY_APP_URL`
- `SHOPIFY_WEBHOOK_SECRET`
- `VIZUALIZD_BACKEND_URL`
- `VIZUALIZD_SHOPIFY_INGEST_SECRET`
- `SHOPIFY_SURVEY_FORWARD_TIMEOUT_MS`

## Dev run

```bash
npm install
npm run dev
```

This scaffold keeps Shopify-specific runtime/tooling isolated from the existing vizualizd frontend architecture.

## Dev store E2E checklist

1. Run backend migration `062_add_shopify_survey_tables`.
2. Start vizualizd backend with `SHOPIFY_INGEST_SHARED_SECRET` configured.
3. Start Shopify app service from this directory with matching `VIZUALIZD_SHOPIFY_INGEST_SECRET`.
4. Install the public app on a Shopify development store.
5. Add the `thank-you-survey` block in Checkout editor.
6. Configure extension settings including `api_base_url`.
7. Place a test order and submit the multi-step survey.
8. Verify row creation in:
   - `shopify_survey_responses_raw`
   - `shopify_store_connections` mapping is applied to `client_uuid`
9. Open `/founder_shopify_survey.html` and verify:
   - store mapping list is visible
   - raw submission row appears with expected shop/order/survey fields
