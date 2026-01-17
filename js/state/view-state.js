/**
 * View State Management
 * Manages view navigation state (current view, view stack, source format)
 */

let currentView = 'root';
let viewStack = [];
let currentSourceFormat = null;

/**
 * Get current view
 * @returns {string}
 */
export function getCurrentView() {
    return currentView;
}

/**
 * Set current view
 * @param {string} view
 */
export function setCurrentView(view) {
    currentView = view || 'root';
}

/**
 * Get view stack
 * @returns {Array}
 */
export function getViewStack() {
    return viewStack;
}

/**
 * Set view stack
 * @param {Array} stack
 */
export function setViewStack(stack) {
    viewStack = stack || [];
}

/**
 * Push view onto stack
 * @param {string} view
 */
export function pushView(view) {
    if (view) {
        viewStack.push(view);
    }
}

/**
 * Pop view from stack
 * @returns {string|null}
 */
export function popView() {
    return viewStack.pop() || null;
}

/**
 * Clear view stack
 */
export function clearViewStack() {
    viewStack = [];
}

/**
 * Get current source format
 * @returns {string|null}
 */
export function getCurrentSourceFormat() {
    return currentSourceFormat;
}

/**
 * Set current source format
 * @param {string|null} format
 */
export function setCurrentSourceFormat(format) {
    currentSourceFormat = format;
}

/**
 * Get all view state
 * @returns {Object}
 */
export function getViewState() {
    return {
        currentView,
        viewStack: [...viewStack], // Return copy of stack
        currentSourceFormat
    };
}

/**
 * Set all view state
 * @param {Object} state
 */
export function setViewState(state) {
    if (state.currentView !== undefined) currentView = state.currentView || 'root';
    if (state.viewStack !== undefined) viewStack = state.viewStack || [];
    if (state.currentSourceFormat !== undefined) currentSourceFormat = state.currentSourceFormat;
}

/**
 * Reset all view state
 */
export function resetViewState() {
    currentView = 'root';
    viewStack = [];
    currentSourceFormat = null;
}
