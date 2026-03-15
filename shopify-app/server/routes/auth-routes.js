import {
  exchangeCodeForOfflineToken,
  generateOAuthState,
  getShopifyInstallUrl,
  normalizeShopForOAuth,
  verifyOAuthHmac,
} from "../services/shopify/oauth-service.js";
import { syncStoreConnection } from "../services/fastapi/store-connection-service.js";

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

export function registerAuthRoutes(app, config) {
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
        clientId: config.shopifyApiKey,
        appUrl: config.shopifyAppUrl,
        scopes: config.shopifyScopes,
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
    if (!verifyOAuthHmac(req.query, config.shopifyApiSecret)) {
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
        clientId: config.shopifyApiKey,
        clientSecret: config.shopifyApiSecret,
      });
      await syncStoreConnection({
        backendBaseUrl: config.backendBaseUrl,
        ingestSecret: config.ingestSecret,
        shopDomain: shop,
        status: "active",
        installedAt: new Date().toISOString(),
        offlineAccessToken: tokenResult.accessToken,
        offlineAccessScopes: tokenResult.scope,
        clearOfflineToken: false,
        timeoutMs: config.storeSyncTimeoutMs,
      });
      res.setHeader("Set-Cookie", buildOAuthStateCookie(""));
      res.status(200).send("MapTheGap app installed successfully. You can now close this tab.");
    } catch (error) {
      console.error("[SHOPIFY_OAUTH] callback failed", error);
      res.status(400).send(error instanceof Error ? error.message : "OAuth callback failed");
    }
  });
}
