/**
 * Prompt Engineering Main Entry Point
 * Coordinates all modules and initializes the page
 */

(function() {
    'use strict';

    // Wait for all dependencies to be loaded
    function waitForDependencies() {
        return new Promise((resolve) => {
            const checkDeps = () => {
                if (window.FounderAdmin && 
                    window.FounderAdminComponents && 
                    window.PromptEngineeringState &&
                    window.PromptAPI &&
                    window.PromptUIRenderer &&
                    window.PromptModalManager &&
                    window.PromptFilterManager &&
                    window.PromptSlideoutManager &&
                    window.PurposesManager) {
                    resolve();
                } else {
                    setTimeout(checkDeps, 50);
                }
            };
            checkDeps();
        });
    }

    /**
     * Main Application
     */
    const PromptEngineeringApp = {
        elements: null,
        modalManager: null,
        filterManager: null,
        slideoutManager: null,

        /**
         * Initialize application
         */
        async init() {
            await waitForDependencies();

            // Get all DOM elements
            this.elements = this.getElements();

            // Initialize authentication
            await this.initAuth();

            // Initialize managers
            this.initManagers();

            // Setup event listeners
            this.setupEventListeners();

            // Load initial data
            await this.loadInitialData();
        },

        /**
         * Get all DOM elements
         */
        getElements() {
            const { DOM } = window.FounderAdmin;
            return {
                appShell: DOM.getElement('appShell'),
                founderEmail: DOM.getElement('founderEmail'),
                logoutButton: DOM.getElement('logoutButton'),
                refreshButton: DOM.getElement('refreshButton'),
                newPromptButton: DOM.getElement('newPromptButton'),
                statusMessage: DOM.getElement('statusMessage'),
                promptsContainer: DOM.getElement('promptsContainer'),
                statusFilter: DOM.getElement('statusFilter'),
                purposeFilter: DOM.getElement('purposeFilter'),
                viewToggle: DOM.getElement('viewToggle', false),
                // Modal elements
                modalBackdrop: DOM.getElement('modalBackdrop'),
                modalTitle: DOM.getElement('modalTitle'),
                promptForm: DOM.getElement('promptForm'),
                nameInput: DOM.getElement('nameInput'),
                versionInput: DOM.getElement('versionInput'),
                promptTypeInput: DOM.getElement('promptTypeInput'),
                promptPurposeInput: DOM.getElement('promptPurposeInput'),
                statusInput: DOM.getElement('statusInput'),
                clientFacingInput: DOM.getElement('clientFacingInput'),
                allClientsGroup: DOM.getElement('allClientsGroup'),
                allClientsInput: DOM.getElement('allClientsInput'),
                clientSelectionGroup: DOM.getElement('clientSelectionGroup'),
                clientIdsContainer: DOM.getElement('clientIdsContainer'),
                contextMenuGroup: DOM.getElement('contextMenuGroup'),
                contextMenuGroupInput: DOM.getElement('contextMenuGroupInput'),
                addContextMenuGroupButton: DOM.getElement('addContextMenuGroupButton'),
                manageContextMenuGroupsButton: DOM.getElement('manageContextMenuGroupsButton'),
                addContextMenuGroupModal: DOM.getElement('addContextMenuGroupModal'),
                manageContextMenuGroupsModal: DOM.getElement('manageContextMenuGroupsModal'),
                addContextMenuGroupForm: DOM.getElement('addContextMenuGroupForm'),
                newContextMenuGroupInput: DOM.getElement('newContextMenuGroupInput'),
                cancelAddContextMenuGroupButton: DOM.getElement('cancelAddContextMenuGroupButton'),
                saveContextMenuGroupButton: DOM.getElement('saveContextMenuGroupButton'),
                contextMenuGroupsList: DOM.getElement('contextMenuGroupsList'),
                cancelManageContextMenuGroupsButton: DOM.getElement('cancelManageContextMenuGroupsButton'),
                llmModelInput: DOM.getElement('llmModelInput'),
                systemMessageInput: DOM.getElement('systemMessageInput'),
                promptMessageInput: DOM.getElement('promptMessageInput'),
                helperPromptSelect: DOM.getElement('helperPromptSelect'),
                userMessageInput: DOM.getElement('userMessageInput'),
                modalCloseButton: DOM.getElement('modalCloseButton'),
                addPurposeButton: DOM.getElement('addPurposeButton'),
                managePurposesButton: DOM.getElement('managePurposesButton'),
                addPurposeModal: DOM.getElement('addPurposeModal'),
                managePurposesModal: DOM.getElement('managePurposesModal'),
                versionHistoryModal: DOM.getElement('versionHistoryModal'),
                versionHistoryTitle: DOM.getElement('versionHistoryTitle'),
                versionHistoryList: DOM.getElement('versionHistoryList'),
                versionHistoryButton: DOM.getElement('versionHistoryButton'),
                closeVersionHistoryButton: DOM.getElement('closeVersionHistoryButton'),
                purposesList: DOM.getElement('purposesList'),
                newPurposeInput: DOM.getElement('newPurposeInput'),
                cancelAddPurposeButton: DOM.getElement('cancelAddPurposeButton'),
                cancelManagePurposesButton: DOM.getElement('cancelManagePurposesButton'),
                savePurposeButton: DOM.getElement('savePurposeButton'),
                saveAndRunButton: DOM.getElement('saveAndRunButton'),
                saveButtonDropdown: DOM.getElement('saveButtonDropdown'),
                saveButtonMenu: DOM.getElement('saveButtonMenu'),
                saveChangesButton: DOM.getElement('saveChangesButton'),
                newVersionButton: DOM.getElement('newVersionButton'),
                deletePromptButton: DOM.getElement('deletePromptButton'),
                // Slideout elements
                slideoutPanel: DOM.getElement('slideoutPanel'),
                slideoutOverlay: DOM.getElement('slideoutOverlay'),
                slideoutContent: DOM.getElement('slideoutContent'),
                slideoutTitle: DOM.getElement('slideoutTitle'),
                closeSlideoutPanel: DOM.getElement('closeSlideoutPanel'),
                slideoutChatInput: DOM.getElement('slideoutChatInput'),
                slideoutChatSend: DOM.getElement('slideoutChatSend'),
                // Filter elements
                promptFiltersBtn: DOM.getElement('promptFiltersBtn', false),
                promptFiltersDropdown: DOM.getElement('promptFiltersDropdown', false),
                promptFilterBadge: DOM.getElement('promptFilterBadge', false),
                clearAllPromptFilters: DOM.getElement('clearAllPromptFilters', false),
                promptNameFilters: DOM.getElement('promptNameFilters', false),
                promptVersionFilters: DOM.getElement('promptVersionFilters', false)
            };
        },

        /**
         * Initialize authentication
         */
        async initAuth() {
            const { AuthUtils } = window.FounderAdmin;
            const state = window.PromptEngineeringState;

            await AuthUtils.initializeAuth(
                (userInfo) => {
                    // On authenticated
                    state.set('founder', userInfo);
                    this.renderFounderInfo();
                    this.showAppShell();
                },
                () => {
                    // On unauthenticated
                    // Auth.showLogin() is called by AuthUtils
                }
            );

            AuthUtils.setupAuthListeners((userInfo) => {
                state.set('founder', userInfo);
                this.renderFounderInfo();
                this.showAppShell();
            });
        },

        /**
         * Initialize managers
         */
        initManagers() {
            const state = window.PromptEngineeringState;
            const { PromptModalManager, PromptFilterManager, PromptSlideoutManager } = window;

            // Initialize modal manager
            this.modalManager = PromptModalManager;
            this.modalManager.init(
                this.elements,
                () => this.loadPrompts(), // onPromptSaved
                async (promptId, userMessage) => { // onPromptExecuted
                    console.log('[APP] onPromptExecuted callback called', {
                        promptId,
                        userMessage: userMessage ? userMessage.substring(0, 100) + (userMessage.length > 100 ? '...' : '') : 'empty',
                        userMessageLength: userMessage ? userMessage.length : 0,
                        timestamp: new Date().toISOString()
                    });

                    console.log('[APP] Loading prompts...');
                    await this.loadPrompts();
                    console.log('[APP] Prompts loaded');

                    if (this.slideoutManager) {
                        console.log('[APP] Setting slideout prompt ID and opening...', { promptId });
                        this.slideoutManager.setPromptId(promptId);
                        this.slideoutManager.open('LLM Outputs');
                        
                        // Execute the prompt (userMessage can be empty - system message alone is valid)
                        console.log('[APP] Executing prompt...', {
                            promptId,
                            userMessage: userMessage ? userMessage.substring(0, 100) + (userMessage.length > 100 ? '...' : '') : 'empty',
                            userMessageLength: userMessage ? userMessage.length : 0
                        });
                        try {
                            // Pass userMessage even if empty - the backend can handle it
                            // Note: executePrompt() now uses streaming and will call displayAllResults() itself
                            await this.slideoutManager.executePrompt(userMessage || '');
                            console.log('[APP] Prompt execution completed (streaming will refresh results automatically)');
                        } catch (error) {
                            console.error('[APP] Prompt execution failed in callback', {
                                promptId,
                                error: error.message || String(error),
                                errorResponse: error.response || error.data || 'no response data',
                                timestamp: new Date().toISOString()
                            });
                            // Still show existing results even if execution fails
                            console.log('[APP] Displaying all results after error...');
                            await this.slideoutManager.displayAllResults(true, 'main-onPromptExecuted-error');
                            console.log('[APP] Results displayed after error');
                        }
                        
                        // Note: We no longer call displayAllResults() here because executePrompt() 
                        // uses streaming and will refresh results automatically after streaming completes
                        // This prevents the double flash of the loading state
                        console.log('[APP] Skipping displayAllResults() call - streaming will handle refresh');
                        
                        // Refresh filters after displaying results
                        if (this.filterManager) {
                            console.log('[APP] Refreshing filters...');
                            this.filterManager.refreshFilters();
                        }
                    } else {
                        console.warn('[APP] slideoutManager not available');
                    }

                    console.log('[APP] onPromptExecuted callback completed');
                }
            );

            // Initialize slideout manager
            this.slideoutManager = PromptSlideoutManager;
            this.slideoutManager.init(
                'slideoutPanel',
                'slideoutOverlay',
                {
                    chatInput: this.elements.slideoutChatInput,
                    chatSend: this.elements.slideoutChatSend
                },
                (actions) => {
                    // onResultsUpdate - rebuild filters
                    if (this.filterManager && actions) {
                        this.filterManager.buildFilterUI(actions);
                    }
                }
            );

            // Initialize filter manager
            if (this.elements.promptFiltersBtn && this.elements.promptFiltersDropdown) {
                this.filterManager = PromptFilterManager;
                this.filterManager.init(
                    {
                        filterButton: this.elements.promptFiltersBtn,
                        filterDropdown: this.elements.promptFiltersDropdown,
                        badge: this.elements.promptFilterBadge,
                        clearAllButton: this.elements.clearAllPromptFilters
                    },
                    () => {
                        // onFilterChange - re-render results
                        const allActions = state.get('allActions');
                        if (allActions && this.slideoutManager) {
                            const content = this.slideoutManager.slideout?.getContent();
                            if (content) {
                                window.PromptUIRenderer.renderActions(
                                    content,
                                    allActions,
                                    (actionId) => this.slideoutManager.handleCopy(actionId),
                                    (actionId) => this.slideoutManager.handleDelete(actionId)
                                );
                            }
                        }
                    }
                );
            }
        },

        /**
         * Setup event listeners
         */
        setupEventListeners() {
            // Refresh button
            if (this.elements.refreshButton) {
                this.elements.refreshButton.addEventListener('click', () => {
                    this.loadInitialData();
                });
            }

            // New prompt button
            if (this.elements.newPromptButton) {
                this.elements.newPromptButton.addEventListener('click', () => {
                    this.modalManager.openPromptModal('create');
                });
            }

            // View toggle
            if (this.elements.viewToggle) {
                this.elements.viewToggle.addEventListener('click', (e) => {
                    const btn = e.target.closest('.view-toggle-btn');
                    if (!btn) return;

                    const view = btn.getAttribute('data-view');
                    if (!view) return;

                    // Update state
                    const state = window.PromptEngineeringState;
                    state.set('viewMode', view);

                    // Update active button
                    this.elements.viewToggle.querySelectorAll('.view-toggle-btn').forEach(b => {
                        b.classList.toggle('active', b.getAttribute('data-view') === view);
                    });

                    // Re-render prompts in new view
                    this.renderPromptsList();
                });
            }

            // Filter dropdowns with debouncing
            const { debounce } = window.FounderAdmin;
            const debouncedLoadPrompts = debounce(() => {
                this.loadPrompts();
            }, 300);

            if (this.elements.statusFilter) {
                this.elements.statusFilter.addEventListener('change', debouncedLoadPrompts);
            }

            if (this.elements.purposeFilter) {
                this.elements.purposeFilter.addEventListener('change', debouncedLoadPrompts);
            }

            // Logout button
            if (this.elements.logoutButton) {
                this.elements.logoutButton.addEventListener('click', () => {
                    Auth.handleLogout();
                });
            }

            // Note: Edit button listeners are attached in UIRenderer.renderPrompts
        },

        /**
         * Show app shell
         */
        showAppShell() {
            if (this.elements.appShell) {
                this.elements.appShell.style.display = 'flex';
            }
            Auth.hideLogin();
        },

        /**
         * Render founder info
         */
        renderFounderInfo() {
            const state = window.PromptEngineeringState;
            const founder = state.get('founder');
            if (this.elements.founderEmail && founder?.email) {
                this.elements.founderEmail.textContent = founder.email;
            }
        },

        /**
         * Load initial data
         */
        async loadInitialData() {
            this.modalManager.showStatus('Loading prompts…', 'success');
            try {
                await this.loadPrompts();
                this.modalManager.hideStatus();
            } catch (error) {
                console.error('[APP] Failed to load initial data:', error);
                this.modalManager.showStatus(error.message || 'Unable to load data.', 'error');
            }
        },

        /**
         * Load prompts
         */
        async loadPrompts() {
            const state = window.PromptEngineeringState;
            const PromptAPI = window.PromptAPI;

            const statusFilter = this.elements.statusFilter?.value || '';
            const purposeFilter = this.elements.purposeFilter?.value || '';

            state.set('statusFilter', statusFilter);
            state.set('purposeFilter', purposeFilter);

            const filters = {};
            if (statusFilter) filters.status = statusFilter;
            if (purposeFilter) filters.prompt_purpose = purposeFilter;

            try {
                const prompts = await PromptAPI.list(filters, true);
                state.set('prompts', prompts);

                // Render prompts list
                this.renderPromptsList();

                // Update purpose filter dropdown with new purposes from prompts
                this.updatePurposeFilter();

                // Refresh slideout filters if slideout is open
                if (this.filterManager && this.slideoutManager && this.slideoutManager.slideout?.isOpen()) {
                    this.filterManager.refreshFilters();
                }
            } catch (error) {
                console.error('[APP] Failed to load prompts:', error);
                throw error;
            }
        },

        /**
         * Render prompts list (card or table view)
         */
        renderPromptsList() {
            const UIRenderer = window.PromptUIRenderer;
            const state = window.PromptEngineeringState;
            const prompts = state.get('prompts');

            if (!this.elements.promptsContainer) return;

            UIRenderer.renderPrompts(
                this.elements.promptsContainer,
                (promptId) => {
                    this.modalManager.openPromptModal('edit', promptId);
                    // Open slideout with results after modal opens
                    setTimeout(async () => {
                        if (this.slideoutManager) {
                            // Find the prompt to get its name and version for filtering
                            const prompt = prompts.find(p => p.id === promptId);
                            
                            // Auto-apply filters for this prompt before opening slideout
                            if (this.filterManager && prompt) {
                                this.filterManager.applyPromptFilter(prompt.name, prompt.version);
                            }
                            
                            this.slideoutManager.setPromptId(promptId);
                            this.slideoutManager.open('LLM Outputs');
                            console.log('[APP] Displaying all results when opening slideout from prompt list');
                            await this.slideoutManager.displayAllResults(true, 'main-onEditClick');
                        }
                    }, 50);
                },
                (promptId) => {
                    this.modalManager.openPromptModal('edit', promptId);
                }
            );
        },

        /**
         * Update purpose filter dropdown
         */
        updatePurposeFilter() {
            if (!this.elements.purposeFilter) return;

            const state = window.PromptEngineeringState;
            const prompts = state.get('prompts');
            const uniquePurposes = [...new Set(prompts.map(p => p.prompt_purpose))].sort();

            // Remove all options except "All Purposes"
            Array.from(this.elements.purposeFilter.options).forEach(option => {
                if (option.value !== '') {
                    option.remove();
                }
            });

            // Add purposes from prompts
            uniquePurposes.forEach(purpose => {
                const existingOptions = Array.from(this.elements.purposeFilter.options).map(opt => opt.value);
                if (!existingOptions.includes(purpose)) {
                    const option = document.createElement('option');
                    option.value = purpose;
                    option.textContent = window.PurposesManager.getDisplayName(purpose);
                    this.elements.purposeFilter.appendChild(option);
                }
            });
        }
    };

    // Export for debugging
    window.PromptEngineeringApp = PromptEngineeringApp;

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            PromptEngineeringApp.init();
        });
    } else {
        PromptEngineeringApp.init();
    }
})();

