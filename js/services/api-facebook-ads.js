/**
 * Facebook Ads API Service
 * Handles all API calls for Facebook ads CRUD operations.
 * Follows service pattern - returns promises, no DOM manipulation.
 */

/**
 * Get the API base URL
 * @returns {string} API base URL
 */
function getApiBaseUrl() {
    return window.APP_CONFIG?.API_BASE_URL || 'http://localhost:8000';
}

/**
 * Get authentication headers
 * @returns {Object} Headers object with Authorization
 */
function getAuthHeaders() {
    if (typeof window.Auth !== 'undefined' && typeof window.Auth.getAuthHeaders === 'function') {
        return window.Auth.getAuthHeaders();
    }
    if (typeof window.getAuthHeaders === 'function') {
        return window.getAuthHeaders();
    }
    return {};
}

/**
 * Handle API response errors
 * @param {Response} response - Fetch response object
 * @throws {Error} If response is not ok
 */
async function handleResponseError(response) {
    if (response.status === 401 || response.status === 403) {
        if (window.Auth?.showLogin) {
            window.Auth.showLogin();
        }
        throw new Error('Authentication required');
    }
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || `Request failed: ${response.status}`);
    }
}

/**
 * Fetch all Facebook ads for a client
 * @param {string} clientId - Client UUID
 * @returns {Promise<Object>} Object with items array and total count
 */
export async function fetchFacebookAds(clientId) {
    const response = await fetch(
        `${getApiBaseUrl()}/api/clients/${clientId}/facebook-ads`,
        { headers: getAuthHeaders() }
    );
    
    await handleResponseError(response);
    return response.json();
}

/**
 * Create a new Facebook ad
 * @param {string} clientId - Client UUID
 * @param {Object} adData - Ad data object
 * @param {string} adData.primary_text - Main ad copy
 * @param {string} adData.headline - Ad headline
 * @param {string} adData.call_to_action - CTA (SHOP_NOW, LEARN_MORE, etc.)
 * @param {Object} adData.full_json - Complete JSON for FB API
 * @param {string} [adData.description] - Ad description
 * @param {string} [adData.destination_url] - Link URL
 * @param {null} [adData.image_hash] - Deprecated, always null
 * @param {Array<string>} [adData.voc_evidence] - VoC quotes
 * @param {string} [adData.insight_id] - Link to insight
 * @param {string} [adData.action_id] - Link to source action
 * @returns {Promise<Object>} Created ad object
 */
export async function createFacebookAd(clientId, adData) {
    const response = await fetch(
        `${getApiBaseUrl()}/api/clients/${clientId}/facebook-ads`,
        {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(adData)
        }
    );
    
    await handleResponseError(response);
    return response.json();
}

/**
 * Update a Facebook ad (e.g., change status)
 * @param {string} adId - Ad UUID
 * @param {Object} updateData - Fields to update
 * @returns {Promise<Object>} Updated ad object
 */
export async function updateFacebookAd(adId, updateData) {
    const response = await fetch(
        `${getApiBaseUrl()}/api/facebook-ads/${adId}`,
        {
            method: 'PATCH',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updateData)
        }
    );
    
    await handleResponseError(response);
    return response.json();
}

/**
 * Delete a Facebook ad
 * @param {string} adId - Ad UUID
 * @returns {Promise<void>}
 */
export async function deleteFacebookAd(adId) {
    const response = await fetch(
        `${getApiBaseUrl()}/api/facebook-ads/${adId}`,
        {
            method: 'DELETE',
            headers: getAuthHeaders()
        }
    );
    
    await handleResponseError(response);
    // 204 No Content - no body to parse
}
