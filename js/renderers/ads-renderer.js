/**
 * Ads Renderer Module
 * Pure rendering functions for Facebook ads grid and cards.
 * Follows renderer pattern - accepts container and data, handles DOM only.
 */

import { deleteFacebookAd, updateFacebookAd } from '/js/services/api-facebook-ads.js';
import { getAdsCache, removeAdFromCache, updateAdInCache, getAdsSearchTerm, getAdsFilters } from '/js/state/ads-state.js';
import { AD_STATUS_OPTIONS, normalizeStatus, getStatusConfig } from '/js/controllers/ads-filter-ui.js';
import { escapeHtml } from '/js/utils/dom.js';

// Store Masonry instance for cleanup/relayout
let masonryInstance = null;

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
    
    masonryInstance = new Masonry(container, {
        itemSelector: '.ads-card',
        columnWidth: '.ads-grid-sizer',
        gutter: '.ads-gutter-sizer',
        percentPosition: true,
        horizontalOrder: true
    });
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
                    primaryText: formattedPrimaryText,
                    headline,
                    description,
                    cta,
                    displayUrl,
                    logoSrc,
                    clientName
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
 * Render Facebook ad mockup HTML
 * @param {Object} params - Ad parameters
 * @returns {string} HTML string
 */
function renderFBAdMockup({ primaryText, headline, description, cta, displayUrl, logoSrc, clientName }) {
    const profilePicContent = logoSrc 
        ? `<img src="${escapeHtml(logoSrc)}" alt="Client Logo" style="width:40px;height:40px;border-radius:50%;object-fit:contain;background:#fff;">`
        : 'Ad';
    const profilePicStyle = logoSrc
        ? 'width:40px;height:40px;min-width:40px;min-height:40px;border-radius:50%;overflow:hidden;flex-shrink:0;margin:0;padding:0;background:#fff;'
        : 'width:40px;height:40px;min-width:40px;min-height:40px;border-radius:50%;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:600;font-size:14px;flex-shrink:0;margin:0;padding:0;';

    return `
        <div class="pe-fb-ad" style="margin:0;padding:0;border:1px solid #dce0e5;display:block;width:100%;background:#fff;border-radius:8px;box-shadow:0 1px 2px rgba(0,0,0,0.1);overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;font-size:15px;line-height:1.3333;color:#050505;">
            <div class="pe-fb-ad__header" style="padding:12px 12px 0;margin:0;display:flex;align-items:center;gap:8px;">
                <div class="pe-fb-ad__profile-pic" style="${profilePicStyle}">${profilePicContent}</div>
                <div class="pe-fb-ad__info" style="flex:1;min-width:0;margin:0;padding:0;">
                    <div class="pe-fb-ad__page-name" style="font-weight:600;font-size:15px;color:#050505;margin:0;padding:0;">${escapeHtml(clientName)}</div>
                    <div class="pe-fb-ad__sponsored" style="display:flex;align-items:center;gap:4px;font-size:13px;color:#65676b;margin:0;padding:0;">
                        <span style="margin:0;padding:0;">Sponsored</span>
                        <span class="pe-fb-ad__dot" style="width:3px;height:3px;background:#65676b;border-radius:50%;margin:0;padding:0;"></span>
                        <span style="margin:0;padding:0;">🌐</span>
                    </div>
                </div>
            </div>
            <div class="pe-fb-ad__primary-text-wrapper" style="padding:8px 12px;margin:0;">
                <div class="pe-fb-ad__primary-text" style="font-size:15px;line-height:1.4;color:#050505;margin:0;padding:0;">${primaryText}</div>
            </div>
            <div class="pe-fb-ad__media" style="width:100%;aspect-ratio:1.91/1;background:linear-gradient(to top right,transparent calc(50% - 1px),#9ca3af calc(50% - 1px),#9ca3af calc(50% + 1px),transparent calc(50% + 1px)),linear-gradient(to top left,transparent calc(50% - 1px),#9ca3af calc(50% - 1px),#9ca3af calc(50% + 1px),transparent calc(50% + 1px)),#e5e7eb;margin:0;padding:0;"></div>
            <div class="pe-fb-ad__link-details" style="background:#f8fafb;padding:10px 12px;margin:0;display:flex;align-items:center;justify-content:space-between;gap:12px;">
                <div class="pe-fb-ad__link-text" style="flex:1;min-width:0;margin:0;padding:0;">
                    <div class="pe-fb-ad__link-url" style="font-size:12px;color:#65676b;text-transform:uppercase;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin:0;padding:0;">${escapeHtml(displayUrl)}</div>
                    <div class="pe-fb-ad__headline" style="font-weight:600;font-size:15px;color:#050505;line-height:1.2;margin:0;padding:0;">${headline}</div>
                    <div class="pe-fb-ad__description" style="font-size:14px;color:#65676b;line-height:1.3;margin:0;padding:0;">${description}</div>
                </div>
                <div class="pe-fb-ad__cta" style="background:#e2e5e9;color:#050505;border:none;padding:8px 12px;border-radius:4px;font-weight:600;font-size:14px;white-space:nowrap;flex-shrink:0;margin:0;">${escapeHtml(cta)}</div>
            </div>
            <div class="pe-fb-ad__footer" style="padding:4px 12px 8px;margin:0;display:flex;justify-content:space-around;border-top:1px solid #e4e6eb;">
                <div class="pe-fb-ad__action" style="display:flex;align-items:center;gap:4px;color:#65676b;font-size:13px;font-weight:600;padding:6px 0;margin:0;">
                    <span style="font-size:16px;margin:0;padding:0;">👍</span>
                    <span style="margin:0;padding:0;">Like</span>
                </div>
                <div class="pe-fb-ad__action" style="display:flex;align-items:center;gap:4px;color:#65676b;font-size:13px;font-weight:600;padding:6px 0;margin:0;">
                    <span style="font-size:16px;margin:0;padding:0;">💬</span>
                    <span style="margin:0;padding:0;">Comment</span>
                </div>
                <div class="pe-fb-ad__action" style="display:flex;align-items:center;gap:4px;color:#65676b;font-size:13px;font-weight:600;padding:6px 0;margin:0;">
                    <span style="font-size:16px;margin:0;padding:0;">↗</span>
                    <span style="margin:0;padding:0;">Share</span>
                </div>
            </div>
        </div>
    `;
}

/**
 * Format CTA value to sentence case (e.g., SHOP_NOW -> "Shop now")
 */
function formatCTA(cta) {
    if (!cta) return 'Learn more';
    const words = cta.toLowerCase().split('_');
    words[0] = words[0].charAt(0).toUpperCase() + words[0].slice(1);
    return words.join(' ');
}

/**
 * Extract domain from URL for display
 */
function extractDomain(url) {
    if (!url) return 'example.com';
    try {
        const urlObj = new URL(url);
        return urlObj.hostname.replace('www.', '');
    } catch {
        return url.replace(/^https?:\/\//, '').split('/')[0];
    }
}

/**
 * Format primary text with proper HTML paragraphs
 */
function formatPrimaryText(text) {
    if (!text) return '';
    
    let rawText = text
        .replace(/\\n/g, '\n')
        .replace(/\\"/g, '"')
        .replace(/\r\n/g, '\n')
        .replace(/\r/g, '\n');
    
    const paragraphs = rawText.split(/\n{2,}/);
    const formattedParagraphs = paragraphs
        .map(para => para.trim())
        .filter(para => para.length > 0)
        .map(para => {
            const escaped = escapeHtml(para);
            return escaped.replace(/\n/g, '<br>');
        });
    
    return formattedParagraphs
        .map((para, idx, arr) => {
            const isLast = idx === arr.length - 1;
            return `<div style="margin-bottom:${isLast ? '0' : '12px'};">${para}</div>`;
        })
        .join('');
}

/**
 * Attach event listeners using event delegation
 */
function attachEventListeners(container) {
    container.addEventListener('click', async (e) => {
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
        
        // Handle accordion toggle
        const accordionTrigger = e.target.closest('.ads-accordion__trigger');
        if (accordionTrigger) {
            const accordion = accordionTrigger.closest('.ads-accordion');
            if (accordion) {
                accordion.classList.toggle('expanded');
            }
            return;
        }
    });
    
    // Close status dropdowns when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.ads-card__status-wrapper')) {
            container.querySelectorAll('.ads-card__status-wrapper.open').forEach(w => {
                w.classList.remove('open');
            });
        }
    });
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
        
        // Re-render via controller
        if (window.renderAdsPage) {
            window.renderAdsPage();
        }
    } catch (error) {
        console.error('[AdsRenderer] Failed to update status:', error);
        alert('Failed to update status: ' + error.message);
    }
}
