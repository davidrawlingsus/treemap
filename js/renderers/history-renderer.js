/**
 * History Renderer
 * Handles rendering of history table
 */

import { highlightSearchTerms, toPascalCase } from '/js/utils/format.js';
import { escapeHtml } from '/js/utils/dom.js';
import {
    getHistoryAllActions,
    getHistorySearchTerm,
    getHistoryCurrentSortBy,
    getHistorySortOrder,
    clearSelectedHistoryIds
} from '/js/state/history-state.js';

/**
 * Render history table
 * Uses state from history-state module
 */
export function renderHistoryTable() {
    // Get escapeHtml with fallback
    const escapeHtmlFn = escapeHtml || window.escapeHtml || ((s) => {
        if (s == null) return '';
        const div = document.createElement('div');
        div.textContent = s;
        return div.innerHTML;
    });
    
    const tbody = document.getElementById('historyPageTableBody');
    if (!tbody) {
        return;
    }
    
    // Get state from module
    const historyAllActions = getHistoryAllActions();
    const historySearchTerm = getHistorySearchTerm();
    const historyCurrentSortBy = getHistoryCurrentSortBy();
    const historySortOrder = getHistorySortOrder();

    // Filter by search term
    let filtered = [...historyAllActions];
    if (historySearchTerm) {
        const searchLower = historySearchTerm.toLowerCase();
        filtered = filtered.filter(action => {
            const promptPurpose = (action.prompt_purpose || '').toLowerCase();
            const contentPreview = (action.content_preview || '').toLowerCase();
            return promptPurpose.includes(searchLower) || contentPreview.includes(searchLower);
        });
    }

    // Sort
    filtered.sort((a, b) => {
        let aVal, bVal;
        if (historyCurrentSortBy === 'name') {
            aVal = (a.prompt_purpose || '').toLowerCase();
            bVal = (b.prompt_purpose || '').toLowerCase();
        } else if (historyCurrentSortBy === 'created_at') {
            aVal = new Date(a.created_at).getTime();
            bVal = new Date(b.created_at).getTime();
        } else if (historyCurrentSortBy === 'origin') {
            const aOrigin = a.origin || {};
            const bOrigin = b.origin || {};
            const aProject = aOrigin.project_name || '';
            const bProject = bOrigin.project_name || '';
            const aDimension = aOrigin.dimension_name || aOrigin.dimension_ref || '';
            const bDimension = bOrigin.dimension_name || bOrigin.dimension_ref || '';
            
            const projectCompare = aProject.localeCompare(bProject);
            if (projectCompare !== 0) {
                return historySortOrder === 'asc' ? projectCompare : -projectCompare;
            }
            const dimensionCompare = aDimension.localeCompare(bDimension);
            return historySortOrder === 'asc' ? dimensionCompare : -dimensionCompare;
        } else {
            return 0;
        }
        
        if (historySortOrder === 'asc') {
            return aVal > bVal ? 1 : aVal < bVal ? -1 : 0;
        } else {
            return aVal < bVal ? 1 : aVal > bVal ? -1 : 0;
        }
    });

    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="empty-state"><h3>No history found</h3><p style="font-size: 12px; color: #999;">' + (historySearchTerm ? 'Try a different search term' : 'No AI expert outputs yet') + '</p></td></tr>';
        return;
    }

    // Get utility functions with fallbacks
    const highlightFn = highlightSearchTerms || window.highlightSearchTerms || ((text) => escapeHtmlFn(text));
    const toPascalCaseFn = toPascalCase || window.toPascalCase || ((text) => text);

    const abbreviations = ['SEO', 'CRO', 'UX', 'UI', 'API', 'CRM', 'CMS', 'CTA', 'ROI', 'KPI', 'A/B', 'AB', 'A', 'B', 'PPC', 'SEM', 'SERP', 'SaaS', 'B2B', 'B2C', 'BOFU', 'MOFU', 'TOFU', 'GDPR', 'LTV', 'CAC', 'MVP', 'FAQ', 'URL', 'HTML', 'CSS', 'JS', 'JSON', 'XML', 'REST', 'HTTP', 'HTTPS', 'SSL', 'TLS', 'CDN', 'DNS', 'IP', 'PDF', 'CSV', 'XLS', 'XLSX'];

    tbody.innerHTML = filtered.map(action => {
        const createdDate = new Date(action.created_at).toLocaleDateString();
        let promptName = action.prompt_purpose || 'Unknown';
        promptName = promptName
            .replace(/_/g, ' ')
            .replace(/-/g, ' ')
            .split(' ')
            .map(word => {
                if (/^[Aa]&[Bb]$/.test(word)) return 'A & B';
                const upperWord = word.toUpperCase();
                if (abbreviations.includes(upperWord)) {
                    return upperWord;
                }
                return word.charAt(0).toUpperCase() + word.substr(1).toLowerCase();
            })
            .join(' ');
        
        const highlightedName = historySearchTerm ? highlightFn(promptName, historySearchTerm) : escapeHtmlFn(promptName);
        
        const origin = action.origin || {};
        const dataSource = origin.data_source || null;
        const dimensionName = origin.dimension_name || null;
        const dimensionRef = origin.dimension_ref || null;
        const categoryName = origin.category || null;
        const topicName = origin.topic_label || null;
        
        const originPills = [];
        if (dimensionName && dimensionRef) {
            const pascalDimension = toPascalCaseFn(dimensionName);
            originPills.push(`<span class="tag tag-data-source insight-origin-pill" data-origin-type="dimension" data-dimension-ref="${dimensionRef}" data-dimension-name="${escapeHtmlFn(dimensionName)}" data-data-source="${dataSource || ''}" onclick="event.stopPropagation(); navigateToDimensionFromInsight('${dimensionRef}', '${escapeHtmlFn(dimensionName)}', '${dataSource || ''}')" style="cursor: pointer;">${escapeHtmlFn(pascalDimension)}</span>`);
        } else if (dimensionName) {
            const pascalDimension = toPascalCaseFn(dimensionName);
            originPills.push(`<span class="tag tag-data-source insight-origin-pill">${escapeHtmlFn(pascalDimension)}</span>`);
        }
        if (categoryName) {
            const pascalCategory = toPascalCaseFn(categoryName);
            originPills.push(`<span class="tag tag-category insight-origin-pill" data-origin-type="category" data-category="${escapeHtmlFn(categoryName)}" data-topic="${topicName ? escapeHtmlFn(topicName) : ''}" data-data-source="${dataSource || ''}" data-dimension="${dimensionName || ''}" data-dimension-ref="${dimensionRef || ''}" onclick="event.stopPropagation(); navigateToCategoryFromInsight('${escapeHtmlFn(categoryName)}', '${topicName ? escapeHtmlFn(topicName) : ''}', '${dataSource || ''}', '${dimensionRef || ''}')" style="cursor: pointer;">${escapeHtmlFn(pascalCategory)}</span>`);
        }
        if (topicName) {
            const pascalTopic = toPascalCaseFn(topicName);
            originPills.push(`<span class="tag tag-topic insight-origin-pill" data-origin-type="topic" data-category="${categoryName ? escapeHtmlFn(categoryName) : ''}" data-topic="${escapeHtmlFn(topicName)}" data-data-source="${dataSource || ''}" data-dimension="${dimensionName || ''}" data-dimension-ref="${dimensionRef || ''}" onclick="event.stopPropagation(); navigateToTopicFromInsight('${escapeHtmlFn(topicName)}', '${categoryName ? escapeHtmlFn(categoryName) : ''}', '${dataSource || ''}', '${dimensionRef || ''}')" style="cursor: pointer;">${escapeHtmlFn(pascalTopic)}</span>`);
        }
        if (originPills.length === 0 && dataSource) {
            let correctedDataSource = dataSource;
            if (dataSource && typeof dataSource === 'string') {
                correctedDataSource = dataSource.replace(/Faceboo\s+Ads/gi, 'Facebook Ads');
            }
            const pascalDataSource = toPascalCaseFn(correctedDataSource);
            originPills.push(`<span class="tag tag-data-source insight-origin-pill">${escapeHtmlFn(pascalDataSource)}</span>`);
        }
        
        const originContent = originPills.length > 0 
            ? originPills.join('<span style="margin: 0 4px; color: oklch(0.7 0 0);">|</span>')
            : '-';

        const checkboxCell = `<td class="checkbox-cell" onclick="event.stopPropagation(); const checkbox = this.querySelector('.history-checkbox'); if (checkbox && !event.target.matches('.history-checkbox')) { checkbox.checked = !checkbox.checked; checkbox.dispatchEvent(new Event('change')); }">
            <input type="checkbox" class="history-checkbox" data-action-id="${action.id}" onchange="handleHistoryCheckboxChange()" onclick="event.stopPropagation()">
        </td>`;
        
        return `
            <tr data-action-id="${action.id}" onclick="event.stopPropagation(); openHistoryAction('${action.id}'); return false;" style="cursor: pointer;">
                ${checkboxCell}
                <td class="name-cell" data-column="name">
                    <div class="name-content" style="position: relative;">
                        <svg class="doc-icon" viewBox="0 0 16 16" fill="currentColor">
                            <path d="M2.5 2.5h11l.5.5v10l-.5.5h-11l-.5-.5V3l.5-.5zM3 4v8h10V4H3zm2 1h6v1H5V5zm0 2h6v1H5V7zm0 2h4v1H5V9z"/>
                        </svg>
                        <span>${highlightedName}</span>
                    </div>
                </td>
                <td data-column="origin" style="white-space: nowrap;">
                    ${originContent}
                </td>
                <td data-column="created_at">${createdDate}</td>
            </tr>
        `;
    }).join('');
    
    // Clear checkbox selections when table is re-rendered
    clearSelectedHistoryIds();
    
    // Call global functions for UI updates
    if (typeof window.updateHistoryDeleteButton === 'function') {
        window.updateHistoryDeleteButton();
    }
    if (typeof window.updateHistorySelectAllCheckbox === 'function') {
        window.updateHistorySelectAllCheckbox();
    }
}
