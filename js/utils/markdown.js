/**
 * Markdown to HTML utilities for settings and product context fields.
 */

import { escapeHtml } from '/js/utils/dom.js';

/**
 * Convert markdown text to HTML for settings/product context display.
 * @param {string} text - Markdown text
 * @returns {string} HTML string
 */
export function renderSettingsMarkdown(text) {
    if (!text || !text.trim()) return '';

    let html = escapeHtml(text);

    // Process code blocks first
    html = html.replace(/```(\w+)?\s*([\s\S]*?)```/g, '<pre><code>$2</code></pre>');

    const lines = html.split('\n');
    const processedLines = [];
    let inList = false;
    let listType = null;
    let inTable = false;
    let tableRows = [];
    let tableAlignments = [];

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const trimmed = line.trim();

        if (/^###\s+/.test(trimmed)) {
            if (inList) { processedLines.push(listType === 'ul' ? '</ul>' : '</ol>'); inList = false; }
            processedLines.push('<h3>' + trimmed.replace(/^###\s+/, '') + '</h3>');
            continue;
        }
        if (/^##\s+/.test(trimmed)) {
            if (inList) { processedLines.push(listType === 'ul' ? '</ul>' : '</ol>'); inList = false; }
            processedLines.push('<h2>' + trimmed.replace(/^##\s+/, '') + '</h2>');
            continue;
        }
        if (/^#\s+/.test(trimmed)) {
            if (inList) { processedLines.push(listType === 'ul' ? '</ul>' : '</ol>'); inList = false; }
            processedLines.push('<h1>' + trimmed.replace(/^#\s+/, '') + '</h1>');
            continue;
        }
        if (/^[-*_]{3,}$/.test(trimmed)) {
            if (inList) { processedLines.push(listType === 'ul' ? '</ul>' : '</ol>'); inList = false; }
            processedLines.push('<hr>');
            continue;
        }
        if (/^[\-\*]\s+/.test(trimmed)) {
            if (!inList || listType !== 'ul') {
                if (inList) processedLines.push('</ol>');
                processedLines.push('<ul>');
                inList = true;
                listType = 'ul';
            }
            processedLines.push('<li>' + trimmed.replace(/^[\-\*]\s+/, '') + '</li>');
            continue;
        }
        if (/^\d+\.\s+/.test(trimmed)) {
            if (!inList || listType !== 'ol') {
                if (inList) processedLines.push('</ul>');
                processedLines.push('<ol>');
                inList = true;
                listType = 'ol';
            }
            processedLines.push('<li>' + trimmed.replace(/^\d+\.\s+/, '') + '</li>');
            continue;
        }
        if (/^\|.+\|$/.test(trimmed)) {
            if (inList) { processedLines.push(listType === 'ul' ? '</ul>' : '</ol>'); inList = false; }
            if (/^\|[\s\-\|:]+$/.test(trimmed)) {
                const cells = trimmed.split('|').slice(1, -1);
                tableAlignments = cells.map(cell => {
                    const t = cell.trim();
                    if (/^:[\-]+:$/.test(t)) return 'center';
                    if (/^:[\-]+$/.test(t)) return 'left';
                    if (/^[\-]+:$/.test(t)) return 'right';
                    return 'left';
                });
                continue;
            }
            if (!inTable) { inTable = true; tableRows = []; tableAlignments = []; }
            const cells = trimmed.split('|').slice(1, -1).map(cell => cell.trim());
            tableRows.push(cells);
            continue;
        }
        if (inTable && !/^\|.+\|$/.test(trimmed)) {
            if (tableRows.length > 0) {
                processedLines.push('<table>');
                const hasHeader = tableAlignments.length > 0;
                const headerRow = hasHeader ? tableRows[0] : null;
                const bodyRows = hasHeader ? tableRows.slice(1) : tableRows;
                if (headerRow) {
                    processedLines.push('<thead><tr>');
                    headerRow.forEach((cell, idx) => processedLines.push(`<th style="text-align:${tableAlignments[idx] || 'left'}">${cell}</th>`));
                    processedLines.push('</tr></thead>');
                }
                if (bodyRows.length > 0) {
                    processedLines.push('<tbody>');
                    bodyRows.forEach(row => {
                        processedLines.push('<tr>');
                        row.forEach((cell, idx) => processedLines.push(`<td style="text-align:${tableAlignments[idx] || 'left'}">${cell}</td>`));
                        processedLines.push('</tr>');
                    });
                    processedLines.push('</tbody>');
                }
                processedLines.push('</table>');
            }
            inTable = false;
            tableRows = [];
        }
        if (trimmed === '') {
            if (inList) { processedLines.push(listType === 'ul' ? '</ul>' : '</ol>'); inList = false; }
            processedLines.push('');
            continue;
        }
        if (inList) { processedLines.push(listType === 'ul' ? '</ul>' : '</ol>'); inList = false; }
        processedLines.push(line);
    }

    if (inList) processedLines.push(listType === 'ul' ? '</ul>' : '</ol>');
    if (inTable && tableRows.length > 0) {
        processedLines.push('<table>');
        const hasHeader = tableAlignments.length > 0;
        const headerRow = hasHeader ? tableRows[0] : null;
        const bodyRows = hasHeader ? tableRows.slice(1) : tableRows;
        if (headerRow) {
            processedLines.push('<thead><tr>');
            headerRow.forEach((cell, idx) => processedLines.push(`<th style="text-align:${tableAlignments[idx] || 'left'}">${cell}</th>`));
            processedLines.push('</tr></thead>');
        }
        if (bodyRows.length > 0) {
            processedLines.push('<tbody>');
            bodyRows.forEach(row => {
                processedLines.push('<tr>');
                row.forEach((cell, idx) => processedLines.push(`<td style="text-align:${tableAlignments[idx] || 'left'}">${cell}</td>`));
                processedLines.push('</tr>');
            });
            processedLines.push('</tbody>');
        }
        processedLines.push('</table>');
    }

    html = processedLines.join('\n');
    html = html.replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*([^*\n]+?)\*/g, '<em>$1</em>');
    html = html.replace(/`([^`\n]+)`/g, '<code>$1</code>');
    html = html.split('\n\n').map(block => {
        const t = block.trim();
        if (!t) return '';
        if (t.match(/^<(h[1-3]|ul|ol|pre|li|table|hr|div|p)/)) return block;
        return '<p>' + t.replace(/\n/g, '<br>') + '</p>';
    }).join('');

    return html;
}
