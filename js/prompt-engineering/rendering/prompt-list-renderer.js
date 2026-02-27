/**
 * Prompt List Renderer Module
 * Handles rendering of the prompts list with version history
 * Supports both card and table views with sorting
 */

(function() {
    'use strict';

    if (!window.FounderAdmin || !window.PromptEngineeringState) {
        console.error('[PROMPT_LIST_RENDERER] Dependencies not loaded');
        return;
    }

    const { DOM } = window.FounderAdmin;
    const state = window.PromptEngineeringState;

    // Constants
    const PROMPT_PREVIEW_LENGTH = 200; // characters

    // Table columns configuration
    const TABLE_COLUMNS = [
        { key: 'name', label: 'Name', sortable: true, filterable: true },
        { key: 'version', label: 'Version', sortable: true, filterable: false },
        { key: 'status', label: 'Status', sortable: true, filterable: true },
        { key: 'prompt_type', label: 'Type', sortable: true, filterable: true },
        { key: 'prompt_purpose', label: 'Purpose', sortable: true, filterable: true },
        { key: 'client_display', label: 'Client', sortable: true, filterable: true },
        { key: 'llm_model', label: 'Model', sortable: true, filterable: true },
        { key: 'updated_at', label: 'Updated', sortable: true, filterable: false },
        { key: 'actions', label: '', sortable: false, filterable: false }
    ];

    /**
     * Render prompts list (dispatches to card or table view)
     * @param {HTMLElement} container - Container element
     * @param {Function} onEditClick - Callback when edit button is clicked
     * @param {Function} onVersionChange - Callback when version selector changes
     */
    function renderPrompts(container, onEditClick, onVersionChange) {
        if (!container) return;

        const viewMode = state.get('viewMode') || 'table';
        
        if (viewMode === 'table') {
            renderPromptsTable(container, onEditClick);
        } else {
            renderPromptsCards(container, onEditClick, onVersionChange);
        }
    }

    /**
     * Render prompts as cards (original view)
     */
    function renderPromptsCards(container, onEditClick, onVersionChange) {
        const prompts = state.get('prompts');

        // Ensure container has card view class
        container.className = 'domains-grid';

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
                const statusBadge = getStatusBadge(latest.status);
                const updatedAt = latest.updated_at ? new Date(latest.updated_at).toLocaleString() : 'Unknown';
                const createdAt = latest.created_at ? new Date(latest.created_at).toLocaleDateString() : 'Unknown';
                const purposeChip = `<span class="client-chip">${latest.prompt_purpose}</span>`;
                const modelChip = `<span class="client-chip" style="background: #edf2f7; border-color: #cbd5e0; color: #4a5568;">${latest.llm_model}</span>`;
                const typeBadge = getTypeBadge(latest.prompt_type || 'system');

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

                // Use appropriate message based on prompt type
                const messageText = latest.prompt_type === 'helper' 
                    ? (latest.prompt_message || '') 
                    : (latest.system_message || '');
                const preview = messageText.substring(0, PROMPT_PREVIEW_LENGTH);
                const hasMore = messageText.length > PROMPT_PREVIEW_LENGTH;

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
                            ${statusBadge} ${typeBadge} ${purposeChip} ${modelChip}
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
    }

    /**
     * Resolve the display text for the Client column based on prompt fields.
     */
    function resolveClientDisplay(prompt) {
        if (!prompt.client_facing) return 'Not Client Facing';
        if (prompt.all_clients) return 'General';

        const clientMap = state.get('clientMap') || {};
        const ids = prompt.client_ids || [];
        if (ids.length === 0) return 'No Clients Assigned';

        const names = ids.map(id => clientMap[id] || id).sort();
        return names.join(', ');
    }

    /**
     * Render prompts as a sortable table
     */
    function renderPromptsTable(container, onEditClick) {
        const prompts = state.get('prompts');
        const sortColumn = state.get('tableSortColumn') || 'updated_at';
        const sortDirection = state.get('tableSortDirection') || 'desc';
        const columnFilters = state.get('columnFilters') || {};
        const searchTerm = (state.get('searchTerm') || '').toLowerCase();
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/0ea04ade-be37-4438-ba64-4de28c7d11e9',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'ad9005'},body:JSON.stringify({sessionId:'ad9005',location:'prompt-list-renderer.js:renderPromptsTable',message:'Renderer called',data:{searchTerm,promptCount:prompts?.length,columnFilterKeys:Object.keys(columnFilters)},timestamp:Date.now(),hypothesisId:'C,D'})}).catch(()=>{});
        // #endregion

        // Change container class for table view
        container.className = 'prompts-table-container';

        if (!prompts || prompts.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">No prompts yet</h3>
                    <p style="font-size: 14px;">Create your first prompt to start transforming insights into actions.</p>
                </div>
            `;
            return;
        }

        // Apply keyword search
        let filtered = prompts;
        if (searchTerm) {
            filtered = filtered.filter(prompt => {
                const clientText = resolveClientDisplay(prompt).toLowerCase();
                return (prompt.name || '').toLowerCase().includes(searchTerm)
                    || (prompt.prompt_purpose || '').toLowerCase().includes(searchTerm)
                    || (prompt.llm_model || '').toLowerCase().includes(searchTerm)
                    || clientText.includes(searchTerm)
                    || (prompt.status || '').toLowerCase().includes(searchTerm);
            });
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/0ea04ade-be37-4438-ba64-4de28c7d11e9',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'ad9005'},body:JSON.stringify({sessionId:'ad9005',location:'prompt-list-renderer.js:searchFilter',message:'Search filter applied',data:{searchTerm,beforeCount:prompts.length,afterCount:filtered.length},timestamp:Date.now(),hypothesisId:'C,D'})}).catch(()=>{});
            // #endregion
        }

        // Apply column filters
        const filteredPrompts = applyColumnFilters(filtered, columnFilters);

        // Sort prompts
        const sortedPrompts = sortPrompts([...filteredPrompts], sortColumn, sortDirection);

        // Build table HTML
        const tableHtml = `
            <table class="prompts-table">
                <thead>
                    <tr>
                        ${TABLE_COLUMNS.map(col => {
                            if (!col.sortable && !col.filterable) {
                                return `<th class="prompts-table-th">${col.label}</th>`;
                            }
                            const isActive = sortColumn === col.key;
                            const arrow = isActive ? (sortDirection === 'asc' ? '↑' : '↓') : '';
                            const hasFilter = columnFilters[col.key] && columnFilters[col.key].length > 0;
                            const filterableClass = col.filterable ? 'filterable' : '';
                            const hasFilterClass = hasFilter ? 'has-filter' : '';
                            const filterIcon = col.filterable ? '<span class="filter-icon">▼</span>' : '';
                            return `
                                <th class="prompts-table-th sortable ${filterableClass} ${hasFilterClass} ${isActive ? 'active' : ''}" 
                                    data-sort-column="${col.key}"
                                    data-filter-column="${col.filterable ? col.key : ''}">
                                    <span>${col.label}</span>
                                    <span class="sort-indicator">${arrow}</span>
                                    ${filterIcon}
                                </th>
                            `;
                        }).join('')}
                    </tr>
                </thead>
                <tbody>
                    ${sortedPrompts.length > 0 
                        ? sortedPrompts.map(prompt => renderTableRow(prompt)).join('')
                        : '<tr><td colspan="' + TABLE_COLUMNS.length + '" style="text-align: center; padding: 24px; color: var(--muted);">No prompts match the current filters</td></tr>'
                    }
                </tbody>
            </table>
        `;

        container.innerHTML = tableHtml;

        // Attach sort listeners (left click for sort)
        container.querySelectorAll('.prompts-table-th.sortable').forEach(th => {
            th.addEventListener('click', (e) => {
                // If clicking on filter icon, open filter dropdown
                if (e.target.classList.contains('filter-icon')) {
                    const filterColumn = th.getAttribute('data-filter-column');
                    if (filterColumn && window.PromptFilters) {
                        e.stopPropagation();
                        window.PromptFilters.openFilterDropdown(filterColumn, th);
                    }
                    return;
                }
                const column = th.getAttribute('data-sort-column');
                handleSortClick(column, container, onEditClick);
            });
        });

        // Attach edit button listeners
        container.querySelectorAll('[data-action="edit-prompt"]').forEach(button => {
            button.addEventListener('click', () => {
                const promptId = button.getAttribute('data-prompt-id');
                if (onEditClick) onEditClick(promptId);
            });
        });
        
        // Update active filters display
        if (window.PromptFilters) {
            window.PromptFilters.updateActiveFiltersDisplay();
        }
    }

    /**
     * Apply column filters to prompts
     */
    function applyColumnFilters(prompts, columnFilters) {
        if (!columnFilters || Object.keys(columnFilters).length === 0) {
            return prompts;
        }

        return prompts.filter(prompt => {
            for (const [column, values] of Object.entries(columnFilters)) {
                if (!values || values.length === 0) continue;
                
                let promptValue;
                if (column === 'client_display') {
                    promptValue = resolveClientDisplay(prompt);
                } else {
                    promptValue = prompt[column];
                }
                
                if (promptValue == null) promptValue = '';
                promptValue = String(promptValue);
                
                if (!values.includes(promptValue)) {
                    return false;
                }
            }
            return true;
        });
    }

    /**
     * Get unique values for a column from all prompts
     */
    function getColumnUniqueValues(column) {
        const prompts = state.get('prompts') || [];
        const values = new Set();
        
        prompts.forEach(prompt => {
            let value;
            if (column === 'client_display') {
                value = resolveClientDisplay(prompt);
            } else {
                value = prompt[column];
            }
            
            if (value != null && value !== '') {
                values.add(String(value));
            }
        });
        
        return Array.from(values).sort();
    }

    /**
     * Render a single table row
     */
    function renderTableRow(prompt) {
        const statusBadge = getStatusBadgeCompact(prompt.status);
        const typeBadge = getTypeBadgeCompact(prompt.prompt_type || 'system');
        const clientDisplay = resolveClientDisplay(prompt);
        const clientBadge = getClientDisplayBadge(clientDisplay);
        const updatedAt = prompt.updated_at ? new Date(prompt.updated_at).toLocaleDateString() : '—';

        return `
            <tr class="prompts-table-row" data-prompt-id="${prompt.id}">
                <td class="prompts-table-td prompts-table-name">
                    <span class="prompt-name-text">${DOM.escapeHtml(prompt.name)}</span>
                </td>
                <td class="prompts-table-td prompts-table-version">v${prompt.version}</td>
                <td class="prompts-table-td">${statusBadge}</td>
                <td class="prompts-table-td">${typeBadge}</td>
                <td class="prompts-table-td prompts-table-purpose">${DOM.escapeHtml(prompt.prompt_purpose || '—')}</td>
                <td class="prompts-table-td prompts-table-client">${clientBadge}</td>
                <td class="prompts-table-td prompts-table-model">${DOM.escapeHtml(prompt.llm_model || '—')}</td>
                <td class="prompts-table-td prompts-table-date">${updatedAt}</td>
                <td class="prompts-table-td prompts-table-actions">
                    <button class="btn btn-secondary btn-sm" data-action="edit-prompt" data-prompt-id="${prompt.id}">Edit</button>
                </td>
            </tr>
        `;
    }

    /**
     * Sort prompts array
     */
    function sortPrompts(prompts, column, direction) {
        const multiplier = direction === 'asc' ? 1 : -1;

        return prompts.sort((a, b) => {
            let aVal = column === 'client_display' ? resolveClientDisplay(a) : a[column];
            let bVal = column === 'client_display' ? resolveClientDisplay(b) : b[column];

            // Handle null/undefined
            if (aVal == null) aVal = '';
            if (bVal == null) bVal = '';

            // Handle dates
            if (column === 'updated_at' || column === 'created_at') {
                aVal = aVal ? new Date(aVal).getTime() : 0;
                bVal = bVal ? new Date(bVal).getTime() : 0;
            }
            // Handle numbers
            else if (column === 'version') {
                aVal = Number(aVal) || 0;
                bVal = Number(bVal) || 0;
            }
            // Handle strings
            else if (typeof aVal === 'string') {
                aVal = aVal.toLowerCase();
                bVal = bVal.toLowerCase();
            }

            if (aVal < bVal) return -1 * multiplier;
            if (aVal > bVal) return 1 * multiplier;
            return 0;
        });
    }

    /**
     * Handle sort column click
     */
    function handleSortClick(column, container, onEditClick) {
        const currentColumn = state.get('tableSortColumn');
        const currentDirection = state.get('tableSortDirection');

        // Toggle direction if same column, otherwise default to desc
        let newDirection = 'desc';
        if (column === currentColumn) {
            newDirection = currentDirection === 'desc' ? 'asc' : 'desc';
        }

        state.set('tableSortColumn', column);
        state.set('tableSortDirection', newDirection);

        // Re-render table
        renderPromptsTable(container, onEditClick);
    }

    /**
     * Compact status badge for table view
     */
    function getStatusBadgeCompact(status) {
        const styles = {
            live: { bg: '#f0fff4', border: '#c6f6d5', color: '#22543d' },
            test: { bg: '#fffbf0', border: '#fbd38d', color: '#744210' },
            archived: { bg: '#f7fafc', border: '#e2e8f0', color: '#4a5568' }
        };

        const style = styles[status] || styles.archived;
        return `<span class="status-badge-compact" style="background: ${style.bg}; border: 1px solid ${style.border}; color: ${style.color};">${status}</span>`;
    }

    /**
     * Compact type badge for table view
     */
    function getTypeBadgeCompact(promptType) {
        const styles = {
            system: { bg: '#e6f3ff', border: '#b3d9ff', color: '#004085' },
            helper: { bg: '#fff4e6', border: '#ffd9b3', color: '#663c00' }
        };

        const style = styles[promptType] || styles.system;
        const label = promptType === 'helper' ? 'Helper' : 'System';
        return `<span class="type-badge-compact" style="background: ${style.bg}; border: 1px solid ${style.border}; color: ${style.color};">${label}</span>`;
    }

    /**
     * Client display badge for table view
     */
    function getClientDisplayBadge(clientDisplay) {
        if (clientDisplay === 'Not Client Facing') {
            return `<span class="client-display-badge" style="background: #f7fafc; border: 1px solid #e2e8f0; color: #718096;">${DOM.escapeHtml(clientDisplay)}</span>`;
        }
        if (clientDisplay === 'General') {
            return `<span class="client-display-badge" style="background: #f0fff4; border: 1px solid #c6f6d5; color: #22543d;">${DOM.escapeHtml(clientDisplay)}</span>`;
        }
        return `<span class="client-display-badge" style="background: #e6f3ff; border: 1px solid #b3d9ff; color: #004085;">${DOM.escapeHtml(clientDisplay)}</span>`;
    }

    /**
     * Get status badge HTML
     * @param {string} status - Status value
     * @returns {string} HTML for status badge
     */
    function getStatusBadge(status) {
        const styles = {
            live: { bg: '#f0fff4', border: '#c6f6d5', color: '#22543d' },
            test: { bg: '#fffbf0', border: '#fbd38d', color: '#744210' },
            archived: { bg: '#f7fafc', border: '#e2e8f0', color: '#4a5568' }
        };

        const style = styles[status] || styles.archived;
        return `<span class="client-chip" style="background: ${style.bg}; border-color: ${style.border}; color: ${style.color};">${status.toUpperCase()}</span>`;
    }

    /**
     * Get prompt type badge HTML
     * @param {string} promptType - Prompt type ('system' or 'helper')
     * @returns {string} HTML for type badge
     */
    function getTypeBadge(promptType) {
        const styles = {
            system: { bg: '#e6f3ff', border: '#b3d9ff', color: '#004085' },
            helper: { bg: '#fff4e6', border: '#ffd9b3', color: '#663c00' }
        };

        const style = styles[promptType] || styles.system;
        const label = promptType === 'helper' ? 'Helper' : 'System';
        return `<span class="client-chip" style="background: ${style.bg}; border-color: ${style.border}; color: ${style.color};">${label}</span>`;
    }

    // Export
    window.PromptListRenderer = {
        renderPrompts,
        getStatusBadge,
        getTypeBadge,
        getColumnUniqueValues,
        TABLE_COLUMNS
    };
})();
