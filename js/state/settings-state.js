/**
 * State management for the Settings page.
 */

let settingsInitialized = false;
let settingsCurrentClientId = null;

export function getSettingsInitialized() {
    return settingsInitialized;
}

export function setSettingsInitialized(value) {
    settingsInitialized = value;
}

export function getSettingsCurrentClientId() {
    return settingsCurrentClientId;
}

export function setSettingsCurrentClientId(clientId) {
    settingsCurrentClientId = clientId;
}

export function resetSettingsState() {
    settingsInitialized = false;
    settingsCurrentClientId = null;
}
