import express from "express";
import { verifyWebhookHmac } from "../services/shopify/webhook-service.js";
import { normalizeShopForOAuth } from "../services/shopify/oauth-service.js";
import { syncStoreConnection } from "../services/fastapi/store-connection-service.js";

export function registerWebhookRoutes(app, config) {
  app.post("/webhooks/app/uninstalled", express.raw({ type: "*/*", limit: "1mb" }), async (req, res) => {
    const isValid = verifyWebhookHmac(
      req.body,
      req.headers["x-shopify-hmac-sha256"],
      config.shopifyApiSecret,
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
        backendBaseUrl: config.backendBaseUrl,
        ingestSecret: config.ingestSecret,
        shopDomain,
        status: "uninstalled",
        uninstalledAt: new Date().toISOString(),
        clearOfflineToken: true,
        timeoutMs: config.storeSyncTimeoutMs,
      });
    } catch (error) {
      console.error("[SHOPIFY_OAUTH] failed to sync uninstall", { shopDomain, error });
    }
    res.status(200).send("ok");
  });
}
