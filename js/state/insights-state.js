/**
 * Insights State Management
 * Manages insights page state (insights list, filters, sorting, search, current insight)
 */

let insightsCurrentClientId = null;
let insightsCurrentInsightId = null;
let insightsAllInsights = [];
let allInsights = [];
let insightsFilters = []; // Array to support multiple filters
let insightsCurrentFilters = {};
let insightsCurrentSortBy = 'name';
let insightsSortBy = 'name';
let insightsSortOrder = 'asc';
let insightsSearchTerm = '';
let insightsCurrentInsightEditor = null;
let insightsAutoFilter = true;

/**
 * Get current insights client ID
 * @returns {string|null}
 */
export function getInsightsCurrentClientId() {
    return insightsCurrentClientId;
}

/**
 * Set current insights client ID
 * @param {string|null} clientId
 */
export function setInsightsCurrentClientId(clientId) {
    insightsCurrentClientId = clientId;
}

/**
 * Get current insight ID
 * @returns {string|null}
 */
export function getInsightsCurrentInsightId() {
    return insightsCurrentInsightId;
}

/**
 * Set current insight ID
 * @param {string|null} insightId
 */
export function setInsightsCurrentInsightId(insightId) {
    insightsCurrentInsightId = insightId;
}

/**
 * Get all insights (raw API response)
 * @returns {Array}
 */
export function getInsightsAllInsights() {
    return insightsAllInsights;
}

/**
 * Set all insights (raw API response)
 * @param {Array} insights
 */
export function setInsightsAllInsights(insights) {
    insightsAllInsights = insights || [];
}

/**
 * Get all insights (filtered/processed)
 * @returns {Array}
 */
export function getAllInsights() {
    return allInsights;
}

/**
 * Set all insights (filtered/processed)
 * @param {Array} insights
 */
export function setAllInsights(insights) {
    allInsights = insights || [];
}

/**
 * Get insights filters
 * @returns {Array}
 */
export function getInsightsFilters() {
    return insightsFilters;
}

/**
 * Set insights filters
 * @param {Array} filters
 */
export function setInsightsFilters(filters) {
    insightsFilters = filters || [];
}

/**
 * Get insights current filters
 * @returns {Object}
 */
export function getInsightsCurrentFilters() {
    return insightsCurrentFilters;
}

/**
 * Set insights current filters
 * @param {Object} filters
 */
export function setInsightsCurrentFilters(filters) {
    insightsCurrentFilters = filters || {};
}

/**
 * Get insights current sort by
 * @returns {string}
 */
export function getInsightsCurrentSortBy() {
    return insightsCurrentSortBy;
}

/**
 * Set insights current sort by
 * @param {string} sortBy
 */
export function setInsightsCurrentSortBy(sortBy) {
    insightsCurrentSortBy = sortBy || 'name';
}

/**
 * Get insights sort by
 * @returns {string}
 */
export function getInsightsSortBy() {
    return insightsSortBy;
}

/**
 * Set insights sort by
 * @param {string} sortBy
 */
export function setInsightsSortBy(sortBy) {
    insightsSortBy = sortBy || 'name';
}

/**
 * Get insights sort order
 * @returns {string}
 */
export function getInsightsSortOrder() {
    return insightsSortOrder;
}

/**
 * Set insights sort order
 * @param {string} order
 */
export function setInsightsSortOrder(order) {
    insightsSortOrder = order || 'asc';
}

/**
 * Get insights search term
 * @returns {string}
 */
export function getInsightsSearchTerm() {
    return insightsSearchTerm;
}

/**
 * Set insights search term
 * @param {string} term
 */
export function setInsightsSearchTerm(term) {
    insightsSearchTerm = term || '';
}

/**
 * Get insights current insight editor
 * @returns {Object|null}
 */
export function getInsightsCurrentInsightEditor() {
    return insightsCurrentInsightEditor;
}

/**
 * Set insights current insight editor
 * @param {Object|null} editor
 */
export function setInsightsCurrentInsightEditor(editor) {
    insightsCurrentInsightEditor = editor;
}

/**
 * Get insights auto filter
 * @returns {boolean}
 */
export function getInsightsAutoFilter() {
    return insightsAutoFilter;
}

/**
 * Set insights auto filter
 * @param {boolean} enabled
 */
export function setInsightsAutoFilter(enabled) {
    insightsAutoFilter = enabled !== undefined ? enabled : true;
}

/**
 * Get all insights state
 * @returns {Object}
 */
export function getInsightsState() {
    return {
        insightsCurrentClientId,
        insightsCurrentInsightId,
        insightsAllInsights: [...insightsAllInsights],
        allInsights: [...allInsights],
        insightsFilters: [...insightsFilters],
        insightsCurrentFilters: { ...insightsCurrentFilters },
        insightsCurrentSortBy,
        insightsSortBy,
        insightsSortOrder,
        insightsSearchTerm,
        insightsCurrentInsightEditor,
        insightsAutoFilter
    };
}

/**
 * Set all insights state
 * @param {Object} state
 */
export function setInsightsState(state) {
    if (state.insightsCurrentClientId !== undefined) insightsCurrentClientId = state.insightsCurrentClientId;
    if (state.insightsCurrentInsightId !== undefined) insightsCurrentInsightId = state.insightsCurrentInsightId;
    if (state.insightsAllInsights !== undefined) insightsAllInsights = state.insightsAllInsights || [];
    if (state.allInsights !== undefined) allInsights = state.allInsights || [];
    if (state.insightsFilters !== undefined) insightsFilters = state.insightsFilters || [];
    if (state.insightsCurrentFilters !== undefined) insightsCurrentFilters = state.insightsCurrentFilters || {};
    if (state.insightsCurrentSortBy !== undefined) insightsCurrentSortBy = state.insightsCurrentSortBy || 'name';
    if (state.insightsSortBy !== undefined) insightsSortBy = state.insightsSortBy || 'name';
    if (state.insightsSortOrder !== undefined) insightsSortOrder = state.insightsSortOrder || 'asc';
    if (state.insightsSearchTerm !== undefined) insightsSearchTerm = state.insightsSearchTerm || '';
    if (state.insightsCurrentInsightEditor !== undefined) insightsCurrentInsightEditor = state.insightsCurrentInsightEditor;
    if (state.insightsAutoFilter !== undefined) insightsAutoFilter = state.insightsAutoFilter !== undefined ? state.insightsAutoFilter : true;
}

/**
 * Reset all insights state
 */
export function resetInsightsState() {
    insightsCurrentClientId = null;
    insightsCurrentInsightId = null;
    insightsAllInsights = [];
    allInsights = [];
    insightsFilters = [];
    insightsCurrentFilters = {};
    insightsCurrentSortBy = 'name';
    insightsSortBy = 'name';
    insightsSortOrder = 'asc';
    insightsSearchTerm = '';
    insightsCurrentInsightEditor = null;
    insightsAutoFilter = true;
}
