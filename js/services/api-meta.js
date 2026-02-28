/**
 * Meta Ads API Service
 * Handles Meta/Facebook OAuth and Marketing API calls.
 */

const API_BASE_URL = window.APP_CONFIG?.API_BASE_URL || 'http://localhost:8000';

/**
 * Get auth headers for API calls
 * @returns {Object} Headers object with Authorization
 */
function getAuthHeaders() {
    return window.Auth?.getAuthHeaders() || {};
}

/**
 * Handle API response errors
 * @param {Response} response - Fetch response
 * @param {string} operation - Description of the operation
 */
async function handleResponse(response, operation) {
    if (response.status === 401 || response.status === 403) {
        window.Auth?.showLogin?.();
    }
    if (!response.ok) {
        const errorText = await response.text();
        let errorMessage;
        try {
            const errorJson = JSON.parse(errorText);
            errorMessage = errorJson.detail || errorJson.error || errorText;
        } catch {
            errorMessage = errorText;
        }
        throw new Error(`${operation} failed: ${errorMessage}`);
    }
    return response.json();
}

// ==================== OAuth Methods ====================

/**
 * Check if a client has a valid Meta token
 * @param {string} clientId - Client UUID
 * @returns {Promise<Object>} Token status response
 */
export async function checkMetaTokenStatus(clientId) {
    const response = await fetch(
        `${API_BASE_URL}/api/meta/token-status?client_id=${clientId}`,
        { headers: getAuthHeaders() }
    );
    return handleResponse(response, 'Check Meta token status');
}

/**
 * Get Meta OAuth initialization URL
 * @param {string} clientId - Client UUID
 * @returns {Promise<Object>} Response with oauth_url and state
 */
export async function getMetaOAuthUrl(clientId) {
    const response = await fetch(
        `${API_BASE_URL}/api/meta/oauth/init?client_id=${clientId}`,
        { headers: getAuthHeaders() }
    );
    return handleResponse(response, 'Get Meta OAuth URL');
}

/**
 * Open Meta OAuth flow in a popup window
 * @param {string} clientId - Client UUID
 * @returns {Promise<Object>} Resolves with success data or rejects with error
 */
export function openMetaOAuthPopup(clientId) {
    return new Promise(async (resolve, reject) => {
        try {
            // Get OAuth URL from backend
            const { oauth_url } = await getMetaOAuthUrl(clientId);
            
            // Calculate popup dimensions
            const width = 600;
            const height = 700;
            const left = window.screenX + (window.outerWidth - width) / 2;
            const top = window.screenY + (window.outerHeight - height) / 2;
            
            // Open popup
            const popup = window.open(
                oauth_url,
                'meta_oauth',
                `width=${width},height=${height},left=${left},top=${top},scrollbars=yes`
            );
            
            if (!popup) {
                reject(new Error('Popup blocked. Please allow popups for this site.'));
                return;
            }
            
            // Listen for messages from popup
            const messageHandler = (event) => {
                if (event.data?.type === 'meta_oauth_success') {
                    window.removeEventListener('message', messageHandler);
                    resolve({
                        success: true,
                        meta_user_name: event.data.meta_user_name,
                    });
                } else if (event.data?.type === 'meta_oauth_error') {
                    window.removeEventListener('message', messageHandler);
                    reject(new Error(event.data.error || 'OAuth failed'));
                }
            };
            
            window.addEventListener('message', messageHandler);
            
            // Check if popup is closed without completing OAuth
            const checkClosed = setInterval(() => {
                if (popup.closed) {
                    clearInterval(checkClosed);
                    window.removeEventListener('message', messageHandler);
                    // Don't reject - user may have completed OAuth before closing
                }
            }, 500);
            
        } catch (error) {
            reject(error);
        }
    });
}

/**
 * Disconnect Meta account from a client
 * @param {string} clientId - Client UUID
 * @returns {Promise<Object>} Success response
 */
export async function disconnectMeta(clientId) {
    const response = await fetch(
        `${API_BASE_URL}/api/meta/disconnect?client_id=${clientId}`,
        {
            method: 'DELETE',
            headers: getAuthHeaders(),
        }
    );
    return handleResponse(response, 'Disconnect Meta');
}

// ==================== Ad Account Methods ====================

/**
 * Fetch Meta ad accounts for a client
 * @param {string} clientId - Client UUID
 * @returns {Promise<Object>} Response with items array of ad accounts
 */
export async function fetchMetaAdAccounts(clientId) {
    const response = await fetch(
        `${API_BASE_URL}/api/meta/ad-accounts?client_id=${clientId}`,
        { headers: getAuthHeaders() }
    );
    return handleResponse(response, 'Fetch Meta ad accounts');
}

/**
 * Set the default ad account for a client
 * @param {string} clientId - Client UUID
 * @param {string} adAccountId - Meta ad account ID
 * @param {string} [adAccountName] - Ad account name for display
 * @returns {Promise<Object>} Success response
 */
export async function setDefaultMetaAdAccount(clientId, adAccountId, adAccountName = null) {
    const response = await fetch(
        `${API_BASE_URL}/api/meta/set-default-ad-account`,
        {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                client_id: clientId,
                ad_account_id: adAccountId,
                ad_account_name: adAccountName,
            }),
        }
    );
    return handleResponse(response, 'Set default ad account');
}

// ==================== Campaign Methods ====================

/**
 * Fetch campaigns for an ad account
 * @param {string} clientId - Client UUID
 * @param {string} adAccountId - Meta ad account ID
 * @returns {Promise<Object>} Response with items array of campaigns
 */
export async function fetchMetaCampaigns(clientId, adAccountId) {
    const response = await fetch(
        `${API_BASE_URL}/api/meta/campaigns?client_id=${clientId}&ad_account_id=${adAccountId}`,
        { headers: getAuthHeaders() }
    );
    return handleResponse(response, 'Fetch Meta campaigns');
}

/**
 * Create a new campaign
 * @param {string} clientId - Client UUID
 * @param {Object} campaignData - Campaign data
 * @returns {Promise<Object>} Created campaign with id
 */
export async function createMetaCampaign(clientId, campaignData) {
    const response = await fetch(
        `${API_BASE_URL}/api/meta/campaigns?client_id=${clientId}`,
        {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(campaignData),
        }
    );
    return handleResponse(response, 'Create Meta campaign');
}

// ==================== AdSet Methods ====================

/**
 * Fetch adsets for a campaign
 * @param {string} clientId - Client UUID
 * @param {string} campaignId - Meta campaign ID
 * @returns {Promise<Object>} Response with items array of adsets
 */
export async function fetchMetaAdsets(clientId, campaignId) {
    const response = await fetch(
        `${API_BASE_URL}/api/meta/adsets?client_id=${clientId}&campaign_id=${campaignId}`,
        { headers: getAuthHeaders() }
    );
    return handleResponse(response, 'Fetch Meta adsets');
}

/**
 * Create a new adset
 * @param {string} clientId - Client UUID
 * @param {Object} adsetData - Adset data
 * @returns {Promise<Object>} Created adset with id
 */
export async function createMetaAdset(clientId, adsetData) {
    const response = await fetch(
        `${API_BASE_URL}/api/meta/adsets?client_id=${clientId}`,
        {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(adsetData),
        }
    );
    return handleResponse(response, 'Create Meta adset');
}

// ==================== Page Methods ====================

/**
 * Fetch Facebook pages the user manages
 * @param {string} clientId - Client UUID
 * @returns {Promise<Object>} Response with items array of pages
 */
export async function fetchMetaPages(clientId) {
    const response = await fetch(
        `${API_BASE_URL}/api/meta/pages?client_id=${clientId}`,
        { headers: getAuthHeaders() }
    );
    return handleResponse(response, 'Fetch Meta pages');
}

// ==================== Pixel Methods ====================

/**
 * Fetch Facebook pixels for the client's ad account
 * @param {string} clientId - Client UUID
 * @returns {Promise<Object>} Response with items array of pixels
 */
export async function fetchMetaPixels(clientId) {
    const response = await fetch(
        `${API_BASE_URL}/api/meta/pixels?client_id=${clientId}`,
        { headers: getAuthHeaders() }
    );
    return handleResponse(response, 'Fetch Meta pixels');
}

// ==================== Media Library (FB Connector) Methods ====================

/**
 * Fetch total counts for media library (for progress). Call before Load All.
 * @param {string} clientId - Client UUID
 * @param {string} [mediaType='all'] - 'all', 'image', or 'video'
 * @returns {Promise<{ image_count?: number|null, video_count?: number|null }>}
 */
export async function fetchMetaMediaLibraryCounts(clientId, mediaType = 'all') {
    const params = new URLSearchParams({ client_id: clientId, media_type: mediaType });
    const response = await fetch(
        `${API_BASE_URL}/api/meta/media-library/counts?${params}`,
        { headers: getAuthHeaders() }
    );
    return handleResponse(response, 'Fetch Meta media library counts');
}

/**
 * Fetch media library (images and/or videos) from the client's Meta ad account
 * @param {string} clientId - Client UUID
 * @param {Object} [opts] - Optional: mediaType ('all'|'image'|'video'), limit, after (single-type cursor), image_after, video_after (for mediaType 'all')
 * @returns {Promise<Object>} Response with items array and paging
 */
export async function fetchMetaMediaLibrary(clientId, opts = {}) {
    const { mediaType = 'all', limit = 50, after, image_after, video_after } = opts;
    const params = new URLSearchParams({ client_id: clientId, media_type: mediaType, limit });
    if (after) params.set('after', after);
    if (image_after) params.set('image_after', image_after);
    if (video_after) params.set('video_after', video_after);
    const response = await fetch(
        `${API_BASE_URL}/api/meta/media-library?${params}`,
        { headers: getAuthHeaders() }
    );
    return handleResponse(response, 'Fetch Meta media library');
}

/**
 * Import selected media from Meta ad account into local library
 * @param {string} clientId - Client UUID
 * @param {Array<{type: string, hash?: string, video_id?: string, original_url: string, filename?: string, thumbnail_url?: string}>} items - Items to import
 * @returns {Promise<Object>} Response with items array of created AdImage records
 */
export async function importMetaMedia(clientId, items) {
    const response = await fetch(
        `${API_BASE_URL}/api/meta/import-media`,
        {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ client_id: clientId, items }),
        }
    );
    return handleResponse(response, 'Import Meta media');
}

/**
 * Import all media from Meta ad account (server-side list + import; no need to load thumbnails).
 * @param {string} clientId - Client UUID
 * @param {string} [mediaType='all'] - 'all', 'image', or 'video'
 * @returns {Promise<Object>} Response with items array and failed_count
 */
export async function importAllMetaMedia(clientId, mediaType = 'all') {
    const response = await fetch(
        `${API_BASE_URL}/api/meta/import-all`,
        {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ client_id: clientId, media_type: mediaType }),
        }
    );
    return handleResponse(response, 'Import all Meta media');
}

/**
 * Import all media with streaming progress. Calls onProgress({ imported, failed, pages_done }) as data arrives.
 * @param {string} clientId - Client UUID
 * @param {string} [mediaType='all'] - 'all', 'image', or 'video'
 * @param {function(Object): void} [onProgress] - Called with { imported, failed, pages_done } on each progress event
 * @returns {Promise<Object>} Resolves with { items, failed_count } on success
 */
export async function importAllMetaMediaStream(clientId, mediaType = 'all', onProgress = null) {
    const response = await fetch(
        `${API_BASE_URL}/api/meta/import-all-stream`,
        {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ client_id: clientId, media_type: mediaType }),
        }
    );
    if (!response.ok) {
        const text = await response.text();
        let msg;
        try {
            const j = JSON.parse(text);
            msg = j.detail || j.error || text;
        } catch {
            msg = text;
        }
        throw new Error(msg || `Import all failed: ${response.status}`);
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';
        for (const chunk of lines) {
            const dataLine = chunk.split('\n').find((l) => l.startsWith('data: '));
            if (!dataLine) continue;
            try {
                const data = JSON.parse(dataLine.slice(6));
                if (data.type === 'progress' && typeof onProgress === 'function') {
                    onProgress({ imported: data.imported ?? 0, failed: data.failed ?? 0, pages_done: data.pages_done ?? 0 });
                } else if (data.type === 'result') {
                    return { items: data.items || [], failed_count: data.failed_count ?? 0 };
                } else if (data.type === 'error') {
                    throw new Error(data.message || 'Import all failed');
                }
            } catch (e) {
                if (e instanceof SyntaxError) continue;
                throw e;
            }
        }
    }
    if (buffer.trim()) {
        const dataLine = buffer.split('\n').find((l) => l.startsWith('data: '));
        if (dataLine) {
            try {
                const data = JSON.parse(dataLine.slice(6));
                if (data.type === 'result') return { items: data.items || [], failed_count: data.failed_count ?? 0 };
                if (data.type === 'error') throw new Error(data.message || 'Import all failed');
            } catch (e) {
                if (!(e instanceof SyntaxError)) throw e;
            }
        }
    }
    throw new Error('Import all ended without result');
}

// ==================== Publishing Methods ====================

/**
 * Publish an ad to Meta
 * @param {string} clientId - Client UUID
 * @param {string} adId - Local ad UUID
 * @param {string} adsetId - Meta adset ID
 * @param {string} adAccountId - Meta ad account ID
 * @param {string} pageId - Facebook page ID
 * @param {string} [name] - Optional ad name
 * @param {string} [status='PAUSED'] - Initial ad status
 * @returns {Promise<Object>} Response with meta_ad_id and meta_creative_id
 */
export async function publishAdToMeta(clientId, adId, adsetId, adAccountId, pageId, name = null, status = 'PAUSED') {
    const response = await fetch(
        `${API_BASE_URL}/api/meta/publish-ad?client_id=${clientId}&page_id=${pageId}`,
        {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                ad_id: adId,
                adset_id: adsetId,
                ad_account_id: adAccountId,
                name: name,
                status: status,
            }),
        }
    );
    return handleResponse(response, 'Publish ad to Meta');
}
