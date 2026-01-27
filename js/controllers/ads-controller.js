/**
 * Ads Controller Module
 * Page-level orchestration for Ads tab: loading, filtering, sorting, search.
 * Follows controller pattern - coordinates between state, services, and renderers.
 */

import { fetchFacebookAds } from '/js/services/api-facebook-ads.js';
import { 
    getAdsCache, setAdsCache, setAdsLoading, setAdsError, 
    getAdsCurrentClientId, setAdsCurrentClientId,
    getAdsSearchTerm, setAdsSearchTerm,
    getAdsFilters, getAdsSortOrder, setAdsSortOrder,
    getAdsViewMode, setAdsViewMode as stateSetViewMode
} from '/js/state/ads-state.js';
import { renderAdsGrid, showLoading, renderError } from '/js/renderers/ads-renderer.js';
import { renderAdsKanban } from '/js/renderers/ads-kanban-renderer.js';
import {
    populateAdsFilterOptions,
    openAdsFilterValueDialog as filterUIOpenDialog,
    toggleAdsInlineFilterDropdown as filterUIToggleDropdown,
    toggleAdsInlineFilterValue as filterUIToggleValue,
    removeAdsInlineFilter as filterUIRemoveInline,
    updateAdsFilterBadge,
    AD_STATUS_OPTIONS,
    normalizeStatus
} from '/js/controllers/ads-filter-ui.js';

// ============ Page Initialization ============

/**
 * Initialize the Ads page - load and render ads
 */
export async function initAdsPage() {
    const container = document.getElementById('adsGrid');
    if (!container) {
        console.error('[AdsController] adsGrid container not found');
        return;
    }
    
    const clientId = window.appStateGet?.('currentClientId') || 
                     document.getElementById('clientSelect')?.value;
    
    if (!clientId) {
        container.innerHTML = `
            <div class="ads-empty">
                <div class="ads-empty__icon">📢</div>
                <h3 class="ads-empty__title">No client selected</h3>
                <p class="ads-empty__text">Please select a client first</p>
            </div>
        `;
        return;
    }
    
    const cachedClientId = getAdsCurrentClientId();
    const cachedAds = getAdsCache();
    
    if (cachedClientId === clientId && cachedAds.length > 0) {
        renderAdsPage();
        return;
    }
    
    showLoading(container);
    setAdsLoading(true);
    setAdsError(null);
    
    try {
        const response = await fetchFacebookAds(clientId);
        const ads = response.items || [];
        
        setAdsCache(ads);
        setAdsCurrentClientId(clientId);
        setAdsLoading(false);
        
        populateAdsFilterOptions(getUniqueFilterValues);
        renderAdsPage();
    } catch (error) {
        console.error('[AdsController] Failed to load ads:', error);
        setAdsLoading(false);
        setAdsError(error.message);
        renderError(container, error.message);
    }
}

/**
 * Render the ads page with current filters, search, and sort applied
 */
export function renderAdsPage() {
    const container = document.getElementById('adsGrid');
    if (!container) return;
    
    const ads = getAdsCache();
    const filteredAds = getFilteredAndSortedAds(ads);
    const viewMode = getAdsViewMode();
    
    updateAdsFilterBadge();
    updateAdsSortUI();
    updateViewToggleUI();
    
    // Render based on view mode
    if (viewMode === 'kanban') {
        renderAdsKanban(container, filteredAds);
    } else {
        renderAdsGrid(container, filteredAds);
    }
}

// ============ Filtering & Sorting Logic ============

/**
 * Get filtered and sorted ads based on current state
 */
function getFilteredAndSortedAds(ads) {
    let filtered = [...ads];
    const searchTerm = getAdsSearchTerm();
    const filters = getAdsFilters();
    const sortOrder = getAdsSortOrder();
    
    if (searchTerm) {
        const term = searchTerm.toLowerCase();
        filtered = filtered.filter(ad =>
            ad.headline?.toLowerCase().includes(term) ||
            ad.primary_text?.toLowerCase().includes(term) ||
            ad.description?.toLowerCase().includes(term) ||
            ad.full_json?.title?.toLowerCase().includes(term)
        );
    }
    
    filters.forEach(filter => {
        filtered = filtered.filter(ad => {
            // Status is on the ad object, not in full_json
            if (filter.field === 'status') {
                const adStatus = normalizeStatus(ad.status);
                return adStatus === filter.value.toLowerCase();
            }
            // Other fields are in full_json
            const value = ad.full_json?.[filter.field];
            if (!value) return false;
            return value.toLowerCase() === filter.value.toLowerCase();
        });
    });
    
    filtered.sort((a, b) => {
        const dateA = new Date(a.created_at);
        const dateB = new Date(b.created_at);
        return sortOrder === 'desc' ? dateB - dateA : dateA - dateB;
    });
    
    return filtered;
}

/**
 * Extract unique values for a field from all ads
 */
function getUniqueFilterValues(field) {
    const ads = getAdsCache();
    
    // Status is a special case - return all possible status values
    if (field === 'status') {
        return AD_STATUS_OPTIONS.map(s => s.label);
    }
    
    // Other fields come from full_json
    const values = new Set();
    ads.forEach(ad => {
        const value = ad.full_json?.[field];
        if (value && typeof value === 'string' && value.trim()) {
            values.add(value.trim());
        }
    });
    
    return Array.from(values).sort();
}

// ============ Sort UI ============

function updateAdsSortUI() {
    const sortLabel = document.getElementById('adsSortLabel');
    const sortCheckDesc = document.getElementById('adsSortCheckDesc');
    const sortCheckAsc = document.getElementById('adsSortCheckAsc');
    const sortOrder = getAdsSortOrder();
    
    if (sortLabel) sortLabel.textContent = sortOrder === 'desc' ? 'Newest first' : 'Oldest first';
    if (sortCheckDesc) sortCheckDesc.textContent = sortOrder === 'desc' ? '✓' : '';
    if (sortCheckAsc) sortCheckAsc.textContent = sortOrder === 'asc' ? '✓' : '';
}

// ============ View Toggle ============

function updateViewToggleUI() {
    const viewMode = getAdsViewMode();
    const buttons = document.querySelectorAll('.ads-view-toggle__btn');
    
    buttons.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.view === viewMode);
    });
}

function setAdsViewMode(mode) {
    stateSetViewMode(mode);
    renderAdsPage();
}

// ============ Event Handlers ============

function handleAdsSearch() {
    const searchInput = document.getElementById('adsSearchInput');
    setAdsSearchTerm(searchInput?.value.trim() || '');
    updateAdsSearchClearButton();
    renderAdsPage();
}

function clearAdsSearch() {
    const searchInput = document.getElementById('adsSearchInput');
    if (searchInput) searchInput.value = '';
    setAdsSearchTerm('');
    updateAdsSearchClearButton();
    renderAdsPage();
}

function updateAdsSearchClearButton() {
    const searchInput = document.getElementById('adsSearchInput');
    const clearBtn = document.getElementById('adsSearchClear');
    if (searchInput && clearBtn) {
        clearBtn.style.display = searchInput.value ? 'flex' : 'none';
    }
}

function toggleAdsFilterMenu(event) {
    event?.stopPropagation();
    const dropdown = document.getElementById('adsFilterDropdown');
    if (!dropdown) return;
    
    closeAdsSortMenu();
    
    if (dropdown.classList.contains('active')) {
        dropdown.classList.remove('active');
    } else {
        dropdown.classList.add('active');
        populateAdsFilterOptions(getUniqueFilterValues);
    }
}

function filterAdsFilterOptions() {
    const searchInput = document.getElementById('adsFilterSearchInput');
    const term = searchInput?.value.toLowerCase() || '';
    const options = document.querySelectorAll('#adsFilterOptionsList .filter-option');
    
    options.forEach(option => {
        option.style.display = option.textContent.toLowerCase().includes(term) ? 'flex' : 'none';
    });
}

function toggleAdsSortMenu(event) {
    event?.stopPropagation();
    const dropdown = document.getElementById('adsSortDropdown');
    if (!dropdown) return;
    
    const filterDropdown = document.getElementById('adsFilterDropdown');
    if (filterDropdown) filterDropdown.classList.remove('active');
    
    dropdown.classList.toggle('active');
}

function closeAdsSortMenu() {
    const dropdown = document.getElementById('adsSortDropdown');
    if (dropdown) dropdown.classList.remove('active');
}

function setAdsSortOrderAndRender(order) {
    setAdsSortOrder(order);
    closeAdsSortMenu();
    renderAdsPage();
}

// Filter UI wrappers that pass dependencies
function openAdsFilterValueDialog(fieldId) {
    filterUIOpenDialog(fieldId, getUniqueFilterValues, handleFilterChange);
}

function toggleAdsInlineFilterDropdown(fieldId, e) {
    filterUIToggleDropdown(fieldId, e);
}

function toggleAdsInlineFilterValue(fieldId, value) {
    filterUIToggleValue(fieldId, value, handleFilterChange);
}

function removeAdsInlineFilter(fieldId) {
    filterUIRemoveInline(fieldId, handleFilterChange);
}

function handleFilterChange() {
    updateAdsFilterBadge();
    renderAdsPage();
}

// Close dropdowns when clicking outside
document.addEventListener('click', (e) => {
    const filterDropdown = document.getElementById('adsFilterDropdown');
    const filterBtn = document.getElementById('adsFilterMenuBtn');
    const sortDropdown = document.getElementById('adsSortDropdown');
    const sortBtn = document.getElementById('adsSortMenuBtn');
    
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

window.initAdsPage = initAdsPage;
window.renderAdsPage = renderAdsPage;
window.handleAdsSearch = handleAdsSearch;
window.clearAdsSearch = clearAdsSearch;
window.updateAdsSearchClearButton = updateAdsSearchClearButton;
window.toggleAdsFilterMenu = toggleAdsFilterMenu;
window.filterAdsFilterOptions = filterAdsFilterOptions;
window.toggleAdsSortMenu = toggleAdsSortMenu;
window.setAdsSortOrder = setAdsSortOrderAndRender;
window.openAdsFilterValueDialog = openAdsFilterValueDialog;
window.toggleAdsInlineFilterDropdown = toggleAdsInlineFilterDropdown;
window.toggleAdsInlineFilterValue = toggleAdsInlineFilterValue;
window.removeAdsInlineFilter = removeAdsInlineFilter;
window.setAdsViewMode = setAdsViewMode;
