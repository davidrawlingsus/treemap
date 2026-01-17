/**
 * Filter State Management
 * Manages filter rules, dimension filters, and metadata field filters
 */

// Filter rules: array of {type: 'category'|'topic'|'location'|'metadata', mode: 'include'|'exclude', values: Set, metadataField?: string}
let filterRules = [];
// Store filters per dimension: key is dimension ref key (or 'all' for null), value is array of filter rules
let dimensionFilters = {}; // Map of dimensionRef -> filterRules array
let availableMetadataFields = {}; // Map of fieldName -> array of values
let currentMetadataField = null; // Currently selected metadata field

/**
 * Get filter rules
 * @returns {Array}
 */
export function getFilterRules() {
    return filterRules;
}

/**
 * Set filter rules
 * @param {Array} rules
 */
export function setFilterRules(rules) {
    filterRules = rules || [];
}

/**
 * Get dimension filters
 * @returns {Object}
 */
export function getDimensionFilters() {
    return dimensionFilters;
}

/**
 * Set dimension filters
 * @param {Object} filters
 */
export function setDimensionFilters(filters) {
    dimensionFilters = filters || {};
}

/**
 * Get dimension filter for a specific dimension
 * @param {string} dimensionRef
 * @returns {Array}
 */
export function getDimensionFilter(dimensionRef) {
    return dimensionFilters[dimensionRef] || [];
}

/**
 * Set dimension filter for a specific dimension
 * @param {string} dimensionRef
 * @param {Array} rules
 */
export function setDimensionFilter(dimensionRef, rules) {
    if (dimensionRef) {
        dimensionFilters[dimensionRef] = rules || [];
    }
}

/**
 * Clear dimension filter for a specific dimension
 * @param {string} dimensionRef
 */
export function clearDimensionFilter(dimensionRef) {
    if (dimensionRef && dimensionFilters[dimensionRef]) {
        delete dimensionFilters[dimensionRef];
    }
}

/**
 * Clear all dimension filters
 */
export function clearAllDimensionFilters() {
    dimensionFilters = {};
}

/**
 * Get available metadata fields
 * @returns {Object}
 */
export function getAvailableMetadataFields() {
    return availableMetadataFields;
}

/**
 * Set available metadata fields
 * @param {Object} fields
 */
export function setAvailableMetadataFields(fields) {
    availableMetadataFields = fields || {};
}

/**
 * Get current metadata field
 * @returns {string|null}
 */
export function getCurrentMetadataField() {
    return currentMetadataField;
}

/**
 * Set current metadata field
 * @param {string|null} field
 */
export function setCurrentMetadataField(field) {
    currentMetadataField = field;
}

/**
 * Get all filter state
 * @returns {Object}
 */
export function getFilterState() {
    return {
        filterRules,
        dimensionFilters,
        availableMetadataFields,
        currentMetadataField
    };
}

/**
 * Set all filter state
 * @param {Object} state
 */
export function setFilterState(state) {
    if (state.filterRules !== undefined) filterRules = state.filterRules || [];
    if (state.dimensionFilters !== undefined) dimensionFilters = state.dimensionFilters || {};
    if (state.availableMetadataFields !== undefined) availableMetadataFields = state.availableMetadataFields || {};
    if (state.currentMetadataField !== undefined) currentMetadataField = state.currentMetadataField;
}

/**
 * Reset all filter state
 */
export function resetFilterState() {
    filterRules = [];
    dimensionFilters = {};
    availableMetadataFields = {};
    currentMetadataField = null;
}
