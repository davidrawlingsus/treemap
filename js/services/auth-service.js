/**
 * Auth service wrapper
 * Provides a consistent interface for authentication functions from auth.js
 * Handles cases where Auth might not be loaded yet
 */

/**
 * Get authentication token
 * @returns {string|null} Auth token or null if not available
 */
export function getToken() {
    if (typeof window !== 'undefined' && window.Auth && typeof window.Auth.getAuthToken === 'function') {
        return window.Auth.getAuthToken();
    }
    // Fallback to direct global function
    if (typeof window !== 'undefined' && typeof window.getAuthToken === 'function') {
        return window.getAuthToken();
    }
    // Fallback to localStorage
    if (typeof window !== 'undefined' && window.localStorage) {
        return window.localStorage.getItem('visualizd_auth_token');
    }
    return null;
}

/**
 * Get authentication headers for API requests
 * @returns {Object} Headers object with Authorization and Content-Type
 */
export function getHeaders() {
    if (typeof window !== 'undefined' && window.Auth && typeof window.Auth.getAuthHeaders === 'function') {
        return window.Auth.getAuthHeaders();
    }
    // Fallback to direct global function
    if (typeof window !== 'undefined' && typeof window.getAuthHeaders === 'function') {
        return window.getAuthHeaders();
    }
    // Fallback: construct headers from token
    const token = getToken();
    return token
        ? {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
        : { 'Content-Type': 'application/json' };
}

/**
 * Get authentication headers safely (with fallback to localStorage)
 * This is a safer version that doesn't throw if Auth isn't loaded yet
 * @returns {Object} Headers object with Authorization and Content-Type
 */
export function getHeadersSafe() {
    let headers = {};
    
    // Try to use getAuthHeaders if available
    if (typeof window !== 'undefined' && typeof window.getAuthHeaders === 'function') {
        headers = window.getAuthHeaders();
        if (headers.Authorization || headers.authorization) {
            return headers;
        }
    }
    
    // Fallback to localStorage token
    const token = typeof window !== 'undefined' && window.localStorage
        ? window.localStorage.getItem('visualizd_auth_token')
        : null;
    
    if (token) {
        return {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        };
    }
    
    // Return headers without Authorization
    return { 'Content-Type': 'application/json' };
}

/**
 * Check if Auth module is available
 * @returns {boolean} True if Auth is loaded
 */
export function isAuthAvailable() {
    return typeof window !== 'undefined' && 
           window.Auth && 
           typeof window.Auth.getAuthToken === 'function';
}

/**
 * Get stored user info
 * @returns {Object|null} User info object or null
 */
export function getStoredUserInfo() {
    if (typeof window !== 'undefined' && window.Auth && typeof window.Auth.getStoredUserInfo === 'function') {
        return window.Auth.getStoredUserInfo();
    }
    return null;
}
