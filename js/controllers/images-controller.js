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
    addImageToCache
} from '/js/state/images-state.js';
import { renderImagesGrid, showLoading, renderError, relayoutImagesGrid, cancelScheduledLayoutFromImageLoad } from '/js/renderers/images-renderer.js';
import { debounce } from '/js/utils/dom.js';

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
    
    // Show a simple toast/notification for progress
    const toast = showUploadToast(`Uploading ${totalFiles} file(s)...`);
    
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        updateUploadToast(toast, `Uploading ${i + 1} of ${totalFiles}...`);
        
        try {
            const image = await uploadAdImage(clientId, file);
            addImageToCache(image);
            successCount++;
        } catch (error) {
            failCount++;
            errors.push(`${file.name}: ${error.message}`);
            console.error(`[ImagesController] Failed to upload ${file.name}:`, error);
        }
    }
    
    // Re-render the grid
    renderImagesPage();
    
    // Show results
    if (failCount === 0) {
        updateUploadToast(toast, `Uploaded ${successCount} file(s)`, true);
    } else {
        updateUploadToast(toast, `Uploaded ${successCount}, failed ${failCount}`, true);
        if (errors.length > 0) {
            console.error('[ImagesController] Upload errors:', errors);
        }
    }
}

/**
 * Show upload progress toast
 * @param {string} message - Initial message
 * @returns {HTMLElement} Toast element
 */
function showUploadToast(message) {
    // Remove any existing toast
    const existing = document.getElementById('imagesUploadToast');
    if (existing) {
        existing.remove();
    }
    
    const toast = document.createElement('div');
    toast.id = 'imagesUploadToast';
    toast.className = 'images-upload-toast';
    toast.innerHTML = `
        <div class="images-upload-toast__spinner"></div>
        <span class="images-upload-toast__text">${message}</span>
    `;
    document.body.appendChild(toast);
    
    // Trigger animation
    requestAnimationFrame(() => {
        toast.classList.add('is-visible');
    });
    
    return toast;
}

/**
 * Update toast message
 * @param {HTMLElement} toast - Toast element
 * @param {string} message - New message
 * @param {boolean} done - If true, hide toast after delay
 */
function updateUploadToast(toast, message, done = false) {
    const textEl = toast.querySelector('.images-upload-toast__text');
    if (textEl) {
        textEl.textContent = message;
    }
    
    if (done) {
        toast.classList.add('is-done');
        setTimeout(() => {
            toast.classList.remove('is-visible');
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 2000);
    }
}

// ============ Page Initialization ============

/**
 * Initialize the Images page - load and render images
 */
export async function initImagesPage() {
    // Initialize slider first (before any rendering)
    initSizeSlider();
    
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
    renderImagesGrid(container, images);
}
