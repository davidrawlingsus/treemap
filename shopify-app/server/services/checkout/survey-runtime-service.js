import { enrichOrderContext, parseAdminTokensMap } from "../../lib/enrich-order-context.js";
import { forwardSurveySubmission } from "../../lib/forward-to-vizualizd.js";
import { verifySessionToken } from "../../lib/verify-session-token.js";
import { fetchStoreOfflineToken } from "../fastapi/store-connection-service.js";
import { getActiveRuntimeSurvey, ingestNormalizedSurveyResponse } from "../fastapi/survey-service.js";

export function parseAdminTokenConfig(rawJson) {
  return parseAdminTokensMap(rawJson);
}

export async function fetchActiveSurveyForCheckout({
  bearerToken,
  expectedShopDomain = "",
  apiSecret,
  backendBaseUrl,
  ingestSecret,
}) {
  const verified = await verifySessionToken(bearerToken, expectedShopDomain, apiSecret);
  const runtime = await getActiveRuntimeSurvey({
    backendBaseUrl,
    ingestSecret,
    shopDomain: verified.shopDomain,
  });
  return {
    shopDomain: verified.shopDomain,
    runtime,
  };
}

export async function processSurveySubmission({
  bearerToken,
  requestBody,
  apiSecret,
  backendBaseUrl,
  ingestSecret,
  surveyForwardTimeoutMs,
  adminApiVersion,
  defaultAdminAccessToken,
  adminTokensByShop,
  adminLookupTimeoutMs,
}) {
  const verified = await verifySessionToken(
    bearerToken,
    requestBody.shop_domain,
    apiSecret,
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
    backendBaseUrl,
    ingestSecret,
    shopDomain: normalizedPayload.shop_domain,
    timeoutMs: adminLookupTimeoutMs,
  });
  const adminTokenForShop = backendToken.offlineAccessToken || defaultAdminAccessToken;
  const enrichment = await enrichOrderContext({
    shopDomain: normalizedPayload.shop_domain,
    orderGid: normalizedPayload.order_gid,
    shopifyOrderId: normalizedPayload.shopify_order_id,
    customerReference: normalizedPayload.customer_reference,
    adminApiVersion,
    defaultAdminToken: adminTokenForShop,
    adminTokensByShop,
    timeoutMs: adminLookupTimeoutMs,
  });
  normalizedPayload.shopify_order_id = enrichment.shopifyOrderId;
  normalizedPayload.order_gid = enrichment.orderGid;
  normalizedPayload.customer_reference = enrichment.customerReference;
  normalizedPayload.extension_context = {
    ...(normalizedPayload.extension_context || {}),
    order_lookup_enriched: Boolean(enrichment.enriched),
    token_source: backendToken.offlineAccessToken ? "backend_store_connection" : "env_fallback",
  };

  const normalizedAnswerRows = Object.entries(normalizedPayload.answers || {}).map(([key, value]) => ({
    question_key: key,
    answer_text: String(value?.answer || ""),
    answer_json: value || {},
  }));

  const ingestResult = await ingestNormalizedSurveyResponse({
    backendBaseUrl,
    ingestSecret,
    payload: {
      shop_domain: normalizedPayload.shop_domain,
      idempotency_key: normalizedPayload.idempotency_key,
      survey_version_id: Number(requestBody.survey_version_id || 0) || null,
      survey_id: Number(requestBody.survey_id || 0) || null,
      shopify_order_id: normalizedPayload.shopify_order_id,
      order_gid: normalizedPayload.order_gid,
      customer_reference: normalizedPayload.customer_reference,
      answers: normalizedAnswerRows,
      extension_context: normalizedPayload.extension_context,
      submitted_at: normalizedPayload.submitted_at,
    },
    timeoutMs: surveyForwardTimeoutMs,
  });

  // Keep raw ingest for backward compatibility with existing reporting pipeline.
  await forwardSurveySubmission({
    backendBaseUrl,
    ingestSecret,
    timeoutMs: surveyForwardTimeoutMs,
    payload: normalizedPayload,
  });

  return {
    ingestResult,
    normalizedPayload,
  };
}
