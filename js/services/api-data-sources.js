/**
 * Data Sources API service
 * Handles API calls related to projects and data sources
 */

import { getBaseUrl } from './api-config.js';

/**
 * Load projects for a specific client
 * @param {string} clientId - Client UUID
 * @param {Function} getAuthHeaders - Function to get auth headers
 * @returns {Promise<Array>} Array of project objects
 */
export async function loadProjects(clientId, getAuthHeaders) {
    const apiBaseUrl = getBaseUrl();
    
    try {
        const url = `${apiBaseUrl}/api/voc/projects?client_uuid=${clientId}`;
        const response = await fetch(url, {
            headers: getAuthHeaders ? getAuthHeaders() : {}
        });
        
        if (!response.ok) {
            throw new Error('Failed to load projects');
        }
        
        const projects = await response.json();
        return projects;
    } catch (error) {
        console.error('Error loading projects:', error);
        throw error;
    }
}

/**
 * Load data sources for a specific client and optional project
 * @param {string} clientId - Client UUID
 * @param {string|null} projectName - Optional project name
 * @param {Function} getAuthHeaders - Function to get auth headers
 * @returns {Promise<Array>} Array of data source objects
 */
export async function loadSources(clientId, projectName = null, getAuthHeaders) {
    const apiBaseUrl = getBaseUrl();
    
    try {
        let url = `${apiBaseUrl}/api/voc/sources?client_uuid=${clientId}`;
        if (projectName) {
            url += `&project_name=${encodeURIComponent(projectName)}`;
        }
        
        const response = await fetch(url, {
            headers: getAuthHeaders ? getAuthHeaders() : {}
        });
        
        if (!response.ok) {
            throw new Error('Failed to load sources');
        }
        
        const sources = await response.json();
        return sources;
    } catch (error) {
        console.error('Error loading sources:', error);
        throw error;
    }
}
