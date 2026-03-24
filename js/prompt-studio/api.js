/**
 * Prompt Studio API service
 */

const API_BASE_URL = window.APP_CONFIG?.API_BASE_URL || 'http://localhost:8000';

function headers() {
    return window.Auth?.getAuthHeaders() || {};
}

async function handleResponse(response) {
    if (response.status === 401 || response.status === 403) {
        window.Auth?.showLogin();
        throw new Error('Authentication required');
    }
    if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || `Request failed: ${response.status}`);
    }
    return response.json();
}

export async function fetchLeadgenRuns(search) {
    const params = search ? `?search=${encodeURIComponent(search)}` : '';
    const res = await fetch(`${API_BASE_URL}/api/founder-admin/leadgen-runs${params}`, { headers: headers() });
    return handleResponse(res);
}

export async function scrapeProspect(url, companyName, maxReviews) {
    const res = await fetch(`${API_BASE_URL}/api/founder-admin/prompt-studio/scrape`, {
        method: 'POST',
        headers: { ...headers(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, company_name: companyName || null, max_reviews: maxReviews }),
    });
    return handleResponse(res);
}

export async function fetchDefaultPrompts() {
    const res = await fetch(`${API_BASE_URL}/api/founder-admin/prompt-studio/default-prompts`, { headers: headers() });
    return handleResponse(res);
}

export async function fetchRunInputs(runId) {
    const res = await fetch(`${API_BASE_URL}/api/founder-admin/prompt-studio/${runId}/inputs`, { headers: headers() });
    return handleResponse(res);
}

export async function fetchPromptVersions(promptPurpose) {
    const res = await fetch(`${API_BASE_URL}/api/founder-admin/prompt-studio/prompt-versions/${encodeURIComponent(promptPurpose)}`, { headers: headers() });
    return handleResponse(res);
}

export async function runContextStep(systemPrompt, url) {
    const res = await fetch(`${API_BASE_URL}/api/founder-admin/prompt-studio/context`, {
        method: 'POST',
        headers: { ...headers(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ system_prompt: systemPrompt, url }),
    });
    return handleResponse(res);
}

export async function runDiscoverStep(systemPrompt, userPromptTemplate, productContext, reviews) {
    const res = await fetch(`${API_BASE_URL}/api/founder-admin/prompt-studio/discover`, {
        method: 'POST',
        headers: { ...headers(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ system_prompt: systemPrompt, user_prompt_template: userPromptTemplate, product_context: productContext, reviews }),
    });
    return handleResponse(res);
}

export async function runCodeStep(systemPrompt, userPromptTemplate, codebook, reviews) {
    const res = await fetch(`${API_BASE_URL}/api/founder-admin/prompt-studio/code`, {
        method: 'POST',
        headers: { ...headers(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ system_prompt: systemPrompt, user_prompt_template: userPromptTemplate, codebook, reviews }),
    });
    return handleResponse(res);
}

export async function runRefineStep(systemPrompt, userPromptTemplate, codebook, stats, noMatches, productContext) {
    const res = await fetch(`${API_BASE_URL}/api/founder-admin/prompt-studio/refine`, {
        method: 'POST',
        headers: { ...headers(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ system_prompt: systemPrompt, user_prompt_template: userPromptTemplate, codebook, stats, no_matches: noMatches, product_context: productContext }),
    });
    return handleResponse(res);
}

// New VoC taxonomy chain steps (streaming)

/**
 * Run a streaming step. Returns { output, elapsed_seconds } just like non-streaming,
 * but calls onTokens(n) as tokens arrive so the UI can show progress.
 */
async function runStreamingStep(url, body, onTokens) {
    console.log('[stream] Starting:', url);
    const res = await fetch(`${API_BASE_URL}${url}?stream=true`, {
        method: 'POST',
        headers: { ...headers(), 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    console.log('[stream] Response status:', res.status, 'content-type:', res.headers.get('content-type'));
    if (res.status === 401 || res.status === 403) {
        window.Auth?.showLogin();
        throw new Error('Authentication required');
    }
    if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        console.error('[stream] Error response:', errBody);
        throw new Error(errBody.detail || `Request failed: ${res.status}`);
    }

    // If the response is JSON (non-streaming fallback), handle directly
    const contentType = res.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
        console.log('[stream] Got JSON response instead of SSE — handling as non-streaming');
        const json = await res.json();
        return { output: json.output, elapsed_seconds: json.elapsed_seconds };
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let result = null;
    let eventCount = 0;
    let chunkCount = 0;

    while (true) {
        const { done, value } = await reader.read();
        if (done) {
            console.log('[stream] Stream ended. Chunks:', chunkCount, 'Events:', eventCount, 'Got result:', !!result);
            break;
        }
        chunkCount++;
        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        // Process complete SSE events (delimited by double newlines)
        const events = buffer.split('\n\n');
        buffer = events.pop(); // keep incomplete event in buffer
        for (const event of events) {
            const dataLine = event.split('\n').find(l => l.startsWith('data: '));
            if (!dataLine) continue;
            eventCount++;
            try {
                const evt = JSON.parse(dataLine.slice(6));
                if (evt.type === 'tokens' && onTokens) {
                    onTokens(evt.output_tokens);
                } else if (evt.type === 'done') {
                    console.log('[stream] Got done event. Output keys:', evt.output ? Object.keys(evt.output) : 'null', 'Elapsed:', evt.elapsed_seconds);
                    result = { output: evt.output, elapsed_seconds: evt.elapsed_seconds };
                } else if (evt.type === 'error') {
                    console.error('[stream] Got error event:', evt.message);
                    throw new Error(evt.message);
                }
            } catch (e) {
                if (e.message && !e.message.startsWith('Unexpected')) throw e;
                console.warn('[stream] JSON parse error on SSE event:', e.message, 'Data (first 200):', dataLine.slice(6, 206));
            }
        }
    }

    // Check for remaining data in buffer
    if (!result && buffer.trim()) {
        console.warn('[stream] Buffer has leftover data (first 500):', buffer.slice(0, 500));
        // Try to parse it as a final event
        const dataLine = buffer.split('\n').find(l => l.startsWith('data: '));
        if (dataLine) {
            try {
                const evt = JSON.parse(dataLine.slice(6));
                if (evt.type === 'done') {
                    console.log('[stream] Recovered done event from buffer');
                    result = { output: evt.output, elapsed_seconds: evt.elapsed_seconds };
                }
            } catch (e) {
                console.error('[stream] Failed to parse leftover buffer:', e.message);
            }
        }
    }

    if (!result) {
        console.error('[stream] No result! Total chunks:', chunkCount, 'events:', eventCount, 'remaining buffer length:', buffer.length);
        throw new Error('Stream ended without a result');
    }
    return result;
}

export async function runExtractStep(systemPrompt, userPromptTemplate, productContext, reviews, onTokens) {
    return runStreamingStep(
        '/api/founder-admin/prompt-studio/extract',
        { system_prompt: systemPrompt, user_prompt_template: userPromptTemplate, product_context: productContext, reviews },
        onTokens,
    );
}

export async function runTaxonomyStep(systemPrompt, userPromptTemplate, productContext, signals, onTokens) {
    return runStreamingStep(
        '/api/founder-admin/prompt-studio/taxonomy',
        { system_prompt: systemPrompt, user_prompt_template: userPromptTemplate, product_context: productContext, signals },
        onTokens,
    );
}

export async function runValidateStep(systemPrompt, userPromptTemplate, productContext, taxonomy, signals, onTokens) {
    return runStreamingStep(
        '/api/founder-admin/prompt-studio/validate',
        { system_prompt: systemPrompt, user_prompt_template: userPromptTemplate, product_context: productContext, taxonomy, signals },
        onTokens,
    );
}

export async function runGenerateAd(systemPrompt, userPrompt, onTokens) {
    return runStreamingStep(
        '/api/founder-admin/prompt-studio/generate-ad',
        { system_prompt: systemPrompt, user_prompt: userPrompt },
        onTokens,
    );
}

export async function savePipelineState(runId, pipelineState) {
    const res = await fetch(`${API_BASE_URL}/api/founder-admin/prompt-studio/${runId}/pipeline`, {
        method: 'PUT',
        headers: { ...headers(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ pipeline_state: pipelineState }),
    });
    return handleResponse(res);
}

// Prompt CRUD — reuses existing prompts API
export async function createPromptVersion(data) {
    const res = await fetch(`${API_BASE_URL}/api/founder/prompts`, {
        method: 'POST',
        headers: { ...headers(), 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    return handleResponse(res);
}

export async function updatePrompt(promptId, data) {
    const res = await fetch(`${API_BASE_URL}/api/founder/prompts/${promptId}`, {
        method: 'PUT',
        headers: { ...headers(), 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    return handleResponse(res);
}
