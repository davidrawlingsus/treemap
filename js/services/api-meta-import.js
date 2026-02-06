/**
 * Meta Ads Library Import API Service
 * Handles API calls for importing media from Meta Ads Library using background jobs.
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
 * Handle API errors consistently
 * @param {Response} response - Fetch response
 * @param {string} defaultMessage - Default error message
 */
async function handleApiError(response, defaultMessage = 'Request failed') {
    if (response.status === 401 || response.status === 403) {
        if (window.Auth?.showLogin) {
            window.Auth.showLogin();
        }
        throw new Error('Authentication required');
    }
    
    const errorText = await response.text().catch(() => '');
    let errorData;
    try {
        errorData = JSON.parse(errorText);
    } catch {
        errorData = { detail: errorText || defaultMessage };
    }
    
    let errorMessage = defaultMessage;
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

/**
 * Start a new Meta Ads Library import job
 * @param {string} clientId - Client UUID
 * @param {string} url - Meta Ads Library URL with view_all_page_id parameter
 * @param {number} maxScrolls - Maximum scroll operations (default 5)
 * @returns {Promise<Object>} ImportJob object
 */
export async function startMetaImportJob(clientId, url, maxScrolls = 5) {
    const apiUrl = `${getApiBaseUrl()}/api/meta-ads-library/import?client_id=${encodeURIComponent(clientId)}&max_scrolls=${maxScrolls}`;
    
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
    
    if (!response.ok) {
        await handleApiError(response, 'Failed to start import job');
    }
    
    return response.json();
}

/**
 * Get the status of an import job
 * @param {string} jobId - Import job UUID
 * @returns {Promise<Object>} ImportJobStatusResponse with job and recent_images
 */
export async function getImportJobStatus(jobId) {
    const apiUrl = `${getApiBaseUrl()}/api/meta-ads-library/jobs/${encodeURIComponent(jobId)}`;
    
    const authHeaders = getAuthHeaders();
    const headers = {};
    if (authHeaders.Authorization) {
        headers.Authorization = authHeaders.Authorization;
    }
    
    const response = await fetch(apiUrl, {
        method: 'GET',
        headers: headers
    });
    
    if (!response.ok) {
        await handleApiError(response, 'Failed to get job status');
    }
    
    return response.json();
}

/**
 * Get images imported by a specific job
 * @param {string} jobId - Import job UUID
 * @param {string} since - ISO timestamp to get images imported after
 * @returns {Promise<Object>} AdImageListResponse
 */
export async function getImportJobImages(jobId, since = null) {
    let apiUrl = `${getApiBaseUrl()}/api/meta-ads-library/jobs/${encodeURIComponent(jobId)}/images`;
    
    if (since) {
        apiUrl += `?since=${encodeURIComponent(since)}`;
    }
    
    const authHeaders = getAuthHeaders();
    const headers = {};
    if (authHeaders.Authorization) {
        headers.Authorization = authHeaders.Authorization;
    }
    
    const response = await fetch(apiUrl, {
        method: 'GET',
        headers: headers
    });
    
    if (!response.ok) {
        await handleApiError(response, 'Failed to get job images');
    }
    
    return response.json();
}

/**
 * List import jobs for a client
 * @param {string} clientId - Client UUID
 * @param {string} status - Optional status filter
 * @param {number} limit - Maximum number of jobs to return
 * @returns {Promise<Object>} ImportJobListResponse
 */
export async function listImportJobs(clientId, status = null, limit = 10) {
    let apiUrl = `${getApiBaseUrl()}/api/meta-ads-library/jobs?client_id=${encodeURIComponent(clientId)}&limit=${limit}`;
    
    if (status) {
        apiUrl += `&status=${encodeURIComponent(status)}`;
    }
    
    const authHeaders = getAuthHeaders();
    const headers = {};
    if (authHeaders.Authorization) {
        headers.Authorization = authHeaders.Authorization;
    }
    
    const response = await fetch(apiUrl, {
        method: 'GET',
        headers: headers
    });
    
    if (!response.ok) {
        await handleApiError(response, 'Failed to list import jobs');
    }
    
    return response.json();
}

/**
 * [DEPRECATED] Legacy synchronous import - use startMetaImportJob instead
 * Import media from Meta Ads Library URL (blocks until complete)
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
    
    if (!response.ok) {
        await handleApiError(response, 'Import failed');
    }
    
    return response.json();
}
