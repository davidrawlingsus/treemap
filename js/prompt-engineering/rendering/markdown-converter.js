/**
 * Markdown Converter Module
 * Handles conversion of markdown text to HTML with support for idea cards
 */

(function() {
    'use strict';

    if (!window.FounderAdmin) {
        console.error('[MARKDOWN_CONVERTER] FounderAdmin utilities must be loaded first');
        return;
    }

    const { DOM } = window.FounderAdmin;

    /**
     * Convert markdown text to HTML
     * @param {string} text - Markdown text
     * @returns {string} HTML string
     */
    function convertMarkdown(text) {
        if (!text) return '';
        
        // Process JSON blocks BEFORE HTML escaping (so JSON.parse works)
        // Use placeholders to preserve their position
        const jsonBlocks = [];
        text = text.replace(/```json\s*([\s\S]*?)```/gi, (match, jsonContent) => {
            try {
                // Skip empty or whitespace-only JSON content
                if (!jsonContent || !jsonContent.trim()) {
                    return match;
                }
                // Try to parse the JSON
                const jsonData = JSON.parse(jsonContent);
                
                let ideaCardsHTML = '';
                
                // Check if this is the structured format with content + ideas
                if (jsonData.ideas && Array.isArray(jsonData.ideas)) {
                    // Generate idea cards HTML object that will be processed later
                    const htmlObject = {
                        content: jsonData.content || null,
                        ideas: jsonData.ideas
                    };
                    
                    // Store and return placeholder
                    const placeholder = `___JSON_BLOCK_${jsonBlocks.length}___`;
                    jsonBlocks.push(htmlObject);
                    return placeholder;
                } 
                // Legacy support: Check if it's an array of ideas or a single idea
                else if (Array.isArray(jsonData)) {
                    const placeholder = `___JSON_BLOCK_${jsonBlocks.length}___`;
                    jsonBlocks.push({ content: null, ideas: jsonData });
                    return placeholder;
                } else {
                    const placeholder = `___JSON_BLOCK_${jsonBlocks.length}___`;
                    jsonBlocks.push({ content: null, ideas: [jsonData] });
                    return placeholder;
                }
            } catch (e) {
                // If JSON parsing fails, treat as regular code block
                // During streaming, incomplete JSON blocks may be present - silently skip them
                // Only log if it looks like a complete block (has closing backticks)
                if (match.includes('```') && match.split('```').length >= 3) {
                    console.warn('[MARKDOWN] Failed to parse JSON block for idea card:', e);
                }
                // Return the original match to be processed as regular code block
                return match;
            }
        });
        
        // Now escape HTML to prevent XSS
        let html = DOM.escapeHtml(text);
        
        // Process remaining code blocks (non-JSON or failed JSON)
        html = html.replace(/```(\w+)?\s*([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
        
        // Restore JSON block placeholders with the actual idea card HTML
        jsonBlocks.forEach((htmlObject, index) => {
            let ideaCardsHTML = '';
            
            // Add content section if present
            if (htmlObject.content) {
                ideaCardsHTML += `<div style="margin-bottom: 20px; padding: 8px 10px; background: #f0f4f8; border-left: 4px solid #B9F040; border-radius: 4px;"><p style="margin: 0; font-size: 16px; line-height: 1.4; color: #2d3748; font-weight: 500;">${DOM.escapeHtml(htmlObject.content)}</p></div>`;
            }
            
            // Generate idea cards from the ideas array
            ideaCardsHTML += htmlObject.ideas.map(idea => generateIdeaCardHTML(idea)).join('');
            
            html = html.replace(`___JSON_BLOCK_${index}___`, ideaCardsHTML);
        });
        
        // Split into lines for block-level processing
        const lines = html.split('\n');
        const processedLines = [];
        let inList = false;
        let listType = null; // 'ul' or 'ol'
        let inTable = false;
        let tableRows = [];
        let tableAlignments = [];
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const trimmed = line.trim();
            
            // Headers (must be at start of line)
            if (/^###\s+/.test(trimmed)) {
                if (inList) {
                    processedLines.push(listType === 'ul' ? '</ul>' : '</ol>');
                    inList = false;
                    listType = null;
                }
                processedLines.push('<h3>' + trimmed.replace(/^###\s+/, '') + '</h3>');
                continue;
            }
            if (/^##\s+/.test(trimmed)) {
                if (inList) {
                    processedLines.push(listType === 'ul' ? '</ul>' : '</ol>');
                    inList = false;
                    listType = null;
                }
                processedLines.push('<h2>' + trimmed.replace(/^##\s+/, '') + '</h2>');
                continue;
            }
            if (/^#\s+/.test(trimmed)) {
                if (inList) {
                    processedLines.push(listType === 'ul' ? '</ul>' : '</ol>');
                    inList = false;
                    listType = null;
                }
                processedLines.push('<h1>' + trimmed.replace(/^#\s+/, '') + '</h1>');
                continue;
            }
            
            // Unordered list
            if (/^[\-\*]\s+/.test(trimmed)) {
                if (!inList || listType !== 'ul') {
                    if (inList && listType === 'ol') {
                        processedLines.push('</ol>');
                    }
                    processedLines.push('<ul>');
                    inList = true;
                    listType = 'ul';
                }
                processedLines.push('<li>' + trimmed.replace(/^[\-\*]\s+/, '') + '</li>');
                continue;
            }
            
            // Ordered list - but check if it's actually a section header
            if (/^\d+\.\s+/.test(trimmed)) {
                // Intent-aware parsing: detect section headers vs ordered list items
                const listItemText = trimmed.replace(/^\d+\.\s+/, '');
                const endsWithColon = listItemText.endsWith(':');
                
                // Look ahead to see what comes next
                let followedByBulletList = false;
                
                for (let j = i + 1; j < lines.length; j++) {
                    const nextTrimmed = lines[j].trim();
                    if (nextTrimmed === '') continue;
                    
                    // Check if next line is a bullet (unordered list)
                    if (/^[\-\*]\s+/.test(nextTrimmed)) {
                        followedByBulletList = true;
                    }
                    break;
                }
                
                // Treat as section heading ONLY if:
                // Ends with colon AND followed by bullet list
                const shouldBeHeading = endsWithColon && followedByBulletList;
                
                if (shouldBeHeading) {
                    // Close any open list
                    if (inList) {
                        processedLines.push(listType === 'ul' ? '</ul>' : '</ol>');
                        inList = false;
                        listType = null;
                    }
                    // Treat as h3 heading
                    processedLines.push('<h3>' + listItemText + '</h3>');
                    continue;
                }
                
                // Otherwise, treat as normal ordered list item
                if (!inList || listType !== 'ol') {
                    if (inList && listType === 'ul') {
                        processedLines.push('</ul>');
                    }
                    processedLines.push('<ol>');
                    inList = true;
                    listType = 'ol';
                }
                processedLines.push('<li>' + listItemText + '</li>');
                continue;
            }
            
            // Table row detection (must start and end with |)
            if (/^\|.+\|$/.test(trimmed)) {
                // Close any open list
                if (inList) {
                    processedLines.push(listType === 'ul' ? '</ul>' : '</ol>');
                    inList = false;
                    listType = null;
                }
                
                // Check if this is a separator row (contains --- or === between pipes)
                if (/^\|[\s\-\|:]+$/.test(trimmed)) {
                    // This is a separator row - extract alignments
                    const cells = trimmed.split('|').slice(1, -1); // Remove empty first/last
                    tableAlignments = cells.map(cell => {
                        const trimmedCell = cell.trim();
                        if (/^:[\-]+:$/.test(trimmedCell)) return 'center';
                        if (/^:[\-]+$/.test(trimmedCell)) return 'left';
                        if (/^[\-]+:$/.test(trimmedCell)) return 'right';
                        return 'left'; // default
                    });
                    // Don't add separator row to tableRows, just continue
                    continue;
                }
                
                // This is a regular table row
                if (!inTable) {
                    // Start a new table
                    inTable = true;
                    tableRows = [];
                    tableAlignments = [];
                }
                
                // Parse cells (split by | and remove empty first/last)
                const cells = trimmed.split('|').slice(1, -1).map(cell => cell.trim());
                tableRows.push(cells);
                continue;
            }
            
            // Close table if we encounter a non-table line
            if (inTable && !/^\|.+\|$/.test(trimmed)) {
                // Render the accumulated table
                if (tableRows.length > 0) {
                    processedLines.push('<table>');
                    
                    // First row is header if we have alignments, otherwise all rows are body
                    const hasHeader = tableAlignments.length > 0;
                    const headerRow = hasHeader ? tableRows[0] : null;
                    const bodyRows = hasHeader ? tableRows.slice(1) : tableRows;
                    
                    if (headerRow) {
                        processedLines.push('<thead><tr>');
                        headerRow.forEach((cell, idx) => {
                            const align = tableAlignments[idx] || 'left';
                            processedLines.push(`<th style="text-align: ${align};">${cell}</th>`);
                        });
                        processedLines.push('</tr></thead>');
                    }
                    
                    if (bodyRows.length > 0) {
                        processedLines.push('<tbody>');
                        bodyRows.forEach(row => {
                            processedLines.push('<tr>');
                            row.forEach((cell, idx) => {
                                const align = tableAlignments[idx] || 'left';
                                processedLines.push(`<td style="text-align: ${align};">${cell}</td>`);
                            });
                            processedLines.push('</tr>');
                        });
                        processedLines.push('</tbody>');
                    }
                    
                    processedLines.push('</table>');
                }
                inTable = false;
                tableRows = [];
                tableAlignments = [];
            }
            
            // Empty line
            if (trimmed === '') {
                if (inList) {
                    processedLines.push(listType === 'ul' ? '</ul>' : '</ol>');
                    inList = false;
                    listType = null;
                }
                processedLines.push('');
                continue;
            }
            
            // Regular text line
            if (inList) {
                processedLines.push(listType === 'ul' ? '</ul>' : '</ol>');
                inList = false;
                listType = null;
            }
            processedLines.push(line);
        }
        
        // Close any open list
        if (inList) {
            processedLines.push(listType === 'ul' ? '</ul>' : '</ol>');
        }
        
        // Close any open table
        if (inTable && tableRows.length > 0) {
            processedLines.push('<table>');
            
            const hasHeader = tableAlignments.length > 0;
            const headerRow = hasHeader ? tableRows[0] : null;
            const bodyRows = hasHeader ? tableRows.slice(1) : tableRows;
            
            if (headerRow) {
                processedLines.push('<thead><tr>');
                headerRow.forEach((cell, idx) => {
                    const align = tableAlignments[idx] || 'left';
                    processedLines.push(`<th style="text-align: ${align};">${cell}</th>`);
                });
                processedLines.push('</tr></thead>');
            }
            
            if (bodyRows.length > 0) {
                processedLines.push('<tbody>');
                bodyRows.forEach(row => {
                    processedLines.push('<tr>');
                    row.forEach((cell, idx) => {
                        const align = tableAlignments[idx] || 'left';
                        processedLines.push(`<td style="text-align: ${align};">${cell}</td>`);
                    });
                    processedLines.push('</tr>');
                });
                processedLines.push('</tbody>');
            }
            
            processedLines.push('</table>');
        }
        
        html = processedLines.join('\n');
        
        // Process inline formatting
        // Bold: **text** -> <strong>text</strong> (do this first)
        html = html.replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>');
        
        // Italic: *text* -> <em>text</em> (after bold, so we don't match **)
        html = html.replace(/\*([^*\n]+?)\*/g, '<em>$1</em>');
        
        // Inline code: `code` -> <code>code</code> (but not inside <pre>)
        html = html.replace(/`([^`\n]+)`/g, '<code>$1</code>');
        
        // Convert double newlines to paragraph breaks, single newlines to <br>
        // But preserve block elements and don't add breaks inside lists
        html = html.split('\n\n').map(block => {
            const trimmed = block.trim();
            if (!trimmed) return '';
            
            // Don't wrap block elements in paragraphs
            // Include div so our idea cards/callouts don't get wrapped in <p>
            if (trimmed.match(/^<(h[1-3]|ul|ol|pre|li|table|div)/)) {
                return block;
            }
            
            // Convert single newlines to <br> within paragraphs
            const withBreaks = trimmed.replace(/\n/g, '<br>');
            return '<p>' + withBreaks + '</p>';
        }).join('');
        
        // Remove <br> tags that appear between list items (inside <ul> or <ol>)
        html = html.replace(/(<\/li>)\s*<br>\s*(<li>)/g, '$1$2');
        html = html.replace(/(<ul>|<ol>)\s*<br>\s*/g, '$1');
        html = html.replace(/\s*<br>\s*(<\/ul>|<\/ol>)/g, '$1');
        
        return html;
    }

    /**
     * Generate HTML for an idea card from JSON data
     * @param {Object} idea - Idea data object
     * @returns {string} HTML string for idea card
     */
    function generateIdeaCardHTML(idea) {
        // Extract fields from the idea object and escape for HTML safety
        const id = DOM.escapeHtml(idea.id || '');
        const title = DOM.escapeHtml(idea.title || idea.name || 'Untitled Idea');
        const testType = DOM.escapeHtml(idea.testType || idea.test_type || idea.type || '');
        const application = DOM.escapeHtml(idea.application || '');
        const origin = DOM.escapeHtml(idea.origin || '');
        const details = DOM.escapeHtml(idea.details || idea.description || '');
        
        // Build metadata rows
        let metaHTML = '';
        if (application) {
            metaHTML += `<div class="pe-idea-card__metaRow"><span class="pe-idea-card__metaLabel">Application:</span><span class="pe-idea-card__metaValue">${application}</span></div>`;
        }
        if (origin) {
            metaHTML += `<div class="pe-idea-card__metaRow"><span class="pe-idea-card__metaLabel">Origin:</span><span class="pe-idea-card__metaValue">${origin}</span></div>`;
        }
        
        // Build details content - preserve line breaks
        let detailsHTML = '';
        if (details) {
            // Convert both literal \n sequences (from JSON \\n) and actual newlines to <br>
            let formattedDetails = details.replace(/\\n|\n/g, '<br>');
            // Remove escaped quote sequences (literal \") that shouldn't be displayed
            formattedDetails = formattedDetails.replace(/\\"/g, '"');
            detailsHTML = `<div class="pe-idea-card__details">${formattedDetails}</div>`;
        }
        
        // Generate the idea card HTML with new structure.
        // Namespaced classes so styles don't inherit/collide with markdown styles.
        return `
            <div class="pe-idea-card" ${id ? `data-idea-id="${id}"` : ''}>
                <div class="pe-idea-card__top">
                    ${testType ? `<div class="pe-idea-card__badge">${testType}</div>` : '<div></div>'}
                    <button class="pe-idea-card__add" type="button" title="Add idea" data-idea='${DOM.escapeHtmlForAttribute(JSON.stringify(idea))}'>
                        +
                    </button>
                </div>
                <div class="pe-idea-card__title">${title}</div>
                ${metaHTML ? `<div class="pe-idea-card__meta">${metaHTML}</div>` : ''}
                    ${detailsHTML}
            </div>
        `;
    }

    // Export
    window.MarkdownConverter = {
        convertMarkdown,
        generateIdeaCardHTML
    };
})();
