/**
 * Prompt Engineering Slideout Panel
 * Manages slideout panel for displaying prompt results and chat
 */

(function() {
    'use strict';

    if (!window.FounderAdmin || !window.FounderAdminComponents || !window.PromptEngineeringState || !window.PromptAPI || !window.PromptUIRenderer) {
        console.error('[PROMPT_SLIDEOUT] Dependencies not loaded');
        return;
    }

    const { SlideoutPanel } = window.FounderAdminComponents;
    const state = window.PromptEngineeringState;
    const PromptAPI = window.PromptAPI;
    const UIRenderer = window.PromptUIRenderer;
    const { DOM } = window.FounderAdmin;

    // Constants
    const SLIDEOUT_DEFAULT_WIDTH = '500px';
    const SLIDEOUT_EXPANDED_WIDTH = '50vw';
    const SCROLL_TO_TOP_THRESHOLD = 200; // px
    const REFRESH_DELAY_AFTER_STREAMING = 500; // ms
    const RESET_ICON_DELAY = 2000; // ms

    /**
     * Slideout Manager
     */
    const SlideoutManager = {
        slideout: null,
        elements: null,
        onResultsUpdate: null,
        activeStreamingRequests: new Set(), // Track active streaming requests

        /**
         * Initialize slideout manager
         * @param {string} panelId - Slideout panel element ID
         * @param {string} overlayId - Overlay element ID
         * @param {Object} elements - Slideout UI elements
         * @param {Function} onResultsUpdate - Callback when results need to be updated
         */
        init(panelId, overlayId, elements, onResultsUpdate) {
            this.elements = elements;
            this.onResultsUpdate = onResultsUpdate;

            // Create slideout component
            this.slideout = new SlideoutPanel(panelId, overlayId, {
                closeOnOverlayClick: true,
                closeOnEscape: true
            });

            // Add prompt engineering context class
            this.slideout.addContextClass('prompt-engineering-context');

            // Setup chat input
            if (this.elements.chatInput && this.elements.chatSend) {
                this.elements.chatSend.addEventListener('click', () => this.handleChatSubmit());
                this.elements.chatInput.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        this.handleChatSubmit();
                    }
                });
            }

            // Setup to-top button
            this.setupToTopButton();

            // Setup expansion button
            this.setupExpandButton();
        },

        /**
         * Open slideout with title
         * @param {string} title - Slideout title
         */
        open(title = 'LLM Outputs') {
            if (this.slideout) {
                this.slideout.open(title);
                // If there are no active streaming requests, refresh results to show any that completed while closed
                if (this.activeStreamingRequests.size === 0 && state.get('slideoutPromptId')) {
                    // Small delay to ensure slideout is fully opened
                    setTimeout(() => {
                        // Check again inside the callback - streaming might have started in the meantime
                        if (this.activeStreamingRequests.size === 0) {
                            this.displayAllResults(false, 'open-after-streaming');
                        }
                    }, 100);
                }
            }
        },

        /**
         * Close slideout
         * Note: Active streaming requests will continue in the background
         */
        close() {
            if (this.slideout) {
                // Reset expanded state when closing
                if (this.slideout.panel) {
                    this.slideout.panel.classList.remove('expanded');
                }
                if (this.slideout.overlay) {
                    this.slideout.overlay.style.width = SLIDEOUT_DEFAULT_WIDTH;
                }
                this.slideout.close();
            }
            if (this.elements.chatInput) {
                this.elements.chatInput.value = '';
            }
            // Don't clear slideoutPromptId if there are active streaming requests
            // This allows the background streaming to complete and save to history
            if (this.activeStreamingRequests.size === 0) {
                state.set('slideoutPromptId', null);
            }
        },

        /**
         * Execute a prompt (used when opening slideout after save and run)
         * @param {string} userMessage - User message to send with prompt
         */
        async executePrompt(userMessage = '') {
            const promptId = state.get('slideoutPromptId');
            if (!promptId) {
                console.warn('[SLIDEOUT] executePrompt() called but no promptId in state');
                return;
            }

            console.log('[SLIDEOUT] executePrompt() called', {
                promptId,
                userMessage: userMessage.substring(0, 100) + (userMessage.length > 100 ? '...' : ''),
                userMessageLength: userMessage.length,
                timestamp: new Date().toISOString()
            });

            const content = this.slideout?.getContent();
            if (!content) {
                console.warn('[SLIDEOUT] No content element available');
                return;
            }

            try {
                // Get prompt info for display
                let promptName = 'Unknown';
                let promptVersion = null;
                try {
                    const prompt = await PromptAPI.get(promptId);
                    promptName = prompt.name || 'Unknown';
                    promptVersion = prompt.version || null;
                } catch (e) {
                    console.warn('[SLIDEOUT] Failed to fetch prompt info:', e);
                }

                // Track this streaming request BEFORE creating the item
                // This ensures open() method won't call displayAllResults() and clear the container
                const streamingRequestId = `streaming-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
                this.activeStreamingRequests.add(streamingRequestId);

                // Create streaming result item
                const streamingItem = UIRenderer.createStreamingResultItem(
                    content,
                    promptName,
                    promptVersion,
                    userMessage
                );

                if (!streamingItem) {
                    // Remove from active requests if creation failed
                    this.activeStreamingRequests.delete(streamingRequestId);
                    throw new Error('Failed to create streaming result item');
                }

                // Attach idea card listeners immediately so they work during streaming
                // Event delegation means they'll work for idea cards added dynamically
                if (content && UIRenderer.attachIdeaCardListeners) {
                    UIRenderer.attachIdeaCardListeners(content);
                }

                console.log('[SLIDEOUT] Calling PromptAPI.executeStream() from executePrompt()', {
                    promptId,
                    userMessageLength: userMessage.length,
                    timestamp: new Date().toISOString()
                });

                // Execute with streaming
                await PromptAPI.executeStream(
                    promptId,
                    userMessage,
                    // onChunk
                    (chunk) => {
                        // Only update UI if slideout is still open and element exists
                        if (this.slideout?.isOpen() && streamingItem && streamingItem.parentElement) {
                            UIRenderer.appendToStreamingItem(streamingItem, chunk);
                        }
                    },
                    // onDone
                    (metadata) => {
                        console.log('[SLIDEOUT] Streaming completed (executePrompt)', {
                            promptId,
                            tokens_used: metadata.tokens_used,
                            model: metadata.model,
                            timestamp: new Date().toISOString()
                        });
                        
                        // Remove from active requests
                        this.activeStreamingRequests.delete(streamingRequestId);
                        
                        // Only update UI if slideout is still open and element exists
                        if (this.slideout?.isOpen() && streamingItem && streamingItem.parentElement) {
                            UIRenderer.finalizeStreamingItem(streamingItem, metadata);
                            
                            // Refresh results to get the saved action (without showing loading state)
                            console.log('[SLIDEOUT] Scheduling displayAllResults() after streaming (executePrompt)', {
                                delay: 500,
                                timestamp: new Date().toISOString()
                            });
                            setTimeout(() => {
                                console.log('[SLIDEOUT] Calling displayAllResults() after streaming timeout (executePrompt)');
                                this.displayAllResults(false, 'executePrompt-onDone');
                            }, REFRESH_DELAY_AFTER_STREAMING);
                        } else {
                            // Slideout was closed, but still refresh history if slideout is reopened
                            // The backend has already saved the action, so it will appear in history
                            console.log('[SLIDEOUT] Streaming completed but slideout is closed, action saved to history', {
                                promptId,
                                timestamp: new Date().toISOString()
                            });
                        }
                        
                        // Clear slideoutPromptId if no more active requests
                        if (this.activeStreamingRequests.size === 0) {
                            state.set('slideoutPromptId', null);
                        }
                    },
                    // onError
                    (error) => {
                        console.error('[SLIDEOUT] Streaming error', {
                            promptId,
                            error: error.message || String(error),
                            timestamp: new Date().toISOString()
                        });
                        
                        // Remove from active requests
                        this.activeStreamingRequests.delete(streamingRequestId);
                        
                        // Only update UI if slideout is still open and element exists
                        if (this.slideout?.isOpen() && streamingItem && streamingItem.parentElement) {
                            // Update the item to show error
                            const contentDiv = streamingItem.querySelector('.prompt-result-content');
                            if (contentDiv) {
                                contentDiv.textContent = `Error: ${error.message || 'Unknown error occurred'}`;
                            }
                            UIRenderer.finalizeStreamingItem(streamingItem, {});
                        }
                        
                        // Clear slideoutPromptId if no more active requests
                        if (this.activeStreamingRequests.size === 0) {
                            state.set('slideoutPromptId', null);
                        }
                    }
                );

                return { success: true };
            } catch (error) {
                console.error('[SLIDEOUT] executePrompt() failed', {
                    promptId,
                    error: error.message || String(error),
                    errorStack: error.stack,
                    errorName: error.name,
                    timestamp: new Date().toISOString()
                });
                throw error;
            }
        },

        /**
         * Display all prompt results
         * @param {boolean} showLoading - Whether to show loading state (default: true)
         * @param {string} caller - Name of the calling function for debugging
         */
        async displayAllResults(showLoading = true, caller = 'unknown') {
            console.log('[SLIDEOUT] displayAllResults() called', {
                showLoading,
                caller,
                timestamp: new Date().toISOString(),
                stackTrace: new Error().stack
            });

            const content = this.slideout?.getContent();
            if (!content) {
                console.warn('[SLIDEOUT] displayAllResults() - No content element available');
                return;
            }

            // Don't show loading state if there are active streaming items - they're already visible
            const hasStreamingItems = content.querySelectorAll('[data-streaming-id]').length > 0;
            const activeStreamingCount = this.activeStreamingRequests.size;
            if (showLoading && !hasStreamingItems && activeStreamingCount === 0) {
                console.log('[SLIDEOUT] displayAllResults() - Showing loading state', { caller });
                UIRenderer.renderLoading(content, 'Loading execution history...');
            } else {
                console.log('[SLIDEOUT] displayAllResults() - Skipping loading state', { caller, hasStreamingItems, activeStreamingCount });
            }

            try {
                console.log('[SLIDEOUT] displayAllResults() - Fetching all actions', { caller });
                const allActions = await PromptAPI.getAllActions();
                console.log('[SLIDEOUT] displayAllResults() - Fetched actions', {
                    caller,
                    actionCount: allActions?.length || 0,
                    timestamp: new Date().toISOString()
                });
                
                state.set('allActions', allActions);

                console.log('[SLIDEOUT] displayAllResults() - Rendering actions', { caller });
                
                // Render results with handlers
                UIRenderer.renderActions(
                    content, 
                    allActions, 
                    async (actionId) => {
                        const success = await this.handleCopy(actionId);
                        if (success && window.PromptModalManager) {
                            window.PromptModalManager.showStatus('Copied to clipboard!', 'success');
                            setTimeout(() => window.PromptModalManager.hideStatus(), 2000);
                        }
                    },
                    async (actionId) => {
                        try {
                            await this.handleDelete(actionId);
                            // Refresh results after delete
                            await this.displayAllResults(true, 'handleDelete');
                            if (window.PromptModalManager) {
                                window.PromptModalManager.showStatus('Execution result deleted', 'success');
                                setTimeout(() => window.PromptModalManager.hideStatus(), 2000);
                            }
                        } catch (error) {
                            if (window.PromptModalManager) {
                                window.PromptModalManager.showStatus(error.message || 'Failed to delete execution result', 'error');
                            }
                            throw error;
                        }
                    }
                );

                console.log('[SLIDEOUT] displayAllResults() - Actions rendered', { caller });

                // Notify that results are updated (for filters)
                if (this.onResultsUpdate) {
                    console.log('[SLIDEOUT] displayAllResults() - Notifying results update', { caller });
                    this.onResultsUpdate(allActions);
                }

                console.log('[SLIDEOUT] displayAllResults() - Completed successfully', { caller });
            } catch (error) {
                console.error('[SLIDEOUT] displayAllResults() - Failed to load execution history', {
                    caller,
                    error: error.message || String(error),
                    errorStack: error.stack,
                    timestamp: new Date().toISOString()
                });
                UIRenderer.renderError(content, error.message || 'Failed to load execution history');
            }
        },

        /**
         * Handle chat submit
         */
        async handleChatSubmit() {
            console.log('[SLIDEOUT] handleChatSubmit() called', {
                timestamp: new Date().toISOString()
            });

            const promptId = state.get('slideoutPromptId');
            console.log('[SLIDEOUT] promptId from state:', promptId);

            if (!promptId) {
                console.warn('[SLIDEOUT] No promptId found in state, aborting');
                return;
            }

            const userMessage = this.elements.chatInput?.value.trim() || '';
            console.log('[SLIDEOUT] userMessage:', {
                message: userMessage.substring(0, 100) + (userMessage.length > 100 ? '...' : ''),
                length: userMessage.length,
                isEmpty: !userMessage
            });

            if (!userMessage) {
                console.warn('[SLIDEOUT] No user message provided, aborting');
                return;
            }

            // Disable send button and show loading
            if (this.elements.chatSend) {
                this.elements.chatSend.disabled = true;
                const sendIcon = document.getElementById('slideoutChatSendIcon');
                if (sendIcon) {
                    sendIcon.style.display = 'none';
                }
                this.elements.chatSend.innerHTML = '<div class="ai-loading-spinner" style="width: 16px; height: 16px; border-width: 2px;"></div>';
            }

            const content = this.slideout?.getContent();
            if (!content) {
                console.warn('[SLIDEOUT] No content element available');
                // Reset send button
                if (this.elements.chatSend) {
                    this.elements.chatSend.innerHTML = '<img src="/images/send%20icon.png" alt="Send" width="20" height="20" id="slideoutChatSendIcon">';
                    this.elements.chatSend.disabled = false;
                }
                return;
            }

            try {
                // Get prompt info for display
                let promptName = 'Unknown';
                let promptVersion = null;
                try {
                    const prompt = await PromptAPI.get(promptId);
                    promptName = prompt.name || 'Unknown';
                    promptVersion = prompt.version || null;
                } catch (e) {
                    console.warn('[SLIDEOUT] Failed to fetch prompt info:', e);
                }

                // Track this streaming request BEFORE creating the item
                // This ensures open() method won't call displayAllResults() and clear the container
                const streamingRequestId = `streaming-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
                this.activeStreamingRequests.add(streamingRequestId);

                // Create streaming result item
                const streamingItem = UIRenderer.createStreamingResultItem(
                    content,
                    promptName,
                    promptVersion,
                    userMessage
                );

                if (!streamingItem) {
                    // Remove from active requests if creation failed
                    this.activeStreamingRequests.delete(streamingRequestId);
                    throw new Error('Failed to create streaming result item');
                }

                // Attach idea card listeners immediately so they work during streaming
                // Event delegation means they'll work for idea cards added dynamically
                if (content && UIRenderer.attachIdeaCardListeners) {
                    UIRenderer.attachIdeaCardListeners(content);
                }

                // Clear the input immediately
                if (this.elements.chatInput) {
                    this.elements.chatInput.value = '';
                }

                console.log('[SLIDEOUT] Calling PromptAPI.executeStream()', {
                    promptId,
                    userMessageLength: userMessage.length,
                    timestamp: new Date().toISOString()
                });

                // Execute with streaming
                await PromptAPI.executeStream(
                    promptId,
                    userMessage,
                    // onChunk
                    (chunk) => {
                        // Only update UI if slideout is still open and element exists
                        if (this.slideout?.isOpen() && streamingItem && streamingItem.parentElement) {
                            UIRenderer.appendToStreamingItem(streamingItem, chunk);
                        }
                    },
                    // onDone
                    (metadata) => {
                        console.log('[SLIDEOUT] Streaming completed (handleChatSubmit)', {
                            promptId,
                            tokens_used: metadata.tokens_used,
                            model: metadata.model,
                            timestamp: new Date().toISOString()
                        });
                        
                        // Remove from active requests
                        this.activeStreamingRequests.delete(streamingRequestId);
                        
                        // Only update UI if slideout is still open and element exists
                        if (this.slideout?.isOpen() && streamingItem && streamingItem.parentElement) {
                            UIRenderer.finalizeStreamingItem(streamingItem, metadata);
                            
                            // Show done icon
                            if (this.elements.chatSend) {
                                // #region agent log
                                fetch('http://127.0.0.1:7242/ingest/0ea04ade-be37-4438-ba64-4de28c7d11e9',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'slideout.js:493',message:'Setting done_icon via innerHTML',data:{elementExists:!!this.elements.chatSend},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H2-race-condition'})}).catch(()=>{});
                                // #endregion agent log
                                this.elements.chatSend.innerHTML = '<img src="/images/done%20icon.png" alt="Done" width="20" height="20" id="slideoutChatSendIcon">';
                            }

                            // Reset to send icon after delay
                            setTimeout(() => {
                                if (this.elements.chatSend) {
                                    // #region agent log
                                    fetch('http://127.0.0.1:7242/ingest/0ea04ade-be37-4438-ba64-4de28c7d11e9',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'slideout.js:502',message:'Resetting to send_icon via innerHTML after delay',data:{delay:RESET_ICON_DELAY},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H2-race-condition'})}).catch(()=>{});
                                    // #endregion agent log
                                    this.elements.chatSend.innerHTML = '<img src="/images/send%20icon.png" alt="Send" width="20" height="20" id="slideoutChatSendIcon">';
                                    this.elements.chatSend.disabled = false;
                                }
                            }, RESET_ICON_DELAY);

                            // Refresh results to get the saved action (without showing loading state)
                            console.log('[SLIDEOUT] Scheduling displayAllResults() after streaming (handleChatSubmit)', {
                                delay: 500,
                                timestamp: new Date().toISOString()
                            });
                            setTimeout(() => {
                                console.log('[SLIDEOUT] Calling displayAllResults() after streaming timeout (handleChatSubmit)');
                                this.displayAllResults(false, 'handleChatSubmit-onDone');
                            }, REFRESH_DELAY_AFTER_STREAMING);
                        } else {
                            // Slideout was closed, but still refresh history if slideout is reopened
                            // The backend has already saved the action, so it will appear in history
                            console.log('[SLIDEOUT] Streaming completed but slideout is closed, action saved to history', {
                                promptId,
                                timestamp: new Date().toISOString()
                            });
                        }
                        
                        // Clear slideoutPromptId if no more active requests
                        if (this.activeStreamingRequests.size === 0) {
                            state.set('slideoutPromptId', null);
                        }
                    },
                    // onError
                    (error) => {
                        console.error('[SLIDEOUT] Streaming error', {
                            promptId,
                            error: error.message || String(error),
                            timestamp: new Date().toISOString()
                        });
                        
                        // Remove from active requests
                        this.activeStreamingRequests.delete(streamingRequestId);
                        
                        // Only update UI if slideout is still open and element exists
                        if (this.slideout?.isOpen() && streamingItem && streamingItem.parentElement) {
                            // Update the item to show error
                            const contentDiv = streamingItem.querySelector('.prompt-result-content');
                            if (contentDiv) {
                                contentDiv.textContent = `Error: ${error.message || 'Unknown error occurred'}`;
                            }
                            UIRenderer.finalizeStreamingItem(streamingItem, {});
                            
                            // Reset to send icon on error
                            if (this.elements.chatSend) {
                                this.elements.chatSend.innerHTML = '<img src="/images/send%20icon.png" alt="Send" width="20" height="20" id="slideoutChatSendIcon">';
                                this.elements.chatSend.disabled = false;
                            }
                        }
                        
                        // Clear slideoutPromptId if no more active requests
                        if (this.activeStreamingRequests.size === 0) {
                            state.set('slideoutPromptId', null);
                        }
                    }
                );
            } catch (error) {
                console.error('[SLIDEOUT] Prompt execution failed', {
                    promptId,
                    error: error.message || String(error),
                    errorStack: error.stack,
                    errorName: error.name,
                    timestamp: new Date().toISOString()
                });
                // Reset to send icon on error
                if (this.elements.chatSend) {
                    this.elements.chatSend.innerHTML = '<img src="/images/send%20icon.png" alt="Send" width="20" height="20" id="slideoutChatSendIcon">';
                    this.elements.chatSend.disabled = false;
                }
                throw error;
            }
        },

        /**
         * Handle copy button click
         * @param {string} actionId - Action ID
         */
        async handleCopy(actionId) {
            const content = this.slideout?.getContent();
            if (!content) return false;

            const outputItem = content.querySelector(`[data-action-id="${actionId}"]`);
            const contentDiv = outputItem?.querySelector('.prompt-result-content');
            
            if (contentDiv) {
                // Check WeakMap first for streaming items (avoids data attribute size limits)
                // Then fall back to data attribute for saved items, then textContent
                const streamingText = window.PromptUIRenderer?.getStreamingContent?.(contentDiv);
                const textToCopy = streamingText || contentDiv.dataset.rawText || contentDiv.textContent || contentDiv.innerText;
                try {
                    await navigator.clipboard.writeText(textToCopy);
                    return true;
                } catch (err) {
                    console.error('[SLIDEOUT] Failed to copy:', err);
                    return false;
                }
            }
            return false;
        },

        /**
         * Handle delete button click
         * @param {string} actionId - Action ID
         */
        async handleDelete(actionId) {
            if (!confirm('Are you sure you want to delete this execution result?')) {
                return false;
            }

            try {
                await PromptAPI.deleteAction(actionId);
                // Reload results
                await this.displayAllResults();
                return true;
            } catch (error) {
                console.error('[SLIDEOUT] Failed to delete action:', error);
                throw error;
            }
        },

        /**
         * Set prompt ID for chat
         * @param {number} promptId - Prompt ID
         */
        setPromptId(promptId) {
            state.set('slideoutPromptId', promptId);
        },

        /**
         * Setup to-top button functionality
         */
        setupToTopButton() {
            const content = this.slideout?.getContent();
            if (!content) return;

            let toTopButton = document.getElementById('slideoutToTopButton');
            
            // Create button if it doesn't exist
            if (!toTopButton) {
                toTopButton = document.createElement('button');
                toTopButton.id = 'slideoutToTopButton';
                toTopButton.className = 'slideout-to-top-btn';
                toTopButton.title = 'Scroll to top';
                toTopButton.style.display = 'none';
                toTopButton.innerHTML = '<img src="/images/arrow_up.png" alt="To top" width="24" height="24">';
                content.appendChild(toTopButton);
            }

            // Show/hide button based on scroll position
            const updateButtonVisibility = () => {
                const scrollTop = content.scrollTop;
                // Show button if scrolled down past threshold
                if (scrollTop > SCROLL_TO_TOP_THRESHOLD) {
                    toTopButton.style.display = 'flex';
                } else {
                    toTopButton.style.display = 'none';
                }
            };

            // Update visibility on scroll
            content.addEventListener('scroll', updateButtonVisibility, { passive: true });

            // Handle button click - scroll to top of first visible prompt-result-content
            toTopButton.addEventListener('click', () => {
                const promptResultContents = content.querySelectorAll('.prompt-result-content');
                
                // Find the first visible prompt-result-content element
                let firstVisible = null;
                for (const element of promptResultContents) {
                    const rect = element.getBoundingClientRect();
                    const containerRect = content.getBoundingClientRect();
                    
                    // Check if element is visible in the viewport
                    if (rect.top >= containerRect.top && rect.top <= containerRect.bottom) {
                        firstVisible = element;
                        break;
                    }
                }

                if (firstVisible) {
                    // Scroll to the first visible prompt-result-content
                    firstVisible.scrollIntoView({ behavior: 'smooth', block: 'start' });
                } else if (promptResultContents.length > 0) {
                    // If no visible element found, scroll to the first one
                    promptResultContents[0].scrollIntoView({ behavior: 'smooth', block: 'start' });
                } else {
                    // Fallback: scroll to top of content
                    content.scrollTo({ top: 0, behavior: 'smooth' });
                }
            });

            // Initial visibility check
            updateButtonVisibility();
        },

        /**
         * Setup expansion button functionality
         */
        setupExpandButton() {
            const expandButton = document.getElementById('slideoutExpandButton');
            if (!expandButton) return;

            expandButton.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent event bubbling
                this.handleExpandToggle();
            });
        },

        /**
         * Handle expand/collapse toggle
         */
        handleExpandToggle() {
            if (!this.slideout || !this.slideout.panel) return;

            const panel = this.slideout.panel;
            const overlay = this.slideout.overlay;
            const isExpanded = panel.classList.contains('expanded');

            // Close any open modals first (hide only, don't close slideout)
            if (window.PromptModalManager && window.PromptModalManager.promptModal && window.PromptModalManager.promptModal.isVisible()) {
                // Hide the modal directly without closing the slideout
                window.PromptModalManager.promptModal.hide();
            }

            if (isExpanded) {
                // Collapse to default width
                panel.classList.remove('expanded');
                if (overlay) {
                    overlay.style.width = SLIDEOUT_DEFAULT_WIDTH;
                }
            } else {
                // Expand to viewport width
                panel.classList.add('expanded');
                if (overlay) {
                    overlay.style.width = SLIDEOUT_EXPANDED_WIDTH;
                }
            }
        }
    };

    // Export
    window.PromptSlideoutManager = SlideoutManager;
})();

