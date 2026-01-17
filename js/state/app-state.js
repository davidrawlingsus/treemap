/**
 * Application State Management
 * Manages core selection state (client, project, data source, question)
 */

let currentClientId = null;
let currentProjectName = null;
let currentDataSourceId = null;
let currentQuestionRefKey = null;

/**
 * Get current client ID
 * @returns {string|null}
 */
export function getCurrentClientId() {
    return currentClientId;
}

/**
 * Set current client ID
 * @param {string|null} clientId
 */
export function setCurrentClientId(clientId) {
    currentClientId = clientId;
}

/**
 * Get current project name
 * @returns {string|null}
 */
export function getCurrentProjectName() {
    return currentProjectName;
}

/**
 * Set current project name
 * @param {string|null} projectName
 */
export function setCurrentProjectName(projectName) {
    currentProjectName = projectName;
}

/**
 * Get current data source ID
 * @returns {string|null}
 */
export function getCurrentDataSourceId() {
    return currentDataSourceId;
}

/**
 * Set current data source ID
 * @param {string|null} dataSourceId
 */
export function setCurrentDataSourceId(dataSourceId) {
    currentDataSourceId = dataSourceId;
}

/**
 * Get current question ref key
 * @returns {string|null}
 */
export function getCurrentQuestionRefKey() {
    return currentQuestionRefKey;
}

/**
 * Set current question ref key
 * @param {string|null} questionRefKey
 */
export function setCurrentQuestionRefKey(questionRefKey) {
    currentQuestionRefKey = questionRefKey;
}

/**
 * Get all current state
 * @returns {Object} State object
 */
export function getState() {
    return {
        clientId: currentClientId,
        projectName: currentProjectName,
        dataSourceId: currentDataSourceId,
        questionRefKey: currentQuestionRefKey
    };
}

/**
 * Set all state at once
 * @param {Object} state - State object
 */
export function setState(state) {
    if (state.clientId !== undefined) currentClientId = state.clientId;
    if (state.projectName !== undefined) currentProjectName = state.projectName;
    if (state.dataSourceId !== undefined) currentDataSourceId = state.dataSourceId;
    if (state.questionRefKey !== undefined) currentQuestionRefKey = state.questionRefKey;
}

/**
 * Reset all state to null
 */
export function resetState() {
    currentClientId = null;
    currentProjectName = null;
    currentDataSourceId = null;
    currentQuestionRefKey = null;
}
