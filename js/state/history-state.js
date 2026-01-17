/**
 * History State Management
 * Manages history page state (actions list, filters, sorting, search, selected items)
 */

let historyCurrentClientId = null;
let historyAllActions = [];
let historySearchTerm = '';
let selectedHistoryIds = new Set();
let historyCurrentSortBy = 'created_at';
let historySortOrder = 'desc';
let historyInitialized = false;

/**
 * Get current history client ID
 * @returns {string|null}
 */
export function getHistoryCurrentClientId() {
    return historyCurrentClientId;
}

/**
 * Set current history client ID
 * @param {string|null} clientId
 */
export function setHistoryCurrentClientId(clientId) {
    historyCurrentClientId = clientId;
}

/**
 * Get all history actions
 * @returns {Array}
 */
export function getHistoryAllActions() {
    return historyAllActions;
}

/**
 * Set all history actions
 * @param {Array} actions
 */
export function setHistoryAllActions(actions) {
    historyAllActions = actions || [];
}

/**
 * Get history search term
 * @returns {string}
 */
export function getHistorySearchTerm() {
    return historySearchTerm;
}

/**
 * Set history search term
 * @param {string} term
 */
export function setHistorySearchTerm(term) {
    historySearchTerm = term || '';
}

/**
 * Get selected history IDs
 * @returns {Set}
 */
export function getSelectedHistoryIds() {
    return selectedHistoryIds;
}

/**
 * Set selected history IDs
 * @param {Set|Array} ids
 */
export function setSelectedHistoryIds(ids) {
    if (ids instanceof Set) {
        selectedHistoryIds = ids;
    } else {
        selectedHistoryIds = new Set(ids || []);
    }
}

/**
 * Add selected history ID
 * @param {string|number} id
 */
export function addSelectedHistoryId(id) {
    if (id != null) {
        selectedHistoryIds.add(id);
    }
}

/**
 * Remove selected history ID
 * @param {string|number} id
 */
export function removeSelectedHistoryId(id) {
    selectedHistoryIds.delete(id);
}

/**
 * Check if history ID is selected
 * @param {string|number} id
 * @returns {boolean}
 */
export function hasSelectedHistoryId(id) {
    return selectedHistoryIds.has(id);
}

/**
 * Clear all selected history IDs
 */
export function clearSelectedHistoryIds() {
    selectedHistoryIds.clear();
}

/**
 * Get history current sort by
 * @returns {string}
 */
export function getHistoryCurrentSortBy() {
    return historyCurrentSortBy;
}

/**
 * Set history current sort by
 * @param {string} sortBy
 */
export function setHistoryCurrentSortBy(sortBy) {
    historyCurrentSortBy = sortBy || 'created_at';
}

/**
 * Get history sort order
 * @returns {string}
 */
export function getHistorySortOrder() {
    return historySortOrder;
}

/**
 * Set history sort order
 * @param {string} order
 */
export function setHistorySortOrder(order) {
    historySortOrder = order || 'desc';
}

/**
 * Get history initialized flag
 * @returns {boolean}
 */
export function getHistoryInitialized() {
    return historyInitialized;
}

/**
 * Set history initialized flag
 * @param {boolean} initialized
 */
export function setHistoryInitialized(initialized) {
    historyInitialized = initialized !== undefined ? initialized : false;
}

/**
 * Get all history state
 * @returns {Object}
 */
export function getHistoryState() {
    return {
        historyCurrentClientId,
        historyAllActions: [...historyAllActions],
        historySearchTerm,
        selectedHistoryIds: Array.from(selectedHistoryIds),
        historyCurrentSortBy,
        historySortOrder,
        historyInitialized
    };
}

/**
 * Set all history state
 * @param {Object} state
 */
export function setHistoryState(state) {
    if (state.historyCurrentClientId !== undefined) historyCurrentClientId = state.historyCurrentClientId;
    if (state.historyAllActions !== undefined) historyAllActions = state.historyAllActions || [];
    if (state.historySearchTerm !== undefined) historySearchTerm = state.historySearchTerm || '';
    if (state.selectedHistoryIds !== undefined) {
        if (state.selectedHistoryIds instanceof Set) {
            selectedHistoryIds = state.selectedHistoryIds;
        } else {
            selectedHistoryIds = new Set(state.selectedHistoryIds || []);
        }
    }
    if (state.historyCurrentSortBy !== undefined) historyCurrentSortBy = state.historyCurrentSortBy || 'created_at';
    if (state.historySortOrder !== undefined) historySortOrder = state.historySortOrder || 'desc';
    if (state.historyInitialized !== undefined) historyInitialized = state.historyInitialized !== undefined ? state.historyInitialized : false;
}

/**
 * Reset all history state
 */
export function resetHistoryState() {
    historyCurrentClientId = null;
    historyAllActions = [];
    historySearchTerm = '';
    selectedHistoryIds.clear();
    historyCurrentSortBy = 'created_at';
    historySortOrder = 'desc';
    historyInitialized = false;
}
