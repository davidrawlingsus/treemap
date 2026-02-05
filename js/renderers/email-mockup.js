/**
 * Email Mockup Renderer
 * Renders email proposals as realistic email mockups during streaming.
 * Similar pattern to fb-ad-mockup.js for Facebook ads.
 */

import { escapeHtml, escapeHtmlForAttribute } from '/js/utils/dom.js';

/**
 * Check if the idea object is an email format
 * @param {Object} idea - Idea data object
 * @returns {boolean} True if email format
 */
export function isEmailFormat(idea) {
    return !!(idea.subject_line && idea.body_text && (idea.cta_text || idea.cta_url));
}

/**
 * Format body text with proper HTML paragraphs
 * @param {string} text - Raw body text
 * @returns {string} Formatted HTML
 */
export function formatEmailBodyText(text) {
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
            return `<p style="margin:0 0 ${isLast ? '0' : '16px'} 0;font-size:15px;line-height:1.6;color:#2d3748;">${para}</p>`;
        })
        .join('');
}

/**
 * Get sequence position label
 * @param {number} position - Sequence position (1-7)
 * @param {number} delayHours - Send delay in hours
 * @returns {string} Human-readable label
 */
function getSequenceLabel(position, delayHours) {
    if (delayHours === 0) return 'Immediate';
    if (delayHours <= 24) return 'Day 1';
    if (delayHours <= 48) return 'Day 2';
    if (delayHours <= 72) return 'Day 3';
    if (delayHours <= 96) return 'Day 4';
    if (delayHours <= 120) return 'Day 5';
    if (delayHours <= 144) return 'Day 6';
    if (delayHours <= 168) return 'Day 7';
    return `Day ${Math.ceil(delayHours / 24)}`;
}

/**
 * Render email mockup HTML
 * @param {Object} params - Email parameters
 * @param {string} params.emailId - Email unique ID
 * @param {number} params.sequencePosition - Position in sequence (1-7)
 * @param {number} params.sendDelayHours - Hours after trigger to send
 * @param {string} params.subjectLine - Email subject line
 * @param {string} params.previewText - Email preview text
 * @param {string} params.fromName - Sender name
 * @param {string} params.headline - Email headline/greeting
 * @param {string} params.bodyText - Main email body text
 * @param {string} params.ctaText - Call to action button text
 * @param {string} params.ctaUrl - CTA destination URL
 * @param {string} [params.discountCode] - Discount code to display
 * @param {string} [params.socialProof] - Customer testimonial/quote
 * @param {string[]} [params.vocEvidence] - VoC evidence array
 * @param {string} [params.strategicIntent] - Strategic intent description
 * @param {string} [params.logoSrc] - Logo image URL
 * @param {string} [params.clientName] - Client/brand name
 * @param {boolean} [params.readOnly=false] - If true, hide add button
 * @returns {string} HTML string
 */
export function renderEmailMockup({
    emailId,
    sequencePosition,
    sendDelayHours,
    subjectLine,
    previewText,
    fromName,
    headline,
    bodyText,
    ctaText,
    ctaUrl,
    discountCode,
    socialProof,
    vocEvidence = [],
    strategicIntent,
    logoSrc,
    clientName,
    readOnly = false
}) {
    const uniqueId = emailId || `email-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const formattedBody = formatEmailBodyText(bodyText);
    const sequenceLabel = getSequenceLabel(sequencePosition, sendDelayHours);
    
    // Get client logo from nav if not provided
    if (!logoSrc) {
        const navLogo = document.getElementById('navClientLogo');
        logoSrc = navLogo ? navLogo.src : '';
    }
    
    // Get client name from dropdown if not provided
    if (!clientName) {
        const clientSelect = document.getElementById('clientSelect');
        clientName = clientSelect?.selectedOptions?.[0]?.textContent?.trim() || 'Brand';
    }

    // Build VoC evidence HTML
    let vocHTML = '';
    if (vocEvidence && vocEvidence.length > 0) {
        const vocItems = vocEvidence.map(quote => 
            `<div class="pe-email-mockup__voc-item">"${escapeHtml(quote)}"</div>`
        ).join('');
        vocHTML = `
            <div class="pe-email-mockup__voc">
                <div class="pe-email-mockup__voc-label">VoC Evidence</div>
                <div class="pe-email-mockup__voc-list">${vocItems}</div>
            </div>`;
    }

    // Build strategy section
    let strategyHTML = '';
    if (strategicIntent) {
        strategyHTML = `
            <div class="pe-email-mockup__strategy">
                <div class="pe-email-mockup__strategy-label">Strategic Intent</div>
                <div class="pe-email-mockup__strategy-text">${escapeHtml(strategicIntent)}</div>
            </div>`;
    }

    // Build the email data object for the add button
    const emailData = {
        email_id: emailId,
        sequence_position: sequencePosition,
        send_delay_hours: sendDelayHours,
        subject_line: subjectLine,
        preview_text: previewText,
        from_name: fromName,
        headline: headline,
        body_text: bodyText,
        cta_text: ctaText,
        cta_url: ctaUrl,
        discount_code: discountCode,
        social_proof: socialProof,
        voc_evidence: vocEvidence,
        strategic_intent: strategicIntent
    };

    const addButtonHTML = readOnly ? '' : `
        <button class="pe-email-mockup__add" type="button" title="Save email" 
            data-email='${escapeHtmlForAttribute(JSON.stringify(emailData))}'
            style="width:28px;height:28px;border-radius:50%;border:none;background:#B9F040;color:#1a202c;font-size:16px;font-weight:700;cursor:pointer;flex-shrink:0;">+</button>`;

    return `
        <div class="pe-email-wrapper" data-email-id="${uniqueId}" style="margin:0;padding:32px 0 0 0;border-top:1px solid #cbd5e0;">
            ${vocHTML}
            <div class="pe-email-mockup" style="margin:24px 0 16px 0;border:1px solid #e2e8f0;border-radius:12px;background:#fff;overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
                
                <!-- Email Header (Gmail-style) -->
                <div style="padding:16px 20px;background:#f8fafc;border-bottom:1px solid #e2e8f0;">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
                        <div style="flex:1;min-width:0;">
                            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                                <span style="display:inline-flex;align-items:center;justify-content:center;background:#e0e7ff;color:#3730a3;font-size:11px;font-weight:600;padding:4px 8px;border-radius:4px;text-transform:uppercase;letter-spacing:0.5px;">
                                    Email ${sequencePosition || ''}${sequenceLabel ? ` • ${sequenceLabel}` : ''}
                                </span>
                            </div>
                            <div style="font-size:13px;color:#718096;margin-bottom:4px;">
                                <span style="font-weight:500;">From:</span> ${escapeHtml(fromName || 'Brand')}
                            </div>
                            <div style="font-weight:600;font-size:16px;color:#1a202c;line-height:1.3;margin-bottom:4px;">
                                ${escapeHtml(subjectLine || 'Subject line')}
                            </div>
                            ${previewText ? `<div style="font-size:13px;color:#718096;line-height:1.4;">${escapeHtml(previewText)}</div>` : ''}
                        </div>
                        ${addButtonHTML}
                    </div>
                </div>
                
                <!-- Email Body Preview -->
                <div style="padding:24px 20px;max-width:600px;">
                    ${logoSrc ? `
                        <div style="margin-bottom:20px;">
                            <img src="${escapeHtml(logoSrc)}" alt="${escapeHtml(clientName)} Logo" style="height:36px;width:auto;object-fit:contain;">
                        </div>
                    ` : ''}
                    
                    ${headline ? `
                        <div style="font-size:20px;font-weight:600;color:#1a202c;margin-bottom:16px;line-height:1.3;">
                            ${escapeHtml(headline)}
                        </div>
                    ` : ''}
                    
                    ${discountCode ? `
                        <div style="background:#f8fafc;border:2px dashed #B9F040;padding:16px;text-align:center;font-size:24px;font-weight:700;letter-spacing:3px;margin:20px 0;border-radius:8px;color:#1a202c;font-family:monospace;">
                            ${escapeHtml(discountCode)}
                        </div>
                    ` : ''}
                    
                    <div style="margin:16px 0;">
                        ${formattedBody}
                    </div>
                    
                    ${socialProof ? `
                        <div style="background:#f8fafc;padding:16px;margin:24px 0;border-left:4px solid #B9F040;font-style:italic;color:#4a5568;border-radius:0 8px 8px 0;font-size:14px;line-height:1.5;">
                            ${escapeHtml(socialProof)}
                        </div>
                    ` : ''}
                    
                    ${ctaText ? `
                        <div style="margin:24px 0;">
                            <a href="${escapeHtml(ctaUrl || '#')}" style="display:inline-block;background:#B9F040;color:#1a202c;padding:14px 28px;text-decoration:none;border-radius:6px;font-weight:600;font-size:15px;">
                                ${escapeHtml(ctaText)}
                            </a>
                        </div>
                    ` : ''}
                    
                    <!-- Simulated email footer -->
                    <div style="margin-top:32px;padding-top:16px;border-top:1px solid #e2e8f0;font-size:12px;color:#a0aec0;">
                        <span style="opacity:0.7;">Questions? Just hit reply — we're real humans.</span>
                        <div style="margin-top:12px;">
                            <a href="#" style="color:#a0aec0;text-decoration:underline;">Unsubscribe</a>
                            <span style="margin:0 8px;">•</span>
                            <a href="#" style="color:#a0aec0;text-decoration:underline;">Manage Preferences</a>
                        </div>
                    </div>
                </div>
            </div>
            ${strategyHTML}
        </div>
    `;
}

/**
 * Generate email card HTML from idea JSON (for markdown-converter integration)
 * @param {Object} idea - Email data object from LLM
 * @returns {string} HTML string for email mockup
 */
export function generateEmailCardHTML(idea) {
    // Get client logo from nav if available
    const navLogo = document.getElementById('navClientLogo');
    const logoSrc = navLogo ? navLogo.src : '';
    
    // Get client name from dropdown
    const clientSelect = document.getElementById('clientSelect');
    const clientName = clientSelect?.selectedOptions?.[0]?.textContent?.trim() || 'Brand';

    return renderEmailMockup({
        emailId: idea.email_id,
        sequencePosition: idea.sequence_position,
        sendDelayHours: idea.send_delay_hours,
        subjectLine: idea.subject_line,
        previewText: idea.preview_text,
        fromName: idea.from_name,
        headline: idea.headline,
        bodyText: idea.body_text,
        ctaText: idea.cta_text,
        ctaUrl: idea.cta_url,
        discountCode: idea.discount_code,
        socialProof: idea.social_proof,
        vocEvidence: idea.voc_evidence || [],
        strategicIntent: idea.strategic_intent,
        logoSrc: logoSrc,
        clientName: clientName,
        readOnly: false
    });
}

/**
 * Render email mockup for saved emails tab (with edit icon and edit controls)
 * Used by emails-renderer.js for the Emails tab.
 * Follows the same pattern as fb-ad-mockup.js renderFBAdMockup.
 * 
 * @param {Object} params - Email parameters
 * @param {string} params.emailId - Email UUID from database
 * @param {string} params.subjectLine - Email subject line
 * @param {string} params.previewText - Email preview text
 * @param {string} params.fromName - Sender name
 * @param {string} params.headline - Email headline/greeting
 * @param {string} params.bodyText - Main email body text
 * @param {string} params.ctaText - Call to action button text
 * @param {string} params.ctaUrl - CTA destination URL
 * @param {string} [params.discountCode] - Discount code to display
 * @param {string} [params.socialProof] - Customer testimonial/quote
 * @param {number} [params.sequencePosition] - Position in sequence
 * @param {number} [params.sendDelayHours] - Hours after trigger
 * @param {string} [params.logoSrc] - Logo image URL
 * @param {string} [params.clientName] - Client/brand name
 * @param {string} [params.imageUrl] - Image URL for the email
 * @param {string} [params.sequenceBadgeText] - Custom sequence badge text (overrides computed value)
 * @param {boolean} [params.readOnly=false] - If true, hide edit controls
 * @param {number} [params.laneEmailCount=7] - Number of emails in the lane (for dropdown options)
 * @returns {string} HTML string
 */
export function renderEmailMockupForSaved({
    emailId,
    subjectLine,
    previewText,
    fromName,
    headline,
    bodyText,
    ctaText,
    ctaUrl,
    discountCode,
    socialProof,
    sequencePosition,
    sendDelayHours,
    logoSrc,
    clientName,
    imageUrl,
    sequenceBadgeText,
    readOnly = false,
    laneEmailCount = 7
}) {
    const formattedBody = formatEmailBodyText(bodyText);
    
    // Calculate day number from send_delay_hours
    const dayNumber = sendDelayHours ? Math.ceil(sendDelayHours / 24) : 1;
    const currentPosition = sequencePosition || 1;
    
    // Generate position options for dropdown (max of laneEmailCount + 1 to allow adding new position)
    const maxOptions = Math.max(laneEmailCount + 1, 7);
    const positionOptionsHtml = Array.from({ length: maxOptions }, (_, i) => i + 1)
        .map(pos => `<option value="${pos}" ${pos === currentPosition ? 'selected' : ''}>Email ${pos}</option>`)
        .join('');
    
    // Generate day options for dropdown (days 1-30, plus current value if higher)
    const maxDay = Math.max(30, dayNumber);
    const dayOptionsHtml = Array.from({ length: maxDay }, (_, i) => i + 1)
        .map(day => `<option value="${day}" ${day === dayNumber ? 'selected' : ''}>Day ${day}</option>`)
        .join('');
    
    // Edit icon HTML (pencil button)
    const editIconHtml = readOnly ? '' : `
        <button class="pe-email-mockup__edit-icon" data-email-id="${emailId}" title="Edit email text" type="button">
            <img src="https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/icons/edit.png" alt="Edit" width="16" height="16">
        </button>`;
    
    // Edit controls HTML (Cancel/Save buttons)
    const editControlsHtml = readOnly ? '' : `
        <div class="pe-email-mockup__edit-controls" data-email-id="${emailId}">
            <button class="pe-email-mockup__edit-cancel" data-email-id="${emailId}" type="button">Cancel</button>
            <button class="pe-email-mockup__edit-save" data-email-id="${emailId}" type="button">Save</button>
        </div>`;
    
    // Image section HTML (if image exists)
    const imageHtml = imageUrl ? `
        <div class="pe-email-mockup__media has-image" style="margin:16px 0;position:relative;">
            <img src="${escapeHtml(imageUrl)}" alt="Email image" style="width:100%;height:auto;display:block;border-radius:8px;">
            ${!readOnly ? `<button class="pe-email-mockup__media-delete" data-email-id="${emailId}" title="Remove image" type="button"><img src="https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/icons/delete_button.png" alt="Delete" width="12" height="12"></button>` : ''}
        </div>
    ` : '';

    return `
        <div class="pe-email-mockup" data-email-id="${emailId}" style="margin:0;border:1px solid #e2e8f0;border-radius:12px;background:#fff;overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;box-shadow:0 2px 8px rgba(0,0,0,0.08);position:relative;">
            ${editIconHtml}
            
            <!-- Email Header (Gmail-style) -->
            <div style="padding:16px 20px;background:#f8fafc;border-bottom:1px solid #e2e8f0;">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
                    <div style="flex:1;min-width:0;">
                        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                            <div class="pe-email-mockup__sequence-pill">
                                <select class="pe-email-mockup__email-position" data-email-id="${emailId}">
                                    ${positionOptionsHtml}
                                </select>
                            </div>
                            <div class="pe-email-mockup__day-pill">
                                <select class="pe-email-mockup__day-select" data-email-id="${emailId}">
                                    ${dayOptionsHtml}
                                </select>
                            </div>
                        </div>
                        <div style="font-size:13px;color:#718096;margin-bottom:4px;">
                            <span style="font-weight:500;">From:</span> ${escapeHtml(fromName || 'Brand')}
                        </div>
                        <div class="pe-email-mockup__subject-line" style="font-weight:600;font-size:16px;color:#1a202c;line-height:1.3;margin-bottom:4px;">
                            ${escapeHtml(subjectLine || 'Subject line')}
                        </div>
                        ${previewText ? `<div class="pe-email-mockup__preview-text" style="font-size:13px;color:#718096;line-height:1.4;">${escapeHtml(previewText)}</div>` : '<div class="pe-email-mockup__preview-text" style="font-size:13px;color:#718096;line-height:1.4;"></div>'}
                    </div>
                </div>
            </div>
            
            <!-- Email Body Preview -->
            <div style="padding:24px 20px;max-width:600px;">
                ${logoSrc ? `
                    <div style="margin-bottom:20px;">
                        <img src="${escapeHtml(logoSrc)}" alt="${escapeHtml(clientName)} Logo" style="height:36px;width:auto;object-fit:contain;">
                    </div>
                ` : ''}
                
                ${headline ? `
                    <div class="pe-email-mockup__headline" style="font-size:20px;font-weight:600;color:#1a202c;margin-bottom:16px;line-height:1.3;">
                        ${escapeHtml(headline)}
                    </div>
                ` : '<div class="pe-email-mockup__headline" style="font-size:20px;font-weight:600;color:#1a202c;margin-bottom:16px;line-height:1.3;"></div>'}
                
                ${discountCode ? `
                    <div style="background:#f8fafc;border:2px dashed #B9F040;padding:16px;text-align:center;font-size:24px;font-weight:700;letter-spacing:3px;margin:20px 0;border-radius:8px;color:#1a202c;font-family:monospace;">
                        ${escapeHtml(discountCode)}
                    </div>
                ` : ''}
                
                ${imageHtml}
                
                <div class="pe-email-mockup__body-text" style="margin:16px 0;">
                    ${formattedBody}
                </div>
                
                ${socialProof ? `
                    <div style="background:#f8fafc;padding:16px;margin:24px 0;border-left:4px solid #B9F040;font-style:italic;color:#4a5568;border-radius:0 8px 8px 0;font-size:14px;line-height:1.5;">
                        ${escapeHtml(socialProof)}
                    </div>
                ` : ''}
                
                ${ctaText ? `
                    <div style="margin:24px 0;">
                        <span class="pe-email-mockup__cta-text" style="display:inline-block;background:#B9F040;color:#1a202c;padding:14px 28px;text-decoration:none;border-radius:6px;font-weight:600;font-size:15px;">
                            ${escapeHtml(ctaText)}
                        </span>
                    </div>
                ` : '<div style="margin:24px 0;"><span class="pe-email-mockup__cta-text" style="display:inline-block;background:#B9F040;color:#1a202c;padding:14px 28px;text-decoration:none;border-radius:6px;font-weight:600;font-size:15px;"></span></div>'}
                
                <!-- Simulated email footer -->
                <div style="margin-top:32px;padding-top:16px;border-top:1px solid #e2e8f0;font-size:12px;color:#a0aec0;">
                    <span style="opacity:0.7;">Questions? Just hit reply — we're real humans.</span>
                    <div style="margin-top:12px;">
                        <a href="#" style="color:#a0aec0;text-decoration:underline;">Unsubscribe</a>
                        <span style="margin:0 8px;">•</span>
                        <a href="#" style="color:#a0aec0;text-decoration:underline;">Manage Preferences</a>
                    </div>
                </div>
            </div>
            ${editControlsHtml}
        </div>
    `;
}
