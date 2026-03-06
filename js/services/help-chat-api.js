import { getHeadersSafe } from '/js/services/auth-service.js';

function getApiBaseUrl() {
    return window.APP_CONFIG?.API_BASE_URL || window.Auth?.getApiBaseUrl?.() || 'http://localhost:8000';
}

function buildUrl(path, params = {}) {
    const url = new URL(`${getApiBaseUrl()}${path}`);
    Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
            url.searchParams.set(key, value);
        }
    });
    return url;
}

async function parseJsonResponse(response) {
    const text = await response.text();
    let body = null;

    if (text) {
        try {
            body = JSON.parse(text);
        } catch (_) {
            body = { detail: text };
        }
    }

    if (!response.ok) {
        const message = body?.detail || body?.message || 'Help chat request failed.';
        throw new Error(message);
    }

    return body;
}

export async function ensureHelpChatConversation(payload) {
    const response = await fetch(buildUrl('/api/help-chat/conversations/ensure'), {
        method: 'POST',
        headers: getHeadersSafe(),
        body: JSON.stringify(payload),
    });
    return parseJsonResponse(response);
}

export async function listHelpChatMessages({ conversationId, visitorToken }) {
    const response = await fetch(
        buildUrl(`/api/help-chat/conversations/${conversationId}/messages`, {
            visitor_token: visitorToken,
        }),
        {
            headers: getHeadersSafe(),
        }
    );
    return parseJsonResponse(response);
}

export async function sendHelpChatMessage({ conversationId, visitorToken, body, clientMessageId }) {
    const response = await fetch(
        buildUrl(`/api/help-chat/conversations/${conversationId}/messages`, {
            visitor_token: visitorToken,
        }),
        {
            method: 'POST',
            headers: getHeadersSafe(),
            body: JSON.stringify({
                body,
                client_message_id: clientMessageId,
            }),
        }
    );
    return parseJsonResponse(response);
}

export function openHelpChatStream({ conversationId, visitorToken, since }) {
    return new EventSource(
        buildUrl(`/api/help-chat/conversations/${conversationId}/stream`, {
            visitor_token: visitorToken,
            since,
        })
    );
}
