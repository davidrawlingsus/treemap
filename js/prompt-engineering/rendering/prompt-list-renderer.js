/**
 * Prompt List Renderer Module
 * Handles rendering of the prompts list with version history
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

    /**
     * Render prompts list
     * @param {HTMLElement} container - Container element
     * @param {Function} onEditClick - Callback when edit button is clicked
     * @param {Function} onVersionChange - Callback when version selector changes
     */
    function renderPrompts(container, onEditClick, onVersionChange) {
        if (!container) return;

        const prompts = state.get('prompts');

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
        getTypeBadge
    };
})();
