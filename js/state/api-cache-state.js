/**
 * API Cache State Management
 * Manages cached API data (clients, projects, sources, dimension names, question types)
 */

let allClients = [];
let clientProjects = [];
let clientSources = [];
let dimensionNamesMap = {}; // Map of ref_key -> custom_name
let questionTypesMap = {}; // Map of dimension_ref -> question_type

/**
 * Get all clients
 * @returns {Array}
 */
export function getAllClients() {
    return allClients;
}

/**
 * Set all clients
 * @param {Array} clients
 */
export function setAllClients(clients) {
    allClients = clients || [];
}

/**
 * Get client projects
 * @returns {Array}
 */
export function getClientProjects() {
    return clientProjects;
}

/**
 * Set client projects
 * @param {Array} projects
 */
export function setClientProjects(projects) {
    clientProjects = projects || [];
}

/**
 * Get client sources
 * @returns {Array}
 */
export function getClientSources() {
    return clientSources;
}

/**
 * Set client sources
 * @param {Array} sources
 */
export function setClientSources(sources) {
    clientSources = sources || [];
}

/**
 * Get dimension names map
 * @returns {Object}
 */
export function getDimensionNamesMap() {
    return dimensionNamesMap;
}

/**
 * Set dimension names map
 * @param {Object} map
 */
export function setDimensionNamesMap(map) {
    dimensionNamesMap = map || {};
}

/**
 * Get dimension name by ref key
 * @param {string} refKey
 * @returns {string|undefined}
 */
export function getDimensionName(refKey) {
    return dimensionNamesMap[refKey];
}

/**
 * Set dimension name for ref key
 * @param {string} refKey
 * @param {string} name
 */
export function setDimensionName(refKey, name) {
    if (refKey) {
        dimensionNamesMap[refKey] = name;
    }
}

/**
 * Get question types map
 * @returns {Object}
 */
export function getQuestionTypesMap() {
    return questionTypesMap;
}

/**
 * Set question types map
 * @param {Object} map
 */
export function setQuestionTypesMap(map) {
    questionTypesMap = map || {};
}

/**
 * Get question type by dimension ref
 * @param {string} dimensionRef
 * @returns {string|undefined}
 */
export function getQuestionType(dimensionRef) {
    return questionTypesMap[dimensionRef];
}

/**
 * Set question type for dimension ref
 * @param {string} dimensionRef
 * @param {string} type
 */
export function setQuestionType(dimensionRef, type) {
    if (dimensionRef) {
        questionTypesMap[dimensionRef] = type;
    }
}

/**
 * Get all API cache state
 * @returns {Object}
 */
export function getApiCacheState() {
    return {
        allClients: [...allClients],
        clientProjects: [...clientProjects],
        clientSources: [...clientSources],
        dimensionNamesMap: { ...dimensionNamesMap },
        questionTypesMap: { ...questionTypesMap }
    };
}

/**
 * Set all API cache state
 * @param {Object} state
 */
export function setApiCacheState(state) {
    if (state.allClients !== undefined) allClients = state.allClients || [];
    if (state.clientProjects !== undefined) clientProjects = state.clientProjects || [];
    if (state.clientSources !== undefined) clientSources = state.clientSources || [];
    if (state.dimensionNamesMap !== undefined) dimensionNamesMap = state.dimensionNamesMap || {};
    if (state.questionTypesMap !== undefined) questionTypesMap = state.questionTypesMap || {};
}

/**
 * Reset all API cache state
 */
export function resetApiCacheState() {
    allClients = [];
    clientProjects = [];
    clientSources = [];
    dimensionNamesMap = {};
    questionTypesMap = {};
}
