import { API_BASE_URL } from './api-config.js';

/**
 * Load insights from API
 * @param {string} clientId - Client ID
 * @param {Object} params - Query parameters (page, page_size, sort_by, sort_order, filters)
 * @param {Function} getAuthHeaders - Function to get auth headers
 * @returns {Promise<Object>} Response object with items array
 */
export async function loadInsights(clientId, params, getAuthHeaders) {
    try {
        const queryParams = new URLSearchParams();
        
        // Add pagination params
        if (params.page) queryParams.append('page', params.page);
        if (params.page_size) queryParams.append('page_size', params.page_size);
        if (params.sort_by) queryParams.append('sort_by', params.sort_by);
        if (params.sort_order) queryParams.append('sort_order', params.sort_order);
        
        // Add filter params
        if (params.filters) {
            Object.entries(params.filters).forEach(([key, value]) => {
                if (value) {
                    queryParams.append(key, value);
                }
            });
        }
        
        const url = `${API_BASE_URL}/api/clients/${clientId}/insights?${queryParams.toString()}`;
        const response = await fetch(url, {
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('Authentication required. Please log in.');
            }
            throw new Error(`Failed to load insights: ${response.status} ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error loading insights:', error);
        throw error;
    }
}

/**
 * Create a new insight
 * @param {string} clientId - Client ID
 * @param {Object} insightData - Insight data to create
 * @param {Function} getAuthHeaders - Function to get auth headers
 * @returns {Promise<Object>} Created insight object
 */
export async function createInsight(clientId, insightData, getAuthHeaders) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/clients/${clientId}/insights`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(insightData)
        });
        
        if (!response.ok) {
            let errorData;
            try {
                errorData = await response.json();
            } catch (e) {
                errorData = { detail: response.statusText };
            }
            throw new Error(errorData.detail || `HTTP ${response.status}: Failed to create insight`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error creating insight:', error);
        throw error;
    }
}

/**
 * Update an existing insight
 * @param {string} clientId - Client ID
 * @param {string} insightId - Insight ID
 * @param {Object} insightData - Insight data to update
 * @param {Function} getAuthHeaders - Function to get auth headers
 * @returns {Promise<Object>} Updated insight object
 */
export async function updateInsight(clientId, insightId, insightData, getAuthHeaders) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/clients/${clientId}/insights/${insightId}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify(insightData)
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(errorData.detail || `Failed to update insight`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error updating insight:', error);
        throw error;
    }
}

/**
 * Delete an insight
 * @param {string} clientId - Client ID
 * @param {string} insightId - Insight ID
 * @param {Function} getAuthHeaders - Function to get auth headers
 * @returns {Promise<void>}
 */
export async function deleteInsight(clientId, insightId, getAuthHeaders) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/clients/${clientId}/insights/${insightId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            throw new Error('Failed to delete insight');
        }
    } catch (error) {
        console.error('Error deleting insight:', error);
        throw error;
    }
}
