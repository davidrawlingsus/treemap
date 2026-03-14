import crypto from "node:crypto";

function normalizeShopDomain(value) {
  const raw = String(value || "").trim().toLowerCase();
  if (!raw) return "";
  if (!/^[a-z0-9][a-z0-9-]*\.myshopify\.com$/.test(raw)) return "";
  return raw;
}

function createHmacMessageFromQuery(queryParams) {
  const items = Object.entries(queryParams || {})
    .filter(([key]) => key !== "hmac" && key !== "signature")
    .map(([key, value]) => {
      if (Array.isArray(value)) {
        return value.map((entry) => `${key}=${entry}`).join("&");
      }
      return `${key}=${value}`;
    })
    .sort();
  return items.join("&");
}

export function generateOAuthState() {
  return crypto.randomBytes(16).toString("hex");
}

export function getShopifyInstallUrl({
  shopDomain,
  clientId,
  appUrl,
  scopes,
  state,
}) {
  const shop = normalizeShopDomain(shopDomain);
  if (!shop) {
    throw new Error("Invalid shop parameter");
  }
  const normalizedScopes = String(scopes || "")
    .split(",")
    .map((scope) => scope.trim())
    .filter(Boolean)
    .join(",");
  if (!clientId || !appUrl || !normalizedScopes || !state) {
    throw new Error("Missing OAuth configuration");
  }
  const redirectUri = `${String(appUrl).replace(/\/$/, "")}/auth/callback`;
  const url = new URL(`https://${shop}/admin/oauth/authorize`);
  url.searchParams.set("client_id", String(clientId));
  url.searchParams.set("scope", normalizedScopes);
  url.searchParams.set("redirect_uri", redirectUri);
  url.searchParams.set("state", state);
  return url.toString();
}

export function verifyOAuthHmac(queryParams, apiSecret) {
  const providedHmac = String(queryParams?.hmac || "");
  if (!providedHmac || !apiSecret) return false;
  const message = createHmacMessageFromQuery(queryParams);
  const digest = crypto.createHmac("sha256", apiSecret).update(message).digest("hex");
  try {
    return crypto.timingSafeEqual(Buffer.from(digest), Buffer.from(providedHmac));
  } catch (_error) {
    return false;
  }
}

export async function exchangeCodeForOfflineToken({
  shopDomain,
  code,
  clientId,
  clientSecret,
}) {
  const shop = normalizeShopDomain(shopDomain);
  if (!shop || !code || !clientId || !clientSecret) {
    throw new Error("Missing OAuth token exchange parameters");
  }
  const response = await fetch(`https://${shop}/admin/oauth/access_token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      client_id: clientId,
      client_secret: clientSecret,
      code,
    }),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok || !body?.access_token) {
    throw new Error(body?.error_description || body?.error || `OAuth exchange failed (${response.status})`);
  }
  return {
    accessToken: String(body.access_token),
    scope: String(body.scope || ""),
  };
}

export function normalizeShopForOAuth(value) {
  return normalizeShopDomain(value);
}
