/**
 * Ads Kanban Renderer Module
 * Renders ads in a Kanban board layout with drag-and-drop between status columns.
 * Follows renderer pattern - accepts container and data, handles DOM only.
 */

import { updateFacebookAd } from '/js/services/api-facebook-ads.js';
import { updateAdInCache, getAdsSearchTerm, getAdsFilters } from '/js/state/ads-state.js';
import { AD_STATUS_OPTIONS, normalizeStatus, getStatusConfig } from '/js/controllers/ads-filter-ui.js';
import { escapeHtml } from '/js/utils/dom.js';

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
