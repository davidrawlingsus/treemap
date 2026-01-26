/**
 * Ads Renderer Module
 * Renders Facebook ads in a grid layout with collapsible details.
 * Follows renderer pattern - accepts container and data, handles DOM, does not modify global state directly.
 */

import { fetchFacebookAds, deleteFacebookAd } from '/js/services/api-facebook-ads.js';
import { 
    getAdsCache, setAdsCache, setAdsLoading, setAdsError, 
    getAdsCurrentClientId, setAdsCurrentClientId, removeAdFromCache 
} from '/js/state/ads-state.js';
import { escapeHtml, escapeHtmlForAttribute } from '/js/utils/dom.js';

/**
 * Initialize the Ads page - load and render ads
 */
export async function initAdsPage() {
    const container = document.getElementById('adsGrid');
    if (!container) {
        console.error('[AdsRenderer] adsGrid container not found');
        return;
    }
    
    // Get current client ID
    const clientId = window.appStateGet?.('currentClientId') || 
                     document.getElementById('clientSelect')?.value;
    
    if (!clientId) {
        renderEmpty(container, 'Please select a client first');
        return;
    }
    
    // Check if we need to reload (client changed or no cache)
    const cachedClientId = getAdsCurrentClientId();
    const cachedAds = getAdsCache();
    
    if (cachedClientId === clientId && cachedAds.length > 0) {
        // Use cached data
        renderAdsGrid(container, cachedAds);
        return;
    }
    
    // Load fresh data
    showLoading(container);
    setAdsLoading(true);
    setAdsError(null);
    
    try {
        const response = await fetchFacebookAds(clientId);
        const ads = response.items || [];
        
        setAdsCache(ads);
        setAdsCurrentClientId(clientId);
        setAdsLoading(false);
        
        renderAdsGrid(container, ads);
    } catch (error) {
        console.error('[AdsRenderer] Failed to load ads:', error);
        setAdsLoading(false);
        setAdsError(error.message);
        renderError(container, error.message);
    }
}

/**
 * Show loading state
 * @param {HTMLElement} container - Container element
 */
function showLoading(container) {
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
function renderError(container, message) {
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
 * Render grid of ad cards
 * @param {HTMLElement} container - Container element
 * @param {Array} ads - Array of ad objects
 */
export function renderAdsGrid(container, ads) {
    if (!ads || ads.length === 0) {
        renderEmpty(container);
        return;
    }
    
    container.innerHTML = ads.map(ad => renderAdCard(ad)).join('');
    
    // Attach event delegation for interactive elements
    attachEventListeners(container);
}

/**
 * Render single ad card with mockup and collapsible details
 * @param {Object} ad - Ad object from API
 * @returns {string} HTML string
 */
function renderAdCard(ad) {
    const id = escapeHtml(ad.id || '');
    const status = escapeHtml(ad.status || 'draft');
    const statusClass = `ads-card__status--${status}`;
    
    // Ad content
    const primaryText = ad.primary_text || '';
    const headline = escapeHtml(ad.headline || '');
    const description = escapeHtml(ad.description || '');
    const cta = formatCTA(ad.call_to_action);
    const destinationUrl = ad.destination_url || '';
    const displayUrl = extractDomain(destinationUrl);
    const imageHash = escapeHtml(ad.image_hash || 'No image prompt available');
    const vocEvidence = ad.voc_evidence || [];
    
    // Format primary text for display
    const formattedPrimaryText = formatPrimaryText(primaryText);
    
    // Get client info for the mockup
    const navLogo = document.getElementById('navClientLogo');
    const logoSrc = navLogo ? navLogo.src : '';
    const clientSelect = document.getElementById('clientSelect');
    const clientName = clientSelect?.selectedOptions?.[0]?.textContent?.trim() || 'Sponsored';
    
    // VoC evidence HTML
    const vocHtml = vocEvidence.length > 0 
        ? `<ul class="ads-card__voc-list">
            ${vocEvidence.map(quote => `<li class="ads-card__voc-item">"${escapeHtml(quote)}"</li>`).join('')}
           </ul>`
        : '<p class="ads-card__detail-value">No VoC evidence available</p>';
    
    return `
        <div class="ads-card" data-ad-id="${id}">
            <div class="ads-card__header">
                <span class="ads-card__status ${statusClass}">${status}</span>
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
            
            <div class="ads-card__details">
                <button class="ads-card__toggle">
                    <span>Image Prompt & VoC Evidence</span>
                    <span class="ads-card__toggle-icon">▼</span>
                </button>
                <div class="ads-card__details-content">
                    <div class="ads-card__details-inner">
                        <div class="ads-card__detail-section">
                            <div class="ads-card__detail-label">Image Prompt</div>
                            <div class="ads-card__detail-value">${imageHash}</div>
                        </div>
                        <div class="ads-card__detail-section">
                            <div class="ads-card__detail-label">VoC Evidence</div>
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
 * @param {string} cta - CTA value
 * @returns {string} Formatted CTA text
 */
function formatCTA(cta) {
    if (!cta) return 'Learn more';
    const words = cta.toLowerCase().split('_');
    words[0] = words[0].charAt(0).toUpperCase() + words[0].slice(1);
    return words.join(' ');
}

/**
 * Extract domain from URL for display
 * @param {string} url - Full URL
 * @returns {string} Domain only
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
 * @param {string} text - Raw primary text
 * @returns {string} HTML formatted text
 */
function formatPrimaryText(text) {
    if (!text) return '';
    
    // Unescape JSON sequences and normalize line breaks
    let rawText = text
        .replace(/\\n/g, '\n')
        .replace(/\\"/g, '"')
        .replace(/\r\n/g, '\n')
        .replace(/\r/g, '\n');
    
    // Split into paragraphs
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
 * @param {HTMLElement} container - Container element
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
        
        // Handle toggle button
        const toggleBtn = e.target.closest('.ads-card__toggle');
        if (toggleBtn) {
            const details = toggleBtn.closest('.ads-card__details');
            if (details) {
                details.classList.toggle('expanded');
            }
            return;
        }
    });
}

/**
 * Handle ad deletion
 * @param {string} adId - Ad UUID
 * @param {HTMLElement} container - Container element
 */
async function handleDeleteAd(adId, container) {
    if (!confirm('Are you sure you want to delete this ad?')) {
        return;
    }
    
    try {
        await deleteFacebookAd(adId);
        removeAdFromCache(adId);
        
        // Re-render with updated cache
        const ads = getAdsCache();
        renderAdsGrid(container, ads);
    } catch (error) {
        console.error('[AdsRenderer] Failed to delete ad:', error);
        alert('Failed to delete ad: ' + error.message);
    }
}

// Expose globally for legacy compatibility
window.initAdsPage = initAdsPage;
