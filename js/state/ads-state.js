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
    addAdToCache
};
