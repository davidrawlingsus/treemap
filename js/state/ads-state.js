/**
 * Ads State Module
 * Manages state for the Ads tab including cache and UI state.
 * Follows state pattern - dedicated module for shared state.
 */

// State variables
let adsCache = [];
let adsLoading = false;
let adsError = null;
let adsCurrentClientId = null;

// Filter/Sort/Search state
let adsSearchTerm = '';
let adsFilters = [];  // [{field: 'testType', value: 'Social Proof'}, ...]
let adsSortBy = 'created_at';
let adsSortOrder = 'desc';

/**
 * Get cached ads
 * @returns {Array} Array of ad objects
 */
export function getAdsCache() {
    return adsCache;
}

/**
 * Set cached ads
 * @param {Array} ads - Array of ad objects
 */
export function setAdsCache(ads) {
    adsCache = ads;
}

/**
 * Get loading state
 * @returns {boolean} True if loading
 */
export function getAdsLoading() {
    return adsLoading;
}

/**
 * Set loading state
 * @param {boolean} loading - Loading state
 */
export function setAdsLoading(loading) {
    adsLoading = loading;
}

/**
 * Get error state
 * @returns {string|null} Error message or null
 */
export function getAdsError() {
    return adsError;
}

/**
 * Set error state
 * @param {string|null} error - Error message or null
 */
export function setAdsError(error) {
    adsError = error;
}

/**
 * Get current client ID for ads
 * @returns {string|null} Client UUID or null
 */
export function getAdsCurrentClientId() {
    return adsCurrentClientId;
}

/**
 * Set current client ID for ads
 * @param {string|null} clientId - Client UUID or null
 */
export function setAdsCurrentClientId(clientId) {
    adsCurrentClientId = clientId;
}

/**
 * Clear all ads state
 */
export function clearAdsState() {
    adsCache = [];
    adsLoading = false;
    adsError = null;
    adsSearchTerm = '';
    adsFilters = [];
    adsSortBy = 'created_at';
    adsSortOrder = 'desc';
}

// ============ Search State ============

/**
 * Get search term
 * @returns {string} Current search term
 */
export function getAdsSearchTerm() {
    return adsSearchTerm;
}

/**
 * Set search term
 * @param {string} term - Search term
 */
export function setAdsSearchTerm(term) {
    adsSearchTerm = term;
}

// ============ Filter State ============

/**
 * Get active filters
 * @returns {Array} Array of filter objects [{field, value}, ...]
 */
export function getAdsFilters() {
    return adsFilters;
}

/**
 * Set filters
 * @param {Array} filters - Array of filter objects
 */
export function setAdsFilters(filters) {
    adsFilters = filters;
}

/**
 * Add a filter
 * @param {string} field - Field name (testType, origin)
 * @param {string} value - Filter value
 */
export function addAdsFilter(field, value) {
    // Don't add duplicates
    const exists = adsFilters.some(f => f.field === field && f.value === value);
    if (!exists) {
        adsFilters = [...adsFilters, { field, value }];
    }
}

/**
 * Remove a filter
 * @param {string} field - Field name
 * @param {string} value - Filter value
 */
export function removeAdsFilter(field, value) {
    adsFilters = adsFilters.filter(f => !(f.field === field && f.value === value));
}

/**
 * Clear all filters
 */
export function clearAdsFilters() {
    adsFilters = [];
}

// ============ Sort State ============

/**
 * Get sort field
 * @returns {string} Current sort field
 */
export function getAdsSortBy() {
    return adsSortBy;
}

/**
 * Set sort field
 * @param {string} field - Sort field name
 */
export function setAdsSortBy(field) {
    adsSortBy = field;
}

/**
 * Get sort order
 * @returns {string} 'asc' or 'desc'
 */
export function getAdsSortOrder() {
    return adsSortOrder;
}

/**
 * Set sort order
 * @param {string} order - 'asc' or 'desc'
 */
export function setAdsSortOrder(order) {
    adsSortOrder = order;
}

/**
 * Toggle sort order
 */
export function toggleAdsSortOrder() {
    adsSortOrder = adsSortOrder === 'asc' ? 'desc' : 'asc';
}

/**
 * Remove an ad from cache by ID
 * @param {string} adId - Ad UUID to remove
 */
export function removeAdFromCache(adId) {
    adsCache = adsCache.filter(ad => ad.id !== adId);
}

/**
 * Add an ad to cache
 * @param {Object} ad - Ad object to add
 */
export function addAdToCache(ad) {
    adsCache = [ad, ...adsCache];
}

// Expose state functions globally for legacy compatibility
window.adsStateModule = {
    getAdsCache,
    setAdsCache,
    getAdsLoading,
    setAdsLoading,
    getAdsError,
    setAdsError,
    getAdsCurrentClientId,
    setAdsCurrentClientId,
    clearAdsState,
    removeAdFromCache,
    addAdToCache,
    // Search
    getAdsSearchTerm,
    setAdsSearchTerm,
    // Filters
    getAdsFilters,
    setAdsFilters,
    addAdsFilter,
    removeAdsFilter,
    clearAdsFilters,
    // Sort
    getAdsSortBy,
    setAdsSortBy,
    getAdsSortOrder,
    setAdsSortOrder,
    toggleAdsSortOrder
};
