/**
 * Emails State Module
 * Manages state for the Emails tab including cache and UI state.
 * Follows state pattern - dedicated module for shared state.
 * Mirrors the structure of ads-state.js for consistency.
 */

// State variables
let emailsCache = [];
let emailsLoading = false;
let emailsError = null;
let emailsCurrentClientId = null;

// Filter/Sort/Search state
let emailsSearchTerm = '';
let emailsFilters = [];  // [{field: 'email_type', value: 'cart_abandonment'}, ...]
let emailsSortBy = 'created_at';
let emailsSortOrder = 'desc';

// ============ Cache State ============

/**
 * Get cached emails
 * @returns {Array} Array of email objects
 */
export function getEmailsCache() {
    return emailsCache;
}

/**
 * Set cached emails
 * @param {Array} emails - Array of email objects
 */
export function setEmailsCache(emails) {
    emailsCache = emails;
}

/**
 * Get loading state
 * @returns {boolean} True if loading
 */
export function getEmailsLoading() {
    return emailsLoading;
}

/**
 * Set loading state
 * @param {boolean} loading - Loading state
 */
export function setEmailsLoading(loading) {
    emailsLoading = loading;
}

/**
 * Get error state
 * @returns {string|null} Error message or null
 */
export function getEmailsError() {
    return emailsError;
}

/**
 * Set error state
 * @param {string|null} error - Error message or null
 */
export function setEmailsError(error) {
    emailsError = error;
}

/**
 * Get current client ID for emails
 * @returns {string|null} Client UUID or null
 */
export function getEmailsCurrentClientId() {
    return emailsCurrentClientId;
}

/**
 * Set current client ID for emails
 * @param {string|null} clientId - Client UUID or null
 */
export function setEmailsCurrentClientId(clientId) {
    emailsCurrentClientId = clientId;
}

/**
 * Clear all emails state
 */
export function clearEmailsState() {
    emailsCache = [];
    emailsLoading = false;
    emailsError = null;
    emailsSearchTerm = '';
    emailsFilters = [];
    emailsSortBy = 'created_at';
    emailsSortOrder = 'desc';
}

// ============ Search State ============

/**
 * Get search term
 * @returns {string} Current search term
 */
export function getEmailsSearchTerm() {
    return emailsSearchTerm;
}

/**
 * Set search term
 * @param {string} term - Search term
 */
export function setEmailsSearchTerm(term) {
    emailsSearchTerm = term;
}

// ============ Filter State ============

/**
 * Get active filters
 * @returns {Array} Array of filter objects [{field, value}, ...]
 */
export function getEmailsFilters() {
    return emailsFilters;
}

/**
 * Set filters
 * @param {Array} filters - Array of filter objects
 */
export function setEmailsFilters(filters) {
    emailsFilters = filters;
}

/**
 * Add a filter
 * @param {string} field - Field name (email_type, status)
 * @param {string} value - Filter value
 */
export function addEmailsFilter(field, value) {
    // Don't add duplicates
    const exists = emailsFilters.some(f => f.field === field && f.value === value);
    if (!exists) {
        emailsFilters = [...emailsFilters, { field, value }];
    }
}

/**
 * Remove a filter
 * @param {string} field - Field name
 * @param {string} value - Filter value
 */
export function removeEmailsFilter(field, value) {
    emailsFilters = emailsFilters.filter(f => !(f.field === field && f.value === value));
}

/**
 * Clear all filters
 */
export function clearEmailsFilters() {
    emailsFilters = [];
}

// ============ Sort State ============

/**
 * Get sort field
 * @returns {string} Current sort field
 */
export function getEmailsSortBy() {
    return emailsSortBy;
}

/**
 * Set sort field
 * @param {string} field - Sort field name
 */
export function setEmailsSortBy(field) {
    emailsSortBy = field;
}

/**
 * Get sort order
 * @returns {string} 'asc' or 'desc'
 */
export function getEmailsSortOrder() {
    return emailsSortOrder;
}

/**
 * Set sort order
 * @param {string} order - 'asc' or 'desc'
 */
export function setEmailsSortOrder(order) {
    emailsSortOrder = order;
}

/**
 * Toggle sort order
 */
export function toggleEmailsSortOrder() {
    emailsSortOrder = emailsSortOrder === 'asc' ? 'desc' : 'asc';
}

// ============ Cache Manipulation ============

/**
 * Remove an email from cache by ID
 * @param {string} emailId - Email UUID to remove
 */
export function removeEmailFromCache(emailId) {
    emailsCache = emailsCache.filter(email => email.id !== emailId);
}

/**
 * Add an email to cache
 * @param {Object} email - Email object to add
 */
export function addEmailToCache(email) {
    emailsCache = [email, ...emailsCache];
}

/**
 * Update an email in cache
 * @param {string} emailId - Email UUID
 * @param {Object} updates - Fields to update
 */
export function updateEmailInCache(emailId, updates) {
    emailsCache = emailsCache.map(email => 
        email.id === emailId ? { ...email, ...updates } : email
    );
}

// Expose state functions globally for legacy compatibility
window.emailsStateModule = {
    getEmailsCache,
    setEmailsCache,
    getEmailsLoading,
    setEmailsLoading,
    getEmailsError,
    setEmailsError,
    getEmailsCurrentClientId,
    setEmailsCurrentClientId,
    clearEmailsState,
    removeEmailFromCache,
    addEmailToCache,
    updateEmailInCache,
    // Search
    getEmailsSearchTerm,
    setEmailsSearchTerm,
    // Filters
    getEmailsFilters,
    setEmailsFilters,
    addEmailsFilter,
    removeEmailsFilter,
    clearEmailsFilters,
    // Sort
    getEmailsSortBy,
    setEmailsSortBy,
    getEmailsSortOrder,
    setEmailsSortOrder,
    toggleEmailsSortOrder
};
