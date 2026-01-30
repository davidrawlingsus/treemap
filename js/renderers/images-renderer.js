/**
 * Images Renderer Module
 * Pure rendering functions for images grid and image picker modal.
 * Follows renderer pattern - accepts container and data, handles DOM only.
 */

import { deleteAdImage } from '/js/services/api-ad-images.js';
import { getImagesCache, getSelectedImageIds, toggleImageSelection, clearImageSelections, removeImagesFromCache } from '/js/state/images-state.js';
import { escapeHtml } from '/js/utils/dom.js';

/**
 * Generate a thumbnail URL for an image using wsrv.nl proxy
 * This provides on-the-fly image optimization without needing server-side processing
 * @param {string} url - Original image URL
 * @param {number} width - Desired width in pixels
 * @param {number} quality - Quality (1-100), default 80
 * @returns {string} Optimized thumbnail URL
 */
function getThumbnailUrl(url, width = 400, quality = 80) {
    // Skip if not an image URL or if it's a video
    if (!url || url.includes('video') || !url.match(/\.(jpg|jpeg|png|gif|webp)($|\?)/i)) {
        return url;
    }
    
    // Use wsrv.nl (free image proxy service) for thumbnail generation
    // Docs: https://wsrv.nl/
    return `https://wsrv.nl/?url=${encodeURIComponent(url)}&w=${width}&q=${quality}&output=webp`;
}

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
 * Only loads media when they're about to enter the viewport
 * @param {HTMLElement} container - Grid container element
 */
function initLazyLoading(container) {
    // Check if Intersection Observer is supported
    if (typeof IntersectionObserver === 'undefined') {
        // Fallback: load all media immediately
        const media = container.querySelectorAll('.images-card__image[data-src]');
        media.forEach(el => {
            el.src = el.dataset.src;
            el.removeAttribute('data-src');
        });
        return;
    }
    
    // Create intersection observer with root margin for preloading
    // Load media 100px before they enter viewport
    window.imagesIntersectionObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const el = entry.target;
                const src = el.dataset.src;
                const isVideo = el.tagName === 'VIDEO';
                
                if (src) {
                    // Add loading class
                    el.classList.add('images-card__image--loading');
                    
                    if (isVideo) {
                        // For videos, just set the src and listen for loadeddata
                        el.src = src;
                        el.removeAttribute('data-src');
                        
                        el.onloadeddata = () => {
                            el.classList.remove('images-card__image--loading');
                            el.classList.add('images-card__image--loaded');
                            
                            requestAnimationFrame(() => {
                                el.style.opacity = '1';
                            });
                            
                            // Hide placeholder
                            const placeholder = el.previousElementSibling;
                            if (placeholder && placeholder.classList.contains('images-card__placeholder')) {
                                placeholder.style.opacity = '0';
                                setTimeout(() => {
                                    placeholder.style.display = 'none';
                                }, 300);
                            }
                            
                            if (masonryInstance) {
                                scheduleLayoutFromImageLoad();
                            }
                        };
                        
                        el.onerror = () => {
                            el.classList.remove('images-card__image--loading');
                            el.classList.add('images-card__image--error');
                        };
                    } else {
                        // For images, preload then set src
                        const tempImg = new Image();
                        tempImg.onload = () => {
                            el.src = src;
                            el.removeAttribute('data-src');
                            el.classList.remove('images-card__image--loading');
                            el.classList.add('images-card__image--loaded');
                            
                            requestAnimationFrame(() => {
                                el.style.opacity = '1';
                            });
                            
                            // Hide placeholder with fade out
                            const placeholder = el.previousElementSibling;
                            if (placeholder && placeholder.classList.contains('images-card__placeholder')) {
                                placeholder.style.opacity = '0';
                                setTimeout(() => {
                                    placeholder.style.display = 'none';
                                }, 300);
                            }
                            
                            // Trigger Masonry relayout
                            if (masonryInstance) {
                                scheduleLayoutFromImageLoad();
                            }
                        };
                        tempImg.onerror = () => {
                            el.classList.remove('images-card__image--loading');
                            el.classList.add('images-card__image--error');
                        };
                        tempImg.src = src;
                    }
                }
                
                // Stop observing once loaded
                window.imagesIntersectionObserver.unobserve(el);
            }
        });
    }, {
        rootMargin: '100px' // Start loading 100px before media enters viewport
    });
    
    // Observe all media with data-src
    const media = container.querySelectorAll('.images-card__image[data-src]');
    media.forEach(el => {
        window.imagesIntersectionObserver.observe(el);
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
 * Check if content type is video
 * @param {string} contentType - MIME type
 * @returns {boolean}
 */
function isVideoType(contentType) {
    return contentType?.startsWith('video/');
}

/**
 * Render single image/video card
 * @param {Object} image - Image/video object from API
 * @returns {string} HTML string
 */
function renderImageCard(image) {
    const id = escapeHtml(image.id || '');
    const url = escapeHtml(image.url || '');
    const filename = escapeHtml(image.filename || '');
    const contentType = image.content_type || '';
    const isVideo = isVideoType(contentType);
    const isSelected = getSelectedImageIds().has(image.id);
    
    // Use thumbnail for grid view (faster loading), keep full URL for preview
    const thumbnailUrl = isVideo ? url : getThumbnailUrl(image.url, 400, 80);
    
    // For videos, render video element with poster; for images, render img with thumbnail
    const mediaElement = isVideo ? `
        <video 
            data-src="${url}" 
            class="images-card__image images-card__video" 
            muted 
            preload="metadata"
        ></video>
        <div class="images-card__play-icon">▶</div>
    ` : `
        <img 
            data-src="${escapeHtml(thumbnailUrl)}" 
            data-full-src="${url}"
            alt="${filename}" 
            class="images-card__image" 
            loading="lazy"
        >
    `;
    
    return `
        <div class="images-card${isSelected ? ' is-selected' : ''}" data-image-id="${id}" data-content-type="${escapeHtml(contentType)}" data-full-url="${url}">
            <div class="images-card__image-wrapper">
                <div class="images-card__placeholder"></div>
                ${mediaElement}
                <label class="images-card__checkbox" data-image-id="${id}">
                    <input type="checkbox" ${isSelected ? 'checked' : ''}>
                    <span class="images-card__checkbox-mark"></span>
                </label>
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
        // Handle checkbox click - but skip if click is directly on INPUT (label click already handles it)
        const checkbox = e.target.closest('.images-card__checkbox');
        if (checkbox && e.target.tagName !== 'INPUT') {
            e.stopPropagation();
            e.preventDefault(); // Prevent the label from also triggering input click
            const imageId = checkbox.dataset.imageId;
            const isSelected = toggleImageSelection(imageId);
            
            // Update card visual state
            const card = checkbox.closest('.images-card');
            if (card) {
                card.classList.toggle('is-selected', isSelected);
            }
            
            // Update checkbox input
            const input = checkbox.querySelector('input[type="checkbox"]');
            if (input) {
                input.checked = isSelected;
            }
            
            // Update delete button visibility in control bar
            updateBulkDeleteButton();
            return;
        }
        
        // Handle image/video card click (show preview) - but not if clicking checkbox
        const imageCard = e.target.closest('.images-card');
        if (imageCard && !e.target.closest('.images-card__checkbox')) {
            const filename = imageCard.querySelector('.images-card__filename')?.textContent || '';
            const contentType = imageCard.dataset.contentType || '';
            // Use full URL from data attribute (not thumbnail)
            const fullUrl = imageCard.dataset.fullUrl;
            const media = imageCard.querySelector('.images-card__image');
            // Fall back to media src if full URL not available
            const mediaUrl = fullUrl || media?.dataset?.fullSrc || media?.src || media?.dataset?.src;
            if (mediaUrl) {
                showMediaPreview(mediaUrl, filename, contentType);
            }
            return;
        }
    });
}

/**
 * Update bulk delete button visibility based on selection
 */
export function updateBulkDeleteButton() {
    const deleteBtn = document.getElementById('imagesBulkDeleteBtn');
    const selectedCount = getSelectedImageIds().size;
    
    if (deleteBtn) {
        if (selectedCount > 0) {
            deleteBtn.style.display = 'flex';
            const countSpan = deleteBtn.querySelector('.images-bulk-delete__count');
            if (countSpan) {
                countSpan.textContent = selectedCount;
            }
        } else {
            deleteBtn.style.display = 'none';
        }
    }
}

/**
 * Handle bulk delete of selected images
 */
export async function handleBulkDelete() {
    const selectedIds = Array.from(getSelectedImageIds());
    
    if (selectedIds.length === 0) {
        return;
    }
    
    const confirmMsg = selectedIds.length === 1 
        ? 'Are you sure you want to delete this item?' 
        : `Are you sure you want to delete ${selectedIds.length} items?`;
    
    if (!confirm(confirmMsg)) {
        return;
    }
    
    // Show progress
    const deleteBtn = document.getElementById('imagesBulkDeleteBtn');
    if (deleteBtn) {
        deleteBtn.classList.add('is-deleting');
    }
    
    let successCount = 0;
    let failCount = 0;
    
    for (const imageId of selectedIds) {
        try {
            await deleteAdImage(imageId);
            successCount++;
        } catch (error) {
            console.error(`[ImagesRenderer] Failed to delete ${imageId}:`, error);
            failCount++;
        }
    }
    
    // Remove from cache
    removeImagesFromCache(selectedIds);
    clearImageSelections();
    
    // Re-render
    if (window.renderImagesPage) {
        window.renderImagesPage();
    }
    
    // Update button
    updateBulkDeleteButton();
    
    if (deleteBtn) {
        deleteBtn.classList.remove('is-deleting');
    }
    
    // Show result
    if (failCount > 0) {
        alert(`Deleted ${successCount}, failed to delete ${failCount}`);
    }
}

/**
 * Show media preview overlay (image or video)
 * @param {string} mediaUrl - URL of the media to preview
 * @param {string} filename - Filename for display
 * @param {string} contentType - MIME type of the media
 */
function showMediaPreview(mediaUrl, filename, contentType) {
    // Remove any existing preview overlay
    const existing = document.querySelector('.images-preview-overlay');
    if (existing) {
        existing.remove();
    }
    
    const isVideo = isVideoType(contentType);
    
    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'images-preview-overlay';
    
    const mediaElement = isVideo ? `
        <video 
            src="${escapeHtml(mediaUrl)}" 
            class="images-preview-video"
            controls
            autoplay
        >
            Your browser does not support video playback.
        </video>
    ` : `
        <img 
            src="${escapeHtml(mediaUrl)}" 
            alt="${escapeHtml(filename)}" 
            class="images-preview-image"
        >
    `;
    
    overlay.innerHTML = `
        <div class="images-preview-container">
            <button class="images-preview-close" aria-label="Close preview">×</button>
            <div class="images-preview-media-wrapper">
                <div class="images-preview-loading">Loading...</div>
                ${mediaElement}
            </div>
            <div class="images-preview-filename">${escapeHtml(filename)}</div>
        </div>
    `;
    
    document.body.appendChild(overlay);
    
    // Prevent body scroll while overlay is open
    document.body.style.overflow = 'hidden';
    
    const loading = overlay.querySelector('.images-preview-loading');
    
    if (isVideo) {
        // Handle video load
        const video = overlay.querySelector('.images-preview-video');
        
        video.onloadeddata = () => {
            loading.style.display = 'none';
            video.classList.add('is-loaded');
        };
        
        video.onerror = () => {
            loading.textContent = 'Failed to load video';
        };
    } else {
        // Handle image load
        const img = overlay.querySelector('.images-preview-image');
        
        img.onload = () => {
            loading.style.display = 'none';
            img.classList.add('is-loaded');
        };
        
        img.onerror = () => {
            loading.textContent = 'Failed to load image';
        };
    }
    
    // Animate in
    requestAnimationFrame(() => {
        overlay.classList.add('is-visible');
    });
    
    // Close handlers
    const closeOverlay = () => {
        // Pause video if playing
        const video = overlay.querySelector('.images-preview-video');
        if (video) {
            video.pause();
        }
        
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
 * Append a single image card to the grid without re-rendering everything
 * @param {HTMLElement} container - Grid container element
 * @param {Object} image - Image object from API
 */
export function appendImageToGrid(container, image) {
    // If the grid is showing empty state, we need to initialize it first
    if (container.querySelector('.images-empty')) {
        // Need to set up the grid structure first
        container.innerHTML = `
            <div class="images-grid-sizer"></div>
            <div class="images-gutter-sizer"></div>
        `;
        
        // Initialize Masonry if available
        if (typeof Masonry !== 'undefined') {
            if (masonryInstance) {
                masonryInstance.destroy();
            }
            masonryInstance = new Masonry(container, {
                itemSelector: '.images-card',
                columnWidth: '.images-grid-sizer',
                gutter: '.images-gutter-sizer',
                percentPosition: true,
                horizontalOrder: true,
                transitionDuration: 0
            });
        }
    }
    
    // Create the new card element
    const cardHtml = renderImageCard(image);
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = cardHtml;
    const newCard = tempDiv.firstElementChild;
    
    // Insert at the beginning (after sizer elements)
    const firstCard = container.querySelector('.images-card');
    if (firstCard) {
        container.insertBefore(newCard, firstCard);
    } else {
        container.appendChild(newCard);
    }
    
    // Set up lazy loading for this single card
    const mediaEl = newCard.querySelector('.images-card__image[data-src]');
    if (mediaEl && window.imagesIntersectionObserver) {
        window.imagesIntersectionObserver.observe(mediaEl);
    } else if (mediaEl) {
        // No observer, load immediately
        const src = mediaEl.dataset.src;
        if (src) {
            if (mediaEl.tagName === 'VIDEO') {
                mediaEl.src = src;
            } else {
                const tempImg = new Image();
                tempImg.onload = () => {
                    mediaEl.src = src;
                    mediaEl.classList.add('images-card__image--loaded');
                    mediaEl.style.opacity = '1';
                    const placeholder = mediaEl.previousElementSibling;
                    if (placeholder?.classList.contains('images-card__placeholder')) {
                        placeholder.style.display = 'none';
                    }
                };
                tempImg.src = src;
            }
            mediaEl.removeAttribute('data-src');
        }
    }
    
    // Update Masonry layout if available
    if (masonryInstance) {
        masonryInstance.prepended(newCard);
        // Schedule a relayout after the image loads
        scheduleLayoutFromImageLoad();
    }
    
    // Attach click handlers to the new card
    newCard.addEventListener('click', (e) => {
        const checkbox = e.target.closest('.images-card__checkbox');
        if (checkbox && e.target.tagName !== 'INPUT') {
            e.stopPropagation();
            e.preventDefault();
            const imageId = checkbox.dataset.imageId;
            const isSelected = toggleImageSelection(imageId);
            newCard.classList.toggle('is-selected', isSelected);
            const input = checkbox.querySelector('input[type="checkbox"]');
            if (input) input.checked = isSelected;
            updateBulkDeleteButton();
            return;
        }
        
        if (!e.target.closest('.images-card__checkbox')) {
            const filename = newCard.querySelector('.images-card__filename')?.textContent || '';
            const contentType = newCard.dataset.contentType || '';
            // Use full URL from data attribute (not thumbnail)
            const fullUrl = newCard.dataset.fullUrl;
            const media = newCard.querySelector('.images-card__image');
            const mediaUrl = fullUrl || media?.dataset?.fullSrc || media?.src || media?.dataset?.src;
            if (mediaUrl) {
                showMediaPreview(mediaUrl, filename, contentType);
            }
        }
    });
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
                <h2>Upload Media</h2>
                <button class="images-upload-modal__close" onclick="this.closest('.images-upload-overlay').remove()">×</button>
            </div>
            <div class="images-upload-modal__body">
                <input type="file" id="imageUploadInput" accept="image/*,video/*" multiple style="display: none;">
                <div class="images-upload-dropzone" id="imageUploadDropzone">
                    <div class="images-upload-dropzone__content">
                        <div class="images-upload-dropzone__icon">📤</div>
                        <p>Click to select or drag and drop</p>
                        <p class="images-upload-dropzone__hint">Supports images and videos up to 50MB</p>
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
                await handleMediaUpload(files[0], clientId, overlay, progress, progressBar);
            } else {
                await handleBulkMediaUpload(files, clientId, overlay, progress, progressBar);
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
        const files = Array.from(e.dataTransfer.files).filter(f => 
            f.type.startsWith('image/') || f.type.startsWith('video/')
        );
        if (files.length > 0) {
            if (files.length === 1) {
                await handleMediaUpload(files[0], clientId, overlay, progress, progressBar);
            } else {
                await handleBulkMediaUpload(files, clientId, overlay, progress, progressBar);
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
 * Handle media upload (image or video)
 */
async function handleMediaUpload(file, clientId, overlay, progress, progressBar) {
    if (!file.type.startsWith('image/') && !file.type.startsWith('video/')) {
        alert('Please select an image or video file');
        return;
    }
    
    // Check file size (50MB limit for server uploads)
    const MAX_SIZE = 50 * 1024 * 1024; // 50MB
    if (file.size > MAX_SIZE) {
        alert(`File is too large. Maximum size is 50MB. Your file is ${formatFileSize(file.size)}.`);
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
        
        // Append to grid without full re-render
        const container = document.getElementById('imagesGrid');
        if (container) {
            appendImageToGrid(container, image);
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
 * Handle bulk media upload (images and videos)
 */
async function handleBulkMediaUpload(files, clientId, overlay, progress, progressBar) {
    progress.style.display = 'block';
    progressBar.style.width = '0%';
    
    const { uploadAdImage } = await import('/js/services/api-ad-images.js');
    const { addImageToCache } = await import('/js/state/images-state.js');
    
    // Check file sizes (50MB limit)
    const MAX_SIZE = 50 * 1024 * 1024; // 50MB
    const oversizedFiles = files.filter(f => f.size > MAX_SIZE);
    if (oversizedFiles.length > 0) {
        const names = oversizedFiles.map(f => `${f.name} (${formatFileSize(f.size)})`).join(', ');
        alert(`Some files are too large (max 50MB): ${names}`);
        // Filter out oversized files
        files = files.filter(f => f.size <= MAX_SIZE);
        if (files.length === 0) {
            progress.style.display = 'none';
            return;
        }
    }
    
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
            
            // Append to grid immediately without waiting for all uploads
            const container = document.getElementById('imagesGrid');
            if (container) {
                appendImageToGrid(container, image);
            }
            
            successCount++;
        } catch (error) {
            failCount++;
            errors.push(`${file.name}: ${error.message}`);
        }
    }
    
    progressBar.style.width = '100%';
    
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
 * Show media picker modal for selecting an image or video for an ad
 * @param {Function} onSelect - Callback function with selected media URL
 */
export function showImagePickerModal(onSelect) {
    // Remove any existing overlays first to prevent stacking
    const existingOverlays = document.querySelectorAll('.images-picker-overlay');
    existingOverlays.forEach(overlay => {
        overlay.remove();
    });
    document.body.classList.remove('picker-open');
    
    imagePickerCallback = onSelect;
    
    const images = getImagesCache();
    
    if (images.length === 0) {
        alert('No media available. Please upload images or videos first.');
        return;
    }
    
    // Create modal overlay
    const overlay = document.createElement('div');
    overlay.className = 'images-picker-overlay';
    overlay.innerHTML = `
        <div class="images-picker-modal">
            <div class="images-picker-modal__header">
                <h2>Select Media</h2>
                <button class="images-picker-modal__close">×</button>
            </div>
            <div class="images-picker-modal__body">
                <div class="images-picker-grid">
                    ${images.map(image => renderPickerMediaCard(image)).join('')}
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(overlay);
    document.body.classList.add('picker-open');
    
    // Initialize lazy loading for picker images
    initPickerLazyLoading(overlay);
    
    // Helper to close modal and restore scroll
    const closeModal = () => {
        overlay.remove();
        document.body.classList.remove('picker-open');
        imagePickerCallback = null;
    };
    
    // Attach click handlers
    overlay.addEventListener('click', (e) => {
        const imageCard = e.target.closest('.images-picker-card');
        if (imageCard) {
            const imageUrl = imageCard.dataset.imageUrl;
            if (imageUrl && imagePickerCallback) {
                imagePickerCallback(imageUrl);
            }
            closeModal();
            return;
        }
        
        // Close on overlay background or close button click
        if (e.target.classList.contains('images-picker-modal__close') || e.target === overlay) {
            closeModal();
        }
    });
}

/**
 * Initialize lazy loading for picker modal media (images and videos)
 * @param {HTMLElement} overlay - Modal overlay element
 */
function initPickerLazyLoading(overlay) {
    if (typeof IntersectionObserver === 'undefined') {
        // Fallback: load all media immediately
        const media = overlay.querySelectorAll('.images-picker-card__image[data-src], .images-picker-card__video[data-src]');
        media.forEach(el => {
            el.src = el.dataset.src;
            el.removeAttribute('data-src');
        });
        return;
    }
    
    const pickerObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const el = entry.target;
                const src = el.dataset.src;
                const isVideo = el.tagName === 'VIDEO';
                
                if (src) {
                    if (isVideo) {
                        // For videos, just set src and listen for loadeddata
                        el.src = src;
                        el.removeAttribute('data-src');
                        
                        el.onloadeddata = () => {
                            el.style.opacity = '1';
                            // Hide placeholder
                            const placeholder = el.previousElementSibling;
                            if (placeholder && placeholder.classList.contains('images-picker-card__placeholder')) {
                                placeholder.style.opacity = '0';
                                setTimeout(() => {
                                    placeholder.style.display = 'none';
                                }, 200);
                            }
                        };
                        el.onerror = () => {
                            el.style.opacity = '0';
                        };
                    } else {
                        // For images, preload then set src
                        const tempImg = new Image();
                        tempImg.onload = () => {
                            el.src = src;
                            el.removeAttribute('data-src');
                            el.style.opacity = '1';
                            
                            // Hide placeholder
                            const placeholder = el.previousElementSibling;
                            if (placeholder && placeholder.classList.contains('images-picker-card__placeholder')) {
                                placeholder.style.opacity = '0';
                                setTimeout(() => {
                                    placeholder.style.display = 'none';
                                }, 200);
                            }
                        };
                        tempImg.onerror = () => {
                            el.style.opacity = '0';
                        };
                        tempImg.src = src;
                    }
                }
                
                pickerObserver.unobserve(el);
            }
        });
    }, {
        rootMargin: '50px'
    });
    
    const media = overlay.querySelectorAll('.images-picker-card__image[data-src], .images-picker-card__video[data-src]');
    media.forEach(el => {
        pickerObserver.observe(el);
    });
}

/**
 * Render media card for picker modal (image or video)
 * @param {Object} media - Media object
 * @returns {string} HTML string
 */
function renderPickerMediaCard(media) {
    const url = escapeHtml(media.url || '');
    const filename = escapeHtml(media.filename || '');
    const contentType = media.content_type || '';
    const isVideo = contentType.startsWith('video/');
    
    // Use thumbnail for picker (faster loading), but return full URL on selection
    const thumbnailUrl = isVideo ? url : getThumbnailUrl(media.url, 300, 75);
    
    const mediaElement = isVideo ? `
        <video 
            data-src="${url}" 
            class="images-picker-card__video"
            muted
            preload="metadata"
        ></video>
        <div class="images-picker-card__play-icon">▶</div>
    ` : `
        <img 
            data-src="${escapeHtml(thumbnailUrl)}" 
            alt="${filename}" 
            class="images-picker-card__image"
        >
    `;
    
    return `
        <div class="images-picker-card" data-image-url="${url}" data-content-type="${escapeHtml(contentType)}">
            <div class="images-picker-card__placeholder"></div>
            ${mediaElement}
            <div class="images-picker-card__overlay">
                <div class="images-picker-card__filename">${filename}</div>
            </div>
        </div>
    `;
}
