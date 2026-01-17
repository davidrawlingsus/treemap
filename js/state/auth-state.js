/**
 * Authentication State Management
 * Manages authentication-related state (accessible clients, authenticated user)
 */

let accessibleClients = [];
let accessibleClientIds = new Set();
let authenticatedUser = null;

/**
 * Get accessible clients
 * @returns {Array}
 */
export function getAccessibleClients() {
    return accessibleClients;
}

/**
 * Set accessible clients
 * @param {Array} clients
 */
export function setAccessibleClients(clients) {
    accessibleClients = clients || [];
}

/**
 * Get accessible client IDs
 * @returns {Set}
 */
export function getAccessibleClientIds() {
    return accessibleClientIds;
}

/**
 * Set accessible client IDs
 * @param {Set|Array} ids
 */
export function setAccessibleClientIds(ids) {
    if (ids instanceof Set) {
        accessibleClientIds = ids;
    } else {
        accessibleClientIds = new Set(ids || []);
    }
}

/**
 * Add accessible client ID
 * @param {string|number} id
 */
export function addAccessibleClientId(id) {
    if (id != null) {
        accessibleClientIds.add(id);
    }
}

/**
 * Remove accessible client ID
 * @param {string|number} id
 */
export function removeAccessibleClientId(id) {
    accessibleClientIds.delete(id);
}

/**
 * Check if client ID is accessible
 * @param {string|number} id
 * @returns {boolean}
 */
export function hasAccessibleClientId(id) {
    return accessibleClientIds.has(id);
}

/**
 * Clear all accessible client IDs
 */
export function clearAccessibleClientIds() {
    accessibleClientIds.clear();
}

/**
 * Get authenticated user
 * @returns {Object|null}
 */
export function getAuthenticatedUser() {
    return authenticatedUser;
}

/**
 * Set authenticated user
 * @param {Object|null} user
 */
export function setAuthenticatedUser(user) {
    authenticatedUser = user;
}

/**
 * Get all authentication state
 * @returns {Object}
 */
export function getAuthState() {
    return {
        accessibleClients: [...accessibleClients],
        accessibleClientIds: Array.from(accessibleClientIds),
        authenticatedUser
    };
}

/**
 * Set all authentication state
 * @param {Object} state
 */
export function setAuthState(state) {
    if (state.accessibleClients !== undefined) accessibleClients = state.accessibleClients || [];
    if (state.accessibleClientIds !== undefined) {
        if (state.accessibleClientIds instanceof Set) {
            accessibleClientIds = state.accessibleClientIds;
        } else {
            accessibleClientIds = new Set(state.accessibleClientIds || []);
        }
    }
    if (state.authenticatedUser !== undefined) authenticatedUser = state.authenticatedUser;
}

/**
 * Reset all authentication state
 */
export function resetAuthState() {
    accessibleClients = [];
    accessibleClientIds.clear();
    authenticatedUser = null;
}
