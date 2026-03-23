import {
    listWidgetSurveys,
    createWidgetSurvey,
    getWidgetSurveyDetail,
    updateWidgetSurvey,
    publishWidgetSurvey,
    unpublishWidgetSurvey,
    deleteWidgetSurvey,
    listWidgetSurveyResponses,
    getWidgetSurveyStats,
    getWidgetInstallationStatus,
} from '/js/services/api-widget-survey.js';
import { getBaseUrl } from '/js/services/api-config.js';
import {
    renderSurveyList,
    renderSurveyEditor,
    renderResponseViewer,
    renderEmbedCode,
    renderStatus,
} from '/js/renderers/widget-survey-renderer.js';

let state = {
    clientId: null,
    surveys: [],
    currentSurvey: null,
    responses: null,
    installStatus: null,
    stats: null,
    view: 'list',
};

let container = null;
let statusEl = null;

export function initClientSurveyController(el, clientId) {
    container = el;
    state.clientId = clientId;
    state.view = 'list';

    // Create or find a status element
    statusEl = container.parentElement?.querySelector('.surveys-status-message');
    if (!statusEl) {
        statusEl = document.createElement('div');
        statusEl.className = 'surveys-status-message status-message';
        statusEl.style.display = 'none';
        container.parentElement?.insertBefore(statusEl, container);
    }

    loadSurveys();
}

function showStatus(message, type = 'success') {
    renderStatus(statusEl, message, type);
}

async function loadSurveys() {
    if (!state.clientId) return;
    try {
        const [surveys, installStatus] = await Promise.all([
            listWidgetSurveys(state.clientId),
            getWidgetInstallationStatus(state.clientId),
        ]);
        state.surveys = surveys;
        state.installStatus = installStatus;
        state.view = 'list';
        renderView();
    } catch (err) {
        showStatus('Failed to load surveys: ' + err.message, 'error');
    }
}

function renderView() {
    if (!container) return;

    if (state.view === 'list') {
        renderSurveyList(container, {
            surveys: state.surveys,
            installStatus: state.installStatus,
            onNew: () => openEditor(null),
            onEdit: (id) => openEditor(id),
            onPublish: (id) => doPublish(id),
            onUnpublish: (id) => doUnpublish(id),
            onDelete: (id) => doDelete(id),
            onViewResponses: (id) => openResponses(id),
            onShowEmbed: () => showEmbed(),
        });
    } else if (state.view === 'editor') {
        renderSurveyEditor(container, {
            survey: state.currentSurvey,
            onSave: (payload) => doSave(payload),
            onBack: () => { state.view = 'list'; loadSurveys(); },
        });
    } else if (state.view === 'responses') {
        renderResponseViewer(container, {
            survey: state.currentSurvey,
            responses: state.responses,
            stats: state.stats,
            onBack: () => { state.view = 'list'; loadSurveys(); },
            onLoadMore: (offset) => loadMoreResponses(offset),
        });
    }
}

async function openEditor(surveyId) {
    if (surveyId) {
        try {
            state.currentSurvey = await getWidgetSurveyDetail(surveyId, state.clientId);
        } catch (err) {
            showStatus('Failed to load survey: ' + err.message, 'error');
            return;
        }
    } else {
        state.currentSurvey = null;
    }
    state.view = 'editor';
    renderView();
}

async function openResponses(surveyId) {
    try {
        const [detail, responses, stats] = await Promise.all([
            getWidgetSurveyDetail(surveyId, state.clientId),
            listWidgetSurveyResponses(surveyId, state.clientId),
            getWidgetSurveyStats(surveyId, state.clientId),
        ]);
        state.currentSurvey = detail;
        state.responses = responses;
        state.stats = stats;
        state.view = 'responses';
        renderView();
    } catch (err) {
        showStatus('Failed to load responses: ' + err.message, 'error');
    }
}

async function loadMoreResponses(offset) {
    if (!state.currentSurvey) return;
    try {
        const more = await listWidgetSurveyResponses(state.currentSurvey.id, state.clientId, { offset });
        state.responses.items = state.responses.items.concat(more.items);
        renderView();
    } catch (err) {
        showStatus('Failed to load more responses: ' + err.message, 'error');
    }
}

async function doSave(payload) {
    try {
        if (state.currentSurvey) {
            state.currentSurvey = await updateWidgetSurvey(state.currentSurvey.id, state.clientId, payload);
        } else {
            state.currentSurvey = await createWidgetSurvey(state.clientId, payload);
        }
        showStatus('Survey saved successfully');
        state.view = 'list';
        loadSurveys();
    } catch (err) {
        showStatus('Failed to save survey: ' + err.message, 'error');
    }
}

async function doPublish(surveyId) {
    try {
        await publishWidgetSurvey(surveyId, state.clientId);
        showStatus('Survey published');
        loadSurveys();
    } catch (err) {
        showStatus('Failed to publish: ' + err.message, 'error');
    }
}

async function doUnpublish(surveyId) {
    try {
        await unpublishWidgetSurvey(surveyId, state.clientId);
        showStatus('Survey unpublished');
        loadSurveys();
    } catch (err) {
        showStatus('Failed to unpublish: ' + err.message, 'error');
    }
}

async function doDelete(surveyId) {
    if (!confirm('Delete this survey and all its responses?')) return;
    try {
        await deleteWidgetSurvey(surveyId, state.clientId);
        showStatus('Survey deleted');
        loadSurveys();
    } catch (err) {
        showStatus('Failed to delete: ' + err.message, 'error');
    }
}

function showEmbed() {
    const apiBaseUrl = getBaseUrl();
    renderEmbedCode(container, {
        apiBaseUrl,
        onBack: () => { state.view = 'list'; renderView(); },
    });
}
