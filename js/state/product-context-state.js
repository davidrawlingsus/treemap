/**
 * State management for Product Context in Settings.
 */

let productContextsList = [];
let productContextSelectedId = null;
let productContextDirty = false;
let productContextExtractedData = null;
let productContextShowUrlInput = false;

export function getProductContextsList() {
    return productContextsList;
}

export function setProductContextsList(list) {
    productContextsList = list || [];
}

export function getProductContextSelectedId() {
    return productContextSelectedId;
}

export function setProductContextSelectedId(id) {
    productContextSelectedId = id;
}

export function getProductContextDirty() {
    return productContextDirty;
}

export function setProductContextDirty(value) {
    productContextDirty = !!value;
}

export function getProductContextExtractedData() {
    return productContextExtractedData;
}

export function setProductContextExtractedData(data) {
    productContextExtractedData = data;
}

export function getProductContextShowUrlInput() {
    return productContextShowUrlInput;
}

export function setProductContextShowUrlInput(value) {
    productContextShowUrlInput = !!value;
}

export function resetProductContextState() {
    productContextsList = [];
    productContextSelectedId = null;
    productContextDirty = false;
    productContextExtractedData = null;
    productContextShowUrlInput = false;
}
