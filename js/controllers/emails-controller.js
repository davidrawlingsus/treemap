/**
 * Emails Controller Module
 * Page-level orchestration for Emails tab: loading, filtering, sorting, search.
 * Follows controller pattern - coordinates between state, services, and renderers.
 * Mirrors the structure of ads-controller.js for consistency.
 */

import { fetchSavedEmails } from '/js/services/api-emails.js';
import { 
    getEmailsCache, setEmailsCache, setEmailsLoading, setEmailsError, 
    getEmailsCurrentClientId, setEmailsCurrentClientId,
    getEmailsSearchTerm, setEmailsSearchTerm,
    getEmailsFilters, getEmailsSortOrder, setEmailsSortOrder
} from '/js/state/emails-state.js';
import { renderEmailsGrid, showLoading, renderError } from '/js/renderers/emails-renderer.js';
import {
    populateEmailsFilterOptions,
    openEmailsFilterValueDialog as filterUIOpenDialog,
    toggleEmailsInlineFilterDropdown as filterUIToggleDropdown,
    toggleEmailsInlineFilterValue as filterUIToggleValue,
    removeEmailsInlineFilter as filterUIRemoveInline,
    updateEmailsFilterBadge,
    EMAIL_STATUS_OPTIONS,
    normalizeStatus
} from '/js/controllers/emails-filter-ui.js';

// ============ Page Initialization ============

/**
 * Initialize the Emails page - load and render emails
 */
export async function initEmailsPage() {
    const container = document.getElementById('emailsGrid');
    if (!container) {
        console.error('[EmailsController] emailsGrid container not found');
        return;
    }
    
    const clientId = window.appStateGet?.('currentClientId') || 
                     document.getElementById('clientSelect')?.value;
    
    if (!clientId) {
        container.innerHTML = `
            <div class="emails-empty">
                <div class="emails-empty__icon">📧</div>
                <h3 class="emails-empty__title">No client selected</h3>
                <p class="emails-empty__text">Please select a client first</p>
            </div>
        `;
        return;
    }
    
    const cachedClientId = getEmailsCurrentClientId();
    const cachedEmails = getEmailsCache();
    
    if (cachedClientId === clientId && cachedEmails.length > 0) {
        renderEmailsPage();
        return;
    }
    
    showLoading(container);
    setEmailsLoading(true);
    setEmailsError(null);
    
    try {
        const response = await fetchSavedEmails(clientId);
        const emails = response.items || [];
        
        setEmailsCache(emails);
        setEmailsCurrentClientId(clientId);
        setEmailsLoading(false);
        
        populateEmailsFilterOptions(getUniqueFilterValues);
        renderEmailsPage();
    } catch (error) {
        console.error('[EmailsController] Failed to load emails:', error);
        setEmailsLoading(false);
        setEmailsError(error.message);
        renderError(container, error.message);
    }
}

/**
 * Render the emails page with current filters, search, and sort applied
 */
export function renderEmailsPage() {
    const container = document.getElementById('emailsGrid');
    if (!container) return;
    
    const emails = getEmailsCache();
    const filteredEmails = getFilteredAndSortedEmails(emails);
    
    updateEmailsFilterBadge();
    updateEmailsSortUI();
    
    renderEmailsGrid(container, filteredEmails);
}

// ============ Filtering & Sorting Logic ============

/**
 * Get filtered and sorted emails based on current state
 */
function getFilteredAndSortedEmails(emails) {
    let filtered = [...emails];
    const searchTerm = getEmailsSearchTerm();
    const filters = getEmailsFilters();
    const sortOrder = getEmailsSortOrder();
    
    // Apply search filter
    if (searchTerm) {
        const term = searchTerm.toLowerCase();
        filtered = filtered.filter(email =>
            email.subject_line?.toLowerCase().includes(term) ||
            email.preview_text?.toLowerCase().includes(term) ||
            email.headline?.toLowerCase().includes(term) ||
            email.body_text?.toLowerCase().includes(term) ||
            email.from_name?.toLowerCase().includes(term)
        );
    }
    
    // Apply field filters
    filters.forEach(filter => {
        filtered = filtered.filter(email => {
            if (filter.field === 'status') {
                const emailStatus = normalizeStatus(email.status);
                return emailStatus === filter.value.toLowerCase();
            }
            if (filter.field === 'email_type') {
                // Match by label or id
                const emailType = email.email_type?.toLowerCase();
                const filterValue = filter.value.toLowerCase();
                // Handle matching by display label
                const typeMap = {
                    'post-purchase onboarding': 'post_purchase_onboarding',
                    'cart abandonment': 'cart_abandonment',
                    'replenishment reminder': 'replenishment_reminder',
                    'browse abandonment': 'browse_abandonment'
                };
                const mappedValue = typeMap[filterValue] || filterValue;
                return emailType === mappedValue || emailType === filterValue;
            }
            // Other fields
            const value = email[filter.field];
            if (!value) return false;
            return value.toLowerCase() === filter.value.toLowerCase();
        });
    });
    
    // Apply sort
    filtered.sort((a, b) => {
        const dateA = new Date(a.created_at);
        const dateB = new Date(b.created_at);
        return sortOrder === 'desc' ? dateB - dateA : dateA - dateB;
    });
    
    return filtered;
}

/**
 * Extract unique values for a field from all emails
 */
function getUniqueFilterValues(field) {
    const emails = getEmailsCache();
    
    // Status is a special case - return all possible status values
    if (field === 'status') {
        return EMAIL_STATUS_OPTIONS.map(s => s.label);
    }
    
    // Other fields come from email objects directly
    const values = new Set();
    emails.forEach(email => {
        const value = email[field];
        if (value && typeof value === 'string' && value.trim()) {
            values.add(value.trim());
        }
    });
    
    return Array.from(values).sort();
}

// ============ Sort UI ============

function updateEmailsSortUI() {
    const sortLabel = document.getElementById('emailsSortLabel');
    const sortCheckDesc = document.getElementById('emailsSortCheckDesc');
    const sortCheckAsc = document.getElementById('emailsSortCheckAsc');
    const sortOrder = getEmailsSortOrder();
    
    if (sortLabel) sortLabel.textContent = sortOrder === 'desc' ? 'Newest first' : 'Oldest first';
    if (sortCheckDesc) sortCheckDesc.textContent = sortOrder === 'desc' ? '✓' : '';
    if (sortCheckAsc) sortCheckAsc.textContent = sortOrder === 'asc' ? '✓' : '';
}

// ============ Event Handlers ============

function handleEmailsSearch() {
    const searchInput = document.getElementById('emailsSearchInput');
    setEmailsSearchTerm(searchInput?.value.trim() || '');
    updateEmailsSearchClearButton();
    renderEmailsPage();
}

function clearEmailsSearch() {
    const searchInput = document.getElementById('emailsSearchInput');
    if (searchInput) searchInput.value = '';
    setEmailsSearchTerm('');
    updateEmailsSearchClearButton();
    renderEmailsPage();
}

function updateEmailsSearchClearButton() {
    const searchInput = document.getElementById('emailsSearchInput');
    const clearBtn = document.getElementById('emailsSearchClear');
    if (searchInput && clearBtn) {
        clearBtn.style.display = searchInput.value ? 'flex' : 'none';
    }
}

function toggleEmailsFilterMenu(event) {
    event?.stopPropagation();
    const dropdown = document.getElementById('emailsFilterDropdown');
    if (!dropdown) return;
    
    closeEmailsSortMenu();
    
    if (dropdown.classList.contains('active')) {
        dropdown.classList.remove('active');
    } else {
        dropdown.classList.add('active');
        populateEmailsFilterOptions(getUniqueFilterValues);
    }
}

function filterEmailsFilterOptions() {
    const searchInput = document.getElementById('emailsFilterSearchInput');
    const term = searchInput?.value.toLowerCase() || '';
    const options = document.querySelectorAll('#emailsFilterOptionsList .filter-option');
    
    options.forEach(option => {
        option.style.display = option.textContent.toLowerCase().includes(term) ? 'flex' : 'none';
    });
}

function toggleEmailsSortMenu(event) {
    event?.stopPropagation();
    const dropdown = document.getElementById('emailsSortDropdown');
    if (!dropdown) return;
    
    const filterDropdown = document.getElementById('emailsFilterDropdown');
    if (filterDropdown) filterDropdown.classList.remove('active');
    
    dropdown.classList.toggle('active');
}

function closeEmailsSortMenu() {
    const dropdown = document.getElementById('emailsSortDropdown');
    if (dropdown) dropdown.classList.remove('active');
}

function setEmailsSortOrderAndRender(order) {
    setEmailsSortOrder(order);
    closeEmailsSortMenu();
    renderEmailsPage();
}

// Filter UI wrappers that pass dependencies
function openEmailsFilterValueDialog(fieldId) {
    filterUIOpenDialog(fieldId, getUniqueFilterValues, handleFilterChange);
}

function toggleEmailsInlineFilterDropdown(fieldId, e) {
    filterUIToggleDropdown(fieldId, e);
}

function toggleEmailsInlineFilterValue(fieldId, value) {
    filterUIToggleValue(fieldId, value, handleFilterChange);
}

function removeEmailsInlineFilter(fieldId) {
    filterUIRemoveInline(fieldId, handleFilterChange);
}

function handleFilterChange() {
    updateEmailsFilterBadge();
    renderEmailsPage();
}

// Close dropdowns when clicking outside
document.addEventListener('click', (e) => {
    const filterDropdown = document.getElementById('emailsFilterDropdown');
    const filterBtn = document.getElementById('emailsFilterMenuBtn');
    const sortDropdown = document.getElementById('emailsSortDropdown');
    const sortBtn = document.getElementById('emailsSortMenuBtn');
    
    if (filterDropdown?.classList.contains('active')) {
        if (!filterDropdown.contains(e.target) && !filterBtn?.contains(e.target)) {
            filterDropdown.classList.remove('active');
        }
    }
    
    if (sortDropdown?.classList.contains('active')) {
        if (!sortDropdown.contains(e.target) && !sortBtn?.contains(e.target)) {
            sortDropdown.classList.remove('active');
        }
    }
});

// ============ Global Exports ============

window.initEmailsPage = initEmailsPage;
window.renderEmailsPage = renderEmailsPage;
window.handleEmailsSearch = handleEmailsSearch;
window.clearEmailsSearch = clearEmailsSearch;
window.updateEmailsSearchClearButton = updateEmailsSearchClearButton;
window.toggleEmailsFilterMenu = toggleEmailsFilterMenu;
window.filterEmailsFilterOptions = filterEmailsFilterOptions;
window.toggleEmailsSortMenu = toggleEmailsSortMenu;
window.setEmailsSortOrder = setEmailsSortOrderAndRender;
window.openEmailsFilterValueDialog = openEmailsFilterValueDialog;
window.toggleEmailsInlineFilterDropdown = toggleEmailsInlineFilterDropdown;
window.toggleEmailsInlineFilterValue = toggleEmailsInlineFilterValue;
window.removeEmailsInlineFilter = removeEmailsInlineFilter;
