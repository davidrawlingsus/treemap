import { getBaseUrl } from './api-config.js';

function buildQuery(params = {}) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
        if (value === undefined || value === null || value === '') return;
        query.append(key, String(value));
    });
    const queryString = query.toString();
    return queryString ? `?${queryString}` : '';
}

async function request(path, options = {}) {
    const apiBaseUrl = getBaseUrl();
    const response = await fetch(`${apiBaseUrl}${path}`, {
        ...options,
        headers: {
            ...(window.Auth?.getAuthHeaders?.() || {}),
            'Content-Type': 'application/json',
            ...(options.headers || {}),
        },
    });

    if (!response.ok) {
        let detail = `Request failed (${response.status})`;
        try {
            const body = await response.json();
            if (body?.detail) detail = body.detail;
        } catch (_error) {
            // Keep fallback detail.
        }
        throw new Error(detail);
    }

    if (response.status === 204) return null;
    return response.json();
}

export async function fetchShopifyStoreConnections() {
    return request('/api/founder-admin/shopify/store-connections', { method: 'GET' });
}

export async function upsertShopifyStoreConnection(payload) {
    return request('/api/founder-admin/shopify/store-connections', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

export async function deleteShopifyStoreConnection(shopDomain) {
    const safeShopDomain = encodeURIComponent(shopDomain);
    return request(`/api/founder-admin/shopify/store-connections/${safeShopDomain}`, {
        method: 'DELETE',
    });
}

export async function fetchShopifyRawResponses({ clientUuid, shopDomain, limit = 100, offset = 0 } = {}) {
    const query = buildQuery({
        client_uuid: clientUuid,
        shop_domain: shopDomain,
        limit,
        offset,
    });
    return request(`/api/founder-admin/shopify/survey-responses/raw${query}`, { method: 'GET' });
}

export async function fetchVocClients() {
    return request('/api/voc/clients', { method: 'GET' });
}
