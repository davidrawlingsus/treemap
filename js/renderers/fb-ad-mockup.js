/**
 * Facebook Ad Mockup Renderer
 * Shared module for rendering Facebook ad mockups.
 * Used by both ads-renderer.js (list view) and ads-kanban-renderer.js (hover preview).
 */

import { escapeHtml } from '/js/utils/dom.js';
import { getOptimizedImageUrl } from '/js/utils/image.js';

/**
 * Check if URL is a video based on file extension
 * @param {string} url - Media URL
 * @returns {boolean}
 */
function isVideoUrl(url) {
    if (!url) return false;
    const videoExtensions = ['.mp4', '.webm', '.mov', '.avi', '.mkv', '.m4v'];
    const lowerUrl = url.toLowerCase();
    return videoExtensions.some(ext => lowerUrl.includes(ext));
}

/**
 * Render Facebook ad mockup HTML
 * @param {Object} params - Ad parameters
 * @param {string} params.adId - Ad UUID
 * @param {string} params.primaryText - Formatted primary text HTML
 * @param {string} params.headline - Escaped headline text
 * @param {string} params.description - Escaped description text
 * @param {string} params.cta - Call to action text
 * @param {string} params.displayUrl - Display URL (domain only)
 * @param {string} params.logoSrc - Client logo URL
 * @param {string} params.clientName - Client/page name
 * @param {string} [params.imageUrl] - Image URL for the ad
 * @param {boolean} [params.readOnly=false] - If true, hide edit controls
 * @returns {string} HTML string
 */
export function renderFBAdMockup({ adId, primaryText, headline, description, cta, displayUrl, logoSrc, clientName, imageUrl, readOnly = false }) {
    const profilePicContent = logoSrc 
        ? `<img src="${escapeHtml(logoSrc)}" alt="Client Logo" style="width:40px;height:40px;border-radius:50%;object-fit:contain;background:#fff;">`
        : 'Ad';
    const profilePicStyle = logoSrc
        ? 'width:40px;height:40px;min-width:40px;min-height:40px;border-radius:50%;overflow:hidden;flex-shrink:0;margin:0;padding:0;background:#fff;'
        : 'width:40px;height:40px;min-width:40px;min-height:40px;border-radius:50%;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:600;font-size:14px;flex-shrink:0;margin:0;padding:0;';

    const editIconHtml = readOnly ? '' : `
                <button class="pe-fb-ad__edit-icon" data-ad-id="${adId}" title="Edit ad text" type="button">
                    <img src="/images/edit.png" alt="Edit" width="16" height="16">
                </button>`;

    const editControlsHtml = readOnly ? '' : `
            <div class="pe-fb-ad__edit-controls" data-ad-id="${adId}" style="padding: 10px 12px !important;">
                <button class="pe-fb-ad__edit-cancel" data-ad-id="${adId}" type="button">Cancel</button>
                <button class="pe-fb-ad__edit-save" data-ad-id="${adId}" type="button">Save</button>
            </div>`;

    return `
        <div class="pe-fb-ad" style="margin:0;padding:0;border:1px solid #dce0e5;display:block;width:100%;background:#fff;border-radius:8px;box-shadow:0 1px 2px rgba(0,0,0,0.1);overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;font-size:15px;line-height:1.3333;color:#050505;">
            <div class="pe-fb-ad__header" style="padding:12px 12px 0;margin:0;display:flex;align-items:center;gap:8px;position:relative;">${editIconHtml}
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
            <div class="pe-fb-ad__media ${imageUrl ? 'has-image' : ''}" style="width:100%;${imageUrl ? '' : 'aspect-ratio:1.91/1;'}position:relative;cursor:pointer;margin:0;padding:0;${imageUrl ? '' : 'background:linear-gradient(to top right,transparent calc(50% - 1px),#9ca3af calc(50% - 1px),#9ca3af calc(50% + 1px),transparent calc(50% + 1px)),linear-gradient(to top left,transparent calc(50% - 1px),#9ca3af calc(50% - 1px),#9ca3af calc(50% + 1px),transparent calc(50% + 1px)),#e5e7eb;'}">
                ${imageUrl ? (isVideoUrl(imageUrl) 
                    ? `<video src="${escapeHtml(imageUrl)}" style="width:100%;height:auto;display:block;object-fit:contain;" muted loop playsinline preload="metadata"></video>`
                    : `<img src="${escapeHtml(getOptimizedImageUrl(imageUrl, 500, 80))}" alt="Ad image" style="width:100%;height:auto;display:block;object-fit:contain;" loading="lazy">`) 
                : '<div class="pe-fb-ad__media-placeholder" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);color:#9ca3af;font-size:14px;pointer-events:none;">Click to add media</div>'}
                ${imageUrl && !readOnly ? `<button class="pe-fb-ad__media-delete" data-ad-id="${adId}" title="Remove media" type="button"><img src="/images/delete_button.png" alt="Delete" width="12" height="12"></button>` : ''}
            </div>
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
            </div>${editControlsHtml}
        </div>
    `;
}

/**
 * Format CTA value to sentence case (e.g., SHOP_NOW -> "Shop now")
 * @param {string} cta - CTA value from API
 * @returns {string} Formatted CTA text
 */
export function formatCTA(cta) {
    if (!cta) return 'Learn more';
    const words = cta.toLowerCase().split('_');
    words[0] = words[0].charAt(0).toUpperCase() + words[0].slice(1);
    return words.join(' ');
}

/**
 * Extract domain from URL for display
 * @param {string} url - Full URL
 * @returns {string} Domain name only
 */
export function extractDomain(url) {
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
 * @returns {string} Formatted HTML
 */
export function formatPrimaryText(text) {
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
