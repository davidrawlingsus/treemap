import { verifySessionToken } from "../lib/verify-session-token.js";

export async function requireShopifySession(req, apiSecret, expectedShopDomain = "") {
  const authHeader = String(req.headers.authorization || "");
  const bearerToken = authHeader.startsWith("Bearer ") ? authHeader.slice(7) : "";
  const verified = await verifySessionToken(bearerToken, expectedShopDomain, apiSecret);
  return {
    bearerToken,
    shopDomain: verified.shopDomain,
    subject: verified.subject,
    payload: verified.payload,
  };
}
