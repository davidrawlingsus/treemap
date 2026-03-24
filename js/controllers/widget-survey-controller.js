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
    renderInstallationStatus,
    renderEmbedCode,
    renderStatus,
} from '/js/renderers/widget-survey-renderer.js';

let state = {
    clientId: null,
    clients: [],
    surveys: [],
    currentSurvey: null,
    responses: null,
    installStatus: null,
    stats: null,
    view: 'list', // 'list' | 'editor' | 'responses'
};

const elements = {};

export function initWidgetSurveyController() {
    elements.statusMessage = document.getElementById('statusMessage');
    elements.clientSelect = document.getElementById('clientSelect');
    elements.mainContent = document.getElementById('mainContent');

    if (elements.clientSelect) {
        elements.clientSelect.addEventListener('change', onClientChange);
    }

    loadClients();
}

function showStatus(message, type = 'success') {
    renderStatus(elements.statusMessage, message, type);
}

async function loadClients() {
    try {
        const apiBaseUrl = getBaseUrl();
        const response = await fetch(`${apiBaseUrl}/api/clients`, {
            headers: window.Auth?.getAuthHeaders?.() || {},
        });
        if (response.ok) {
            state.clients = await response.json();
            renderClientOptions();
            if (state.clients.length > 0) {
                state.clientId = state.clients[0].id;
                elements.clientSelect.value = state.clientId;
                loadSurveys();
            }
        }
    } catch (err) {
        showStatus('Failed to load clients: ' + err.message, 'error');
    }
}

function renderClientOptions() {
    if (!elements.clientSelect) return;
    elements.clientSelect.innerHTML = state.clients
        .map(c => `<option value="${c.id}">${c.name}</option>`)
        .join('');
}

function onClientChange() {
    state.clientId = elements.clientSelect.value;
    state.view = 'list';
    loadSurveys();
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
    if (!elements.mainContent) return;

    if (state.view === 'list') {
        renderSurveyList(elements.mainContent, {
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
        renderSurveyEditor(elements.mainContent, {
            survey: state.currentSurvey,
            onSave: (payload) => doSave(payload),
            onBack: () => { state.view = 'list'; loadSurveys(); },
        });
    } else if (state.view === 'responses') {
        renderResponseViewer(elements.mainContent, {
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
    renderEmbedCode(elements.mainContent, {
        apiBaseUrl,
        onBack: () => { state.view = 'list'; renderView(); },
    });
}
