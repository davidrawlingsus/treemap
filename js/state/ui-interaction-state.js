/**
 * UI Interaction State Management
 * Manages temporary UI interaction state (filter UI, verbatim display, editing, selection, resize)
 */

let currentFilterType = null;
let currentFilterSelections = new Set();
let currentFilterSearchTerm = '';
let currentVerbatimsData = null;
let currentTopicName = null;
let currentCategoryName = null;
let currentEditingRefKey = null;
let selectedInsightIds = new Set();
let currentResizeHeader = null;
let currentContextData = null;

/**
 * Get current filter type
 * @returns {string|null}
 */
export function getCurrentFilterType() {
    return currentFilterType;
}

/**
 * Set current filter type
 * @param {string|null} type
 */
export function setCurrentFilterType(type) {
    currentFilterType = type;
}

/**
 * Get current filter selections
 * @returns {Set}
 */
export function getCurrentFilterSelections() {
    return currentFilterSelections;
}

/**
 * Set current filter selections
 * @param {Set|Array} selections
 */
export function setCurrentFilterSelections(selections) {
    if (selections instanceof Set) {
        currentFilterSelections = selections;
    } else {
        currentFilterSelections = new Set(selections || []);
    }
}

/**
 * Add current filter selection
 * @param {string} selection
 */
export function addCurrentFilterSelection(selection) {
    if (selection != null) {
        currentFilterSelections.add(selection);
    }
}

/**
 * Remove current filter selection
 * @param {string} selection
 */
export function removeCurrentFilterSelection(selection) {
    currentFilterSelections.delete(selection);
}

/**
 * Clear current filter selections
 */
export function clearCurrentFilterSelections() {
    currentFilterSelections.clear();
}

/**
 * Get current filter search term
 * @returns {string}
 */
export function getCurrentFilterSearchTerm() {
    return currentFilterSearchTerm;
}

/**
 * Set current filter search term
 * @param {string} term
 */
export function setCurrentFilterSearchTerm(term) {
    currentFilterSearchTerm = term || '';
}

/**
 * Get current verbatims data
 * @returns {Array|null}
 */
export function getCurrentVerbatimsData() {
    return currentVerbatimsData;
}

/**
 * Set current verbatims data
 * @param {Array|null} data
 */
export function setCurrentVerbatimsData(data) {
    currentVerbatimsData = data;
}

/**
 * Get current topic name
 * @returns {string|null}
 */
export function getCurrentTopicName() {
    return currentTopicName;
}

/**
 * Set current topic name
 * @param {string|null} name
 */
export function setCurrentTopicName(name) {
    currentTopicName = name;
}

/**
 * Get current category name
 * @returns {string|null}
 */
export function getCurrentCategoryName() {
    return currentCategoryName;
}

/**
 * Set current category name
 * @param {string|null} name
 */
export function setCurrentCategoryName(name) {
    currentCategoryName = name;
}

/**
 * Get current editing ref key
 * @returns {string|null}
 */
export function getCurrentEditingRefKey() {
    return currentEditingRefKey;
}

/**
 * Set current editing ref key
 * @param {string|null} refKey
 */
export function setCurrentEditingRefKey(refKey) {
    currentEditingRefKey = refKey;
}

/**
 * Get selected insight IDs
 * @returns {Set}
 */
export function getSelectedInsightIds() {
    return selectedInsightIds;
}

/**
 * Set selected insight IDs
 * @param {Set|Array} ids
 */
export function setSelectedInsightIds(ids) {
    if (ids instanceof Set) {
        selectedInsightIds = ids;
    } else {
        selectedInsightIds = new Set(ids || []);
    }
}

/**
 * Add selected insight ID
 * @param {string|number} id
 */
export function addSelectedInsightId(id) {
    if (id != null) {
        selectedInsightIds.add(id);
    }
}

/**
 * Remove selected insight ID
 * @param {string|number} id
 */
export function removeSelectedInsightId(id) {
    selectedInsightIds.delete(id);
}

/**
 * Clear selected insight IDs
 */
export function clearSelectedInsightIds() {
    selectedInsightIds.clear();
}

/**
 * Get current resize header
 * @returns {HTMLElement|null}
 */
export function getCurrentResizeHeader() {
    return currentResizeHeader;
}

/**
 * Set current resize header
 * @param {HTMLElement|null} header
 */
export function setCurrentResizeHeader(header) {
    currentResizeHeader = header;
}

/**
 * Get current context data
 * @returns {Object|null}
 */
export function getCurrentContextData() {
    return currentContextData;
}

/**
 * Set current context data
 * @param {Object|null} data
 */
export function setCurrentContextData(data) {
    currentContextData = data;
}

/**
 * Get all UI interaction state
 * @returns {Object}
 */
export function getUiInteractionState() {
    return {
        currentFilterType,
        currentFilterSelections: Array.from(currentFilterSelections),
        currentFilterSearchTerm,
        currentVerbatimsData,
        currentTopicName,
        currentCategoryName,
        currentEditingRefKey,
        selectedInsightIds: Array.from(selectedInsightIds),
        currentResizeHeader,
        currentContextData
    };
}

/**
 * Set all UI interaction state
 * @param {Object} state
 */
export function setUiInteractionState(state) {
    if (state.currentFilterType !== undefined) currentFilterType = state.currentFilterType;
    if (state.currentFilterSelections !== undefined) {
        if (state.currentFilterSelections instanceof Set) {
            currentFilterSelections = state.currentFilterSelections;
        } else {
            currentFilterSelections = new Set(state.currentFilterSelections || []);
        }
    }
    if (state.currentFilterSearchTerm !== undefined) currentFilterSearchTerm = state.currentFilterSearchTerm || '';
    if (state.currentVerbatimsData !== undefined) currentVerbatimsData = state.currentVerbatimsData;
    if (state.currentTopicName !== undefined) currentTopicName = state.currentTopicName;
    if (state.currentCategoryName !== undefined) currentCategoryName = state.currentCategoryName;
    if (state.currentEditingRefKey !== undefined) currentEditingRefKey = state.currentEditingRefKey;
    if (state.selectedInsightIds !== undefined) {
        if (state.selectedInsightIds instanceof Set) {
            selectedInsightIds = state.selectedInsightIds;
        } else {
            selectedInsightIds = new Set(state.selectedInsightIds || []);
        }
    }
    if (state.currentResizeHeader !== undefined) currentResizeHeader = state.currentResizeHeader;
    if (state.currentContextData !== undefined) currentContextData = state.currentContextData;
}

/**
 * Reset all UI interaction state
 */
export function resetUiInteractionState() {
    currentFilterType = null;
    currentFilterSelections.clear();
    currentFilterSearchTerm = '';
    currentVerbatimsData = null;
    currentTopicName = null;
    currentCategoryName = null;
    currentEditingRefKey = null;
    selectedInsightIds.clear();
    currentResizeHeader = null;
    currentContextData = null;
}
