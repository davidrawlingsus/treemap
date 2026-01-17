/**
 * API Configuration
 * Centralized API base URL management
 */

/**
 * Get the API base URL
 * Checks window.APP_CONFIG first, then falls back to default
 * @returns {string} API base URL
 */
export function getBaseUrl() {
    if (typeof window !== 'undefined' && window.APP_CONFIG && window.APP_CONFIG.API_BASE_URL) {
        return window.APP_CONFIG.API_BASE_URL;
    }
    return 'http://localhost:8000';
}

/**
 * Get API_BASE_URL constant (for backward compatibility)
 * @returns {string} API base URL
 */
export const API_BASE_URL = getBaseUrl();
