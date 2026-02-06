/**
 * Image Preview Renderer Module
 * Handles full-screen media preview overlay with keyboard navigation.
 */

import { getImagesCache } from '/js/state/images-state.js';
import { escapeHtml } from '/js/utils/dom.js';

// Track current preview index for navigation
let currentPreviewIndex = -1;

/**
 * Check if content type is video
 * @param {string} contentType - MIME type
 * @returns {boolean}
 */
function isVideoType(contentType) {
    return contentType?.startsWith('video/');
}

/**
 * Show media preview overlay (image or video) with keyboard navigation
 * @param {string} mediaUrl - URL of the media to preview
 * @param {string} filename - Filename for display
 * @param {string} contentType - MIME type of the media
 * @param {string} [imageId] - Optional image ID for navigation
 */
export function showMediaPreview(mediaUrl, filename, contentType, imageId) {
    // Remove any existing preview overlay
    const existing = document.querySelector('.images-preview-overlay');
    if (existing) {
        existing.remove();
    }
    
    // Find current index in cache for navigation
    const images = getImagesCache();
    if (imageId) {
        currentPreviewIndex = images.findIndex(img => img.id === imageId);
    } else {
        // Try to find by URL
        currentPreviewIndex = images.findIndex(img => img.url === mediaUrl);
    }

    const isVideo = isVideoType(contentType);
    const hasMultipleImages = images.length > 1;
    
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
    
    // Navigation buttons (only show if multiple images)
    const navButtons = hasMultipleImages ? `
        <button class="images-preview-nav images-preview-nav--prev" aria-label="Previous image">
            <span>‹</span>
        </button>
        <button class="images-preview-nav images-preview-nav--next" aria-label="Next image">
            <span>›</span>
        </button>
    ` : '';
    
    // Counter display
    const counter = hasMultipleImages && currentPreviewIndex >= 0 ? `
        <div class="images-preview-counter">${currentPreviewIndex + 1} / ${images.length}</div>
    ` : '';
    
    overlay.innerHTML = `
        <div class="images-preview-container">
            <button class="images-preview-close" aria-label="Close preview">×</button>
            ${navButtons}
            <div class="images-preview-media-wrapper">
                <div class="images-preview-loading">Loading...</div>
                ${mediaElement}
            </div>
            <div class="images-preview-footer">
                <div class="images-preview-filename">${escapeHtml(filename)}</div>
                ${counter}
            </div>
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
    
    // Navigation function - use current cache (not closure) so brand switch works correctly
    const navigatePreview = (direction) => {
        const currentCache = getImagesCache();
        if (currentCache.length <= 1) return;

        const mediaEl = overlay.querySelector('.images-preview-image, .images-preview-video');
        const displayedSrc = mediaEl?.src || mediaEl?.currentSrc || '';
        if (!displayedSrc) return;

        // Find current index in the current cache by matching displayed URL or filename
        const idx = currentCache.findIndex(img =>
            (img.url && (displayedSrc.endsWith(img.url) || displayedSrc.includes(img.url))) ||
            (img.filename && displayedSrc.endsWith(img.filename))
        );
        if (idx < 0) return;

        let newIndex = idx + direction;
        if (newIndex < 0) newIndex = currentCache.length - 1;
        if (newIndex >= currentCache.length) newIndex = 0;

        const newImage = currentCache[newIndex];
        if (newImage) {
            overlay.remove();
            document.removeEventListener('keydown', handleKeydown);
            showMediaPreview(newImage.url, newImage.filename, newImage.content_type, newImage.id);
        }
    };
    
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
    
    // Close on background click, handle nav button clicks
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay || e.target.classList.contains('images-preview-close')) {
            closeOverlay();
        }
        // Navigation buttons
        if (e.target.closest('.images-preview-nav--prev')) {
            navigatePreview(-1);
        }
        if (e.target.closest('.images-preview-nav--next')) {
            navigatePreview(1);
        }
    });
    
    // Keyboard navigation: Escape to close, Left/Right arrows to navigate
    const handleKeydown = (e) => {
        if (e.key === 'Escape') {
            closeOverlay();
            document.removeEventListener('keydown', handleKeydown);
        } else if (e.key === 'ArrowLeft') {
            e.preventDefault();
            navigatePreview(-1);
        } else if (e.key === 'ArrowRight') {
            e.preventDefault();
            navigatePreview(1);
        }
    };
    document.addEventListener('keydown', handleKeydown);
    
    // Preload adjacent images for smoother navigation
    preloadAdjacentImages(currentPreviewIndex, images, 2);
}

/**
 * Preload images adjacent to the current one for faster navigation
 * @param {number} currentIndex - Current image index
 * @param {Array} images - Array of all images
 * @param {number} range - Number of images to preload in each direction
 */
function preloadAdjacentImages(currentIndex, images, range = 2) {
    if (currentIndex < 0 || images.length <= 1) return;
    
    const indicesToPreload = [];
    
    // Collect indices to preload (previous and next)
    for (let i = 1; i <= range; i++) {
        // Previous images
        let prevIndex = currentIndex - i;
        if (prevIndex < 0) prevIndex = images.length + prevIndex; // Wrap around
        indicesToPreload.push(prevIndex);
        
        // Next images
        let nextIndex = currentIndex + i;
        if (nextIndex >= images.length) nextIndex = nextIndex - images.length; // Wrap around
        indicesToPreload.push(nextIndex);
    }
    
    // Preload each image
    indicesToPreload.forEach(index => {
        const image = images[index];
        if (image && image.url && !isVideoType(image.content_type)) {
            const preloadImg = new Image();
            preloadImg.src = image.url;
        }
    });
}
