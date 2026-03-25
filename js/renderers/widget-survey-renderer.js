import { escapeHtml } from '/js/utils/dom.js';

export function renderStatus(element, message, type = 'success') {
    if (!element) return;
    if (!message) {
        element.textContent = '';
        element.style.display = 'none';
        element.classList.remove('success', 'error');
        return;
    }
    element.textContent = message;
    element.style.display = 'block';
    element.classList.remove('success', 'error');
    element.classList.add(type);
    setTimeout(() => { element.style.display = 'none'; }, 4000);
}

// ── Survey List View ──────────────────────────────────────────────

export function renderSurveyList(container, { surveys, installStatus, onNew, onEdit, onPublish, onUnpublish, onDelete, onViewResponses, onShowEmbed }) {
    if (!container) return;
    container.className = 'ws';

    const installBadge = installStatus?.is_installed
        ? '<span class="badge badge-success">Script Installed</span>'
        : '<span class="badge badge-muted">Script Not Detected</span>';

    const installedPages = (installStatus?.pages || [])
        .map(p => `<span class="installed-page">${escapeHtml(p.page_url)}</span>`)
        .join('');

    const surveyCards = surveys.length === 0
        ? '<div class="empty-state">No popup surveys yet. Create your first one!</div>'
        : surveys.map(s => {
            const isActive = s.status === 'active' && s.active_version_id;
            const statusBadge = isActive
                ? '<span class="badge badge-live">Live</span>'
                : s.active_version_id
                    ? '<span class="badge badge-muted">Inactive</span>'
                    : '<span class="badge badge-draft">Draft</span>';

            return `
                <article class="survey-card" data-id="${s.id}">
                    <div class="survey-card-header">
                        <h3>${escapeHtml(s.title)}</h3>
                        ${statusBadge}
                    </div>
                    ${s.description ? `<p class="survey-card-desc">${escapeHtml(s.description)}</p>` : ''}
                    <div class="survey-card-stats">
                        <span class="stat"><strong>${s.impression_count}</strong> impressions</span>
                        <span class="stat"><strong>${s.response_count}</strong> responses</span>
                        ${s.impression_count > 0 ? `<span class="stat"><strong>${(s.response_count / s.impression_count * 100).toFixed(1)}%</strong> rate</span>` : ''}
                    </div>
                    <div class="survey-card-actions">
                        <button class="btn btn-sm" data-action="edit" data-id="${s.id}">Edit</button>
                        <button class="btn btn-sm" data-action="responses" data-id="${s.id}">Responses</button>
                        ${isActive
                            ? `<button class="btn btn-sm btn-warning" data-action="unpublish" data-id="${s.id}">Unpublish</button>`
                            : `<button class="btn btn-sm btn-primary" data-action="publish" data-id="${s.id}">Publish</button>`
                        }
                        <button class="btn btn-sm btn-danger" data-action="delete" data-id="${s.id}">Delete</button>
                    </div>
                </article>
            `;
        }).join('');

    container.innerHTML = `
        <div class="survey-list-header">
            <h2>Popup Surveys</h2>
            <div class="survey-list-actions">
                <button class="btn btn-secondary" id="embedCodeBtn">Embed Code</button>
                <button class="btn btn-primary" id="newSurveyBtn">+ New Survey</button>
            </div>
        </div>
        <div class="installation-status">
            ${installBadge}
            ${installedPages ? `<div class="installed-pages">${installedPages}</div>` : ''}
        </div>
        <div class="survey-cards">${surveyCards}</div>
    `;

    container.querySelector('#newSurveyBtn')?.addEventListener('click', onNew);
    container.querySelector('#embedCodeBtn')?.addEventListener('click', onShowEmbed);
    container.querySelectorAll('[data-action]').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = parseInt(btn.dataset.id, 10);
            const action = btn.dataset.action;
            if (action === 'edit') onEdit(id);
            else if (action === 'publish') onPublish(id);
            else if (action === 'unpublish') onUnpublish(id);
            else if (action === 'delete') onDelete(id);
            else if (action === 'responses') onViewResponses(id);
        });
    });
}

// ── Survey Editor (two-panel with preview) ────────────────────────

export function renderSurveyEditor(container, { survey, onSave, onSaveAndPublish, onBack }) {
    if (!container) return;
    container.className = 'ws';

    const draft = survey?.draft_version || survey?.active_version || null;
    const draftSettings = draft?.settings || {};
    const urlTargeting = draft?.url_targeting || { mode: 'contains', patterns: [] };
    const triggerRules = draft?.trigger_rules || { type: 'immediate', delay_ms: 3000 };
    const frequency = draft?.frequency || { mode: 'until_answered', days: 7 };
    const questions = draft?.questions || [];

    // State
    let editorQuestions = questions.map((q, i) => ({ ...q, position: q.position ?? i }));
    let editorRules = (draft?.display_rules || []).map(r => ({
        target_question_key: r.target_question_key,
        source_question_key: r.source_question_key,
        operator: r.operator,
        comparison_value: r.comparison_value,
    }));
    let activeTab = 'questions';
    let previewStep = 0;
    let displayType = draftSettings.display_type || 'popover';
    let slideupPosition = draftSettings.slideup_position || 'bottom-right';
    let theme = draftSettings.theme || 'light';
    let buttonColor = draftSettings.button_color || '#4F46E5';

    container.innerHTML = `
        <div style="display:flex;align-items:flex-start;gap:0;">
            <!-- LEFT: Editor panel -->
            <div style="flex:1 1 0;min-width:0;border-right:1px solid #c9ccd0;padding:0 24px 0 0;">
                <div class="editor-header">
                    <button class="btn" id="backBtn">
                        <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14"><path fill-rule="evenodd" d="M11.78 5.47a.75.75 0 0 1 0 1.06L8.31 10l3.47 3.47a.75.75 0 1 1-1.06 1.06l-4-4a.75.75 0 0 1 0-1.06l4-4a.75.75 0 0 1 1.06 0Z" clip-rule="evenodd"/></svg>
                        Surveys
                    </button>
                    ${survey ? `<span class="badge ${survey.status === 'active' ? 'badge-live' : 'badge-draft'}">${survey.status === 'active' ? 'Live' : 'Draft'}</span>` : ''}
                </div>

                <!-- Survey meta card -->
                <div class="card">
                    <div class="card-section">
                        <div class="field-group">
                            <label class="field-label">Survey name</label>
                            <input id="surveyTitle" class="field-input" type="text" placeholder="e.g. Post-purchase feedback" value="${escapeHtml(survey?.title || '')}" />
                        </div>
                        <div class="field-group">
                            <label class="field-label">Description <span class="field-label-optional">(internal, optional)</span></label>
                            <textarea id="surveyDesc" class="field-input field-input-textarea" rows="2" placeholder="Internal note about this survey">${escapeHtml(survey?.description || '')}</textarea>
                        </div>
                        <div class="field-group">
                            <label class="field-label">Popup heading <span class="field-label-optional">(shown to visitors)</span></label>
                            <input id="widgetTitle" class="field-input" type="text" placeholder="e.g. Quick question before you go" value="${escapeHtml(draftSettings.widget_title || '')}" />
                        </div>
                        <div class="field-group">
                            <label class="field-label">Submit button text</label>
                            <input id="submitLabel" class="field-input" type="text" placeholder="Submit" value="${escapeHtml(draftSettings.submit_label || '')}" />
                        </div>
                    </div>
                </div>

                <!-- Tabs -->
                <div class="tabs" role="tablist">
                    <button class="tab active" data-tab="questions">Questions</button>
                    <button class="tab" data-tab="display">Display</button>
                    <button class="tab" data-tab="logic">Conditional logic</button>
                    <button class="tab" data-tab="settings">Targeting & Trigger</button>
                </div>

                <!-- Questions panel -->
                <div class="tab-panel" data-panel="questions">
                    <div id="questionList" class="question-stack"></div>
                    <div id="questionsEmpty" class="empty-questions" ${editorQuestions.length > 0 ? 'hidden' : ''}>
                        <p>No questions yet. Add your first question below.</p>
                    </div>
                    <button type="button" class="btn btn-add-question" id="addQuestionBtn">+ Add question</button>
                </div>

                <!-- Display panel -->
                <div class="tab-panel" data-panel="display" hidden>
                    <div class="settings-group">
                        <div class="settings-group-label">Display type</div>
                        <div style="display:flex;gap:12px;margin-bottom:16px;">
                            <label class="display-type-card ${(draftSettings.display_type || 'popover') === 'popover' ? 'active' : ''}" style="flex:1;cursor:pointer;border:2px solid ${(draftSettings.display_type || 'popover') === 'popover' ? '#2c5cc5' : '#c9ccd0'};border-radius:8px;padding:16px;text-align:center;transition:border-color 120ms;">
                                <input type="radio" name="displayType" value="popover" ${(draftSettings.display_type || 'popover') === 'popover' ? 'checked' : ''} style="display:none;" />
                                <div style="font-size:32px;margin-bottom:8px;">
                                    <svg width="48" height="36" viewBox="0 0 48 36" fill="none"><rect x="1" y="1" width="46" height="34" rx="4" stroke="#8c9196" stroke-width="1.5" fill="#f1f2f4"/><rect x="10" y="6" width="28" height="24" rx="3" fill="#fff" stroke="#303030" stroke-width="1.5"/><rect x="14" y="11" width="20" height="2" rx="1" fill="#c9ccd0"/><rect x="14" y="16" width="16" height="2" rx="1" fill="#c9ccd0"/><rect x="28" y="22" width="8" height="4" rx="2" fill="#4F46E5"/></svg>
                                </div>
                                <div style="font-size:13px;font-weight:600;color:#303030;">Popover</div>
                                <div style="font-size:11px;color:#616161;">Centered modal with overlay</div>
                            </label>
                            <label class="display-type-card ${draftSettings.display_type === 'slideup' ? 'active' : ''}" style="flex:1;cursor:pointer;border:2px solid ${draftSettings.display_type === 'slideup' ? '#2c5cc5' : '#c9ccd0'};border-radius:8px;padding:16px;text-align:center;transition:border-color 120ms;">
                                <input type="radio" name="displayType" value="slideup" ${draftSettings.display_type === 'slideup' ? 'checked' : ''} style="display:none;" />
                                <div style="font-size:32px;margin-bottom:8px;">
                                    <svg width="48" height="36" viewBox="0 0 48 36" fill="none"><rect x="1" y="1" width="46" height="34" rx="4" stroke="#8c9196" stroke-width="1.5" fill="#f1f2f4"/><rect x="24" y="14" width="22" height="21" rx="3" fill="#fff" stroke="#303030" stroke-width="1.5"/><rect x="28" y="19" width="14" height="2" rx="1" fill="#c9ccd0"/><rect x="28" y="24" width="10" height="2" rx="1" fill="#c9ccd0"/><rect x="36" y="29" width="6" height="3" rx="1.5" fill="#4F46E5"/></svg>
                                </div>
                                <div style="font-size:13px;font-weight:600;color:#303030;">Slide-up</div>
                                <div style="font-size:11px;color:#616161;">Corner widget, Hotjar-style</div>
                            </label>
                        </div>
                    </div>
                    <div id="slideupPositionGroup" class="settings-group" ${(draftSettings.display_type || 'popover') !== 'slideup' ? 'hidden' : ''}>
                        <div class="settings-group-label">Position</div>
                        <label class="radio-option"><input type="radio" name="slideupPosition" value="bottom-right" ${(draftSettings.slideup_position || 'bottom-right') === 'bottom-right' ? 'checked' : ''}> Bottom right</label>
                        <label class="radio-option"><input type="radio" name="slideupPosition" value="bottom-left" ${draftSettings.slideup_position === 'bottom-left' ? 'checked' : ''}> Bottom left</label>
                    </div>
                    <div class="settings-group" style="margin-top:16px;">
                        <div class="settings-group-label">Theme</div>
                        <div style="display:flex;gap:12px;margin-bottom:16px;">
                            <label style="flex:1;cursor:pointer;border:2px solid ${(draftSettings.theme || 'light') === 'light' ? '#2c5cc5' : '#c9ccd0'};border-radius:8px;padding:14px;text-align:center;transition:border-color 120ms;background:#fff;" class="theme-card">
                                <input type="radio" name="theme" value="light" ${(draftSettings.theme || 'light') === 'light' ? 'checked' : ''} style="display:none;" />
                                <div style="width:32px;height:22px;margin:0 auto 8px;background:#fff;border:2px solid #e2e8f0;border-radius:4px;"></div>
                                <div style="font-size:13px;font-weight:600;color:#303030;">Light</div>
                            </label>
                            <label style="flex:1;cursor:pointer;border:2px solid ${draftSettings.theme === 'dark' ? '#2c5cc5' : '#c9ccd0'};border-radius:8px;padding:14px;text-align:center;transition:border-color 120ms;background:#fff;" class="theme-card">
                                <input type="radio" name="theme" value="dark" ${draftSettings.theme === 'dark' ? 'checked' : ''} style="display:none;" />
                                <div style="width:32px;height:22px;margin:0 auto 8px;background:#1a1a1a;border:2px solid #1a1a1a;border-radius:4px;"></div>
                                <div style="font-size:13px;font-weight:600;color:#303030;">Dark</div>
                            </label>
                        </div>
                    </div>
                    <div class="settings-group" style="margin-top:16px;">
                        <div class="settings-group-label">Button color</div>
                        <div id="colorSwatches" style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;">
                            ${['#4F46E5','#2563EB','#0891B2','#059669','#D97706','#DC2626','#7C3AED','#DB2777','#1a1a1a','#475569'].map(c => `
                                <button type="button" data-swatch="${c}" style="width:32px;height:32px;border-radius:8px;border:2px solid ${(draftSettings.button_color || '#4F46E5') === c ? '#303030' : 'transparent'};background:${c};cursor:pointer;transition:border-color 120ms;outline:none;" title="${c}"></button>
                            `).join('')}
                        </div>
                        <div style="display:flex;align-items:center;gap:8px;">
                            <input type="color" id="buttonColor" value="${draftSettings.button_color || '#4F46E5'}" style="width:34px;height:34px;padding:2px;border:1px solid #c9ccd0;border-radius:6px;cursor:pointer;background:#fff;" title="Custom color" />
                            <input type="text" id="buttonColorHex" class="field-input" value="${draftSettings.button_color || '#4F46E5'}" style="max-width:100px;font-family:'SF Mono',monospace;font-size:13px;" placeholder="#4F46E5" />
                        </div>
                    </div>
                </div>

                <!-- Logic panel -->
                <div class="tab-panel" data-panel="logic" hidden>
                    <p class="panel-description">Show or hide questions based on how visitors answer previous questions.</p>
                    <div id="ruleList" class="rule-stack"></div>
                    <div style="margin-top:12px">
                        <button class="btn btn-secondary" id="addRuleBtn">Add rule</button>
                    </div>
                </div>

                <!-- Settings panel -->
                <div class="tab-panel" data-panel="settings" hidden>
                    <div class="card" style="box-shadow:none;border:none;">
                        <div class="card-section" style="padding:0 0 16px;">
                            <div class="settings-group">
                                <div class="settings-group-label">URL Targeting</div>
                                <div class="field-group">
                                    <label class="field-label">Mode</label>
                                    <select id="urlMode" class="field-select" style="max-width:200px;">
                                        <option value="contains" ${urlTargeting.mode === 'contains' ? 'selected' : ''}>URL Contains</option>
                                        <option value="regex" ${urlTargeting.mode === 'regex' ? 'selected' : ''}>Regex</option>
                                    </select>
                                </div>
                                <div class="field-group">
                                    <label class="field-label">URL Patterns <span class="field-label-optional">(one per line, empty = all pages)</span></label>
                                    <textarea id="urlPatterns" class="field-input field-input-textarea" rows="3" placeholder="/thank-you&#10;/success">${escapeHtml(urlTargeting.patterns.join('\n'))}</textarea>
                                </div>
                            </div>
                        </div>
                        <div class="card-section" style="padding:16px 0;border-top:1px solid #c9ccd0;">
                            <div class="settings-group">
                                <div class="settings-group-label">Trigger</div>
                                <label class="radio-option"><input type="radio" name="triggerType" value="immediate" ${triggerRules.type === 'immediate' ? 'checked' : ''}> Immediate</label>
                                <label class="radio-option"><input type="radio" name="triggerType" value="delay" ${triggerRules.type === 'delay' ? 'checked' : ''}> Delay <input type="number" id="delayMs" class="field-input field-input-inline" value="${triggerRules.delay_ms || 3000}" min="0" step="500"> ms</label>
                                <label class="radio-option"><input type="radio" name="triggerType" value="exit_intent" ${triggerRules.type === 'exit_intent' ? 'checked' : ''}> Exit intent</label>
                            </div>
                        </div>
                        <div class="card-section" style="padding:16px 0;border-top:1px solid #c9ccd0;">
                            <div class="settings-group">
                                <div class="settings-group-label">Frequency</div>
                                <label class="radio-option"><input type="radio" name="freqMode" value="once" ${frequency.mode === 'once' ? 'checked' : ''}> Show once</label>
                                <label class="radio-option"><input type="radio" name="freqMode" value="until_answered" ${frequency.mode === 'until_answered' ? 'checked' : ''}> Show until answered</label>
                                <label class="radio-option"><input type="radio" name="freqMode" value="every_n_days" ${frequency.mode === 'every_n_days' ? 'checked' : ''}> Every <input type="number" id="freqDays" class="field-input field-input-inline" value="${frequency.days || 7}" min="1"> days</label>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Success screen -->
                <div class="card" style="margin-top:16px;">
                    <div class="card-section">
                        <div class="settings-group-label" style="margin-bottom:12px;">Success screen</div>
                        <div class="field-group">
                            <label class="field-label">Heading</label>
                            <input id="successHeading" class="field-input" type="text" placeholder="Thank you!" value="${escapeHtml(draftSettings.success_heading || '')}" />
                        </div>
                        <div class="field-group">
                            <label class="field-label">Message</label>
                            <textarea id="successMessage" class="field-input field-input-textarea" rows="2" placeholder="Your feedback has been submitted.">${escapeHtml(draftSettings.success_message || '')}</textarea>
                        </div>
                        <div class="field-group">
                            <label class="field-label">Auto-dismiss after <span class="field-label-optional">(seconds, 0 = manual close only)</span></label>
                            <input id="successDismiss" class="field-input" type="number" min="0" max="30" value="${draftSettings.success_dismiss_seconds ?? 3}" style="max-width:80px;" />
                        </div>
                    </div>
                </div>

                <!-- Save actions -->
                <div style="margin-top:16px;padding-top:16px;border-top:1px solid #c9ccd0;display:flex;justify-content:flex-end;gap:8px;">
                    ${survey?.status === 'active' ? `
                        <button class="btn btn-primary" id="publishBtn">Publish changes</button>
                    ` : `
                        <div style="position:relative;display:inline-flex;" id="splitBtnWrap">
                            <button class="btn btn-primary" id="saveBtn" style="border-radius:6px 0 0 6px;">Save draft</button>
                            <button class="btn btn-primary" id="splitToggle" style="border-radius:0 6px 6px 0;border-left:1px solid rgba(255,255,255,0.3);padding:7px 8px;" title="More options">&#9660;</button>
                            <div id="splitMenu" style="display:none;position:absolute;bottom:100%;right:0;margin-bottom:4px;background:#fff;border:1px solid #c9ccd0;border-radius:6px;box-shadow:0 4px 12px rgba(0,0,0,0.12);overflow:hidden;min-width:160px;z-index:10;">
                                <button class="btn" id="saveAndPublishBtn" style="width:100%;border:none;border-radius:0;justify-content:flex-start;padding:10px 14px;font-size:13px;">Save &amp; Publish</button>
                            </div>
                        </div>
                    `}
                </div>
            </div>

            <!-- RIGHT: Preview panel -->
            <div style="flex:0 0 420px;position:sticky;top:80px;padding:0 0 0 24px;">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                    <span style="font-size:13px;font-weight:600;color:#616161;text-transform:uppercase;letter-spacing:0.05em;">Preview</span>
                    <div style="display:flex;gap:8px;">
                        <button class="btn btn-sm" id="prevStepBtn" style="padding:4px 8px;">&#8249;</button>
                        <span id="stepIndicator" style="font-size:12px;color:#616161;line-height:28px;">1 / 1</span>
                        <button class="btn btn-sm" id="nextStepBtn" style="padding:4px 8px;">&#8250;</button>
                    </div>
                </div>
                <div id="previewViewport" style="background:#f1f2f4;border-radius:12px;padding:20px;min-height:300px;display:flex;align-items:flex-end;justify-content:center;">
                    <!-- Popup preview rendered here -->
                </div>
            </div>
        </div>
    `;

    // ── Tab switching ──
    container.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            container.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            activeTab = tab.dataset.tab;
            container.querySelectorAll('.tab-panel').forEach(p => {
                p.hidden = p.dataset.panel !== activeTab;
            });
        });
    });

    // ── Display type switching ──
    container.querySelectorAll('input[name="displayType"]').forEach(radio => {
        radio.addEventListener('change', () => {
            displayType = radio.value;
            // Update card borders
            container.querySelectorAll('.display-type-card').forEach(card => {
                const isActive = card.querySelector('input').value === displayType;
                card.style.borderColor = isActive ? '#2c5cc5' : '#c9ccd0';
                card.classList.toggle('active', isActive);
            });
            // Show/hide position options
            const posGroup = container.querySelector('#slideupPositionGroup');
            if (posGroup) posGroup.hidden = displayType !== 'slideup';
            renderPreview();
        });
    });
    container.querySelectorAll('input[name="slideupPosition"]').forEach(radio => {
        radio.addEventListener('change', () => {
            slideupPosition = radio.value;
            renderPreview();
        });
    });
    container.querySelectorAll('input[name="theme"]').forEach(radio => {
        radio.addEventListener('change', () => {
            theme = radio.value;
            container.querySelectorAll('.theme-card').forEach(card => {
                const isActive = card.querySelector('input').value === theme;
                card.style.borderColor = isActive ? '#2c5cc5' : '#c9ccd0';
            });
            renderPreview();
        });
    });
    const colorPicker = container.querySelector('#buttonColor');
    const colorHex = container.querySelector('#buttonColorHex');
    function updateSwatchBorders() {
        container.querySelectorAll('[data-swatch]').forEach(s => {
            s.style.borderColor = s.dataset.swatch === buttonColor ? '#303030' : 'transparent';
        });
    }
    function setButtonColor(c) {
        buttonColor = c;
        if (colorPicker) colorPicker.value = c;
        if (colorHex) colorHex.value = c;
        updateSwatchBorders();
        renderPreview();
    }
    container.querySelectorAll('[data-swatch]').forEach(s => {
        s.addEventListener('click', () => setButtonColor(s.dataset.swatch));
    });
    if (colorPicker && colorHex) {
        colorPicker.addEventListener('input', () => setButtonColor(colorPicker.value));
        colorHex.addEventListener('input', () => {
            const v = colorHex.value.trim();
            if (/^#[0-9a-fA-F]{6}$/.test(v)) setButtonColor(v);
        });
    }

    // ── Questions ──
    function renderQuestions() {
        const list = container.querySelector('#questionList');
        const empty = container.querySelector('#questionsEmpty');
        if (!list) return;
        list.innerHTML = '';
        if (empty) empty.hidden = editorQuestions.length > 0;

        editorQuestions.forEach((q, idx) => {
            const card = document.createElement('div');
            card.className = 'question-card';
            card.innerHTML = `
                <div class="question-card-header">
                    <span class="question-num">Q${idx + 1}</span>
                    <input class="q-title-input" type="text" placeholder="Ask a question…" value="${escapeHtml(q.title || '')}" data-idx="${idx}" />
                    <button class="btn btn-sm btn-danger" data-remove-q="${idx}" title="Delete question">&times;</button>
                </div>
                <div class="type-chips">
                    <button type="button" class="chip ${q.answer_type === 'single_line_text' ? 'active' : ''}" data-set-type="single_line_text" data-idx="${idx}">Short text</button>
                    <button type="button" class="chip ${q.answer_type === 'multi_line_text' ? 'active' : ''}" data-set-type="multi_line_text" data-idx="${idx}">Long text</button>
                    <button type="button" class="chip ${q.answer_type === 'choice_list' ? 'active' : ''}" data-set-type="choice_list" data-idx="${idx}">Multiple choice</button>
                </div>
                <div class="options-editor" ${q.answer_type !== 'choice_list' ? 'hidden' : ''}>
                    <div class="options-list"></div>
                    <button type="button" class="btn btn-sm" style="align-self:flex-start;" data-add-option="${idx}">+ Add option</button>
                </div>
                <div class="question-card-footer">
                    <label class="toggle-row">
                        <span class="toggle-label">Required</span>
                        <input type="checkbox" class="toggle-input" data-toggle-required="${idx}" ${q.is_required ? 'checked' : ''} />
                    </label>
                </div>
            `;

            // Render options
            const optList = card.querySelector('.options-list');
            (q.options || []).forEach((opt, optIdx) => {
                const row = document.createElement('div');
                row.className = 'option-row';
                row.innerHTML = `
                    <span class="option-bullet">&bull;</span>
                    <input class="field-input option-input" type="text" value="${escapeHtml(opt)}" placeholder="Option ${optIdx + 1}" />
                    <button class="btn btn-sm btn-danger" data-remove-opt="${optIdx}" data-q="${idx}" style="padding:2px 6px;">&times;</button>
                `;
                row.querySelector('input').addEventListener('input', e => {
                    editorQuestions[idx].options[optIdx] = e.target.value;
                    renderPreview();
                });
                row.querySelector('[data-remove-opt]').addEventListener('click', () => {
                    editorQuestions[idx].options.splice(optIdx, 1);
                    renderQuestions();
                    renderPreview();
                });
                optList.appendChild(row);
            });

            // Wire events
            card.querySelector('.q-title-input').addEventListener('input', e => {
                editorQuestions[idx].title = e.target.value;
                renderPreview();
            });
            card.querySelector('.q-title-input').addEventListener('focus', () => {
                previewStep = idx;
                renderPreview();
            });
            card.querySelectorAll('[data-set-type]').forEach(chip => {
                chip.addEventListener('click', () => {
                    editorQuestions[idx].answer_type = chip.dataset.setType;
                    if (chip.dataset.setType === 'choice_list' && (!editorQuestions[idx].options || editorQuestions[idx].options.length === 0)) {
                        editorQuestions[idx].options = ['Option 1', 'Option 2'];
                    }
                    renderQuestions();
                    renderPreview();
                });
            });
            card.querySelector(`[data-add-option="${idx}"]`)?.addEventListener('click', () => {
                if (!editorQuestions[idx].options) editorQuestions[idx].options = [];
                editorQuestions[idx].options.push('');
                renderQuestions();
            });
            card.querySelector(`[data-toggle-required="${idx}"]`)?.addEventListener('change', e => {
                editorQuestions[idx].is_required = e.target.checked;
            });
            card.querySelector(`[data-remove-q="${idx}"]`)?.addEventListener('click', () => {
                editorQuestions.splice(idx, 1);
                if (previewStep >= editorQuestions.length) previewStep = Math.max(0, editorQuestions.length - 1);
                renderQuestions();
                renderPreview();
            });

            list.appendChild(card);
        });
    }

    // ── Rules ──
    function renderRules() {
        const list = container.querySelector('#ruleList');
        if (!list) return;
        const qKeys = editorQuestions.map(q => q.question_key || q.title).filter(Boolean);
        list.innerHTML = '';

        editorRules.forEach((r, idx) => {
            const card = document.createElement('div');
            card.className = 'rule-card';
            card.innerHTML = `
                <div class="rule-row">
                    <span>If</span>
                    <select data-rule="source" data-idx="${idx}">
                        ${qKeys.map(k => `<option value="${escapeHtml(k)}" ${r.source_question_key === k ? 'selected' : ''}>${escapeHtml(k)}</option>`).join('')}
                    </select>
                    <span>equals</span>
                    <input type="text" data-rule="value" data-idx="${idx}" value="${escapeHtml(r.comparison_value || '')}" placeholder="value" />
                    <span>then show</span>
                    <select data-rule="target" data-idx="${idx}">
                        ${qKeys.map(k => `<option value="${escapeHtml(k)}" ${r.target_question_key === k ? 'selected' : ''}>${escapeHtml(k)}</option>`).join('')}
                    </select>
                </div>
                <div class="rule-actions">
                    <button class="btn btn-sm btn-danger" data-remove-rule="${idx}">Remove</button>
                </div>
            `;
            card.querySelectorAll('[data-rule]').forEach(el => {
                el.addEventListener('input', () => {
                    if (el.dataset.rule === 'source') editorRules[idx].source_question_key = el.value;
                    else if (el.dataset.rule === 'target') editorRules[idx].target_question_key = el.value;
                    else if (el.dataset.rule === 'value') editorRules[idx].comparison_value = el.value;
                });
            });
            card.querySelector(`[data-remove-rule="${idx}"]`)?.addEventListener('click', () => {
                editorRules.splice(idx, 1);
                renderRules();
            });
            list.appendChild(card);
        });
    }

    // ── Preview ──
    function renderPreview() {
        const viewport = container.querySelector('#previewViewport');
        const indicator = container.querySelector('#stepIndicator');
        if (!viewport) return;

        const visible = editorQuestions.filter(q => q.title || q.options?.length);
        const total = visible.length || 1;
        const step = Math.min(previewStep, total - 1);
        const q = visible[step];

        if (indicator) indicator.textContent = `${step + 1} / ${total}`;

        if (!q) {
            viewport.innerHTML = `
                <div style="background:#fff;border-radius:12px;box-shadow:0 -4px 20px rgba(0,0,0,0.15);padding:24px;width:100%;max-width:380px;text-align:center;color:#616161;font-size:14px;">
                    Add a question to see preview
                </div>
            `;
            return;
        }

        // Theme colors
        const isDark = theme === 'dark';
        const bg = isDark ? '#1a1a1a' : '#fff';
        const textColor = isDark ? '#f0f0f0' : '#303030';
        const mutedColor = isDark ? '#a0a0a0' : '#8c9196';
        const borderColor = isDark ? '#333' : '#e2e8f0';
        const inputBg = isDark ? '#2a2a2a' : '#fff';
        const footerBorder = isDark ? '#333' : '#f0f2f4';
        const backBtnBg = isDark ? '#2a2a2a' : '#fff';
        const backBtnBorder = isDark ? '#555' : '#c9ccd0';

        let inputHtml = '';
        if (q.answer_type === 'choice_list' && q.options?.length) {
            inputHtml = q.options.map(opt => `
                <div style="padding:8px 12px;margin-bottom:6px;border:1px solid ${borderColor};border-radius:8px;font-size:13px;color:${textColor};cursor:default;">
                    <span style="margin-right:8px;color:${mutedColor};">&#9675;</span>${escapeHtml(opt)}
                </div>
            `).join('');
        } else if (q.answer_type === 'multi_line_text') {
            inputHtml = `<textarea style="width:100%;padding:8px 12px;border:1px solid ${borderColor};border-radius:6px;font-size:13px;min-height:60px;resize:none;color:${mutedColor};background:${inputBg};box-sizing:border-box;" disabled placeholder="Your answer..."></textarea>`;
        } else {
            inputHtml = `<input type="text" style="width:100%;padding:8px 12px;border:1px solid ${borderColor};border-radius:6px;font-size:13px;color:${mutedColor};background:${inputBg};box-sizing:border-box;" disabled placeholder="Your answer..." />`;
        }

        const previewTitle = container.querySelector('#widgetTitle')?.value || '';
        const previewSubmitLabel = container.querySelector('#submitLabel')?.value || 'Submit';
        const isLast = step >= total - 1;

        // Update viewport alignment based on display type
        if (displayType === 'slideup') {
            viewport.style.alignItems = 'flex-end';
            viewport.style.justifyContent = slideupPosition === 'bottom-left' ? 'flex-start' : 'flex-end';
        } else {
            viewport.style.alignItems = 'center';
            viewport.style.justifyContent = 'center';
        }

        const isSlideup = displayType === 'slideup';
        const cardRadius = isSlideup ? '12px 12px 0 0' : '12px';
        const cardShadow = isSlideup ? '0 2px 16px rgba(0,0,0,0.2)' : '0 -4px 20px rgba(0,0,0,0.15)';
        const cardWidth = isSlideup ? '340px' : '380px';
        const titleSize = isSlideup ? '14px' : '15px';
        const bodyPadding = isSlideup ? '16px 16px 0' : '20px 20px 0';
        const footerPadding = isSlideup ? '12px 16px' : '16px 20px';

        const iconFilter = isDark ? 'filter:invert(0.7);' : '';
        const collapseBtn = isSlideup
            ? `<img src="https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/survey-icons/collapse_icon-RYPksPuuo9v7xJYQPMkpaxgaByqYas.svg" alt="Collapse" style="width:18px;height:18px;cursor:pointer;${iconFilter}" />`
            : `<img src="https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/survey-icons/close_icon-bX0w8aJ2pJgf5aUuXZoEpQHw6dwtFB.svg" alt="Close" style="width:18px;height:18px;cursor:pointer;${iconFilter}" />`;

        viewport.innerHTML = `
            <div style="background:${bg};border-radius:${cardRadius};box-shadow:${cardShadow};padding:0;width:100%;max-width:${cardWidth};overflow:hidden;">
                <div style="padding:${bodyPadding};">
                    ${(previewTitle && step === 0) ? `<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:${isSlideup ? '8px' : '12px'};">
                        <span style="font-size:${titleSize};font-weight:600;color:${textColor};flex:1;margin-right:8px;">${escapeHtml(previewTitle)}</span>` : `<div style="display:flex;justify-content:flex-end;margin-bottom:${isSlideup ? '8px' : '12px'};">`}
                        ${collapseBtn}
                    </div>
                    <div style="font-size:${isSlideup ? '13px' : '14px'};font-weight:500;color:${textColor};margin-bottom:${isSlideup ? '8px' : '12px'};">${escapeHtml(q.title || 'Question text...')}${q.is_required ? '<span style="color:#b42318;margin-left:2px;">*</span>' : ''}</div>
                    ${inputHtml}
                </div>
                <div style="display:flex;justify-content:space-between;padding:${footerPadding};border-top:1px solid ${footerBorder};margin-top:${isSlideup ? '8px' : '12px'};">
                    ${step > 0 ? `<button style="padding:${isSlideup ? '5px 12px' : '6px 14px'};border:1px solid ${backBtnBorder};border-radius:6px;background:${backBtnBg};font-size:13px;color:${textColor};cursor:default;">Back</button>` : '<div></div>'}
                    <button style="padding:${isSlideup ? '5px 12px' : '6px 14px'};border:none;border-radius:6px;background:${buttonColor};font-size:13px;color:#fff;cursor:default;">${isLast ? escapeHtml(previewSubmitLabel) : 'Next'}</button>
                </div>
            </div>
        `;
    }

    // ── Wire up ──
    renderQuestions();
    renderRules();
    renderPreview();

    // Live-reload preview when heading, submit label, or success fields change
    container.querySelector('#widgetTitle')?.addEventListener('input', () => renderPreview());
    container.querySelector('#submitLabel')?.addEventListener('input', () => renderPreview());
    container.querySelector('#successHeading')?.addEventListener('input', () => renderPreview());
    container.querySelector('#successMessage')?.addEventListener('input', () => renderPreview());

    container.querySelector('#backBtn')?.addEventListener('click', onBack);

    container.querySelector('#addQuestionBtn')?.addEventListener('click', () => {
        const idx = editorQuestions.length;
        editorQuestions.push({
            question_key: `q${idx + 1}`,
            title: '',
            answer_type: 'choice_list',
            is_required: false,
            is_enabled: true,
            position: idx,
            options: ['Option 1', 'Option 2'],
            settings: {},
        });
        renderQuestions();
        previewStep = idx;
        renderPreview();
    });

    container.querySelector('#addRuleBtn')?.addEventListener('click', () => {
        const qKeys = editorQuestions.map(q => q.question_key).filter(Boolean);
        if (qKeys.length < 2) return;
        editorRules.push({
            target_question_key: qKeys[1] || '',
            source_question_key: qKeys[0] || '',
            operator: 'equals',
            comparison_value: '',
        });
        renderRules();
    });

    // Preview step controls
    container.querySelector('#prevStepBtn')?.addEventListener('click', () => {
        if (previewStep > 0) { previewStep--; renderPreview(); }
    });
    container.querySelector('#nextStepBtn')?.addEventListener('click', () => {
        if (previewStep < editorQuestions.length - 1) { previewStep++; renderPreview(); }
    });

    // Save helpers
    function collectPayload() {
        const title = container.querySelector('#surveyTitle')?.value?.trim();
        if (!title) return null;

        const urlPatternsRaw = container.querySelector('#urlPatterns')?.value || '';
        const patterns = urlPatternsRaw.split('\n').map(p => p.trim()).filter(Boolean);
        const urlMode = container.querySelector('#urlMode')?.value || 'contains';
        const triggerType = container.querySelector('input[name="triggerType"]:checked')?.value || 'immediate';
        const delayMs = parseInt(container.querySelector('#delayMs')?.value || '3000', 10);
        const freqMode = container.querySelector('input[name="freqMode"]:checked')?.value || 'until_answered';
        const freqDays = parseInt(container.querySelector('#freqDays')?.value || '7', 10);

        editorQuestions.forEach((q, i) => {
            if (!q.question_key) q.question_key = `q${i + 1}`;
            q.position = i;
        });

        const widgetTitle = container.querySelector('#widgetTitle')?.value?.trim() || null;
        const submitLabel = container.querySelector('#submitLabel')?.value?.trim() || null;

        return {
            title,
            description: container.querySelector('#surveyDesc')?.value?.trim() || null,
            status: 'active',
            draft_version: {
                settings: {
                    widget_title: widgetTitle, submit_label: submitLabel,
                    display_type: displayType, slideup_position: slideupPosition,
                    theme, button_color: buttonColor,
                    success_heading: container.querySelector('#successHeading')?.value?.trim() || null,
                    success_message: container.querySelector('#successMessage')?.value?.trim() || null,
                    success_dismiss_seconds: parseInt(container.querySelector('#successDismiss')?.value || '3', 10),
                },
                url_targeting: { mode: urlMode, patterns },
                trigger_rules: { type: triggerType, delay_ms: triggerType === 'delay' ? delayMs : null },
                frequency: { mode: freqMode, days: freqMode === 'every_n_days' ? freqDays : null },
                questions: editorQuestions,
                display_rules: editorRules,
            },
        };
    }

    function canPublish() {
        const title = container.querySelector('#surveyTitle')?.value?.trim();
        if (!title) return false;
        if (editorQuestions.length === 0) return false;
        if (!editorQuestions.some(q => q.title?.trim())) return false;
        return true;
    }

    // Live survey: single "Publish changes" button
    container.querySelector('#publishBtn')?.addEventListener('click', () => {
        const payload = collectPayload();
        if (!payload) return;
        onSaveAndPublish(payload);
    });

    // New/draft survey: split button
    container.querySelector('#saveBtn')?.addEventListener('click', () => {
        const payload = collectPayload();
        if (payload) onSave(payload);
    });

    // Split button toggle
    const splitToggle = container.querySelector('#splitToggle');
    const splitMenu = container.querySelector('#splitMenu');
    if (splitToggle && splitMenu) {
        splitToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            splitMenu.style.display = splitMenu.style.display === 'none' ? 'block' : 'none';
        });
        document.addEventListener('click', () => { splitMenu.style.display = 'none'; }, { once: false });

        const sapBtn = container.querySelector('#saveAndPublishBtn');
        if (sapBtn) {
            function updateSapState() {
                sapBtn.disabled = !canPublish();
                sapBtn.style.opacity = canPublish() ? '1' : '0.4';
                sapBtn.style.cursor = canPublish() ? 'pointer' : 'not-allowed';
            }
            updateSapState();
            // Re-check on question/title changes
            container.addEventListener('input', updateSapState);

            sapBtn.addEventListener('click', () => {
                if (!canPublish()) return;
                splitMenu.style.display = 'none';
                const payload = collectPayload();
                if (payload) onSaveAndPublish(payload);
            });
        }
    }
}

// ── Response Viewer ───────────────────────────────────────────────

export function renderResponseViewer(container, { survey, responses, stats, onBack, onLoadMore }) {
    if (!container) return;
    container.className = 'ws';

    const items = responses?.items || [];
    const total = responses?.total || 0;

    const clarityBanner = stats?.detected_clarity_project_id
        ? `<div class="clarity-banner">Clarity detected: <strong>${escapeHtml(stats.detected_clarity_project_id)}</strong></div>`
        : '';

    const statsHtml = `
        <div class="response-stats">
            <span class="stat"><strong>${stats?.impression_count || 0}</strong> impressions</span>
            <span class="stat"><strong>${stats?.response_count || 0}</strong> responses</span>
            ${stats?.response_rate != null ? `<span class="stat"><strong>${stats.response_rate}%</strong> response rate</span>` : ''}
        </div>
    `;

    const rows = items.map(item => {
        const answersHtml = (item.answers || []).map(a =>
            `<div class="answer-row"><strong>${escapeHtml(a.question_key || '?')}:</strong> ${escapeHtml(a.answer_text || JSON.stringify(a.answer_json || ''))}</div>`
        ).join('');

        const clarityBtn = (item.clarity_session_id && item.clarity_project_id)
            ? `<a href="https://clarity.microsoft.com/projects/view/${encodeURIComponent(item.clarity_project_id)}/session/${encodeURIComponent(item.clarity_session_id)}" target="_blank" rel="noopener" class="btn btn-sm btn-clarity">Watch Session</a>`
            : '';

        const ts = item.submitted_at ? new Date(item.submitted_at).toLocaleString() : '';

        return `
            <tr>
                <td>${escapeHtml(ts)}</td>
                <td>${escapeHtml(item.site_domain || '')}</td>
                <td>${answersHtml}</td>
                <td>${clarityBtn}</td>
            </tr>
        `;
    }).join('');

    container.innerHTML = `
        <div class="editor-header">
            <button class="btn" id="backBtn">
                <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14"><path fill-rule="evenodd" d="M11.78 5.47a.75.75 0 0 1 0 1.06L8.31 10l3.47 3.47a.75.75 0 1 1-1.06 1.06l-4-4a.75.75 0 0 1 0-1.06l4-4a.75.75 0 0 1 1.06 0Z" clip-rule="evenodd"/></svg>
                Surveys
            </button>
            <h2>Responses: ${escapeHtml(survey?.title || '')}</h2>
        </div>
        ${clarityBanner}
        ${statsHtml}
        <table class="responses-table">
            <thead>
                <tr>
                    <th>Submitted</th>
                    <th>Site</th>
                    <th>Answers</th>
                    <th>Session</th>
                </tr>
            </thead>
            <tbody>${rows || '<tr><td colspan="4" class="empty-state">No responses yet</td></tr>'}</tbody>
        </table>
        ${items.length < total ? `<button class="btn btn-secondary" id="loadMoreBtn" style="margin-top:12px;">Load more (${total - items.length} remaining)</button>` : ''}
    `;

    container.querySelector('#backBtn')?.addEventListener('click', onBack);
    container.querySelector('#loadMoreBtn')?.addEventListener('click', () => onLoadMore(items.length));
}

// ── Embed Code ────────────────────────────────────────────────────

export function renderEmbedCode(container, { apiBaseUrl, onBack }) {
    if (!container) return;
    container.className = 'ws';

    const snippet = `<script>
  window.VizualizdSurvey = {
    apiKey: "YOUR_API_KEY",
    apiBaseUrl: "${apiBaseUrl}"
  };
</script>
<script src="${apiBaseUrl}/static/widget/vizualizd-survey.js" defer></script>`;

    container.innerHTML = `
        <div class="editor-header">
            <button class="btn" id="backBtn">
                <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14"><path fill-rule="evenodd" d="M11.78 5.47a.75.75 0 0 1 0 1.06L8.31 10l3.47 3.47a.75.75 0 1 1-1.06 1.06l-4-4a.75.75 0 0 1 0-1.06l4-4a.75.75 0 0 1 1.06 0Z" clip-rule="evenodd"/></svg>
                Surveys
            </button>
            <h2>Embed Code</h2>
        </div>
        <p style="font-size:14px;color:#616161;margin-bottom:4px;">Add this snippet to your website. The survey will automatically show based on your URL targeting and trigger settings.</p>
        <div class="embed-code-block">
            <pre><code>${escapeHtml(snippet)}</code></pre>
            <button class="btn btn-sm" id="copyEmbedBtn">Copy</button>
        </div>
        <p style="font-size:12px;color:#8c9196;">Replace YOUR_API_KEY with your client API key from the API Keys page.</p>
    `;

    container.querySelector('#backBtn')?.addEventListener('click', onBack);
    container.querySelector('#copyEmbedBtn')?.addEventListener('click', () => {
        navigator.clipboard.writeText(snippet).then(() => {
            const btn = container.querySelector('#copyEmbedBtn');
            if (btn) { btn.textContent = 'Copied!'; setTimeout(() => { btn.textContent = 'Copy'; }, 2000); }
        });
    });
}

// ── Installation Status ───────────────────────────────────────────

export function renderInstallationStatus(container, status) {
    if (!container || !status) return;
    const badge = status.is_installed
        ? '<span class="badge badge-success">Installed</span>'
        : '<span class="badge badge-muted">Not detected</span>';
    container.innerHTML = badge;
}
