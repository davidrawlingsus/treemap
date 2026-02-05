/**
 * Emails Filter UI Module
 * Handles filter chips, dropdowns, and badge for emails tab.
 * Follows the pattern from ads-filter-ui.js for consistency.
 */

import {
    getEmailsFilters,
    setEmailsFilters,
    addEmailsFilter,
    removeEmailsFilter,
    clearEmailsFilters
} from '/js/state/emails-state.js';

// ============ Email Type Options ============

export const EMAIL_TYPE_OPTIONS = [
    { id: 'discount_code_welcome', label: 'Discount Code & O/CO' },
    { id: 'post_purchase_onboarding', label: 'Post-Purchase Onboarding' },
    { id: 'cart_abandonment', label: 'Cart Abandonment' },
    { id: 'replenishment_reminder', label: 'Replenishment Reminder' },
    { id: 'browse_abandonment', label: 'Browse Abandonment' }
];

// ============ Status Options ============

export const EMAIL_STATUS_OPTIONS = [
    { id: 'draft', label: 'Draft' },
    { id: 'ready', label: 'Ready' },
    { id: 'exported', label: 'Exported' }
];

/**
 * Normalize status value for comparison
 * @param {string} status - Status value from API
 * @returns {string} Normalized lowercase status
 */
export function normalizeStatus(status) {
    if (!status) return 'draft';
    return status.toLowerCase().trim();
}

/**
 * Get status display config
 * @param {string} normalizedStatus - Normalized status value
 * @returns {Object} Status config with label and class
 */
export function getStatusConfig(normalizedStatus) {
    const option = EMAIL_STATUS_OPTIONS.find(s => s.id === normalizedStatus);
    return option || { id: 'draft', label: 'Draft' };
}

/**
 * Get email type display label
 * @param {string} typeId - Email type ID
 * @returns {string} Display label
 */
export function getEmailTypeLabel(typeId) {
    const option = EMAIL_TYPE_OPTIONS.find(t => t.id === typeId);
    return option ? option.label : typeId || 'Unknown';
}

// ============ Filter Options Population ============

/**
 * Populate filter options in the dropdown
 * @param {Function} getUniqueValuesFn - Function to get unique values for a field
 */
export function populateEmailsFilterOptions(getUniqueValuesFn) {
    const optionsList = document.getElementById('emailsFilterOptionsList');
    if (!optionsList) return;
    
    const currentFilters = getEmailsFilters();
    
    // Build options HTML
    let html = '';
    
    // Email Type filter
    html += `<div class="filter-option" data-field="email_type">
        <span class="filter-option__label">Email Type</span>
        <span class="filter-option__arrow">›</span>
    </div>`;
    
    // Status filter
    html += `<div class="filter-option" data-field="status">
        <span class="filter-option__label">Status</span>
        <span class="filter-option__arrow">›</span>
    </div>`;
    
    optionsList.innerHTML = html;
}

/**
 * Open filter value selection dialog
 * @param {string} fieldId - Field to filter on
 * @param {Function} getUniqueValuesFn - Function to get unique values
 * @param {Function} onChangeFn - Callback when filter changes
 */
export function openEmailsFilterValueDialog(fieldId, getUniqueValuesFn, onChangeFn) {
    const dropdown = document.getElementById('emailsFilterDropdown');
    if (!dropdown) return;
    
    const currentFilters = getEmailsFilters();
    const activeValues = currentFilters
        .filter(f => f.field === fieldId)
        .map(f => f.value.toLowerCase());
    
    // Get options based on field type
    let options = [];
    if (fieldId === 'email_type') {
        options = EMAIL_TYPE_OPTIONS.map(t => t.label);
    } else if (fieldId === 'status') {
        options = EMAIL_STATUS_OPTIONS.map(s => s.label);
    } else {
        options = getUniqueValuesFn(fieldId);
    }
    
    // Build value selection HTML
    const valuesHtml = options.map(value => {
        const isActive = activeValues.includes(value.toLowerCase());
        return `
            <div class="filter-value-option ${isActive ? 'active' : ''}" data-value="${value}">
                <span class="filter-value-option__check">${isActive ? '✓' : ''}</span>
                <span class="filter-value-option__label">${value}</span>
            </div>
        `;
    }).join('');
    
    // Show values in dropdown
    const optionsList = document.getElementById('emailsFilterOptionsList');
    optionsList.innerHTML = `
        <div class="filter-values-header">
            <button class="filter-values-back" onclick="populateEmailsFilterOptions()">← Back</button>
            <span>${fieldId === 'email_type' ? 'Email Type' : 'Status'}</span>
        </div>
        <div class="filter-values-list">
            ${valuesHtml}
        </div>
    `;
    
    // Attach value click handlers
    optionsList.querySelectorAll('.filter-value-option').forEach(option => {
        option.addEventListener('click', () => {
            const value = option.dataset.value;
            const isActive = option.classList.contains('active');
            
            if (isActive) {
                removeEmailsFilter(fieldId, value);
                option.classList.remove('active');
                option.querySelector('.filter-value-option__check').textContent = '';
            } else {
                addEmailsFilter(fieldId, value);
                option.classList.add('active');
                option.querySelector('.filter-value-option__check').textContent = '✓';
            }
            
            onChangeFn();
        });
    });
}

// ============ Inline Filter Chips ============

/**
 * Toggle inline filter dropdown for a field
 * @param {string} fieldId - Field name
 * @param {Event} e - Click event
 */
export function toggleEmailsInlineFilterDropdown(fieldId, e) {
    e?.stopPropagation();
    
    // Close other dropdowns
    document.querySelectorAll('.emails-inline-filter__dropdown.open').forEach(d => {
        if (d.dataset.field !== fieldId) d.classList.remove('open');
    });
    
    const dropdown = document.querySelector(`.emails-inline-filter__dropdown[data-field="${fieldId}"]`);
    dropdown?.classList.toggle('open');
}

/**
 * Toggle inline filter value
 * @param {string} fieldId - Field name
 * @param {string} value - Value to toggle
 * @param {Function} onChangeFn - Callback when filter changes
 */
export function toggleEmailsInlineFilterValue(fieldId, value, onChangeFn) {
    const currentFilters = getEmailsFilters();
    const exists = currentFilters.some(f => f.field === fieldId && f.value.toLowerCase() === value.toLowerCase());
    
    if (exists) {
        removeEmailsFilter(fieldId, value);
    } else {
        addEmailsFilter(fieldId, value);
    }
    
    onChangeFn();
}

/**
 * Remove inline filter
 * @param {string} fieldId - Field name
 * @param {Function} onChangeFn - Callback when filter changes
 */
export function removeEmailsInlineFilter(fieldId, onChangeFn) {
    const currentFilters = getEmailsFilters();
    const newFilters = currentFilters.filter(f => f.field !== fieldId);
    setEmailsFilters(newFilters);
    onChangeFn();
}

// ============ Filter Badge ============

/**
 * Update filter badge count
 */
export function updateEmailsFilterBadge() {
    const badge = document.getElementById('emailsFilterBadge');
    const count = getEmailsFilters().length;
    
    if (badge) {
        badge.textContent = count;
        badge.style.display = count > 0 ? 'inline-flex' : 'none';
    }
}

// ============ Clear All Filters ============

/**
 * Clear all email filters
 * @param {Function} onChangeFn - Callback when filters cleared
 */
export function clearAllEmailsFilters(onChangeFn) {
    clearEmailsFilters();
    onChangeFn();
}
