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
        
        // Before splitting into paragraphs, ensure lines starting with <strong>Label:</strong> 
        // followed by content get proper paragraph breaks (not just <br>)
        // This improves readability in TipTap editor
        html = html.replace(/(<strong>[^<]+:<\/strong>[^\n]*)\n([^<\n])/g, '$1</p><p>$2');
        
        // Convert double newlines to paragraph breaks, single newlines to <br>
        // But preserve block elements and don't add breaks inside lists
        html = html.split('\n\n').map(block => {
            const trimmed = block.trim();
            if (!trimmed) return '';
            
            // Don't wrap block elements in paragraphs
            // Include div so our idea cards/callouts don't get wrapped in <p>
            if (trimmed.match(/^<(h[1-3]|ul|ol|pre|li|table|div|p)/)) {
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
     * Check if the idea object is a Facebook ad format
     * @param {Object} idea - Idea data object
     * @returns {boolean} True if Facebook ad format
     */
    function isFacebookAdFormat(idea) {
        return !!(idea.primary_text && idea.headline && idea.call_to_action);
    }

    /**
     * Format CTA value to sentence case (e.g., SHOP_NOW -> "Shop now")
     * @param {string} cta - CTA value like SHOP_NOW, LEARN_MORE, etc.
     * @returns {string} Formatted CTA text
     */
    function formatCTA(cta) {
        if (!cta) return 'Learn more';
        // Convert SHOP_NOW to "Shop now"
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
     * Generate HTML for a Facebook Ad card from JSON data
     * @param {Object} idea - Facebook ad data object
     * @returns {string} HTML string for FB ad card
     */
    function generateFBAdCardHTML(idea) {
        const id = DOM.escapeHtml(idea.id || '');
        const primaryText = idea.primary_text || '';
        const headline = DOM.escapeHtml(idea.headline || '');
        const description = DOM.escapeHtml(idea.description || '');
        const cta = formatCTA(idea.call_to_action);
        const destinationUrl = idea.destination_url || '';
        const displayUrl = extractDomain(destinationUrl);
        const vocEvidence = idea.voc_evidence || [];

        // Format primary text - convert to HTML with proper paragraph spacing
        // First unescape JSON sequences, then normalize line breaks
        let rawText = primaryText
            .replace(/\\n/g, '\n')      // Convert escaped \n to actual newlines
            .replace(/\\"/g, '"')        // Unescape quotes
            .replace(/\r\n/g, '\n')      // Normalize Windows line breaks
            .replace(/\r/g, '\n');       // Normalize old Mac line breaks
        
        // Split into paragraphs (double newline = paragraph break)
        // Then convert single newlines within paragraphs to <br>
        const paragraphs = rawText.split(/\n{2,}/);
        const formattedParagraphs = paragraphs
            .map(para => para.trim())
            .filter(para => para.length > 0)
            .map(para => {
                const escaped = DOM.escapeHtml(para);
                // Convert single newlines to <br> within paragraph
                return escaped.replace(/\n/g, '<br>');
            });
        
        // Wrap each paragraph in a div with margin (except last one)
        const formattedPrimaryText = formattedParagraphs
            .map((para, idx, arr) => {
                const isLast = idx === arr.length - 1;
                return `<div style="margin-bottom:${isLast ? '0' : '12px'};">${para}</div>`;
            })
            .join('');

        // Build VoC evidence HTML as free text above the ad
        let vocHTML = '';
        if (vocEvidence.length > 0) {
            const vocItems = vocEvidence.map(quote => 
                `<div class="pe-fb-ad-wrapper__voc-item" style="font-size:13px;color:#4a5568;line-height:1.5;padding:6px 0;border-bottom:1px solid #e2e8f0;font-style:italic;">"${DOM.escapeHtml(quote)}"</div>`
            ).join('');
            vocHTML = `<div class="pe-fb-ad-wrapper__voc" style="margin-bottom:12px;padding-bottom:12px;border-bottom:1px solid #e2e8f0;"><div class="pe-fb-ad-wrapper__voc-label" style="font-size:12px;font-weight:600;color:#718096;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">VoC Evidence</div><div class="pe-fb-ad-wrapper__voc-list" style="display:block;">${vocItems}</div></div>`;
        }

        // Generate unique ID for this ad card
        const uniqueId = id || `fb-ad-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

        // Get client logo from nav if available
        const navLogo = document.getElementById('navClientLogo');
        const logoSrc = navLogo ? navLogo.src : '';
        const profilePicContent = logoSrc 
            ? `<img src="${DOM.escapeHtml(logoSrc)}" alt="Client Logo" style="width:40px;height:40px;border-radius:50%;object-fit:contain;background:#fff;">`
            : 'Ad';
        const profilePicStyle = logoSrc
            ? 'width:40px;height:40px;min-width:40px;min-height:40px;border-radius:50%;overflow:hidden;flex-shrink:0;margin:0;padding:0;background:#fff;'
            : 'width:40px;height:40px;min-width:40px;min-height:40px;border-radius:50%;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:600;font-size:14px;flex-shrink:0;margin:0;padding:0;';

        // Get client name from the client select dropdown
        const clientSelect = document.getElementById('clientSelect');
        const clientName = clientSelect?.selectedOptions?.[0]?.textContent?.trim() || 'Sponsored';

        // Use inline styles for guaranteed highest specificity
        // Add button is now inside the ad header at top right
        // VoC appears before the ad, horizontal rule separates multiple ads
        return `<div class="pe-fb-ad-wrapper" ${id ? `data-idea-id="${id}"` : ''} data-fb-ad-id="${uniqueId}" style="margin:0;padding:32px 0 0 0;border-top:1px solid #cbd5e0;">${vocHTML}<div class="pe-fb-ad" style="margin:24px 0 16px 0;padding:0;border:1px solid #e2e8f0;display:block;width:100%;background:#fff;border-radius:8px;box-shadow:0 1px 2px rgba(0,0,0,0.1);overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;font-size:15px;line-height:1.3333;color:#050505;position:relative;"><button class="pe-fb-ad-wrapper__add" type="button" title="Add idea" data-idea='${DOM.escapeHtmlForAttribute(JSON.stringify(idea))}' style="position:absolute;top:8px;right:8px;width:28px;height:28px;border-radius:50%;border:none;background:rgba(0,0,0,0.05);color:#65676b;font-size:16px;font-weight:700;display:inline-flex;align-items:center;justify-content:center;cursor:pointer;z-index:10;">+</button><div class="pe-fb-ad__header" style="padding:12px 12px 0;margin:0;display:flex;align-items:center;gap:8px;"><div class="pe-fb-ad__profile-pic" style="${profilePicStyle}">${profilePicContent}</div><div class="pe-fb-ad__info" style="flex:1;min-width:0;margin:0;padding:0;"><div class="pe-fb-ad__page-name" style="font-weight:600;font-size:15px;color:#050505;margin:0;padding:0;">${DOM.escapeHtml(clientName)}</div><div class="pe-fb-ad__sponsored" style="display:flex;align-items:center;gap:4px;font-size:13px;color:#65676b;margin:0;padding:0;"><span style="margin:0;padding:0;">Sponsored</span><span class="pe-fb-ad__dot" style="width:3px;height:3px;background:#65676b;border-radius:50%;margin:0;padding:0;"></span><span style="margin:0;padding:0;">🌐</span></div></div></div><div class="pe-fb-ad__primary-text-wrapper" style="padding:8px 12px;margin:0;"><div class="pe-fb-ad__primary-text" style="font-size:15px;line-height:1.4;color:#050505;margin:0;padding:0;">${formattedPrimaryText}</div></div><div class="pe-fb-ad__media" style="width:100%;aspect-ratio:1.91/1;background:linear-gradient(to top right,transparent calc(50% - 1px),#9ca3af calc(50% - 1px),#9ca3af calc(50% + 1px),transparent calc(50% + 1px)),linear-gradient(to top left,transparent calc(50% - 1px),#9ca3af calc(50% - 1px),#9ca3af calc(50% + 1px),transparent calc(50% + 1px)),#e5e7eb;margin:0;padding:0;"></div><div class="pe-fb-ad__link-details" style="background:#f8fafb;padding:10px 12px;margin:0;display:flex;align-items:center;justify-content:space-between;gap:12px;"><div class="pe-fb-ad__link-text" style="flex:1;min-width:0;margin:0;padding:0;"><div class="pe-fb-ad__link-url" style="font-size:12px;color:#65676b;text-transform:uppercase;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin:0;padding:0;">${DOM.escapeHtml(displayUrl)}</div><div class="pe-fb-ad__headline" style="font-weight:600;font-size:15px;color:#050505;line-height:1.2;margin:0;padding:0;">${headline}</div><div class="pe-fb-ad__description" style="font-size:14px;color:#65676b;line-height:1.3;margin:0;padding:0;">${description}</div></div><div class="pe-fb-ad__cta" style="background:#e2e5e9;color:#050505;border:none;padding:8px 12px;border-radius:4px;font-weight:600;font-size:14px;white-space:nowrap;flex-shrink:0;margin:0;">${DOM.escapeHtml(cta)}</div></div><div class="pe-fb-ad__footer" style="padding:4px 12px 8px;margin:0;display:flex;justify-content:space-around;border-top:1px solid #e4e6eb;"><div class="pe-fb-ad__action" style="display:flex;align-items:center;gap:4px;color:#65676b;font-size:13px;font-weight:600;padding:6px 0;margin:0;"><span style="font-size:16px;margin:0;padding:0;">👍</span><span style="margin:0;padding:0;">Like</span></div><div class="pe-fb-ad__action" style="display:flex;align-items:center;gap:4px;color:#65676b;font-size:13px;font-weight:600;padding:6px 0;margin:0;"><span style="font-size:16px;margin:0;padding:0;">💬</span><span style="margin:0;padding:0;">Comment</span></div><div class="pe-fb-ad__action" style="display:flex;align-items:center;gap:4px;color:#65676b;font-size:13px;font-weight:600;padding:6px 0;margin:0;"><span style="font-size:16px;margin:0;padding:0;">↗</span><span style="margin:0;padding:0;">Share</span></div></div></div></div>`;
    }

    /**
     * Generate HTML for an idea card from JSON data
     * @param {Object} idea - Idea data object
     * @returns {string} HTML string for idea card
     */
    function generateIdeaCardHTML(idea) {
        // Check if this is a Facebook ad format
        if (isFacebookAdFormat(idea)) {
            return generateFBAdCardHTML(idea);
        }
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

    /**
     * Initialize FB ad card interactions
     * Uses event delegation on a container element
     * @param {HTMLElement} container - Container element to attach listeners to
     */
    function initFBAdInteractions(container) {
        if (!container) return;
        
        // Prevent duplicate listeners
        if (container.dataset.fbAdListenerAttached === 'true') {
            return;
        }
        
        // Mark that we've attached the listener
        // Currently no additional interactions needed beyond the add button
        // which is handled by action-renderer.js
        container.dataset.fbAdListenerAttached = 'true';
    }

    // Export
    window.MarkdownConverter = {
        convertMarkdown,
        generateIdeaCardHTML,
        generateFBAdCardHTML,
        isFacebookAdFormat,
        initFBAdInteractions
    };
})();
