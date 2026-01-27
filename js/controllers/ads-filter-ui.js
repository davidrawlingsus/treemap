/**
 * Ads Filter UI Module
 * Handles inline filter dropdown creation and management for Ads tab.
 * Follows controller pattern - UI orchestration for filter components.
 */

import { 
    getAdsFilters, addAdsFilter, removeAdsFilter, clearAdsFilters 
} from '/js/state/ads-state.js';
import { escapeHtml, escapeHtmlForAttribute } from '/js/utils/dom.js';

// Status options configuration
export const AD_STATUS_OPTIONS = [
    { id: 'draft', label: 'Draft', color: '#fef3c7', textColor: '#92400e' },
    { id: 'queued', label: 'Queued', color: '#e0e7ff', textColor: '#3730a3' },
    { id: 'testing', label: 'Testing', color: '#fce7f3', textColor: '#9d174d' },
    { id: 'live', label: 'Live', color: '#d1fae5', textColor: '#065f46' },
    { id: 'retired', label: 'Retired', color: '#f3f4f6', textColor: '#6b7280' }
];

/**
 * Normalize status value - convert any unknown status to 'draft'
 * @param {string} status - Raw status value
 * @returns {string} Normalized status
 */
export function normalizeStatus(status) {
    const validStatuses = AD_STATUS_OPTIONS.map(s => s.id);
    const normalized = (status || 'draft').toLowerCase();
    return validStatuses.includes(normalized) ? normalized : 'draft';
}

/**
 * Get status config by ID
 * @param {string} statusId - Status ID
 * @returns {Object} Status config object
 */
export function getStatusConfig(statusId) {
    const normalized = normalizeStatus(statusId);
    return AD_STATUS_OPTIONS.find(s => s.id === normalized) || AD_STATUS_OPTIONS[0];
}

// Filter field configuration
export const ADS_FILTER_FIELDS = [
    { id: 'status', label: 'Status', icon: '📊', type: 'select' },
    { id: 'testType', label: 'Test Type', icon: '🧪', type: 'select' },
    { id: 'origin', label: 'Origin', icon: '📍', type: 'select' }
];

/**
 * Populate the filter dropdown with field options
 * @param {Function} getUniqueFilterValues - Function to get unique values for a field
 */
export function populateAdsFilterOptions(getUniqueFilterValues) {
    const optionsList = document.getElementById('adsFilterOptionsList');
    if (!optionsList) return;
    
    optionsList.innerHTML = ADS_FILTER_FIELDS.map(field => {
        const values = getUniqueFilterValues(field.id);
        if (values.length === 0) return '';
        
        return `
            <div class="filter-option" onclick="event.stopPropagation(); event.preventDefault(); openAdsFilterValueDialog('${field.id}')">
                <div class="filter-option-icon">${field.icon}</div>
                <div class="filter-option-text">${field.label}</div>
            </div>
        `;
    }).join('') || '<div class="filter-dropdown-empty">No filter options available</div>';
}

/**
 * Open filter value dialog - creates inline dropdown
 * @param {string} fieldId - Field ID to open
 * @param {Function} getUniqueFilterValues - Function to get unique values
 * @param {Function} onFilterChange - Callback when filter changes
 */
export function openAdsFilterValueDialog(fieldId, getUniqueFilterValues, onFilterChange) {
    const field = ADS_FILTER_FIELDS.find(f => f.id === fieldId);
    if (!field) return;
    
    const mainDropdown = document.getElementById('adsFilterDropdown');
    if (mainDropdown) mainDropdown.classList.remove('active');
    
    const existingDropdown = document.getElementById(`ads-inline-filter-${fieldId}`);
    if (existingDropdown) {
        toggleExistingDropdown(existingDropdown, fieldId);
        return;
    }
    
    createInlineFilterDropdown(fieldId, field, getUniqueFilterValues, onFilterChange);
}

/**
 * Toggle existing dropdown open/closed
 */
function toggleExistingDropdown(dropdown, fieldId) {
    const header = dropdown.querySelector('.inline-filter-header');
    const options = dropdown.querySelector('.inline-filter-options');
    if (header && options) {
        header.classList.toggle('open');
        options.classList.toggle('open');
        options.style.display = options.classList.contains('open') ? 'block' : 'none';
        updateAdsInlineFilterOptions(fieldId);
    }
}

/**
 * Create a new inline filter dropdown
 */
function createInlineFilterDropdown(fieldId, field, getUniqueFilterValues, onFilterChange) {
    const values = getUniqueFilterValues(fieldId);
    const filters = getAdsFilters();
    
    const filterChipsContainer = document.getElementById('adsFilterChips');
    if (!filterChipsContainer) return;
    
    const inlineFilter = document.createElement('div');
    inlineFilter.className = 'inline-filter-dropdown';
    inlineFilter.id = `ads-inline-filter-${fieldId}`;
    
    const optionsHTML = values.map(value => {
        const isSelected = filters.some(f => f.field === fieldId && f.value === value);
        const escapedValue = escapeHtml(value);
        const attrValue = escapeHtmlForAttribute(value);
        return `
            <div class="inline-filter-option ${isSelected ? 'selected' : ''}" 
                 data-filter-value="${escapedValue}"
                 onclick="event.stopPropagation(); toggleAdsInlineFilterValue('${fieldId}', '${attrValue}')">
                <input type="checkbox" class="inline-filter-checkbox" ${isSelected ? 'checked' : ''} 
                       data-filter-value="${escapedValue}"
                       onclick="event.stopPropagation()" 
                       onchange="event.stopPropagation(); toggleAdsInlineFilterValue('${fieldId}', '${attrValue}')">
                <span>${escapedValue || '(empty)'}</span>
            </div>
        `;
    }).join('');
    
    inlineFilter.innerHTML = `
        <div class="inline-filter-header open" onclick="toggleAdsInlineFilterDropdown('${fieldId}', event)">
            <span class="inline-filter-icon">${field.icon}</span>
            <span class="inline-filter-label">${field.label}</span>
            <span class="inline-filter-chevron">▼</span>
        </div>
        <div class="inline-filter-options open" style="display: block;">
            ${optionsHTML}
        </div>
        <div class="inline-filter-remove" onclick="event.stopPropagation(); removeAdsInlineFilter('${fieldId}')" title="Remove filter">×</div>
    `;
    
    filterChipsContainer.appendChild(inlineFilter);
    setTimeout(() => updateAdsInlineFilterHeader(fieldId), 0);
}

/**
 * Toggle inline filter dropdown open/closed
 */
export function toggleAdsInlineFilterDropdown(fieldId, e) {
    if (e) e.stopPropagation();
    
    const dropdown = document.getElementById(`ads-inline-filter-${fieldId}`);
    if (!dropdown) return;
    
    const header = dropdown.querySelector('.inline-filter-header');
    const options = dropdown.querySelector('.inline-filter-options');
    
    if (header && options) {
        const isOpen = options.classList.contains('open');
        header.classList.toggle('open', !isOpen);
        options.classList.toggle('open', !isOpen);
        options.style.display = isOpen ? 'none' : 'block';
    }
}

/**
 * Toggle a filter value on/off
 * @param {string} fieldId - Field ID
 * @param {string} value - Value to toggle
 * @param {Function} onFilterChange - Callback when filter changes
 */
export function toggleAdsInlineFilterValue(fieldId, value, onFilterChange) {
    const filters = getAdsFilters();
    const existingIndex = filters.findIndex(f => f.field === fieldId && f.value === value);
    
    if (existingIndex >= 0) {
        removeAdsFilter(fieldId, value);
    } else {
        addAdsFilter(fieldId, value);
    }
    
    updateAdsInlineFilterOptions(fieldId);
    if (onFilterChange) onFilterChange();
}

/**
 * Update inline filter options checkbox states
 */
export function updateAdsInlineFilterOptions(fieldId) {
    const dropdown = document.getElementById(`ads-inline-filter-${fieldId}`);
    if (!dropdown) return;
    
    const options = dropdown.querySelectorAll('.inline-filter-option');
    const filters = getAdsFilters();
    
    options.forEach(option => {
        const checkbox = option.querySelector('.inline-filter-checkbox');
        const value = option.getAttribute('data-filter-value') || checkbox?.getAttribute('data-filter-value');
        if (!value) return;
        
        const isSelected = filters.some(f => f.field === fieldId && f.value === value);
        checkbox.checked = isSelected;
        option.classList.toggle('selected', isSelected);
    });
    
    updateAdsInlineFilterHeader(fieldId);
}

/**
 * Update inline filter header label
 */
export function updateAdsInlineFilterHeader(fieldId) {
    const dropdown = document.getElementById(`ads-inline-filter-${fieldId}`);
    if (!dropdown) return;
    
    const labelElement = dropdown.querySelector('.inline-filter-label');
    if (!labelElement) return;
    
    const field = ADS_FILTER_FIELDS.find(f => f.id === fieldId);
    const filters = getAdsFilters();
    const activeFilters = filters.filter(f => f.field === fieldId);
    
    if (activeFilters.length === 0) {
        labelElement.textContent = field ? field.label : fieldId;
    } else if (activeFilters.length === 1) {
        labelElement.textContent = activeFilters[0].value;
    } else {
        const firstValue = activeFilters[0].value;
        const displayValue = firstValue.length > 15 ? firstValue.substring(0, 15) + '...' : firstValue;
        labelElement.textContent = `${displayValue} + ${activeFilters.length - 1} more`;
    }
}

/**
 * Remove inline filter and clear all values for that field
 * @param {string} fieldId - Field ID to remove
 * @param {Function} onFilterChange - Callback when filter changes
 */
export function removeAdsInlineFilter(fieldId, onFilterChange) {
    const filters = getAdsFilters();
    const remaining = filters.filter(f => f.field !== fieldId);
    
    clearAdsFilters();
    remaining.forEach(f => addAdsFilter(f.field, f.value));
    
    const dropdown = document.getElementById(`ads-inline-filter-${fieldId}`);
    if (dropdown) dropdown.remove();
    
    if (onFilterChange) onFilterChange();
}

/**
 * Update filter badge count
 */
export function updateAdsFilterBadge() {
    const badge = document.getElementById('adsFilterBadge');
    if (!badge) return;
    
    const filters = getAdsFilters();
    badge.textContent = filters.length > 0 ? filters.length : '';
    badge.style.display = filters.length > 0 ? 'flex' : 'none';
}
