/**
 * Images Renderer Module
 * Core rendering functions for images grid.
 * Follows renderer pattern - accepts container and data, handles DOM only.
 */

import { deleteAdImage } from '/js/services/api-ad-images.js';
import { getImagesCache, getSelectedImageIds, toggleImageSelection, clearImageSelections, removeImagesFromCache, selectAllImages } from '/js/state/images-state.js';
import { escapeHtml } from '/js/utils/dom.js';

// Re-export from extracted modules for backward compatibility
export { showMediaPreview } from '/js/renderers/image-preview-renderer.js';
export { showImageUploadModal } from '/js/renderers/image-upload-modal.js';
export { showImagePickerModal } from '/js/renderers/image-picker-modal.js';

// Import for internal use
import { showMediaPreview } from '/js/renderers/image-preview-renderer.js';
import { showImageUploadModal as showUploadModal } from '/js/renderers/image-upload-modal.js';

/**
 * Generate a thumbnail URL for an image using wsrv.nl proxy
 * @param {string} url - Original image URL
 * @param {number} width - Desired width in pixels
 * @param {number} quality - Quality (1-100), default 80
 * @returns {string} Optimized thumbnail URL
 */
function getThumbnailUrl(url, width = 400, quality = 80) {
    if (!url || url.includes('video') || !url.match(/\.(jpg|jpeg|png|gif|webp)($|\?)/i)) {
        return url;
    }
    return `https://wsrv.nl/?url=${encodeURIComponent(url)}&w=${width}&q=${quality}&output=webp`;
}

// Store Masonry instance for cleanup/relayout
let masonryInstance = null;

let imageLoadLayoutTimeout = null;
const IMAGE_LOAD_LAYOUT_DELAY_MS = 120;
let lastSliderRelayoutTime = 0;
const SLIDER_COOLDOWN_MS = 600;

/** Debounced layout for image-load callbacks */
function scheduleLayoutFromImageLoad() {
    const timeSinceSlider = Date.now() - lastSliderRelayoutTime;
    if (timeSinceSlider < SLIDER_COOLDOWN_MS) {
        return;
    }
    
    if (imageLoadLayoutTimeout) clearTimeout(imageLoadLayoutTimeout);
    imageLoadLayoutTimeout = setTimeout(() => {
        imageLoadLayoutTimeout = null;
        const timeSinceSliderExec = Date.now() - lastSliderRelayoutTime;
        if (timeSinceSliderExec < SLIDER_COOLDOWN_MS) {
            return;
        }
        if (masonryInstance) {
            const grid = masonryInstance.element;
            grid.classList.add('images-grid--no-transition');
            masonryInstance.layout();
            setTimeout(() => {
                grid.classList.remove('images-grid--no-transition');
            }, 50);
        }
    }, IMAGE_LOAD_LAYOUT_DELAY_MS);
}

/**
 * Cancel any pending image-load-triggered layout
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
            <button class="images-empty__upload-btn" onclick="window.showImportMediaModal()">Upload Image</button>
        </div>
    `;
}

/**
 * Render grid of images
 * @param {HTMLElement} container - Container element
 * @param {Array} images - Array of image objects
 */
export function renderImagesGrid(container, images) {
    cancelScheduledLayoutFromImageLoad(false);
    if (masonryInstance) {
        masonryInstance.destroy();
        masonryInstance = null;
    }
    
    if (window.imagesIntersectionObserver) {
        window.imagesIntersectionObserver.disconnect();
        window.imagesIntersectionObserver = null;
    }
    
    if (!images || images.length === 0) {
        renderEmpty(container);
        return;
    }
    
    container.innerHTML = `
        <div class="images-grid-sizer"></div>
        <div class="images-gutter-sizer"></div>
        ${images.map(image => renderImageCard(image)).join('')}
    `;
    
    attachEventListeners(container);
    initLazyLoading(container);
    initMasonry(container);
}

/**
 * Initialize lazy loading with Intersection Observer
 * @param {HTMLElement} container - Grid container element
 */
function initLazyLoading(container) {
    if (typeof IntersectionObserver === 'undefined') {
        const media = container.querySelectorAll('.images-card__image[data-src]');
        media.forEach(el => {
            el.src = el.dataset.src;
            el.removeAttribute('data-src');
        });
        return;
    }
    
    window.imagesIntersectionObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const el = entry.target;
                const src = el.dataset.src;
                const isVideo = el.tagName === 'VIDEO';
                
                if (src) {
                    el.classList.add('images-card__image--loading');
                    
                    if (isVideo) {
                        el.src = src;
                        el.removeAttribute('data-src');
                        
                        el.onloadeddata = () => {
                            el.classList.remove('images-card__image--loading');
                            el.classList.add('images-card__image--loaded');
                            requestAnimationFrame(() => { el.style.opacity = '1'; });
                            
                            const placeholder = el.previousElementSibling;
                            if (placeholder?.classList.contains('images-card__placeholder')) {
                                placeholder.style.opacity = '0';
                                setTimeout(() => { placeholder.style.display = 'none'; }, 300);
                            }
                            
                            if (masonryInstance) scheduleLayoutFromImageLoad();
                        };
                        
                        el.onerror = () => {
                            el.classList.remove('images-card__image--loading');
                            el.classList.add('images-card__image--error');
                        };
                    } else {
                        const tempImg = new Image();
                        tempImg.onload = () => {
                            el.src = src;
                            el.removeAttribute('data-src');
                            el.classList.remove('images-card__image--loading');
                            el.classList.add('images-card__image--loaded');
                            requestAnimationFrame(() => { el.style.opacity = '1'; });
                            
                            const placeholder = el.previousElementSibling;
                            if (placeholder?.classList.contains('images-card__placeholder')) {
                                placeholder.style.opacity = '0';
                                setTimeout(() => { placeholder.style.display = 'none'; }, 300);
                            }
                            
                            if (masonryInstance) scheduleLayoutFromImageLoad();
                        };
                        tempImg.onerror = () => {
                            el.classList.remove('images-card__image--loading');
                            el.classList.add('images-card__image--error');
                        };
                        tempImg.src = src;
                    }
                }
                
                window.imagesIntersectionObserver.unobserve(el);
            }
        });
    }, { rootMargin: '100px' });
    
    const media = container.querySelectorAll('.images-card__image[data-src]');
    media.forEach(el => window.imagesIntersectionObserver.observe(el));
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
    
    container.classList.add('images-grid--no-transition');
    
    masonryInstance = new Masonry(container, {
        itemSelector: '.images-card',
        columnWidth: '.images-grid-sizer',
        gutter: '.images-gutter-sizer',
        percentPosition: true,
        horizontalOrder: true,
        transitionDuration: 0
    });
    
    const images = container.querySelectorAll('.images-card__image');
    let loadedCount = 0;
    const totalImages = images.length;
    
    if (totalImages === 0) return;
    
    images.forEach(img => {
        if (img.complete || img.classList.contains('images-card__image--loaded')) {
            loadedCount++;
            if (loadedCount === totalImages) scheduleLayoutFromImageLoad();
        } else if (!img.dataset.src) {
            img.addEventListener('load', () => {
                loadedCount++;
                if (loadedCount === totalImages) scheduleLayoutFromImageLoad();
            }, { once: true });
        } else {
            const checkLoad = () => {
                if (img.complete) {
                    loadedCount++;
                    if (loadedCount === totalImages) scheduleLayoutFromImageLoad();
                } else {
                    img.addEventListener('load', () => {
                        loadedCount++;
                        if (loadedCount === totalImages) scheduleLayoutFromImageLoad();
                    }, { once: true });
                }
            };
            
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
 */
export function relayoutImagesGrid() {
    if (masonryInstance) {
        const grid = masonryInstance.element;
        grid.classList.add('images-grid--no-transition');
        
        const sizer = grid.querySelector('.images-grid-sizer');
        if (sizer) void sizer.offsetWidth;
        
        masonryInstance.layout();
        
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
 * Format a date for display
 * @param {string} dateStr - ISO date string
 * @returns {string} Formatted date like "Jan 15, 2024"
 */
function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric', 
            year: 'numeric' 
        });
    } catch {
        return '';
    }
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
    
    // Meta Ads Library metadata
    const startedRunningOn = image.started_running_on;
    const libraryId = image.library_id;
    const hasMetaData = startedRunningOn || libraryId;
    
    const thumbnailUrl = isVideo ? url : getThumbnailUrl(image.url, 400, 80);
    
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
    
    // Build metadata section if we have Meta Ads data
    let metadataHtml = '';
    if (hasMetaData) {
        const dateHtml = startedRunningOn 
            ? `<span class="images-card__meta-date" title="Started running on">${formatDate(startedRunningOn)}</span>`
            : '';
        const idHtml = libraryId 
            ? `<span class="images-card__meta-library-id" title="Library ID: ${escapeHtml(libraryId)}">ID: ${escapeHtml(libraryId)}</span>`
            : '';
        metadataHtml = `<div class="images-card__meta-extra">${dateHtml}${idHtml}</div>`;
    }
    
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
                ${image.uploaded_at ? `<div class="images-card__meta images-card__meta-date-added" title="Date added to library">Added ${formatDate(image.uploaded_at)}</div>` : ''}
                ${metadataHtml}
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

/** True after user has clicked a checkbox at least once (shows bottom selection bar). */
let selectionModeActive = false;

/**
 * Attach event listeners using event delegation
 */
function attachEventListeners(container) {
    container.addEventListener('click', async (e) => {
        const checkbox = e.target.closest('.images-card__checkbox');
        if (checkbox && e.target.tagName !== 'INPUT') {
            e.stopPropagation();
            e.preventDefault();
            const imageId = checkbox.dataset.imageId;
            const isSelected = toggleImageSelection(imageId);
            
            const card = checkbox.closest('.images-card');
            if (card) card.classList.toggle('is-selected', isSelected);
            
            const input = checkbox.querySelector('input[type="checkbox"]');
            if (input) input.checked = isSelected;
            selectionModeActive = true;
            updateSelectionBar();
            return;
        }

        const imageCard = e.target.closest('.images-card');
        if (imageCard && !e.target.closest('.images-card__checkbox')) {
            const imageId = imageCard.dataset.imageId;
            const filename = imageCard.querySelector('.images-card__filename')?.textContent || '';
            const contentType = imageCard.dataset.contentType || '';
            const fullUrl = imageCard.dataset.fullUrl;
            const media = imageCard.querySelector('.images-card__image');
            const mediaUrl = fullUrl || media?.dataset?.fullSrc || media?.src || media?.dataset?.src;
            if (mediaUrl) {
                showMediaPreview(mediaUrl, filename, contentType, imageId);
            }
            return;
        }
    });

    container.addEventListener('change', (e) => {
        const input = e.target;
        if (input.type === 'checkbox' && input.closest('.images-card__checkbox')) {
            const checkbox = input.closest('.images-card__checkbox');
            const imageId = checkbox?.dataset.imageId;
            if (!imageId) return;
            const selected = getSelectedImageIds();
            const nowChecked = input.checked;
            if (nowChecked && !selected.has(imageId)) {
                toggleImageSelection(imageId);
            } else if (!nowChecked && selected.has(imageId)) {
                toggleImageSelection(imageId);
            }
            const card = checkbox.closest('.images-card');
            if (card) card.classList.toggle('is-selected', input.checked);
            selectionModeActive = true;
            updateSelectionBar();
        }
    });
}

/**
 * Update bottom selection bar visibility and button state
 */
function updateSelectionBar() {
    const cache = getImagesCache();
    const hasItems = cache.length > 0;
    const selectedIds = getSelectedImageIds();
    const selectedCount = selectedIds.size;
    const allSelected = hasItems && selectedCount === cache.length;

    const bar = document.getElementById('imagesSelectionBar');
    const selectDeselectBtn = document.getElementById('imagesSelectDeselectAllBtn');
    const deleteBtn = document.getElementById('imagesSelectionDeleteBtn');

    if (!bar || !selectDeselectBtn || !deleteBtn) return;

    if (selectionModeActive && hasItems) {
        bar.classList.add('is-visible');
        bar.setAttribute('aria-hidden', 'false');
        selectDeselectBtn.textContent = allSelected ? 'Deselect all' : 'Select all';
        deleteBtn.disabled = selectedCount === 0;
        const countSpan = deleteBtn.querySelector('.images-bulk-delete__count');
        if (countSpan) countSpan.textContent = selectedCount;
    } else {
        if (!hasItems) selectionModeActive = false;
        bar.classList.remove('is-visible');
        bar.setAttribute('aria-hidden', 'true');
    }
}

/** Kept for backward compatibility (controller / post-render). */
export function updateBulkDeleteButton() {
    updateSelectionBar();
}

/**
 * Select all images in the grid and update UI
 */
export function handleImagesSelectAll() {
    const cache = getImagesCache();
    if (cache.length === 0) return;
    selectionModeActive = true;
    selectAllImages();
    const container = document.getElementById('imagesGrid');
    if (container) {
        container.querySelectorAll('.images-card').forEach((card) => {
            card.classList.add('is-selected');
            const input = card.querySelector('.images-card__checkbox input[type="checkbox"]');
            if (input) input.checked = true;
        });
    }
    updateSelectionBar();
}

/**
 * Deselect all images and update UI
 */
export function handleImagesDeselectAll() {
    clearImageSelections();
    const container = document.getElementById('imagesGrid');
    if (container) {
        container.querySelectorAll('.images-card').forEach((card) => {
            card.classList.remove('is-selected');
            const input = card.querySelector('.images-card__checkbox input[type="checkbox"]');
            if (input) input.checked = false;
        });
    }
    updateSelectionBar();
}

/**
 * Toggle select all / deselect all (used by bottom bar button)
 */
export function handleImagesSelectDeselectAll() {
    const cache = getImagesCache();
    if (cache.length === 0) return;
    const allSelected = getSelectedImageIds().size === cache.length;
    if (allSelected) {
        handleImagesDeselectAll();
    } else {
        handleImagesSelectAll();
    }
}

/**
 * Delete all images in the library (with confirmation)
 */
export async function handleDeleteAllImages() {
    const cache = getImagesCache();
    if (cache.length === 0) return;
    const count = cache.length;
    if (!confirm(`Are you sure you want to delete all ${count} items? This cannot be undone.`)) return;

    const deleteAllBtn = document.getElementById('imagesDeleteAllBtn');
    const totalToDelete = cache.length;
    if (deleteAllBtn) {
        deleteAllBtn.classList.add('is-deleting');
        deleteAllBtn.textContent = totalToDelete === 1 ? 'Deleting…' : `Deleting 0 of ${totalToDelete}…`;
    }

    const allIds = cache.map((img) => img.id);
    let successCount = 0;
    let failCount = 0;

    for (let i = 0; i < allIds.length; i++) {
        const imageId = allIds[i];
        try {
            await deleteAdImage(imageId);
            successCount++;
        } catch (error) {
            console.error(`[ImagesRenderer] Failed to delete ${imageId}:`, error);
            failCount++;
        }
        if (deleteAllBtn && totalToDelete > 1) {
            deleteAllBtn.textContent = `Deleting ${i + 1} of ${totalToDelete}…`;
        }
    }

    removeImagesFromCache(allIds);
    clearImageSelections();

    if (window.renderImagesPage) window.renderImagesPage();
    updateBulkDeleteButton();

    if (deleteAllBtn) {
        deleteAllBtn.classList.remove('is-deleting');
        deleteAllBtn.textContent = 'Delete all';
    }

    if (failCount > 0) {
        alert(`Deleted ${successCount}, failed to delete ${failCount}`);
    }
}

/** Default bulk delete button content (restored after progress). */
const BULK_DELETE_BTN_HTML = '<img src="/images/delete_button.png" alt="Delete" width="18" height="18"><span>Delete</span><span class="images-bulk-delete__count">0</span>';

/**
 * Handle bulk delete of selected images
 */
export async function handleBulkDelete() {
    const selectedIds = Array.from(getSelectedImageIds());
    
    if (selectedIds.length === 0) return;
    
    const confirmMsg = selectedIds.length === 1 
        ? 'Are you sure you want to delete this item?' 
        : `Are you sure you want to delete ${selectedIds.length} items?`;
    
    if (!confirm(confirmMsg)) return;

    const deleteBtn = document.getElementById('imagesSelectionDeleteBtn');
    const total = selectedIds.length;
    if (deleteBtn) {
        deleteBtn.classList.add('is-deleting');
        deleteBtn.textContent = total === 1 ? 'Deleting…' : `Deleting 0 of ${total}…`;
    }
    
    let successCount = 0;
    let failCount = 0;
    
    for (let i = 0; i < selectedIds.length; i++) {
        const imageId = selectedIds[i];
        try {
            await deleteAdImage(imageId);
            successCount++;
        } catch (error) {
            console.error(`[ImagesRenderer] Failed to delete ${imageId}:`, error);
            failCount++;
        }
        if (deleteBtn && total > 1) {
            deleteBtn.textContent = `Deleting ${i + 1} of ${total}…`;
        }
    }
    
    removeImagesFromCache(selectedIds);
    clearImageSelections();
    
    if (window.renderImagesPage) window.renderImagesPage();
    
    if (deleteBtn) {
        deleteBtn.classList.remove('is-deleting');
        deleteBtn.innerHTML = BULK_DELETE_BTN_HTML;
    }
    updateBulkDeleteButton();

    if (failCount > 0) {
        alert(`Deleted ${successCount}, failed to delete ${failCount}`);
    }
}

/**
 * Append a single image card to the grid without re-rendering everything
 * @param {HTMLElement} container - Grid container element
 * @param {Object} image - Image object from API
 */
export function appendImageToGrid(container, image) {
    if (container.querySelector('.images-empty')) {
        container.innerHTML = `
            <div class="images-grid-sizer"></div>
            <div class="images-gutter-sizer"></div>
        `;
        
        if (typeof Masonry !== 'undefined') {
            if (masonryInstance) masonryInstance.destroy();
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
    
    const cardHtml = renderImageCard(image);
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = cardHtml;
    const newCard = tempDiv.firstElementChild;
    
    const firstCard = container.querySelector('.images-card');
    if (firstCard) {
        container.insertBefore(newCard, firstCard);
    } else {
        container.appendChild(newCard);
    }
    
    const mediaEl = newCard.querySelector('.images-card__image[data-src]');
    if (mediaEl && window.imagesIntersectionObserver) {
        window.imagesIntersectionObserver.observe(mediaEl);
    } else if (mediaEl) {
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
    
    if (masonryInstance) {
        masonryInstance.prepended(newCard);
        scheduleLayoutFromImageLoad();
    }
    
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
            const imageId = newCard.dataset.imageId;
            const filename = newCard.querySelector('.images-card__filename')?.textContent || '';
            const contentType = newCard.dataset.contentType || '';
            const fullUrl = newCard.dataset.fullUrl;
            const media = newCard.querySelector('.images-card__image');
            const mediaUrl = fullUrl || media?.dataset?.fullSrc || media?.src || media?.dataset?.src;
            if (mediaUrl) {
                showMediaPreview(mediaUrl, filename, contentType, imageId);
            }
        }
    });
    updateBulkDeleteButton();
}

/**
 * Wrapper for upload modal that handles appending to grid
 */
export function showImageUploadModalWithGridUpdate() {
    const container = document.getElementById('imagesGrid');
    showUploadModal((image) => {
        if (container) {
            appendImageToGrid(container, image);
        }
    });
}
