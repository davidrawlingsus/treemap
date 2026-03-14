let founderUser = null;
let clients = [];
let storeConnections = [];
let rawResponses = [];
let selectedClientUuid = '';
let selectedShopDomain = '';

export function getFounderUser() {
    return founderUser;
}

export function setFounderUser(user) {
    founderUser = user;
}

export function getClients() {
    return clients;
}

export function setClients(nextClients) {
    clients = Array.isArray(nextClients) ? nextClients : [];
}

export function getStoreConnections() {
    return storeConnections;
}

export function setStoreConnections(nextConnections) {
    storeConnections = Array.isArray(nextConnections) ? nextConnections : [];
}

export function getRawResponses() {
    return rawResponses;
}

export function setRawResponses(nextResponses) {
    rawResponses = Array.isArray(nextResponses) ? nextResponses : [];
}

export function getSelectedClientUuid() {
    return selectedClientUuid;
}

export function setSelectedClientUuid(value) {
    selectedClientUuid = String(value || '');
}

export function getSelectedShopDomain() {
    return selectedShopDomain;
}

export function setSelectedShopDomain(value) {
    selectedShopDomain = String(value || '');
}
