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
let imagesColumnCount = null; // null means use default (4)
let selectedImageIds = new Set(); // Track selected images for bulk operations
let imagesSortBy = null; // null means use default ('newest')

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
 * Add image to cache (prepends to show newest first)
 * @param {Object} image - Image object
 */
export function addImageToCache(image) {
    imagesCache.unshift(image);
}

/**
 * Get column count preference
 * @returns {number} Column count (default 4)
 */
export function getImagesColumnCount() {
    if (imagesColumnCount !== null) {
        return imagesColumnCount;
    }
    // Try to restore from localStorage
    try {
        const stored = localStorage.getItem('imagesColumnCount');
        if (stored !== null) {
            const count = parseInt(stored, 10);
            if (count >= 2 && count <= 8) {
                imagesColumnCount = count;
                return count;
            }
        }
    } catch (e) {
        // localStorage not available or error
    }
    return 4; // Default
}

/**
 * Set column count preference
 * @param {number} count - Column count (2-8)
 */
export function setImagesColumnCount(count) {
    const validCount = Math.max(2, Math.min(8, Math.round(count)));
    imagesColumnCount = validCount;
    // Persist to localStorage
    try {
        localStorage.setItem('imagesColumnCount', String(validCount));
    } catch (e) {
        // localStorage not available or error
    }
}

/**
 * Get selected image IDs
 * @returns {Set} Set of selected image IDs
 */
export function getSelectedImageIds() {
    return selectedImageIds;
}

/**
 * Toggle image selection
 * @param {string} imageId - Image UUID
 * @returns {boolean} New selection state (true = selected)
 */
export function toggleImageSelection(imageId) {
    if (selectedImageIds.has(imageId)) {
        selectedImageIds.delete(imageId);
        return false;
    } else {
        selectedImageIds.add(imageId);
        return true;
    }
}

/**
 * Clear all selections
 */
export function clearImageSelections() {
    selectedImageIds.clear();
}

/**
 * Remove multiple images from cache
 * @param {string[]} imageIds - Array of image UUIDs
 */
export function removeImagesFromCache(imageIds) {
    const idsSet = new Set(imageIds);
    imagesCache = imagesCache.filter(img => !idsSet.has(img.id));
    // Also clear these from selection
    imageIds.forEach(id => selectedImageIds.delete(id));
}

/**
 * Get sort preference
 * @returns {string} Sort option ('newest', 'oldest', 'running_longest', 'running_newest')
 */
export function getImagesSortBy() {
    if (imagesSortBy !== null) {
        return imagesSortBy;
    }
    // Try to restore from localStorage
    try {
        const stored = localStorage.getItem('imagesSortBy');
        if (stored) {
            imagesSortBy = stored;
            return stored;
        }
    } catch (e) {
        // localStorage not available or error
    }
    return 'newest'; // Default
}

/**
 * Set sort preference
 * @param {string} sortBy - Sort option
 */
export function setImagesSortBy(sortBy) {
    imagesSortBy = sortBy;
    // Persist to localStorage
    try {
        localStorage.setItem('imagesSortBy', sortBy);
    } catch (e) {
        // localStorage not available or error
    }
}

/**
 * Clear all images state
 */
export function clearImagesState() {
    imagesCache = [];
    imagesLoading = false;
    imagesError = null;
    imagesCurrentClientId = null;
    selectedImageIds.clear();
    // Note: Don't clear imagesColumnCount or imagesSortBy - they're user preferences
}
