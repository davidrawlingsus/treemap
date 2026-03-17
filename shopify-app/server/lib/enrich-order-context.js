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
        name
        legacyResourceId
        email
        tags
        discountCodes
        createdAt
        totalPriceSet { shopMoney { amount currencyCode } }
        subtotalPriceSet { shopMoney { amount currencyCode } }
        totalDiscountsSet { shopMoney { amount currencyCode } }
        totalShippingPriceSet { shopMoney { amount currencyCode } }
        customer {
          email
          ordersCount
          totalSpentV2 { amount currencyCode }
        }
        lineItems(first: 20) {
          edges {
            node {
              title
              variantTitle
              quantity
              sku
              vendor
              originalTotalSet { shopMoney { amount currencyCode } }
            }
          }
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

    const lineItems = (orderNode.lineItems?.edges || []).map(({ node }) => ({
      title: node.title || "",
      variant: node.variantTitle || null,
      quantity: node.quantity || 1,
      price: node.originalTotalSet?.shopMoney?.amount || null,
      currency: node.originalTotalSet?.shopMoney?.currencyCode || null,
      sku: node.sku || null,
      vendor: node.vendor || null,
    }));

    const orderContext = {
      order_name: orderNode.name || null,
      order_total: orderNode.totalPriceSet?.shopMoney?.amount || null,
      order_subtotal: orderNode.subtotalPriceSet?.shopMoney?.amount || null,
      order_discounts: orderNode.totalDiscountsSet?.shopMoney?.amount || null,
      order_shipping: orderNode.totalShippingPriceSet?.shopMoney?.amount || null,
      currency: orderNode.totalPriceSet?.shopMoney?.currencyCode || null,
      discount_codes: orderNode.discountCodes || [],
      tags: orderNode.tags || [],
      item_count: lineItems.reduce((sum, item) => sum + item.quantity, 0),
      line_items: lineItems,
      customer_email: enrichedEmail || null,
      customer_order_count: orderNode.customer?.ordersCount ?? null,
      customer_total_spent: orderNode.customer?.totalSpentV2?.amount || null,
    };

    return {
      orderGid: String(orderNode.id || resolvedOrderGid),
      shopifyOrderId: legacyResourceId || fallbackOrderId || parseLegacyResourceIdFromGid(resolvedOrderGid) || null,
      customerReference: enrichedEmail || fallbackCustomerReference,
      orderContext,
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
