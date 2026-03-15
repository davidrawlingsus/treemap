// ─── SESSION & API ───────────────────────────────────────────────────────────
async function getSessionToken() {
  if (window.shopify?.idToken) return window.shopify.idToken();
  if (window.__SHOPIFY_DEV_SESSION_TOKEN) return window.__SHOPIFY_DEV_SESSION_TOKEN;
  throw new Error("Missing Shopify session token in embedded app context.");
}

async function api(path, method = "GET", body = null) {
  const token = await getSessionToken();
  const res = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: body ? JSON.stringify(body) : undefined,
  });
  const payload = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(payload?.detail || `Request failed (${res.status})`);
  return payload;
}

// ─── STATE ───────────────────────────────────────────────────────────────────
const state = {
  surveys: [],
  templates: [],
  activeSurvey: null,
  draft: null,           // { questions: [], display_rules: [] }
  savedSnapshot: null,   // JSON string — dirty check baseline
  view: "list",
  activeTab: "questions",
  previewStep: 0,
  previewDevice: "mobile",
};

function isDirty() {
  if (!state.savedSnapshot || !state.draft) return false;
  return JSON.stringify(collectSnapshot()) !== state.savedSnapshot;
}

function collectSnapshot() {
  return {
    title: el("surveyTitle")?.value?.trim() ?? "",
    description: el("surveyDescription")?.value?.trim() ?? "",
    templateKey: el("templateSelect")?.value ?? "",
    startsAt: el("startsAt")?.value ?? "",
    endsAt: el("endsAt")?.value ?? "",
    questions: (state.draft?.questions ?? []).map(q => ({ ...q })),
    display_rules: (state.draft?.display_rules ?? []).map(r => ({ ...r })),
  };
}

function takeSnapshot() {
  state.savedSnapshot = JSON.stringify(collectSnapshot());
}

// ─── DOM HELPER ──────────────────────────────────────────────────────────────
function el(id) { return document.getElementById(id); }

// ─── VIEW ROUTER ─────────────────────────────────────────────────────────────
function navigate(view, surveyId = null) {
  state.view = view;
  el("view-list").hidden = view !== "list";
  el("view-editor").hidden = view !== "editor";

  if (view === "list") {
    updateTitleBarForList();
    closeSaveBar();
    renderSurveyGrid();
  } else if (view === "editor" && surveyId) {
    loadSurvey(surveyId).catch(err => showToast(err.message || "Failed to load survey.", "error"));
  }
}

// ─── TITLE BAR ───────────────────────────────────────────────────────────────
function updateTitleBarForList() {
  const tb = document.querySelector("ui-title-bar");
  if (!tb) return;
  tb.setAttribute("title", "Surveys");
  tb.innerHTML = `<button variant="primary" id="ab-create-btn">Create survey</button>`;
  el("ab-create-btn")?.addEventListener("click", handleCreateSurvey);
}

function updateTitleBarForEditor(survey) {
  const tb = document.querySelector("ui-title-bar");
  if (!tb) return;
  const isLive = Boolean(survey?.active_version_id);
  tb.setAttribute("title", survey?.title || "Survey editor");
  tb.innerHTML = isLive
    ? `<button id="ab-unpublish-btn">Unpublish</button>`
    : `<button variant="primary" id="ab-publish-btn">Publish</button>`;
  el("ab-publish-btn")?.addEventListener("click", handlePublish);
  el("ab-unpublish-btn")?.addEventListener("click", handleUnpublish);
}

// ─── SAVE BAR ────────────────────────────────────────────────────────────────
function syncSaveBar() {
  const bar = el("saveBar");
  if (!bar) return;
  isDirty() ? bar.setAttribute("open", "") : bar.removeAttribute("open");
}

function closeSaveBar() {
  el("saveBar")?.removeAttribute("open");
}

// ─── TOAST ───────────────────────────────────────────────────────────────────
function showToast(message, type = "info") {
  const region = el("toastRegion");
  if (!region) return;
  const toast = document.createElement("div");
  toast.className = `toast toast--${type}`;
  toast.textContent = message;
  region.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add("toast--visible"));
  setTimeout(() => {
    toast.classList.remove("toast--visible");
    toast.addEventListener("transitionend", () => toast.remove(), { once: true });
  }, 3500);
}

// ─── LIST VIEW ───────────────────────────────────────────────────────────────
async function loadSurveys() {
  const payload = await api("/api/admin/surveys");
  state.surveys = payload.surveys || [];
}

function renderSurveyGrid() {
  const grid = el("surveyGrid");
  const empty = el("emptyState");
  if (!grid) return;
  grid.innerHTML = "";
  const noSurveys = !state.surveys.length;
  if (empty) empty.hidden = !noSurveys;
  if (noSurveys) return;
  state.surveys.forEach(survey => grid.appendChild(buildSurveyCard(survey)));
}

function buildSurveyCard(survey) {
  const isLive = Boolean(survey.active_version_id);
  const card = document.createElement("div");
  card.className = "survey-card";
  card.innerHTML = `
    <div class="survey-card__top">
      <span class="badge ${isLive ? "badge--live" : "badge--draft"}">${isLive ? "Live" : "Draft"}</span>
    </div>
    <h3 class="survey-card__title">${escHtml(survey.title || "Untitled survey")}</h3>
    <p class="survey-card__meta">${survey.description ? escHtml(survey.description) : '<span style="color:var(--color-text-disabled)">No description</span>'}</p>
    <div class="survey-card__actions">
      <button class="btn btn--secondary btn--sm">Edit survey</button>
    </div>
  `;
  card.querySelector(".btn").addEventListener("click", () => navigate("editor", survey.id));
  return card;
}

// ─── EDITOR: LOAD ────────────────────────────────────────────────────────────
async function loadSurvey(surveyId) {
  const payload = await api(`/api/admin/surveys/${surveyId}`);
  applyToEditor(payload.survey);
}

function applyToEditor(survey) {
  state.activeSurvey = survey;
  const src = survey.draft_version || survey.active_version || null;
  const isLive = Boolean(survey.active_version_id);

  state.draft = {
    questions: (src?.questions ?? []).map(q => ({ ...q, options: q.options ?? [] })),
    display_rules: (src?.display_rules ?? []).map(r => ({ ...r })),
  };

  // Populate form fields
  el("surveyTitle").value = survey.title ?? "";
  el("surveyDescription").value = survey.description ?? "";
  el("templateSelect").value = src?.template_key ?? "";
  el("startsAt").value = src?.starts_at ? new Date(src.starts_at).toISOString().slice(0, 16) : "";
  el("endsAt").value = src?.ends_at ? new Date(src.ends_at).toISOString().slice(0, 16) : "";

  // Status badge
  const badge = el("editorStatusBadge");
  if (badge) {
    badge.textContent = isLive ? "Live" : "Draft";
    badge.className = `badge ${isLive ? "badge--live" : "badge--draft"}`;
    badge.hidden = false;
  }

  updateTitleBarForEditor(survey);
  takeSnapshot();
  closeSaveBar();
  state.previewStep = 0;
  switchTab("questions");
  renderQuestions();
  renderRules();
  renderPreview();
}

// ─── EDITOR: DIRTY TRACKING ──────────────────────────────────────────────────
function markDirty() {
  syncSaveBar();
  renderPreview();
}

function collectDraftFromForm() {
  const isLive = Boolean(state.activeSurvey?.active_version_id);
  return {
    title: el("surveyTitle")?.value?.trim() ?? "",
    status: isLive ? "active" : "inactive",
    description: el("surveyDescription")?.value?.trim() ?? "",
    draft_version: {
      template_key: el("templateSelect")?.value || null,
      starts_at: el("startsAt")?.value ? new Date(el("startsAt").value).toISOString() : null,
      ends_at: el("endsAt")?.value ? new Date(el("endsAt").value).toISOString() : null,
      settings: {},
      questions: (state.draft?.questions ?? []).map((q, i) => ({
        ...q,
        question_key: `q${i + 1}`,
        position: i,
      })),
      display_rules: state.draft?.display_rules ?? [],
    },
  };
}

async function ensureSurveyId() {
  if (state.activeSurvey?.id) return state.activeSurvey.id;
  const created = await api("/api/admin/surveys", "POST", collectDraftFromForm());
  if (created?.survey) {
    applyToEditor(created.survey);
    await loadSurveys();
    renderSurveyGrid();
  }
  return created?.survey?.id ?? null;
}

// ─── TABS ────────────────────────────────────────────────────────────────────
function switchTab(tabName) {
  state.activeTab = tabName;
  document.querySelectorAll(".tab").forEach(tab => {
    const active = tab.dataset.tab === tabName;
    tab.classList.toggle("tab--active", active);
    tab.setAttribute("aria-selected", String(active));
  });
  document.querySelectorAll(".tab-panel").forEach(panel => {
    panel.hidden = panel.dataset.panel !== tabName;
  });
  if (tabName === "responses") refreshResponses();
}

// ─── QUESTIONS TAB ───────────────────────────────────────────────────────────
function renderQuestions() {
  const list = el("questionList");
  const empty = el("questionsEmpty");
  if (!list) return;
  list.innerHTML = "";
  const hasQ = state.draft?.questions?.length > 0;
  if (empty) empty.hidden = hasQ;
  if (hasQ) {
    state.draft.questions.forEach((q, idx) => list.appendChild(buildQuestionCard(q, idx)));
  }
}

function buildQuestionCard(q, idx) {
  const card = document.createElement("div");
  card.className = "question-card";
  card.draggable = true;
  card.dataset.index = String(idx);

  card.innerHTML = `
    <div class="question-card__handle" title="Drag to reorder">${ICON_DRAG}</div>
    <div class="question-card__body">
      <div class="question-card__header">
        <span class="question-num">Q${idx + 1}</span>
        <input class="q-title-input" type="text"
          placeholder="Ask a question…"
          value="${escAttr(q.title)}"
          data-action="question-title" />
        <button class="btn btn--icon btn--danger" data-action="remove-question" title="Delete question">
          ${ICON_TRASH}
        </button>
      </div>
      <div class="type-chips" role="group" aria-label="Answer type">
        <button class="chip ${q.answer_type === "single_line_text" ? "chip--active" : ""}"
          data-action="set-type" data-type="single_line_text">
          ${ICON_TEXT}&nbsp;Short text
        </button>
        <button class="chip ${q.answer_type === "multi_line_text" ? "chip--active" : ""}"
          data-action="set-type" data-type="multi_line_text">
          ${ICON_PARAGRAPH}&nbsp;Long text
        </button>
        <button class="chip ${q.answer_type === "choice_list" ? "chip--active" : ""}"
          data-action="set-type" data-type="choice_list">
          ${ICON_LIST}&nbsp;Multiple choice
        </button>
      </div>
      <div class="options-editor" ${q.answer_type !== "choice_list" ? "hidden" : ""}>
        <div class="options-list"></div>
        <button class="btn btn--plain btn--sm" data-action="add-option">+ Add option</button>
      </div>
      <div class="question-card__footer">
        <label class="toggle-row">
          <span class="toggle-label">Required</span>
          <input type="checkbox" class="toggle-input" data-action="toggle-required"
            ${q.is_required ? "checked" : ""} />
        </label>
      </div>
    </div>
  `;

  renderOptionsInCard(card, q, idx);
  wireQuestionCard(card, idx);
  return card;
}

function renderOptionsInCard(cardEl, q, qIdx) {
  const list = cardEl.querySelector(".options-list");
  if (!list) return;
  list.innerHTML = "";
  (q.options ?? []).forEach((opt, optIdx) => {
    const row = document.createElement("div");
    row.className = "option-row";
    row.innerHTML = `
      <span class="option-bullet">•</span>
      <input class="field-input option-input" type="text"
        value="${escAttr(opt)}" placeholder="Option ${optIdx + 1}" />
      <button class="btn btn--icon" data-action="remove-option" data-opt-index="${optIdx}"
        aria-label="Remove option">${ICON_CLOSE}</button>
    `;
    row.querySelector("input").addEventListener("input", e => {
      state.draft.questions[qIdx].options[optIdx] = e.target.value;
      markDirty();
    });
    list.appendChild(row);
  });
}

function wireQuestionCard(card, idx) {
  // Drag and drop
  card.addEventListener("dragstart", e => {
    card.classList.add("is-dragging");
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", String(idx));
  });
  card.addEventListener("dragend", () => card.classList.remove("is-dragging"));
  card.addEventListener("dragover", e => { e.preventDefault(); card.classList.add("drag-over"); });
  card.addEventListener("dragleave", () => card.classList.remove("drag-over"));
  card.addEventListener("drop", e => {
    e.preventDefault();
    card.classList.remove("drag-over");
    const from = Number(e.dataTransfer.getData("text/plain"));
    if (isNaN(from) || from === idx) return;
    const [moved] = state.draft.questions.splice(from, 1);
    state.draft.questions.splice(idx, 0, moved);
    renderQuestions();
    renderRules();
    markDirty();
  });

  // Input: question title
  card.addEventListener("input", e => {
    if (e.target.dataset.action === "question-title") {
      state.draft.questions[idx].title = e.target.value;
      markDirty();
    }
  });

  // Change: required toggle
  card.addEventListener("change", e => {
    if (e.target.dataset.action === "toggle-required") {
      state.draft.questions[idx].is_required = e.target.checked;
      markDirty();
    }
  });

  // Click: remove question, set type, add/remove option
  card.addEventListener("click", e => {
    const target = e.target.closest("[data-action]");
    if (!target) return;
    const action = target.dataset.action;

    if (action === "remove-question") {
      state.draft.questions.splice(idx, 1);
      // Clean up any rules that referenced this question key
      const removedKey = `q${idx + 1}`;
      state.draft.display_rules = state.draft.display_rules.filter(
        r => r.source_question_key !== removedKey && r.target_question_key !== removedKey
      );
      renderQuestions();
      renderRules();
      markDirty();
    } else if (action === "set-type") {
      state.draft.questions[idx].answer_type = target.dataset.type;
      renderQuestions();
      markDirty();
    } else if (action === "add-option") {
      state.draft.questions[idx].options = [...(state.draft.questions[idx].options ?? []), ""];
      renderOptionsInCard(card, state.draft.questions[idx], idx);
      markDirty();
      // Focus the new input
      const inputs = card.querySelectorAll(".option-input");
      inputs[inputs.length - 1]?.focus();
    } else if (action === "remove-option") {
      const optIdx = Number(target.dataset.optIndex);
      state.draft.questions[idx].options.splice(optIdx, 1);
      renderOptionsInCard(card, state.draft.questions[idx], idx);
      markDirty();
    }
  });
}

// ─── LOGIC TAB ───────────────────────────────────────────────────────────────
function renderRules() {
  const list = el("ruleList");
  const empty = el("rulesEmpty");
  if (!list) return;
  list.innerHTML = "";

  // Build key→title map from current draft (keys auto-assigned as q1, q2...)
  const keys = (state.draft?.questions ?? []).map((q, i) => ({
    key: `q${i + 1}`,
    label: q.title ? `Q${i + 1}: ${q.title}` : `Question ${i + 1}`,
  }));

  const hasRules = state.draft?.display_rules?.length > 0;
  if (empty) empty.hidden = hasRules;
  if (!hasRules) return;

  state.draft.display_rules.forEach((rule, idx) => {
    list.appendChild(buildRuleCard(rule, idx, keys));
  });
}

function buildRuleCard(rule, idx, keys) {
  const srcOptions = keys.map(k =>
    `<option value="${escAttr(k.key)}" ${rule.source_question_key === k.key ? "selected" : ""}>${escHtml(k.label)}</option>`
  ).join("");
  const tgtOptions = keys.map(k =>
    `<option value="${escAttr(k.key)}" ${rule.target_question_key === k.key ? "selected" : ""}>${escHtml(k.label)}</option>`
  ).join("");

  const card = document.createElement("div");
  card.className = "rule-card";
  card.innerHTML = `
    <div class="rule-card__row">
      <span class="rule-card__label">If answer to</span>
      <select class="field-select" data-field="source_question_key" style="flex:1;min-width:120px">${srcOptions}</select>
      <span class="rule-card__label">equals</span>
      <input class="field-input" type="text" placeholder="value"
        value="${escAttr(rule.comparison_value)}" data-field="comparison_value" style="flex:0.6;min-width:80px" />
    </div>
    <div class="rule-card__row">
      <span class="rule-card__label">then show</span>
      <select class="field-select" data-field="target_question_key" style="flex:1;min-width:120px">${tgtOptions}</select>
    </div>
    <button class="btn btn--plain btn--danger btn--sm" data-action="remove-rule">Remove rule</button>
  `;

  card.addEventListener("change", e => {
    const field = e.target.dataset.field;
    if (field) { state.draft.display_rules[idx][field] = e.target.value; markDirty(); }
  });
  card.addEventListener("input", e => {
    const field = e.target.dataset.field;
    if (field) { state.draft.display_rules[idx][field] = e.target.value; markDirty(); }
  });
  card.querySelector("[data-action='remove-rule']").addEventListener("click", () => {
    state.draft.display_rules.splice(idx, 1);
    renderRules();
    markDirty();
  });
  return card;
}

// ─── SCHEDULE TAB ────────────────────────────────────────────────────────────
function renderTemplates() {
  const sel = el("templateSelect");
  if (!sel) return;
  const current = sel.value;
  sel.innerHTML = `<option value="">No template</option>` +
    state.templates.map(t =>
      `<option value="${escAttr(t.key)}" ${current === t.key ? "selected" : ""}>${escHtml(t.name)}</option>`
    ).join("");
}

// ─── RESPONSES TAB ───────────────────────────────────────────────────────────
async function refreshResponses() {
  if (!state.activeSurvey?.id) return;
  try {
    const payload = await api(`/api/admin/surveys/${state.activeSurvey.id}/responses`);
    renderResponses(payload.items || []);
  } catch (err) {
    showToast("Could not load responses.", "error");
  }
}

function renderResponses(items) {
  const list = el("responseList");
  const count = el("responseCount");
  if (!list) return;
  if (count) count.textContent = items.length
    ? `${items.length} response${items.length !== 1 ? "s" : ""}`
    : "No responses yet";
  list.innerHTML = "";
  if (!items.length) {
    list.innerHTML = `<div style="padding:20px 24px;color:var(--color-text-muted);font-size:13px">No responses collected yet.</div>`;
    return;
  }
  items.forEach(row => {
    const div = document.createElement("div");
    div.className = "response-row";
    div.innerHTML = `
      <span class="response-id">#${row.id}</span>
      <span class="response-date">${new Date(row.submitted_at).toLocaleString()}</span>
    `;
    list.appendChild(div);
  });
}

// ─── PREVIEW ─────────────────────────────────────────────────────────────────
function renderPreview() {
  const container = el("surveyPreviewCard");
  if (!container) return;

  const questions = state.draft?.questions ?? [];
  const total = questions.length;

  // Clamp step
  if (state.previewStep >= total) state.previewStep = Math.max(0, total - 1);

  // Update step nav
  const indicator = el("previewStepIndicator");
  if (indicator) indicator.textContent = total ? `Step ${state.previewStep + 1} of ${total}` : "No questions";
  el("prevStepBtn")?.toggleAttribute("disabled", state.previewStep <= 0);
  el("nextStepBtn")?.toggleAttribute("disabled", state.previewStep >= total - 1 || total === 0);

  if (!total) {
    container.innerHTML = `<p class="survey-preview__empty">Add questions above to preview your survey here.</p>`;
    return;
  }

  const q = questions[state.previewStep];
  const isLast = state.previewStep === total - 1;
  const surveyTitle = el("surveyTitle")?.value?.trim() || "Quick question";

  let inputHtml;
  if (q.answer_type === "choice_list") {
    const opts = (q.options ?? []).filter(Boolean);
    if (opts.length) {
      inputHtml = `<div class="preview-choices">
        ${opts.map(opt => `
          <label class="preview-choice">
            <input type="radio" name="pq-${state.previewStep}" value="${escAttr(opt)}" />
            <span>${escHtml(opt)}</span>
          </label>
        `).join("")}
      </div>`;
    } else {
      inputHtml = `<p class="preview-hint">Add options to see choices here.</p>`;
    }
  } else if (q.answer_type === "multi_line_text") {
    inputHtml = `<textarea class="preview-textarea" placeholder="Your answer…" rows="3"></textarea>`;
  } else {
    inputHtml = `<input class="preview-text-input" type="text" placeholder="Your answer…" />`;
  }

  container.innerHTML = `
    <p class="preview-survey-label">${escHtml(surveyTitle)}</p>
    <p class="preview-question-text">
      ${escHtml(q.title || "Your question will appear here")}${q.is_required ? '<span class="preview-required">*</span>' : ""}
    </p>
    ${inputHtml}
    <div class="preview-actions">
      ${state.previewStep > 0
        ? `<button class="preview-btn preview-btn--ghost">&larr; Back</button>`
        : ""}
      <button class="preview-btn preview-btn--primary">${isLast ? "Submit" : "Next &rarr;"}</button>
    </div>
  `;
}

// ─── ACTION HANDLERS ─────────────────────────────────────────────────────────
async function handleSave() {
  try {
    const surveyId = await ensureSurveyId();
    if (!surveyId) return;
    await api(`/api/admin/surveys/${surveyId}`, "PUT", collectDraftFromForm());
    await loadSurvey(surveyId);
    takeSnapshot();
    syncSaveBar();
    showToast("Draft saved", "success");
  } catch (err) {
    showToast(err.message || "Save failed.", "error");
  }
}

function handleDiscard() {
  if (state.activeSurvey) applyToEditor(state.activeSurvey);
}

async function handlePublish() {
  try {
    const surveyId = await ensureSurveyId();
    if (!surveyId) return;
    const otherLive = state.surveys.find(s => s.id !== surveyId && Boolean(s.active_version_id));
    if (otherLive) {
      const ok = window.confirm(`Publishing will deactivate "${otherLive.title}". Continue?`);
      if (!ok) return;
    }
    await api(`/api/admin/surveys/${surveyId}/publish`, "POST", {});
    await loadSurvey(surveyId);
    await loadSurveys();
    renderSurveyGrid();
    showToast("Survey is now live", "success");
  } catch (err) {
    showToast(err.message || "Publish failed.", "error");
  }
}

async function handleUnpublish() {
  if (!state.activeSurvey?.id) return;
  const surveyId = state.activeSurvey.id;
  const preserved = {
    questions: (state.draft?.questions ?? []).map(q => ({ ...q })),
    display_rules: (state.draft?.display_rules ?? []).map(r => ({ ...r })),
  };
  try {
    await api(`/api/admin/surveys/${surveyId}/unpublish`, "POST", {});
    await loadSurvey(surveyId);
    if (preserved.questions.length && !(state.draft?.questions?.length)) {
      state.draft = preserved;
      await api(`/api/admin/surveys/${surveyId}`, "PUT", collectDraftFromForm());
      await loadSurvey(surveyId);
    }
    await loadSurveys();
    renderSurveyGrid();
    showToast("Survey turned off", "success");
  } catch (err) {
    showToast(err.message || "Unpublish failed.", "error");
  }
}

async function handleCreateSurvey() {
  try {
    const created = await api("/api/admin/surveys", "POST", {
      title: "New survey",
      status: "inactive",
      description: "",
      draft_version: {
        template_key: null, starts_at: null, ends_at: null,
        settings: {}, questions: [], display_rules: [],
      },
    });
    await loadSurveys();
    navigate("editor", created.survey.id);
  } catch (err) {
    showToast(err.message || "Could not create survey.", "error");
  }
}

// ─── ICONS ───────────────────────────────────────────────────────────────────
const ICON_DRAG = `<svg viewBox="0 0 20 20" fill="currentColor" width="16" height="16" aria-hidden="true"><path d="M7 2a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm6 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zM7 8.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm6 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zM7 15a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm6 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z"/></svg>`;
const ICON_TRASH = `<svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14" aria-hidden="true"><path fill-rule="evenodd" d="M8.5 1A1.5 1.5 0 0 0 7 2.5h-.5A2.5 2.5 0 0 0 4 5v.5H3a.75.75 0 0 0 0 1.5h.5V15A2.5 2.5 0 0 0 6 17.5h8A2.5 2.5 0 0 0 16.5 15V7H17a.75.75 0 0 0 0-1.5h-1V5a2.5 2.5 0 0 0-2.5-2.5H13A1.5 1.5 0 0 0 11.5 1h-3Zm0 1.5h3V3h-3v-.5ZM5.5 5A1 1 0 0 1 6.5 4h7a1 1 0 0 1 1 1v.5h-9V5Zm9 3H5.5v7A1 1 0 0 0 6.5 16h7a1 1 0 0 0 1-1V8ZM8 9.75a.75.75 0 0 1 1.5 0v4.5a.75.75 0 0 1-1.5 0v-4.5Zm3 0a.75.75 0 0 1 1.5 0v4.5a.75.75 0 0 1-1.5 0v-4.5Z" clip-rule="evenodd"/></svg>`;
const ICON_CLOSE = `<svg viewBox="0 0 20 20" fill="currentColor" width="12" height="12" aria-hidden="true"><path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22z"/></svg>`;
const ICON_TEXT = `<svg viewBox="0 0 20 20" fill="currentColor" width="12" height="12" aria-hidden="true"><path d="M3.75 3.5a.75.75 0 0 0 0 1.5H9v11.25a.75.75 0 0 0 1.5 0V5h5.25a.75.75 0 0 0 0-1.5h-12Z"/></svg>`;
const ICON_PARAGRAPH = `<svg viewBox="0 0 20 20" fill="currentColor" width="12" height="12" aria-hidden="true"><path fill-rule="evenodd" d="M3.5 4A.5.5 0 0 1 4 3.5h12a.5.5 0 0 1 0 1H4A.5.5 0 0 1 3.5 4Zm0 4A.5.5 0 0 1 4 7.5h12a.5.5 0 0 1 0 1H4A.5.5 0 0 1 3.5 8Zm0 4a.5.5 0 0 1 .5-.5h12a.5.5 0 0 1 0 1H4a.5.5 0 0 1-.5-.5Zm0 4a.5.5 0 0 1 .5-.5h8a.5.5 0 0 1 0 1H4a.5.5 0 0 1-.5-.5Z" clip-rule="evenodd"/></svg>`;
const ICON_LIST = `<svg viewBox="0 0 20 20" fill="currentColor" width="12" height="12" aria-hidden="true"><path fill-rule="evenodd" d="M4.5 5a1 1 0 1 0 0-2 1 1 0 0 0 0 2Zm2-.75a.75.75 0 0 1 .75-.75h8a.75.75 0 0 1 0 1.5h-8A.75.75 0 0 1 6.5 4.25Zm0 5.5a.75.75 0 0 1 .75-.75h8a.75.75 0 0 1 0 1.5h-8a.75.75 0 0 1-.75-.75Zm0 5.5a.75.75 0 0 1 .75-.75h8a.75.75 0 0 1 0 1.5h-8a.75.75 0 0 1-.75-.75ZM4.5 11a1 1 0 1 0 0-2 1 1 0 0 0 0 2Zm0 5.5a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z" clip-rule="evenodd"/></svg>`;

// ─── UTILS ───────────────────────────────────────────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function escAttr(str) {
  return String(str).replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

// ─── INIT ────────────────────────────────────────────────────────────────────
async function init() {
  // Save bar events (App Bridge fires these on the element itself)
  const saveBar = el("saveBar");
  saveBar?.addEventListener("save", handleSave);
  saveBar?.addEventListener("discard", handleDiscard);
  // Button fallbacks (App Bridge version variance)
  el("ab-save-btn")?.addEventListener("click", handleSave);
  el("ab-discard-btn")?.addEventListener("click", handleDiscard);

  // Create survey
  el("emptyCreateBtn")?.addEventListener("click", handleCreateSurvey);

  // Back to list
  el("backBtn")?.addEventListener("click", () => navigate("list"));

  // Tabs
  document.querySelectorAll(".tab").forEach(tab => {
    tab.addEventListener("click", () => switchTab(tab.dataset.tab));
  });

  // Add question
  el("addQuestionBtn")?.addEventListener("click", () => {
    if (!state.draft) state.draft = { questions: [], display_rules: [] };
    state.draft.questions.push({
      question_key: `q${state.draft.questions.length + 1}`,
      title: "",
      answer_type: "single_line_text",
      is_required: false,
      is_enabled: true,
      options: [],
      settings: {},
    });
    renderQuestions();
    markDirty();
    // Focus the new question's title field
    const cards = document.querySelectorAll(".question-card");
    cards[cards.length - 1]?.querySelector(".q-title-input")?.focus();
  });

  // Add rule
  el("addRuleBtn")?.addEventListener("click", () => {
    if (!state.draft) return;
    const firstKey = state.draft.questions.length ? "q1" : "";
    state.draft.display_rules.push({
      target_question_key: firstKey,
      source_question_key: firstKey,
      operator: "equals",
      comparison_value: "",
    });
    renderRules();
    markDirty();
  });

  // Refresh responses
  el("refreshResponsesBtn")?.addEventListener("click", refreshResponses);

  // Template select
  el("templateSelect")?.addEventListener("change", () => {
    const template = state.templates.find(t => t.key === el("templateSelect").value);
    if (!template || !state.draft) return;
    state.draft.questions = (template.questions ?? []).map((q, i) => ({
      question_key: `q${i + 1}`,
      title: q.title,
      answer_type: q.answer_type,
      is_required: Boolean(q.is_required),
      is_enabled: true,
      options: q.options ?? [],
      settings: {},
      position: i,
    }));
    state.draft.display_rules = [];
    renderQuestions();
    renderRules();
    markDirty();
  });

  // Global dirty tracking for meta fields
  el("surveyTitle")?.addEventListener("input", () => {
    const val = el("surveyTitle").value.trim();
    document.querySelector("ui-title-bar")?.setAttribute("title", val || "Survey editor");
    markDirty();
  });
  el("surveyDescription")?.addEventListener("input", markDirty);
  el("startsAt")?.addEventListener("change", markDirty);
  el("endsAt")?.addEventListener("change", markDirty);

  // Preview step navigation
  el("prevStepBtn")?.addEventListener("click", () => {
    if (state.previewStep > 0) { state.previewStep--; renderPreview(); }
  });
  el("nextStepBtn")?.addEventListener("click", () => {
    const max = Math.max(0, (state.draft?.questions?.length ?? 1) - 1);
    if (state.previewStep < max) { state.previewStep++; renderPreview(); }
  });

  // Device toggle (mobile / desktop)
  document.querySelectorAll(".preview-device-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      state.previewDevice = btn.dataset.device;
      document.querySelectorAll(".preview-device-btn").forEach(b =>
        b.classList.toggle("preview-device-btn--active", b === btn)
      );
      const mock = el("checkoutMock");
      if (mock) mock.classList.toggle("is-desktop", state.previewDevice === "desktop");
    });
  });

  // Initial data load
  try {
    await Promise.all([
      api("/api/admin/survey-templates").then(p => { state.templates = p.templates || []; }),
      loadSurveys(),
    ]);
    renderTemplates();
    navigate("list");
  } catch (err) {
    console.error("[SHOPIFY_ADMIN] init failed", err);
    showToast("Failed to initialize. Please refresh.", "error");
  }
}

init();
