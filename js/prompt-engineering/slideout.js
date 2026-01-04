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

    /**
     * Slideout Manager
     */
    const SlideoutManager = {
        slideout: null,
        elements: null,
        onResultsUpdate: null,

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
        },

        /**
         * Open slideout with title
         * @param {string} title - Slideout title
         */
        open(title = 'LLM Outputs') {
            if (this.slideout) {
                this.slideout.open(title);
            }
        },

        /**
         * Close slideout
         */
        close() {
            if (this.slideout) {
                this.slideout.close();
            }
            if (this.elements.chatInput) {
                this.elements.chatInput.value = '';
            }
            state.set('slideoutPromptId', null);
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

                // Create streaming result item
                const streamingItem = UIRenderer.createStreamingResultItem(
                    content,
                    promptName,
                    promptVersion,
                    userMessage
                );

                if (!streamingItem) {
                    throw new Error('Failed to create streaming result item');
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
                        UIRenderer.appendToStreamingItem(streamingItem, chunk);
                    },
                    // onDone
                    (metadata) => {
                        console.log('[SLIDEOUT] Streaming completed', {
                            promptId,
                            tokens_used: metadata.tokens_used,
                            model: metadata.model,
                            timestamp: new Date().toISOString()
                        });
                        UIRenderer.finalizeStreamingItem(streamingItem, metadata);
                        
                        // Refresh results silently to get the saved action (no loading flash)
                        setTimeout(() => {
                            this.displayAllResults(false);
                        }, 500);
                    },
                    // onError
                    (error) => {
                        console.error('[SLIDEOUT] Streaming error', {
                            promptId,
                            error: error.message || String(error),
                            timestamp: new Date().toISOString()
                        });
                        
                        // Update the item to show error
                        const contentDiv = streamingItem.querySelector('.prompt-result-content');
                        if (contentDiv) {
                            contentDiv.textContent = `Error: ${error.message || 'Unknown error occurred'}`;
                        }
                        UIRenderer.finalizeStreamingItem(streamingItem, {});
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
         */
        async displayAllResults(showLoading = true) {
            const content = this.slideout?.getContent();
            if (!content) return;

            if (showLoading) {
                UIRenderer.renderLoading(content, 'Loading execution history...');
            }

            try {
                const allActions = await PromptAPI.getAllActions();
                state.set('allActions', allActions);

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
                            await this.displayAllResults();
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

                // Notify that results are updated (for filters)
                if (this.onResultsUpdate) {
                    this.onResultsUpdate(allActions);
                }
            } catch (error) {
                console.error('[SLIDEOUT] Failed to load execution history:', error);
                if (showLoading) {
                    UIRenderer.renderError(content, error.message || 'Failed to load execution history');
                }
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
                    this.elements.chatSend.innerHTML = '<img src="https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/icons/send_icon.png" alt="Send" width="20" height="20" id="slideoutChatSendIcon">';
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

                // Create streaming result item
                const streamingItem = UIRenderer.createStreamingResultItem(
                    content,
                    promptName,
                    promptVersion,
                    userMessage
                );

                if (!streamingItem) {
                    throw new Error('Failed to create streaming result item');
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
                        UIRenderer.appendToStreamingItem(streamingItem, chunk);
                    },
                    // onDone
                    (metadata) => {
                        console.log('[SLIDEOUT] Streaming completed', {
                            promptId,
                            tokens_used: metadata.tokens_used,
                            model: metadata.model,
                            timestamp: new Date().toISOString()
                        });
                        UIRenderer.finalizeStreamingItem(streamingItem, metadata);
                        
                        // Show done icon
                        if (this.elements.chatSend) {
                            this.elements.chatSend.innerHTML = '<img src="https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/icons/done_icon.png" alt="Done" width="20" height="20" id="slideoutChatSendIcon">';
                        }

                        // Reset to send icon after 2 seconds
                        setTimeout(() => {
                            if (this.elements.chatSend) {
                                this.elements.chatSend.innerHTML = '<img src="https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/icons/send_icon.png" alt="Send" width="20" height="20" id="slideoutChatSendIcon">';
                                this.elements.chatSend.disabled = false;
                            }
                        }, 2000);

                        // Refresh results silently to get the saved action (no loading flash)
                        setTimeout(() => {
                            this.displayAllResults(false);
                        }, 500);
                    },
                    // onError
                    (error) => {
                        console.error('[SLIDEOUT] Streaming error', {
                            promptId,
                            error: error.message || String(error),
                            timestamp: new Date().toISOString()
                        });
                        
                        // Update the item to show error
                        const contentDiv = streamingItem.querySelector('.prompt-result-content');
                        if (contentDiv) {
                            contentDiv.textContent = `Error: ${error.message || 'Unknown error occurred'}`;
                        }
                        UIRenderer.finalizeStreamingItem(streamingItem, {});
                        
                        // Reset to send icon on error
                        if (this.elements.chatSend) {
                            this.elements.chatSend.innerHTML = '<img src="https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/icons/send_icon.png" alt="Send" width="20" height="20" id="slideoutChatSendIcon">';
                            this.elements.chatSend.disabled = false;
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
                    this.elements.chatSend.innerHTML = '<img src="https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/icons/send_icon.png" alt="Send" width="20" height="20" id="slideoutChatSendIcon">';
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
                const textToCopy = contentDiv.textContent || contentDiv.innerText;
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
        }
    };

    // Export
    window.PromptSlideoutManager = SlideoutManager;
})();

