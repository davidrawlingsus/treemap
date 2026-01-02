/**
 * Prompt Engineering Filters
 * Filter UI and logic for prompt results
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
        },

        /**
         * Build filter UI from actions
         * @param {Array} actions - Array of action objects
         */
        buildFilterUI(actions) {
            if (!this.elements.nameFilters || !this.elements.versionFilters) {
                return;
            }

            // Collect unique prompt names and versions
            const promptNames = new Set();
            const promptVersions = new Map(); // name -> Set of versions

            actions.forEach(action => {
                if (action.prompt_name) {
                    promptNames.add(action.prompt_name);
                    if (!promptVersions.has(action.prompt_name)) {
                        promptVersions.set(action.prompt_name, new Set());
                    }
                    if (action.prompt_version !== null && action.prompt_version !== undefined) {
                        promptVersions.get(action.prompt_name).add(action.prompt_version);
                    }
                }
            });

            const filterState = state.get('filterState');
            const shouldCheckAll = filterState.promptNames.size === 0 && filterState.promptVersions.size === 0;

            // Build prompt name checkboxes
            let nameFiltersHtml = '';
            Array.from(promptNames).sort().forEach(name => {
                const isChecked = shouldCheckAll || filterState.promptNames.has(name);
                if (isChecked && shouldCheckAll) {
                    filterState.promptNames.add(name);
                }
                const safeName = DOM.escapeHtmlForAttribute(name);
                nameFiltersHtml += `
                    <div class="filter-checkbox-item">
                        <input type="checkbox" id="filter-name-${safeName}" data-prompt-name="${safeName}" ${isChecked ? 'checked' : ''}>
                        <label for="filter-name-${safeName}">${DOM.escapeHtml(name)}</label>
                    </div>
                `;
            });
            this.elements.nameFilters.innerHTML = nameFiltersHtml || '<span style="color: var(--muted); font-size: 12px;">No prompts found</span>';

            // Build version checkboxes
            let versionFiltersHtml = '';
            Array.from(promptVersions.entries()).sort().forEach(([name, versions]) => {
                Array.from(versions).sort((a, b) => a - b).forEach(version => {
                    const versionKey = `${name}:v${version}`;
                    const isChecked = shouldCheckAll || filterState.promptVersions.has(versionKey);
                    if (isChecked && shouldCheckAll) {
                        filterState.promptVersions.add(versionKey);
                    }
                    const safeName = DOM.escapeHtmlForAttribute(name);
                    const safeVersionKey = DOM.escapeHtmlForAttribute(versionKey);
                    versionFiltersHtml += `
                        <div class="filter-checkbox-item">
                            <input type="checkbox" id="filter-version-${safeName}-${version}" data-version-key="${safeVersionKey}" data-prompt-name="${safeName}" data-version="${version}" ${isChecked ? 'checked' : ''}>
                            <label for="filter-version-${safeName}-${version}">${DOM.escapeHtml(name)} v${version}</label>
                        </div>
                    `;
                });
            });
            this.elements.versionFilters.innerHTML = versionFiltersHtml || '<span style="color: var(--muted); font-size: 12px;">No versions found</span>';

            // Show/hide filter button
            if (this.elements.filterButton) {
                this.elements.filterButton.style.display = actions.length > 0 ? 'flex' : 'none';
            }

            // Update badge
            this.updateBadge();

            // Attach listeners
            this.attachListeners();
        },

        /**
         * Attach filter event listeners
         */
        attachListeners() {
            if (!this.elements.nameFilters || !this.elements.versionFilters) {
                return;
            }

            const filterState = state.get('filterState');

            // Clear state
            filterState.promptNames.clear();
            filterState.promptVersions.clear();

            // Prompt name filters
            const nameCheckboxes = this.elements.nameFilters.querySelectorAll('input[type="checkbox"]');
            const debouncedNameChange = debounce(() => {
                this.handleFilterChange();
            }, 300);

            nameCheckboxes.forEach(checkbox => {
                // Initialize state from checked checkboxes
                if (checkbox.checked) {
                    const promptName = checkbox.getAttribute('data-prompt-name');
                    filterState.promptNames.add(promptName);
                }

                checkbox.addEventListener('change', (e) => {
                    const promptName = e.target.getAttribute('data-prompt-name');
                    if (e.target.checked) {
                        filterState.promptNames.add(promptName);
                    } else {
                        filterState.promptNames.delete(promptName);
                    }
                    debouncedNameChange();
                });
            });

            // Version filters
            const versionCheckboxes = this.elements.versionFilters.querySelectorAll('input[type="checkbox"]');
            const debouncedVersionChange = debounce(() => {
                this.handleFilterChange();
            }, 300);

            versionCheckboxes.forEach(checkbox => {
                // Initialize state from checked checkboxes
                if (checkbox.checked) {
                    const versionKey = checkbox.getAttribute('data-version-key');
                    filterState.promptVersions.add(versionKey);
                }

                checkbox.addEventListener('change', (e) => {
                    const versionKey = e.target.getAttribute('data-version-key');
                    if (e.target.checked) {
                        filterState.promptVersions.add(versionKey);
                    } else {
                        filterState.promptVersions.delete(versionKey);
                    }
                    debouncedVersionChange();
                });
            });
        },

        /**
         * Handle filter change with debouncing
         */
        handleFilterChange() {
            this.updateBadge();
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

            // Uncheck all checkboxes
            if (this.elements.nameFilters) {
                this.elements.nameFilters.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                    cb.checked = false;
                });
            }
            if (this.elements.versionFilters) {
                this.elements.versionFilters.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                    cb.checked = false;
                });
            }

            this.updateBadge();
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
            const totalFilters = filterState.promptNames.size + filterState.promptVersions.size;

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
        },

        /**
         * Open filter dropdown
         */
        open() {
            if (this.elements.filterDropdown) {
                this.elements.filterDropdown.style.display = 'block';
            }
        },

        /**
         * Close filter dropdown
         */
        close() {
            if (this.elements.filterDropdown) {
                this.elements.filterDropdown.style.display = 'none';
            }
        },

        /**
         * Check if filter dropdown is open
         */
        isOpen() {
            return this.elements.filterDropdown?.style.display !== 'none';
        }
    };

    // Export
    window.PromptFilterManager = FilterManager;
})();

