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
    if (!images || images.length === 0) {
        renderEmpty(container);
        return;
    }
    
    // Container already has class="images-grid", so just add the cards directly
    const cardsHtml = images.map(image => renderImageCard(image)).join('');
    container.innerHTML = cardsHtml;
    
    // Attach event listeners
    attachEventListeners(container);
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
                <img src="${url}" alt="${filename}" class="images-card__image" loading="lazy">
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
    });
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
                <button class="images-picker-modal__close" onclick="this.closest('.images-picker-overlay').remove()">×</button>
            </div>
            <div class="images-picker-modal__body">
                <div class="images-picker-grid">
                    ${images.map(image => renderPickerImageCard(image)).join('')}
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(overlay);
    
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
        }
        
        // Close on overlay or close button click
        if (e.target.classList.contains('images-picker-modal__close') || e.target === overlay) {
            overlay.remove();
            imagePickerCallback = null;
        }
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
            <img src="${url}" alt="${filename}" class="images-picker-card__image" loading="lazy">
            <div class="images-picker-card__overlay">
                <div class="images-picker-card__filename">${filename}</div>
            </div>
        </div>
    `;
}
