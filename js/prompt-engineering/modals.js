/**
 * Prompt Engineering Modals
 * Manages prompt modal and purpose modals
 */

(function() {
    'use strict';

    if (!window.FounderAdmin || !window.FounderAdminComponents || !window.PromptEngineeringState || 
        !window.PromptAPI || !window.PurposesManager) {
        console.error('[PROMPT_MODALS] Dependencies not loaded');
        return;
    }

    const { Modal, StatusMessage } = window.FounderAdminComponents;
    const state = window.PromptEngineeringState;
    const PromptAPI = window.PromptAPI;
    const PurposesManager = window.PurposesManager;
    const { DOM } = window.FounderAdmin;

    /**
     * Modal Manager
     */
    const ModalManager = {
        promptModal: null,
        addPurposeModal: null,
        managePurposesModal: null,
        statusMessage: null,
        elements: null,
        onPromptSaved: null,
        onPromptExecuted: null,

        /**
         * Initialize modal manager
         * @param {Object} elements - Modal UI elements
         * @param {Function} onPromptSaved - Callback when prompt is saved
         * @param {Function} onPromptExecuted - Callback when prompt is executed
         */
        init(elements, onPromptSaved, onPromptExecuted) {
            this.elements = elements;
            this.onPromptSaved = onPromptSaved;
            this.onPromptExecuted = onPromptExecuted;

            // Create modal components
            if (elements.modalBackdrop) {
                this.promptModal = new Modal('modalBackdrop', {
                    closeOnBackdropClick: true,
                    closeOnEscape: true
                });
            }

            if (elements.addPurposeModal) {
                this.addPurposeModal = new Modal('addPurposeModal', {
                    closeOnBackdropClick: true,
                    closeOnEscape: true
                });
            }

            if (elements.managePurposesModal) {
                this.managePurposesModal = new Modal('managePurposesModal', {
                    closeOnBackdropClick: true,
                    closeOnEscape: true
                });
            }

            // Status message
            if (elements.statusMessage) {
                this.statusMessage = new StatusMessage('statusMessage');
            }

            // Setup event listeners
            this.setupEventListeners();
        },

        /**
         * Setup event listeners for modals
         */
        setupEventListeners() {
            // Prompt form submission
            if (this.elements.promptForm) {
                this.elements.promptForm.addEventListener('submit', (e) => {
                    e.preventDefault();
                    this.handlePromptFormSubmit();
                });
            }

            // Save buttons
            if (this.elements.saveAndRunButton) {
                this.elements.saveAndRunButton.addEventListener('click', async (e) => {
                    e.preventDefault();
                    state.set('actionMode', 'save-and-run');
                    // Validate form first
                    if (this.elements.promptForm && this.elements.promptForm.checkValidity()) {
                        await this.handlePromptFormSubmit();
                    } else if (this.elements.promptForm) {
                        // Trigger HTML5 validation display
                        this.elements.promptForm.reportValidity();
                    }
                });
            }

            if (this.elements.saveChangesButton) {
                this.elements.saveChangesButton.addEventListener('click', async (e) => {
                    e.preventDefault();
                    state.set('actionMode', 'save-only');
                    // Validate form first
                    if (this.elements.promptForm && this.elements.promptForm.checkValidity()) {
                        await this.handlePromptFormSubmit();
                    } else if (this.elements.promptForm) {
                        // Trigger HTML5 validation display
                        this.elements.promptForm.reportValidity();
                    }
                });
            }

            // Split button dropdown
            if (this.elements.saveButtonDropdown && this.elements.saveButtonMenu) {
                this.elements.saveButtonDropdown.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.elements.saveButtonMenu.classList.toggle('visible');
                });

                // Close dropdown on outside click
                document.addEventListener('click', (e) => {
                    if (!this.elements.saveButtonDropdown.contains(e.target) && 
                        !this.elements.saveButtonMenu.contains(e.target)) {
                        this.elements.saveButtonMenu.classList.remove('visible');
                    }
                });
            }

            // Modal close button
            if (this.elements.modalCloseButton) {
                this.elements.modalCloseButton.addEventListener('click', () => {
                    this.closePromptModal();
                });
            }

            // New version button
            if (this.elements.newVersionButton) {
                this.elements.newVersionButton.addEventListener('click', () => {
                    this.createNewVersion();
                });
            }

            // Delete prompt button
            if (this.elements.deletePromptButton) {
                this.elements.deletePromptButton.addEventListener('click', () => {
                    this.handleDeletePrompt();
                });
            }

            // Purpose modals
            if (this.elements.addPurposeButton) {
                this.elements.addPurposeButton.addEventListener('click', () => {
                    this.openAddPurposeModal();
                });
            }

            if (this.elements.managePurposesButton) {
                this.elements.managePurposesButton.addEventListener('click', () => {
                    this.openManagePurposesModal();
                });
            }

            if (this.elements.cancelAddPurposeButton) {
                this.elements.cancelAddPurposeButton.addEventListener('click', () => {
                    this.closeAddPurposeModal();
                });
            }

            if (this.elements.cancelManagePurposesButton) {
                this.elements.cancelManagePurposesButton.addEventListener('click', () => {
                    this.closeManagePurposesModal();
                });
            }

            if (this.elements.savePurposeButton) {
                this.elements.savePurposeButton.addEventListener('click', () => {
                    this.handleAddPurpose();
                });
            }

            // Enter key for add purpose
            if (this.elements.newPurposeInput) {
                this.elements.newPurposeInput.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        this.handleAddPurpose();
                    }
                });
            }
        },

        /**
         * Open prompt modal
         * @param {string} mode - 'create' or 'edit'
         * @param {number} promptId - Prompt ID (for edit mode)
         */
        openPromptModal(mode, promptId = null) {
            state.set('currentMode', mode);
            state.set('currentPromptId', promptId);

            if (this.elements.promptForm) {
                this.elements.promptForm.reset();
            }

            // Get prompts to include their purposes in dropdown
            const prompts = state.get('prompts') || [];

            // Reload custom purposes (include purposes from existing prompts)
            if (this.elements.promptPurposeInput) {
                PurposesManager.populateSelect(this.elements.promptPurposeInput, true, prompts);
            }

            if (mode === 'edit' && promptId) {
                const prompt = prompts.find((item) => item.id === promptId);
                
                if (!prompt) {
                    this.showStatus('Selected prompt could not be found.', 'error');
                    return;
                }

                if (this.elements.modalTitle) {
                    this.elements.modalTitle.textContent = `Edit ${prompt.name} (v${prompt.version})`;
                }

                // Populate form
                if (this.elements.nameInput) this.elements.nameInput.value = prompt.name;
                if (this.elements.versionInput) this.elements.versionInput.value = prompt.version;
                if (this.elements.promptPurposeInput) this.elements.promptPurposeInput.value = prompt.prompt_purpose;
                if (this.elements.statusInput) this.elements.statusInput.value = prompt.status;
                if (this.elements.llmModelInput) this.elements.llmModelInput.value = prompt.llm_model;
                if (this.elements.systemMessageInput) this.elements.systemMessageInput.value = prompt.system_message;
                if (this.elements.userMessageInput) this.elements.userMessageInput.value = '';

                // Show "New Version" button
                if (this.elements.newVersionButton) {
                    this.elements.newVersionButton.style.display = 'block';
                }

                // Show delete button
                if (this.elements.deletePromptButton) {
                    this.elements.deletePromptButton.style.display = 'inline-flex';
                }

                // Set prompt ID for slideout
                state.set('slideoutPromptId', promptId);
            } else {
                if (this.elements.modalTitle) {
                    this.elements.modalTitle.textContent = 'New Prompt';
                }

                // Set default values
                if (this.elements.nameInput) this.elements.nameInput.value = '';
                if (this.elements.versionInput) this.elements.versionInput.value = '1';
                if (this.elements.promptPurposeInput) this.elements.promptPurposeInput.value = '';
                if (this.elements.statusInput) this.elements.statusInput.value = 'test';
                if (this.elements.llmModelInput) this.elements.llmModelInput.value = 'gpt-4o-mini';
                if (this.elements.systemMessageInput) this.elements.systemMessageInput.value = '';
                if (this.elements.userMessageInput) this.elements.userMessageInput.value = '';

                // Hide "New Version" button
                if (this.elements.newVersionButton) {
                    this.elements.newVersionButton.style.display = 'none';
                }

                // Hide delete button
                if (this.elements.deletePromptButton) {
                    this.elements.deletePromptButton.style.display = 'none';
                }
            }

            if (this.promptModal) {
                this.promptModal.show();
            }

            state.set('actionMode', 'save-and-run');
            
            // If editing, open slideout with results and apply filters
            if (mode === 'edit' && promptId && window.PromptSlideoutManager) {
                setTimeout(async () => {
                    const slideoutManager = window.PromptSlideoutManager;
                    slideoutManager.setPromptId(promptId);
                    
                    // Auto-apply filters for this prompt before opening slideout
                    if (window.PromptFilterManager && prompt) {
                        window.PromptFilterManager.applyPromptFilter(prompt.name, prompt.version);
                    }
                    
                    slideoutManager.open('LLM Outputs');
                    console.log('[MODAL] Displaying all results when opening slideout from modal');
                    await slideoutManager.displayAllResults(true, 'modals-openPromptModal');
                }, 50);
            }
            
            // Focus on name input
            setTimeout(() => {
                if (this.elements.nameInput) {
                    this.elements.nameInput.focus();
                }
            }, 50);
        },

        /**
         * Close prompt modal
         */
        closePromptModal() {
            state.set('currentMode', 'create');
            state.set('currentPromptId', null);
            
            if (this.promptModal) {
                this.promptModal.hide();
            }

            if (this.elements.newVersionButton) {
                this.elements.newVersionButton.style.display = 'none';
            }

            if (this.elements.deletePromptButton) {
                this.elements.deletePromptButton.style.display = 'none';
            }

            // Close slideout if open
            if (window.PromptSlideoutManager) {
                window.PromptSlideoutManager.close();
            }
        },

        /**
         * Create new version from current prompt
         */
        createNewVersion() {
            const currentPromptId = state.get('currentPromptId');
            if (!currentPromptId) {
                this.showStatus('No prompt selected to create version from.', 'error');
                return;
            }

            const prompts = state.get('prompts');
            const currentPrompt = prompts.find((item) => item.id === currentPromptId);
            
            if (!currentPrompt) {
                this.showStatus('Current prompt could not be found.', 'error');
                return;
            }

            // Find the highest version for this prompt name
            const sameNamePrompts = prompts.filter(p => p.name === currentPrompt.name);
            const maxVersion = Math.max(...sameNamePrompts.map(p => p.version));
            const newVersion = maxVersion + 1;

            // Pre-fill form
            if (this.elements.modalTitle) {
                this.elements.modalTitle.textContent = `New Version: ${currentPrompt.name} (v${newVersion})`;
            }
            if (this.elements.nameInput) this.elements.nameInput.value = currentPrompt.name;
            if (this.elements.versionInput) this.elements.versionInput.value = newVersion;
            if (this.elements.promptPurposeInput) this.elements.promptPurposeInput.value = currentPrompt.prompt_purpose;
            if (this.elements.statusInput) this.elements.statusInput.value = 'test';
            if (this.elements.llmModelInput) this.elements.llmModelInput.value = currentPrompt.llm_model;
            if (this.elements.systemMessageInput) this.elements.systemMessageInput.value = currentPrompt.system_message;
            if (this.elements.userMessageInput) this.elements.userMessageInput.value = '';

            // Change mode to create
            state.set('currentMode', 'create');
            state.set('currentPromptId', null);

            // Hide "New Version" button
            if (this.elements.newVersionButton) {
                this.elements.newVersionButton.style.display = 'none';
            }

            // Hide delete button
            if (this.elements.deletePromptButton) {
                this.elements.deletePromptButton.style.display = 'none';
            }
        },

        /**
         * Handle delete prompt
         */
        async handleDeletePrompt() {
            const currentPromptId = state.get('currentPromptId');
            if (!currentPromptId) {
                this.showStatus('No prompt selected to delete.', 'error');
                return;
            }

            const prompts = state.get('prompts') || [];
            const prompt = prompts.find((item) => item.id === currentPromptId);
            
            if (!prompt) {
                this.showStatus('Prompt could not be found.', 'error');
                return;
            }

            const confirmMessage = `Are you sure you want to delete "${prompt.name}" (v${prompt.version})?\n\nThis action cannot be undone.`;
            if (!confirm(confirmMessage)) {
                return;
            }

            try {
                // Delete the prompt
                await PromptAPI.delete(currentPromptId);
                
                // Close the modal (this also closes the slideout)
                this.closePromptModal();
                
                // Refresh prompts list to remove the deleted card
                if (this.onPromptSaved) {
                    await this.onPromptSaved();
                }
                
                // Show success message on main page
                this.showStatus('Prompt deleted successfully.', 'success');
                setTimeout(() => this.hideStatus(), 2000);
            } catch (error) {
                console.error('[MODALS] Prompt delete failed:', error);
                this.showStatus(error.message || 'Unable to delete prompt.', 'error');
            }
        },

        /**
         * Handle prompt form submission
         */
        async handlePromptFormSubmit() {
            const actionMode = state.get('actionMode');
            const shouldExecute = actionMode === 'save-and-run';
            await this.savePrompt(shouldExecute);
        },

        /**
         * Save prompt
         * @param {boolean} shouldExecute - Whether to execute after saving
         */
        async savePrompt(shouldExecute = false) {
            if (this.elements.saveAndRunButton) {
                this.elements.saveAndRunButton.disabled = true;
            }
            if (this.elements.saveChangesButton) {
                this.elements.saveChangesButton.disabled = true;
            }

            // Get form values
            const nameValue = this.elements.nameInput?.value.trim() || '';
            const versionValue = parseInt(this.elements.versionInput?.value || '1');
            const promptPurposeValue = this.elements.promptPurposeInput?.value || '';
            const statusValue = this.elements.statusInput?.value || 'test';
            const llmModelValue = this.elements.llmModelInput?.value.trim() || '';
            const systemMessageValue = this.elements.systemMessageInput?.value.trim() || '';

            // Validation
            if (!nameValue || !promptPurposeValue || !systemMessageValue || !llmModelValue) {
                this.showStatus('All required fields must be filled.', 'error');
                this.enableSaveButtons();
                return;
            }

            if (isNaN(versionValue) || versionValue < 1) {
                this.showStatus('Version must be a positive integer.', 'error');
                this.enableSaveButtons();
                return;
            }

            const payload = {
                name: nameValue,
                version: versionValue,
                prompt_purpose: promptPurposeValue,
                status: statusValue,
                llm_model: llmModelValue,
                system_message: systemMessageValue,
            };

            try {
                const currentMode = state.get('currentMode');
                const currentPromptId = state.get('currentPromptId');
                let savedPrompt;

                if (currentMode === 'edit' && currentPromptId) {
                    savedPrompt = await PromptAPI.update(currentPromptId, payload);
                    this.showStatus('Prompt updated successfully.', 'success');
                } else {
                    savedPrompt = await PromptAPI.create(payload);
                    this.showStatus('Prompt created successfully.', 'success');
                }

                if (shouldExecute) {
                    const userMessage = this.elements.userMessageInput?.value.trim() || '';
                    console.log('[MODALS] Prompt saved, executing...', {
                        promptId: savedPrompt.id,
                        promptName: savedPrompt.name,
                        userMessage: userMessage.substring(0, 100) + (userMessage.length > 100 ? '...' : ''),
                        userMessageLength: userMessage.length,
                        timestamp: new Date().toISOString()
                    });

                    if (this.onPromptSaved) {
                        console.log('[MODALS] Calling onPromptSaved callback...');
                        await this.onPromptSaved();
                        console.log('[MODALS] onPromptSaved callback completed');
                    }
                    if (this.onPromptExecuted) {
                        console.log('[MODALS] Calling onPromptExecuted callback...', {
                            promptId: savedPrompt.id,
                            userMessageLength: userMessage.length
                        });
                        await this.onPromptExecuted(savedPrompt.id, userMessage);
                        console.log('[MODALS] onPromptExecuted callback completed');
                    }
                } else {
                    this.closePromptModal();
                    if (this.onPromptSaved) {
                        await this.onPromptSaved();
                    }
                }
            } catch (error) {
                console.error('[MODALS] Prompt save failed:', error);
                this.showStatus(error.message || 'Unable to save prompt.', 'error');
            } finally {
                this.enableSaveButtons();
            }
        },

        /**
         * Enable save buttons
         */
        enableSaveButtons() {
            if (this.elements.saveAndRunButton) {
                this.elements.saveAndRunButton.disabled = false;
            }
            if (this.elements.saveChangesButton) {
                this.elements.saveChangesButton.disabled = false;
            }
        },

        /**
         * Open add purpose modal
         */
        openAddPurposeModal() {
            if (this.elements.newPurposeInput) {
                this.elements.newPurposeInput.value = '';
            }
            if (this.addPurposeModal) {
                this.addPurposeModal.show();
            }
            setTimeout(() => {
                if (this.elements.newPurposeInput) {
                    this.elements.newPurposeInput.focus();
                }
            }, 50);
        },

        /**
         * Close add purpose modal
         */
        closeAddPurposeModal() {
            if (this.addPurposeModal) {
                this.addPurposeModal.hide();
            }
            if (this.elements.newPurposeInput) {
                this.elements.newPurposeInput.value = '';
            }
        },

        /**
         * Handle add purpose
         */
        handleAddPurpose() {
            const newPurpose = this.elements.newPurposeInput?.value.trim();
            if (!newPurpose) {
                this.showStatus('Please enter a purpose name.', 'error');
                return;
            }

            const normalizedPurpose = PurposesManager.addPurpose(newPurpose);
            if (normalizedPurpose) {
                // Update dropdowns
                if (this.elements.promptPurposeInput) {
                    const prompts = state.get('prompts') || [];
                    PurposesManager.populateSelect(this.elements.promptPurposeInput, true, prompts);
                    this.elements.promptPurposeInput.value = normalizedPurpose;
                }

                this.closeAddPurposeModal();

                // If manage modal is open, refresh the list
                if (this.managePurposesModal && this.managePurposesModal.isVisible()) {
                    this.renderPurposesList();
                }

                this.showStatus('Purpose added successfully.', 'success');
                setTimeout(() => this.hideStatus(), 2000);
            }
        },

        /**
         * Open manage purposes modal
         */
        openManagePurposesModal() {
            this.renderPurposesList();
            if (this.managePurposesModal) {
                this.managePurposesModal.show();
            }
        },

        /**
         * Close manage purposes modal
         */
        closeManagePurposesModal() {
            if (this.managePurposesModal) {
                this.managePurposesModal.hide();
            }
        },

        /**
         * Render purposes list
         */
        renderPurposesList() {
            if (!this.elements.purposesList) return;

            const customPurposes = PurposesManager.getCustomPurposes();

            if (customPurposes.length === 0) {
                this.elements.purposesList.innerHTML = '<p style="color: var(--muted); text-align: center; padding: 24px;">No custom purposes yet. Add one using the "+" button.</p>';
                return;
            }

            let html = '<div style="display: flex; flex-direction: column; gap: 12px;">';

            customPurposes.forEach((purpose) => {
                const displayName = PurposesManager.getDisplayName(purpose);
                const safePurpose = DOM.escapeHtmlForAttribute(purpose);

                html += `
                    <div class="purpose-item" data-purpose="${safePurpose}" style="display: flex; align-items: center; gap: 12px; padding: 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg);">
                        <div style="flex: 1;">
                            <div style="font-weight: 500; margin-bottom: 4px;">${DOM.escapeHtml(displayName)}</div>
                            <div style="font-size: 12px; color: var(--muted); font-family: monospace;">${DOM.escapeHtml(purpose)}</div>
                        </div>
                        <button type="button" class="btn btn-secondary edit-purpose-btn" data-purpose="${safePurpose}" style="padding: 8px 12px; white-space: nowrap;">Edit</button>
                        <button type="button" class="btn btn-secondary delete-purpose-btn" data-purpose="${safePurpose}" style="padding: 8px 12px; white-space: nowrap; background: var(--danger); color: white;">Delete</button>
                    </div>
                `;
            });

            html += '</div>';
            this.elements.purposesList.innerHTML = html;

            // Attach event listeners
            this.elements.purposesList.querySelectorAll('.edit-purpose-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    e.preventDefault();
                    const purpose = e.currentTarget.getAttribute('data-purpose');
                    if (purpose) {
                        this.editPurpose(purpose);
                    }
                });
            });

            this.elements.purposesList.querySelectorAll('.delete-purpose-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    e.preventDefault();
                    const purpose = e.currentTarget.getAttribute('data-purpose');
                    if (purpose) {
                        this.deletePurpose(purpose);
                    }
                });
            });
        },

        /**
         * Edit purpose
         * @param {string} oldPurpose - Old purpose name
         */
        editPurpose(oldPurpose) {
            if (!oldPurpose) return;

            const displayName = PurposesManager.getDisplayName(oldPurpose);
            const newName = prompt(`Edit purpose name:\n\nCurrent: ${displayName}\n(${oldPurpose})`, displayName);

            if (!newName || newName.trim() === '') {
                return;
            }

            const normalizedPurpose = PurposesManager.updatePurpose(oldPurpose, newName);
            
            if (!normalizedPurpose) {
                this.showStatus('A purpose with this name already exists.', 'error');
                return;
            }

            // Update dropdowns
            if (this.elements.promptPurposeInput) {
                const prompts = state.get('prompts') || [];
                PurposesManager.populateSelect(this.elements.promptPurposeInput, true, prompts);
                if (this.elements.promptPurposeInput.value === oldPurpose) {
                    this.elements.promptPurposeInput.value = normalizedPurpose;
                }
            }

            // Re-render list
            this.renderPurposesList();

            this.showStatus('Purpose updated successfully.', 'success');
            setTimeout(() => this.hideStatus(), 2000);
        },

        /**
         * Delete purpose
         * @param {string} purpose - Purpose name to delete
         */
        deletePurpose(purpose) {
            const displayName = PurposesManager.getDisplayName(purpose);
            if (!confirm(`Are you sure you want to delete the purpose "${displayName}"?\n\nThis will not affect existing prompts, but you won't be able to select this purpose for new prompts.`)) {
                return;
            }

            PurposesManager.removePurpose(purpose);

            // Update dropdowns
            if (this.elements.promptPurposeInput) {
                const prompts = state.get('prompts') || [];
                PurposesManager.populateSelect(this.elements.promptPurposeInput, true, prompts);
                if (this.elements.promptPurposeInput.value === purpose) {
                    this.elements.promptPurposeInput.value = '';
                }
            }

            // Re-render list
            this.renderPurposesList();

            this.showStatus('Purpose deleted successfully.', 'success');
            setTimeout(() => this.hideStatus(), 2000);
        },

        /**
         * Show status message
         * @param {string} message - Message text
         * @param {string} type - 'success' or 'error'
         */
        showStatus(message, type = 'success') {
            if (this.statusMessage) {
                this.statusMessage.show(message, type);
            }
        },

        /**
         * Hide status message
         */
        hideStatus() {
            if (this.statusMessage) {
                this.statusMessage.hide();
            }
        }
    };

    // Export
    window.PromptModalManager = ModalManager;
})();

