/**
 * Images State Module
 * Manages state for the Images tab including cache and UI state.
 * Follows state pattern - dedicated module for shared state.
 */

// State variables
let imagesCache = [];
let imagesLoading = false;
let imagesError = null;
let imagesCurrentClientId = null;

/**
 * Get cached images
 * @returns {Array} Array of image objects
 */
export function getImagesCache() {
    return imagesCache;
}

/**
 * Set cached images
 * @param {Array} images - Array of image objects
 */
export function setImagesCache(images) {
    imagesCache = images;
}

/**
 * Get loading state
 * @returns {boolean} Loading state
 */
export function getImagesLoading() {
    return imagesLoading;
}

/**
 * Set loading state
 * @param {boolean} loading - Loading state
 */
export function setImagesLoading(loading) {
    imagesLoading = loading;
}

/**
 * Get error state
 * @returns {string|null} Error message
 */
export function getImagesError() {
    return imagesError;
}

/**
 * Set error state
 * @param {string|null} error - Error message
 */
export function setImagesError(error) {
    imagesError = error;
}

/**
 * Get current client ID
 * @returns {string|null} Client ID
 */
export function getImagesCurrentClientId() {
    return imagesCurrentClientId;
}

/**
 * Set current client ID
 * @param {string} clientId - Client ID
 */
export function setImagesCurrentClientId(clientId) {
    imagesCurrentClientId = clientId;
}

/**
 * Remove image from cache
 * @param {string} imageId - Image UUID
 */
export function removeImageFromCache(imageId) {
    imagesCache = imagesCache.filter(img => img.id !== imageId);
}

/**
 * Add image to cache
 * @param {Object} image - Image object
 */
export function addImageToCache(image) {
    imagesCache.push(image);
}

/**
 * Clear all images state
 */
export function clearImagesState() {
    imagesCache = [];
    imagesLoading = false;
    imagesError = null;
    imagesCurrentClientId = null;
}
