/**
 * Images Controller Module
 * Page-level orchestration for Images tab: loading, rendering.
 * Follows controller pattern - coordinates between state, services, and renderers.
 */

import { fetchAdImages } from '/js/services/api-ad-images.js';
import { 
    getImagesCache, setImagesCache, setImagesLoading, setImagesError, 
    getImagesCurrentClientId, setImagesCurrentClientId,
    getImagesColumnCount, setImagesColumnCount
} from '/js/state/images-state.js';
import { renderImagesGrid, showLoading, renderError, relayoutImagesGrid, cancelScheduledLayoutFromImageLoad } from '/js/renderers/images-renderer.js';
import { debounce } from '/js/utils/dom.js';

// ============ Slider Initialization ============

// Track if slider has been initialized to avoid duplicate listeners
let sliderInitialized = false;

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

// ============ Page Initialization ============

/**
 * Initialize the Images page - load and render images
 */
export async function initImagesPage() {
    // Initialize slider first (before any rendering)
    initSizeSlider();
    
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
