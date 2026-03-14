import "dotenv/config";
import express from "express";
import { verifySessionToken } from "./lib/verify-session-token.js";
import { forwardSurveySubmission } from "./lib/forward-to-vizualizd.js";

const app = express();
app.use(express.json({ limit: "256kb" }));
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

const PORT = Number(process.env.PORT || 3100);
const SHOPIFY_API_SECRET = process.env.SHOPIFY_API_SECRET || "";
const VIZUALIZD_BACKEND_URL = process.env.VIZUALIZD_BACKEND_URL || "";
const VIZUALIZD_SHOPIFY_INGEST_SECRET = process.env.VIZUALIZD_SHOPIFY_INGEST_SECRET || "";
const SHOPIFY_SURVEY_FORWARD_TIMEOUT_MS = Number(process.env.SHOPIFY_SURVEY_FORWARD_TIMEOUT_MS || 10000);

app.get("/health", (_req, res) => {
  res.json({ status: "ok", service: "shopify-survey-service" });
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

    const ingestResult = await forwardSurveySubmission({
      backendBaseUrl: VIZUALIZD_BACKEND_URL,
      ingestSecret: VIZUALIZD_SHOPIFY_INGEST_SECRET,
      timeoutMs: SHOPIFY_SURVEY_FORWARD_TIMEOUT_MS,
      payload: normalizedPayload,
    });
    console.log("[SHOPIFY_SURVEY] forward success", {
      shop_domain: normalizedPayload.shop_domain,
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
