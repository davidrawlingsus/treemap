import crypto from "node:crypto";

export function verifyWebhookHmac(rawBodyBuffer, hmacHeader, apiSecret) {
  const headerValue = String(hmacHeader || "");
  if (!rawBodyBuffer || !headerValue || !apiSecret) {
    return false;
  }
  const digest = crypto.createHmac("sha256", apiSecret).update(rawBodyBuffer).digest("base64");
  try {
    return crypto.timingSafeEqual(Buffer.from(digest), Buffer.from(headerValue));
  } catch (_error) {
    return false;
  }
}
