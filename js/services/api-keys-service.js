/**
 * API service for API key management.
 */

/**
 * List API keys for a client.
 * @param {string} clientId - The client UUID
 * @returns {Promise<Array>} List of API keys
 */
export async function fetchApiKeys(clientId) {
    const API_BASE_URL = window.APP_CONFIG?.API_BASE_URL || 'http://localhost:8000';
    const headers = window.Auth?.getAuthHeaders() || {};

    const response = await fetch(`${API_BASE_URL}/api/api-keys/?client_id=${clientId}`, {
        headers
    });

    if (!response.ok) {
        throw new Error(`Failed to load API keys: ${response.status}`);
    }

    return response.json();
}

/**
 * Create a new API key for a client.
 * @param {string} clientId - The client UUID
 * @param {string} name - Human label for the key
 * @returns {Promise<Object>} Created key (includes raw key shown once)
 */
export async function createApiKey(clientId, name) {
    const API_BASE_URL = window.APP_CONFIG?.API_BASE_URL || 'http://localhost:8000';
    const headers = {
        ...window.Auth?.getAuthHeaders(),
        'Content-Type': 'application/json'
    };

    const response = await fetch(`${API_BASE_URL}/api/api-keys/`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ client_id: clientId, name })
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to create API key: ${response.status}`);
    }

    return response.json();
}

/**
 * Revoke an API key.
 * @param {string} keyId - The API key UUID
 * @returns {Promise<void>}
 */
export async function revokeApiKey(keyId) {
    const API_BASE_URL = window.APP_CONFIG?.API_BASE_URL || 'http://localhost:8000';
    const headers = window.Auth?.getAuthHeaders() || {};

    const response = await fetch(`${API_BASE_URL}/api/api-keys/${keyId}`, {
        method: 'DELETE',
        headers
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to revoke API key: ${response.status}`);
    }
}
