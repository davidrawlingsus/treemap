/**
 * Action Renderer Module
 * Handles rendering of prompt execution results/actions
 */

(function() {
    'use strict';

    if (!window.FounderAdmin || !window.PromptEngineeringState || !window.MarkdownConverter) {
        console.error('[ACTION_RENDERER] Dependencies not loaded');
        return;
    }

    const { DOM } = window.FounderAdmin;
    const state = window.PromptEngineeringState;
    const { convertMarkdown } = window.MarkdownConverter;

    // Constants
    const USER_MESSAGE_PREVIEW_LENGTH = 200; // characters
    const SCROLL_BOTTOM_THRESHOLD = 50; // px
    const DONE_CHECK_IMAGE_URL = 'https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/icons/done_check_black_1768289477172.png';

    /**
     * Render prompt results/actions
     * @param {HTMLElement} container - Container element
     * @param {Array} actions - Array of action objects
     * @param {Function} onCopy - Callback when copy button is clicked
     * @param {Function} onDelete - Callback when delete button is clicked
     */
    function renderActions(container, actions, onCopy, onDelete) {
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

        if (filterState.models.size > 0) {
            filteredActions = filteredActions.filter(action => {
                const model = action.actions?.model;
                return model && filterState.models.has(model);
            });
        }

        if (filteredActions.length === 0) {
            container.innerHTML = '<p style="color: var(--muted); padding: 24px; text-align: center;">No execution results match the selected filters.</p>';
            return;
        }

        // Store scroll position before clearing
        const scrollTopBefore = container.scrollTop;
        const wasAtBottomBefore = _isAtBottom(container, SCROLL_BOTTOM_THRESHOLD);

        // Use document fragment for better performance
        const fragment = document.createDocumentFragment();
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = filteredActions.map(action => {
            return renderActionItem(action, onCopy, onDelete);
        }).join('');

        // Move nodes to fragment
        while (tempDiv.firstChild) {
            fragment.appendChild(tempDiv.firstChild);
        }

        // Clear and append fragment
        container.innerHTML = '';
        container.appendChild(fragment);

        // Attach system message toggle listeners
        attachSystemMessageToggles(container);
        
        // Attach idea card button listeners (with event delegation for dynamic content)
        attachIdeaCardListeners(container);

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
                        console.error('[ACTION_RENDERER] Delete failed:', error);
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
    }

    /**
     * Render a single action item
     * @param {Object} action - Action object
     * @param {Function} onCopy - Copy callback
     * @param {Function} onDelete - Delete callback
     * @returns {string} HTML string
     */
    function renderActionItem(action, onCopy, onDelete) {
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
        let userMessageHtml = '';
        if (userMessage) {
            const isLong = userMessage.length > USER_MESSAGE_PREVIEW_LENGTH;
            const preview = isLong ? userMessage.substring(0, USER_MESSAGE_PREVIEW_LENGTH) + '...' : userMessage;
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
                <div class="prompt-result-content" data-raw-text="${DOM.escapeHtmlForAttribute(content)}">${convertMarkdown(content)}</div>
            </div>
        `;
    }

    /**
     * Attach system message toggle listeners
     * @param {HTMLElement} container - Container element
     */
    function attachSystemMessageToggles(container) {
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
    }

    /**
     * Get current client ID from various possible sources
     * @returns {string|null} Client ID or null if not found
     */
    function getCurrentClientId() {
        // Try window.currentClientId first
        if (typeof window.currentClientId !== 'undefined' && window.currentClientId) {
            return window.currentClientId;
        }
        
        // Try window.insightsCurrentClientId
        if (typeof window.insightsCurrentClientId !== 'undefined' && window.insightsCurrentClientId) {
            return window.insightsCurrentClientId;
        }
        
        // Try to access via Function constructor (safe eval) to access script-scoped variables
        try {
            // eslint-disable-next-line no-new-func
            const getClientId = new Function('return typeof currentClientId !== "undefined" ? currentClientId : null');
            const clientId = getClientId();
            if (clientId) {
                return clientId;
            }
        } catch (e) {
            // Ignore - variable not accessible this way
        }
        
        return null;
    }

    /**
     * Create an insight from idea card data
     * @param {Object} ideaData - Idea card data object
     * @returns {Promise<void>}
     */
    async function createInsightFromIdeaCard(ideaData) {
        // Get current client ID
        const currentClientId = getCurrentClientId();
        if (!currentClientId) {
            throw new Error('No client selected. Please select a client first.');
        }

        // Get origin and voc_json from SlideoutPanel (set when AI expert panel or history action is opened)
        const slideoutPanel = window.SlideoutPanel;
        if (!slideoutPanel || !slideoutPanel.createInsightOrigin) {
            throw new Error('No context available. Please open the AI expert panel again.');
        }
        
        // Get voc_json from stored action data (for history items) or currentVocData (for AI expert)
        const vocJsonData = slideoutPanel.currentActionVocJson || slideoutPanel.currentVocData || null;

        // Get API base URL
        const API_BASE_URL = window.APP_CONFIG?.API_BASE_URL || 'http://localhost:8000';

        // Get auth headers
        let getAuthHeaders;
        if (typeof window.getAuthHeaders === 'function') {
            getAuthHeaders = window.getAuthHeaders;
        } else if (typeof window.Auth !== 'undefined' && typeof window.Auth.getAuthHeaders === 'function') {
            getAuthHeaders = window.Auth.getAuthHeaders;
        } else {
            throw new Error('Authentication not available. Please log in again.');
        }

        // Map idea card fields to insight schema
        // Badge content (testType) - this is the type of test (headlines, social proof, lead-in, etc.)
        const badgeContent = ideaData.testType || ideaData.test_type || ideaData.type || '';
        // Application field from idea card - comma-separated values (homepage, pdp, google ad, etc.)
        const applicationField = ideaData.application || null;
        // Details/description goes to notes (the WYSIWYG body) and description
        const detailsContent = ideaData.details || ideaData.description || null;
        
        const insightData = {
            name: ideaData.title || ideaData.name || 'Untitled Idea',
            type: badgeContent || '', // Type is the badge content (test type)
            application: applicationField || null, // Application is the application field (comma-separated)
            description: detailsContent, // Keep description for backwards compatibility
            notes: detailsContent, // Details go to notes (the WYSIWYG body/editor)
            origins: [slideoutPanel.createInsightOrigin],
            verbatims: null,
            metadata: null,
            voc_json: vocJsonData
        };

        // Create the insight via API
        const response = await fetch(`${API_BASE_URL}/api/clients/${currentClientId}/insights`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(insightData)
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Failed to create insight' }));
            throw new Error(error.detail || `Failed to create insight: ${response.statusText}`);
        }

        return await response.json();
    }

    /**
     * Attach idea card button listeners using event delegation
     * @param {HTMLElement} container - Container element
     */
    function attachIdeaCardListeners(container) {
        if (!container) return;
        
        // Check if we've already attached the delegated listener
        if (container.dataset.ideaListenerAttached === 'true') {
            return;
        }
        
        // Use event delegation to handle dynamically added idea cards
        container.addEventListener('click', async (e) => {
            const button = e.target.closest('.pe-idea-card__add');
            if (!button) return;
            
            e.stopPropagation();
            
            const ideaContainer = button.closest('.pe-idea-card');
            if (!ideaContainer) return;

            // Check if already processing (prevent duplicate clicks)
            if (button.disabled || button.dataset.processing === 'true') {
                return;
            }

            // Get the idea data
            let ideaData;
            try {
                const ideaDataStr = button.getAttribute('data-idea');
                if (!ideaDataStr) {
                    console.error('[ACTION_RENDERER] No idea data found');
                    alert('Error: No idea data found');
                    return;
                }
                ideaData = JSON.parse(ideaDataStr);
            } catch (e) {
                console.error('[ACTION_RENDERER] Failed to parse idea data:', e);
                alert('Error: Failed to parse idea data');
                return;
            }

            // Set processing state
            button.disabled = true;
            button.dataset.processing = 'true';
            const originalText = button.textContent;
            button.textContent = '...';
            button.style.opacity = '0.6';
            button.style.cursor = 'wait';

            try {
                // Create insight
                const newInsight = await createInsightFromIdeaCard(ideaData);
                console.log('[ACTION_RENDERER] Insight created successfully:', newInsight);

                // Update button to show success state
                ideaContainer.classList.add('is-selected');
                button.classList.add('is-selected');
                button.innerHTML = `<img src="${DONE_CHECK_IMAGE_URL}" alt="Added" style="width: 70%; height: 70%; object-fit: contain;" />`;
                button.style.opacity = '1';
                button.style.cursor = 'default';
                button.title = 'Added to insights';

                // Refresh insights list if available
                if (typeof window.loadInsightsPage === 'function') {
                    window.loadInsightsPage();
                } else if (typeof window.loadInsights === 'function') {
                    window.loadInsights();
                }

                // Show brief success feedback
                const successMsg = document.createElement('div');
                successMsg.textContent = 'Idea added to insights';
                successMsg.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #B9F040; color: #000; padding: 12px 20px; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 10000; font-size: 14px; font-weight: 500;';
                document.body.appendChild(successMsg);
                setTimeout(() => {
                    successMsg.style.transition = 'opacity 0.3s ease';
                    successMsg.style.opacity = '0';
                    setTimeout(() => successMsg.remove(), 300);
                }, 2000);

            } catch (error) {
                console.error('[ACTION_RENDERER] Failed to create insight:', error);
                
                // Reset button state
                button.disabled = false;
                button.dataset.processing = 'false';
                button.textContent = originalText;
                button.style.opacity = '1';
                button.style.cursor = 'pointer';

                // Show error message
                alert('Error: ' + (error.message || 'Failed to add idea to insights'));
            }
        });
        
        // Mark that we've attached the listener to prevent duplicates
        container.dataset.ideaListenerAttached = 'true';
    }

    /**
     * Render loading state
     * @param {HTMLElement} container - Container element
     * @param {string} message - Loading message
     */
    function renderLoading(container, message = 'Loading...') {
        if (!container) return;

        container.innerHTML = `
            <div class="ai-loading">
                <div class="ai-loading-spinner"></div>
                <p>${DOM.escapeHtml(message)}</p>
            </div>
        `;
    }

    /**
     * Render error state
     * @param {HTMLElement} container - Container element
     * @param {string} message - Error message
     */
    function renderError(container, message = 'An error occurred') {
        if (!container) return;

        container.innerHTML = `
            <div style="padding: 24px;">
                <h3 style="color: var(--danger); margin-bottom: 12px;">Error</h3>
                <p style="color: var(--text);">${DOM.escapeHtml(message)}</p>
            </div>
        `;
    }

    /**
     * Check if container is scrolled to bottom (within threshold)
     * @param {HTMLElement} container - Container element
     * @param {number} threshold - Threshold in pixels
     * @returns {boolean} True if at bottom
     */
    function _isAtBottom(container, threshold) {
        if (!container) return false;
        const scrollTop = container.scrollTop;
        const scrollHeight = container.scrollHeight;
        const clientHeight = container.clientHeight;
        const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
        return distanceFromBottom <= threshold;
    }

    // Export
    window.ActionRenderer = {
        renderActions,
        renderActionItem,
        attachSystemMessageToggles,
        attachIdeaCardListeners,
        renderLoading,
        renderError
    };
})();
