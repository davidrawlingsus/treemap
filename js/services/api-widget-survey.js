import { getBaseUrl } from './api-config.js';

function buildQuery(params = {}) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
        if (value === undefined || value === null || value === '') return;
        query.append(key, String(value));
    });
    const queryString = query.toString();
    return queryString ? `?${queryString}` : '';
}

async function request(path, options = {}) {
    const apiBaseUrl = getBaseUrl();
    const response = await fetch(`${apiBaseUrl}${path}`, {
        ...options,
        headers: {
            ...(window.Auth?.getAuthHeaders?.() || {}),
            'Content-Type': 'application/json',
            ...(options.headers || {}),
        },
    });

    if (!response.ok) {
        let detail = `Request failed (${response.status})`;
        try {
            const body = await response.json();
            if (body?.detail) detail = body.detail;
        } catch (_error) {
            // Keep fallback detail.
        }
        throw new Error(detail);
    }

    if (response.status === 204) return null;
    return response.json();
}

// ── Survey CRUD ─────────────────────────────────────────────────

export async function listWidgetSurveys(clientId) {
    return request(`/api/widget-surveys/${buildQuery({ client_id: clientId })}`, { method: 'GET' });
}

export async function createWidgetSurvey(clientId, payload) {
    return request(`/api/widget-surveys/${buildQuery({ client_id: clientId })}`, {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

export async function getWidgetSurveyDetail(surveyId, clientId) {
    return request(`/api/widget-surveys/${surveyId}${buildQuery({ client_id: clientId })}`, { method: 'GET' });
}

export async function updateWidgetSurvey(surveyId, clientId, payload) {
    return request(`/api/widget-surveys/${surveyId}${buildQuery({ client_id: clientId })}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
    });
}

export async function publishWidgetSurvey(surveyId, clientId) {
    return request(`/api/widget-surveys/${surveyId}/publish${buildQuery({ client_id: clientId })}`, {
        method: 'POST',
    });
}

export async function unpublishWidgetSurvey(surveyId, clientId) {
    return request(`/api/widget-surveys/${surveyId}/unpublish${buildQuery({ client_id: clientId })}`, {
        method: 'POST',
    });
}

export async function deleteWidgetSurvey(surveyId, clientId) {
    return request(`/api/widget-surveys/${surveyId}${buildQuery({ client_id: clientId })}`, {
        method: 'DELETE',
    });
}

// ── Responses ───────────────────────────────────────────────────

export async function listWidgetSurveyResponses(surveyId, clientId, { limit = 100, offset = 0 } = {}) {
    return request(`/api/widget-surveys/${surveyId}/responses${buildQuery({ client_id: clientId, limit, offset })}`, {
        method: 'GET',
    });
}

// ── Stats & installation ────────────────────────────────────────

export async function getWidgetSurveyStats(surveyId, clientId) {
    return request(`/api/widget-surveys/${surveyId}/stats${buildQuery({ client_id: clientId })}`, { method: 'GET' });
}

export async function getWidgetInstallationStatus(clientId) {
    return request(`/api/widget-surveys/installation-status${buildQuery({ client_id: clientId })}`, { method: 'GET' });
}

// ── Client settings (Clarity project ID) ────────────────────────

export async function updateClientSettings(clientId, settings) {
    return request(`/api/clients/${clientId}/settings`, {
        method: 'PATCH',
        body: JSON.stringify(settings),
    });
}
