/**
 * Clients API service
 * Handles API calls related to clients
 */

import { getBaseUrl } from './api-config.js';

/**
 * Load clients from the API
 * @param {Object} options - Options for loading clients
 * @param {Set} options.accessibleClientIds - Set of accessible client IDs for filtering
 * @param {Function} options.getAuthHeaders - Function to get auth headers
 * @returns {Promise<Array>} Array of client objects
 */
export async function loadClients({ accessibleClientIds = new Set(), getAuthHeaders }) {
    const apiBaseUrl = getBaseUrl();
    
    try {
        const response = await fetch(`${apiBaseUrl}/api/voc/clients`, {
            headers: getAuthHeaders ? getAuthHeaders() : {}
        });
        
        if (!response.ok) {
            throw new Error('Failed to load clients');
        }
        
        let clients = await response.json();
        
        // Filter by accessible client IDs if provided
        if (accessibleClientIds.size > 0) {
            clients = clients.filter(client => {
                // Check both client.id and client.client_uuid since accessibleClientIds uses client.id
                return (client.client_uuid && accessibleClientIds.has(client.client_uuid)) ||
                       (client.id && accessibleClientIds.has(client.id));
            });
        }
        
        // Sort clients alphabetically by client_name
        clients.sort((a, b) => {
            const nameA = (a.client_name || '').toLowerCase();
            const nameB = (b.client_name || '').toLowerCase();
            return nameA.localeCompare(nameB);
        });
        
        return clients;
    } catch (error) {
        console.error('Error loading clients:', error);
        throw error;
    }
}
