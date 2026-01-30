/**
 * Image Picker Modal Module
 * Handles media picker modal for selecting images/videos from library.
 */

import { getImagesCache } from '/js/state/images-state.js';
import { escapeHtml } from '/js/utils/dom.js';

// Store current image picker callback
let imagePickerCallback = null;

/**
 * Generate a thumbnail URL for an image using wsrv.nl proxy
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
    return `https://wsrv.nl/?url=${encodeURIComponent(url)}&w=${width}&q=${quality}&output=webp`;
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
