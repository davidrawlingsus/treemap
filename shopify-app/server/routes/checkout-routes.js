import {
  fetchActiveSurveyForCheckout,
  parseAdminTokenConfig,
  processSurveySubmission,
} from "../services/checkout/survey-runtime-service.js";

export function registerCheckoutRoutes(app, config) {
  const adminTokensByShop = parseAdminTokenConfig(config.shopifyAdminAccessTokensJson);

  app.get("/api/checkout-survey/active", async (req, res) => {
    const authHeader = String(req.headers.authorization || "");
    const bearerToken = authHeader.startsWith("Bearer ") ? authHeader.slice(7) : "";
    const expectedShopDomain = String(req.query.shop_domain || "");
    try {
      const result = await fetchActiveSurveyForCheckout({
        bearerToken,
        expectedShopDomain,
        apiSecret: config.shopifyApiSecret,
        backendBaseUrl: config.backendBaseUrl,
        ingestSecret: config.ingestSecret,
      });
      res.json({
        ok: true,
        shop_domain: result.shopDomain,
        survey: result.runtime?.survey || null,
      });
    } catch (error) {
      res.status(400).json({
        ok: false,
        detail: error instanceof Error ? error.message : "Failed to fetch active survey",
      });
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
      const { ingestResult, normalizedPayload } = await processSurveySubmission({
        bearerToken,
        requestBody,
        apiSecret: config.shopifyApiSecret,
        backendBaseUrl: config.backendBaseUrl,
        ingestSecret: config.ingestSecret,
        surveyForwardTimeoutMs: config.surveyForwardTimeoutMs,
        adminApiVersion: config.shopifyAdminApiVersion,
        defaultAdminAccessToken: config.shopifyAdminAccessToken,
        adminTokensByShop,
        adminLookupTimeoutMs: config.shopifyAdminLookupTimeoutMs,
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
}
