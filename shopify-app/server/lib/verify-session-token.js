import { jwtVerify } from "jose";

function normalizeShopDomain(value) {
  return String(value || "").trim().toLowerCase();
}

export async function verifySessionToken(token, expectedShopDomain, apiSecret) {
  if (!token) {
    throw new Error("Missing session token");
  }
  if (!apiSecret) {
    throw new Error("Shopify API secret is not configured");
  }

  const secretKey = new TextEncoder().encode(apiSecret);
  const { payload } = await jwtVerify(token, secretKey, {
    algorithms: ["HS256"],
  });

  const destination = String(payload.dest || "");
  const destinationHost = destination.replace(/^https?:\/\//, "").toLowerCase();
  const tokenShopDomain = normalizeShopDomain(destinationHost.split("/")[0]);
  const requestedShopDomain = normalizeShopDomain(expectedShopDomain);

  if (!tokenShopDomain) {
    throw new Error("Session token missing destination shop");
  }
  if (requestedShopDomain && tokenShopDomain !== requestedShopDomain) {
    throw new Error("Session token shop does not match request");
  }

  return {
    shopDomain: tokenShopDomain,
    subject: String(payload.sub || ""),
    payload,
  };
}
