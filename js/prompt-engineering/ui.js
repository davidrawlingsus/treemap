/**
 * Prompt Engineering UI Rendering
 * Functions for rendering prompts list and results display
 */

(function() {
    'use strict';

    if (!window.FounderAdmin || !window.PromptEngineeringState) {
        console.error('[PROMPT_UI] Dependencies not loaded');
        return;
    }

    const { DOM } = window.FounderAdmin;
    const state = window.PromptEngineeringState;

    // Store streaming content in memory instead of data attributes to avoid size limits
    // Use WeakMap so elements can be garbage collected when removed from DOM
    const streamingContentStore = new WeakMap();

    /**
     * UI Renderer
     */
    const UIRenderer = {
        /**
         * Get raw text content from streaming content store (for copy functionality)
         * @param {HTMLElement} contentElement - Content element
         * @returns {string} Raw text content or empty string
         */
        getStreamingContent(contentElement) {
            return streamingContentStore.get(contentElement) || '';
        },
        /**
         * Convert markdown text to HTML
         * @param {string} text - Markdown text
         * @returns {string} HTML string
         */
        convertMarkdown(text) {
            if (!text) return '';
            
            // First escape HTML to prevent XSS
            let html = DOM.escapeHtml(text);
            
            // Code blocks first (before other processing)
            html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
            
            // Split into lines for block-level processing
            const lines = html.split('\n');
            const processedLines = [];
            let inList = false;
            let listType = null; // 'ul' or 'ol'
            
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
                    const isNumberOne = /^1\.\s+/.test(trimmed);
                    
                    // Look ahead to see what comes next
                    let followedByBulletList = false;
                    let followedByOrderedItem = false;
                    let nextOrderedIsAlsoOne = false;
                    let nextNonEmptyLine = null;
                    
                    for (let j = i + 1; j < lines.length; j++) {
                        const nextTrimmed = lines[j].trim();
                        if (nextTrimmed === '') continue;
                        nextNonEmptyLine = nextTrimmed;
                        
                        // Check if next line is a bullet (unordered list)
                        if (/^[\-\*]\s+/.test(nextTrimmed)) {
                            followedByBulletList = true;
                        }
                        // Check if next line is an ordered list item
                        if (/^\d+\.\s+/.test(nextTrimmed)) {
                            followedByOrderedItem = true;
                            // Check if it's also "1."
                            if (/^1\.\s+/.test(nextTrimmed)) {
                                nextOrderedIsAlsoOne = true;
                            }
                        }
                        break;
                    }
                    
                    // Treat as section heading ONLY if:
                    // Ends with colon AND followed by bullet list
                    // (Don't treat repeated "1." as headings - they're just numbered list items)
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
                if (trimmed.match(/^<(h[1-3]|ul|ol|pre|li)/)) {
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
        },

        /**
         * Render prompts list
         * @param {HTMLElement} container - Container element
         * @param {Function} onEditClick - Callback when edit button is clicked
         * @param {Function} onVersionChange - Callback when version selector changes
         */
        renderPrompts(container, onEditClick, onVersionChange) {
            if (!container) return;

            const prompts = state.get('prompts');

            if (!prompts || prompts.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">No prompts yet</h3>
                        <p style="font-size: 14px;">Create your first prompt to start transforming insights into actions.</p>
                    </div>
                `;
                return;
            }

            // Group prompts by name to show version history
            const promptsByName = {};
            prompts.forEach(prompt => {
                if (!promptsByName[prompt.name]) {
                    promptsByName[prompt.name] = [];
                }
                promptsByName[prompt.name].push(prompt);
            });

            // Use document fragment for better performance
            const fragment = document.createDocumentFragment();
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = Object.entries(promptsByName)
                .map(([name, versions]) => {
                    const sortedVersions = versions.sort((a, b) => b.version - a.version);
                    const latest = sortedVersions[0];
                    const versionCount = versions.length;
                    const statusBadge = this.getStatusBadge(latest.status);
                    const updatedAt = latest.updated_at ? new Date(latest.updated_at).toLocaleString() : 'Unknown';
                    const createdAt = latest.created_at ? new Date(latest.created_at).toLocaleDateString() : 'Unknown';
                    const purposeChip = `<span class="client-chip">${latest.prompt_purpose}</span>`;
                    const modelChip = `<span class="client-chip" style="background: #edf2f7; border-color: #cbd5e0; color: #4a5568;">${latest.llm_model}</span>`;

                    // Build version selector if multiple versions exist
                    let versionSelector = '';
                    if (versionCount > 1) {
                        const versionOptions = sortedVersions.map(v => 
                            `<option value="${v.id}" ${v.id === latest.id ? 'selected' : ''}>v${v.version} - ${v.status}${v.updated_at ? ' (' + new Date(v.updated_at).toLocaleDateString() + ')' : ''}</option>`
                        ).join('');
                        versionSelector = `
                            <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border);">
                                <label style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); display: block; margin-bottom: 6px;">Version History</label>
                                <select class="version-selector" data-prompt-name="${DOM.escapeHtmlForAttribute(name)}" style="width: 100%; padding: 8px 12px; border: 1px solid var(--border); border-radius: 8px; font-size: 14px; background: white;">
                                    ${versionOptions}
                                </select>
                            </div>
                        `;
                    }

                    const preview = latest.system_message.substring(0, 200);
                    const hasMore = latest.system_message.length > 200;

                    return `
                        <article class="domain-card" data-prompt-name="${DOM.escapeHtmlForAttribute(name)}">
                            <div class="domain-header">
                                <div>
                                    <h2>${DOM.escapeHtml(name)}</h2>
                                    <div class="domain-meta">
                                        <span>Version ${latest.version}${versionCount > 1 ? ` (${versionCount} versions)` : ''}</span>
                                        <span>Created ${createdAt}</span>
                                        <span>Updated ${updatedAt}</span>
                                    </div>
                                </div>
                                <button class="btn btn-secondary" data-action="edit-prompt" data-prompt-id="${latest.id}">Edit</button>
                            </div>
                            <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px;">
                                ${statusBadge} ${purposeChip} ${modelChip}
                            </div>
                            <div class="description" style="font-family: monospace; font-size: 12px; max-height: 100px; overflow-y: auto; background: #f7fafc; padding: 8px; border-radius: 6px; white-space: pre-wrap; word-break: break-word;">${DOM.escapeHtml(preview)}${hasMore ? '...' : ''}</div>
                            ${versionSelector}
                        </article>
                    `;
                })
                .join('');

            // Move nodes to fragment
            while (tempDiv.firstChild) {
                fragment.appendChild(tempDiv.firstChild);
            }

            // Clear and append fragment
            container.innerHTML = '';
            container.appendChild(fragment);

            // Attach event listeners
            container.querySelectorAll('[data-action="edit-prompt"]').forEach((button) => {
                button.addEventListener('click', () => {
                    const promptId = button.getAttribute('data-prompt-id');
                    if (onEditClick) onEditClick(promptId);
                });
            });

            container.querySelectorAll('.version-selector').forEach((select) => {
                select.addEventListener('change', (e) => {
                    const promptId = e.target.value;
                    if (onVersionChange) onVersionChange(promptId);
                });
            });
        },

        /**
         * Get status badge HTML
         * @param {string} status - Status value
         * @returns {string} HTML for status badge
         */
        getStatusBadge(status) {
            const styles = {
                live: { bg: '#f0fff4', border: '#c6f6d5', color: '#22543d' },
                test: { bg: '#fffbf0', border: '#fbd38d', color: '#744210' },
                archived: { bg: '#f7fafc', border: '#e2e8f0', color: '#4a5568' }
            };

            const style = styles[status] || styles.archived;
            return `<span class="client-chip" style="background: ${style.bg}; border-color: ${style.border}; color: ${style.color};">${status.toUpperCase()}</span>`;
        },

        /**
         * Render prompt results/actions
         * @param {HTMLElement} container - Container element
         * @param {Array} actions - Array of action objects
         * @param {Function} onCopy - Callback when copy button is clicked
         * @param {Function} onDelete - Callback when delete button is clicked
         */
        renderActions(container, actions, onCopy, onDelete) {
            if (!container) return;

            if (!actions || actions.length === 0) {
                container.innerHTML = '<p style="color: var(--muted); padding: 24px; text-align: center;">No execution results match the selected filters.</p>';
                return;
            }

            const filterState = state.get('filterState');
            let filteredActions = actions;

            // Apply filters
            if (filterState.promptNames.size > 0) {
                filteredActions = filteredActions.filter(action => 
                    action.prompt_name && filterState.promptNames.has(action.prompt_name)
                );
            }

            if (filterState.promptVersions.size > 0) {
                filteredActions = filteredActions.filter(action => {
                    if (!action.prompt_name || action.prompt_version === null || action.prompt_version === undefined) {
                        return false;
                    }
                    const versionKey = `${action.prompt_name}:v${action.prompt_version}`;
                    return filterState.promptVersions.has(versionKey);
                });
            }

            if (filteredActions.length === 0) {
                container.innerHTML = '<p style="color: var(--muted); padding: 24px; text-align: center;">No execution results match the selected filters.</p>';
                return;
            }

            // Store scroll position before clearing
            const scrollTopBefore = container.scrollTop;
            const wasAtBottomBefore = this._isAtBottom(container, 100);

            // Use document fragment for better performance
            const fragment = document.createDocumentFragment();
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = filteredActions.map(action => {
                return this.renderActionItem(action, onCopy, onDelete);
            }).join('');

            // Move nodes to fragment
            while (tempDiv.firstChild) {
                fragment.appendChild(tempDiv.firstChild);
            }

            // Clear and append fragment
            container.innerHTML = '';
            container.appendChild(fragment);

            // Attach system message toggle listeners
            this.attachSystemMessageToggles(container);

            // Get all action items for navigation
            const actionItems = Array.from(container.querySelectorAll('.prompt-output-item'));
            
            // Attach navigation button listeners
            actionItems.forEach((itemElement, index) => {
                const prevButton = itemElement.querySelector('.btn-nav-prev');
                const nextButton = itemElement.querySelector('.btn-nav-next');
                
                // Disable prev button for first item
                if (prevButton) {
                    if (index === 0) {
                        prevButton.disabled = true;
                        prevButton.style.opacity = '0.3';
                        prevButton.style.cursor = 'not-allowed';
                    } else {
                        prevButton.addEventListener('click', (e) => {
                            e.stopPropagation();
                            const prevItem = actionItems[index - 1];
                            if (prevItem) {
                                prevItem.scrollIntoView({ behavior: 'smooth', block: 'start' });
                            }
                        });
                    }
                }
                
                // Disable next button for last item
                if (nextButton) {
                    if (index === actionItems.length - 1) {
                        nextButton.disabled = true;
                        nextButton.style.opacity = '0.3';
                        nextButton.style.cursor = 'not-allowed';
                    } else {
                        nextButton.addEventListener('click', (e) => {
                            e.stopPropagation();
                            const nextItem = actionItems[index + 1];
                            if (nextItem) {
                                nextItem.scrollIntoView({ behavior: 'smooth', block: 'start' });
                            }
                        });
                    }
                }
            });

            // Attach copy and delete button listeners
            container.querySelectorAll('.btn-copy-output').forEach(button => {
                button.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    const actionId = button.getAttribute('data-action-id');
                    if (onCopy) {
                        const success = await onCopy(actionId);
                        // Could show a toast notification here
                    }
                });
            });

            container.querySelectorAll('.btn-delete-output').forEach(button => {
                button.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    const actionId = button.getAttribute('data-action-id');
                    if (onDelete) {
                        try {
                            await onDelete(actionId);
                            // Results will be refreshed by the caller
                        } catch (error) {
                            console.error('[UI] Delete failed:', error);
                        }
                    }
                });
            });

            // Auto-scroll to bottom only if user was already at bottom
            // This prevents interrupting reading when results are refreshed
            if (wasAtBottomBefore) {
                requestAnimationFrame(() => {
                    requestAnimationFrame(() => {
                        if (container) {
                            container.scrollTop = container.scrollHeight;
                        }
                    });
                });
            } else {
                // Restore scroll position when user wasn't at bottom
                // Wait for layout to complete before restoring scroll position
                requestAnimationFrame(() => {
                    requestAnimationFrame(() => {
                        if (container) {
                            container.scrollTop = scrollTopBefore;
                        }
                    });
                });
            }
        },

        /**
         * Render a single action item
         * @param {Object} action - Action object
         * @param {Function} onCopy - Copy callback
         * @param {Function} onDelete - Delete callback
         * @returns {string} HTML string
         */
        renderActionItem(action, onCopy, onDelete) {
            const actionContent = action.actions?.content || '';
            const content = typeof actionContent === 'string' 
                ? actionContent 
                : JSON.stringify(actionContent, null, 2);
            
            const createdAt = action.created_at 
                ? new Date(action.created_at).toLocaleString() 
                : 'Unknown';
            
            const metadata = action.actions || {};
            
            // Parse prompt_text_sent to extract system and user messages
            const promptTextSent = action.prompt_text_sent || '';
            let systemMessage = '';
            let userMessage = '';
            
            if (promptTextSent.includes('System:') && promptTextSent.includes('User:')) {
                const parts = promptTextSent.split('User:');
                systemMessage = parts[0].replace('System:', '').trim();
                userMessage = parts.slice(1).join('User:').trim();
            } else {
                systemMessage = action.prompt_system_message || promptTextSent;
                userMessage = '';
            }

            const promptName = action.prompt_name || 'Unknown';
            const promptVersion = action.prompt_version !== null && action.prompt_version !== undefined 
                ? `v${action.prompt_version}` 
                : '';

            // Handle user message truncation
            const MAX_PREVIEW_LENGTH = 200;
            let userMessageHtml = '';
            if (userMessage) {
                const isLong = userMessage.length > MAX_PREVIEW_LENGTH;
                const preview = isLong ? userMessage.substring(0, MAX_PREVIEW_LENGTH) + '...' : userMessage;
                userMessageHtml = `
                    <div style="margin-top: 8px;">
                        <div style="font-size: 12px; color: var(--text); margin-top: 4px;">
                            <strong>User Message:</strong> 
                            <span class="user-message-preview" id="user-msg-preview-${action.id}">${DOM.escapeHtml(preview)}</span>
                            ${isLong ? `<span class="user-message-full" id="user-msg-full-${action.id}" style="display: none;">${DOM.escapeHtml(userMessage)}</span>` : ''}
                        </div>
                        ${isLong ? `
                            <button class="toggle-user-message" data-action-id="${action.id}" style="background: none; border: none; color: #666; cursor: pointer; font-size: 12px; padding: 0; text-decoration: underline; margin-top: 4px;">
                                <span class="toggle-text">Show</span> Full User Message
                            </button>
                        ` : ''}
                    </div>
                `;
            }

            return `
                <div class="prompt-output-item" data-action-id="${action.id}" data-prompt-name="${DOM.escapeHtmlForAttribute(promptName)}" data-prompt-version="${action.prompt_version || ''}">
                    <div class="prompt-output-header">
                        <div class="prompt-output-meta">
                            <div style="margin-bottom: 4px;">
                                <strong>${DOM.escapeHtml(promptName)} ${promptVersion}</strong>
                                <span style="color: var(--muted); font-size: 12px; margin-left: 12px;">${createdAt}</span>
                                ${metadata.model ? `<span style="color: var(--muted); font-size: 12px; margin-left: 8px;">• ${DOM.escapeHtml(metadata.model)}</span>` : ''}
                                ${metadata.tokens_used ? `<span style="color: var(--muted); font-size: 12px; margin-left: 8px;">• ${metadata.tokens_used} tokens</span>` : ''}
                            </div>
                            ${userMessageHtml}
                            ${systemMessage ? `
                                <div style="margin-top: 8px;">
                                    <button class="toggle-system-message" data-action-id="${action.id}" style="background: none; border: none; color: #666; cursor: pointer; font-size: 12px; padding: 0; text-decoration: underline;">
                                        <span class="toggle-text">Show</span> System Message
                                    </button>
                                    <div class="system-message-content" id="system-msg-${action.id}" style="display: none; margin-top: 8px; padding: 12px; background: #f7fafc; border-radius: 6px; font-size: 12px; color: var(--text); white-space: pre-wrap; font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;">${DOM.escapeHtml(systemMessage)}</div>
                                </div>
                            ` : ''}
                        </div>
                        <div class="prompt-output-actions">
                            <button class="btn-nav-prev" data-action-id="${action.id}" title="Previous message">
                                <img src="https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/insights/1767496461750-8ikag.png" alt="Previous" width="16" height="16">
                            </button>
                            <button class="btn-nav-next" data-action-id="${action.id}" title="Next message">
                                <img src="https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/insights/1767496465023-xx3hee.png" alt="Next" width="16" height="16">
                            </button>
                            <button class="btn-copy-output" data-action-id="${action.id}" title="Copy to clipboard">
                                <img src="https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/icons/copy_button.png" alt="Copy" width="16" height="16">
                            </button>
                            <button class="btn-delete-output" data-action-id="${action.id}" title="Delete">
                                <img src="https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/icons/delete_button.png" alt="Delete" width="16" height="16">
                            </button>
                        </div>
                    </div>
                    <div class="prompt-result-content" data-raw-text="${DOM.escapeHtmlForAttribute(content)}">${this.convertMarkdown(content)}</div>
                </div>
            `;
        },

        /**
         * Attach system message toggle listeners
         * @param {HTMLElement} container - Container element
         */
        attachSystemMessageToggles(container) {
            if (!container) return;

            container.querySelectorAll('.toggle-system-message').forEach(button => {
                button.addEventListener('click', (e) => {
                    const actionId = button.getAttribute('data-action-id');
                    const systemMsgDiv = document.getElementById(`system-msg-${actionId}`);
                    const toggleText = button.querySelector('.toggle-text');
                    
                    if (systemMsgDiv && toggleText) {
                        if (systemMsgDiv.style.display === 'none') {
                            systemMsgDiv.style.display = 'block';
                            toggleText.textContent = 'Hide';
                        } else {
                            systemMsgDiv.style.display = 'none';
                            toggleText.textContent = 'Show';
                        }
                    }
                });
            });

            // Attach user message toggle listeners
            container.querySelectorAll('.toggle-user-message').forEach(button => {
                button.addEventListener('click', (e) => {
                    const actionId = button.getAttribute('data-action-id');
                    const previewDiv = document.getElementById(`user-msg-preview-${actionId}`);
                    const fullDiv = document.getElementById(`user-msg-full-${actionId}`);
                    const toggleText = button.querySelector('.toggle-text');
                    
                    if (previewDiv && fullDiv && toggleText) {
                        if (previewDiv.style.display !== 'none') {
                            // Show full message
                            previewDiv.style.display = 'none';
                            fullDiv.style.display = 'inline';
                            toggleText.textContent = 'Hide';
                        } else {
                            // Show preview
                            previewDiv.style.display = 'inline';
                            fullDiv.style.display = 'none';
                            toggleText.textContent = 'Show';
                        }
                    }
                });
            });
        },

        /**
         * Render loading state
         * @param {HTMLElement} container - Container element
         * @param {string} message - Loading message
         */
        renderLoading(container, message = 'Loading...') {
            if (!container) return;

            container.innerHTML = `
                <div class="ai-loading">
                    <div class="ai-loading-spinner"></div>
                    <p>${DOM.escapeHtml(message)}</p>
                </div>
            `;
        },

        /**
         * Render error state
         * @param {HTMLElement} container - Container element
         * @param {string} message - Error message
         */
        renderError(container, message = 'An error occurred') {
            if (!container) return;

            container.innerHTML = `
                <div style="padding: 24px;">
                    <h3 style="color: var(--danger); margin-bottom: 12px;">Error</h3>
                    <p style="color: var(--text);">${DOM.escapeHtml(message)}</p>
                </div>
            `;
        },

        /**
         * Create a streaming result item placeholder
         * @param {HTMLElement} container - Container element to append to
         * @param {string} promptName - Prompt name
         * @param {string|number} promptVersion - Prompt version
         * @param {string} userMessage - User message (optional)
         * @returns {HTMLElement} The created streaming item element
         */
        createStreamingResultItem(container, promptName, promptVersion, userMessage = '') {
            if (!container) return null;

            const streamingId = `streaming-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
            const createdAt = new Date().toLocaleString();
            const versionStr = promptVersion !== null && promptVersion !== undefined ? `v${promptVersion}` : '';

            const itemHTML = `
                <div class="prompt-output-item" data-streaming-id="${streamingId}" data-prompt-name="${DOM.escapeHtmlForAttribute(promptName)}" data-prompt-version="${promptVersion || ''}">
                    <div class="prompt-output-header" data-streaming-header="${streamingId}">
                        <div class="prompt-output-meta">
                            <div style="margin-bottom: 4px;">
                                <strong>${DOM.escapeHtml(promptName)} ${versionStr}</strong>
                                <span style="color: var(--muted); font-size: 12px; margin-left: 12px;">${createdAt}</span>
                                <span style="color: var(--muted); font-size: 12px; margin-left: 8px;">• Streaming...</span>
                            </div>
                            ${userMessage ? `
                                <div style="margin-top: 8px;">
                                    <div style="font-size: 12px; color: var(--text); margin-top: 4px;">
                                        <strong>User Message:</strong> 
                                        <span>${DOM.escapeHtml(userMessage.length > 200 ? userMessage.substring(0, 200) + '...' : userMessage)}</span>
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                        <div class="prompt-output-actions">
                            <div class="ai-loading-spinner" style="width: 16px; height: 16px; border-width: 2px; margin-right: 8px;"></div>
                        </div>
                    </div>
                    <div class="prompt-result-content" data-streaming-content="${streamingId}"></div>
                </div>
            `;

            // Append to container
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = itemHTML;
            const itemElement = tempDiv.firstElementChild;
            container.appendChild(itemElement);

            // Initialize auto-scroll state: enabled by default, user can disable by scrolling
            itemElement.dataset.autoScrollEnabled = 'true';
            itemElement.dataset.lastScrollTop = container.scrollTop.toString();

            // Add scroll event listener to detect manual scrolling
            let scrollTimeout = null;
            const handleScroll = () => {
                const currentScrollTop = container.scrollTop;
                const lastScrollTop = parseFloat(itemElement.dataset.lastScrollTop || '0');
                
                // If user scrolled up manually, disable auto-scroll
                if (currentScrollTop < lastScrollTop - 5) { // 5px threshold to account for minor adjustments
                    console.log('[UI] User scrolled up manually, disabling auto-scroll for streaming item', {
                        streamingId,
                        currentScrollTop,
                        lastScrollTop
                    });
                    itemElement.dataset.autoScrollEnabled = 'false';
                }
                
                itemElement.dataset.lastScrollTop = currentScrollTop.toString();
                
                // Clear timeout and set new one to detect when scrolling stops
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(() => {
                    // After scrolling stops, check if user is at bottom
                    const isAtBottom = this._isAtBottom(container);
                    if (isAtBottom) {
                        // Re-enable auto-scroll if user scrolled back to bottom
                        console.log('[UI] User scrolled back to bottom, re-enabling auto-scroll', { streamingId });
                        itemElement.dataset.autoScrollEnabled = 'true';
                    }
                }, 150);
            };

            container.addEventListener('scroll', handleScroll, { passive: true });
            
            // Store cleanup function on element
            itemElement._cleanupScrollListener = () => {
                container.removeEventListener('scroll', handleScroll);
                if (scrollTimeout) clearTimeout(scrollTimeout);
            };

            // Initial scroll to bottom
            requestAnimationFrame(() => {
                if (container) {
                    container.scrollTop = container.scrollHeight;
                    itemElement.dataset.lastScrollTop = container.scrollTop.toString();
                }
            });

            return itemElement;
        },

        /**
         * Check if container is scrolled to bottom (within threshold)
         * @param {HTMLElement} container - Container element
         * @param {number} threshold - Threshold in pixels (default: 50)
         * @returns {boolean} True if at bottom
         */
        _isAtBottom(container, threshold = 50) {
            if (!container) return false;
            const scrollTop = container.scrollTop;
            const scrollHeight = container.scrollHeight;
            const clientHeight = container.clientHeight;
            const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
            return distanceFromBottom <= threshold;
        },

        /**
         * Check if streaming header is at or above the top of the container viewport
         * Uses getBoundingClientRect to check when header aligns with container top
         * @param {HTMLElement} itemElement - Streaming item element
         * @param {HTMLElement} container - Container element
         * @returns {boolean} True if header is at or above top of viewport
         */
        _isHeaderAtTop(itemElement, container) {
            if (!itemElement || !container) return false;
            
            const header = itemElement.querySelector('[data-streaming-header]');
            if (!header) return false;

            // Use getBoundingClientRect to get current viewport positions
            const containerRect = container.getBoundingClientRect();
            const headerRect = header.getBoundingClientRect();
            
            // When the header reaches the top of the container, headerRect.top should equal containerRect.top
            // We want to stop when header's top edge is at or just above the container's top edge
            // Add a small threshold to account for subpixel rendering and rounding
            const threshold = 3;
            const headerTopRelativeToContainer = headerRect.top - containerRect.top;
            const isAtTop = headerTopRelativeToContainer <= threshold;
            
            // Only log when we're close to the top to avoid spam
            if (headerTopRelativeToContainer <= 50) {
                console.log('[UI] Header position check', {
                    headerTop: headerRect.top,
                    containerTop: containerRect.top,
                    headerTopRelativeToContainer,
                    scrollTop: container.scrollTop,
                    isAtTop,
                    threshold
                });
            }
            
            return isAtTop;
        },

        /**
         * Append content to a streaming result item
         * @param {HTMLElement} itemElement - The streaming item element
         * @param {string} chunk - Content chunk to append
         */
        appendToStreamingItem(itemElement, chunk) {
            if (!itemElement || !chunk) return;

            const contentElement = itemElement.querySelector(`[data-streaming-content]`);
            if (!contentElement) return;

            // Accumulate text for markdown rendering
            // Store raw text in WeakMap to avoid data attribute size limits
            const currentText = streamingContentStore.get(contentElement) || '';
            const newText = currentText + chunk;
            
            try {
                // Store in WeakMap instead of data attribute
                streamingContentStore.set(contentElement, newText);

                // Render markdown and update innerHTML
                contentElement.innerHTML = this.convertMarkdown(newText);
            } catch (error) {
                console.error('[UI] Error in appendToStreamingItem:', error);
                throw error;
            }

            // Check if auto-scroll is enabled
            const autoScrollEnabled = itemElement.dataset.autoScrollEnabled === 'true';
            if (!autoScrollEnabled) {
                // Auto-scroll disabled, don't scroll
                return;
            }

            const container = itemElement.closest('.slideout-content') || itemElement.parentElement;
            if (!container) return;

            // Check if user is at bottom before auto-scrolling
            const isAtBottom = this._isAtBottom(container);
            if (!isAtBottom) {
                // User is not at bottom, don't auto-scroll
                console.log('[UI] User not at bottom, skipping auto-scroll', {
                    streamingId: itemElement.dataset.streamingId,
                    scrollTop: container.scrollTop,
                    scrollHeight: container.scrollHeight,
                    clientHeight: container.clientHeight
                });
                return;
            }

            // User is at bottom and auto-scroll is enabled, scroll to bottom
            // But first check if header will reach top after this scroll
            requestAnimationFrame(() => {
                if (container && itemElement.dataset.autoScrollEnabled === 'true') {
                    // Store current scroll position
                    const scrollBefore = container.scrollTop;
                    
                    // Scroll to bottom
                    container.scrollTop = container.scrollHeight;
                    itemElement.dataset.lastScrollTop = container.scrollTop.toString();
                    
                    // Check if header is now at top AFTER scrolling
                    // Use requestAnimationFrame to ensure DOM has updated
                    requestAnimationFrame(() => {
                        if (this._isHeaderAtTop(itemElement, container)) {
                            console.log('[UI] Streaming header reached top of viewport after scroll, disabling auto-scroll', {
                                streamingId: itemElement.dataset.streamingId,
                                scrollBefore,
                                scrollAfter: container.scrollTop
                            });
                            itemElement.dataset.autoScrollEnabled = 'false';
                        }
                    });
                }
            });
        },

        /**
         * Finalize a streaming result item (remove loading, add metadata)
         * @param {HTMLElement} itemElement - The streaming item element
         * @param {Object} metadata - Metadata object with tokens_used, model, etc.
         */
        finalizeStreamingItem(itemElement, metadata = {}) {
            if (!itemElement) return;

            // Clean up scroll listener
            if (itemElement._cleanupScrollListener) {
                itemElement._cleanupScrollListener();
                delete itemElement._cleanupScrollListener;
            }

            // Remove streaming ID attribute
            const streamingId = itemElement.getAttribute('data-streaming-id');
            if (streamingId) {
                itemElement.removeAttribute('data-streaming-id');
            }

            // Remove streaming header attribute
            const header = itemElement.querySelector('[data-streaming-header]');
            if (header) {
                header.removeAttribute('data-streaming-header');
            }

            // Update header to remove loading indicator and add metadata
            const metaDiv = header?.querySelector('.prompt-output-meta > div');
            const actionsDiv = header?.querySelector('.prompt-output-actions');

            if (metaDiv) {
                // Remove "Streaming..." text
                const streamingSpan = metaDiv.querySelector('span:last-child');
                if (streamingSpan && streamingSpan.textContent.includes('Streaming')) {
                    streamingSpan.remove();
                }

                // Add metadata if available
                if (metadata.model || metadata.tokens_used) {
                    const metadataHTML = [];
                    if (metadata.model) {
                        metadataHTML.push(`<span style="color: var(--muted); font-size: 12px; margin-left: 8px;">• ${DOM.escapeHtml(metadata.model)}</span>`);
                    }
                    if (metadata.tokens_used) {
                        metadataHTML.push(`<span style="color: var(--muted); font-size: 12px; margin-left: 8px;">• ${metadata.tokens_used} tokens</span>`);
                    }
                    if (metadataHTML.length > 0) {
                        metaDiv.insertAdjacentHTML('beforeend', metadataHTML.join(''));
                    }
                }
            }

            // Remove loading spinner and add action buttons
            if (actionsDiv) {
                actionsDiv.innerHTML = `
                    <button class="btn-nav-prev" data-action-id="streaming-${streamingId}" title="Previous message">
                        <img src="https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/insights/1767496461750-8ikag.png" alt="Previous" width="16" height="16">
                    </button>
                    <button class="btn-nav-next" data-action-id="streaming-${streamingId}" title="Next message">
                        <img src="https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/insights/1767496465023-xx3hee.png" alt="Next" width="16" height="16">
                    </button>
                    <button class="btn-copy-output" data-action-id="streaming-${streamingId}" title="Copy to clipboard">
                        <img src="https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/icons/copy_button.png" alt="Copy" width="16" height="16">
                    </button>
                    <button class="btn-delete-output" data-action-id="streaming-${streamingId}" title="Delete">
                        <img src="https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/icons/delete_button.png" alt="Delete" width="16" height="16">
                    </button>
                `;
            }

            // Remove streaming content attribute and clean up WeakMap entry
            const contentElementFinal = itemElement.querySelector(`[data-streaming-content]`);
            if (contentElementFinal) {
                contentElementFinal.removeAttribute('data-streaming-content');
                // Clean up WeakMap entry (WeakMap will automatically clean up when element is GC'd, but we can clear it explicitly)
                streamingContentStore.delete(contentElementFinal);
            }

            // Clean up auto-scroll tracking attributes
            delete itemElement.dataset.autoScrollEnabled;
            delete itemElement.dataset.lastScrollTop;
        }
    };

    // Export
    window.PromptUIRenderer = UIRenderer;
})();

