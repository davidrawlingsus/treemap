/**
 * API service for client settings operations.
 */

/**
 * Fetch client data including settings.
 * @param {string} clientId - The client UUID
 * @returns {Promise<Object>} Client data
 */
export async function fetchClientSettings(clientId) {
    const API_BASE_URL = window.APP_CONFIG?.API_BASE_URL || 'http://localhost:8000';
    const headers = window.Auth?.getAuthHeaders() || {};
    
    const response = await fetch(`${API_BASE_URL}/api/clients/${clientId}`, {
        headers
    });
    
    if (!response.ok) {
        throw new Error(`Failed to load client: ${response.status}`);
    }
    
    return response.json();
}

/**
 * Update client settings.
 * @param {string} clientId - The client UUID
 * @param {Object} settingsData - Settings to update
 * @param {string} [settingsData.client_url] - Brand website URL
 * @param {string} [settingsData.logo_url] - Logo URL
 * @param {string} [settingsData.header_color] - Header background color (hex)
 * @param {string} [settingsData.business_summary] - Business context summary
 * @param {string} [settingsData.tone_of_voice] - Brand tone of voice
 * @returns {Promise<Object>} Updated client data
 */
export async function updateClientSettings(clientId, settingsData) {
    const API_BASE_URL = window.APP_CONFIG?.API_BASE_URL || 'http://localhost:8000';
    const headers = {
        ...window.Auth?.getAuthHeaders(),
        'Content-Type': 'application/json'
    };
    
    const response = await fetch(`${API_BASE_URL}/api/clients/${clientId}/settings`, {
        method: 'PUT',
        headers,
        body: JSON.stringify(settingsData)
    });
    
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to save: ${response.status}`);
    }
    
    return response.json();
}

/**
 * Generate tone of voice guide using AI.
 * Crawls the brand website and uses LLM to generate a comprehensive tone guide.
 * @param {string} clientId - The client UUID
 * @returns {Promise<Object>} Generated tone of voice data
 * @returns {string} return.tone_of_voice - The generated tone guide
 * @returns {Array} return.pages_crawled - List of pages crawled
 * @returns {number} return.tokens_used - Tokens used by LLM
 * @returns {string} return.model - LLM model used
 */
export async function generateToneOfVoice(clientId) {
    const API_BASE_URL = window.APP_CONFIG?.API_BASE_URL || 'http://localhost:8000';
    const headers = {
        ...window.Auth?.getAuthHeaders(),
        'Content-Type': 'application/json'
    };
    
    const response = await fetch(`${API_BASE_URL}/api/clients/${clientId}/generate-tone-of-voice`, {
        method: 'POST',
        headers
    });
    
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to generate: ${response.status}`);
    }
    
    return response.json();
}
