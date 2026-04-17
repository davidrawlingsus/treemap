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
export function isVideoUrl(url) {
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
 * @param {string} [params.posterUrl] - Poster/thumbnail URL for video ads (shown when video 403s or is loading)
 * @param {boolean} [params.readOnly=false] - If true, hide edit controls
 * @param {boolean} [params.muted=true] - If false, render video without muted attribute
 * @returns {string} HTML string
 */
export function renderFBAdMockup({ adId, primaryText, headline, description, cta, displayUrl, logoSrc, clientName, imageUrl, posterUrl, readOnly = false, muted = true, analysisJson = null }) {
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

    const isGated = window.currentClientIsLead && !window.leadAdsRevealed && !readOnly;
    const gatedClass = isGated ? ' pe-fb-ad--lead-gated' : '';
    const gatedWrapperClass = isGated ? ' pe-fb-ad__primary-text-wrapper--gated' : '';
    const gateOverlayHtml = isGated ? `
                <div style="position:absolute;top:2em;left:0;right:0;bottom:0;min-height:80px;background:linear-gradient(to bottom,rgba(255,255,255,0) 0%,rgba(255,255,255,0.85) 25%,#fff 50%);display:flex;align-items:center;justify-content:center;flex-direction:column;gap:6px;z-index:2;">
                    <div style="display:flex;flex-direction:column;align-items:center;gap:6px;margin-top:8px;">
                        <div onclick="if(window.Calendly){Calendly.initPopupWidget({url:'https://calendly.com/david-rawlings-gfm7/mapthegap-strategy-call'});return false;}" style="background:#B9F040;color:#1a1a1a;font-weight:700;font-size:14px;padding:10px 28px;border-radius:6px;cursor:pointer;border:2px solid #a8d835;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;white-space:nowrap;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.1);">Book a Strategy Call</div>
                        <div style="font-size:12px;color:#65676b;text-align:center;">& Test These Ads For Free</div>
                    </div>
                </div>` : '';

    return `
        <div class="pe-fb-ad${gatedClass}" style="margin:0;padding:0;border:1px solid #dce0e5;display:block;width:100%;background:#fff;border-radius:8px;box-shadow:0 1px 2px rgba(0,0,0,0.1);overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;font-size:15px;line-height:1.3333;color:#050505;">
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
            <div class="pe-fb-ad__primary-text-wrapper${gatedWrapperClass}" style="padding:8px 12px;margin:0;${isGated ? 'position:relative;' : ''}">
                <div class="pe-fb-ad__primary-text" style="font-size:15px;line-height:1.4;color:#050505;margin:0;padding:0;">${primaryText}</div>
                ${gateOverlayHtml}
            </div>
            ${analysisJson ? buildInlineCritiqueHtml(analysisJson) : ''}
            <div class="pe-fb-ad__media ${imageUrl ? 'has-image' : ''}" style="width:100%;${imageUrl ? '' : 'aspect-ratio:1.91/1;'}position:relative;cursor:pointer;margin:0;padding:0;${imageUrl ? '' : 'background:linear-gradient(to top right,transparent calc(50% - 1px),#9ca3af calc(50% - 1px),#9ca3af calc(50% + 1px),transparent calc(50% + 1px)),linear-gradient(to top left,transparent calc(50% - 1px),#9ca3af calc(50% - 1px),#9ca3af calc(50% + 1px),transparent calc(50% + 1px)),#e5e7eb;'}">
                ${imageUrl ? (isVideoUrl(imageUrl)
                    ? `<div class="pe-fb-ad__video-wrapper">
                        <video src="${escapeHtml(imageUrl)}" ${posterUrl ? `poster="${escapeHtml(getOptimizedImageUrl(posterUrl, 500, 80))}"` : ''} playsinline preload="metadata"></video>
                        <div class="pe-fb-ad__video-play-btn">
                            <svg width="48" height="48" viewBox="0 0 48 48" fill="none"><circle cx="24" cy="24" r="24" fill="rgba(0,0,0,0.5)"/><path d="M19 15L35 24L19 33V15Z" fill="white"/></svg>
                        </div>
                        <div class="pe-fb-ad__video-controls">
                            <button class="pe-fb-ad__video-ctrl-btn pe-fb-ad__video-playpause" type="button" aria-label="Play">
                                <svg class="pe-fb-ad__icon-play" width="14" height="14" viewBox="0 0 14 14" fill="white"><path d="M3 1L12 7L3 13V1Z"/></svg>
                                <svg class="pe-fb-ad__icon-pause" width="14" height="14" viewBox="0 0 14 14" fill="white" style="display:none"><rect x="2" y="1" width="3.5" height="12"/><rect x="8.5" y="1" width="3.5" height="12"/></svg>
                            </button>
                            <div class="pe-fb-ad__video-progress">
                                <div class="pe-fb-ad__video-progress-fill"></div>
                            </div>
                            <span class="pe-fb-ad__video-time">0:00</span>
                            <button class="pe-fb-ad__video-ctrl-btn pe-fb-ad__video-mute" type="button" aria-label="Mute">
                                <svg class="pe-fb-ad__icon-unmuted" width="14" height="14" viewBox="0 0 16 16" fill="white"><path d="M8 2L4 6H1v4h3l4 4V2z"/><path d="M11.4 4.6a5 5 0 010 6.8M13.5 2.5a8 8 0 010 11" stroke="white" stroke-width="1.3" fill="none" stroke-linecap="round"/></svg>
                                <svg class="pe-fb-ad__icon-muted" width="14" height="14" viewBox="0 0 16 16" fill="white" style="display:none"><path d="M8 2L4 6H1v4h3l4 4V2z"/><path d="M12 5l4 4M16 5l-4 4" stroke="white" stroke-width="1.3" fill="none" stroke-linecap="round"/></svg>
                            </button>
                        </div>
                    </div>`
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

// ============ Inline Critique Card (matches Chrome extension injection) ============

function buildInlineCritiqueHtml(analysis) {
    if (!analysis || !analysis.grade) return '';

    const grade = escapeHtml(analysis.grade || '');

    const gradeColors = {
        'A': 'background:#dcfce7;color:#166534;', 'A+': 'background:#dcfce7;color:#166534;', 'A-': 'background:#dcfce7;color:#166534;',
        'B': 'background:#ecfccb;color:#3f6212;', 'B+': 'background:#ecfccb;color:#3f6212;', 'B-': 'background:#ecfccb;color:#3f6212;',
        'C': 'background:#fef9c3;color:#854d0e;', 'C+': 'background:#fef9c3;color:#854d0e;', 'C-': 'background:#fef9c3;color:#854d0e;',
        'D': 'background:#fee2e2;color:#991b1b;', 'D+': 'background:#fee2e2;color:#991b1b;', 'D-': 'background:#fee2e2;color:#991b1b;',
        'F': 'background:#fecaca;color:#7f1d1d;',
    };

    const latencyColors = { 'low': 'background:#dcfce7;color:#166534;', 'medium': 'background:#fef9c3;color:#854d0e;', 'high': 'background:#fee2e2;color:#991b1b;' };
    const funnelColors = { 'tof': 'background:#dbeafe;color:#1e40af;', 'mof': 'background:#ede9fe;color:#5b21b6;', 'bof': 'background:#dcfce7;color:#166534;' };

    function parseScoreField(raw) {
        if (!raw) return null;
        const m = raw.match(/^(\d+)\s*(?:\/10\s*)?[—–\-]\s*(.+)$/);
        if (m) return { num: parseInt(m[1], 10), text: m[2].trim() };
        const numOnly = raw.match(/^(\d+)/);
        return numOnly ? { num: parseInt(numOnly[1], 10), text: '' } : null;
    }

    function scoreColorStyle(num) {
        return num >= 7 ? 'color:#166534;' : num >= 4 ? 'color:#a16207;' : 'color:#b91c1c;';
    }

    function scoreRow(label, raw) {
        const s = parseScoreField(raw);
        if (!s) return '';
        return `
            <div style="padding:5px 0;border-bottom:1px solid #f0f2f5;">
                <div style="display:flex;justify-content:space-between;align-items:center;font-size:12px;gap:8px;">
                    <span style="color:#1c1e21;font-weight:700;font-size:11px;">${escapeHtml(label)}</span>
                    <span style="font-weight:800;font-size:12px;${scoreColorStyle(s.num)}">${s.num}/10</span>
                </div>
                ${s.text ? `<div style="font-size:11px;color:#4b4f56;line-height:1.4;margin-top:1px;">${escapeHtml(s.text)}</div>` : ''}
            </div>`;
    }

    function tagRow(label, raw, colorMap) {
        if (!raw) return '';
        const m = raw.match(/^(\S+)\s*[—–\-]\s*(.+)$/);
        if (m) {
            const tagStyle = colorMap[m[1].toLowerCase()] || 'background:rgba(55,53,47,0.06);color:#1c1e21;';
            return `
                <div style="padding:5px 0;border-bottom:1px solid #f0f2f5;">
                    <div style="display:flex;justify-content:space-between;align-items:center;font-size:12px;gap:8px;">
                        <span style="color:#1c1e21;font-weight:700;font-size:11px;">${escapeHtml(label)}</span>
                        <span style="display:inline-block;padding:1px 7px;border-radius:4px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.3px;${tagStyle}">${escapeHtml(m[1])}</span>
                    </div>
                    <div style="font-size:11px;color:#4b4f56;line-height:1.4;margin-top:1px;">${escapeHtml(m[2])}</div>
                </div>`;
        }
        return `<div style="padding:5px 0;border-bottom:1px solid #f0f2f5;"><div style="display:flex;justify-content:space-between;align-items:center;font-size:12px;"><span style="color:#1c1e21;font-weight:700;font-size:11px;">${escapeHtml(label)}</span></div><div style="font-size:11px;color:#4b4f56;line-height:1.4;margin-top:1px;">${escapeHtml(raw)}</div></div>`;
    }

    const gradeStyle = gradeColors[grade] || 'background:#f0f2f5;color:#1c1e21;';

    return `
        <div style="margin:0;padding:14px 16px;background:#fff;border-left:3px solid #B9F040;border-top:1px solid #e4e6eb;font-family:Lato,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:13px;color:#1c1e21;line-height:1.4;box-sizing:border-box;">
            <div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:6px;">
                ${grade ? `<span style="display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:6px;font-size:14px;font-weight:900;flex-shrink:0;${gradeStyle}">${grade}</span>` : ''}
                ${analysis.verdict ? `<span style="font-size:13px;font-weight:700;color:#1c1e21;line-height:1.3;">${escapeHtml(analysis.verdict)}</span>` : ''}
            </div>
            ${analysis.weakness ? `<div style="font-size:12px;color:#b91c1c;margin-bottom:6px;line-height:1.3;padding-left:38px;">Weakness: ${escapeHtml(analysis.weakness)}</div>` : ''}
            ${scoreRow('Hook', analysis.hook)}
            ${scoreRow('Mind Movie', analysis.mind_movie)}
            ${scoreRow('Specificity', analysis.specificity)}
            ${scoreRow('Emotion', analysis.emotion)}
            ${scoreRow('VoC Density', analysis.voc_density)}
            ${tagRow('Latency', analysis.latency, latencyColors)}
            ${tagRow('Funnel', analysis.funnel, funnelColors)}
            ${analysis.longevity ? `<div style="margin-top:6px;padding-top:6px;border-top:1px solid #f0f2f5;font-size:11px;color:#8a8d91;font-style:italic;line-height:1.3;">${escapeHtml(analysis.longevity)}</div>` : ''}
        </div>`;
}


// ============ Video Player Controller ============

export function initVideoPlayerControls() {
    if (window._vzdVideoControlsInit) return;
    window._vzdVideoControlsInit = true;
    _registerVideoHandlers();
}

function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

function getWrapper(el) {
    return el.closest('.pe-fb-ad__video-wrapper');
}

function getVideo(wrapper) {
    return wrapper?.querySelector('video');
}

function updatePlayPauseIcons(wrapper, playing) {
    wrapper.classList.toggle('is-playing', playing);
    const playIcon = wrapper.querySelector('.pe-fb-ad__icon-play');
    const pauseIcon = wrapper.querySelector('.pe-fb-ad__icon-pause');
    if (playIcon) playIcon.style.display = playing ? 'none' : '';
    if (pauseIcon) pauseIcon.style.display = playing ? '' : 'none';
}

function updateMuteIcons(wrapper, muted) {
    const unmutedIcon = wrapper.querySelector('.pe-fb-ad__icon-unmuted');
    const mutedIcon = wrapper.querySelector('.pe-fb-ad__icon-muted');
    if (unmutedIcon) unmutedIcon.style.display = muted ? 'none' : '';
    if (mutedIcon) mutedIcon.style.display = muted ? '' : 'none';
}

function _registerVideoHandlers() {
    // Capture phase — fires before any bubbling-phase stopPropagation
    document.addEventListener('click', (e) => {
        const wrapper = e.target.closest('.pe-fb-ad__video-wrapper');
        if (!wrapper) return;

        const video = wrapper.querySelector('video');
        if (!video) return;

        // Progress bar seek
        const progressBar = e.target.closest('.pe-fb-ad__video-progress');
        if (progressBar) {
            e.stopPropagation();
            e.preventDefault();
            if (video.duration) {
                const rect = progressBar.getBoundingClientRect();
                const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
                video.currentTime = pct * video.duration;
            }
            return;
        }

        // Mute toggle
        if (e.target.closest('.pe-fb-ad__video-mute')) {
            e.stopPropagation();
            e.preventDefault();
            video.muted = !video.muted;
            updateMuteIcons(wrapper, video.muted);
            return;
        }

        // Play/pause (button or anywhere on wrapper except controls)
        const controls = e.target.closest('.pe-fb-ad__video-controls');
        if (e.target.closest('.pe-fb-ad__video-playpause') || !controls) {
            e.stopPropagation();
            e.preventDefault();
            const p = video.paused ? video.play() : (video.pause(), null);
            if (p?.catch) p.catch(() => {});
        }
    }, true);

    // State listeners (capture phase)
    document.addEventListener('play', (e) => {
        if (e.target.tagName !== 'VIDEO') return;
        const w = getWrapper(e.target);
        if (w) updatePlayPauseIcons(w, true);
    }, true);

    document.addEventListener('pause', (e) => {
        if (e.target.tagName !== 'VIDEO') return;
        const w = getWrapper(e.target);
        if (w) updatePlayPauseIcons(w, false);
    }, true);

    document.addEventListener('timeupdate', (e) => {
        if (e.target.tagName !== 'VIDEO') return;
        const w = getWrapper(e.target);
        if (!w) return;
        const fill = w.querySelector('.pe-fb-ad__video-progress-fill');
        const timeEl = w.querySelector('.pe-fb-ad__video-time');
        if (fill && e.target.duration) fill.style.width = (e.target.currentTime / e.target.duration * 100) + '%';
        if (timeEl) timeEl.textContent = formatTime(e.target.currentTime);
    }, true);

    document.addEventListener('loadedmetadata', (e) => {
        if (e.target.tagName !== 'VIDEO') return;
        const w = getWrapper(e.target);
        if (!w) return;
        const timeEl = w.querySelector('.pe-fb-ad__video-time');
        if (timeEl) timeEl.textContent = formatTime(e.target.duration);
    }, true);
} // end _registerVideoHandlers
