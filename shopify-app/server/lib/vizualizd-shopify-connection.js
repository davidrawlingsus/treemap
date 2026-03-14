function normalizeShopDomain(value) {
  return String(value || "").trim().toLowerCase();
}

function getRequiredConfig({ backendBaseUrl, ingestSecret }) {
  const baseUrl = String(backendBaseUrl || "").replace(/\/$/, "");
  const secret = String(ingestSecret || "").trim();
  if (!baseUrl) {
    throw new Error("VIZUALIZD_BACKEND_URL is required");
  }
  if (!secret) {
    throw new Error("VIZUALIZD_SHOPIFY_INGEST_SECRET is required");
  }
  return { baseUrl, secret };
}

export async function syncStoreConnection({
  backendBaseUrl,
  ingestSecret,
  shopDomain,
  status,
  installedAt = null,
  uninstalledAt = null,
  offlineAccessToken = null,
  offlineAccessScopes = null,
  clearOfflineToken = false,
  timeoutMs = 10000,
}) {
  const { baseUrl, secret } = getRequiredConfig({ backendBaseUrl, ingestSecret });
  const normalizedShopDomain = normalizeShopDomain(shopDomain);
  if (!normalizedShopDomain) {
    throw new Error("shopDomain is required");
  }

  const controller = new AbortController();
  const timeoutHandle = setTimeout(() => controller.abort(), timeoutMs);
  const endpoint = `${baseUrl}/api/shopify/store-connections/sync`;
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Vizualizd-Shopify-Secret": secret,
      },
      body: JSON.stringify({
        shop_domain: normalizedShopDomain,
        status: String(status || "active"),
        installed_at: installedAt,
        uninstalled_at: uninstalledAt,
        offline_access_token: offlineAccessToken,
        offline_access_scopes: offlineAccessScopes,
        clear_offline_token: Boolean(clearOfflineToken),
      }),
      signal: controller.signal,
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body?.detail || `Failed store sync (${response.status})`);
    }
    return response.json().catch(() => ({ ok: true }));
  } finally {
    clearTimeout(timeoutHandle);
  }
}

export async function fetchStoreOfflineToken({
  backendBaseUrl,
  ingestSecret,
  shopDomain,
  timeoutMs = 7000,
}) {
  const { baseUrl, secret } = getRequiredConfig({ backendBaseUrl, ingestSecret });
  const normalizedShopDomain = normalizeShopDomain(shopDomain);
  if (!normalizedShopDomain) {
    return { hasOfflineAccessToken: false, offlineAccessToken: null, offlineAccessScopes: null };
  }
  const controller = new AbortController();
  const timeoutHandle = setTimeout(() => controller.abort(), timeoutMs);
  const endpoint = `${baseUrl}/api/shopify/store-connections/${encodeURIComponent(normalizedShopDomain)}/offline-token`;
  try {
    const response = await fetch(endpoint, {
      method: "GET",
      headers: {
        "X-Vizualizd-Shopify-Secret": secret,
      },
      signal: controller.signal,
    });
    if (response.status === 404) {
      return { hasOfflineAccessToken: false, offlineAccessToken: null, offlineAccessScopes: null };
    }
    if (!response.ok) {
      return { hasOfflineAccessToken: false, offlineAccessToken: null, offlineAccessScopes: null };
    }
    const body = await response.json().catch(() => ({}));
    return {
      hasOfflineAccessToken: Boolean(body?.has_offline_access_token),
      offlineAccessToken: body?.offline_access_token || null,
      offlineAccessScopes: body?.offline_access_scopes || null,
    };
  } finally {
    clearTimeout(timeoutHandle);
  }
}
