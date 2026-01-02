/**
 * Founder Admin Shared UI Components
 * Reusable components for founder admin pages
 */

(function() {
    'use strict';

    if (!window.FounderAdmin) {
        console.error('[COMPONENTS] FounderAdmin utilities must be loaded first');
        return;
    }

    const { DOM } = window.FounderAdmin;

    /**
     * Modal Component
     */
    class Modal {
        constructor(containerId, options = {}) {
            this.container = DOM.getElement(containerId);
            if (!this.container) {
                console.error(`[Modal] Container not found: #${containerId}`);
                return;
            }

            this.options = {
                closeOnBackdropClick: true,
                closeOnEscape: true,
                ...options
            };

            this.init();
        }

        init() {
            // Find close button
            this.closeButton = this.container.querySelector('[data-modal-close]') ||
                             this.container.querySelector('.modal-close-button');

            // Setup event listeners
            if (this.closeButton) {
                this.closeButton.addEventListener('click', () => this.hide());
            }

            if (this.options.closeOnBackdropClick) {
                this.container.addEventListener('click', (e) => {
                    if (e.target === this.container) {
                        this.hide();
                    }
                });
            }

            if (this.options.closeOnEscape) {
                this.escapeHandler = (e) => {
                    if (e.key === 'Escape' && this.isVisible()) {
                        this.hide();
                    }
                };
                document.addEventListener('keydown', this.escapeHandler);
            }
        }

        show() {
            if (this.container) {
                this.container.classList.add('visible');
                // Remove inline display style if present to allow CSS to control visibility
                if (this.container.style.display === 'none') {
                    this.container.style.display = '';
                }
            }
        }

        hide() {
            if (this.container) {
                this.container.classList.remove('visible');
            }
        }

        isVisible() {
            return this.container?.classList.contains('visible') || false;
        }

        setContent(html) {
            const form = this.container?.querySelector('form');
            if (form) {
                form.innerHTML = html;
            } else {
                const content = this.container?.querySelector('.modal-content') ||
                              this.container?.querySelector('form');
                if (content) {
                    content.innerHTML = html;
                }
            }
        }

        destroy() {
            if (this.escapeHandler) {
                document.removeEventListener('keydown', this.escapeHandler);
            }
        }
    }

    /**
     * Status Message Component
     */
    class StatusMessage {
        constructor(elementId) {
            this.element = DOM.getElement(elementId);
        }

        show(message, type = 'success') {
            DOM.showStatus(this.element, message, type);
        }

        hide() {
            DOM.showStatus(this.element, '', 'success');
        }

        success(message) {
            this.show(message, 'success');
        }

        error(message) {
            this.show(message, 'error');
        }
    }

    /**
     * Slideout Panel Component
     */
    class SlideoutPanel {
        constructor(panelId, overlayId, options = {}) {
            this.panel = DOM.getElement(panelId);
            this.overlay = DOM.getElement(overlayId);
            
            if (!this.panel) {
                console.error(`[Slideout] Panel not found: #${panelId}`);
                return;
            }

            this.options = {
                width: 500,
                closeOnOverlayClick: true,
                closeOnEscape: true,
                ...options
            };

            this.init();
        }

        init() {
            // Find close button
            const closeBtn = this.panel.querySelector('[data-slideout-close]') ||
                           this.panel.querySelector('.ai-close-btn');
            
            if (closeBtn) {
                closeBtn.addEventListener('click', () => this.close());
            }

            // Overlay click handler
            if (this.overlay && this.options.closeOnOverlayClick) {
                this.overlay.addEventListener('click', (e) => {
                    if (e.target === this.overlay) {
                        this.close();
                    }
                });
            }

            // Escape key handler
            if (this.options.closeOnEscape) {
                this.escapeHandler = (e) => {
                    if (e.key === 'Escape' && this.isOpen()) {
                        this.close();
                    }
                };
                document.addEventListener('keydown', this.escapeHandler);
            }
        }

        open(title = null) {
            if (title && this.panel) {
                const titleEl = this.panel.querySelector('[data-slideout-title]') ||
                              this.panel.querySelector('.ai-insights-header h2, .ai-insights-header > div');
                if (titleEl) {
                    titleEl.textContent = title;
                }
            }

            if (this.panel) {
                this.panel.classList.add('open');
            }

            if (this.overlay) {
                this.overlay.classList.add('visible');
            }

            document.body.classList.add('slideout-open');
        }

        close() {
            if (this.panel) {
                this.panel.classList.remove('open');
                this.panel.classList.remove('prompt-engineering-context');
            }

            if (this.overlay) {
                this.overlay.classList.remove('visible');
            }

            document.body.classList.remove('slideout-open');
        }

        isOpen() {
            return this.panel?.classList.contains('open') || false;
        }

        setContent(html) {
            const content = this.panel?.querySelector('[data-slideout-content]') ||
                          this.panel?.querySelector('.ai-insights-content');
            if (content) {
                content.innerHTML = html;
            }
        }

        getContent() {
            const content = this.panel?.querySelector('[data-slideout-content]') ||
                          this.panel?.querySelector('.ai-insights-content');
            return content;
        }

        addContextClass(className) {
            if (this.panel) {
                this.panel.classList.add(className);
            }
        }

        removeContextClass(className) {
            if (this.panel) {
                this.panel.classList.remove(className);
            }
        }

        destroy() {
            if (this.escapeHandler) {
                document.removeEventListener('keydown', this.escapeHandler);
            }
        }
    }

    /**
     * Filter Component
     */
    class Filter {
        constructor(containerId, options = {}) {
            this.container = DOM.getElement(containerId);
            if (!this.container) {
                console.error(`[Filter] Container not found: #${containerId}`);
                return;
            }

            this.options = {
                onFilterChange: null,
                debounceMs: 300,
                ...options
            };

            this.state = {
                filters: new Map(),
                activeCount: 0
            };

            this.init();
        }

        init() {
            // Find filter button and dropdown
            this.filterButton = this.container.querySelector('[data-filter-button]') ||
                              this.container.querySelector('.filter-button');
            this.dropdown = this.container.querySelector('[data-filter-dropdown]') ||
                          this.container.querySelector('.filter-dropdown');
            this.badge = this.container.querySelector('[data-filter-badge]') ||
                        this.container.querySelector('.filter-badge');

            // Setup toggle
            if (this.filterButton && this.dropdown) {
                this.filterButton.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.toggle();
                });

                // Close on outside click
                document.addEventListener('click', (e) => {
                    if (!this.container.contains(e.target) && this.isOpen()) {
                        this.close();
                    }
                });
            }
        }

        toggle() {
            if (this.dropdown) {
                const isVisible = this.dropdown.style.display !== 'none';
                this.dropdown.style.display = isVisible ? 'none' : 'block';
            }
        }

        open() {
            if (this.dropdown) {
                this.dropdown.style.display = 'block';
            }
        }

        close() {
            if (this.dropdown) {
                this.dropdown.style.display = 'none';
            }
        }

        isOpen() {
            return this.dropdown?.style.display !== 'none';
        }

        /**
         * Build filter UI from data
         * @param {Array} items - Array of items to create filters for
         * @param {Function} getKey - Function to get unique key from item
         * @param {Function} getLabel - Function to get label from item
         * @param {HTMLElement} container - Container element for filters
         */
        buildFilters(items, getKey, getLabel, container) {
            if (!container) return;

            container.innerHTML = '';

            items.forEach(item => {
                const key = getKey(item);
                const label = getLabel(item);
                const isChecked = this.state.filters.has(key);

                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.id = `filter-${key}`;
                checkbox.checked = isChecked;
                checkbox.dataset.filterKey = key;
                checkbox.addEventListener('change', (e) => {
                    this.handleFilterChange(key, e.target.checked);
                });

                const labelEl = document.createElement('label');
                labelEl.htmlFor = `filter-${key}`;
                labelEl.textContent = label;

                const itemDiv = document.createElement('div');
                itemDiv.className = 'filter-checkbox-item';
                itemDiv.appendChild(checkbox);
                itemDiv.appendChild(labelEl);

                container.appendChild(itemDiv);
            });

            this.updateBadge();
        }

        handleFilterChange(key, checked) {
            if (checked) {
                this.state.filters.set(key, true);
            } else {
                this.state.filters.delete(key);
            }

            this.updateBadge();

            if (this.options.onFilterChange) {
                const debounced = window.FounderAdmin?.debounce || ((fn, ms) => {
                    let timeout;
                    return (...args) => {
                        clearTimeout(timeout);
                        timeout = setTimeout(() => fn(...args), ms);
                    };
                });

                debounced(this.options.onFilterChange, this.options.debounceMs)(this.getActiveFilters());
            }
        }

        getActiveFilters() {
            return Array.from(this.state.filters.keys());
        }

        clearFilters() {
            this.state.filters.clear();
            
            // Uncheck all checkboxes
            if (this.container) {
                this.container.querySelectorAll('input[type="checkbox"][data-filter-key]').forEach(cb => {
                    cb.checked = false;
                });
            }

            this.updateBadge();

            if (this.options.onFilterChange) {
                this.options.onFilterChange(this.getActiveFilters());
            }
        }

        updateBadge() {
            this.state.activeCount = this.state.filters.size;
            
            if (this.badge) {
                if (this.state.activeCount > 0) {
                    this.badge.textContent = this.state.activeCount;
                    this.badge.classList.add('active');
                } else {
                    this.badge.classList.remove('active');
                }
            }
        }
    }

    // Export components
    window.FounderAdminComponents = {
        Modal,
        StatusMessage,
        SlideoutPanel,
        Filter
    };
})();

