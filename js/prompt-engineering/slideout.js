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
         * Display all prompt results
         */
        async displayAllResults() {
            const content = this.slideout?.getContent();
            if (!content) return;

            UIRenderer.renderLoading(content, 'Loading execution history...');

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
                UIRenderer.renderError(content, error.message || 'Failed to load execution history');
            }
        },

        /**
         * Handle chat submit
         */
        async handleChatSubmit() {
            const promptId = state.get('slideoutPromptId');
            if (!promptId) {
                return;
            }

            const userMessage = this.elements.chatInput?.value.trim();
            if (!userMessage) {
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

            try {
                // Execute the prompt
                await PromptAPI.execute(promptId, userMessage);

                // Clear the input
                if (this.elements.chatInput) {
                    this.elements.chatInput.value = '';
                }

                // Refresh results
                await this.displayAllResults();

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
            } catch (error) {
                console.error('[SLIDEOUT] Prompt execution failed:', error);
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

