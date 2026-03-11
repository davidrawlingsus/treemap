const API_BASE_URL = window.APP_CONFIG?.API_BASE_URL || "http://localhost:8000";

/**
 * Request LLM-ready Trustpilot payload from public API.
 * @param {Object} body request payload
 * @returns {Promise<Object>} API response body
 */
export async function generateTrustpilotPayload(body) {
    const response = await fetch(`${API_BASE_URL}/api/public/trustpilot-leadgen`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
    });

    let data = {};
    try {
        data = await response.json();
    } catch (_error) {
        data = {};
    }

    if (!response.ok) {
        const detail = data?.detail || `Request failed (${response.status})`;
        throw new Error(detail);
    }

    return data;
}
