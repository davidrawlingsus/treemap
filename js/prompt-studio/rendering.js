/**
 * Prompt Studio rendering functions — builds step cards and output panels.
 */

/**
 * Render a step card into the editor panel.
 * @param {Object} step - Pipeline step object
 * @param {number} index - Step position
 * @returns {HTMLElement}
 */
export function renderStepCard(step, index) {
    const card = document.createElement('section');
    card.className = 'prompt-step';
    card.dataset.stepId = step.id;

    const isContext = step.type === 'context';
    const hasUserPrompt = !isContext;

    card.innerHTML = `
        ${index > 0 ? '<div class="step-wire"></div>' : ''}
        <div class="prompt-step-header">
            <h3>
                <span class="step-number">${index + 1}</span>
                <span class="step-type-badge ${step.type}">${step.type}</span>
            </h3>
            <button class="btn-delete-step" data-action="delete-step" data-step-id="${step.id}" title="Delete step">&times;</button>
        </div>
        <div class="step-version-bar">
            <select class="version-select" data-step-id="${step.id}" data-action="select-version">
                <option value="">Hardcoded default</option>
            </select>
            <span class="dirty-indicator" data-step-id="${step.id}"></span>
            <div class="save-dropdown" data-step-id="${step.id}">
                <button class="save-dropdown-btn" type="button" data-step-id="${step.id}">Save &#9662;</button>
                <div class="save-dropdown-menu" data-step-id="${step.id}">
                    <button type="button" data-action="save-new" data-step-id="${step.id}">Save New Version</button>
                    <button type="button" data-action="overwrite" data-step-id="${step.id}">Overwrite Current</button>
                    <button type="button" data-action="set-live" data-step-id="${step.id}">Set Selected Live</button>
                </div>
            </div>
        </div>
        <label class="prompt-textarea-label">System Prompt</label>
        <textarea class="prompt-textarea" data-step-id="${step.id}" data-field="systemPrompt" rows="5">${escapeHtml(step.systemPrompt || '')}</textarea>
        ${hasUserPrompt ? `
            <label class="prompt-textarea-label">User Prompt Template</label>
            <textarea class="prompt-textarea" data-step-id="${step.id}" data-field="userPrompt" rows="5">${escapeHtml(step.userPrompt || '')}</textarea>
        ` : `
            <label class="prompt-textarea-label">Page Text (auto-fetched)</label>
            <textarea class="prompt-textarea readonly" data-step-id="${step.id}" data-field="pageText" rows="3" readonly placeholder="Page text will appear after running this step"></textarea>
        `}
        <div class="step-actions">
            <button class="btn-play" data-action="run-step" data-step-id="${step.id}">
                <span class="play-icon">&#9654;</span>
                <span class="spinner"></span>
                Run
            </button>
            <span class="step-elapsed" data-step-id="${step.id}"></span>
            <span class="step-tokens" data-step-id="${step.id}" style="display:none; font-size:12px; color:var(--muted); margin-left:4px;"></span>
        </div>
    `;
    return card;
}

/**
 * Render an output panel for a step.
 * @param {Object} step - Pipeline step object
 * @returns {HTMLElement}
 */
export function renderOutputPanel(step) {
    const panel = document.createElement('section');
    panel.className = 'output-panel empty';
    panel.dataset.stepId = step.id;

    panel.innerHTML = `
        <div class="output-panel-header">
            <h3>
                <span class="step-type-badge ${step.type}">${step.type}</span>
                Output
            </h3>
            <button class="btn-copy-output" data-step-id="${step.id}" title="Copy to clipboard" style="display:none">Copy</button>
        </div>
        <div class="output-meta" data-step-id="${step.id}"></div>
        <div class="output-summary" data-step-id="${step.id}" style="display:none"></div>
        <div class="output-body" data-step-id="${step.id}">
            <span class="output-placeholder">Run this step to see output.</span>
        </div>
    `;
    return panel;
}

/**
 * Update an output panel with step results.
 * @param {HTMLElement} panel - Output panel element
 * @param {Object} step - Pipeline step with output
 */
export function updateOutputPanel(panel, step) {
    const copyBtn = panel.querySelector('.btn-copy-output');

    if (!step.output) {
        panel.classList.add('empty');
        panel.querySelector('.output-body').innerHTML = '<span class="output-placeholder">Run this step to see output.</span>';
        panel.querySelector('.output-meta').textContent = '';
        if (copyBtn) copyBtn.style.display = 'none';
        const summary = panel.querySelector('.output-summary');
        if (summary) summary.style.display = 'none';
        return;
    }

    panel.classList.remove('empty');
    if (copyBtn) copyBtn.style.display = '';
    const meta = panel.querySelector('.output-meta');
    meta.textContent = step.elapsedSeconds ? `${step.elapsedSeconds}s` : '';

    const body = panel.querySelector('.output-body');
    const summaryEl = panel.querySelector('.output-summary');

    if (step.type === 'context') {
        if (summaryEl) summaryEl.style.display = 'none';
        body.innerHTML = `<pre class="output-json">${highlightJson(step.output)}</pre>`;
    } else if (step.type === 'code') {
        const coded = step.output.coded_reviews || [];
        const stats = step.output.stats || {};
        const noMatches = step.output.no_matches || [];
        if (summaryEl) {
            summaryEl.style.display = 'flex';
            summaryEl.innerHTML = `
                <span class="stat">Coded: <span class="stat-value">${coded.length}</span></span>
                <span class="stat">No-match: <span class="stat-value">${noMatches.length}</span></span>
                <span class="stat">Rate: <span class="stat-value">${((stats.no_match_rate || 0) * 100).toFixed(1)}%</span></span>
            `;
        }
        body.innerHTML = renderCodeOutput(step.output);
    } else if (step.type === 'discover' || step.type === 'refine') {
        if (summaryEl) summaryEl.style.display = 'none';
        body.innerHTML = renderCodebookOutput(step.output, step.type);
    } else {
        if (summaryEl) summaryEl.style.display = 'none';
        body.innerHTML = `<pre class="output-json">${highlightJson(step.output)}</pre>`;
    }
}

/**
 * Populate the version dropdown for a step.
 * @param {HTMLElement} card - Step card element
 * @param {Object} step - Pipeline step with promptVersions
 */
export function updateVersionDropdown(card, step) {
    const select = card.querySelector('.version-select');
    if (!select) return;

    const currentVal = select.value;
    select.innerHTML = '<option value="">Hardcoded default</option>';
    (step.promptVersions || []).forEach(v => {
        const opt = document.createElement('option');
        opt.value = v.id;
        opt.textContent = `v${v.version} (${v.status})`;
        select.appendChild(opt);
    });

    if (step.selectedVersionId) {
        select.value = step.selectedVersionId;
    } else if (currentVal) {
        select.value = currentVal;
    }
}

/**
 * Set the dirty indicator visibility.
 */
export function setDirtyIndicator(stepId, isDirty) {
    const indicator = document.querySelector(`.dirty-indicator[data-step-id="${stepId}"]`);
    if (indicator) {
        indicator.classList.toggle('visible', isDirty);
    }
}

/**
 * Render a codebook (discover/refine) as collapsible category cards.
 */
function renderCodebookOutput(output, stepType) {
    const categories = output.categories || [];
    const version = output.codebook_version || '';
    const totalThemes = categories.reduce((sum, c) => sum + (c.themes || []).length, 0);

    let html = `<div class="output-structured">`;
    html += `<div class="output-stat-row">
        <span class="stat">Version: <span class="stat-value">${escapeHtml(version)}</span></span>
        <span class="stat">Categories: <span class="stat-value">${categories.length}</span></span>
        <span class="stat">Themes: <span class="stat-value">${totalThemes}</span></span>
    </div>`;

    if (stepType === 'refine' && output.changelog?.length) {
        html += `<details class="output-details"><summary>Changelog (${output.changelog.length} changes)</summary>`;
        html += `<div class="output-details-body">`;
        output.changelog.forEach(c => {
            html += `<div class="changelog-item"><span class="changelog-action">${escapeHtml(c.action)}</span> ${escapeHtml(c.rationale || '')}</div>`;
        });
        html += `</div></details>`;
    }

    categories.forEach(cat => {
        const themes = cat.themes || [];
        html += `<details class="output-details" open>
            <summary><strong>${escapeHtml(cat.category)}</strong> (${themes.length} themes)</summary>
            <div class="output-details-body">`;
        themes.forEach(t => {
            html += `<div class="theme-card">
                <div class="theme-header">
                    <span class="theme-label">${escapeHtml(t.label)}</span>
                    <span class="theme-sentiment ${t.sentiment_direction || ''}">${escapeHtml(t.sentiment_direction || '')}</span>
                    <span class="theme-count">${t.review_count || 0} reviews</span>
                </div>
                <div class="theme-desc">${escapeHtml(t.description || '')}</div>
                ${t.example_verbatims?.length ? `<div class="theme-verbatims">${t.example_verbatims.slice(0, 3).map(v => `<div class="theme-verbatim">"${escapeHtml(v)}"</div>`).join('')}</div>` : ''}
            </div>`;
        });
        html += `</div></details>`;
    });

    html += `<details class="output-details"><summary>Raw JSON</summary>
        <pre class="output-json">${highlightJson(output)}</pre>
    </details>`;
    html += `</div>`;
    return html;
}

/**
 * Render code step output with summary stats and collapsible reviews.
 */
function renderCodeOutput(output) {
    const coded = output.coded_reviews || [];
    const stats = output.stats || {};
    const noMatches = output.no_matches || [];
    const freq = stats.theme_frequency || {};

    // Top themes by frequency
    const topThemes = Object.entries(freq).sort((a, b) => b[1] - a[1]).slice(0, 10);

    let html = `<div class="output-structured">`;

    if (topThemes.length) {
        html += `<details class="output-details" open><summary>Top Themes</summary><div class="output-details-body">`;
        topThemes.forEach(([code, count]) => {
            html += `<div class="theme-freq-row"><span class="theme-freq-code">${escapeHtml(code)}</span><span class="theme-freq-bar" style="width:${Math.min(100, (count / coded.length) * 100 * 3)}%"></span><span class="theme-freq-count">${count}</span></div>`;
        });
        html += `</div></details>`;
    }

    if (noMatches.length) {
        html += `<details class="output-details"><summary>No-match Reviews (${noMatches.length})</summary><div class="output-details-body">`;
        noMatches.slice(0, 20).forEach(r => {
            html += `<div class="no-match-row">${escapeHtml(r.respondent_id || '')} — ${escapeHtml(r.no_match_reason || 'no reason')}</div>`;
        });
        html += `</div></details>`;
    }

    html += `<details class="output-details"><summary>All Coded Reviews (${coded.length})</summary>
        <pre class="output-json">${highlightJson(output)}</pre>
    </details>`;

    html += `</div>`;
    return html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Syntax-highlight a JSON string with colored spans.
 */
export function highlightJson(obj) {
    const raw = JSON.stringify(obj, null, 2);
    return escapeHtml(raw)
        .replace(/"([^"]+)"(?=\s*:)/g, '<span class="json-key">"$1"</span>')
        .replace(/:\s*"([^"]*?)"/g, ': <span class="json-string">"$1"</span>')
        .replace(/:\s*(\d+\.?\d*)/g, ': <span class="json-number">$1</span>')
        .replace(/:\s*(true|false)/g, ': <span class="json-bool">$1</span>')
        .replace(/:\s*(null)/g, ': <span class="json-null">$1</span>');
}
