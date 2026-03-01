/**
 * Ad Images API Service
 * Handles all API calls for ad images CRUD operations.
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
 * Upload an ad image
 * @param {string} clientId - Client UUID
 * @param {File} file - Image file
 * @returns {Promise<Object>} Uploaded image object with URL and metadata
 */
export async function uploadAdImage(clientId, file) {
    // First upload to Vercel Blob via server.js
    const formData = new FormData();
    formData.append('file', file);
    
    // Use backend API for blob upload (Python backend has the BLOB_READ_WRITE_TOKEN)
    const uploadUrl = `${getApiBaseUrl()}/api/upload-ad-image?client_id=${clientId}`;
    const uploadResponse = await fetch(uploadUrl, {
        method: 'POST',
        body: formData
    });
    
    if (!uploadResponse.ok) {
        const errorText = await uploadResponse.text().catch(() => '');
        let errorData;
        try {
            errorData = JSON.parse(errorText);
        } catch {
            errorData = { error: errorText || 'Upload failed' };
        }
        throw new Error(errorData.error || `Upload failed: ${uploadResponse.status}`);
    }
    
    const uploadData = await uploadResponse.json();
    
    // Then save metadata to backend database
    const formData2 = new FormData();
    formData2.append('url', uploadData.url || '');
    formData2.append('filename', uploadData.filename || '');
    formData2.append('file_size', (uploadData.file_size || 0).toString());
    formData2.append('content_type', uploadData.content_type || '');
    
    const apiUrl = `${getApiBaseUrl()}/api/clients/${clientId}/ad-images`;
    const authHeaders = getAuthHeaders();
    
    // For FormData, we must NOT set Content-Type - browser will set it with boundary
    // Only include Authorization header, not Content-Type
    const headers = {};
    if (authHeaders.Authorization) {
        headers.Authorization = authHeaders.Authorization;
    }
    
    const response = await fetch(apiUrl, {
        method: 'POST',
        headers: headers,
        body: formData2
    });
    
    if (!response.ok) {
        const errorText = await response.text().catch(() => '');
        let errorData;
        try {
            errorData = JSON.parse(errorText);
        } catch {
            errorData = { detail: errorText || 'Request failed' };
        }
        
        // Format FastAPI validation errors
        let errorMessage = 'Request failed';
        if (errorData.detail) {
            if (Array.isArray(errorData.detail)) {
                errorMessage = errorData.detail.map(e => `${e.loc?.join('.')}: ${e.msg}`).join(', ');
            } else if (typeof errorData.detail === 'string') {
                errorMessage = errorData.detail;
            } else {
                errorMessage = JSON.stringify(errorData.detail);
            }
        }
        
        if (response.status === 401 || response.status === 403) {
            if (window.Auth?.showLogin) {
                window.Auth.showLogin();
            }
            throw new Error('Authentication required');
        }
        
        throw new Error(errorMessage);
    }
    
    const result = await response.json();
    return result;
}

/**
 * Map frontend sort key to backend sort_by and order
 * @param {string} sortBy - Frontend: newest, oldest, running_longest, running_newest
 * @returns {{ sort_by: string, order: string }}
 */
function getSortParams(sortBy) {
    switch (sortBy) {
        case 'revenue_desc':
            return { sort_by: 'revenue', order: 'desc' };
        case 'revenue_asc':
            return { sort_by: 'revenue', order: 'asc' };
        case 'roas_desc':
            return { sort_by: 'roas', order: 'desc' };
        case 'roas_asc':
            return { sort_by: 'roas', order: 'asc' };
        case 'ctr_desc':
            return { sort_by: 'ctr', order: 'desc' };
        case 'ctr_asc':
            return { sort_by: 'ctr', order: 'asc' };
        case 'clicks_desc':
            return { sort_by: 'clicks', order: 'desc' };
        case 'clicks_asc':
            return { sort_by: 'clicks', order: 'asc' };
        case 'impressions_desc':
            return { sort_by: 'impressions', order: 'desc' };
        case 'impressions_asc':
            return { sort_by: 'impressions', order: 'asc' };
        case 'spend_desc':
            return { sort_by: 'spend', order: 'desc' };
        case 'spend_asc':
            return { sort_by: 'spend', order: 'asc' };
        case 'oldest':
            return { sort_by: 'meta_created_time', order: 'asc' };
        case 'running_longest':
            return { sort_by: 'started_running_on', order: 'asc' };
        case 'running_newest':
            return { sort_by: 'started_running_on', order: 'desc' };
        case 'library_oldest':
            return { sort_by: 'meta_created_time', order: 'asc' };
        case 'library_newest':
            return { sort_by: 'meta_created_time', order: 'desc' };
        case 'newest':
        default:
            return { sort_by: 'meta_created_time', order: 'desc' };
    }
}

/**
 * Fetch ad images for a client with optional pagination and filters.
 * @param {string} clientId - Client UUID
 * @param {Object} [options] - Optional: limit, offset, sortBy, mediaType
 * @param {number} [options.limit=60] - Page size
 * @param {number} [options.offset=0] - Pagination offset
 * @param {string} [options.sortBy=newest] - Frontend sort: newest, oldest, running_longest, running_newest
 * @param {string} [options.mediaType=all] - Filter: all, image, video
 * @returns {Promise<Object>} Object with items array and total count
 */
export async function fetchAdImages(clientId, options = {}) {
    const {
        limit = 60,
        offset = 0,
        sortBy = 'newest',
        mediaType = 'all',
        minClicks = null,
        minRevenue = null,
        minImpressions = null,
        minSpend = null,
    } = options;
    const { sort_by, order } = getSortParams(sortBy);
    const params = new URLSearchParams({
        limit: String(limit),
        offset: String(offset),
        sort_by,
        order,
        media_type: mediaType,
    });
    if (Number.isFinite(minClicks)) params.set('min_clicks', String(minClicks));
    if (Number.isFinite(minRevenue)) params.set('min_revenue', String(minRevenue));
    if (Number.isFinite(minImpressions)) params.set('min_impressions', String(minImpressions));
    if (Number.isFinite(minSpend)) params.set('min_spend', String(minSpend));
    const url = `${getApiBaseUrl()}/api/clients/${clientId}/ad-images?${params.toString()}`;
    const response = await fetch(url, { headers: getAuthHeaders() });
    await handleResponseError(response);
    return response.json();
}

/**
 * Delete an ad image
 * @param {string} imageId - Image UUID
 * @returns {Promise<void>}
 */
export async function deleteAdImage(imageId) {
    const response = await fetch(
        `${getApiBaseUrl()}/api/ad-images/${imageId}`,
        {
            method: 'DELETE',
            headers: getAuthHeaders()
        }
    );
    
    await handleResponseError(response);
    // 204 No Content - no body to parse
}
