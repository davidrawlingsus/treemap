/**
 * Insights Renderer
 * Handles rendering of insights table
 */

import { getDimensionDisplayName, highlightSearchTerms, toPascalCase } from '/js/utils/format.js';
import { escapeHtml } from '/js/utils/dom.js';
import { getCurrentQuestionRefKey } from '/js/state/app-state.js';
import {
    getAllInsights,
    getInsightsSearchTerm,
    getInsightsCurrentFilters,
    getInsightsSortBy,
    getInsightsSortOrder
} from '/js/state/insights-state.js';

/**
 * Render insights table
 * @param {Array} insights - Optional insights array (if not provided, uses state)
 */
export function renderInsights(insights) {
    const tbody = document.getElementById('insightsTableBody');
    if (!tbody) return;

    // Get state values
    const allInsights = getAllInsights();
    const insightsSearchTerm = getInsightsSearchTerm();
    const insightsFilters = getInsightsCurrentFilters(); // Using current filters as object
    const currentQuestionRefKey = getCurrentQuestionRefKey();
    const insightsSortBy = getInsightsSortBy();
    const insightsSortOrder = getInsightsSortOrder();

    let filtered = [...(insights || allInsights)];

    // Apply search
    if (insightsSearchTerm) {
        const term = insightsSearchTerm.toLowerCase();
        filtered = filtered.filter(insight =>
            insight.name?.toLowerCase().includes(term) ||
            insight.description?.toLowerCase().includes(term)
        );
    }

    // Apply filters
    Object.entries(insightsFilters || {}).forEach(([key, value]) => {
        if (value) {
            filtered = filtered.filter(insight => {
                // Filter logic (type filter removed)
                return true;
            });
        }
    });

    // Pin overviews for current dimension to top
    // Check if insight is type='Overview' and matches current dimension
    const isPinnedOverview = (insight) => {
        if (insight.type !== 'Overview') return false;
        if (!currentQuestionRefKey) return false; // No dimension selected, don't pin
        
        const origin = insight.origins?.[0] || {};
        
        // Match by dimension_ref (primary)
        if (origin.dimension_ref === currentQuestionRefKey) {
            return true;
        }
        
        // Fallback: Match by dimension name if dimension_ref doesn't match
        // Extract dimension name from insight name (format: "Overview: [Dimension Name]" or "Overview: - [Dimension Name]")
        const insightDimensionName = insight.name?.replace(/^Overview:\s*-?\s*/, '').trim() || '';
        const currentDimensionName = currentQuestionRefKey ? getDimensionDisplayName(currentQuestionRefKey) : null;
        
        // Match by dimension name if available
        if (insightDimensionName && currentDimensionName && insightDimensionName === currentDimensionName) {
            return true;
        }
        
        return false;
    };

    // Apply sorting with pinning
    filtered.sort((a, b) => {
        const aIsPinned = isPinnedOverview(a);
        const bIsPinned = isPinnedOverview(b);
        
        // Pinned items come first
        if (aIsPinned && !bIsPinned) return -1;
        if (!aIsPinned && bIsPinned) return 1;
        
        // Within pinned or non-pinned groups, apply normal sort
        let aVal, bVal;
        if (insightsSortBy === 'name') {
            aVal = a.name || '';
            bVal = b.name || '';
        } else if (insightsSortBy === 'type') {
            aVal = a.type || '';
            bVal = b.type || '';
        } else if (insightsSortBy === 'application') {
            aVal = (a.application && a.application.length > 0) ? a.application.join(', ') : '';
            bVal = (b.application && b.application.length > 0) ? b.application.join(', ') : '';
        } else if (insightsSortBy === 'created_at') {
            aVal = new Date(a.created_at).getTime();
            bVal = new Date(b.created_at).getTime();
        } else {
            return 0;
        }

        if (typeof aVal === 'string') {
            return insightsSortOrder === 'asc' 
                ? aVal.localeCompare(bVal)
                : bVal.localeCompare(aVal);
        } else {
            return insightsSortOrder === 'asc' ? aVal - bVal : bVal - aVal;
        }
    });

    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="2" class="empty-state"><h3>No insights found</h3><p>Create your first insight to get started</p></td></tr>';
        return;
    }

    
    const escapeHtmlFn = escapeHtml || ((s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;'));
    
    tbody.innerHTML = filtered.map(insight => {
        const createdDate = new Date(insight.created_at).toLocaleDateString();
        // Highlight search terms in insight name if there's a search term
        const insightName = toPascalCase(insight.name || '');
        const highlightedName = insightsSearchTerm ? highlightSearchTerms(insightName, insightsSearchTerm) : escapeHtmlFn(insightName);

        // Check if this insight is pinned
        const isPinned = isPinnedOverview(insight);
        const pinnedClass = isPinned ? 'pinned-overview' : '';
        const pinIconUrl = '/images/pinned_item.svg';
        
        // Use pin icon for pinned items, doc icon for others
        const iconHTML = isPinned
            ? `<img src="${pinIconUrl}" alt="Pinned" class="pin-icon" width="16" height="16">`
            : `<svg class="doc-icon" viewBox="0 0 16 16" fill="currentColor">
                <path d="M2.5 2.5h11l.5.5v10l-.5.5h-11l-.5-.5V3l.5-.5zM3 4v8h10V4H3zm2 1h6v1H5V5zm0 2h6v1H5V7zm0 2h4v1H5V9z"/>
            </svg>`;

        return `
            <tr data-insight-id="${insight.id}" class="${pinnedClass}" onclick="SlideoutPanel.openInsightNotes('${insight.id}')" style="cursor: pointer;">
                <td class="name-cell">
                    <div class="name-content" style="position: relative;">
                        ${iconHTML}
                        <span>${highlightedName}</span>
                        <button class="insight-open-btn-table" onclick="SlideoutPanel.openInsightNotes('${insight.id}')" title="Open in side peek" style="display: none;">
                            <span style="font-size: 12px; margin-right: 4px;">OPEN</span>
                            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" style="opacity: 0.6;">
                                <rect x="4" y="4" width="8" height="8" stroke="currentColor" stroke-width="1.5" fill="none" rx="1"/>
                                <path d="M6 2 L6 6 M10 2 L10 6 M2 6 L2 10 M2 6 L6 6 M10 6 L14 6 M14 6 L14 10" stroke="currentColor" stroke-width="1.5" fill="none"/>
                            </svg>
                        </button>
                    </div>
                </td>
                <td data-column="created_at">${createdDate}</td>
            </tr>
        `;
    }).join('');
}
