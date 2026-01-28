/**
 * Images Renderer Module
 * Pure rendering functions for images grid and image picker modal.
 * Follows renderer pattern - accepts container and data, handles DOM only.
 */

import { deleteAdImage } from '/js/services/api-ad-images.js';
import { getImagesCache, removeImageFromCache } from '/js/state/images-state.js';
import { escapeHtml } from '/js/utils/dom.js';

// Store current image picker callback
let imagePickerCallback = null;

// Store Masonry instance for cleanup/relayout
let masonryInstance = null;

let imageLoadLayoutTimeout = null;
const IMAGE_LOAD_LAYOUT_DELAY_MS = 120;
let lastSliderRelayoutTime = 0;
const SLIDER_COOLDOWN_MS = 600; // Ignore image-load layouts for 600ms after slider change

/** Debounced layout for image-load callbacks. Batches many load-triggered layouts into one. */
function scheduleLayoutFromImageLoad() {
    // Skip if we're in the cooldown period after a slider change
    const timeSinceSlider = Date.now() - lastSliderRelayoutTime;
    if (timeSinceSlider < SLIDER_COOLDOWN_MS) {
        return;
    }
    
    if (imageLoadLayoutTimeout) clearTimeout(imageLoadLayoutTimeout);
    imageLoadLayoutTimeout = setTimeout(() => {
        imageLoadLayoutTimeout = null;
        // Check cooldown again when executing (images might have loaded during cooldown)
        const timeSinceSliderExec = Date.now() - lastSliderRelayoutTime;
        if (timeSinceSliderExec < SLIDER_COOLDOWN_MS) {
            return;
        }
        if (masonryInstance) {
            // Disable transitions during layout to prevent visual glitch
            const grid = masonryInstance.element;
            grid.classList.add('images-grid--no-transition');
            
            masonryInstance.layout();
            
            // Re-enable transitions after layout completes
            setTimeout(() => {
                grid.classList.remove('images-grid--no-transition');
            }, 50);
        }
    }, IMAGE_LOAD_LAYOUT_DELAY_MS);
}

/**
 * Cancel any pending image-load-triggered layout.
 * When setCooldown is true (default), also marks slider relayout time so image-load layouts
 * are skipped for SLIDER_COOLDOWN_MS. Only pass true when called from slider handler.
 * Pass false when clearing before re-render (e.g. renderImagesGrid) so we don't block
 * image-load layouts after initial load.
 * @param {boolean} [setCooldown=true] - Whether to set cooldown timestamp
 */
export function cancelScheduledLayoutFromImageLoad(setCooldown = true) {
    if (setCooldown) {
        lastSliderRelayoutTime = Date.now();
    }
    if (imageLoadLayoutTimeout) {
        clearTimeout(imageLoadLayoutTimeout);
        imageLoadLayoutTimeout = null;
    }
}

/**
 * Show loading state
 * @param {HTMLElement} container - Container element
 */
export function showLoading(container) {
    container.innerHTML = `
        <div class="images-loading">
            <p>Loading images...</p>
        </div>
    `;
}

/**
 * Render error state with retry button
 * @param {HTMLElement} container - Container element
 * @param {string} message - Error message
 */
export function renderError(container, message) {
    container.innerHTML = `
        <div class="images-error">
            <p class="images-error__text">${escapeHtml(message)}</p>
            <button class="images-error__retry" onclick="window.initImagesPage()">Retry</button>
        </div>
    `;
}

/**
 * Render empty state
 * @param {HTMLElement} container - Container element
 */
export function renderEmpty(container) {
    container.innerHTML = `
        <div class="images-empty">
            <div class="images-empty__icon">🖼️</div>
            <h3 class="images-empty__title">No images yet</h3>
            <p class="images-empty__text">Upload images to build your inventory</p>
            <button class="images-empty__upload-btn" onclick="window.showImageUploadModal()">Upload Image</button>
        </div>
    `;
}

/**
 * Render grid of images
 * @param {HTMLElement} container - Container element
 * @param {Array} images - Array of image objects
 */
export function renderImagesGrid(container, images) {
    cancelScheduledLayoutFromImageLoad(false); // Clear pending only; don't set cooldown
    // Destroy existing Masonry instance before re-rendering
    if (masonryInstance) {
        masonryInstance.destroy();
        masonryInstance = null;
    }
    
    // Clean up existing intersection observer
    if (window.imagesIntersectionObserver) {
        window.imagesIntersectionObserver.disconnect();
        window.imagesIntersectionObserver = null;
    }
    
    if (!images || images.length === 0) {
        renderEmpty(container);
        return;
    }
    
    // Add sizer elements for Masonry + image cards
    container.innerHTML = `
        <div class="images-grid-sizer"></div>
        <div class="images-gutter-sizer"></div>
        ${images.map(image => renderImageCard(image)).join('')}
    `;
    
    // Attach event listeners
    attachEventListeners(container);
    
    // Initialize lazy loading with Intersection Observer
    initLazyLoading(container);
    
    // Initialize Masonry for tiling layout
    initMasonry(container);
}

/**
 * Initialize lazy loading with Intersection Observer
 * Only loads images when they're about to enter the viewport
 * @param {HTMLElement} container - Grid container element
 */
function initLazyLoading(container) {
    // Check if Intersection Observer is supported
    if (typeof IntersectionObserver === 'undefined') {
        // Fallback: load all images immediately
        const images = container.querySelectorAll('.images-card__image[data-src]');
        images.forEach(img => {
            img.src = img.dataset.src;
            img.removeAttribute('data-src');
        });
        return;
    }
    
    // Create intersection observer with root margin for preloading
    // Load images 100px before they enter viewport
    window.imagesIntersectionObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                const src = img.dataset.src;
                
                if (src) {
                    // Add loading class
                    img.classList.add('images-card__image--loading');
                    
                    // Load the image
                    const tempImg = new Image();
                    tempImg.onload = () => {
                        img.src = src;
                        img.removeAttribute('data-src');
                        img.classList.remove('images-card__image--loading');
                        img.classList.add('images-card__image--loaded');
                        
                        // Fade in image
                        requestAnimationFrame(() => {
                            img.style.opacity = '1';
                        });
                        
                        // Hide placeholder with fade out
                        const placeholder = img.previousElementSibling;
                        if (placeholder && placeholder.classList.contains('images-card__placeholder')) {
                            placeholder.style.opacity = '0';
                            setTimeout(() => {
                                placeholder.style.display = 'none';
                            }, 300);
                        }
                        
                        // Trigger Masonry relayout (debounced to avoid cascade → "revert then slide again")
                        if (masonryInstance) {
                            scheduleLayoutFromImageLoad();
                        }
                    };
                    tempImg.onerror = () => {
                        img.classList.remove('images-card__image--loading');
                        img.classList.add('images-card__image--error');
                    };
                    tempImg.src = src;
                }
                
                // Stop observing once loaded
                window.imagesIntersectionObserver.unobserve(img);
            }
        });
    }, {
        rootMargin: '100px' // Start loading 100px before image enters viewport
    });
    
    // Observe all images with data-src
    const images = container.querySelectorAll('.images-card__image[data-src]');
    images.forEach(img => {
        window.imagesIntersectionObserver.observe(img);
    });
}

/**
 * Initialize Masonry layout on the container
 * @param {HTMLElement} container - Grid container element
 */
function initMasonry(container) {
    if (typeof Masonry === 'undefined') {
        console.warn('[ImagesRenderer] Masonry.js not loaded, falling back to CSS layout');
        return;
    }
    
    // Disable transitions during initial layout to prevent visual glitch
    container.classList.add('images-grid--no-transition');
    
    masonryInstance = new Masonry(container, {
        itemSelector: '.images-card',
        columnWidth: '.images-grid-sizer',
        gutter: '.images-gutter-sizer',
        percentPosition: true,
        horizontalOrder: true,
        transitionDuration: 0 // No animation during initial layout
    });
    
    // Keep transitions disabled - they'll be re-enabled after the first debounced layout
    // This prevents the "grow then snap back" effect during initial load
    
    // Relayout after images load to handle different aspect ratios
    const images = container.querySelectorAll('.images-card__image');
    let loadedCount = 0;
    const totalImages = images.length;
    
    if (totalImages === 0) return;
    
    images.forEach(img => {
        // Check if already loaded (not using lazy loading) or loaded via Intersection Observer
        if (img.complete || img.classList.contains('images-card__image--loaded')) {
            loadedCount++;
            if (loadedCount === totalImages) {
                scheduleLayoutFromImageLoad();
            }
        } else if (!img.dataset.src) {
            // Image has src but not loaded yet
            img.addEventListener('load', () => {
                loadedCount++;
                if (loadedCount === totalImages) {
                    scheduleLayoutFromImageLoad();
                }
            }, { once: true });
        } else {
            // Image is lazy loading - wait for load event after src is set
            const checkLoad = () => {
                if (img.complete) {
                    loadedCount++;
                    if (loadedCount === totalImages) {
                        scheduleLayoutFromImageLoad();
                    }
                } else {
                    img.addEventListener('load', () => {
                        loadedCount++;
                        if (loadedCount === totalImages) {
                            scheduleLayoutFromImageLoad();
                        }
                    }, { once: true });
                }
            };
            
            // Check periodically if image has been loaded by Intersection Observer
            const checkInterval = setInterval(() => {
                if (img.classList.contains('images-card__image--loaded') || !img.dataset.src) {
                    clearInterval(checkInterval);
                    checkLoad();
                }
            }, 100);
        }
    });
}

/**
 * Relayout the images grid (for use when column count changes)
 * Safe to call even if Masonry instance doesn't exist
 * Forces Masonry to re-measure columnWidth before layout to ensure CSS variable changes are picked up
 */
export function relayoutImagesGrid() {
    if (masonryInstance) {
        const grid = masonryInstance.element;
        
        // Disable transitions during slider-driven layout to prevent visual glitch
        grid.classList.add('images-grid--no-transition');
        
        // Force browser to recalculate CSS (reflow)
        const sizer = grid.querySelector('.images-grid-sizer');
        if (sizer) {
            void sizer.offsetWidth;
        }
        
        // Perform layout immediately (no animation)
        masonryInstance.layout();
        
        // Re-enable transitions after a short delay so subsequent layouts animate
        setTimeout(() => {
            grid.classList.remove('images-grid--no-transition');
        }, 50);
    }
}

/**
 * Render single image card
 * @param {Object} image - Image object from API
 * @returns {string} HTML string
 */
function renderImageCard(image) {
    const id = escapeHtml(image.id || '');
    const url = escapeHtml(image.url || '');
    const filename = escapeHtml(image.filename || '');
    
    return `
        <div class="images-card" data-image-id="${id}">
            <div class="images-card__image-wrapper">
                <div class="images-card__placeholder"></div>
                <img 
                    data-src="${url}" 
                    alt="${filename}" 
                    class="images-card__image" 
                    loading="lazy"
                >
                <button class="images-card__delete" data-image-id="${id}" title="Delete image">×</button>
            </div>
            <div class="images-card__info">
                <div class="images-card__filename" title="${filename}">${filename}</div>
                <div class="images-card__meta">${formatFileSize(image.file_size || 0)}</div>
            </div>
        </div>
    `;
}

/**
 * Format file size
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
 * Attach event listeners using event delegation
 */
function attachEventListeners(container) {
    container.addEventListener('click', async (e) => {
        // Handle delete button
        const deleteBtn = e.target.closest('.images-card__delete');
        if (deleteBtn) {
            const imageId = deleteBtn.dataset.imageId;
            await handleDeleteImage(imageId, container);
            return;
        }
        
        // Handle image card click (show preview)
        const imageCard = e.target.closest('.images-card');
        if (imageCard) {
            const img = imageCard.querySelector('.images-card__image');
            const filename = imageCard.querySelector('.images-card__filename')?.textContent || '';
            // Get the actual src (either from src or data-src if not loaded yet)
            const imageUrl = img?.src || img?.dataset?.src;
            if (imageUrl) {
                showImagePreview(imageUrl, filename);
            }
            return;
        }
    });
}

/**
 * Show image preview overlay
 * @param {string} imageUrl - URL of the image to preview
 * @param {string} filename - Filename for display
 */
function showImagePreview(imageUrl, filename) {
    // Remove any existing preview overlay
    const existing = document.querySelector('.images-preview-overlay');
    if (existing) {
        existing.remove();
    }
    
    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'images-preview-overlay';
    overlay.innerHTML = `
        <div class="images-preview-container">
            <button class="images-preview-close" aria-label="Close preview">×</button>
            <div class="images-preview-image-wrapper">
                <div class="images-preview-loading">Loading...</div>
                <img 
                    src="${escapeHtml(imageUrl)}" 
                    alt="${escapeHtml(filename)}" 
                    class="images-preview-image"
                >
            </div>
            <div class="images-preview-filename">${escapeHtml(filename)}</div>
        </div>
    `;
    
    document.body.appendChild(overlay);
    
    // Prevent body scroll while overlay is open
    document.body.style.overflow = 'hidden';
    
    // Handle image load
    const img = overlay.querySelector('.images-preview-image');
    const loading = overlay.querySelector('.images-preview-loading');
    
    img.onload = () => {
        loading.style.display = 'none';
        img.classList.add('is-loaded');
    };
    
    img.onerror = () => {
        loading.textContent = 'Failed to load image';
    };
    
    // Animate in
    requestAnimationFrame(() => {
        overlay.classList.add('is-visible');
    });
    
    // Close handlers
    const closeOverlay = () => {
        overlay.classList.remove('is-visible');
        document.body.style.overflow = '';
        setTimeout(() => {
            overlay.remove();
        }, 200);
    };
    
    // Close on background click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay || e.target.classList.contains('images-preview-close')) {
            closeOverlay();
        }
    });
    
    // Close on Escape key
    const handleKeydown = (e) => {
        if (e.key === 'Escape') {
            closeOverlay();
            document.removeEventListener('keydown', handleKeydown);
        }
    };
    document.addEventListener('keydown', handleKeydown);
}

/**
 * Handle image deletion
 */
async function handleDeleteImage(imageId, container) {
    if (!confirm('Are you sure you want to delete this image?')) {
        return;
    }
    
    try {
        await deleteAdImage(imageId);
        removeImageFromCache(imageId);
        
        // Re-render via controller
        if (window.renderImagesPage) {
            window.renderImagesPage();
        }
    } catch (error) {
        console.error('[ImagesRenderer] Failed to delete image:', error);
        alert('Failed to delete image: ' + error.message);
    }
}

/**
 * Show image upload modal
 */
export function showImageUploadModal() {
    const clientId = window.appStateGet?.('currentClientId') || 
                     document.getElementById('clientSelect')?.value;
    
    if (!clientId) {
        alert('Please select a client first');
        return;
    }
    
    // Create modal overlay
    const overlay = document.createElement('div');
    overlay.className = 'images-upload-overlay';
    overlay.innerHTML = `
        <div class="images-upload-modal">
            <div class="images-upload-modal__header">
                <h2>Upload Image</h2>
                <button class="images-upload-modal__close" onclick="this.closest('.images-upload-overlay').remove()">×</button>
            </div>
            <div class="images-upload-modal__body">
                <input type="file" id="imageUploadInput" accept="image/*" multiple style="display: none;">
                <div class="images-upload-dropzone" id="imageUploadDropzone">
                    <div class="images-upload-dropzone__content">
                        <div class="images-upload-dropzone__icon">📤</div>
                        <p>Click to select or drag and drop</p>
                        <p class="images-upload-dropzone__hint">Supports JPG, PNG, WebP (multiple files allowed)</p>
                    </div>
                </div>
                <div class="images-upload-progress" id="imageUploadProgress" style="display: none;">
                    <div class="images-upload-progress__bar" id="imageUploadProgressBar"></div>
                    <p class="images-upload-progress__text">Uploading...</p>
                </div>
            </div>
            <div class="images-upload-modal__footer">
                <button class="images-upload-modal__cancel" onclick="this.closest('.images-upload-overlay').remove()">Cancel</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(overlay);
    
    const fileInput = overlay.querySelector('#imageUploadInput');
    const dropzone = overlay.querySelector('#imageUploadDropzone');
    const progress = overlay.querySelector('#imageUploadProgress');
    const progressBar = overlay.querySelector('#imageUploadProgressBar');
    
    // Click to select file
    dropzone.addEventListener('click', () => fileInput.click());
    
    // File input change
    fileInput.addEventListener('change', async (e) => {
        const files = Array.from(e.target.files || []);
        if (files.length > 0) {
            if (files.length === 1) {
                await handleImageUpload(files[0], clientId, overlay, progress, progressBar);
            } else {
                await handleBulkImageUpload(files, clientId, overlay, progress, progressBar);
            }
        }
    });
    
    // Drag and drop
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('is-dragover');
    });
    
    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('is-dragover');
    });
    
    dropzone.addEventListener('drop', async (e) => {
        e.preventDefault();
        dropzone.classList.remove('is-dragover');
        const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/'));
        if (files.length > 0) {
            if (files.length === 1) {
                await handleImageUpload(files[0], clientId, overlay, progress, progressBar);
            } else {
                await handleBulkImageUpload(files, clientId, overlay, progress, progressBar);
            }
        }
    });
    
    // Close on overlay click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.remove();
        }
    });
}

/**
 * Handle image upload
 */
async function handleImageUpload(file, clientId, overlay, progress, progressBar) {
    if (!file.type.startsWith('image/')) {
        alert('Please select an image file');
        return;
    }
    
    progress.style.display = 'block';
    progressBar.style.width = '0%';
    
    try {
        const { uploadAdImage } = await import('/js/services/api-ad-images.js');
        const { addImageToCache } = await import('/js/state/images-state.js');
        
        // Simulate progress (actual upload happens in service)
        let progressValue = 0;
        const progressInterval = setInterval(() => {
            progressValue += 10;
            if (progressValue < 90) {
                progressBar.style.width = progressValue + '%';
            }
        }, 100);
        
        const image = await uploadAdImage(clientId, file);
        
        clearInterval(progressInterval);
        progressBar.style.width = '100%';
        
        addImageToCache(image);
        
        // Re-render
        if (window.renderImagesPage) {
            window.renderImagesPage();
        }
        
        // Close modal after short delay
        setTimeout(() => {
            overlay.remove();
        }, 500);
    } catch (error) {
        console.error('[ImagesRenderer] Upload failed:', error);
        alert('Failed to upload image: ' + error.message);
        progress.style.display = 'none';
    }
}

/**
 * Handle bulk image upload
 */
async function handleBulkImageUpload(files, clientId, overlay, progress, progressBar) {
    progress.style.display = 'block';
    progressBar.style.width = '0%';
    
    const { uploadAdImage } = await import('/js/services/api-ad-images.js');
    const { addImageToCache } = await import('/js/state/images-state.js');
    
    const totalFiles = files.length;
    let successCount = 0;
    let failCount = 0;
    const errors = [];
    
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const progressPercent = Math.round((i / totalFiles) * 100);
        progressBar.style.width = progressPercent + '%';
        progress.querySelector('.images-upload-progress__text').textContent = `Uploading ${i + 1} of ${totalFiles}...`;
        
        try {
            const image = await uploadAdImage(clientId, file);
            addImageToCache(image);
            successCount++;
        } catch (error) {
            failCount++;
            errors.push(`${file.name}: ${error.message}`);
        }
    }
    
    progressBar.style.width = '100%';
    
    // Re-render
    if (window.renderImagesPage) {
        window.renderImagesPage();
    }
    
    // Show results
    if (failCount === 0) {
        progress.querySelector('.images-upload-progress__text').textContent = `Successfully uploaded ${successCount} image(s)`;
        setTimeout(() => {
            overlay.remove();
        }, 1500);
    } else {
        progress.querySelector('.images-upload-progress__text').textContent = `Uploaded ${successCount}, failed ${failCount}`;
        alert(`Upload complete:\n\nSuccess: ${successCount}\nFailed: ${failCount}\n\nErrors:\n${errors.join('\n')}`);
        progress.style.display = 'none';
    }
}

/**
 * Show image picker modal for selecting an image for an ad
 * @param {Function} onSelect - Callback function with selected image URL
 */
export function showImagePickerModal(onSelect) {
    // Remove any existing overlays first to prevent stacking
    const existingOverlays = document.querySelectorAll('.images-picker-overlay');
    existingOverlays.forEach(overlay => {
        overlay.remove();
    });
    
    imagePickerCallback = onSelect;
    
    const images = getImagesCache();
    
    if (images.length === 0) {
        alert('No images available. Please upload images first.');
        return;
    }
    
    // Create modal overlay
    const overlay = document.createElement('div');
    overlay.className = 'images-picker-overlay';
    overlay.innerHTML = `
        <div class="images-picker-modal">
            <div class="images-picker-modal__header">
                <h2>Select Image</h2>
                <button class="images-picker-modal__close">×</button>
            </div>
            <div class="images-picker-modal__body">
                <div class="images-picker-grid">
                    ${images.map(image => renderPickerImageCard(image)).join('')}
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(overlay);
    
    // Initialize lazy loading for picker images
    initPickerLazyLoading(overlay);
    
    // Attach click handlers
    overlay.addEventListener('click', (e) => {
        const imageCard = e.target.closest('.images-picker-card');
        if (imageCard) {
            const imageUrl = imageCard.dataset.imageUrl;
            if (imageUrl && imagePickerCallback) {
                imagePickerCallback(imageUrl);
            }
            overlay.remove();
            imagePickerCallback = null;
            return;
        }
        
        // Close on overlay background or close button click
        if (e.target.classList.contains('images-picker-modal__close') || e.target === overlay) {
            overlay.remove();
            imagePickerCallback = null;
        }
    });
}

/**
 * Initialize lazy loading for picker modal images
 * @param {HTMLElement} overlay - Modal overlay element
 */
function initPickerLazyLoading(overlay) {
    if (typeof IntersectionObserver === 'undefined') {
        // Fallback: load all images immediately
        const images = overlay.querySelectorAll('.images-picker-card__image[data-src]');
        images.forEach(img => {
            img.src = img.dataset.src;
            img.removeAttribute('data-src');
        });
        return;
    }
    
    const pickerObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                const src = img.dataset.src;
                
                if (src) {
                    const tempImg = new Image();
                    tempImg.onload = () => {
                        img.src = src;
                        img.removeAttribute('data-src');
                        img.style.opacity = '1';
                        
                        // Hide placeholder
                        const placeholder = img.previousElementSibling;
                        if (placeholder && placeholder.classList.contains('images-picker-card__placeholder')) {
                            placeholder.style.opacity = '0';
                            setTimeout(() => {
                                placeholder.style.display = 'none';
                            }, 200);
                        }
                    };
                    tempImg.onerror = () => {
                        img.style.opacity = '0';
                    };
                    tempImg.src = src;
                }
                
                pickerObserver.unobserve(img);
            }
        });
    }, {
        rootMargin: '50px'
    });
    
    const images = overlay.querySelectorAll('.images-picker-card__image[data-src]');
    images.forEach(img => {
        pickerObserver.observe(img);
    });
}

/**
 * Render image card for picker modal
 * @param {Object} image - Image object
 * @returns {string} HTML string
 */
function renderPickerImageCard(image) {
    const url = escapeHtml(image.url || '');
    const filename = escapeHtml(image.filename || '');
    
    return `
        <div class="images-picker-card" data-image-url="${url}">
            <div class="images-picker-card__placeholder"></div>
            <img 
                data-src="${url}" 
                alt="${filename}" 
                class="images-picker-card__image"
            >
            <div class="images-picker-card__overlay">
                <div class="images-picker-card__filename">${filename}</div>
            </div>
        </div>
    `;
}
