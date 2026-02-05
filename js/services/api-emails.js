/**
 * Saved Emails API Service
 * Handles all API calls for saved emails CRUD operations.
 * Follows service pattern - returns promises, no DOM manipulation.
 * Mirrors the structure of api-facebook-ads.js for consistency.
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
 * Fetch all saved emails for a client
 * @param {string} clientId - Client UUID
 * @param {string} [emailType] - Optional email type filter
 * @returns {Promise<Object>} Object with items array and total count
 */
export async function fetchSavedEmails(clientId, emailType = null) {
    let url = `${getApiBaseUrl()}/api/clients/${clientId}/saved-emails`;
    if (emailType) {
        url += `?email_type=${encodeURIComponent(emailType)}`;
    }
    
    const response = await fetch(url, { headers: getAuthHeaders() });
    await handleResponseError(response);
    return response.json();
}

/**
 * Create a new saved email
 * @param {string} clientId - Client UUID
 * @param {Object} emailData - Email data object
 * @returns {Promise<Object>} Created email object
 */
export async function createSavedEmail(clientId, emailData) {
    const response = await fetch(
        `${getApiBaseUrl()}/api/clients/${clientId}/saved-emails`,
        {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(emailData)
        }
    );
    
    await handleResponseError(response);
    return response.json();
}

/**
 * Get a single saved email by ID
 * @param {string} emailId - Email UUID
 * @returns {Promise<Object>} Email object
 */
export async function getSavedEmail(emailId) {
    const response = await fetch(
        `${getApiBaseUrl()}/api/saved-emails/${emailId}`,
        { headers: getAuthHeaders() }
    );
    
    await handleResponseError(response);
    return response.json();
}

/**
 * Update a saved email (e.g., change status, edit content, set image)
 * @param {string} emailId - Email UUID
 * @param {Object} updateData - Fields to update
 * @returns {Promise<Object>} Updated email object
 */
export async function updateSavedEmail(emailId, updateData) {
    const response = await fetch(
        `${getApiBaseUrl()}/api/saved-emails/${emailId}`,
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
 * Delete a saved email
 * @param {string} emailId - Email UUID
 * @returns {Promise<void>}
 */
export async function deleteSavedEmail(emailId) {
    const response = await fetch(
        `${getApiBaseUrl()}/api/saved-emails/${emailId}`,
        {
            method: 'DELETE',
            headers: getAuthHeaders()
        }
    );
    
    await handleResponseError(response);
    // 204 No Content - no body to parse
}

/**
 * Batch reorder emails (update sequence positions and send delays)
 * @param {string} clientId - Client UUID
 * @param {Array<Object>} updates - Array of { id, sequence_position, send_delay_hours }
 * @returns {Promise<Object>} Object with updated_count and emails array
 */
export async function reorderEmails(clientId, updates) {
    const response = await fetch(
        `${getApiBaseUrl()}/api/clients/${clientId}/saved-emails/reorder`,
        {
            method: 'PATCH',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ updates })
        }
    );
    
    await handleResponseError(response);
    return response.json();
}
