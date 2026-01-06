/**
 * Prompt Engineering Filters
 * Filter UI and logic for prompt results with two-layer navigation
 */

(function() {
    'use strict';

    if (!window.FounderAdmin || !window.PromptEngineeringState || !window.PromptUIRenderer) {
        console.error('[PROMPT_FILTERS] Dependencies not loaded');
        return;
    }

    const { DOM, debounce } = window.FounderAdmin;
    const state = window.PromptEngineeringState;
    const UIRenderer = window.PromptUIRenderer;

    /**
     * Filter Manager
     */
    const FilterManager = {
        elements: null,
        onFilterChange: null,
        currentFilterType: null, // 'prompt' or 'version'
        selectedPromptNames: new Set(), // For version filtering

        /**
         * Initialize filter manager
         * @param {Object} elements - Filter UI elements
         * @param {Function} onFilterChange - Callback when filters change
         */
        init(elements, onFilterChange) {
            this.elements = elements;
            this.onFilterChange = onFilterChange;

            if (!this.elements.filterButton || !this.elements.filterDropdown) {
                console.warn('[FILTERS] Filter elements not found');
                return;
            }

            // Setup filter button toggle
            this.elements.filterButton.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggle();
            });

            // Close on outside click
            document.addEventListener('click', (e) => {
                if (!this.elements.filterDropdown.contains(e.target) && 
                    !this.elements.filterButton.contains(e.target) &&
                    this.isOpen()) {
                    this.close();
                }
            });

            // Clear all filters button
            if (this.elements.clearAllButton) {
                this.elements.clearAllButton.addEventListener('click', () => {
                    this.clearAll();
                });
            }

            // Back button
            const backButton = document.getElementById('backToPromptFilterType');
            if (backButton) {
                backButton.addEventListener('click', () => {
                    this.showFilterTypeView();
                });
            }

            // Select all / Clear all buttons
            const selectAllBtn = document.getElementById('selectAllPromptItems');
            const clearAllBtn = document.getElementById('clearAllPromptItems');
            if (selectAllBtn) {
                selectAllBtn.addEventListener('click', () => {
                    this.selectAllCurrentItems();
                });
            }
            if (clearAllBtn) {
                clearAllBtn.addEventListener('click', () => {
                    this.clearAllCurrentItems();
                });
            }

            // Listen for prompt updates to refresh filters
            state.subscribe('prompts', () => {
                // Only refresh if dropdown is open or slideout is open
                if (this.isOpen() || (window.PromptEngineeringApp && window.PromptEngineeringApp.slideoutManager && window.PromptEngineeringApp.slideoutManager.slideout?.isOpen())) {
                    this.refreshFilters();
                }
            });
        },

        /**
         * Build filter UI from prompts and actions
         * @param {Array} actions - Array of action objects (optional, for backward compatibility)
         */
        buildFilterUI(actions = null) {
            // Get prompts from state (all prompts, not just those with actions)
            const prompts = state.get('prompts') || [];
            
            // Also get actions to see which prompts/versions have results
            const allActions = actions || state.get('allActions') || [];
            
            // Build prompt name -> versions map from prompts
            const promptVersionsMap = new Map(); // name -> Set of versions
            const promptsWithResults = new Set(); // Track which prompts have execution results
            
            prompts.forEach(prompt => {
                if (prompt.name) {
                    if (!promptVersionsMap.has(prompt.name)) {
                        promptVersionsMap.set(prompt.name, new Set());
                    }
                    promptVersionsMap.get(prompt.name).add(prompt.version);
                }
            });
            
            // Also add versions from actions (in case there are actions for prompts not in current list)
            allActions.forEach(action => {
                if (action.prompt_name && action.prompt_version !== null && action.prompt_version !== undefined) {
                    if (!promptVersionsMap.has(action.prompt_name)) {
                        promptVersionsMap.set(action.prompt_name, new Set());
                    }
                    promptVersionsMap.get(action.prompt_name).add(action.prompt_version);
                    promptsWithResults.add(action.prompt_name);
                }
            });

            // Build filter type list (first layer)
            this.buildFilterTypeList(promptVersionsMap, promptsWithResults);

            // Show/hide filter button
            if (this.elements.filterButton) {
                const hasPrompts = promptVersionsMap.size > 0;
                this.elements.filterButton.style.display = hasPrompts ? 'flex' : 'none';
            }

            // Update badge
            this.updateBadge();

            // Update active filters display
            this.updateActiveFiltersDisplay();
        },

        /**
         * Build filter type list (first layer)
         */
        buildFilterTypeList(promptVersionsMap, promptsWithResults) {
            const filterTypeList = document.getElementById('promptFilterTypeList');
            if (!filterTypeList) return;

            const filterState = state.get('filterState');
            const hasPromptFilters = filterState.promptNames.size > 0;
            const hasVersionFilters = filterState.promptVersions.size > 0;
            const hasModelFilters = filterState.models.size > 0;

            let html = '';

            // Prompt filter option
            html += `
                <div class="filter-type-item" data-filter-type="prompt" style="padding: 12px 16px; border-bottom: 1px solid #e0e0e0; cursor: pointer; display: flex; justify-content: space-between; align-items: center; transition: background 0.2s;" 
                     onmouseover="this.style.backgroundColor='#f0f0f0';" 
                     onmouseout="this.style.backgroundColor='transparent';">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span style="font-size: 14px; font-weight: 500;">Prompt</span>
                        ${hasPromptFilters ? `<span style="font-size: 11px; color: #667eea; background: #e8edff; padding: 2px 6px; border-radius: 10px;">${filterState.promptNames.size}</span>` : ''}
                    </div>
                    <span style="color: #999; font-size: 12px;">→</span>
                </div>
            `;

            // Version filter option
            html += `
                <div class="filter-type-item" data-filter-type="version" style="padding: 12px 16px; border-bottom: 1px solid #e0e0e0; cursor: pointer; display: flex; justify-content: space-between; align-items: center; transition: background 0.2s;" 
                     onmouseover="this.style.backgroundColor='#f0f0f0';" 
                     onmouseout="this.style.backgroundColor='transparent';">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span style="font-size: 14px; font-weight: 500;">Version</span>
                        ${hasVersionFilters ? `<span style="font-size: 11px; color: #667eea; background: #e8edff; padding: 2px 6px; border-radius: 10px;">${filterState.promptVersions.size}</span>` : ''}
                    </div>
                    <span style="color: #999; font-size: 12px;">→</span>
                </div>
            `;

            // Model filter option
            html += `
                <div class="filter-type-item" data-filter-type="model" style="padding: 12px 16px; border-bottom: 1px solid #e0e0e0; cursor: pointer; display: flex; justify-content: space-between; align-items: center; transition: background 0.2s;" 
                     onmouseover="this.style.backgroundColor='#f0f0f0';" 
                     onmouseout="this.style.backgroundColor='transparent';">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span style="font-size: 14px; font-weight: 500;">Model</span>
                        ${hasModelFilters ? `<span style="font-size: 11px; color: #667eea; background: #e8edff; padding: 2px 6px; border-radius: 10px;">${filterState.models.size}</span>` : ''}
                    </div>
                    <span style="color: #999; font-size: 12px;">→</span>
                </div>
            `;

            filterTypeList.innerHTML = html;

            // Attach click handlers
            filterTypeList.querySelectorAll('.filter-type-item').forEach(item => {
                item.addEventListener('click', (e) => {
                    const filterType = e.currentTarget.getAttribute('data-filter-type');
                    if (filterType === 'prompt') {
                        this.showPromptSelection();
                    } else if (filterType === 'version') {
                        this.showVersionSelection();
                    } else if (filterType === 'model') {
                        this.showModelSelection();
                    }
                });
            });
        },

        /**
         * Show prompt selection view (second layer)
         */
        showPromptSelection() {
            this.currentFilterType = 'prompt';
            const typeView = document.getElementById('promptFilterTypeView');
            const selectionView = document.getElementById('promptFilterSelectionView');
            const selectionTitle = document.getElementById('promptFilterSelectionTitle');
            const selectionList = document.getElementById('promptFilterSelectionList');

            if (!typeView || !selectionView || !selectionTitle || !selectionList) return;

            typeView.style.display = 'none';
            selectionView.style.display = 'block';
            selectionTitle.textContent = 'Filter by Prompt';

            // Get prompts from state
            const prompts = state.get('prompts') || [];
            const promptNames = new Set();
            prompts.forEach(p => {
                if (p.name) promptNames.add(p.name);
            });

            const filterState = state.get('filterState');
            const shouldCheckAll = filterState.promptNames.size === 0;

            let html = '';
            Array.from(promptNames).sort().forEach(name => {
                const isChecked = shouldCheckAll || filterState.promptNames.has(name);
                if (isChecked && shouldCheckAll) {
                    filterState.promptNames.add(name);
                }
                const safeName = DOM.escapeHtmlForAttribute(name);
                html += `
                    <div class="filter-checkbox-item" style="padding: 10px 12px; border-bottom: 1px solid #f0f0f0; display: flex; align-items: center; gap: 10px; cursor: pointer; transition: background 0.2s;"
                         onmouseover="this.style.backgroundColor='#f8f9fa';" 
                         onmouseout="this.style.backgroundColor='transparent';">
                        <input type="checkbox" id="filter-prompt-${safeName}" data-prompt-name="${safeName}" ${isChecked ? 'checked' : ''} style="cursor: pointer;">
                        <label for="filter-prompt-${safeName}" style="cursor: pointer; flex: 1; font-size: 13px; margin: 0;">${DOM.escapeHtml(name)}</label>
                    </div>
                `;
            });

            selectionList.innerHTML = html || '<div style="padding: 16px; text-align: center; color: #999; font-size: 13px;">No prompts found</div>';

            // Attach listeners
            selectionList.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
                checkbox.addEventListener('change', (e) => {
                    const promptName = e.target.getAttribute('data-prompt-name');
                    const filterState = state.get('filterState');
                    if (e.target.checked) {
                        filterState.promptNames.add(promptName);
                    } else {
                        filterState.promptNames.delete(promptName);
                    }
                    this.handleFilterChange();
                });
            });
        },

        /**
         * Show version selection view (second layer)
         */
        showVersionSelection() {
            this.currentFilterType = 'version';
            const typeView = document.getElementById('promptFilterTypeView');
            const selectionView = document.getElementById('promptFilterSelectionView');
            const selectionTitle = document.getElementById('promptFilterSelectionTitle');
            const selectionList = document.getElementById('promptFilterSelectionList');

            if (!typeView || !selectionView || !selectionTitle || !selectionList) return;

            typeView.style.display = 'none';
            selectionView.style.display = 'block';
            selectionTitle.textContent = 'Filter by Version';

            // Get prompts from state
            const prompts = state.get('prompts') || [];
            const promptVersionsMap = new Map(); // name -> Set of versions

            prompts.forEach(prompt => {
                if (prompt.name) {
                    if (!promptVersionsMap.has(prompt.name)) {
                        promptVersionsMap.set(prompt.name, new Set());
                    }
                    promptVersionsMap.get(prompt.name).add(prompt.version);
                }
            });

            // Also get from actions
            const allActions = state.get('allActions') || [];
            allActions.forEach(action => {
                if (action.prompt_name && action.prompt_version !== null && action.prompt_version !== undefined) {
                    if (!promptVersionsMap.has(action.prompt_name)) {
                        promptVersionsMap.set(action.prompt_name, new Set());
                    }
                    promptVersionsMap.get(action.prompt_name).add(action.prompt_version);
                }
            });

            const filterState = state.get('filterState');
            const shouldCheckAll = filterState.promptVersions.size === 0;

            let html = '';
            Array.from(promptVersionsMap.entries()).sort().forEach(([name, versions]) => {
                Array.from(versions).sort((a, b) => a - b).forEach(version => {
                    const versionKey = `${name}:v${version}`;
                    const isChecked = shouldCheckAll || filterState.promptVersions.has(versionKey);
                    if (isChecked && shouldCheckAll) {
                        filterState.promptVersions.add(versionKey);
                    }
                    const safeName = DOM.escapeHtmlForAttribute(name);
                    const safeVersionKey = DOM.escapeHtmlForAttribute(versionKey);
                    html += `
                        <div class="filter-checkbox-item" style="padding: 10px 12px; border-bottom: 1px solid #f0f0f0; display: flex; align-items: center; gap: 10px; cursor: pointer; transition: background 0.2s;"
                             onmouseover="this.style.backgroundColor='#f8f9fa';" 
                             onmouseout="this.style.backgroundColor='transparent';">
                            <input type="checkbox" id="filter-version-${safeName}-${version}" data-version-key="${safeVersionKey}" data-prompt-name="${safeName}" data-version="${version}" ${isChecked ? 'checked' : ''} style="cursor: pointer;">
                            <label for="filter-version-${safeName}-${version}" style="cursor: pointer; flex: 1; font-size: 13px; margin: 0;">${DOM.escapeHtml(name)} v${version}</label>
                        </div>
                    `;
                });
            });

            selectionList.innerHTML = html || '<div style="padding: 16px; text-align: center; color: #999; font-size: 13px;">No versions found</div>';

            // Attach listeners
            selectionList.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
                checkbox.addEventListener('change', (e) => {
                    const versionKey = e.target.getAttribute('data-version-key');
                    const filterState = state.get('filterState');
                    if (e.target.checked) {
                        filterState.promptVersions.add(versionKey);
                    } else {
                        filterState.promptVersions.delete(versionKey);
                    }
                    this.handleFilterChange();
                });
            });
        },

        /**
         * Show model selection view (second layer)
         */
        showModelSelection() {
            this.currentFilterType = 'model';
            const typeView = document.getElementById('promptFilterTypeView');
            const selectionView = document.getElementById('promptFilterSelectionView');
            const selectionTitle = document.getElementById('promptFilterSelectionTitle');
            const selectionList = document.getElementById('promptFilterSelectionList');

            if (!typeView || !selectionView || !selectionTitle || !selectionList) return;

            typeView.style.display = 'none';
            selectionView.style.display = 'block';
            selectionTitle.textContent = 'Filter by Model';

            // Get all actions to extract unique models
            const allActions = state.get('allActions') || [];
            const models = new Set();
            
            allActions.forEach(action => {
                const model = action.actions?.model;
                if (model) {
                    models.add(model);
                }
            });

            const filterState = state.get('filterState');
            const shouldCheckAll = filterState.models.size === 0;

            let html = '';
            Array.from(models).sort().forEach(model => {
                const isChecked = shouldCheckAll || filterState.models.has(model);
                if (isChecked && shouldCheckAll) {
                    filterState.models.add(model);
                }
                const safeModel = DOM.escapeHtmlForAttribute(model);
                html += `
                    <div class="filter-checkbox-item" style="padding: 10px 12px; border-bottom: 1px solid #f0f0f0; display: flex; align-items: center; gap: 10px; cursor: pointer; transition: background 0.2s;"
                         onmouseover="this.style.backgroundColor='#f8f9fa';" 
                         onmouseout="this.style.backgroundColor='transparent';">
                        <input type="checkbox" id="filter-model-${safeModel}" data-model="${safeModel}" ${isChecked ? 'checked' : ''} style="cursor: pointer;">
                        <label for="filter-model-${safeModel}" style="cursor: pointer; flex: 1; font-size: 13px; margin: 0;">${DOM.escapeHtml(model)}</label>
                    </div>
                `;
            });

            selectionList.innerHTML = html || '<div style="padding: 16px; text-align: center; color: #999; font-size: 13px;">No models found</div>';

            // Attach listeners
            selectionList.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
                checkbox.addEventListener('change', (e) => {
                    const model = e.target.getAttribute('data-model');
                    const filterState = state.get('filterState');
                    if (e.target.checked) {
                        filterState.models.add(model);
                    } else {
                        filterState.models.delete(model);
                    }
                    this.handleFilterChange();
                });
            });
        },

        /**
         * Show filter type view (first layer)
         */
        showFilterTypeView() {
            this.currentFilterType = null;
            const typeView = document.getElementById('promptFilterTypeView');
            const selectionView = document.getElementById('promptFilterSelectionView');

            if (typeView) typeView.style.display = 'block';
            if (selectionView) selectionView.style.display = 'none';

            // Rebuild filter type list to update counts
            this.refreshFilters();
        },

        /**
         * Select all items in current view
         */
        selectAllCurrentItems() {
            const selectionList = document.getElementById('promptFilterSelectionList');
            if (!selectionList) return;

            const filterState = state.get('filterState');
            const checkboxes = selectionList.querySelectorAll('input[type="checkbox"]');

            checkboxes.forEach(checkbox => {
                checkbox.checked = true;
                if (this.currentFilterType === 'prompt') {
                    const promptName = checkbox.getAttribute('data-prompt-name');
                    filterState.promptNames.add(promptName);
                } else if (this.currentFilterType === 'version') {
                    const versionKey = checkbox.getAttribute('data-version-key');
                    filterState.promptVersions.add(versionKey);
                } else if (this.currentFilterType === 'model') {
                    const model = checkbox.getAttribute('data-model');
                    filterState.models.add(model);
                }
            });

            this.handleFilterChange();
        },

        /**
         * Clear all items in current view
         */
        clearAllCurrentItems() {
            const selectionList = document.getElementById('promptFilterSelectionList');
            if (!selectionList) return;

            const filterState = state.get('filterState');
            const checkboxes = selectionList.querySelectorAll('input[type="checkbox"]');

            checkboxes.forEach(checkbox => {
                checkbox.checked = false;
                if (this.currentFilterType === 'prompt') {
                    const promptName = checkbox.getAttribute('data-prompt-name');
                    filterState.promptNames.delete(promptName);
                } else if (this.currentFilterType === 'version') {
                    const versionKey = checkbox.getAttribute('data-version-key');
                    filterState.promptVersions.delete(versionKey);
                } else if (this.currentFilterType === 'model') {
                    const model = checkbox.getAttribute('data-model');
                    filterState.models.delete(model);
                }
            });

            this.handleFilterChange();
        },

        /**
         * Update active filters display
         */
        updateActiveFiltersDisplay() {
            const activeFiltersList = document.getElementById('activePromptFiltersList');
            if (!activeFiltersList) return;

            const filterState = state.get('filterState');
            const activeFilters = [];

            filterState.promptNames.forEach(name => {
                activeFilters.push(`Prompt: ${name}`);
            });

            filterState.promptVersions.forEach(versionKey => {
                const [name, version] = versionKey.split(':v');
                activeFilters.push(`Version: ${name} v${version}`);
            });

            filterState.models.forEach(model => {
                activeFilters.push(`Model: ${model}`);
            });

            if (activeFilters.length === 0) {
                activeFiltersList.innerHTML = '<div style="padding: 8px; text-align: center; color: #999; font-size: 12px;">No active filters</div>';
            } else {
                activeFiltersList.innerHTML = activeFilters.map(filter => 
                    `<div style="padding: 4px 8px; margin: 2px; background: #e8edff; color: #667eea; border-radius: 4px; font-size: 11px; display: inline-block;">${DOM.escapeHtml(filter)}</div>`
                ).join('');
            }
        },

        /**
         * Refresh filters (rebuild from current state)
         */
        refreshFilters() {
            const actions = state.get('allActions') || [];
            this.buildFilterUI(actions);
        },

        /**
         * Handle filter change with debouncing
         */
        handleFilterChange() {
            this.updateBadge();
            this.updateActiveFiltersDisplay();
            if (this.onFilterChange) {
                this.onFilterChange();
            }
        },

        /**
         * Clear all filters
         */
        clearAll() {
            const filterState = state.get('filterState');
            filterState.promptNames.clear();
            filterState.promptVersions.clear();
            filterState.models.clear();

            // If in selection view, uncheck all checkboxes
            const selectionList = document.getElementById('promptFilterSelectionList');
            if (selectionList) {
                selectionList.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                    cb.checked = false;
                });
            }

            this.updateBadge();
            this.updateActiveFiltersDisplay();
            if (this.onFilterChange) {
                this.onFilterChange();
            }
        },

        /**
         * Update filter badge
         */
        updateBadge() {
            if (!this.elements.badge) return;

            const filterState = state.get('filterState');
            const totalFilters = filterState.promptNames.size + filterState.promptVersions.size + filterState.models.size;

            if (totalFilters > 0) {
                this.elements.badge.textContent = totalFilters;
                this.elements.badge.classList.add('active');
            } else {
                this.elements.badge.classList.remove('active');
            }
        },

        /**
         * Toggle filter dropdown
         */
        toggle() {
            if (!this.elements.filterDropdown) return;
            const isVisible = this.elements.filterDropdown.style.display !== 'none';
            this.elements.filterDropdown.style.display = isVisible ? 'none' : 'block';
            
            // Refresh filters when opening
            if (!isVisible) {
                this.refreshFilters();
            }
        },

        /**
         * Open filter dropdown
         */
        open() {
            if (this.elements.filterDropdown) {
                this.elements.filterDropdown.style.display = 'block';
                this.refreshFilters();
            }
        },

        /**
         * Close filter dropdown
         */
        close() {
            if (this.elements.filterDropdown) {
                this.elements.filterDropdown.style.display = 'none';
                // Return to filter type view when closing
                this.showFilterTypeView();
            }
        },

        /**
         * Check if filter dropdown is open
         */
        isOpen() {
            return this.elements.filterDropdown?.style.display !== 'none';
        },

        /**
         * Auto-apply filters for a specific prompt
         * This sets filters to show only results for the given prompt name
         * @param {string} promptName - The prompt name to filter by
         * @param {number|null} promptVersion - Optional specific version to filter by
         */
        applyPromptFilter(promptName, promptVersion = null) {
            if (!promptName) return;

            const filterState = state.get('filterState');
            
            // Clear existing filters
            filterState.promptNames.clear();
            filterState.promptVersions.clear();
            filterState.models.clear();

            // Set filter for this prompt name
            filterState.promptNames.add(promptName);

            // If a specific version is provided, also filter by version
            if (promptVersion !== null && promptVersion !== undefined) {
                const versionKey = `${promptName}:v${promptVersion}`;
                filterState.promptVersions.add(versionKey);
            }

            // Update UI
            this.updateBadge();
            this.updateActiveFiltersDisplay();
            
            // Refresh filter UI if dropdown is open or slideout is open
            if (this.isOpen() || (window.PromptEngineeringApp && window.PromptEngineeringApp.slideoutManager && window.PromptEngineeringApp.slideoutManager.slideout?.isOpen())) {
                this.refreshFilters();
            }

            // Trigger filter change callback to re-render results
            if (this.onFilterChange) {
                this.onFilterChange();
            }
        }
    };

    // Export
    window.PromptFilterManager = FilterManager;
})();
