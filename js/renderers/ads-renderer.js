/**
 * Ads Renderer Module
 * Pure rendering functions for Facebook ads grid and cards.
 * Follows renderer pattern - accepts container and data, handles DOM only.
 */

import { deleteFacebookAd, updateFacebookAd } from '/js/services/api-facebook-ads.js';
import { getAdsCache, removeAdFromCache, updateAdInCache, getAdsSearchTerm, getAdsFilters } from '/js/state/ads-state.js';
import { AD_STATUS_OPTIONS, normalizeStatus, getStatusConfig } from '/js/controllers/ads-filter-ui.js';
import { escapeHtml } from '/js/utils/dom.js';
import { renderFBAdMockup, formatCTA, extractDomain, formatPrimaryText } from '/js/renderers/fb-ad-mockup.js';

// Store Masonry instance for cleanup/relayout
let masonryInstance = null;

// Store event handler refs so we can remove before re-attaching on re-render (avoids duplicate handlers → multiple picker opens)
let _adsContainerClickHandler = null;
let _adsDocumentClickHandler = null;
let _adsContainerInputHandler = null;
let _adsContainerKeydownHandler = null;
let _adsEventContainer = null;

/**
 * Show loading state
 * @param {HTMLElement} container - Container element
 */
export function showLoading(container) {
    container.innerHTML = `
        <div class="ads-loading">
            <p>Loading ads...</p>
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
        <div class="ads-error">
            <p class="ads-error__text">${escapeHtml(message)}</p>
            <button class="ads-error__retry" onclick="window.initAdsPage()">Retry</button>
        </div>
    `;
}

/**
 * Render empty state
 * @param {HTMLElement} container - Container element
 * @param {string} [message] - Optional custom message
 */
export function renderEmpty(container, message) {
    container.innerHTML = `
        <div class="ads-empty">
            <div class="ads-empty__icon">📢</div>
            <h3 class="ads-empty__title">No ads yet</h3>
            <p class="ads-empty__text">${escapeHtml(message || 'Add Facebook ads from the Visualizations or History tabs')}</p>
        </div>
    `;
}

/**
 * Render grid of ad cards
 * @param {HTMLElement} container - Container element
 * @param {Array} ads - Array of ad objects (already filtered/sorted)
 */
export function renderAdsGrid(container, ads) {
    const allAds = getAdsCache();
    const hasFiltersOrSearch = getAdsSearchTerm() || getAdsFilters().length > 0;
    
    // Destroy existing Masonry instance before re-rendering
    if (masonryInstance) {
        masonryInstance.destroy();
        masonryInstance = null;
    }
    
    if (!ads || ads.length === 0) {
        if (hasFiltersOrSearch && allAds.length > 0) {
            renderEmpty(container, 'No ads match your search or filters');
        } else {
            renderEmpty(container);
        }
        return;
    }
    
    // Add sizer elements for Masonry + ad cards
    container.innerHTML = `
        <div class="ads-grid-sizer"></div>
        <div class="ads-gutter-sizer"></div>
        ${ads.map(ad => renderAdCard(ad)).join('')}
    `;
    
    // Attach event delegation for interactive elements
    attachEventListeners(container);
    
    // Initialize Masonry for horizontal-first reading order
    initMasonry(container);
}

/**
 * Initialize Masonry layout on the container
 * @param {HTMLElement} container - Grid container element
 */
function initMasonry(container) {
    if (typeof Masonry === 'undefined') {
        console.warn('[AdsRenderer] Masonry.js not loaded, falling back to CSS layout');
        return;
    }
    
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/0ea04ade-be37-4438-ba64-4de28c7d11e9',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ads-renderer.js:initMasonry:entry',message:'Masonry init starting',data:{cardCount:container.querySelectorAll('.ads-card').length,imagesWithSrc:container.querySelectorAll('.pe-fb-ad__media.has-image img').length},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H1,H3'})}).catch(()=>{});
    // #endregion
    
    masonryInstance = new Masonry(container, {
        itemSelector: '.ads-card',
        columnWidth: '.ads-grid-sizer',
        gutter: '.ads-gutter-sizer',
        percentPosition: true,
        horizontalOrder: true
    });
    
    // #region agent log
    const cards = container.querySelectorAll('.ads-card');
    const cardHeights = Array.from(cards).slice(0, 6).map((c, i) => ({idx: i, height: c.offsetHeight, hasImage: !!c.querySelector('.pe-fb-ad__media.has-image')}));
    fetch('http://127.0.0.1:7242/ingest/0ea04ade-be37-4438-ba64-4de28c7d11e9',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ads-renderer.js:initMasonry:after',message:'Masonry init complete - card heights BEFORE image load',data:{cardHeights},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H1,H2'})}).catch(()=>{});
    // #endregion
    
    // #region agent log
    // Listen for image loads to track height changes
    const images = container.querySelectorAll('.pe-fb-ad__media.has-image img');
    images.forEach((img, idx) => {
        if (img.complete) {
            fetch('http://127.0.0.1:7242/ingest/0ea04ade-be37-4438-ba64-4de28c7d11e9',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ads-renderer.js:initMasonry:imgAlreadyLoaded',message:`Image ${idx} already loaded`,data:{idx,naturalHeight:img.naturalHeight,naturalWidth:img.naturalWidth},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H1,H4'})}).catch(()=>{});
        } else {
            img.addEventListener('load', () => {
                const card = img.closest('.ads-card');
                fetch('http://127.0.0.1:7242/ingest/0ea04ade-be37-4438-ba64-4de28c7d11e9',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ads-renderer.js:initMasonry:imgLoaded',message:`Image ${idx} loaded AFTER Masonry init`,data:{idx,naturalHeight:img.naturalHeight,cardHeightNow:card?.offsetHeight},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H1,H3'})}).catch(()=>{});
            });
        }
    });
    // #endregion
}

/**
 * Render single ad card with mockup and collapsible details
 * @param {Object} ad - Ad object from API
 * @returns {string} HTML string
 */
function renderAdCard(ad) {
    const id = escapeHtml(ad.id || '');
    const normalizedStatus = normalizeStatus(ad.status);
    const statusConfig = getStatusConfig(normalizedStatus);
    const statusClass = `ads-card__status--${normalizedStatus}`;
    
    const primaryText = ad.primary_text || '';
    const headline = escapeHtml(ad.headline || '');
    const description = escapeHtml(ad.description || '');
    const cta = formatCTA(ad.call_to_action);
    const destinationUrl = ad.destination_url || '';
    const displayUrl = extractDomain(destinationUrl);
    const vocEvidence = ad.voc_evidence || [];
    
    const formattedPrimaryText = formatPrimaryText(primaryText);
    
    // Get client info for the mockup
    const navLogo = document.getElementById('navClientLogo');
    const logoSrc = navLogo ? navLogo.src : '';
    const clientSelect = document.getElementById('clientSelect');
    const clientName = clientSelect?.selectedOptions?.[0]?.textContent?.trim() || 'Sponsored';
    
    const vocHtml = vocEvidence.length > 0 
        ? `<ul class="ads-card__voc-list">
            ${vocEvidence.map(quote => `<li class="ads-card__voc-item">"${escapeHtml(quote)}"</li>`).join('')}
           </ul>`
        : '<p class="ads-card__detail-value">No VoC evidence available</p>';
    
    // Render status dropdown options
    const statusOptionsHtml = AD_STATUS_OPTIONS.map(opt => `
        <button class="ads-card__status-option ${opt.id === normalizedStatus ? 'active' : ''}" 
                data-status="${opt.id}">
            ${escapeHtml(opt.label)}
        </button>
    `).join('');
    
    return `
        <div class="ads-card" data-ad-id="${id}">
            <div class="ads-card__header">
                <div class="ads-card__status-wrapper">
                    <button class="ads-card__status ${statusClass}" data-ad-id="${id}" title="Click to change status">
                        ${escapeHtml(statusConfig.label)}
                        <span class="ads-card__status-chevron">▼</span>
                    </button>
                    <div class="ads-card__status-dropdown">
                        ${statusOptionsHtml}
                    </div>
                </div>
                <button class="ads-card__delete" data-ad-id="${id}" title="Delete ad">×</button>
            </div>
            
            <div class="ads-card__mockup">
                ${renderFBAdMockup({
                    adId: id,
                    primaryText: formattedPrimaryText,
                    headline,
                    description,
                    cta,
                    displayUrl,
                    logoSrc,
                    clientName,
                    imageUrl: ad.full_json?.image_url || null
                })}
            </div>
            
            <div class="ads-card__accordions">
                <div class="ads-accordion">
                    <button class="ads-accordion__trigger" data-accordion="voc-evidence">
                        <span class="ads-accordion__title">VoC Evidence</span>
                        <svg class="ads-accordion__chevron" width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M4 6L8 10L12 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </button>
                    <div class="ads-accordion__content">
                        <div class="ads-accordion__body">
                            ${vocHtml}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Enable edit mode for an ad
 * @param {string} adId - Ad UUID
 * @param {HTMLElement} adCard - The ads-card element
 */
function enableEditMode(adId, adCard) {
    const fbAd = adCard.querySelector('.pe-fb-ad');
    if (!fbAd) return;
    
    // Store original values for revert
    const primaryTextEl = fbAd.querySelector('.pe-fb-ad__primary-text');
    const headlineEl = fbAd.querySelector('.pe-fb-ad__headline');
    const descriptionEl = fbAd.querySelector('.pe-fb-ad__description');
    
    if (!primaryTextEl || !headlineEl || !descriptionEl) return;
    
    // Store original values (use innerHTML to preserve HTML structure like <div> and <br> tags)
    fbAd.dataset.originalPrimaryText = primaryTextEl.innerHTML;
    fbAd.dataset.originalHeadline = headlineEl.innerHTML;
    fbAd.dataset.originalDescription = descriptionEl.innerHTML;
    
    // Make elements contenteditable (sponsored text is not editable)
    primaryTextEl.contentEditable = 'true';
    headlineEl.contentEditable = 'true';
    descriptionEl.contentEditable = 'true';
    
    // Add edit mode class (CSS will show edit controls)
    fbAd.classList.add('is-editing');
    
    // Recalculate Masonry layout after showing edit controls (adds height)
    requestAnimationFrame(() => {
        if (masonryInstance) {
            masonryInstance.layout();
        }
    });
    
    // Focus first editable element
    primaryTextEl.focus();
}

/**
 * Disable edit mode and revert changes
 * @param {HTMLElement} adCard - The ads-card element
 */
function disableEditMode(adCard) {
    const fbAd = adCard.querySelector('.pe-fb-ad');
    if (!fbAd) return;
    
    // Restore original values
    const primaryTextEl = fbAd.querySelector('.pe-fb-ad__primary-text');
    const headlineEl = fbAd.querySelector('.pe-fb-ad__headline');
    const descriptionEl = fbAd.querySelector('.pe-fb-ad__description');
    
    if (primaryTextEl && fbAd.dataset.originalPrimaryText !== undefined) {
        primaryTextEl.innerHTML = fbAd.dataset.originalPrimaryText;
    }
    if (headlineEl && fbAd.dataset.originalHeadline !== undefined) {
        headlineEl.innerHTML = fbAd.dataset.originalHeadline;
    }
    if (descriptionEl && fbAd.dataset.originalDescription !== undefined) {
        descriptionEl.innerHTML = fbAd.dataset.originalDescription;
    }
    
    // Remove contenteditable
    if (primaryTextEl) primaryTextEl.contentEditable = 'false';
    if (headlineEl) headlineEl.contentEditable = 'false';
    if (descriptionEl) descriptionEl.contentEditable = 'false';
    
    // Remove edit mode class (CSS will hide edit controls)
    fbAd.classList.remove('is-editing');
    
    // Recalculate Masonry layout after hiding edit controls (removes height)
    requestAnimationFrame(() => {
        if (masonryInstance) {
            masonryInstance.layout();
        }
    });
    
    // Clean up stored values
    delete fbAd.dataset.originalPrimaryText;
    delete fbAd.dataset.originalHeadline;
    delete fbAd.dataset.originalDescription;
}

/**
 * Extract plain text from contenteditable element, preserving line breaks
 * @param {HTMLElement} element - Contenteditable element
 * @returns {string} Plain text with line breaks
 */
function extractTextContent(element) {
    if (!element) return '';
    
    // Preserve paragraph structure: <div> elements should become double newlines (\n\n)
    // and <br> elements should become single newlines (\n)
    // This matches what formatPrimaryText() expects: \n\n for paragraphs, \n for line breaks
    
    // Get the HTML and convert it to text with proper newline structure
    let html = element.innerHTML || '';
    
    // Replace closing </div> tags with double newlines (paragraph breaks)
    html = html.replace(/<\/div>/gi, '\n\n');
    
    // Replace <br> and <br/> with single newlines (line breaks)
    html = html.replace(/<br\s*\/?>/gi, '\n');
    
    // Remove all remaining HTML tags
    html = html.replace(/<[^>]+>/g, '');
    
    // Decode HTML entities
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    let text = tempDiv.textContent || tempDiv.innerText || '';
    
    // Normalize: collapse multiple consecutive newlines (3+) to double newlines
    text = text.replace(/\n{3,}/g, '\n\n');
    
    // Trim leading/trailing whitespace but preserve structure
    text = text.trim();
    
    return text;
}

/**
 * Save ad edits to API
 * @param {string} adId - Ad UUID
 * @param {HTMLElement} adCard - The ads-card element
 */
async function saveAdEdits(adId, adCard) {
    const fbAd = adCard.querySelector('.pe-fb-ad');
    if (!fbAd) return;
    
    const primaryTextEl = fbAd.querySelector('.pe-fb-ad__primary-text');
    const headlineEl = fbAd.querySelector('.pe-fb-ad__headline');
    const descriptionEl = fbAd.querySelector('.pe-fb-ad__description');
    
    if (!primaryTextEl || !headlineEl || !descriptionEl) return;
    
    // Extract text content
    // Note: Header text (sponsored) is editable but not saved as it's not stored in backend
    const primaryText = extractTextContent(primaryTextEl);
    const headline = extractTextContent(headlineEl);
    const description = extractTextContent(descriptionEl);
    
    // Disable save button during save
    const saveBtn = fbAd.querySelector('.pe-fb-ad__edit-save');
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.textContent = 'Saving...';
    }
    
    try {
        // Update via API
        await updateFacebookAd(adId, {
            primary_text: primaryText,
            headline: headline,
            description: description
        });
        
        // Update cache
        updateAdInCache(adId, {
            primary_text: primaryText,
            headline: headline,
            description: description
        });
        
        // Exit edit mode
        disableEditMode(adCard);
        
        // Re-render via controller to refresh the display
        if (window.renderAdsPage) {
            window.renderAdsPage();
            
            // Wait for DOM to update and new Masonry instance to be created, then recalculate layout
            // Double requestAnimationFrame ensures layout happens after all DOM updates and Masonry init
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    if (masonryInstance) {
                        masonryInstance.layout();
                    }
                });
            });
        }
    } catch (error) {
        console.error('[AdsRenderer] Failed to save ad edits:', error);
        alert('Failed to save changes: ' + error.message);
        
        // Re-enable save button
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.textContent = 'Save';
        }
    }
}

/**
 * Attach event listeners using event delegation
 */
function attachEventListeners(container) {
    // Remove old handlers if they exist (from previous render) to prevent duplicate handlers
    if (_adsEventContainer) {
        if (_adsContainerClickHandler) {
            _adsEventContainer.removeEventListener('click', _adsContainerClickHandler);
        }
        if (_adsContainerInputHandler) {
            _adsEventContainer.removeEventListener('input', _adsContainerInputHandler);
        }
        if (_adsContainerKeydownHandler) {
            _adsEventContainer.removeEventListener('keydown', _adsContainerKeydownHandler);
        }
        if (_adsDocumentClickHandler) {
            document.removeEventListener('click', _adsDocumentClickHandler);
        }
    }
    
    // Store container reference
    _adsEventContainer = container;
    
    // Create and store new click handler
    _adsContainerClickHandler = async (e) => {
        // Handle edit icon click
        const editIcon = e.target.closest('.pe-fb-ad__edit-icon');
        if (editIcon) {
            e.stopPropagation();
            const adId = editIcon.dataset.adId;
            const adCard = editIcon.closest('.ads-card');
            if (adId && adCard) {
                enableEditMode(adId, adCard);
            }
            return;
        }
        
        // Handle save button click
        const saveBtn = e.target.closest('.pe-fb-ad__edit-save');
        if (saveBtn) {
            e.stopPropagation();
            const adId = saveBtn.dataset.adId;
            const adCard = saveBtn.closest('.ads-card');
            if (adId && adCard) {
                await saveAdEdits(adId, adCard);
            }
            return;
        }
        
        // Handle cancel button click
        const cancelBtn = e.target.closest('.pe-fb-ad__edit-cancel');
        if (cancelBtn) {
            e.stopPropagation();
            const adCard = cancelBtn.closest('.ads-card');
            if (adCard) {
                disableEditMode(adCard);
            }
            return;
        }
        
        // Handle delete button
        const deleteBtn = e.target.closest('.ads-card__delete');
        if (deleteBtn) {
            const adId = deleteBtn.dataset.adId;
            await handleDeleteAd(adId, container);
            return;
        }
        
        // Handle status pill click (toggle dropdown)
        const statusBtn = e.target.closest('.ads-card__status');
        if (statusBtn && !e.target.closest('.ads-card__status-dropdown')) {
            e.stopPropagation();
            const wrapper = statusBtn.closest('.ads-card__status-wrapper');
            // Close all other dropdowns first
            container.querySelectorAll('.ads-card__status-wrapper.open').forEach(w => {
                if (w !== wrapper) w.classList.remove('open');
            });
            wrapper?.classList.toggle('open');
            return;
        }
        
        // Handle status option selection
        const statusOption = e.target.closest('.ads-card__status-option');
        if (statusOption) {
            e.stopPropagation();
            const newStatus = statusOption.dataset.status;
            const card = statusOption.closest('.ads-card');
            const adId = card?.dataset.adId;
            if (adId && newStatus) {
                await handleStatusChange(adId, newStatus);
            }
            // Close dropdown
            statusOption.closest('.ads-card__status-wrapper')?.classList.remove('open');
            return;
        }
        
        // Handle image delete button click
        const mediaDeleteBtn = e.target.closest('.pe-fb-ad__media-delete');
        if (mediaDeleteBtn) {
            e.stopPropagation();
            const adId = mediaDeleteBtn.dataset.adId;
            if (adId) {
                await handleImageDelete(adId, mediaDeleteBtn.closest('.pe-fb-ad__media'));
            }
            return;
        }
        
        // Handle image media click (open image picker)
        const mediaElement = e.target.closest('.pe-fb-ad__media');
        if (mediaElement) {
            e.stopPropagation(); // Prevent event from bubbling to other handlers
            // Don't allow image selection while in edit mode
            const fbAd = mediaElement.closest('.pe-fb-ad');
            if (fbAd && fbAd.classList.contains('is-editing')) {
                return;
            }
            const card = mediaElement.closest('.ads-card');
            const adId = card?.dataset.adId;
            if (adId) {
                await handleImageSelection(adId, mediaElement);
            }
            return;
        }
        
        // Handle accordion toggle
        const accordionTrigger = e.target.closest('.ads-accordion__trigger');
        if (accordionTrigger) {
            // Don't allow accordion toggle while in edit mode
            const fbAd = accordionTrigger.closest('.pe-fb-ad');
            if (fbAd && fbAd.classList.contains('is-editing')) {
                return;
            }
            const accordion = accordionTrigger.closest('.ads-accordion');
            if (accordion) {
                accordion.classList.toggle('expanded');
                // Force CSS columns to recalculate layout after accordion animation
                setTimeout(() => {
                    container.style.columnCount = 'auto';
                    // eslint-disable-next-line no-unused-expressions
                    container.offsetHeight; // Force reflow
                    container.style.columnCount = '';
                }, 260); // Slightly longer than the 250ms accordion transition
            }
            return;
        }
    };
    
    // Attach click handler
    container.addEventListener('click', _adsContainerClickHandler);
    
    // Create and store document click handler for closing dropdowns
    _adsDocumentClickHandler = (e) => {
        if (!e.target.closest('.ads-card__status-wrapper')) {
            container.querySelectorAll('.ads-card__status-wrapper.open').forEach(w => {
                w.classList.remove('open');
            });
        }
    };
    document.addEventListener('click', _adsDocumentClickHandler);
    
    // Create and store input handler
    _adsContainerInputHandler = (e) => {
        const fbAd = e.target.closest('.pe-fb-ad.is-editing');
        if (fbAd && e.target.contentEditable === 'true') {
            // Debounce layout updates to avoid excessive recalculations
            clearTimeout(fbAd._layoutTimeout);
            fbAd._layoutTimeout = setTimeout(() => {
                if (masonryInstance) {
                    masonryInstance.layout();
                }
            }, 150);
        }
    };
    container.addEventListener('input', _adsContainerInputHandler);
    
    // Create and store keydown handler
    _adsContainerKeydownHandler = (e) => {
        const fbAd = e.target.closest('.pe-fb-ad.is-editing');
        if (!fbAd) return;
        
        // Escape key - cancel editing
        if (e.key === 'Escape') {
            e.preventDefault();
            e.stopPropagation();
            const adCard = fbAd.closest('.ads-card');
            if (adCard) {
                disableEditMode(adCard);
            }
            return;
        }
        
        // Enter key in contenteditable - handle line breaks properly
        if (e.key === 'Enter' && e.target.contentEditable === 'true') {
            const isPrimaryText = e.target.classList.contains('pe-fb-ad__primary-text');
            const isSingleLine = e.target.classList.contains('pe-fb-ad__headline') || 
                                e.target.classList.contains('pe-fb-ad__description');
            
            // For primary text (multi-line), insert <br> instead of creating <div>
            if (isPrimaryText) {
                e.preventDefault();
                // Insert a line break (<br>) instead of letting contenteditable create a <div>
                if (document.execCommand) {
                    document.execCommand('insertLineBreak', false, null);
                } else {
                    // Fallback: manually insert <br>
                    const selection = window.getSelection();
                    if (selection.rangeCount > 0) {
                        const range = selection.getRangeAt(0);
                        const br = document.createElement('br');
                        range.deleteContents();
                        range.insertNode(br);
                        // Move cursor after the <br>
                        range.setStartAfter(br);
                        range.collapse(true);
                        selection.removeAllRanges();
                        selection.addRange(range);
                    }
                }
                return;
            }
            
            // For single-line fields, move to next field
            if (isSingleLine && !e.shiftKey) {
                e.preventDefault();
                // Move focus to next field or blur
                const fields = [
                    fbAd.querySelector('.pe-fb-ad__primary-text'),
                    fbAd.querySelector('.pe-fb-ad__headline'),
                    fbAd.querySelector('.pe-fb-ad__description')
                ].filter(Boolean);
                
                const currentIndex = fields.indexOf(e.target);
                if (currentIndex < fields.length - 1) {
                    fields[currentIndex + 1].focus();
                } else {
                    e.target.blur();
                }
                return;
            }
        }
    };
    container.addEventListener('keydown', _adsContainerKeydownHandler);
}

/**
 * Handle ad deletion
 */
async function handleDeleteAd(adId, container) {
    if (!confirm('Are you sure you want to delete this ad?')) {
        return;
    }
    
    try {
        await deleteFacebookAd(adId);
        removeAdFromCache(adId);
        
        // Re-render via controller
        if (window.renderAdsPage) {
            window.renderAdsPage();
        }
    } catch (error) {
        console.error('[AdsRenderer] Failed to delete ad:', error);
        alert('Failed to delete ad: ' + error.message);
    }
}

/**
 * Handle status change
 * @param {string} adId - Ad UUID
 * @param {string} newStatus - New status value
 */
async function handleStatusChange(adId, newStatus) {
    try {
        // Update via API
        await updateFacebookAd(adId, { status: newStatus });
        
        // Update cache
        updateAdInCache(adId, { status: newStatus });
        
        // Save scroll position before re-render (page scrolls via window.scrollY)
        const windowScrollYBefore = window.scrollY;
        const mainContainer = document.getElementById('mainContainer');
        const mainContainerScrollTopBefore = mainContainer ? mainContainer.scrollTop : 0;
        
        // Re-render via controller
        if (window.renderAdsPage) {
            window.renderAdsPage();
        }
        
        // Restore scroll position after DOM update
        if (windowScrollYBefore > 0) {
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    window.scrollTo({ top: windowScrollYBefore, behavior: 'auto' });
                    if (mainContainer && mainContainerScrollTopBefore > 0) {
                        mainContainer.scrollTop = mainContainerScrollTopBefore;
                    }
                });
            });
        }
    } catch (error) {
        console.error('[AdsRenderer] Failed to update status:', error);
        alert('Failed to update status: ' + error.message);
    }
}

/**
 * Handle image selection for an ad
 * @param {string} adId - Ad UUID
 * @param {HTMLElement} mediaElement - Media element that was clicked
 */
async function handleImageSelection(adId, mediaElement) {
    try {
        // Import image picker
        const { showImagePickerModal } = await import('/js/renderers/images-renderer.js');
        const { fetchAdImages } = await import('/js/services/api-ad-images.js');
        
        // Get current client ID
        const clientId = window.appStateGet?.('currentClientId') || 
                         document.getElementById('clientSelect')?.value;
        
        if (!clientId) {
            alert('Please select a client first');
            return;
        }
        
        // Fetch images for the client
        const response = await fetchAdImages(clientId);
        const images = response.items || [];
        
        if (images.length === 0) {
            alert('No images available. Please upload images in the Images tab first.');
            return;
        }
        
        const { setImagesCache } = await import('/js/state/images-state.js');
        setImagesCache(images);
        
        // Show picker modal
        showImagePickerModal(async (imageUrl) => {
            try {
                // Get current ad to preserve full_json
                const ads = getAdsCache();
                const ad = ads.find(a => a.id === adId);
                
                if (!ad) {
                    throw new Error('Ad not found');
                }
                
                // Update via API - pass image_url which will be stored in full_json by backend
                await updateFacebookAd(adId, { 
                    image_url: imageUrl
                });
                
                // Update cache - update full_json with image_url
                const updatedFullJson = {
                    ...ad.full_json,
                    image_url: imageUrl
                };
                updateAdInCache(adId, { 
                    full_json: updatedFullJson
                });
                
                // Save scroll position before re-render to avoid disorienting jump
                // The page scrolls via window.scrollY, not mainContainer.scrollTop
                const windowScrollYBefore = window.scrollY;
                const mainContainer = document.getElementById('mainContainer');
                const mainContainerScrollTopBefore = mainContainer ? mainContainer.scrollTop : 0;
                
                // Re-render via controller
                if (window.renderAdsPage) {
                    window.renderAdsPage();
                }
                
                // Restore scroll position after DOM update
                // Use double requestAnimationFrame to ensure layout is complete
                if (windowScrollYBefore > 0) {
                    requestAnimationFrame(() => {
                        requestAnimationFrame(() => {
                            window.scrollTo({ top: windowScrollYBefore, behavior: 'auto' });
                            // Also restore mainContainer if it was scrolled
                            if (mainContainer && mainContainerScrollTopBefore > 0) {
                                mainContainer.scrollTop = mainContainerScrollTopBefore;
                            }
                        });
                    });
                }
            } catch (error) {
                console.error('[AdsRenderer] Failed to update image:', error);
                alert('Failed to update image: ' + error.message);
            }
        });
    } catch (error) {
        console.error('[AdsRenderer] Failed to open image picker:', error);
        alert('Failed to open image picker: ' + error.message);
    }
}

/**
 * Handle image deletion for an ad (restore placeholder)
 * @param {string} adId - Ad UUID
 * @param {HTMLElement} mediaElement - Media element containing the image
 */
async function handleImageDelete(adId, mediaElement) {
    try {
        // Get current ad to preserve full_json
        const ads = getAdsCache();
        const ad = ads.find(a => a.id === adId);
        
        if (!ad) {
            throw new Error('Ad not found');
        }
        
        // Update via API - pass null image_url to remove it
        await updateFacebookAd(adId, { 
            image_url: null
        });
        
        // Update cache - remove image_url from full_json
        const updatedFullJson = {
            ...ad.full_json
        };
        delete updatedFullJson.image_url;
        
        updateAdInCache(adId, { 
            full_json: updatedFullJson
        });
        
        // Save scroll position before re-render
        const windowScrollYBefore = window.scrollY;
        const mainContainer = document.getElementById('mainContainer');
        const mainContainerScrollTopBefore = mainContainer ? mainContainer.scrollTop : 0;
        
        // Re-render via controller
        if (window.renderAdsPage) {
            window.renderAdsPage();
        }
        
        // Restore scroll position after DOM update
        if (windowScrollYBefore > 0) {
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    window.scrollTo({ top: windowScrollYBefore, behavior: 'auto' });
                    if (mainContainer && mainContainerScrollTopBefore > 0) {
                        mainContainer.scrollTop = mainContainerScrollTopBefore;
                    }
                });
            });
        }
    } catch (error) {
        console.error('[AdsRenderer] Failed to delete image:', error);
        alert('Failed to delete image: ' + error.message);
    }
}
