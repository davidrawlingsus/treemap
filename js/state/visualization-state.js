/**
 * Visualization Data State Management
 * Manages data state for treemap visualization (raw data, filtered data, hierarchy)
 */

let rawData = [];
let fullRawData = []; // Store unfiltered data
let dimensionFilteredData = []; // Store dimension-filtered data (before category filtering)
let hierarchyData = null;

/**
 * Get raw data
 * @returns {Array}
 */
export function getRawData() {
    return rawData;
}

/**
 * Set raw data
 * @param {Array} data
 */
export function setRawData(data) {
    rawData = data || [];
}

/**
 * Get full raw data (unfiltered)
 * @returns {Array}
 */
export function getFullRawData() {
    return fullRawData;
}

/**
 * Set full raw data (unfiltered)
 * @param {Array} data
 */
export function setFullRawData(data) {
    fullRawData = data || [];
}

/**
 * Get dimension filtered data
 * @returns {Array}
 */
export function getDimensionFilteredData() {
    return dimensionFilteredData;
}

/**
 * Set dimension filtered data
 * @param {Array} data
 */
export function setDimensionFilteredData(data) {
    dimensionFilteredData = data || [];
}

/**
 * Get hierarchy data
 * @returns {Object|null}
 */
export function getHierarchyData() {
    return hierarchyData;
}

/**
 * Set hierarchy data
 * @param {Object|null} data
 */
export function setHierarchyData(data) {
    hierarchyData = data;
}

/**
 * Get all visualization state
 * @returns {Object}
 */
export function getVisualizationState() {
    return {
        rawData,
        fullRawData,
        dimensionFilteredData,
        hierarchyData
    };
}

/**
 * Set all visualization state
 * @param {Object} state
 */
export function setVisualizationState(state) {
    if (state.rawData !== undefined) rawData = state.rawData || [];
    if (state.fullRawData !== undefined) fullRawData = state.fullRawData || [];
    if (state.dimensionFilteredData !== undefined) dimensionFilteredData = state.dimensionFilteredData || [];
    if (state.hierarchyData !== undefined) hierarchyData = state.hierarchyData;
}

/**
 * Reset all visualization state
 */
export function resetVisualizationState() {
    rawData = [];
    fullRawData = [];
    dimensionFilteredData = [];
    hierarchyData = null;
}
