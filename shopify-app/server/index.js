import "dotenv/config";
import express from "express";
import { verifySessionToken } from "./lib/verify-session-token.js";
import { forwardSurveySubmission } from "./lib/forward-to-vizualizd.js";
import { enrichOrderContext, parseAdminTokensMap } from "./lib/enrich-order-context.js";
import {
  exchangeCodeForOfflineToken,
  generateOAuthState,
  getShopifyInstallUrl,
  normalizeShopForOAuth,
  verifyOAuthHmac,
} from "./lib/shopify-oauth.js";
import { verifyWebhookHmac } from "./lib/verify-webhook-hmac.js";
import { fetchStoreOfflineToken, syncStoreConnection } from "./lib/vizualizd-shopify-connection.js";

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
const SHOP_ADMIN_TOKENS_BY_SHOP = parseAdminTokensMap(SHOPIFY_ADMIN_ACCESS_TOKENS_JSON);

function readCookie(req, key) {
  const cookieHeader = String(req.headers.cookie || "");
  const cookiePairs = cookieHeader.split(";").map((entry) => entry.trim());
  for (const pair of cookiePairs) {
    if (!pair) continue;
    const [name, ...rest] = pair.split("=");
    if (name === key) {
      return decodeURIComponent(rest.join("="));
    }
  }
  return "";
}

function buildOAuthStateCookie(value) {
  return `shopify_oauth_state=${encodeURIComponent(value)}; Path=/; HttpOnly; SameSite=Lax; Max-Age=600`;
}

app.use((req, res, next) => {
  res.header("Access-Control-Allow-Origin", "*");
  res.header("Access-Control-Allow-Headers", "Authorization,Content-Type");
  res.header("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  if (req.method === "OPTIONS") {
    res.status(204).end();
    return;
  }
  next();
});

app.post("/webhooks/app/uninstalled", express.raw({ type: "*/*", limit: "1mb" }), async (req, res) => {
  const isValid = verifyWebhookHmac(
    req.body,
    req.headers["x-shopify-hmac-sha256"],
    SHOPIFY_API_SECRET,
  );
  if (!isValid) {
    res.status(401).send("invalid webhook hmac");
    return;
  }
  const shopDomain = normalizeShopForOAuth(req.headers["x-shopify-shop-domain"]);
  if (!shopDomain) {
    res.status(400).send("missing shop domain");
    return;
  }
  try {
    await syncStoreConnection({
      backendBaseUrl: VIZUALIZD_BACKEND_URL,
      ingestSecret: VIZUALIZD_SHOPIFY_INGEST_SECRET,
      shopDomain,
      status: "uninstalled",
      uninstalledAt: new Date().toISOString(),
      clearOfflineToken: true,
      timeoutMs: SHOPIFY_STORE_SYNC_TIMEOUT_MS,
    });
  } catch (error) {
    console.error("[SHOPIFY_OAUTH] failed to sync uninstall", { shopDomain, error });
  }
  res.status(200).send("ok");
});

app.use(express.json({ limit: "256kb" }));

app.get("/health", (_req, res) => {
  res.json({ status: "ok", service: "shopify-survey-service" });
});

app.get("/auth", (req, res) => {
  try {
    const shop = normalizeShopForOAuth(req.query.shop);
    if (!shop) {
      res.status(400).send("Missing or invalid shop query parameter");
      return;
    }
    const state = generateOAuthState();
    const installUrl = getShopifyInstallUrl({
      shopDomain: shop,
      clientId: SHOPIFY_API_KEY,
      appUrl: SHOPIFY_APP_URL,
      scopes: SHOPIFY_SCOPES,
      state,
    });
    res.setHeader("Set-Cookie", buildOAuthStateCookie(state));
    res.redirect(302, installUrl);
  } catch (error) {
    res.status(500).send(error instanceof Error ? error.message : "OAuth init failed");
  }
});

app.get("/auth/callback", async (req, res) => {
  const stateFromCookie = readCookie(req, "shopify_oauth_state");
  const stateFromQuery = String(req.query.state || "");
  if (!stateFromCookie || !stateFromQuery || stateFromCookie !== stateFromQuery) {
    res.status(400).send("Invalid OAuth state");
    return;
  }
  if (!verifyOAuthHmac(req.query, SHOPIFY_API_SECRET)) {
    res.status(401).send("Invalid OAuth signature");
    return;
  }
  const shop = normalizeShopForOAuth(req.query.shop);
  const code = String(req.query.code || "");
  if (!shop || !code) {
    res.status(400).send("Missing OAuth shop/code");
    return;
  }

  try {
    const tokenResult = await exchangeCodeForOfflineToken({
      shopDomain: shop,
      code,
      clientId: SHOPIFY_API_KEY,
      clientSecret: SHOPIFY_API_SECRET,
    });
    await syncStoreConnection({
      backendBaseUrl: VIZUALIZD_BACKEND_URL,
      ingestSecret: VIZUALIZD_SHOPIFY_INGEST_SECRET,
      shopDomain: shop,
      status: "active",
      installedAt: new Date().toISOString(),
      offlineAccessToken: tokenResult.accessToken,
      offlineAccessScopes: tokenResult.scope,
      clearOfflineToken: false,
      timeoutMs: SHOPIFY_STORE_SYNC_TIMEOUT_MS,
    });
    res.setHeader("Set-Cookie", buildOAuthStateCookie(""));
    res.status(200).send("MapTheGap app installed successfully. You can now close this tab.");
  } catch (error) {
    console.error("[SHOPIFY_OAUTH] callback failed", error);
    res.status(400).send(error instanceof Error ? error.message : "OAuth callback failed");
  }
});

app.post("/api/checkout-survey/submit", async (req, res) => {
  const authHeader = String(req.headers.authorization || "");
  const bearerToken = authHeader.startsWith("Bearer ") ? authHeader.slice(7) : "";
  const requestBody = req.body || {};
  console.log("[SHOPIFY_SURVEY] submit received", {
    shop_domain: requestBody.shop_domain || null,
    has_auth_header: Boolean(bearerToken),
    has_answers: Boolean(requestBody.answers),
  });

  try {
    const verified = await verifySessionToken(
      bearerToken,
      requestBody.shop_domain,
      SHOPIFY_API_SECRET,
    );

    const normalizedPayload = {
      shop_domain: verified.shopDomain,
      idempotency_key: String(requestBody.idempotency_key || ""),
      shopify_order_id: requestBody.shopify_order_id || null,
      order_gid: requestBody.order_gid || null,
      customer_reference: requestBody.customer_reference || null,
      survey_version: String(requestBody.survey_version || "v1"),
      answers: requestBody.answers || {},
      extension_context: {
        ...(requestBody.extension_context || {}),
        token_subject: verified.subject || null,
      },
      submitted_at: requestBody.submitted_at || new Date().toISOString(),
    };

    const backendToken = await fetchStoreOfflineToken({
      backendBaseUrl: VIZUALIZD_BACKEND_URL,
      ingestSecret: VIZUALIZD_SHOPIFY_INGEST_SECRET,
      shopDomain: normalizedPayload.shop_domain,
      timeoutMs: SHOPIFY_ADMIN_LOOKUP_TIMEOUT_MS,
    });
    const adminTokenForShop = backendToken.offlineAccessToken || SHOPIFY_ADMIN_ACCESS_TOKEN;
    const enrichment = await enrichOrderContext({
      shopDomain: normalizedPayload.shop_domain,
      orderGid: normalizedPayload.order_gid,
      shopifyOrderId: normalizedPayload.shopify_order_id,
      customerReference: normalizedPayload.customer_reference,
      adminApiVersion: SHOPIFY_ADMIN_API_VERSION,
      defaultAdminToken: adminTokenForShop,
      adminTokensByShop: SHOP_ADMIN_TOKENS_BY_SHOP,
      timeoutMs: SHOPIFY_ADMIN_LOOKUP_TIMEOUT_MS,
    });
    normalizedPayload.shopify_order_id = enrichment.shopifyOrderId;
    normalizedPayload.order_gid = enrichment.orderGid;
    normalizedPayload.customer_reference = enrichment.customerReference;
    normalizedPayload.extension_context = {
      ...(normalizedPayload.extension_context || {}),
      order_lookup_enriched: Boolean(enrichment.enriched),
      token_source: backendToken.offlineAccessToken ? "backend_store_connection" : "env_fallback",
    };

    const ingestResult = await forwardSurveySubmission({
      backendBaseUrl: VIZUALIZD_BACKEND_URL,
      ingestSecret: VIZUALIZD_SHOPIFY_INGEST_SECRET,
      timeoutMs: SHOPIFY_SURVEY_FORWARD_TIMEOUT_MS,
      payload: normalizedPayload,
    });
    console.log("[SHOPIFY_SURVEY] forward success", {
      shop_domain: normalizedPayload.shop_domain,
      shopify_order_id: normalizedPayload.shopify_order_id,
      customer_reference_present: Boolean(normalizedPayload.customer_reference),
      response_id: ingestResult?.id || null,
      deduplicated: Boolean(ingestResult?.deduplicated),
    });

    res.status(201).json({
      ok: true,
      forwarded: true,
      result: ingestResult,
    });
  } catch (error) {
    console.error("[SHOPIFY_SURVEY] submit failed", error);
    res.status(400).json({
      ok: false,
      detail: error instanceof Error ? error.message : "Failed to submit survey response",
    });
  }
});

app.listen(PORT, () => {
  console.log(`[SHOPIFY_SURVEY] Service listening on :${PORT}`);
});
