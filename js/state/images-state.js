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
let imagesTotal = 0; // Total count from API (for pagination "X of Y")
let imagesMediaTypeFilter = null; // null means use default ('all'); 'all' | 'image' | 'video'
let imagesViewMode = null; // null means default ('gallery'); 'gallery' | 'table'
let imagesMetricFilters = null; // { minClicks, minRevenue, minImpressions, minSpend }
let imagesTableColumns = null; // visible metric columns in table view
let imagesHideDuplicates = null; // table-only dedupe toggle

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
 * Select all images currently in cache (for "Select all" button).
 */
export function selectAllImages() {
    selectedImageIds = new Set(imagesCache.map((img) => img.id));
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
 * Get total count from last API response (for pagination)
 * @returns {number}
 */
export function getImagesTotal() {
    return imagesTotal;
}

/**
 * Set total count from API
 * @param {number} total
 */
export function setImagesTotal(total) {
    imagesTotal = total;
}

/**
 * Get media type filter
 * @returns {string} 'all' | 'image' | 'video'
 */
export function getImagesMediaTypeFilter() {
    if (imagesMediaTypeFilter !== null) {
        return imagesMediaTypeFilter;
    }
    try {
        const stored = localStorage.getItem('imagesMediaTypeFilter');
        if (stored === 'all' || stored === 'image' || stored === 'video') {
            imagesMediaTypeFilter = stored;
            return stored;
        }
    } catch (e) {
        // localStorage not available or error
    }
    return 'all';
}

/**
 * Set media type filter
 * @param {string} mediaType - 'all' | 'image' | 'video'
 */
export function setImagesMediaTypeFilter(mediaType) {
    imagesMediaTypeFilter = mediaType;
    try {
        localStorage.setItem('imagesMediaTypeFilter', mediaType);
    } catch (e) {
        // localStorage not available or error
    }
}

/**
 * Get images view mode
 * @returns {string} 'gallery' | 'table'
 */
export function getImagesViewMode() {
    if (imagesViewMode !== null) {
        return imagesViewMode;
    }
    try {
        const stored = localStorage.getItem('imagesViewMode');
        if (stored === 'gallery' || stored === 'table') {
            imagesViewMode = stored;
            return stored;
        }
    } catch (e) {
        // localStorage not available or error
    }
    return 'gallery';
}

/**
 * Set images view mode
 * @param {string} mode - 'gallery' | 'table'
 */
export function setImagesViewMode(mode) {
    const validMode = mode === 'table' ? 'table' : 'gallery';
    imagesViewMode = validMode;
    try {
        localStorage.setItem('imagesViewMode', validMode);
    } catch (e) {
        // localStorage not available or error
    }
}

/**
 * Get metric filters for images API
 * @returns {{ minClicks: number|null, minRevenue: number|null, minImpressions: number|null, minSpend: number|null }}
 */
export function getImagesMetricFilters() {
    if (imagesMetricFilters !== null) {
        return imagesMetricFilters;
    }
    const defaults = { minClicks: null, minRevenue: null, minImpressions: null, minSpend: null };
    try {
        const raw = localStorage.getItem('imagesMetricFilters');
        if (!raw) {
            imagesMetricFilters = defaults;
            return defaults;
        }
        const parsed = JSON.parse(raw);
        imagesMetricFilters = {
            minClicks: Number.isFinite(parsed?.minClicks) ? parsed.minClicks : null,
            minRevenue: Number.isFinite(parsed?.minRevenue) ? parsed.minRevenue : null,
            minImpressions: Number.isFinite(parsed?.minImpressions) ? parsed.minImpressions : null,
            minSpend: Number.isFinite(parsed?.minSpend) ? parsed.minSpend : null,
        };
        return imagesMetricFilters;
    } catch (e) {
        imagesMetricFilters = defaults;
        return defaults;
    }
}

/**
 * Set metric filters for images API
 * @param {{ minClicks?: number|null, minRevenue?: number|null, minImpressions?: number|null, minSpend?: number|null }} filters
 */
export function setImagesMetricFilters(filters = {}) {
    const current = getImagesMetricFilters();
    imagesMetricFilters = {
        minClicks: Number.isFinite(filters.minClicks) ? filters.minClicks : (filters.minClicks === null ? null : current.minClicks),
        minRevenue: Number.isFinite(filters.minRevenue) ? filters.minRevenue : (filters.minRevenue === null ? null : current.minRevenue),
        minImpressions: Number.isFinite(filters.minImpressions) ? filters.minImpressions : (filters.minImpressions === null ? null : current.minImpressions),
        minSpend: Number.isFinite(filters.minSpend) ? filters.minSpend : (filters.minSpend === null ? null : current.minSpend),
    };
    try {
        localStorage.setItem('imagesMetricFilters', JSON.stringify(imagesMetricFilters));
    } catch (e) {
        // localStorage not available or error
    }
}

const DEFAULT_TABLE_COLUMNS = ['revenue', 'roas', 'ctr', 'clicks', 'impressions', 'spend'];

/**
 * Get visible metric columns for media table view
 * @returns {string[]}
 */
export function getImagesTableColumns() {
    if (imagesTableColumns !== null) {
        return imagesTableColumns;
    }
    try {
        const raw = localStorage.getItem('imagesTableColumns');
        if (!raw) {
            imagesTableColumns = [...DEFAULT_TABLE_COLUMNS];
            return imagesTableColumns;
        }
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.every(v => typeof v === 'string')) {
            imagesTableColumns = parsed;
            return imagesTableColumns;
        }
    } catch (e) {
        // localStorage not available or error
    }
    imagesTableColumns = [...DEFAULT_TABLE_COLUMNS];
    return imagesTableColumns;
}

/**
 * Set visible metric columns for media table view
 * @param {string[]} columns
 */
export function setImagesTableColumns(columns) {
    imagesTableColumns = Array.isArray(columns) ? columns.filter(c => typeof c === 'string') : [...DEFAULT_TABLE_COLUMNS];
    try {
        localStorage.setItem('imagesTableColumns', JSON.stringify(imagesTableColumns));
    } catch (e) {
        // localStorage not available or error
    }
}

/**
 * Get dedupe toggle for images table view
 * @returns {boolean}
 */
export function getImagesHideDuplicates() {
    if (imagesHideDuplicates !== null) {
        return imagesHideDuplicates;
    }
    try {
        const stored = localStorage.getItem('imagesHideDuplicates');
        if (stored === 'true' || stored === 'false') {
            imagesHideDuplicates = stored === 'true';
            return imagesHideDuplicates;
        }
    } catch (e) {
        // localStorage not available or error
    }
    return false;
}

/**
 * Set dedupe toggle for images table view
 * @param {boolean} enabled
 */
export function setImagesHideDuplicates(enabled) {
    imagesHideDuplicates = !!enabled;
    try {
        localStorage.setItem('imagesHideDuplicates', imagesHideDuplicates ? 'true' : 'false');
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
    imagesTotal = 0;
    selectedImageIds.clear();
    // Note: Don't clear imagesColumnCount, imagesSortBy or imagesMediaTypeFilter - they're user preferences
}
