import "dotenv/config";
import express from "express";
import { registerAuthRoutes } from "./routes/auth-routes.js";
import { registerAdminRoutes } from "./routes/admin-routes.js";
import { registerCheckoutRoutes } from "./routes/checkout-routes.js";
import { registerWebhookRoutes } from "./routes/webhook-routes.js";
import { registerCors } from "./middleware/cors.js";

const app = express();
const PORT = Number(process.env.PORT || 3100);
const SHOPIFY_API_KEY = String(process.env.SHOPIFY_API_KEY || "");
const SHOPIFY_API_SECRET = String(process.env.SHOPIFY_API_SECRET || "");
const SHOPIFY_APP_URL = String(process.env.SHOPIFY_APP_URL || "").replace(/\/$/, "");
const SHOPIFY_SCOPES = String(process.env.SHOPIFY_SCOPES || "read_orders");
const VIZUALIZD_BACKEND_URL = String(process.env.VIZUALIZD_BACKEND_URL || "");
const VIZUALIZD_SHOPIFY_INGEST_SECRET = String(process.env.VIZUALIZD_SHOPIFY_INGEST_SECRET || "");
const SHOPIFY_SURVEY_FORWARD_TIMEOUT_MS = Number(process.env.SHOPIFY_SURVEY_FORWARD_TIMEOUT_MS || 10000);
const SHOPIFY_ADMIN_API_VERSION = String(process.env.SHOPIFY_ADMIN_API_VERSION || "2026-01");
const SHOPIFY_ADMIN_ACCESS_TOKEN = String(process.env.SHOPIFY_ADMIN_ACCESS_TOKEN || "");
const SHOPIFY_ADMIN_ACCESS_TOKENS_JSON = String(process.env.SHOPIFY_ADMIN_ACCESS_TOKENS_JSON || "");
const SHOPIFY_ADMIN_LOOKUP_TIMEOUT_MS = Number(process.env.SHOPIFY_ADMIN_LOOKUP_TIMEOUT_MS || 7000);
const SHOPIFY_STORE_SYNC_TIMEOUT_MS = Number(process.env.SHOPIFY_STORE_SYNC_TIMEOUT_MS || 10000);
registerCors(app);
registerWebhookRoutes(app, {
  shopifyApiSecret: SHOPIFY_API_SECRET,
  backendBaseUrl: VIZUALIZD_BACKEND_URL,
  ingestSecret: VIZUALIZD_SHOPIFY_INGEST_SECRET,
  storeSyncTimeoutMs: SHOPIFY_STORE_SYNC_TIMEOUT_MS,
});

app.use(express.json({ limit: "256kb" }));

app.get("/health", (_req, res) => {
  res.json({ status: "ok", service: "shopify-survey-service" });
});

app.get("/", (req, res) => {
  const query = new URLSearchParams(req.query || {}).toString();
  res.redirect(query ? `/app?${query}` : "/app");
});

registerAuthRoutes(app, {
  shopifyApiKey: SHOPIFY_API_KEY,
  shopifyApiSecret: SHOPIFY_API_SECRET,
  shopifyAppUrl: SHOPIFY_APP_URL,
  shopifyScopes: SHOPIFY_SCOPES,
  backendBaseUrl: VIZUALIZD_BACKEND_URL,
  ingestSecret: VIZUALIZD_SHOPIFY_INGEST_SECRET,
  storeSyncTimeoutMs: SHOPIFY_STORE_SYNC_TIMEOUT_MS,
});

registerAdminRoutes(app, {
  shopifyApiKey: SHOPIFY_API_KEY,
  shopifyApiSecret: SHOPIFY_API_SECRET,
  backendBaseUrl: VIZUALIZD_BACKEND_URL,
  ingestSecret: VIZUALIZD_SHOPIFY_INGEST_SECRET,
});

registerCheckoutRoutes(app, {
  shopifyApiSecret: SHOPIFY_API_SECRET,
  backendBaseUrl: VIZUALIZD_BACKEND_URL,
  ingestSecret: VIZUALIZD_SHOPIFY_INGEST_SECRET,
  surveyForwardTimeoutMs: SHOPIFY_SURVEY_FORWARD_TIMEOUT_MS,
  shopifyAdminApiVersion: SHOPIFY_ADMIN_API_VERSION,
  shopifyAdminAccessToken: SHOPIFY_ADMIN_ACCESS_TOKEN,
  shopifyAdminAccessTokensJson: SHOPIFY_ADMIN_ACCESS_TOKENS_JSON,
  shopifyAdminLookupTimeoutMs: SHOPIFY_ADMIN_LOOKUP_TIMEOUT_MS,
});

app.listen(PORT, () => {
  console.log(`[SHOPIFY_SURVEY] Service listening on :${PORT}`);
});
