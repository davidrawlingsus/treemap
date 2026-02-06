/**
 * Meta Ads Library Import API Service
 * Handles API calls for importing media from Meta Ads Library.
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
 * Import media from Meta Ads Library URL
 * @param {string} clientId - Client UUID
 * @param {string} url - Meta Ads Library URL with view_all_page_id parameter
 * @returns {Promise<Object>} Object with imported count and media array
 */
export async function importFromMetaAdsLibrary(clientId, url) {
    const apiUrl = `${getApiBaseUrl()}/api/meta-ads-library/scrape?client_id=${encodeURIComponent(clientId)}`;
    
    const formData = new FormData();
    formData.append('url', url);
    
    const authHeaders = getAuthHeaders();
    const headers = {};
    if (authHeaders.Authorization) {
        headers.Authorization = authHeaders.Authorization;
    }
    
    const response = await fetch(apiUrl, {
        method: 'POST',
        headers: headers,
        body: formData
    });
    
    if (response.status === 401 || response.status === 403) {
        if (window.Auth?.showLogin) {
            window.Auth.showLogin();
        }
        throw new Error('Authentication required');
    }
    
    if (!response.ok) {
        const errorText = await response.text().catch(() => '');
        let errorData;
        try {
            errorData = JSON.parse(errorText);
        } catch {
            errorData = { detail: errorText || 'Import failed' };
        }
        
        let errorMessage = 'Import failed';
        if (errorData.detail) {
            if (typeof errorData.detail === 'string') {
                errorMessage = errorData.detail;
            } else if (Array.isArray(errorData.detail)) {
                errorMessage = errorData.detail.map(e => e.msg || e).join(', ');
            } else {
                errorMessage = JSON.stringify(errorData.detail);
            }
        } else if (errorData.error) {
            errorMessage = errorData.error;
        }
        
        throw new Error(errorMessage);
    }
    
    return response.json();
}
