/**
 * Storage service - localStorage wrappers and state persistence
 * Handles all localStorage access patterns for the application
 */

// State persistence constants
export const STATE_STORAGE_KEY = 'treemap_app_state';

// Tag color storage constants
export const TAG_COLORS_STORAGE_KEY = 'vizualizd_tag_colors';

export const TAG_COLOR_MAP = {
    'default': { bg: 'rgba(99, 71, 169, 0.1)', color: '#6347a9' },
    'gray': { bg: 'rgba(156, 163, 175, 0.15)', color: '#6b7280' },
    'brown': { bg: 'rgba(146, 64, 14, 0.15)', color: '#92400e' },
    'orange': { bg: 'rgba(249, 115, 22, 0.15)', color: '#f97316' },
    'yellow': { bg: 'rgba(234, 179, 8, 0.15)', color: '#ca8a04' },
    'green': { bg: 'rgba(34, 197, 94, 0.15)', color: '#16a34a' },
    'blue': { bg: 'rgba(59, 130, 246, 0.15)', color: '#2563eb' },
    'purple': { bg: 'rgba(168, 85, 247, 0.15)', color: '#9333ea' },
    'pink': { bg: 'rgba(236, 72, 153, 0.15)', color: '#db2777' },
    'red': { bg: 'rgba(239, 68, 68, 0.15)', color: '#dc2626' }
};

/**
 * Save current application state to localStorage
 * @param {Object} state - State object containing clientId, projectName, dataSourceId, questionRefKey
 */
export function saveState(state) {
    try {
        localStorage.setItem(STATE_STORAGE_KEY, JSON.stringify(state));
    } catch (error) {
        console.error('Error saving state:', error);
    }
}

/**
 * Load state from localStorage
 * @returns {Object|null} State object or null if not found/invalid
 */
export function loadState() {
    try {
        const stateJson = localStorage.getItem(STATE_STORAGE_KEY);
        if (stateJson) {
            return JSON.parse(stateJson);
        }
    } catch (error) {
        console.error('Error loading state:', error);
    }
    return null;
}

/**
 * Get filter storage key scoped by client ID
 * @param {string} clientId - Client ID (defaults to 'global')
 * @returns {string} Storage key
 */
export function getFilterStorageKey(clientId = 'global') {
    return `insights_filters_${clientId}`;
}

/**
 * Load filters from localStorage (scoped by client ID)
 * @param {string} clientId - Client ID
 * @returns {Array} Array of filter objects
 */
export function loadFiltersFromStorage(clientId) {
    const storageKey = getFilterStorageKey(clientId);
    const saved = localStorage.getItem(storageKey);
    if (saved) {
        try {
            return JSON.parse(saved);
        } catch (e) {
            console.warn('Failed to parse saved filters:', e);
            return [];
        }
    }
    return [];
}

/**
 * Save filters to localStorage (scoped by client ID)
 * @param {string} clientId - Client ID
 * @param {Array} filters - Array of filter objects
 */
export function saveFiltersToStorage(clientId, filters) {
    const storageKey = getFilterStorageKey(clientId);
    localStorage.setItem(storageKey, JSON.stringify(filters));
}

/**
 * Get favorites storage key scoped by client and project
 * @param {string} clientId - Client ID
 * @param {string} projectName - Project name (defaults to 'all-projects')
 * @returns {string} Storage key
 */
export function getFavouritesStorageKey(clientId, projectName = 'all-projects') {
    return `verbatimFavourites_${clientId}_${projectName}`;
}

/**
 * Get favorites from localStorage
 * @param {string} clientId - Client ID
 * @param {string} projectName - Project name
 * @returns {Array} Array of favorite objects
 */
export function getFavourites(clientId, projectName) {
    try {
        const storageKey = getFavouritesStorageKey(clientId, projectName);
        const saved = localStorage.getItem(storageKey);
        return saved ? JSON.parse(saved) : [];
    } catch (e) {
        return [];
    }
}

/**
 * Save favorites to localStorage
 * @param {string} clientId - Client ID
 * @param {string} projectName - Project name
 * @param {Array} favourites - Array of favorite objects
 */
export function saveFavourites(clientId, projectName, favourites) {
    const storageKey = getFavouritesStorageKey(clientId, projectName);
    localStorage.setItem(storageKey, JSON.stringify(favourites));
}

/**
 * Get all tag colors from localStorage
 * @returns {Object} Map of color keys to color names
 */
export function getTagColors() {
    try {
        const stored = localStorage.getItem(TAG_COLORS_STORAGE_KEY);
        return stored ? JSON.parse(stored) : {};
    } catch (e) {
        console.error('Error loading tag colors:', e);
        return {};
    }
}

/**
 * Set tag color for a specific field and value
 * @param {string} fieldName - Field name (e.g., 'type', 'application')
 * @param {string} tagValue - Tag value
 * @param {string} colorName - Color name from TAG_COLOR_MAP
 */
export function setTagColor(fieldName, tagValue, colorName) {
    const colors = getTagColors();
    const key = `${fieldName}:${tagValue}`;
    if (colorName === 'default') {
        delete colors[key];
    } else {
        colors[key] = colorName;
    }
    try {
        localStorage.setItem(TAG_COLORS_STORAGE_KEY, JSON.stringify(colors));
    } catch (e) {
        console.error('Error saving tag color:', e);
    }
}

/**
 * Get tag color for a specific field and value
 * @param {string} fieldName - Field name
 * @param {string} tagValue - Tag value
 * @returns {Object} Color object with bg and color properties
 */
export function getTagColor(fieldName, tagValue) {
    const colors = getTagColors();
    const key = `${fieldName}:${tagValue}`;
    const colorName = colors[key] || 'default';
    return TAG_COLOR_MAP[colorName] || TAG_COLOR_MAP['default'];
}
