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
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/0ea04ade-be37-4438-ba64-4de28c7d11e9',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api-ad-images.js:58',message:'uploadAdImage called',data:{clientId,fileName:file?.name,fileSize:file?.size,uploadUrl,currentOrigin:window.location.origin,appConfigApiUrl:window.APP_CONFIG?.API_BASE_URL},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H-E'})}).catch(()=>{});
    // #endregion
    const uploadResponse = await fetch(uploadUrl, {
        method: 'POST',
        body: formData
    });
    
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/0ea04ade-be37-4438-ba64-4de28c7d11e9',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api-ad-images.js:70',message:'uploadResponse received',data:{status:uploadResponse.status,ok:uploadResponse.ok,statusText:uploadResponse.statusText},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H-A,H-E'})}).catch(()=>{});
    // #endregion
    if (!uploadResponse.ok) {
        const errorText = await uploadResponse.text().catch(() => '');
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/0ea04ade-be37-4438-ba64-4de28c7d11e9',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api-ad-images.js:76',message:'upload failed - error details',data:{errorText,status:uploadResponse.status},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H-A,H-B,H-E'})}).catch(()=>{});
        // #endregion
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
 * Fetch all ad images for a client
 * @param {string} clientId - Client UUID
 * @returns {Promise<Object>} Object with items array and total count
 */
export async function fetchAdImages(clientId) {
    const response = await fetch(
        `${getApiBaseUrl()}/api/clients/${clientId}/ad-images`,
        { headers: getAuthHeaders() }
    );
    
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
