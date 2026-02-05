/**
 * Emails Renderer Module
 * Renders saved emails in horizontal lanes grouped by email_type.
 * Supports drag-and-drop reordering within lanes.
 */

import { deleteSavedEmail, updateSavedEmail } from '/js/services/api-emails.js';
import { getEmailsCache, removeEmailFromCache, updateEmailInCache, getEmailsSearchTerm, getEmailsFilters } from '/js/state/emails-state.js';
import { EMAIL_STATUS_OPTIONS, normalizeStatus, getStatusConfig, getEmailTypeLabel } from '/js/controllers/emails-filter-ui.js';
import { escapeHtml } from '/js/utils/dom.js';
import { renderEmailMockupForSaved, formatEmailBodyText } from '/js/renderers/email-mockup.js';

// Store event handler refs to prevent duplicates
let _emailsContainerClickHandler = null;
let _emailsContainerContextMenuHandler = null;
let _emailsDocumentClickHandler = null;
let _emailsContainerInputHandler = null;
let _emailsContainerKeydownHandler = null;
let _emailsContainerChangeHandler = null;
let _emailsEventContainer = null;

// Drag and drop state
let draggedCard = null;
let draggedEmailId = null;
let draggedLaneType = null;

// Lane order preference (most common first)
const LANE_ORDER = [
    'post_purchase_onboarding',
    'welcome',
    'cart_abandonment',
    'browse_abandonment',
    'replenishment_reminder',
    'winback',
    null // "Uncategorized" for emails without email_type
];

/**
 * Show loading state
 * @param {HTMLElement} container - Container element
 */
export function showLoading(container) {
    container.innerHTML = `
        <div class="emails-loading">
            <p>Loading emails...</p>
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
        <div class="emails-error">
            <p class="emails-error__text">${escapeHtml(message)}</p>
            <button class="emails-error__retry" onclick="window.initEmailsPage()">Retry</button>
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
        <div class="emails-empty">
            <div class="emails-empty__icon">📧</div>
            <h3 class="emails-empty__title">No emails yet</h3>
            <p class="emails-empty__text">${escapeHtml(message || 'Save email ideas from the Prompt Engineering tool')}</p>
        </div>
    `;
}

/**
 * Group emails by email_type
 * @param {Array} emails - Array of email objects
 * @returns {Object} Object with email_type as keys and arrays of emails as values
 */
function groupEmailsByType(emails) {
    const groups = {};
    
    emails.forEach(email => {
        const type = email.email_type || null;
        if (!groups[type]) {
            groups[type] = [];
        }
        groups[type].push(email);
    });
    
    // Sort emails within each group by sequence_position
    Object.keys(groups).forEach(type => {
        groups[type].sort((a, b) => {
            const posA = a.sequence_position || 999;
            const posB = b.sequence_position || 999;
            return posA - posB;
        });
    });
    
    return groups;
}

/**
 * Get sorted lane types based on preference order
 * @param {Object} emailsByType - Grouped emails object
 * @returns {Array} Sorted array of email types
 */
function getSortedLaneTypes(emailsByType) {
    const types = Object.keys(emailsByType);
    
    return types.sort((a, b) => {
        const aIndex = LANE_ORDER.indexOf(a === 'null' ? null : a);
        const bIndex = LANE_ORDER.indexOf(b === 'null' ? null : b);
        
        // If both are in the order, sort by index
        if (aIndex !== -1 && bIndex !== -1) {
            return aIndex - bIndex;
        }
        // If only one is in the order, it comes first
        if (aIndex !== -1) return -1;
        if (bIndex !== -1) return 1;
        // If neither is in the order, sort alphabetically
        return String(a).localeCompare(String(b));
    });
}

/**
 * Render horizontal lanes of email cards grouped by type
 * @param {HTMLElement} container - Container element
 * @param {Array} emails - Array of email objects (already filtered/sorted)
 */
export function renderEmailsGrid(container, emails) {
    const allEmails = getEmailsCache();
    const hasFiltersOrSearch = getEmailsSearchTerm() || getEmailsFilters().length > 0;
    
    if (!emails || emails.length === 0) {
        if (hasFiltersOrSearch && allEmails.length > 0) {
            renderEmpty(container, 'No emails match your search or filters');
        } else {
            renderEmpty(container);
        }
        return;
    }
    
    // Group emails by type
    const emailsByType = groupEmailsByType(emails);
    const sortedTypes = getSortedLaneTypes(emailsByType);
    
    // Render lanes container
    container.innerHTML = `<div class="emails-lanes-container">
        ${sortedTypes.map(type => renderLane(type, emailsByType[type])).join('')}
    </div>`;
    
    // Attach event delegation for interactive elements
    attachEventListeners(container);
    
    // Initialize drag and drop
    initDragAndDrop(container);
}

/**
 * Render a single horizontal lane for an email type
 * @param {string|null} emailType - Email type (or null for uncategorized)
 * @param {Array} emails - Array of emails for this type
 * @returns {string} HTML string
 */
function renderLane(emailType, emails) {
    const typeLabel = emailType ? getEmailTypeLabel(emailType) : 'Uncategorized';
    const typeClass = emailType ? `emails-lane__type-badge--${emailType}` : '';
    const count = emails.length;
    
    return `
        <div class="emails-lane" data-email-type="${escapeHtml(emailType || '')}">
            <div class="emails-lane__header">
                <div class="emails-lane__title">
                    <span class="emails-lane__type-badge ${typeClass}">${escapeHtml(typeLabel)}</span>
                    <span class="emails-lane__count">${count} email${count !== 1 ? 's' : ''}</span>
                </div>
            </div>
            <div class="emails-lane__cards" data-email-type="${escapeHtml(emailType || '')}">
                ${emails.map(email => renderEmailCard(email, emails)).join('')}
            </div>
        </div>
    `;
}

/**
 * Render single email card with mockup and collapsible details
 * @param {Object} email - Email object from API
 * @param {Array} laneEmails - All emails in the same lane (for position dropdown)
 * @returns {string} HTML string
 */
function renderEmailCard(email, laneEmails = []) {
    const id = escapeHtml(email.id || '');
    const normalizedStatus = normalizeStatus(email.status);
    const statusConfig = getStatusConfig(normalizedStatus);
    const statusClass = `emails-card__status--${normalizedStatus}`;
    
    const vocEvidence = email.voc_evidence || [];
    const strategicIntent = email.strategic_intent || '';
    const emailType = email.email_type;
    const emailTypeLabel = getEmailTypeLabel(emailType);
    
    const vocHtml = vocEvidence.length > 0 
        ? `<ul class="emails-card__voc-list">
            ${vocEvidence.map(quote => `<li class="emails-card__voc-item">"${escapeHtml(quote)}"</li>`).join('')}
           </ul>`
        : '<p class="emails-card__detail-value">No VoC evidence available</p>';
    
    const strategyHtml = strategicIntent
        ? `<p class="emails-accordion__text">${escapeHtml(strategicIntent)}</p>`
        : '<p class="emails-card__detail-value">No strategic intent provided</p>';
    
    // Render status dropdown options
    const statusOptionsHtml = EMAIL_STATUS_OPTIONS.map(opt => `
        <button class="emails-card__status-option ${opt.id === normalizedStatus ? 'active' : ''}" 
                data-status="${opt.id}">
            ${escapeHtml(opt.label)}
        </button>
    `).join('');
    
    // Get client info for the mockup
    const navLogo = document.getElementById('navClientLogo');
    const logoSrc = navLogo ? navLogo.src : '';
    const clientSelect = document.getElementById('clientSelect');
    const clientName = clientSelect?.selectedOptions?.[0]?.textContent?.trim() || 'Brand';
    
    return `
        <div class="emails-card" data-email-id="${id}" data-email-type="${escapeHtml(emailType || '')}" draggable="true">
            <div class="emails-card__header">
                <div class="emails-card__header-left">
                    <div class="emails-card__status-wrapper">
                        <button class="emails-card__status ${statusClass}" data-email-id="${id}" title="Click to change status">
                            ${escapeHtml(statusConfig.label)}
                            <span class="emails-card__status-chevron">▼</span>
                        </button>
                        <div class="emails-card__status-dropdown">
                            ${statusOptionsHtml}
                        </div>
                    </div>
                </div>
                <div class="emails-card__actions">
                    <button class="emails-card__delete" data-email-id="${id}" title="Delete email">×</button>
                </div>
            </div>
            
            <div class="emails-card__mockup">
                ${renderEmailMockupForSaved({
                    emailId: id,
                    subjectLine: email.subject_line,
                    previewText: email.preview_text,
                    fromName: email.from_name,
                    headline: email.headline,
                    bodyText: email.body_text,
                    ctaText: email.cta_text,
                    ctaUrl: email.cta_url,
                    discountCode: email.discount_code,
                    socialProof: email.social_proof,
                    sequencePosition: email.sequence_position,
                    sendDelayHours: email.send_delay_hours,
                    logoSrc,
                    clientName,
                    imageUrl: email.full_json?.image_url || null,
                    sequenceBadgeText: email.full_json?.sequence_badge_text || null,
                    readOnly: false,
                    laneEmailCount: laneEmails.length
                })}
            </div>
            
            <div class="emails-card__accordions">
                <div class="emails-accordion">
                    <button class="emails-accordion__trigger" data-accordion="voc-evidence">
                        <span class="emails-accordion__title">VoC Evidence</span>
                        <svg class="emails-accordion__chevron" width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M4 6L8 10L12 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </button>
                    <div class="emails-accordion__content">
                        <div class="emails-accordion__body">
                            ${vocHtml}
                        </div>
                    </div>
                </div>
                <div class="emails-accordion">
                    <button class="emails-accordion__trigger" data-accordion="strategy">
                        <span class="emails-accordion__title">Strategic Intent</span>
                        <svg class="emails-accordion__chevron" width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M4 6L8 10L12 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </button>
                    <div class="emails-accordion__content">
                        <div class="emails-accordion__body">
                            ${strategyHtml}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// ============ Drag and Drop ============

/**
 * Initialize drag and drop functionality for email lanes
 * @param {HTMLElement} container - Container element
 */
function initDragAndDrop(container) {
    const cards = container.querySelectorAll('.emails-card');
    const lanes = container.querySelectorAll('.emails-lane__cards');
    
    // Card drag events
    cards.forEach(card => {
        card.addEventListener('dragstart', handleDragStart);
        card.addEventListener('dragend', handleDragEnd);
    });
    
    // Lane drop zone events
    lanes.forEach(lane => {
        lane.addEventListener('dragover', handleDragOver);
        lane.addEventListener('dragleave', handleDragLeave);
        lane.addEventListener('drop', handleDrop);
    });
}

/**
 * Handle drag start
 * @param {DragEvent} e - Drag event
 */
function handleDragStart(e) {
    const card = e.target.closest('.emails-card');
    if (!card) return;
    
    draggedCard = card;
    draggedEmailId = card.dataset.emailId;
    draggedLaneType = card.dataset.emailType;
    
    card.classList.add('is-dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', draggedEmailId);
    
    // Set drag image
    requestAnimationFrame(() => {
        card.style.opacity = '0.5';
    });
}

/**
 * Handle drag end
 * @param {DragEvent} e - Drag event
 */
function handleDragEnd(e) {
    const card = e.target.closest('.emails-card');
    if (card) {
        card.classList.remove('is-dragging');
        card.style.opacity = '';
    }
    
    // Remove all drag states
    document.querySelectorAll('.emails-card').forEach(c => {
        c.classList.remove('drag-target-before', 'drag-target-after');
    });
    document.querySelectorAll('.emails-lane').forEach(l => {
        l.classList.remove('drag-over');
    });
    
    // Remove all drop indicators
    document.querySelectorAll('.emails-drop-indicator').forEach(ind => {
        ind.remove();
    });
    
    draggedCard = null;
    draggedEmailId = null;
    draggedLaneType = null;
}

/**
 * Handle drag over
 * @param {DragEvent} e - Drag event
 */
function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    
    const lane = e.target.closest('.emails-lane__cards');
    if (!lane) return;
    
    // Only allow drops within same email type lane
    const laneType = lane.dataset.emailType;
    if (laneType !== draggedLaneType) {
        e.dataTransfer.dropEffect = 'none';
        return;
    }
    
    lane.closest('.emails-lane')?.classList.add('drag-over');
    
    // Find the card we're hovering over
    const cards = Array.from(lane.querySelectorAll('.emails-card:not(.is-dragging)'));
    const hoveredCard = e.target.closest('.emails-card');
    
    // Clear previous indicators from cards
    cards.forEach(c => {
        c.classList.remove('drag-target-before', 'drag-target-after');
    });
    
    // Remove any existing drop indicator
    const existingIndicator = lane.querySelector('.emails-drop-indicator');
    
    if (hoveredCard && hoveredCard !== draggedCard) {
        // Determine if we should place before or after based on mouse position
        const rect = hoveredCard.getBoundingClientRect();
        const midpoint = rect.left + rect.width / 2;
        
        const insertBefore = e.clientX < midpoint;
        
        if (insertBefore) {
            hoveredCard.classList.add('drag-target-before');
        } else {
            hoveredCard.classList.add('drag-target-after');
        }
        
        // Insert or move the drop indicator element
        if (!existingIndicator) {
            const indicator = document.createElement('div');
            indicator.className = 'emails-drop-indicator';
            indicator.innerHTML = '<div class="emails-drop-indicator__line"></div>';
            
            if (insertBefore) {
                hoveredCard.insertAdjacentElement('beforebegin', indicator);
            } else {
                hoveredCard.insertAdjacentElement('afterend', indicator);
            }
        } else {
            // Move existing indicator
            if (insertBefore) {
                hoveredCard.insertAdjacentElement('beforebegin', existingIndicator);
            } else {
                hoveredCard.insertAdjacentElement('afterend', existingIndicator);
            }
        }
    } else if (!hoveredCard && cards.length > 0) {
        // If hovering at the end of the lane (past all cards), show indicator at end
        const lastCard = cards[cards.length - 1];
        if (lastCard) {
            lastCard.classList.add('drag-target-after');
            if (!existingIndicator) {
                const indicator = document.createElement('div');
                indicator.className = 'emails-drop-indicator';
                indicator.innerHTML = '<div class="emails-drop-indicator__line"></div>';
                lastCard.insertAdjacentElement('afterend', indicator);
            } else {
                lastCard.insertAdjacentElement('afterend', existingIndicator);
            }
        }
    }
}

/**
 * Handle drag leave
 * @param {DragEvent} e - Drag event
 */
function handleDragLeave(e) {
    const lane = e.target.closest('.emails-lane__cards');
    if (!lane) return;
    
    // Only remove class if actually leaving the lane
    if (!lane.contains(e.relatedTarget)) {
        lane.closest('.emails-lane')?.classList.remove('drag-over');
        
        // Clear indicators
        lane.querySelectorAll('.emails-card').forEach(c => {
            c.classList.remove('drag-target-before', 'drag-target-after');
        });
        
        // Remove drop indicator element
        const indicator = lane.querySelector('.emails-drop-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
}

/**
 * Handle drop
 * @param {DragEvent} e - Drag event
 */
async function handleDrop(e) {
    e.preventDefault();
    
    const lane = e.target.closest('.emails-lane__cards');
    if (!lane || !draggedCard || !draggedEmailId) return;
    
    // Only allow drops within same email type lane
    const laneType = lane.dataset.emailType;
    if (laneType !== draggedLaneType) return;
    
    lane.closest('.emails-lane')?.classList.remove('drag-over');
    
    // Remove drop indicator element
    const indicator = lane.querySelector('.emails-drop-indicator');
    if (indicator) {
        indicator.remove();
    }
    
    // Find insertion point
    const cards = Array.from(lane.querySelectorAll('.emails-card:not(.is-dragging)'));
    const targetCard = cards.find(c => 
        c.classList.contains('drag-target-before') || c.classList.contains('drag-target-after')
    );
    
    // Clear indicators
    cards.forEach(c => {
        c.classList.remove('drag-target-before', 'drag-target-after');
    });
    
    // Calculate new position
    let newPosition;
    if (!targetCard) {
        // Dropped at end
        newPosition = cards.length + 1;
    } else {
        const targetIndex = cards.indexOf(targetCard);
        const insertBefore = targetCard.classList.contains('drag-target-before');
        newPosition = insertBefore ? targetIndex + 1 : targetIndex + 2;
    }
    
    // Get current position
    const emails = getEmailsCache();
    const email = emails.find(e => e.id === draggedEmailId);
    const currentPosition = email?.sequence_position || 1;
    
    // If position hasn't changed, do nothing
    if (newPosition === currentPosition) return;
    
    // Perform the reorder
    await reorderEmailsInLane(draggedEmailId, newPosition, laneType);
}

/**
 * Reorder emails in a lane after drag and drop
 * @param {string} movedEmailId - ID of the email that was moved
 * @param {number} newPosition - New sequence position
 * @param {string} laneType - Email type of the lane
 */
async function reorderEmailsInLane(movedEmailId, newPosition, laneType) {
    const emails = getEmailsCache();
    
    // Filter to emails in this lane
    const laneEmails = emails.filter(e => (e.email_type || '') === laneType);
    
    // Sort by current sequence_position
    laneEmails.sort((a, b) => (a.sequence_position || 999) - (b.sequence_position || 999));
    
    // Find the moved email and its current index
    const movedEmail = laneEmails.find(e => e.id === movedEmailId);
    if (!movedEmail) return;
    
    const currentIndex = laneEmails.indexOf(movedEmail);
    
    // Remove from current position
    laneEmails.splice(currentIndex, 1);
    
    // Insert at new position (convert to 0-based index)
    const newIndex = Math.max(0, Math.min(laneEmails.length, newPosition - 1));
    laneEmails.splice(newIndex, 0, movedEmail);
    
    // Calculate new sequence positions and day numbers
    const updates = [];
    let previousDay = 0;
    
    laneEmails.forEach((email, index) => {
        const newSeqPos = index + 1;
        
        // Calculate day based on position
        // First email is Day 1, subsequent emails increment
        let newDay;
        if (index === 0) {
            newDay = 1;
        } else {
            // Default to previous day + 1
            newDay = previousDay + 1;
        }
        
        const currentDay = Math.ceil((email.send_delay_hours || 0) / 24) || 1;
        const sendDelayHours = newDay * 24; // Convert day to hours
        
        // Only include in updates if position or day changed
        if (email.sequence_position !== newSeqPos || currentDay !== newDay) {
            updates.push({
                id: email.id,
                sequence_position: newSeqPos,
                send_delay_hours: sendDelayHours
            });
        }
        
        previousDay = newDay;
    });
    
    if (updates.length === 0) return;
    
    // Check if this will cascade changes to multiple emails
    if (updates.length > 1) {
        const shouldCascade = await showCascadeDialog(updates.length);
        if (!shouldCascade) {
            // Only update the moved email's position, not days
            const movedUpdate = updates.find(u => u.id === movedEmailId);
            if (movedUpdate) {
                try {
                    await updateSavedEmail(movedEmailId, {
                        sequence_position: movedUpdate.sequence_position
                    });
                    updateEmailInCache(movedEmailId, {
                        sequence_position: movedUpdate.sequence_position
                    });
                    
                    if (window.renderEmailsPage) {
                        window.renderEmailsPage();
                    }
                } catch (error) {
                    console.error('[EmailsRenderer] Failed to update position:', error);
                    alert('Failed to update position: ' + error.message);
                }
            }
            return;
        }
    }
    
    // Apply all updates
    try {
        // Update each email
        for (const update of updates) {
            await updateSavedEmail(update.id, {
                sequence_position: update.sequence_position,
                send_delay_hours: update.send_delay_hours
            });
            updateEmailInCache(update.id, {
                sequence_position: update.sequence_position,
                send_delay_hours: update.send_delay_hours
            });
        }
        
        // Re-render
        if (window.renderEmailsPage) {
            window.renderEmailsPage();
        }
    } catch (error) {
        console.error('[EmailsRenderer] Failed to reorder emails:', error);
        alert('Failed to reorder emails: ' + error.message);
        
        // Re-render to restore correct state
        if (window.renderEmailsPage) {
            window.renderEmailsPage();
        }
    }
}

/**
 * Show cascade confirmation dialog
 * @param {number} affectedCount - Number of emails affected
 * @returns {Promise<boolean>} True if user confirms cascade
 */
function showCascadeDialog(affectedCount) {
    return new Promise((resolve) => {
        // Create overlay
        const overlay = document.createElement('div');
        overlay.className = 'emails-cascade-dialog__overlay';
        
        // Create dialog
        const dialog = document.createElement('div');
        dialog.className = 'emails-cascade-dialog';
        dialog.innerHTML = `
            <h3 class="emails-cascade-dialog__title">Update Email Sequence?</h3>
            <p class="emails-cascade-dialog__text">
                This will update the sequence position and day numbers for ${affectedCount} emails 
                to maintain a logical order (Email 1 → Day 1, Email 2 → Day 2, etc.).
            </p>
            <div class="emails-cascade-dialog__actions">
                <button class="emails-cascade-dialog__btn emails-cascade-dialog__btn--skip">Position Only</button>
                <button class="emails-cascade-dialog__btn emails-cascade-dialog__btn--cancel">Cancel</button>
                <button class="emails-cascade-dialog__btn emails-cascade-dialog__btn--confirm">Update All</button>
            </div>
        `;
        
        document.body.appendChild(overlay);
        document.body.appendChild(dialog);
        
        // Handle button clicks
        dialog.querySelector('.emails-cascade-dialog__btn--confirm').addEventListener('click', () => {
            overlay.remove();
            dialog.remove();
            resolve(true);
        });
        
        dialog.querySelector('.emails-cascade-dialog__btn--cancel').addEventListener('click', () => {
            overlay.remove();
            dialog.remove();
            resolve(false);
        });
        
        dialog.querySelector('.emails-cascade-dialog__btn--skip').addEventListener('click', () => {
            overlay.remove();
            dialog.remove();
            resolve(false);
        });
        
        // Close on overlay click
        overlay.addEventListener('click', () => {
            overlay.remove();
            dialog.remove();
            resolve(false);
        });
    });
}

// ============ Edit Mode Functions ============

/**
 * Enable edit mode for an email
 * @param {string} emailId - Email UUID
 * @param {HTMLElement} emailCard - The emails-card element
 */
function enableEditMode(emailId, emailCard) {
    const mockup = emailCard.querySelector('.pe-email-mockup');
    if (!mockup) return;
    
    // Store original values for revert
    const subjectLineEl = mockup.querySelector('.pe-email-mockup__subject-line');
    const previewTextEl = mockup.querySelector('.pe-email-mockup__preview-text');
    const headlineEl = mockup.querySelector('.pe-email-mockup__headline');
    const bodyTextEl = mockup.querySelector('.pe-email-mockup__body-text');
    const ctaTextEl = mockup.querySelector('.pe-email-mockup__cta-text');
    const emailPositionSelect = mockup.querySelector('.pe-email-mockup__email-position');
    const daySelect = mockup.querySelector('.pe-email-mockup__day-select');
    
    // Store original values
    if (subjectLineEl) mockup.dataset.originalSubjectLine = subjectLineEl.innerHTML;
    if (previewTextEl) mockup.dataset.originalPreviewText = previewTextEl.innerHTML;
    if (headlineEl) mockup.dataset.originalHeadline = headlineEl.innerHTML;
    if (bodyTextEl) mockup.dataset.originalBodyText = bodyTextEl.innerHTML;
    if (ctaTextEl) mockup.dataset.originalCtaText = ctaTextEl.innerHTML;
    if (emailPositionSelect) mockup.dataset.originalEmailPosition = emailPositionSelect.value;
    if (daySelect) mockup.dataset.originalDay = daySelect.value;
    
    // Make elements contenteditable
    if (subjectLineEl) subjectLineEl.contentEditable = 'true';
    if (previewTextEl) previewTextEl.contentEditable = 'true';
    if (headlineEl) headlineEl.contentEditable = 'true';
    if (bodyTextEl) bodyTextEl.contentEditable = 'true';
    if (ctaTextEl) ctaTextEl.contentEditable = 'true';
    
    // Add edit mode class (CSS will show edit controls)
    mockup.classList.add('is-editing');
    
    // Focus first editable element
    if (subjectLineEl) subjectLineEl.focus();
}

/**
 * Disable edit mode and revert changes
 * @param {HTMLElement} emailCard - The emails-card element
 */
function disableEditMode(emailCard) {
    const mockup = emailCard.querySelector('.pe-email-mockup');
    if (!mockup) return;
    
    // Restore original values
    const subjectLineEl = mockup.querySelector('.pe-email-mockup__subject-line');
    const previewTextEl = mockup.querySelector('.pe-email-mockup__preview-text');
    const headlineEl = mockup.querySelector('.pe-email-mockup__headline');
    const bodyTextEl = mockup.querySelector('.pe-email-mockup__body-text');
    const ctaTextEl = mockup.querySelector('.pe-email-mockup__cta-text');
    const emailPositionSelect = mockup.querySelector('.pe-email-mockup__email-position');
    const daySelect = mockup.querySelector('.pe-email-mockup__day-select');
    
    if (subjectLineEl && mockup.dataset.originalSubjectLine !== undefined) {
        subjectLineEl.innerHTML = mockup.dataset.originalSubjectLine;
    }
    if (previewTextEl && mockup.dataset.originalPreviewText !== undefined) {
        previewTextEl.innerHTML = mockup.dataset.originalPreviewText;
    }
    if (headlineEl && mockup.dataset.originalHeadline !== undefined) {
        headlineEl.innerHTML = mockup.dataset.originalHeadline;
    }
    if (bodyTextEl && mockup.dataset.originalBodyText !== undefined) {
        bodyTextEl.innerHTML = mockup.dataset.originalBodyText;
    }
    if (ctaTextEl && mockup.dataset.originalCtaText !== undefined) {
        ctaTextEl.innerHTML = mockup.dataset.originalCtaText;
    }
    if (emailPositionSelect && mockup.dataset.originalEmailPosition !== undefined) {
        emailPositionSelect.value = mockup.dataset.originalEmailPosition;
    }
    if (daySelect && mockup.dataset.originalDay !== undefined) {
        daySelect.value = mockup.dataset.originalDay;
    }
    
    // Remove contenteditable
    if (subjectLineEl) subjectLineEl.contentEditable = 'false';
    if (previewTextEl) previewTextEl.contentEditable = 'false';
    if (headlineEl) headlineEl.contentEditable = 'false';
    if (bodyTextEl) bodyTextEl.contentEditable = 'false';
    if (ctaTextEl) ctaTextEl.contentEditable = 'false';
    
    // Remove edit mode class
    mockup.classList.remove('is-editing');
    
    // Clean up stored values
    delete mockup.dataset.originalSubjectLine;
    delete mockup.dataset.originalPreviewText;
    delete mockup.dataset.originalHeadline;
    delete mockup.dataset.originalBodyText;
    delete mockup.dataset.originalCtaText;
    delete mockup.dataset.originalEmailPosition;
    delete mockup.dataset.originalDay;
}

/**
 * Extract plain text from contenteditable element, preserving line breaks
 * @param {HTMLElement} element - Contenteditable element
 * @returns {string} Plain text with line breaks
 */
function extractTextContent(element) {
    if (!element) return '';
    
    let html = element.innerHTML || '';
    
    // Replace closing </p> and </div> tags with double newlines
    html = html.replace(/<\/p>/gi, '\n\n');
    html = html.replace(/<\/div>/gi, '\n\n');
    
    // Replace <br> and <br/> with single newlines
    html = html.replace(/<br\s*\/?>/gi, '\n');
    
    // Remove all remaining HTML tags
    html = html.replace(/<[^>]+>/g, '');
    
    // Decode HTML entities
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    let text = tempDiv.textContent || tempDiv.innerText || '';
    
    // Normalize: collapse multiple consecutive newlines
    text = text.replace(/\n{3,}/g, '\n\n');
    
    // Trim
    text = text.trim();
    
    return text;
}

/**
 * Save email edits to API
 * @param {string} emailId - Email UUID
 * @param {HTMLElement} emailCard - The emails-card element
 */
async function saveEmailEdits(emailId, emailCard) {
    const mockup = emailCard.querySelector('.pe-email-mockup');
    if (!mockup) return;
    
    const subjectLineEl = mockup.querySelector('.pe-email-mockup__subject-line');
    const previewTextEl = mockup.querySelector('.pe-email-mockup__preview-text');
    const headlineEl = mockup.querySelector('.pe-email-mockup__headline');
    const bodyTextEl = mockup.querySelector('.pe-email-mockup__body-text');
    const ctaTextEl = mockup.querySelector('.pe-email-mockup__cta-text');
    const emailPositionSelect = mockup.querySelector('.pe-email-mockup__email-position');
    const daySelect = mockup.querySelector('.pe-email-mockup__day-select');
    
    // Extract text content
    const subjectLine = extractTextContent(subjectLineEl);
    const previewText = extractTextContent(previewTextEl);
    const headline = extractTextContent(headlineEl);
    const bodyText = extractTextContent(bodyTextEl);
    const ctaText = extractTextContent(ctaTextEl);
    const sequencePosition = emailPositionSelect ? parseInt(emailPositionSelect.value, 10) : null;
    const dayNumber = daySelect ? parseInt(daySelect.value, 10) : null;
    const sendDelayHours = dayNumber ? dayNumber * 24 : null;
    
    // Disable save button during save
    const saveBtn = mockup.querySelector('.pe-email-mockup__edit-save');
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.textContent = 'Saving...';
    }
    
    try {
        // Update via API
        const updateData = {
            subject_line: subjectLine,
            preview_text: previewText || null,
            headline: headline || null,
            body_text: bodyText,
            cta_text: ctaText || null
        };
        
        if (sequencePosition !== null) {
            updateData.sequence_position = sequencePosition;
        }
        if (sendDelayHours !== null) {
            updateData.send_delay_hours = sendDelayHours;
        }
        
        await updateSavedEmail(emailId, updateData);
        
        // Update cache
        updateEmailInCache(emailId, updateData);
        
        // Exit edit mode
        disableEditMode(emailCard);
        
        // Re-render via controller
        if (window.renderEmailsPage) {
            window.renderEmailsPage();
        }
    } catch (error) {
        console.error('[EmailsRenderer] Failed to save email edits:', error);
        alert('Failed to save changes: ' + error.message);
        
        // Re-enable save button
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.textContent = 'Save';
        }
    }
}

// ============ Context Menu for Image Insertion ============

let activeContextMenu = null;

/**
 * Show context menu for image insertion
 * @param {number} x - X coordinate
 * @param {number} y - Y coordinate
 * @param {string} emailId - Email UUID
 * @param {HTMLElement} mockup - Email mockup element
 */
function showEmailContextMenu(x, y, emailId, mockup) {
    // Remove any existing context menu
    hideEmailContextMenu();
    
    const menu = document.createElement('div');
    menu.className = 'emails-context-menu';
    menu.innerHTML = `
        <button class="emails-context-menu__item" data-action="insert-image">
            <span class="emails-context-menu__icon">🖼️</span>
            Insert Image
        </button>
    `;
    
    // Position menu
    menu.style.position = 'fixed';
    menu.style.left = `${x}px`;
    menu.style.top = `${y}px`;
    menu.style.zIndex = '10000';
    
    document.body.appendChild(menu);
    activeContextMenu = menu;
    
    // Handle menu item clicks
    menu.addEventListener('click', async (e) => {
        const item = e.target.closest('.emails-context-menu__item');
        if (!item) return;
        
        const action = item.dataset.action;
        if (action === 'insert-image') {
            hideEmailContextMenu();
            await handleImageSelection(emailId, mockup);
        }
    });
    
    // Close menu on outside click
    setTimeout(() => {
        document.addEventListener('click', hideEmailContextMenu, { once: true });
    }, 0);
}

/**
 * Hide the context menu
 */
function hideEmailContextMenu() {
    if (activeContextMenu) {
        activeContextMenu.remove();
        activeContextMenu = null;
    }
}

/**
 * Handle image selection for an email
 * @param {string} emailId - Email UUID
 * @param {HTMLElement} mockup - Email mockup element
 */
async function handleImageSelection(emailId, mockup) {
    try {
        // Import image picker
        const { showImagePickerModal } = await import('/js/renderers/image-picker-modal.js');
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
                // Get current email to preserve full_json
                const emails = getEmailsCache();
                const email = emails.find(e => e.id === emailId);
                
                if (!email) {
                    throw new Error('Email not found');
                }
                
                // Update via API
                await updateSavedEmail(emailId, { 
                    image_url: imageUrl
                });
                
                // Update cache
                const updatedFullJson = {
                    ...email.full_json,
                    image_url: imageUrl
                };
                updateEmailInCache(emailId, { 
                    full_json: updatedFullJson
                });
                
                // Re-render via controller
                if (window.renderEmailsPage) {
                    window.renderEmailsPage();
                }
            } catch (error) {
                console.error('[EmailsRenderer] Failed to update image:', error);
                alert('Failed to update image: ' + error.message);
            }
        });
    } catch (error) {
        console.error('[EmailsRenderer] Failed to open image picker:', error);
        alert('Failed to open image picker: ' + error.message);
    }
}

/**
 * Handle image deletion for an email
 * @param {string} emailId - Email UUID
 */
async function handleImageDelete(emailId) {
    try {
        // Get current email to preserve full_json
        const emails = getEmailsCache();
        const email = emails.find(e => e.id === emailId);
        
        if (!email) {
            throw new Error('Email not found');
        }
        
        // Update via API
        await updateSavedEmail(emailId, { 
            image_url: null
        });
        
        // Update cache
        const updatedFullJson = {
            ...email.full_json
        };
        delete updatedFullJson.image_url;
        
        updateEmailInCache(emailId, { 
            full_json: updatedFullJson
        });
        
        // Re-render via controller
        if (window.renderEmailsPage) {
            window.renderEmailsPage();
        }
    } catch (error) {
        console.error('[EmailsRenderer] Failed to delete image:', error);
        alert('Failed to delete image: ' + error.message);
    }
}

// ============ Event Listeners ============

/**
 * Attach event listeners using event delegation
 */
function attachEventListeners(container) {
    // Remove old handlers if they exist
    if (_emailsEventContainer) {
        if (_emailsContainerClickHandler) {
            _emailsEventContainer.removeEventListener('click', _emailsContainerClickHandler);
        }
        if (_emailsContainerContextMenuHandler) {
            _emailsEventContainer.removeEventListener('contextmenu', _emailsContainerContextMenuHandler);
        }
        if (_emailsContainerInputHandler) {
            _emailsEventContainer.removeEventListener('input', _emailsContainerInputHandler);
        }
        if (_emailsContainerKeydownHandler) {
            _emailsEventContainer.removeEventListener('keydown', _emailsContainerKeydownHandler);
        }
        if (_emailsDocumentClickHandler) {
            document.removeEventListener('click', _emailsDocumentClickHandler);
        }
        if (_emailsContainerChangeHandler) {
            _emailsEventContainer.removeEventListener('change', _emailsContainerChangeHandler);
        }
    }
    
    _emailsEventContainer = container;
    
    // Click handler
    _emailsContainerClickHandler = async (e) => {
        // Handle edit icon click
        const editIcon = e.target.closest('.pe-email-mockup__edit-icon');
        if (editIcon) {
            e.stopPropagation();
            const emailId = editIcon.dataset.emailId;
            const emailCard = editIcon.closest('.emails-card');
            if (emailId && emailCard) {
                enableEditMode(emailId, emailCard);
            }
            return;
        }
        
        // Handle save button click
        const saveBtn = e.target.closest('.pe-email-mockup__edit-save');
        if (saveBtn) {
            e.stopPropagation();
            const emailId = saveBtn.dataset.emailId;
            const emailCard = saveBtn.closest('.emails-card');
            if (emailId && emailCard) {
                await saveEmailEdits(emailId, emailCard);
            }
            return;
        }
        
        // Handle cancel button click
        const cancelBtn = e.target.closest('.pe-email-mockup__edit-cancel');
        if (cancelBtn) {
            e.stopPropagation();
            const emailCard = cancelBtn.closest('.emails-card');
            if (emailCard) {
                disableEditMode(emailCard);
            }
            return;
        }
        
        // Handle delete button
        const deleteBtn = e.target.closest('.emails-card__delete');
        if (deleteBtn) {
            const emailId = deleteBtn.dataset.emailId;
            await handleDeleteEmail(emailId, container);
            return;
        }
        
        // Handle image delete button click
        const mediaDeleteBtn = e.target.closest('.pe-email-mockup__media-delete');
        if (mediaDeleteBtn) {
            e.stopPropagation();
            const emailId = mediaDeleteBtn.dataset.emailId;
            if (emailId) {
                await handleImageDelete(emailId);
            }
            return;
        }
        
        // Handle status pill click (toggle dropdown)
        const statusBtn = e.target.closest('.emails-card__status');
        if (statusBtn && !e.target.closest('.emails-card__status-dropdown')) {
            e.stopPropagation();
            const wrapper = statusBtn.closest('.emails-card__status-wrapper');
            // Close all other dropdowns first
            container.querySelectorAll('.emails-card__status-wrapper.open').forEach(w => {
                if (w !== wrapper) w.classList.remove('open');
            });
            wrapper?.classList.toggle('open');
            return;
        }
        
        // Handle status option selection
        const statusOption = e.target.closest('.emails-card__status-option');
        if (statusOption) {
            e.stopPropagation();
            const newStatus = statusOption.dataset.status;
            const card = statusOption.closest('.emails-card');
            const emailId = card?.dataset.emailId;
            if (emailId && newStatus) {
                await handleStatusChange(emailId, newStatus);
            }
            // Close dropdown
            statusOption.closest('.emails-card__status-wrapper')?.classList.remove('open');
            return;
        }
        
        // Handle accordion toggle
        const accordionTrigger = e.target.closest('.emails-accordion__trigger');
        if (accordionTrigger) {
            const mockup = accordionTrigger.closest('.pe-email-mockup');
            if (mockup && mockup.classList.contains('is-editing')) {
                return;
            }
            const accordion = accordionTrigger.closest('.emails-accordion');
            if (accordion) {
                accordion.classList.toggle('expanded');
            }
            return;
        }
        
        // Handle email position dropdown change
        const positionSelect = e.target.closest('.pe-email-mockup__email-position');
        if (positionSelect) {
            // Handled by change event
            return;
        }
    };
    
    container.addEventListener('click', _emailsContainerClickHandler);
    
    // Context menu handler for image insertion
    _emailsContainerContextMenuHandler = (e) => {
        const mockup = e.target.closest('.pe-email-mockup');
        if (!mockup) return;
        
        // Only show context menu if not in edit mode
        if (mockup.classList.contains('is-editing')) return;
        
        e.preventDefault();
        const card = mockup.closest('.emails-card');
        const emailId = card?.dataset.emailId;
        if (emailId) {
            showEmailContextMenu(e.clientX, e.clientY, emailId, mockup);
        }
    };
    
    container.addEventListener('contextmenu', _emailsContainerContextMenuHandler);
    
    // Document click handler for closing dropdowns
    _emailsDocumentClickHandler = (e) => {
        if (!e.target.closest('.emails-card__status-wrapper')) {
            container.querySelectorAll('.emails-card__status-wrapper.open').forEach(w => {
                w.classList.remove('open');
            });
        }
    };
    document.addEventListener('click', _emailsDocumentClickHandler);
    
    // Input handler for editing (for contenteditable elements)
    _emailsContainerInputHandler = (e) => {
        // This handler is kept for contenteditable elements if needed
    };
    container.addEventListener('input', _emailsContainerInputHandler);
    
    // Change handler for position dropdown
    _emailsContainerChangeHandler = async (e) => {
        const positionSelect = e.target.closest('.pe-email-mockup__email-position');
        if (!positionSelect) return;
        
        const mockup = positionSelect.closest('.pe-email-mockup');
        // Only auto-save if not in edit mode (direct position change)
        if (mockup && !mockup.classList.contains('is-editing')) {
            const card = positionSelect.closest('.emails-card');
            const emailId = card?.dataset.emailId;
            const newPosition = parseInt(positionSelect.value, 10);
            const emailType = card?.dataset.emailType || '';
            
            if (emailId && newPosition) {
                await reorderEmailsInLane(emailId, newPosition, emailType);
            }
        }
    };
    container.addEventListener('change', _emailsContainerChangeHandler);
    
    // Keydown handler for edit mode
    _emailsContainerKeydownHandler = (e) => {
        const mockup = e.target.closest('.pe-email-mockup.is-editing');
        if (!mockup) return;
        
        // Escape key - cancel editing
        if (e.key === 'Escape') {
            e.preventDefault();
            e.stopPropagation();
            const emailCard = mockup.closest('.emails-card');
            if (emailCard) {
                disableEditMode(emailCard);
            }
            return;
        }
        
        // Enter key in contenteditable
        if (e.key === 'Enter' && e.target.contentEditable === 'true') {
            const isBodyText = e.target.classList.contains('pe-email-mockup__body-text');
            const isSingleLine = !isBodyText;
            
            // For body text, insert <br>
            if (isBodyText) {
                e.preventDefault();
                if (document.execCommand) {
                    document.execCommand('insertLineBreak', false, null);
                } else {
                    const selection = window.getSelection();
                    if (selection.rangeCount > 0) {
                        const range = selection.getRangeAt(0);
                        const br = document.createElement('br');
                        range.deleteContents();
                        range.insertNode(br);
                        range.setStartAfter(br);
                        range.collapse(true);
                        selection.removeAllRanges();
                        selection.addRange(range);
                    }
                }
                return;
            }
            
            // For single-line fields, move to next field or blur
            if (isSingleLine && !e.shiftKey) {
                e.preventDefault();
                const fields = [
                    mockup.querySelector('.pe-email-mockup__subject-line'),
                    mockup.querySelector('.pe-email-mockup__preview-text'),
                    mockup.querySelector('.pe-email-mockup__headline'),
                    mockup.querySelector('.pe-email-mockup__body-text'),
                    mockup.querySelector('.pe-email-mockup__cta-text')
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
    container.addEventListener('keydown', _emailsContainerKeydownHandler);
}

/**
 * Handle email deletion
 */
async function handleDeleteEmail(emailId, container) {
    if (!confirm('Are you sure you want to delete this email?')) {
        return;
    }
    
    try {
        await deleteSavedEmail(emailId);
        removeEmailFromCache(emailId);
        
        // Re-render via controller
        if (window.renderEmailsPage) {
            window.renderEmailsPage();
        }
    } catch (error) {
        console.error('[EmailsRenderer] Failed to delete email:', error);
        alert('Failed to delete email: ' + error.message);
    }
}

/**
 * Handle status change
 * @param {string} emailId - Email UUID
 * @param {string} newStatus - New status value
 */
async function handleStatusChange(emailId, newStatus) {
    try {
        // Update via API
        await updateSavedEmail(emailId, { status: newStatus });
        
        // Update cache
        updateEmailInCache(emailId, { status: newStatus });
        
        // Re-render
        if (window.renderEmailsPage) {
            window.renderEmailsPage();
        }
    } catch (error) {
        console.error('[EmailsRenderer] Failed to update status:', error);
        alert('Failed to update status: ' + error.message);
    }
}
