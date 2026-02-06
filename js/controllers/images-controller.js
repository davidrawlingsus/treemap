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
    addImageToCache
} from '/js/state/images-state.js';
import { renderImagesGrid, showLoading, renderError, relayoutImagesGrid, cancelScheduledLayoutFromImageLoad } from '/js/renderers/images-renderer.js';
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
            // Sort by created_at descending (newest first)
            sorted.sort((a, b) => {
                const dateA = new Date(a.created_at || 0);
                const dateB = new Date(b.created_at || 0);
                return dateB - dateA;
            });
            break;
        case 'oldest':
            // Sort by created_at ascending (oldest first)
            sorted.sort((a, b) => {
                const dateA = new Date(a.created_at || 0);
                const dateB = new Date(b.created_at || 0);
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
            renderImagesPage();
        });
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        const container = document.querySelector('.images-sort-menu-container');
        if (container && !container.contains(e.target)) {
            closeSortDropdown();
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
}

/**
 * Toggle sort dropdown visibility
 */
export function toggleSortDropdown(e) {
    e.stopPropagation();
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
    
    // Re-render the grid
    renderImagesPage();
    
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

// ============ Page Initialization ============

/**
 * Initialize the Images page - load and render images
 */
export async function initImagesPage() {
    // Initialize controls first (before any rendering)
    initSizeSlider();
    initSortDropdown();
    
    // Initialize viewport drag-and-drop
    initViewportDragDrop();
    
    const container = document.getElementById('imagesGrid');
    if (!container) {
        console.error('[ImagesController] imagesGrid container not found');
        return;
    }
    
    const clientId = window.appStateGet?.('currentClientId') || 
                     document.getElementById('clientSelect')?.value;
    
    if (!clientId) {
        container.innerHTML = `
            <div class="images-empty">
                <div class="images-empty__icon">🖼️</div>
                <h3 class="images-empty__title">No client selected</h3>
                <p class="images-empty__text">Please select a client first</p>
            </div>
        `;
        return;
    }
    
    const cachedClientId = getImagesCurrentClientId();
    const cachedImages = getImagesCache();
    
    if (cachedClientId === clientId && cachedImages.length > 0) {
        renderImagesPage();
        return;
    }
    
    showLoading(container);
    setImagesLoading(true);
    setImagesError(null);
    
    try {
        const response = await fetchAdImages(clientId);
        const images = response.items || [];
        
        setImagesCache(images);
        setImagesCurrentClientId(clientId);
        setImagesLoading(false);
        
        renderImagesPage();
    } catch (error) {
        console.error('[ImagesController] Failed to load images:', error);
        setImagesLoading(false);
        setImagesError(error.message);
        renderError(container, error.message);
    }
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
    renderImagesGrid(container, sortedImages);
}
