/**
 * Images Controller Module
 * Page-level orchestration for Images tab: loading, rendering.
 * Follows controller pattern - coordinates between state, services, and renderers.
 */

import { fetchAdImages } from '/js/services/api-ad-images.js';
import { 
    getImagesCache, setImagesCache, setImagesLoading, setImagesError, 
    getImagesCurrentClientId, setImagesCurrentClientId
} from '/js/state/images-state.js';
import { renderImagesGrid, showLoading, renderError } from '/js/renderers/images-renderer.js';

// ============ Page Initialization ============

/**
 * Initialize the Images page - load and render images
 */
export async function initImagesPage() {
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
