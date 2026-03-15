const state = {
  surveys: [],
  templates: [],
  activeSurvey: null,
  draft: null,
};

const els = {
  surveyList: document.getElementById("surveyList"),
  questionList: document.getElementById("questionList"),
  ruleList: document.getElementById("ruleList"),
  responseList: document.getElementById("responseList"),
  createSurveyBtn: document.getElementById("createSurveyBtn"),
  saveDraftBtn: document.getElementById("saveDraftBtn"),
  publishBtn: document.getElementById("publishBtn"),
  unpublishBtn: document.getElementById("unpublishBtn"),
  addQuestionBtn: document.getElementById("addQuestionBtn"),
  addRuleBtn: document.getElementById("addRuleBtn"),
  refreshResponsesBtn: document.getElementById("refreshResponsesBtn"),
  surveyTitle: document.getElementById("surveyTitle"),
  surveyStatus: document.getElementById("surveyStatus"),
  surveyDescription: document.getElementById("surveyDescription"),
  templateSelect: document.getElementById("templateSelect"),
  startsAt: document.getElementById("startsAt"),
  endsAt: document.getElementById("endsAt"),
};

async function getSessionToken() {
  if (window.shopify?.idToken) return window.shopify.idToken();
  if (window.__SHOPIFY_DEV_SESSION_TOKEN) return window.__SHOPIFY_DEV_SESSION_TOKEN;
  throw new Error("Missing Shopify session token in embedded app context.");
}

async function api(path, method = "GET", body = null) {
  const token = await getSessionToken();
  const response = await fetch(path, {
    method,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload?.detail || `Request failed (${response.status})`);
  return payload;
}

function formatDateTimeInput(value) {
  if (!value) return "";
  return new Date(value).toISOString().slice(0, 16);
}

function collectDraftFromForm() {
  return {
    title: els.surveyTitle.value.trim(),
    status: els.surveyStatus.value,
    description: els.surveyDescription.value.trim(),
    draft_version: {
      template_key: els.templateSelect.value || null,
      starts_at: els.startsAt.value ? new Date(els.startsAt.value).toISOString() : null,
      ends_at: els.endsAt.value ? new Date(els.endsAt.value).toISOString() : null,
      settings: {},
      questions: state.draft.questions.map((q, position) => ({ ...q, position })),
      display_rules: state.draft.display_rules,
    },
  };
}

function renderSurveyList() {
  els.surveyList.innerHTML = "";
  for (const survey of state.surveys) {
    const el = document.createElement("button");
    el.className = `survey-item ${state.activeSurvey?.id === survey.id ? "active" : ""}`;
    el.innerHTML = `<strong>${survey.title}</strong><div class="muted">${survey.status}</div>`;
    el.addEventListener("click", () => loadSurvey(survey.id));
    els.surveyList.appendChild(el);
  }
}

function renderTemplates() {
  els.templateSelect.innerHTML = `<option value="">None</option>`;
  for (const template of state.templates) {
    const opt = document.createElement("option");
    opt.value = template.key;
    opt.textContent = template.name;
    els.templateSelect.appendChild(opt);
  }
}

function renderQuestions() {
  els.questionList.innerHTML = "";
  state.draft.questions.forEach((question, index) => {
    const el = document.createElement("div");
    el.className = "question-item";
    el.draggable = true;
    el.dataset.index = String(index);
    el.innerHTML = `
      <label>Question
        <input data-field="title" value="${question.title.replace(/"/g, "&quot;")}" />
      </label>
      <div class="form-grid">
        <label>Key <input data-field="question_key" value="${question.question_key}" /></label>
        <label>Type
          <select data-field="answer_type">
            <option value="single_line_text">Single line</option>
            <option value="multi_line_text">Multi line</option>
            <option value="choice_list">Choice list</option>
          </select>
        </label>
        <label>Required
          <select data-field="is_required">
            <option value="false">No</option>
            <option value="true">Yes</option>
          </select>
        </label>
      </div>
      <label>Options (comma separated)
        <input data-field="options" value="${(question.options || []).join(", ")}" />
      </label>
      <button class="btn btn-secondary" data-remove="1">Remove</button>
    `;
    el.querySelector('[data-field="answer_type"]').value = question.answer_type;
    el.querySelector('[data-field="is_required"]').value = String(Boolean(question.is_required));
    el.addEventListener("dragstart", () => el.classList.add("dragging"));
    el.addEventListener("dragend", () => el.classList.remove("dragging"));
    el.addEventListener("dragover", (event) => event.preventDefault());
    el.addEventListener("drop", () => {
      const from = Number(document.querySelector(".question-item.dragging")?.dataset.index ?? -1);
      const to = index;
      if (from < 0 || from === to) return;
      const [moved] = state.draft.questions.splice(from, 1);
      state.draft.questions.splice(to, 0, moved);
      renderQuestions();
    });
    el.addEventListener("input", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLInputElement || target instanceof HTMLSelectElement)) return;
      const field = target.dataset.field;
      if (!field) return;
      if (field === "options") {
        state.draft.questions[index].options = target.value.split(",").map((v) => v.trim()).filter(Boolean);
        return;
      }
      if (field === "is_required") {
        state.draft.questions[index].is_required = target.value === "true";
        return;
      }
      state.draft.questions[index][field] = target.value;
    });
    el.querySelector("[data-remove]")?.addEventListener("click", () => {
      state.draft.questions.splice(index, 1);
      renderQuestions();
      renderRules();
    });
    els.questionList.appendChild(el);
  });
}

function renderRules() {
  els.ruleList.innerHTML = "";
  const keys = state.draft.questions.map((q) => q.question_key).filter(Boolean);
  state.draft.display_rules.forEach((rule, index) => {
    const el = document.createElement("div");
    el.className = "rule-item";
    el.innerHTML = `
      <div class="form-grid">
        <label>Source
          <select data-field="source_question_key">${keys.map((k) => `<option value="${k}">${k}</option>`).join("")}</select>
        </label>
        <label>Target
          <select data-field="target_question_key">${keys.map((k) => `<option value="${k}">${k}</option>`).join("")}</select>
        </label>
        <label>Value <input data-field="comparison_value" value="${rule.comparison_value}" /></label>
      </div>
      <button class="btn btn-secondary" data-remove="1">Remove</button>
    `;
    el.querySelector('[data-field="source_question_key"]').value = rule.source_question_key;
    el.querySelector('[data-field="target_question_key"]').value = rule.target_question_key;
    el.addEventListener("input", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLInputElement || target instanceof HTMLSelectElement)) return;
      const field = target.dataset.field;
      if (!field) return;
      state.draft.display_rules[index][field] = target.value;
    });
    el.querySelector("[data-remove]")?.addEventListener("click", () => {
      state.draft.display_rules.splice(index, 1);
      renderRules();
    });
    els.ruleList.appendChild(el);
  });
}

function renderResponses(responses = []) {
  els.responseList.innerHTML = "";
  responses.forEach((row) => {
    const el = document.createElement("div");
    el.className = "response-item";
    el.innerHTML = `<strong>#${row.id}</strong> <span class="muted">${new Date(row.submitted_at).toLocaleString()}</span>`;
    els.responseList.appendChild(el);
  });
}

function applySurveyToForm(survey) {
  state.activeSurvey = survey;
  const draft = survey.draft_version || survey.active_version || null;
  state.draft = {
    questions: draft?.questions ? draft.questions.map((q) => ({ ...q, options: q.options || [] })) : [],
    display_rules: draft?.display_rules ? draft.display_rules.map((r) => ({ ...r })) : [],
  };
  els.surveyTitle.value = survey.title || "";
  els.surveyStatus.value = survey.status || "active";
  els.surveyDescription.value = survey.description || "";
  els.templateSelect.value = draft?.template_key || "";
  els.startsAt.value = formatDateTimeInput(draft?.starts_at);
  els.endsAt.value = formatDateTimeInput(draft?.ends_at);
  renderSurveyList();
  renderQuestions();
  renderRules();
}

async function loadSurveys() {
  const payload = await api("/api/admin/surveys");
  state.surveys = payload.surveys || [];
  renderSurveyList();
  if (state.surveys.length && !state.activeSurvey) {
    await loadSurvey(state.surveys[0].id);
  }
}

async function loadSurvey(surveyId) {
  const payload = await api(`/api/admin/surveys/${surveyId}`);
  applySurveyToForm(payload.survey);
}

async function loadTemplates() {
  const payload = await api("/api/admin/survey-templates");
  state.templates = payload.templates || [];
  renderTemplates();
}

async function refreshResponses() {
  if (!state.activeSurvey?.id) return;
  const payload = await api(`/api/admin/surveys/${state.activeSurvey.id}/responses`);
  renderResponses(payload.items || []);
}

els.createSurveyBtn.addEventListener("click", async () => {
  const payload = {
    title: "New survey",
    status: "active",
    description: "",
    draft_version: {
      template_key: null,
      starts_at: null,
      ends_at: null,
      settings: {},
      questions: [],
      display_rules: [],
    },
  };
  const created = await api("/api/admin/surveys", "POST", payload);
  await loadSurveys();
  applySurveyToForm(created.survey);
});

els.saveDraftBtn.addEventListener("click", async () => {
  if (!state.activeSurvey?.id) return;
  await api(`/api/admin/surveys/${state.activeSurvey.id}`, "PUT", collectDraftFromForm());
  await loadSurvey(state.activeSurvey.id);
});

els.publishBtn.addEventListener("click", async () => {
  if (!state.activeSurvey?.id) return;
  await api(`/api/admin/surveys/${state.activeSurvey.id}/publish`, "POST", {});
  await loadSurvey(state.activeSurvey.id);
});

els.unpublishBtn.addEventListener("click", async () => {
  if (!state.activeSurvey?.id) return;
  await api(`/api/admin/surveys/${state.activeSurvey.id}/unpublish`, "POST", {});
  await loadSurvey(state.activeSurvey.id);
});

els.addQuestionBtn.addEventListener("click", () => {
  state.draft.questions.push({
    question_key: `q${state.draft.questions.length + 1}`,
    title: "New question",
    answer_type: "single_line_text",
    is_required: false,
    is_enabled: true,
    options: [],
    settings: {},
  });
  renderQuestions();
});

els.addRuleBtn.addEventListener("click", () => {
  const first = state.draft.questions[0]?.question_key || "";
  state.draft.display_rules.push({
    target_question_key: first,
    source_question_key: first,
    operator: "equals",
    comparison_value: "",
  });
  renderRules();
});

els.refreshResponsesBtn.addEventListener("click", refreshResponses);

els.templateSelect.addEventListener("change", () => {
  const template = state.templates.find((item) => item.key === els.templateSelect.value);
  if (!template) return;
  state.draft.questions = template.questions.map((q, idx) => ({
    question_key: q.question_key || `q${idx + 1}`,
    title: q.title,
    answer_type: q.answer_type,
    is_required: q.is_required,
    is_enabled: true,
    options: q.options || [],
    settings: {},
    position: idx,
  }));
  state.draft.display_rules = [];
  renderQuestions();
  renderRules();
});

async function init() {
  await loadTemplates();
  await loadSurveys();
}

init().catch((error) => {
  console.error("[SHOPIFY_ADMIN] init failed", error);
  alert(error instanceof Error ? error.message : "Failed to initialize survey builder.");
});
