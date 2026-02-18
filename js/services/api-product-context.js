/**
 * API service for product context operations.
 */

/**
 * Fetch all product contexts for a client.
 * @param {string} clientId - The client UUID
 * @returns {Promise<Array>} List of product contexts
 */
export async function fetchProductContexts(clientId) {
    const API_BASE_URL = window.APP_CONFIG?.API_BASE_URL || 'http://localhost:8000';
    const headers = window.Auth?.getAuthHeaders() || {};

    const response = await fetch(`${API_BASE_URL}/api/clients/${clientId}/product-contexts`, { headers });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to load product contexts: ${response.status}`);
    }

    return response.json();
}

/**
 * Extract product context from a PDP URL. Does not persist.
 * @param {string} clientId - The client UUID
 * @param {string} url - PDP URL to fetch
 * @returns {Promise<{name: string, context_text: string, source_url: string}>}
 */
export async function extractProductContextFromUrl(clientId, url) {
    const API_BASE_URL = window.APP_CONFIG?.API_BASE_URL || 'http://localhost:8000';
    const headers = {
        ...window.Auth?.getAuthHeaders(),
        'Content-Type': 'application/json'
    };

    const response = await fetch(`${API_BASE_URL}/api/clients/${clientId}/product-contexts/extract-from-url`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ url })
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to extract: ${response.status}`);
    }

    return response.json();
}

/**
 * Create a new product context.
 * @param {string} clientId - The client UUID
 * @param {Object} data - { name, context_text, source_url }
 * @returns {Promise<Object>} Created product context
 */
export async function createProductContext(clientId, data) {
    const API_BASE_URL = window.APP_CONFIG?.API_BASE_URL || 'http://localhost:8000';
    const headers = {
        ...window.Auth?.getAuthHeaders(),
        'Content-Type': 'application/json'
    };

    const response = await fetch(`${API_BASE_URL}/api/clients/${clientId}/product-contexts`, {
        method: 'POST',
        headers,
        body: JSON.stringify(data)
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to create: ${response.status}`);
    }

    return response.json();
}

/**
 * Update a product context.
 * @param {string} clientId - The client UUID
 * @param {string} id - Product context UUID
 * @param {Object} data - { name?, context_text?, source_url? }
 * @returns {Promise<Object>} Updated product context
 */
export async function updateProductContext(clientId, id, data) {
    const API_BASE_URL = window.APP_CONFIG?.API_BASE_URL || 'http://localhost:8000';
    const headers = {
        ...window.Auth?.getAuthHeaders(),
        'Content-Type': 'application/json'
    };

    const response = await fetch(`${API_BASE_URL}/api/clients/${clientId}/product-contexts/${id}`, {
        method: 'PUT',
        headers,
        body: JSON.stringify(data)
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to update: ${response.status}`);
    }

    return response.json();
}

/**
 * Set a product context as live.
 * @param {string} clientId - The client UUID
 * @param {string} id - Product context UUID
 * @returns {Promise<Object>}
 */
export async function setProductContextLive(clientId, id) {
    const API_BASE_URL = window.APP_CONFIG?.API_BASE_URL || 'http://localhost:8000';
    const headers = window.Auth?.getAuthHeaders() || {};

    const response = await fetch(`${API_BASE_URL}/api/clients/${clientId}/product-contexts/${id}/set-live`, {
        method: 'PATCH',
        headers
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to set live: ${response.status}`);
    }

    return response.json();
}

/**
 * Delete a product context.
 * @param {string} clientId - The client UUID
 * @param {string} id - Product context UUID
 * @returns {Promise<void>}
 */
export async function deleteProductContext(clientId, id) {
    const API_BASE_URL = window.APP_CONFIG?.API_BASE_URL || 'http://localhost:8000';
    const headers = window.Auth?.getAuthHeaders() || {};

    const response = await fetch(`${API_BASE_URL}/api/clients/${clientId}/product-contexts/${id}`, {
        method: 'DELETE',
        headers
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to delete: ${response.status}`);
    }
}
