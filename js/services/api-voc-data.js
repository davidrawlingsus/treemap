import { API_BASE_URL } from './api-config.js';

/**
 * Load VOC data from API
 * @param {string} clientUuid - Client UUID
 * @param {string} projectName - Project name (optional)
 * @param {string} dataSource - Data source identifier
 * @param {Function} getAuthHeaders - Function to get auth headers
 * @returns {Promise<Array>} Array of process_voc rows
 */
export async function loadVocData(clientUuid, projectName, dataSource, getAuthHeaders) {
    try {
        // Build query parameters
        const params = new URLSearchParams();
        if (clientUuid) params.append('client_uuid', clientUuid);
        if (projectName) params.append('project_name', projectName);
        if (dataSource) params.append('data_source', dataSource);
        
        const url = `${API_BASE_URL}/api/voc/data?${params.toString()}`;
        const response = await fetch(url, {
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: Failed to load data`);
        }
        
        const processVocRows = await response.json();
        
        // Validate response structure
        if (!processVocRows || !Array.isArray(processVocRows)) {
            throw new Error('Invalid response structure: expected array of process_voc rows');
        }
        
        return processVocRows;
    } catch (error) {
        console.error('Error loading VOC data:', error);
        throw error;
    }
}

/**
 * Load dimension names from API
 * @param {string} dataSourceId - Data source ID
 * @param {Function} getAuthHeaders - Function to get auth headers
 * @returns {Promise<Array>} Array of dimension names
 */
export async function loadDimensionNames(dataSourceId, getAuthHeaders) {
    if (!dataSourceId) return [];
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/data-sources/${dataSourceId}/dimension-names`, {
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            return await response.json();
        }
        return [];
    } catch (error) {
        console.error('Error loading dimension names:', error);
        return [];
    }
}

/**
 * Load questions (dimensions) from API
 * @param {string} clientUuid - Client UUID
 * @param {string} dataSource - Data source identifier
 * @param {string} projectName - Project name (optional)
 * @param {Function} getAuthHeaders - Function to get auth headers
 * @returns {Promise<Array>} Array of question objects
 */
export async function loadQuestions(clientUuid, dataSource, projectName, getAuthHeaders) {
    try {
        const params = new URLSearchParams();
        params.append('client_uuid', clientUuid);
        params.append('data_source', dataSource);
        if (projectName) {
            params.append('project_name', projectName);
        }
        
        const response = await fetch(`${API_BASE_URL}/api/voc/questions?${params.toString()}`, {
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            throw new Error('Failed to load questions');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error loading questions:', error);
        throw error;
    }
}
