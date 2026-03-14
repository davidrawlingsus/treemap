function normalizeShopDomain(value) {
  return String(value || "").trim().toLowerCase();
}

function normalizeOrderGid(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  if (raw.startsWith("gid://shopify/Order/")) return raw;
  if (/^\d+$/.test(raw)) return `gid://shopify/Order/${raw}`;
  return "";
}

function parseLegacyResourceIdFromGid(orderGid) {
  const gid = String(orderGid || "").trim();
  const match = gid.match(/^gid:\/\/shopify\/Order\/(\d+)$/);
  return match ? match[1] : "";
}

function getShopAdminToken(shopDomain, tokensByShop, defaultToken) {
  const normalizedShop = normalizeShopDomain(shopDomain);
  if (!normalizedShop) return "";
  if (tokensByShop[normalizedShop]) return tokensByShop[normalizedShop];
  return String(defaultToken || "").trim();
}

function getGraphQLEmail(orderNode) {
  if (!orderNode || typeof orderNode !== "object") return "";
  const customerEmail = String(orderNode?.customer?.email || "").trim();
  if (customerEmail) return customerEmail;
  return String(orderNode?.email || "").trim();
}

export function parseAdminTokensMap(rawJson) {
  if (!rawJson) return {};
  try {
    const parsed = JSON.parse(rawJson);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return {};
    }
    const normalized = {};
    Object.entries(parsed).forEach(([shop, token]) => {
      const shopDomain = normalizeShopDomain(shop);
      const tokenValue = String(token || "").trim();
      if (shopDomain && tokenValue) {
        normalized[shopDomain] = tokenValue;
      }
    });
    return normalized;
  } catch (_error) {
    return {};
  }
}

export async function enrichOrderContext({
  shopDomain,
  orderGid,
  shopifyOrderId,
  customerReference,
  adminApiVersion = "2026-01",
  defaultAdminToken = "",
  adminTokensByShop = {},
  timeoutMs = 7000,
}) {
  const resolvedOrderGid = normalizeOrderGid(orderGid || shopifyOrderId);
  const fallbackOrderId = String(shopifyOrderId || "").trim();
  const fallbackCustomerReference = String(customerReference || "").trim() || null;
  const token = getShopAdminToken(shopDomain, adminTokensByShop, defaultAdminToken);
  if (!resolvedOrderGid || !token) {
    return {
      orderGid: resolvedOrderGid || null,
      shopifyOrderId: fallbackOrderId || parseLegacyResourceIdFromGid(resolvedOrderGid) || null,
      customerReference: fallbackCustomerReference,
      enriched: false,
    };
  }

  const endpoint = `https://${normalizeShopDomain(shopDomain)}/admin/api/${adminApiVersion}/graphql.json`;
  const query = `
    query OrderForSurveyIngest($id: ID!) {
      order(id: $id) {
        id
        legacyResourceId
        email
        customer {
          email
        }
      }
    }
  `;
  const controller = new AbortController();
  const timeoutHandle = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": token,
      },
      body: JSON.stringify({
        query,
        variables: { id: resolvedOrderGid },
      }),
      signal: controller.signal,
    });

    const body = await response.json().catch(() => null);
    if (!response.ok) {
      return {
        orderGid: resolvedOrderGid,
        shopifyOrderId: fallbackOrderId || parseLegacyResourceIdFromGid(resolvedOrderGid) || null,
        customerReference: fallbackCustomerReference,
        enriched: false,
      };
    }
    const errors = Array.isArray(body?.errors) ? body.errors : [];
    const orderNode = body?.data?.order || null;
    if (errors.length || !orderNode) {
      return {
        orderGid: resolvedOrderGid,
        shopifyOrderId: fallbackOrderId || parseLegacyResourceIdFromGid(resolvedOrderGid) || null,
        customerReference: fallbackCustomerReference,
        enriched: false,
      };
    }

    const legacyResourceId = String(orderNode.legacyResourceId || "").trim();
    const enrichedEmail = getGraphQLEmail(orderNode);
    return {
      orderGid: String(orderNode.id || resolvedOrderGid),
      shopifyOrderId: legacyResourceId || fallbackOrderId || parseLegacyResourceIdFromGid(resolvedOrderGid) || null,
      customerReference: enrichedEmail || fallbackCustomerReference,
      enriched: true,
    };
  } catch (_error) {
    return {
      orderGid: resolvedOrderGid,
      shopifyOrderId: fallbackOrderId || parseLegacyResourceIdFromGid(resolvedOrderGid) || null,
      customerReference: fallbackCustomerReference,
      enriched: false,
    };
  } finally {
    clearTimeout(timeoutHandle);
  }
}
