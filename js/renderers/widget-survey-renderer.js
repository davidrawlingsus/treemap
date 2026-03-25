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

export function renderSurveyEditor(container, { survey, onSave, onBack }) {
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

                <!-- Save button -->
                <div style="margin-top:16px;padding-top:16px;border-top:1px solid #c9ccd0;display:flex;justify-content:flex-end;gap:8px;">
                    <button class="btn btn-primary" id="saveBtn">Save draft</button>
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

        let inputHtml = '';
        if (q.answer_type === 'choice_list' && q.options?.length) {
            inputHtml = q.options.map(opt => `
                <div style="padding:8px 12px;margin-bottom:6px;border:1px solid #e2e8f0;border-radius:8px;font-size:13px;color:#303030;cursor:default;">
                    <span style="margin-right:8px;color:#c9ccd0;">&#9675;</span>${escapeHtml(opt)}
                </div>
            `).join('');
        } else if (q.answer_type === 'multi_line_text') {
            inputHtml = `<textarea style="width:100%;padding:8px 12px;border:1px solid #c9ccd0;border-radius:6px;font-size:13px;min-height:60px;resize:none;color:#8c9196;box-sizing:border-box;" disabled placeholder="Your answer..."></textarea>`;
        } else {
            inputHtml = `<input type="text" style="width:100%;padding:8px 12px;border:1px solid #c9ccd0;border-radius:6px;font-size:13px;color:#8c9196;box-sizing:border-box;" disabled placeholder="Your answer..." />`;
        }

        const previewTitle = container.querySelector('#widgetTitle')?.value || '';
        const previewSubmitLabel = container.querySelector('#submitLabel')?.value || 'Submit';
        const isLast = step >= total - 1;

        viewport.innerHTML = `
            <div style="background:#fff;border-radius:12px 12px 0 0;box-shadow:0 -4px 20px rgba(0,0,0,0.15);padding:0;width:100%;max-width:380px;overflow:hidden;">
                <div style="padding:20px 20px 0;">
                    ${previewTitle ? `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                        <span style="font-size:15px;font-weight:600;color:#303030;">${escapeHtml(previewTitle)}</span>` : `<div style="display:flex;justify-content:flex-end;margin-bottom:12px;">`}
                        <span style="color:#8c9196;cursor:pointer;font-size:18px;">&times;</span>
                    </div>
                    ${total > 1 ? `<div style="font-size:11px;color:#8c9196;margin-bottom:12px;">Question ${step + 1} of ${total}</div>` : ''}
                    <div style="font-size:14px;font-weight:500;color:#303030;margin-bottom:12px;">${escapeHtml(q.title || 'Question text...')}${q.is_required ? '<span style="color:#b42318;margin-left:2px;">*</span>' : ''}</div>
                    ${inputHtml}
                </div>
                <div style="display:flex;justify-content:space-between;padding:16px 20px;border-top:1px solid #f0f2f4;margin-top:12px;">
                    ${step > 0 ? '<button style="padding:6px 14px;border:1px solid #c9ccd0;border-radius:6px;background:#fff;font-size:13px;color:#303030;cursor:default;">Back</button>' : '<div></div>'}
                    <button style="padding:6px 14px;border:none;border-radius:6px;background:#303030;font-size:13px;color:#fff;cursor:default;">${isLast ? escapeHtml(previewSubmitLabel) : 'Next'}</button>
                </div>
            </div>
        `;
    }

    // ── Wire up ──
    renderQuestions();
    renderRules();
    renderPreview();

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

    // Save
    container.querySelector('#saveBtn')?.addEventListener('click', () => {
        const title = container.querySelector('#surveyTitle')?.value?.trim();
        if (!title) return;

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

        const payload = {
            title,
            description: container.querySelector('#surveyDesc')?.value?.trim() || null,
            status: 'active',
            draft_version: {
                settings: { widget_title: widgetTitle, submit_label: submitLabel },
                url_targeting: { mode: urlMode, patterns },
                trigger_rules: { type: triggerType, delay_ms: triggerType === 'delay' ? delayMs : null },
                frequency: { mode: freqMode, days: freqMode === 'every_n_days' ? freqDays : null },
                questions: editorQuestions,
                display_rules: editorRules,
            },
        };
        onSave(payload);
    });
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
