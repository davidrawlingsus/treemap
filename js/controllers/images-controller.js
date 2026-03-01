/**
 * Images Controller Module
 * Page-level orchestration for Images tab: loading, rendering.
 * Follows controller pattern - coordinates between state, services, and renderers.
 */

import { fetchAdImages, uploadAdImage } from '/js/services/api-ad-images.js';
import { 
    getImagesCache, setImagesCache, setImagesLoading, setImagesError, 
    getImagesCurrentClientId, setImagesCurrentClientId,
    getImagesColumnCount, setImagesColumnCount,
    getImagesSortBy, setImagesSortBy,
    getImagesTotal, setImagesTotal,
    getImagesMediaTypeFilter, setImagesMediaTypeFilter,
    getImagesViewMode, setImagesViewMode as setImagesViewModeState,
    getImagesMetricFilters, setImagesMetricFilters,
    getImagesTableColumns, setImagesTableColumns,
    getImagesHideDuplicates, setImagesHideDuplicates,
    addImageToCache
} from '/js/state/images-state.js';
import { renderImagesGrid, showLoading, renderError, relayoutImagesGrid, cancelScheduledLayoutFromImageLoad, updateBulkDeleteButton } from '/js/renderers/images-renderer.js';
import { renderImagesTable } from '/js/renderers/images-table-renderer.js';
import { debounce } from '/js/utils/dom.js';

// ============ Sort Initialization ============

let sortInitialized = false;

/**
 * Sort images by the selected criteria
 * @param {Array} images - Array of image objects
 * @param {string} sortBy - Sort criteria
 * @returns {Array} Sorted images
 */
function sortImages(images, sortBy) {
    const sorted = [...images];
    
    switch (sortBy) {
        case 'newest':
            // Sort by uploaded_at descending (newest first). API returns uploaded_at, not created_at.
            sorted.sort((a, b) => {
                const dateA = new Date(a.uploaded_at || a.created_at || 0);
                const dateB = new Date(b.uploaded_at || b.created_at || 0);
                return dateB - dateA;
            });
            break;
        case 'oldest':
            // Sort by uploaded_at ascending (oldest first). API returns uploaded_at, not created_at.
            sorted.sort((a, b) => {
                const dateA = new Date(a.uploaded_at || a.created_at || 0);
                const dateB = new Date(b.uploaded_at || b.created_at || 0);
                return dateA - dateB;
            });
            break;
        case 'running_longest':
            // Sort by started_running_on ascending (oldest running first)
            // Items without started_running_on go to the end
            sorted.sort((a, b) => {
                const dateA = a.started_running_on ? new Date(a.started_running_on) : null;
                const dateB = b.started_running_on ? new Date(b.started_running_on) : null;
                if (dateA && dateB) return dateA - dateB;
                if (dateA) return -1; // a has date, b doesn't
                if (dateB) return 1;  // b has date, a doesn't
                return 0; // neither has date
            });
            break;
        case 'running_newest':
            // Sort by started_running_on descending (most recent running first)
            // Items without started_running_on go to the end
            sorted.sort((a, b) => {
                const dateA = a.started_running_on ? new Date(a.started_running_on) : null;
                const dateB = b.started_running_on ? new Date(b.started_running_on) : null;
                if (dateA && dateB) return dateB - dateA;
                if (dateA) return -1;
                if (dateB) return 1;
                return 0;
            });
            break;
        default:
            // No sorting
            break;
    }
    
    return sorted;
}

/**
 * Initialize the sort dropdown
 */
function initSortDropdown() {
    if (sortInitialized) {
        return;
    }
    
    const dropdown = document.getElementById('imagesSortDropdown');
    const sortOptions = document.querySelectorAll('.images-sort-option');
    
    if (!dropdown || !sortOptions.length) {
        console.warn('[ImagesController] Sort dropdown not found');
        return;
    }
    
    // Restore saved sort preference and update checkmarks
    const savedSort = getImagesSortBy();
    updateSortCheckmarks(savedSort);
    
    // Handle sort option clicks
    sortOptions.forEach(option => {
        option.addEventListener('click', () => {
            const sortBy = option.dataset.sort;
            setImagesSortBy(sortBy);
            updateSortCheckmarks(sortBy);
            closeSortDropdown();
            setImagesCache([]);
            setImagesTotal(0);
            loadFirstPage();
        });
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        const container = document.querySelector('.images-sort-menu-container');
        if (container && !container.contains(e.target)) {
            closeSortDropdown();
        }
        const filterContainer = document.querySelector('.images-filter-menu-container');
        if (filterContainer && !filterContainer.contains(e.target)) {
            closeFilterDropdown();
        }
    });
    
    sortInitialized = true;
}

/**
 * Update checkmarks on sort options
 */
function updateSortCheckmarks(selectedSort) {
    document.getElementById('sortCheckNewest').textContent = selectedSort === 'newest' ? '✓' : '';
    document.getElementById('sortCheckOldest').textContent = selectedSort === 'oldest' ? '✓' : '';
    document.getElementById('sortCheckRunningLongest').textContent = selectedSort === 'running_longest' ? '✓' : '';
    document.getElementById('sortCheckRunningNewest').textContent = selectedSort === 'running_newest' ? '✓' : '';
    const libNewestEl = document.getElementById('sortCheckLibraryNewest');
    const libOldestEl = document.getElementById('sortCheckLibraryOldest');
    if (libNewestEl) libNewestEl.textContent = selectedSort === 'library_newest' ? '✓' : '';
    if (libOldestEl) libOldestEl.textContent = selectedSort === 'library_oldest' ? '✓' : '';
    const perfIds = [
        ['sortCheckRevenueDesc', 'revenue_desc'],
        ['sortCheckRevenueAsc', 'revenue_asc'],
        ['sortCheckRoasDesc', 'roas_desc'],
        ['sortCheckRoasAsc', 'roas_asc'],
        ['sortCheckCtrDesc', 'ctr_desc'],
        ['sortCheckCtrAsc', 'ctr_asc'],
        ['sortCheckClicksDesc', 'clicks_desc'],
        ['sortCheckClicksAsc', 'clicks_asc'],
        ['sortCheckImpressionsDesc', 'impressions_desc'],
        ['sortCheckImpressionsAsc', 'impressions_asc'],
        ['sortCheckSpendDesc', 'spend_desc'],
        ['sortCheckSpendAsc', 'spend_asc'],
    ];
    perfIds.forEach(([id, key]) => {
        const el = document.getElementById(id);
        if (el) el.textContent = selectedSort === key ? '✓' : '';
    });
}

/**
 * Toggle sort dropdown visibility
 */
export function toggleSortDropdown(e) {
    e.stopPropagation();
    closeFilterDropdown();
    const dropdown = document.getElementById('imagesSortDropdown');
    if (dropdown) {
        dropdown.classList.toggle('is-open');
    }
}

/**
 * Close sort dropdown
 */
function closeSortDropdown() {
    const dropdown = document.getElementById('imagesSortDropdown');
    if (dropdown) {
        dropdown.classList.remove('is-open');
    }
}

/**
 * Toggle filter dropdown visibility
 */
export function toggleFilterDropdown(e) {
    e.stopPropagation();
    closeSortDropdown();
    const dropdown = document.getElementById('imagesFilterDropdown');
    if (dropdown) {
        dropdown.classList.toggle('is-open');
    }
}

/**
 * Close filter dropdown
 */
function closeFilterDropdown() {
    const dropdown = document.getElementById('imagesFilterDropdown');
    if (dropdown) {
        dropdown.classList.remove('is-open');
    }
}

// ============ Media Type Filter ============

let mediaTypeFilterInitialized = false;

function initMediaTypeFilter() {
    if (mediaTypeFilterInitialized) return;
    const options = document.querySelectorAll('.images-media-type-option');
    if (!options.length) return;

    const updateActive = (mediaType) => {
        options.forEach((el) => {
            el.classList.toggle('is-active', el.dataset.mediaType === mediaType);
        });
    };
    updateActive(getImagesMediaTypeFilter());

    options.forEach((option) => {
        option.addEventListener('click', () => {
            const mediaType = option.dataset.mediaType;
            if (!mediaType) return;
            setImagesMediaTypeFilter(mediaType);
            updateActive(mediaType);
            updateMetricFilterBadge();
            setImagesCache([]);
            setImagesTotal(0);
            loadFirstPage();
        });
    });
    mediaTypeFilterInitialized = true;
}

// ============ View Toggle ============

let viewToggleInitialized = false;

function updateViewToggleUI() {
    const viewMode = getImagesViewMode();
    const buttons = document.querySelectorAll('.images-view-toggle__btn');
    buttons.forEach((btn) => {
        btn.classList.toggle('active', btn.dataset.view === viewMode);
    });
}

function initViewToggle() {
    if (viewToggleInitialized) return;
    const buttons = document.querySelectorAll('.images-view-toggle__btn');
    if (!buttons.length) return;
    buttons.forEach((btn) => {
        btn.addEventListener('click', () => {
            const mode = btn.dataset.view;
            if (!mode) return;
            setImagesViewMode(mode);
        });
    });
    viewToggleInitialized = true;
}

export function setImagesViewMode(mode) {
    setImagesViewModeState(mode);
    updateViewToggleUI();
    const sizeToolbar = document.querySelector('.images-size-toolbar');
    if (sizeToolbar) {
        sizeToolbar.style.display = mode === 'table' ? 'none' : 'flex';
    }
    renderImagesPage();
}

// ============ Metric Filters ============

let metricFiltersInitialized = false;
const applyMetricFiltersDebounced = debounce(() => {
    setImagesCache([]);
    setImagesTotal(0);
    loadFirstPage();
}, 250);

function updateMetricFilterBadge() {
    const badge = document.getElementById('imagesFilterBadge');
    if (!badge) return;
    const { minClicks, minRevenue, minImpressions, minSpend } = getImagesMetricFilters();
    const metricCount = [minClicks, minRevenue, minImpressions, minSpend].filter((v) => Number.isFinite(v)).length;
    const mediaTypeCount = getImagesMediaTypeFilter() !== 'all' ? 1 : 0;
    const dedupeCount = getImagesHideDuplicates() ? 1 : 0;
    const activeCount = metricCount + mediaTypeCount + dedupeCount;
    badge.textContent = activeCount > 0 ? String(activeCount) : '';
    badge.classList.toggle('is-visible', activeCount > 0);
}

function initMetricFilters() {
    if (metricFiltersInitialized) return;
    const minClicksInput = document.getElementById('imagesMinClicks');
    const minRevenueInput = document.getElementById('imagesMinRevenue');
    const minImpressionsInput = document.getElementById('imagesMinImpressions');
    const minSpendInput = document.getElementById('imagesMinSpend');
    const hideDuplicatesInput = document.getElementById('imagesHideDuplicates');
    const applyBtn = document.getElementById('imagesFilterApplyBtn');
    const clearBtn = document.getElementById('imagesFilterClearBtn');
    if (!minClicksInput || !minRevenueInput || !minImpressionsInput || !minSpendInput || !hideDuplicatesInput || !applyBtn || !clearBtn) return;

    const filters = getImagesMetricFilters();
    minClicksInput.value = Number.isFinite(filters.minClicks) ? String(filters.minClicks) : '';
    minRevenueInput.value = Number.isFinite(filters.minRevenue) ? String(filters.minRevenue) : '';
    minImpressionsInput.value = Number.isFinite(filters.minImpressions) ? String(filters.minImpressions) : '';
    minSpendInput.value = Number.isFinite(filters.minSpend) ? String(filters.minSpend) : '';
    hideDuplicatesInput.checked = getImagesHideDuplicates();

    const collectAndSave = () => {
        setImagesMetricFilters({
            minClicks: minClicksInput.value === '' ? null : Number(minClicksInput.value),
            minRevenue: minRevenueInput.value === '' ? null : Number(minRevenueInput.value),
            minImpressions: minImpressionsInput.value === '' ? null : Number(minImpressionsInput.value),
            minSpend: minSpendInput.value === '' ? null : Number(minSpendInput.value),
        });
        setImagesHideDuplicates(hideDuplicatesInput.checked);
        updateMetricFilterBadge();
    };

    [minClicksInput, minRevenueInput, minImpressionsInput, minSpendInput].forEach((el) => {
        el.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                collectAndSave();
                closeFilterDropdown();
                applyMetricFiltersDebounced();
            }
        });
    });

    applyBtn.addEventListener('click', () => {
        collectAndSave();
        closeFilterDropdown();
        applyMetricFiltersDebounced();
    });

    clearBtn.addEventListener('click', () => {
        minClicksInput.value = '';
        minRevenueInput.value = '';
        minImpressionsInput.value = '';
        minSpendInput.value = '';
        hideDuplicatesInput.checked = false;
        setImagesMediaTypeFilter('all');
        document.querySelectorAll('.images-media-type-option').forEach((el) => {
            el.classList.toggle('is-active', el.dataset.mediaType === 'all');
        });
        setImagesMetricFilters({
            minClicks: null,
            minRevenue: null,
            minImpressions: null,
            minSpend: null,
        });
        setImagesHideDuplicates(false);
        updateMetricFilterBadge();
        closeFilterDropdown();
        applyMetricFiltersDebounced();
    });

    updateMetricFilterBadge();
    metricFiltersInitialized = true;
}

// ============ Slider Initialization ============

// Track if slider has been initialized to avoid duplicate listeners
let sliderInitialized = false;

// Track if drag-drop has been initialized
let dragDropInitialized = false;

/**
 * Initialize the size slider
 */
function initSizeSlider() {
    if (sliderInitialized) {
        return; // Already initialized
    }
    
    const slider = document.getElementById('imagesSizeSlider');
    const valueDisplay = document.getElementById('imagesSizeValue');
    const container = document.querySelector('.images-container');
    
    if (!slider || !valueDisplay || !container) {
        console.warn('[ImagesController] Slider elements not found');
        return;
    }
    
    // Restore saved column count
    const savedCount = getImagesColumnCount();
    slider.value = savedCount;
    valueDisplay.textContent = savedCount;
    container.style.setProperty('--images-column-count', String(savedCount));
    
    // Debounced handler for slider changes
    const handleSliderChange = debounce((value) => {
        const count = parseInt(value, 10);
        setImagesColumnCount(count);
        valueDisplay.textContent = count;
        container.style.setProperty('--images-column-count', String(count));
        cancelScheduledLayoutFromImageLoad();
        relayoutImagesGrid();
    }, 100);
    
    // Attach event listener
    slider.addEventListener('input', (e) => {
        const value = e.target.value;
        valueDisplay.textContent = value;
        handleSliderChange(value);
    });
    
    sliderInitialized = true;
}

// ============ Drag-and-Drop Initialization ============

/**
 * Initialize viewport drag-and-drop for image uploads
 */
function initViewportDragDrop() {
    if (dragDropInitialized) {
        return; // Already initialized
    }
    
    const container = document.querySelector('.images-container');
    if (!container) {
        console.warn('[ImagesController] images-container not found for drag-drop');
        return;
    }
    
    // Create drop zone overlay (hidden by default)
    let dropOverlay = document.getElementById('imagesDropOverlay');
    if (!dropOverlay) {
        dropOverlay = document.createElement('div');
        dropOverlay.id = 'imagesDropOverlay';
        dropOverlay.className = 'images-drop-overlay';
        dropOverlay.innerHTML = `
            <div class="images-drop-overlay__content">
                <div class="images-drop-overlay__icon">📤</div>
                <p class="images-drop-overlay__text">Drop media to upload</p>
                <p class="images-drop-overlay__hint">Images and videos up to 50MB</p>
            </div>
        `;
        container.appendChild(dropOverlay);
    }
    
    // Track drag enter/leave depth to handle nested elements
    let dragDepth = 0;
    
    // Prevent default drag behaviors on document to enable custom drop
    const preventDefault = (e) => {
        e.preventDefault();
        e.stopPropagation();
    };
    
    // Handle drag enter on container
    container.addEventListener('dragenter', (e) => {
        preventDefault(e);
        
        // Only show overlay for files (not text selections, etc.)
        if (!e.dataTransfer.types.includes('Files')) {
            return;
        }
        
        dragDepth++;
        if (dragDepth === 1) {
            dropOverlay.classList.add('is-visible');
        }
    });
    
    // Handle drag over (required to enable drop)
    container.addEventListener('dragover', (e) => {
        preventDefault(e);
        
        if (!e.dataTransfer.types.includes('Files')) {
            return;
        }
        
        e.dataTransfer.dropEffect = 'copy';
    });
    
    // Handle drag leave
    container.addEventListener('dragleave', (e) => {
        preventDefault(e);
        
        dragDepth--;
        if (dragDepth === 0) {
            dropOverlay.classList.remove('is-visible');
        }
    });
    
    // Handle drop
    container.addEventListener('drop', async (e) => {
        preventDefault(e);
        dragDepth = 0;
        dropOverlay.classList.remove('is-visible');
        
        // Get media files from drop (images and videos)
        const files = Array.from(e.dataTransfer.files).filter(f => 
            f.type.startsWith('image/') || f.type.startsWith('video/')
        );
        
        if (files.length === 0) {
            return;
        }
        
        // Get client ID
        const clientId = window.appStateGet?.('currentClientId') || 
                         document.getElementById('clientSelect')?.value;
        
        if (!clientId) {
            alert('Please select a client first');
            return;
        }
        
        // Upload the files
        await handleViewportDrop(files, clientId);
    });
    
    dragDropInitialized = true;
}

/**
 * Format file size for display
 * @param {number} bytes - File size in bytes
 * @returns {string} Formatted size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Handle dropped files upload
 * @param {File[]} files - Array of media files
 * @param {string} clientId - Client UUID
 */
async function handleViewportDrop(files, clientId) {
    // Check file sizes (50MB limit for server uploads)
    const MAX_SIZE = 50 * 1024 * 1024; // 50MB
    const oversizedFiles = files.filter(f => f.size > MAX_SIZE);
    
    if (oversizedFiles.length > 0) {
        const names = oversizedFiles.map(f => `${f.name} (${formatFileSize(f.size)})`).join('\n');
        alert(`Some files are too large (max 50MB):\n${names}`);
        // Filter out oversized files
        files = files.filter(f => f.size <= MAX_SIZE);
        if (files.length === 0) {
            return;
        }
    }
    
    const totalFiles = files.length;
    let successCount = 0;
    let failCount = 0;
    const errors = [];
    
    // Show progress banner at top of container
    const banner = showUploadBanner('Uploading...', totalFiles);
    
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        updateUploadBanner(banner, i, totalFiles, false, `Uploading ${file.name}...`);
        
        try {
            const image = await uploadAdImage(clientId, file);
            addImageToCache(image);
            successCount++;
        } catch (error) {
            failCount++;
            errors.push(`${file.name}: ${error.message}`);
            console.error(`[ImagesController] Failed to upload ${file.name}:`, error);
        }
        
        // Update progress after each file
        updateUploadBanner(banner, i + 1, totalFiles);
    }
    
    // Re-render the grid (cache now has new items; keep total at least cache length for "Showing X of Y")
    setImagesTotal(Math.max(getImagesTotal(), getImagesCache().length));
    renderImagesPage();
    updateLoadMoreVisibility();

    // Show results
    if (failCount === 0) {
        updateUploadBanner(banner, totalFiles, totalFiles, true, `Uploaded ${successCount} file(s)`);
    } else {
        updateUploadBanner(banner, totalFiles, totalFiles, true, `Uploaded ${successCount}, failed ${failCount}`);
        if (errors.length > 0) {
            console.error('[ImagesController] Upload errors:', errors);
        }
    }
}

/**
 * Show upload progress banner
 * @param {string} message - Initial message
 * @param {number} total - Total number of files
 * @returns {HTMLElement} Banner element
 */
function showUploadBanner(message, total) {
    // Remove any existing banner
    const existing = document.getElementById('imagesUploadBanner');
    if (existing) {
        existing.remove();
    }
    
    const container = document.querySelector('.images-container');
    if (!container) {
        return null;
    }
    
    const banner = document.createElement('div');
    banner.id = 'imagesUploadBanner';
    banner.className = 'images-upload-banner';
    banner.innerHTML = `
        <div class="images-upload-banner__content">
            <div class="images-upload-banner__spinner"></div>
            <span class="images-upload-banner__text">${message}</span>
            <span class="images-upload-banner__count">0 / ${total}</span>
        </div>
        <div class="images-upload-banner__progress">
            <div class="images-upload-banner__progress-bar"></div>
        </div>
    `;
    
    // Insert at top of container
    container.insertBefore(banner, container.firstChild);
    
    // Trigger animation
    requestAnimationFrame(() => {
        banner.classList.add('is-visible');
    });
    
    return banner;
}

/**
 * Update banner progress
 * @param {HTMLElement} banner - Banner element
 * @param {number} current - Current file index (1-based)
 * @param {number} total - Total number of files
 * @param {boolean} done - If true, show completion state
 * @param {string} [message] - Optional message override
 */
function updateUploadBanner(banner, current, total, done = false, message = null) {
    if (!banner) return;
    
    const textEl = banner.querySelector('.images-upload-banner__text');
    const countEl = banner.querySelector('.images-upload-banner__count');
    const progressBar = banner.querySelector('.images-upload-banner__progress-bar');
    
    if (message && textEl) {
        textEl.textContent = message;
    }
    
    if (countEl) {
        countEl.textContent = `${current} / ${total}`;
    }
    
    if (progressBar) {
        const percent = Math.round((current / total) * 100);
        progressBar.style.width = `${percent}%`;
    }
    
    if (done) {
        banner.classList.add('is-done');
        setTimeout(() => {
            banner.classList.remove('is-visible');
            setTimeout(() => {
                banner.remove();
            }, 300);
        }, 2000);
    }
}

// ============ Pagination ============

const IMAGES_PAGE_SIZE = 60;

/**
 * Load first page of images and render (used on init and when sort/media filter changes).
 */
async function loadFirstPage() {
    const container = document.getElementById('imagesGrid');
    const clientId = window.appStateGet?.('currentClientId') || document.getElementById('clientSelect')?.value;
    if (!container || !clientId) return;

    showLoading(container);
    setImagesLoading(true);
    setImagesError(null);
    try {
        const response = await fetchAdImages(clientId, {
            limit: IMAGES_PAGE_SIZE,
            offset: 0,
            sortBy: getImagesSortBy(),
            mediaType: getImagesMediaTypeFilter(),
            ...getImagesMetricFilters(),
        });
        const items = response.items || [];
        setImagesCache(items);
        setImagesTotal(response.total ?? 0);
        setImagesCurrentClientId(clientId);
        setImagesLoading(false);
        renderImagesPage();
        updateLoadMoreVisibility();
    } catch (error) {
        console.error('[ImagesController] Failed to load images:', error);
        setImagesLoading(false);
        setImagesError(error.message);
        renderError(container, error.message);
        updateLoadMoreVisibility();
    }
}

/**
 * Get the scrollable ancestor of an element (has overflow-y auto/scroll and scrollable content).
 * @param {HTMLElement} el
 * @returns {{ element: HTMLElement | null, scrollTop: number } | null}
 */
function getScrollPosition(el) {
    if (!el) return null;
    const win = el.ownerDocument?.defaultView || window;
    let scrollTop = win.scrollY ?? win.pageYOffset ?? document.documentElement.scrollTop;
    let scrollable = null;
    let node = el.parentElement;
    while (node && node !== document.body) {
        const style = win.getComputedStyle(node);
        const overflowY = style.overflowY;
        const canScroll = (overflowY === 'auto' || overflowY === 'scroll' || overflowY === 'overlay') &&
            node.scrollHeight > node.clientHeight;
        if (canScroll) {
            scrollable = node;
            scrollTop = node.scrollTop;
            break;
        }
        node = node.parentElement;
    }
    return { element: scrollable || (win === window ? document.documentElement : null), scrollTop };
}

/**
 * Restore scroll position after a re-render so the user stays in place.
 * @param {{ element: HTMLElement | null, scrollTop: number } | null} saved
 */
function restoreScrollPosition(saved) {
    if (!saved) return;
    requestAnimationFrame(() => {
        if (saved.element && saved.element !== document.documentElement) {
            saved.element.scrollTop = saved.scrollTop;
        } else {
            window.scrollTo(0, saved.scrollTop);
        }
    });
}

/**
 * Load next page and append to grid.
 */
export async function loadMoreImagesPage() {
    const container = document.getElementById('imagesGrid');
    const clientId = getImagesCurrentClientId();
    const cache = getImagesCache();
    const total = getImagesTotal();
    if (!container || !clientId || cache.length >= total) return;

    const savedScroll = getScrollPosition(container);

    const loadMoreEl = document.getElementById('imagesLoadMoreBtn');
    const loadMoreWrap = document.getElementById('imagesLoadMoreWrap');
    if (loadMoreEl) loadMoreEl.disabled = true;
    if (loadMoreWrap) loadMoreWrap.classList.add('is-loading');

    try {
        const response = await fetchAdImages(clientId, {
            limit: IMAGES_PAGE_SIZE,
            offset: cache.length,
            sortBy: getImagesSortBy(),
            mediaType: getImagesMediaTypeFilter(),
            ...getImagesMetricFilters(),
        });
        const newItems = response.items || [];
        setImagesCache([...cache, ...newItems]);
        setImagesTotal(response.total ?? total);
        renderImagesPage();
        updateLoadMoreVisibility();
        restoreScrollPosition(savedScroll);
    } catch (error) {
        console.error('[ImagesController] Load more failed:', error);
        updateLoadMoreVisibility();
    } finally {
        if (loadMoreEl) loadMoreEl.disabled = false;
        if (loadMoreWrap) loadMoreWrap.classList.remove('is-loading');
    }
}

/**
 * Show/hide Load more area and update "Showing X of Y" text.
 */
function updateLoadMoreVisibility() {
    const wrap = document.getElementById('imagesLoadMoreWrap');
    const btn = document.getElementById('imagesLoadMoreBtn');
    const countEl = document.getElementById('imagesLoadMoreCount');
    const cache = getImagesCache();
    const total = getImagesTotal();

    if (!wrap) return;
    if (total === 0 && cache.length === 0) {
        wrap.classList.add('is-hidden');
        return;
    }
    wrap.classList.remove('is-hidden');
    if (countEl) countEl.textContent = `Showing ${cache.length} of ${total}`;
    if (btn) {
        btn.disabled = cache.length >= total;
        btn.textContent = cache.length >= total ? 'All loaded' : 'Load more';
    }
}

// ============ Page Initialization ============

/**
 * Initialize the Images page - load and render images
 */
export async function initImagesPage() {
    initSizeSlider();
    initSortDropdown();
    initMediaTypeFilter();
    initViewToggle();
    initMetricFilters();
    initViewportDragDrop();
    updateViewToggleUI();
    const sizeToolbar = document.querySelector('.images-size-toolbar');
    if (sizeToolbar) {
        sizeToolbar.style.display = getImagesViewMode() === 'table' ? 'none' : 'flex';
    }

    const container = document.getElementById('imagesGrid');
    if (!container) {
        console.error('[ImagesController] imagesGrid container not found');
        return;
    }

    const clientId = window.appStateGet?.('currentClientId') || document.getElementById('clientSelect')?.value;
    if (!clientId) {
        container.innerHTML = `
            <div class="images-empty">
                <div class="images-empty__icon">🖼️</div>
                <h3 class="images-empty__title">No client selected</h3>
                <p class="images-empty__text">Please select a client first</p>
            </div>
        `;
        updateLoadMoreVisibility();
        return;
    }

    const cachedClientId = getImagesCurrentClientId();
    const cachedImages = getImagesCache();
    const sameClientAndHasCache = cachedClientId === clientId && cachedImages.length > 0;

    if (sameClientAndHasCache) {
        renderImagesPage();
        updateLoadMoreVisibility();
        return;
    }

    await loadFirstPage();
}

/**
 * Render the images page
 */
export function renderImagesPage() {
    const container = document.getElementById('imagesGrid');
    if (!container) {
        return;
    }
    
    const images = getImagesCache();
    const sortBy = getImagesSortBy();
    const sortedImages = sortImages(images, sortBy);
    const viewMode = getImagesViewMode();
    const dedupedImages = (viewMode === 'table' && getImagesHideDuplicates())
        ? dedupeImagesForTable(sortedImages)
        : sortedImages;
    updateViewToggleUI();

    if (viewMode === 'table') {
        renderImagesTable(container, dedupedImages, {
            columns: getImagesTableColumns(),
            onColumnsChange: (columns) => {
                setImagesTableColumns(columns);
                renderImagesPage();
            },
        });
    } else {
        renderImagesGrid(container, sortedImages);
    }
    updateBulkDeleteButton();
}

function dedupeImagesForTable(images = []) {
    const seen = new Set();
    return images.filter((image) => {
        const key = [
            image.id || '',
            image.revenue ?? '',
            image.roas ?? '',
            image.ctr ?? '',
            image.clicks ?? '',
            image.impressions ?? '',
            image.spend ?? '',
            image.purchases ?? '',
            image.started_running_on_best_ad || '',
            image.meta_ad_id || ''
        ].join('|');
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
    });
}
