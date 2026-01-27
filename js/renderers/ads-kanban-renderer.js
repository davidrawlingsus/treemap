/**
 * Ads Kanban Renderer Module
 * Renders ads in a Kanban board layout with drag-and-drop between status columns.
 * Follows renderer pattern - accepts container and data, handles DOM only.
 */

import { updateFacebookAd } from '/js/services/api-facebook-ads.js';
import { updateAdInCache, getAdsSearchTerm, getAdsFilters, getAdsCache } from '/js/state/ads-state.js';
import { AD_STATUS_OPTIONS, normalizeStatus, getStatusConfig } from '/js/controllers/ads-filter-ui.js';
import { escapeHtml } from '/js/utils/dom.js';
import { renderFBAdMockup, formatCTA, extractDomain, formatPrimaryText } from '/js/renderers/fb-ad-mockup.js';

// Hover preview state
let previewContainer = null;
let hoverTimeout = null;
const HOVER_DELAY = 400; // ms before showing preview

/**
 * Render ads in Kanban board layout
 * @param {HTMLElement} container - Container element
 * @param {Array} ads - Array of ad objects (already filtered/sorted)
 */
export function renderAdsKanban(container, ads) {
    const hasFiltersOrSearch = getAdsSearchTerm() || getAdsFilters().length > 0;
    
    if (!ads || ads.length === 0) {
        if (hasFiltersOrSearch) {
            renderEmpty(container, 'No ads match your search or filters');
        } else {
            renderEmpty(container);
        }
        return;
    }
    
    // Group ads by status
    const adsByStatus = groupAdsByStatus(ads);
    
    // Render Kanban board
    container.innerHTML = `
        <div class="ads-kanban">
            ${AD_STATUS_OPTIONS.map(status => renderKanbanColumn(status, adsByStatus[status.id] || [])).join('')}
        </div>
    `;
    
    // Initialize drag and drop
    initKanbanDragDrop(container);
    
    // Initialize hover preview
    initKanbanHoverPreview(container);
}

/**
 * Group ads by their normalized status
 * @param {Array} ads - Array of ad objects
 * @returns {Object} Object with status IDs as keys and arrays of ads as values
 */
function groupAdsByStatus(ads) {
    const groups = {};
    
    AD_STATUS_OPTIONS.forEach(status => {
        groups[status.id] = [];
    });
    
    ads.forEach(ad => {
        const status = normalizeStatus(ad.status);
        if (groups[status]) {
            groups[status].push(ad);
        } else {
            groups['draft'].push(ad);
        }
    });
    
    return groups;
}

/**
 * Render a single Kanban column
 * @param {Object} status - Status config object
 * @param {Array} ads - Ads in this column
 * @returns {string} HTML string
 */
function renderKanbanColumn(status, ads) {
    const cardsHtml = ads.map(ad => renderKanbanCard(ad)).join('');
    
    return `
        <div class="ads-kanban__column" data-status="${status.id}">
            <div class="ads-kanban__column-header">
                <span class="ads-kanban__column-title">${escapeHtml(status.label)}</span>
                <span class="ads-kanban__column-count">${ads.length}</span>
            </div>
            <div class="ads-kanban__column-body" data-status="${status.id}">
                ${cardsHtml || '<div class="ads-kanban__empty">Drop ads here</div>'}
            </div>
        </div>
    `;
}

/**
 * Render a single Kanban card (simplified version of ad card)
 * @param {Object} ad - Ad object
 * @returns {string} HTML string
 */
function renderKanbanCard(ad) {
    const id = escapeHtml(ad.id || '');
    const headline = escapeHtml(ad.headline || 'Untitled Ad');
    const primaryText = escapeHtml((ad.primary_text || '').substring(0, 100));
    const testType = escapeHtml(ad.full_json?.testType || '');
    
    return `
        <div class="ads-kanban__card" draggable="true" data-ad-id="${id}">
            <div class="ads-kanban__card-headline">${headline}</div>
            ${testType ? `<div class="ads-kanban__card-type">${testType}</div>` : ''}
            ${primaryText ? `<div class="ads-kanban__card-preview">${primaryText}${ad.primary_text?.length > 100 ? '...' : ''}</div>` : ''}
            <div class="ads-kanban__card-drag-handle">⋮⋮</div>
        </div>
    `;
}

/**
 * Render empty state
 * @param {HTMLElement} container - Container element
 * @param {string} [message] - Optional custom message
 */
function renderEmpty(container, message) {
    container.innerHTML = `
        <div class="ads-empty">
            <div class="ads-empty__icon">📢</div>
            <h3 class="ads-empty__title">No ads yet</h3>
            <p class="ads-empty__text">${escapeHtml(message || 'Add Facebook ads from the Visualizations or History tabs')}</p>
        </div>
    `;
}

/**
 * Get or create the preview container element
 * @returns {HTMLElement} The preview container
 */
function getPreviewContainer() {
    if (!previewContainer) {
        previewContainer = document.createElement('div');
        previewContainer.className = 'ads-kanban__preview';
        document.body.appendChild(previewContainer);
    }
    return previewContainer;
}

/**
 * Show preview for an ad card
 * @param {HTMLElement} card - The Kanban card element
 */
function showPreview(card) {
    const adId = card.dataset.adId;
    const ads = getAdsCache();
    const ad = ads.find(a => a.id === adId);
    
    if (!ad) return;
    
    const preview = getPreviewContainer();
    
    // Get client info for the mockup
    const navLogo = document.getElementById('navClientLogo');
    const logoSrc = navLogo ? navLogo.src : '';
    const clientSelect = document.getElementById('clientSelect');
    const clientName = clientSelect?.selectedOptions?.[0]?.textContent?.trim() || 'Sponsored';
    
    // Render the FB ad mockup (read-only)
    const mockupHtml = renderFBAdMockup({
        adId: ad.id,
        primaryText: formatPrimaryText(ad.primary_text || ''),
        headline: escapeHtml(ad.headline || ''),
        description: escapeHtml(ad.description || ''),
        cta: formatCTA(ad.call_to_action),
        displayUrl: extractDomain(ad.destination_url || ''),
        logoSrc,
        clientName,
        imageUrl: ad.full_json?.image_url || null,
        readOnly: true
    });
    
    preview.innerHTML = mockupHtml;
    
    // Position the preview
    positionPreview(card, preview);
    
    // Show with fade-in
    preview.classList.add('visible');
}

/**
 * Position preview next to the card, keeping it within viewport
 * @param {HTMLElement} card - The Kanban card element
 * @param {HTMLElement} preview - The preview container
 */
function positionPreview(card, preview) {
    const cardRect = card.getBoundingClientRect();
    const previewWidth = 380; // matches CSS max-width
    const padding = 12;
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    
    // Try to position to the right of the card
    let left = cardRect.right + padding;
    
    // If not enough space on right, position to the left
    if (left + previewWidth > viewportWidth - padding) {
        left = cardRect.left - previewWidth - padding;
    }
    
    // If still not enough space, center it over the card
    if (left < padding) {
        left = Math.max(padding, (viewportWidth - previewWidth) / 2);
    }
    
    // Vertical positioning - align top with card, but keep within viewport
    let top = cardRect.top;
    
    // Get preview height after content is rendered
    preview.style.visibility = 'hidden';
    preview.style.display = 'block';
    const previewHeight = preview.offsetHeight;
    preview.style.visibility = '';
    
    // Adjust if preview would go below viewport
    if (top + previewHeight > viewportHeight - padding) {
        top = Math.max(padding, viewportHeight - previewHeight - padding);
    }
    
    preview.style.left = `${left}px`;
    preview.style.top = `${top}px`;
}

/**
 * Hide the preview
 */
function hidePreview() {
    if (hoverTimeout) {
        clearTimeout(hoverTimeout);
        hoverTimeout = null;
    }
    
    if (previewContainer) {
        previewContainer.classList.remove('visible');
    }
}

/**
 * Initialize hover preview functionality
 * @param {HTMLElement} container - Container element
 */
function initKanbanHoverPreview(container) {
    const cards = container.querySelectorAll('.ads-kanban__card');
    
    cards.forEach(card => {
        card.addEventListener('mouseenter', () => {
            // Don't show preview if card is being dragged
            if (card.classList.contains('dragging')) return;
            
            // Clear any existing timeout
            if (hoverTimeout) {
                clearTimeout(hoverTimeout);
            }
            
            // Delay before showing preview
            hoverTimeout = setTimeout(() => {
                // Double-check not dragging after delay
                if (!card.classList.contains('dragging')) {
                    showPreview(card);
                }
            }, HOVER_DELAY);
        });
        
        card.addEventListener('mouseleave', () => {
            hidePreview();
        });
        
        // Also hide on drag start
        card.addEventListener('dragstart', () => {
            hidePreview();
        });
    });
}

/**
 * Initialize drag and drop functionality for Kanban board
 * @param {HTMLElement} container - Container element
 */
function initKanbanDragDrop(container) {
    const cards = container.querySelectorAll('.ads-kanban__card');
    const dropZones = container.querySelectorAll('.ads-kanban__column-body');
    
    let draggedCard = null;
    
    // Card drag events
    cards.forEach(card => {
        card.addEventListener('dragstart', (e) => {
            draggedCard = card;
            card.classList.add('dragging');
            hidePreview(); // Hide preview when dragging starts
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', card.dataset.adId);
        });
        
        card.addEventListener('dragend', () => {
            card.classList.remove('dragging');
            draggedCard = null;
            // Remove all drag-over states
            dropZones.forEach(zone => zone.classList.remove('drag-over'));
        });
    });
    
    // Drop zone events
    dropZones.forEach(zone => {
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            zone.classList.add('drag-over');
        });
        
        zone.addEventListener('dragleave', (e) => {
            // Only remove if leaving the zone entirely
            if (!zone.contains(e.relatedTarget)) {
                zone.classList.remove('drag-over');
            }
        });
        
        zone.addEventListener('drop', async (e) => {
            e.preventDefault();
            zone.classList.remove('drag-over');
            
            if (!draggedCard) return;
            
            const adId = draggedCard.dataset.adId;
            const newStatus = zone.dataset.status;
            const currentStatus = draggedCard.closest('.ads-kanban__column')?.dataset.status;
            
            // If dropped in same column, do nothing
            if (newStatus === currentStatus) return;
            
            // Move card visually first for immediate feedback
            const emptyPlaceholder = zone.querySelector('.ads-kanban__empty');
            if (emptyPlaceholder) emptyPlaceholder.remove();
            zone.appendChild(draggedCard);
            
            // Update counts
            updateColumnCounts(container);
            
            // Update via API
            await handleKanbanStatusChange(adId, newStatus);
        });
    });
}

/**
 * Update column counts after drag/drop
 * @param {HTMLElement} container - Container element
 */
function updateColumnCounts(container) {
    const columns = container.querySelectorAll('.ads-kanban__column');
    columns.forEach(column => {
        const count = column.querySelectorAll('.ads-kanban__card').length;
        const countEl = column.querySelector('.ads-kanban__column-count');
        if (countEl) countEl.textContent = count;
        
        // Add/remove empty placeholder
        const body = column.querySelector('.ads-kanban__column-body');
        const hasCards = body.querySelectorAll('.ads-kanban__card').length > 0;
        const hasEmpty = body.querySelector('.ads-kanban__empty');
        
        if (!hasCards && !hasEmpty) {
            body.innerHTML = '<div class="ads-kanban__empty">Drop ads here</div>';
        }
    });
}

/**
 * Handle status change from Kanban drag/drop
 * @param {string} adId - Ad UUID
 * @param {string} newStatus - New status value
 */
async function handleKanbanStatusChange(adId, newStatus) {
    try {
        await updateFacebookAd(adId, { status: newStatus });
        updateAdInCache(adId, { status: newStatus });
    } catch (error) {
        console.error('[AdsKanbanRenderer] Failed to update status:', error);
        // Re-render to restore correct state
        if (window.renderAdsPage) {
            window.renderAdsPage();
        }
        alert('Failed to update status: ' + error.message);
    }
}
