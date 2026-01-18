/**
 * Verbatims Renderer
 * Handles rendering of verbatim cards in the overlay
 */

import { highlightSearchTerms } from '/js/utils/format.js';
import { escapeHtml } from '/js/utils/dom.js';

/**
 * Load metadata settings from localStorage
 * @returns {Object} Settings object with show flags
 */
function loadMetadataSettings() {
    try {
        const saved = localStorage.getItem('verbatimMetadataSettings');
        if (saved) {
            return JSON.parse(saved);
        }
    } catch (e) {
        console.warn('Failed to load metadata settings:', e);
    }
    // Default settings
    return {
        showSentiment: true,
        showLocation: true,
        showIndex: true
    };
}

/**
 * Render verbatim cards in the overlay container
 * @param {Array} verbatims - Array of verbatim objects
 * @param {string} topicName - Current topic name
 * @param {string} categoryName - Current category name
 * @param {string} verbatimSearchTerm - Current search term
 * @param {string} currentCategoryName - Category name for subtitle
 */
export function renderVerbatims(verbatims, topicName, categoryName, verbatimSearchTerm = '', currentCategoryName = '') {
    // Get escapeHtml with fallback
    const escapeHtmlFn = escapeHtml || window.escapeHtml || ((s) => {
        if (s == null) return '';
        const div = document.createElement('div');
        div.textContent = s;
        return div.innerHTML;
    });
    
    // Get highlightSearchTerms with fallback
    const highlightFn = highlightSearchTerms || window.highlightSearchTerms || ((text) => escapeHtmlFn(text));
    
    const container = document.getElementById('verbatims');
    if (!container) return;
    
    const settings = loadMetadataSettings();
    
    // Filter verbatims based on search term
    const searchTerm = (verbatimSearchTerm || '').toLowerCase().trim();
    const filteredVerbatims = searchTerm === '' 
        ? verbatims 
        : verbatims.filter(v => {
            const text = (v.text || '').toLowerCase();
            const city = (v.city || '').toLowerCase();
            const country = (v.country || '').toLowerCase();
            const sentiment = (v.sentiment || '').toLowerCase();
            const index = String(v.index || '').toLowerCase();
            
            return text.includes(searchTerm) || 
                   city.includes(searchTerm) || 
                   country.includes(searchTerm) || 
                   sentiment.includes(searchTerm) ||
                   index.includes(searchTerm);
        });
    
    // Update subtitle with filtered count
    const subtitle = document.getElementById('overlaySubtitle');
    const displayCategoryName = currentCategoryName || categoryName;
    if (subtitle && displayCategoryName) {
        if (searchTerm === '') {
            subtitle.textContent = `${displayCategoryName} • ${verbatims.length} verbatim${verbatims.length !== 1 ? 's' : ''}`;
        } else {
            subtitle.textContent = `${displayCategoryName} • ${filteredVerbatims.length} of ${verbatims.length} verbatim${verbatims.length !== 1 ? 's' : ''}`;
        }
    }
    
    // Clear and populate verbatims
    container.innerHTML = '';

    if (filteredVerbatims.length === 0 && searchTerm !== '') {
        container.innerHTML = '<div style="padding: 40px; text-align: center; color: #999; font-size: 14px;">No verbatims match your search</div>';
        return;
    }

    filteredVerbatims.forEach((v, index) => {
        const card = document.createElement('div');
        card.className = 'verbatim-card';
        
        const sentimentClass = v.sentiment ? `sentiment-${v.sentiment}` : 'sentiment-neutral';
        // Highlight search terms if there's a search
        const highlightedText = searchTerm ? highlightFn(v.text || 'No text available', verbatimSearchTerm) : escapeHtmlFn(v.text || 'No text available');
        const escapedCity = v.city ? escapeHtmlFn(v.city) : '';
        const escapedCountry = v.country ? escapeHtmlFn(v.country) : '';
        
        // Build metadata HTML based on settings
        const metaItems = [];
        
        if (settings.showSentiment) {
            metaItems.push(`
                <div class="verbatim-meta-item">
                    <span class="verbatim-meta-label">Sentiment:</span>
                    <span class="sentiment ${sentimentClass}">${v.sentiment || 'neutral'}</span>
                </div>
            `);
        }
        
        if (settings.showLocation && v.country) {
            metaItems.push(`
                <div class="verbatim-meta-item">
                    <span class="verbatim-meta-label">Location:</span>
                    <span>${escapedCity ? escapedCity + ', ' : ''}${escapedCountry}</span>
                </div>
            `);
        }
        
        if (settings.showIndex) {
            metaItems.push(`
                <div class="verbatim-meta-item">
                    <span class="verbatim-meta-label">Index:</span>
                    <span>#${v.index}</span>
                </div>
            `);
        }
        
        // Only show metadata section if there are items to display
        const metaHTML = metaItems.length > 0 ? `
            <div class="verbatim-meta">
                ${metaItems.join('')}
            </div>
        ` : '';
        
        // Store verbatim data in a data attribute for the onclick handler
        // Use base64 encoding with Unicode-safe encoding
        const verbatimJson = JSON.stringify(v);
        const verbatimData = btoa(unescape(encodeURIComponent(verbatimJson)));
        
        card.innerHTML = `
            <div class="verbatim-card-header">
                <div class="verbatim-text" style="flex: 1; margin-bottom: 0; padding-right: 8px;">${highlightedText}</div>
                <button class="create-insight-button" data-verbatim="${verbatimData}" onclick="createInsightFromVerbatim(this)" title="Create insight from this verbatim" style="background: none; border: none; cursor: pointer; padding: 4px; display: flex; align-items: center; justify-content: center; color: oklch(0.556 0 0); transition: all 0.2s ease;" onmouseover="this.style.color='#B9F040'" onmouseout="this.style.color='oklch(0.556 0 0)'">
                    <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 5v14M5 12h14"/>
                    </svg>
                </button>
            </div>
            ${metaHTML ? `<div style="margin-top: 16px;">${metaHTML}</div>` : ''}
        `;
        
        container.appendChild(card);
    });
}
