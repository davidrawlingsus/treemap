import { getBaseUrl } from './api-config.js';

export async function loadLeadRuns(getAuthHeaders, search = null, limit = 200) {
    const apiBaseUrl = getBaseUrl();
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    params.append('limit', String(limit));

    const response = await fetch(`${apiBaseUrl}/api/voc/leads/runs?${params.toString()}`, {
        headers: getAuthHeaders ? getAuthHeaders() : {}
    });
    if (!response.ok) {
        throw new Error(`Failed to load lead runs: HTTP ${response.status}`);
    }
    const payload = await response.json();
    return payload.items || [];
}

export async function loadLeadRunData(runId, getAuthHeaders) {
    const apiBaseUrl = getBaseUrl();
    const params = new URLSearchParams();
    params.append('run_id', runId);

    const response = await fetch(`${apiBaseUrl}/api/voc/leads/data?${params.toString()}`, {
        headers: getAuthHeaders ? getAuthHeaders() : {}
    });
    if (!response.ok) {
        throw new Error(`Failed to load lead run data: HTTP ${response.status}`);
    }
    return response.json();
}
