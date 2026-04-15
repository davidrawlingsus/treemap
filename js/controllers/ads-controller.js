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
    getAdsViewMode, setAdsViewMode as stateSetViewMode,
    getAdsSource, setAdsSource as stateSetAdsSource,
    getSelectedAdIds, clearAdsSelection
} from '/js/state/ads-state.js';
import { renderAdsGrid, showLoading, renderError, updateBulkPublishButton } from '/js/renderers/ads-renderer.js';
import { renderAdsKanban } from '/js/renderers/ads-kanban-renderer.js';
import { showMetaPublishModal } from '/js/renderers/meta-publish-modal.js';
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
    if (typeof window.updateLeadAdsToggle === 'function') window.updateLeadAdsToggle();
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
    
    const source = getAdsSource();
    const cachedClientId = getAdsCurrentClientId();
    const cachedAds = getAdsCache();

    // Use a cache key that includes the source so switching triggers a re-fetch
    const cacheKey = `${clientId}:${source}`;
    if (cachedClientId === cacheKey && cachedAds.length > 0) {
        renderAdsPage();
        return;
    }

    showLoading(container);
    setAdsLoading(true);
    setAdsError(null);

    try {
        let ads = [];
        if (source === 'current') {
            ads = await fetchCurrentAds(clientId);
        } else {
            const response = await fetchFacebookAds(clientId);
            ads = response.items || [];
        }
        setAdsCache(ads);
        setAdsCurrentClientId(cacheKey);
        setAdsLoading(false);

        if (source === 'test') {
            populateAdsFilterOptions(getUniqueFilterValues);
        }
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
    const source = getAdsSource();
    const filteredAds = getFilteredAndSortedAds(ads);
    const viewMode = getAdsViewMode();
    updateSourceToggleUI();
    updateControlBarForSource();
    updateAdsSortUI();

    if (source === 'test') {
        updateAdsFilterBadge();
        updateViewToggleUI();
    }

    // Render based on view mode (current ads always grid)
    if (source === 'test' && viewMode === 'kanban') {
        renderAdsKanban(container, filteredAds);
    } else {
        renderAdsGrid(container, filteredAds);
    }
    if (source === 'test') updateBulkPublishButton();
}

/**
 * Handle bulk publish - open modal with selected ads
 */
export function handleAdsBulkPublish() {
    const selectedIds = Array.from(getSelectedAdIds());
    if (selectedIds.length === 0) return;
    const ads = getAdsCache().filter(a => selectedIds.includes(a.id));
    if (ads.length === 0) return;
    showMetaPublishModal(selectedIds, ads);
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
            ad.cta?.toLowerCase().includes(term) ||
            ad.page_name?.toLowerCase().includes(term) ||
            ad.full_json?.title?.toLowerCase().includes(term)
        );
    }

    // Only apply filters for test ads (current ads don't have angle/funnel)
    if (getAdsSource() === 'test') {
        filters.forEach(filter => {
            filtered = filtered.filter(ad => {
                if (filter.field === 'status') {
                    const adStatus = normalizeStatus(ad.status);
                    return adStatus === filter.value.toLowerCase();
                }
                let value = ad.full_json?.[filter.field];
                if (!value && filter.field === 'angle') {
                    value = ad.full_json?.testType;
                }
                if (!value) return false;
                return value.toLowerCase() === filter.value.toLowerCase();
            });
        });
    }

    filtered.sort((a, b) => {
        // Use created_at for test ads, started_running_on for current ads
        const dateField = getAdsSource() === 'current' ? 'started_running_on' : 'created_at';
        const dateA = new Date(a[dateField] || a.created_at || 0);
        const dateB = new Date(b[dateField] || b.created_at || 0);
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
        // For 'angle', also check legacy 'testType' key for pre-migration data
        let value = ad.full_json?.[field];
        if (!value && field === 'angle') {
            value = ad.full_json?.testType;
        }
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

// ============ Source Toggle ============

async function fetchCurrentAds(clientId) {
    const apiBase = window.APP_CONFIG?.API_BASE_URL || 'http://localhost:8000';
    const headers = window.Auth?.getAuthHeaders?.() || {};

    // Get imports list
    const importsRes = await fetch(`${apiBase}/api/clients/${clientId}/ad-library-imports`, { headers });
    if (!importsRes.ok) throw new Error('Failed to load ad library imports');
    const importsData = await importsRes.json();
    const imports = importsData.items || [];
    if (!imports.length) return [];

    // Get latest import with full ads
    const latestId = imports[0].id;
    const detailRes = await fetch(`${apiBase}/api/clients/${clientId}/ad-library-imports/${latestId}`, { headers });
    if (!detailRes.ok) throw new Error('Failed to load import details');
    const detail = await detailRes.json();

    // Store import-level analysis for the renderer
    window._currentImportAnalysis = {
        synthesisText: detail.synthesis_text || null,
        signalText: detail.signal_text || null,
        adCopyScore: detail.ad_copy_score || null,
        signalScore: detail.signal_score || null,
        opportunityScore: detail.opportunity_score || null,
    };

    return detail.ads || [];
}

function switchAdsSource(source) {
    stateSetAdsSource(source);
    setAdsCache([]);
    setAdsCurrentClientId(null);
    updateSourceToggleUI();
    updateControlBarForSource();
    initAdsPage();
}

function updateSourceToggleUI() {
    const source = getAdsSource();
    document.querySelectorAll('.ads-source-toggle__btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.source === source);
    });
}

function updateControlBarForSource() {
    const source = getAdsSource();
    const isCurrent = source === 'current';

    // Hide controls that don't apply to current ads
    const hideSelectors = [
        '#adsFilterChips',
        '#adsFilterMenuBtn',
        '#adsBulkPublishBtn',
        '.ads-find-replace-button',
        '#adsViewToggle',
    ];
    hideSelectors.forEach(sel => {
        const el = document.querySelector(sel);
        if (el) el.style.display = isCurrent ? 'none' : '';
    });

    // Update heading
    const heading = document.querySelector('#ads-section .control-bar h1');
    if (heading) heading.textContent = isCurrent ? 'Current Ads' : 'Saved Ads';
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
window.switchAdsSource = switchAdsSource;
