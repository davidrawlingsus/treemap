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

    /**
     * UI Renderer
     */
    const UIRenderer = {
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

            // Auto-scroll to bottom
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    if (container) {
                        container.scrollTop = container.scrollHeight;
                    }
                });
            });
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
                            <button class="btn-copy-output" data-action-id="${action.id}" title="Copy to clipboard">
                                <img src="https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/icons/copy_button.png" alt="Copy" width="16" height="16">
                            </button>
                            <button class="btn-delete-output" data-action-id="${action.id}" title="Delete">
                                <img src="https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/icons/delete_button.png" alt="Delete" width="16" height="16">
                            </button>
                        </div>
                    </div>
                    <div class="prompt-result-content">${DOM.escapeHtml(content)}</div>
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
                    <div class="prompt-output-header">
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
                    <div class="prompt-result-content" data-streaming-content="${streamingId}" style="font-family: monospace; font-size: 12px; white-space: pre-wrap; word-break: break-word;"></div>
                </div>
            `;

            // Append to container
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = itemHTML;
            const itemElement = tempDiv.firstElementChild;
            container.appendChild(itemElement);

            // Auto-scroll to bottom
            requestAnimationFrame(() => {
                if (container) {
                    container.scrollTop = container.scrollHeight;
                }
            });

            return itemElement;
        },

        /**
         * Append content to a streaming result item
         * @param {HTMLElement} itemElement - The streaming item element
         * @param {string} chunk - Content chunk to append
         */
        appendToStreamingItem(itemElement, chunk) {
            if (!itemElement || !chunk) return;

            const contentElement = itemElement.querySelector(`[data-streaming-content]`);
            if (contentElement) {
                // Append chunk (escape HTML for safety)
                contentElement.textContent += chunk;

                // Auto-scroll to bottom
                const container = itemElement.closest('.slideout-content') || itemElement.parentElement;
                if (container) {
                    requestAnimationFrame(() => {
                        container.scrollTop = container.scrollHeight;
                    });
                }
            }
        },

        /**
         * Finalize a streaming result item (remove loading, add metadata)
         * @param {HTMLElement} itemElement - The streaming item element
         * @param {Object} metadata - Metadata object with tokens_used, model, etc.
         */
        finalizeStreamingItem(itemElement, metadata = {}) {
            if (!itemElement) return;

            // Remove streaming ID attribute
            const streamingId = itemElement.getAttribute('data-streaming-id');
            if (streamingId) {
                itemElement.removeAttribute('data-streaming-id');
            }

            // Update header to remove loading indicator and add metadata
            const header = itemElement.querySelector('.prompt-output-header');
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
                    <button class="btn-copy-output" data-action-id="streaming-${streamingId}" title="Copy to clipboard">
                        <img src="https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/icons/copy_button.png" alt="Copy" width="16" height="16">
                    </button>
                    <button class="btn-delete-output" data-action-id="streaming-${streamingId}" title="Delete">
                        <img src="https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/icons/delete_button.png" alt="Delete" width="16" height="16">
                    </button>
                `;
            }

            // Remove streaming content attribute
            const contentElement = itemElement.querySelector(`[data-streaming-content]`);
            if (contentElement) {
                contentElement.removeAttribute('data-streaming-content');
            }
        }
    };

    // Export
    window.PromptUIRenderer = UIRenderer;
})();

