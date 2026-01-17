/**
 * Available Options State Management
 * Manages available filter options extracted from data (questions, categories, topics, locations)
 */

let availableQuestions = [];
let availableCategories = [];
let availableTopics = [];
let availableLocations = [];

/**
 * Get available questions
 * @returns {Array}
 */
export function getAvailableQuestions() {
    return availableQuestions;
}

/**
 * Set available questions
 * @param {Array} questions
 */
export function setAvailableQuestions(questions) {
    availableQuestions = questions || [];
}

/**
 * Get available categories
 * @returns {Array}
 */
export function getAvailableCategories() {
    return availableCategories;
}

/**
 * Set available categories
 * @param {Array} categories
 */
export function setAvailableCategories(categories) {
    availableCategories = categories || [];
}

/**
 * Get available topics
 * @returns {Array}
 */
export function getAvailableTopics() {
    return availableTopics;
}

/**
 * Set available topics
 * @param {Array} topics
 */
export function setAvailableTopics(topics) {
    availableTopics = topics || [];
}

/**
 * Get available locations
 * @returns {Array}
 */
export function getAvailableLocations() {
    return availableLocations;
}

/**
 * Set available locations
 * @param {Array} locations
 */
export function setAvailableLocations(locations) {
    availableLocations = locations || [];
}

/**
 * Get all available options state
 * @returns {Object}
 */
export function getAvailableOptionsState() {
    return {
        availableQuestions,
        availableCategories,
        availableTopics,
        availableLocations
    };
}

/**
 * Set all available options state
 * @param {Object} state
 */
export function setAvailableOptionsState(state) {
    if (state.availableQuestions !== undefined) availableQuestions = state.availableQuestions || [];
    if (state.availableCategories !== undefined) availableCategories = state.availableCategories || [];
    if (state.availableTopics !== undefined) availableTopics = state.availableTopics || [];
    if (state.availableLocations !== undefined) availableLocations = state.availableLocations || [];
}

/**
 * Reset all available options state
 */
export function resetAvailableOptionsState() {
    availableQuestions = [];
    availableCategories = [];
    availableTopics = [];
    availableLocations = [];
}
