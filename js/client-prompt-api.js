/**
 * Client-Facing Prompt API Module
 * API calls for prompts from client interface (not founder admin)
 */

(function() {
    'use strict';

    const API_BASE_URL = window.APP_CONFIG?.API_BASE_URL || 'http://localhost:8000';
    const USER_MESSAGE_LOG_PREVIEW_LENGTH = 100; // characters

    /**
     * Get authentication headers
     */
    function getAuthHeaders() {
        const token = localStorage.getItem('visualizd_auth_token');
        if (!token) {
            throw new Error('Not authenticated');
        }
        return {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        };
    }

    /**
     * Client Prompt API methods
     */
    const ClientPromptAPI = {
        /**
         * Get all live prompts for a client
         * @param {string} clientId - Client ID (UUID)
         * @returns {Promise<Array>} Array of prompts with id and name
         */
        async listPrompts(clientId) {
            try {
                const endpoint = `${API_BASE_URL}/api/clients/${clientId}/prompts`;
                const response = await fetch(endpoint, {
                    method: 'GET',
                    headers: getAuthHeaders()
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                    if (response.status === 401 || response.status === 403) {
                        throw new Error('Authentication required');
                    }
                    throw new Error(errorData.detail || `Request failed with status ${response.status}`);
                }

                return await response.json();
            } catch (error) {
                console.error('[CLIENT_PROMPT_API] listPrompts() error', {
                    clientId,
                    error: error.message || String(error),
                    timestamp: new Date().toISOString()
                });
                throw error;
            }
        },

        /**
         * Get prompt by purpose (e.g. ad_iterate)
         * @param {string} clientId - Client ID (UUID)
         * @param {string} purpose - prompt_purpose value (e.g. 'ad_iterate')
         * @returns {Promise<{id: string, name: string}>} Prompt with id and name
         * @throws {Error} If no prompt found (404) or auth error
         */
        async getPromptByPurpose(clientId, purpose) {
            try {
                const url = `${API_BASE_URL}/api/clients/${clientId}/prompts/by-purpose?purpose=${encodeURIComponent(purpose)}`;
                const response = await fetch(url, {
                    method: 'GET',
                    headers: getAuthHeaders()
                });

                if (!response.ok) {
                    if (response.status === 401 || response.status === 403) {
                        throw new Error('Authentication required');
                    }
                    if (response.status === 404) {
                        const errorData = await response.json().catch(() => ({}));
                        throw new Error(errorData.detail || `No prompt with purpose '${purpose}' configured`);
                    }
                    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                    throw new Error(errorData.detail || `Request failed with status ${response.status}`);
                }

                return await response.json();
            } catch (error) {
                console.error('[CLIENT_PROMPT_API] getPromptByPurpose() error', {
                    clientId,
                    purpose,
                    error: error.message || String(error),
                    timestamp: new Date().toISOString()
                });
                throw error;
            }
        },

        /**
         * Get prompts flagged for the top-level AI button dropdown
         * @param {string} clientId - Client ID (UUID)
         * @returns {Promise<Array>} Array of prompts with id and name
         */
        async listTopLevelAiPrompts(clientId) {
            try {
                const endpoint = `${API_BASE_URL}/api/clients/${clientId}/prompts/top-level-ai`;
                const response = await fetch(endpoint, {
                    method: 'GET',
                    headers: getAuthHeaders()
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                    if (response.status === 401 || response.status === 403) {
                        throw new Error('Authentication required');
                    }
                    throw new Error(errorData.detail || `Request failed with status ${response.status}`);
                }

                return await response.json();
            } catch (error) {
                console.error('[CLIENT_PROMPT_API] listTopLevelAiPrompts() error', {
                    clientId,
                    error: error.message || String(error),
                    timestamp: new Date().toISOString()
                });
                throw error;
            }
        },

        async listLeadContentPrompts() {
            try {
                const promptsEndpoint = `${API_BASE_URL}/api/founder/prompts?status=live&prompt_purpose=lead-content`;
                const promptsResponse = await fetch(promptsEndpoint, {
                    method: 'GET',
                    headers: getAuthHeaders()
                });
                if (!promptsResponse.ok) {
                    const errorData = await promptsResponse.json().catch(() => ({ detail: promptsResponse.statusText }));
                    throw new Error(errorData.detail || `Failed to load lead-content prompts (${promptsResponse.status})`);
                }

                const prompts = await promptsResponse.json();
                if (!Array.isArray(prompts) || prompts.length === 0) {
                    return [];
                }

                let groupsById = {};
                try {
                    const groupsEndpoint = `${API_BASE_URL}/api/founder/context-menu-groups`;
                    const groupsResponse = await fetch(groupsEndpoint, {
                        method: 'GET',
                        headers: getAuthHeaders()
                    });
                    if (groupsResponse.ok) {
                        const groups = await groupsResponse.json();
                        groupsById = (groups || []).reduce((acc, group) => {
                            if (group?.id) {
                                acc[group.id] = group;
                            }
                            return acc;
                        }, {});
                    }
                } catch (error) {
                    console.warn('[CLIENT_PROMPT_API] listLeadContentPrompts() context menu groups unavailable, using fallback group', error);
                }

                const fallbackGroupId = 'lead-content';
                const grouped = {};
                prompts.forEach((prompt) => {
                    const groupId = prompt.context_menu_group_id || fallbackGroupId;
                    const groupMeta = groupsById[groupId];
                    if (!grouped[groupId]) {
                        grouped[groupId] = {
                            id: groupId,
                            label: groupMeta?.label || 'Lead Content',
                            sort_order: Number.isFinite(groupMeta?.sort_order) ? groupMeta.sort_order : 999,
                            prompts: []
                        };
                    }
                    grouped[groupId].prompts.push({
                        id: prompt.id,
                        name: prompt.name
                    });
                });

                return Object.values(grouped)
                    .map((group) => ({
                        ...group,
                        prompts: group.prompts.sort((a, b) => (a.name || '').localeCompare(b.name || ''))
                    }))
                    .sort((a, b) => (a.sort_order - b.sort_order) || (a.label || '').localeCompare(b.label || ''));
            } catch (error) {
                console.error('[CLIENT_PROMPT_API] listLeadContentPrompts() error', {
                    error: error.message || String(error),
                    timestamp: new Date().toISOString()
                });
                throw error;
            }
        },

        async executeLeadStream(promptId, vocData, onChunk, onDone, onError, origin = null) {
            const endpoint = `${API_BASE_URL}/api/founder/prompts/${promptId}/execute?stream=true`;
            const userMessagePayload = {
                voc_data: vocData,
                origin: origin || null
            };
            const userMessage = [
                'Lead Voice of Customer Data:',
                JSON.stringify(userMessagePayload, null, 2)
            ].join('\n\n');
            try {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: getAuthHeaders(),
                    body: JSON.stringify({ user_message: userMessage })
                });

                if (!response.ok) {
                    if (response.status === 401 || response.status === 403) {
                        throw new Error('Authentication required');
                    }
                    let errorMessage = `Request failed with status ${response.status}`;
                    try {
                        const errorData = await response.json();
                        errorMessage = errorData.detail || errorData.message || errorMessage;
                    } catch (e) {
                        const errorText = await response.text();
                        if (errorText) errorMessage = errorText;
                    }
                    throw new Error(errorMessage);
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n\n');
                    buffer = lines.pop() || '';

                    for (const line of lines) {
                        if (!line.startsWith('data: ')) continue;
                        const data = JSON.parse(line.substring(6));
                        if (data.type === 'chunk' && data.content) {
                            if (onChunk) onChunk(data.content);
                        } else if (data.type === 'done') {
                            if (onDone) onDone({ tokens_used: data.tokens_used, model: data.model, content: data.content });
                            return;
                        } else if (data.type === 'error') {
                            const error = new Error(data.error || 'Streaming error');
                            if (onError) onError(error); else throw error;
                            return;
                        }
                    }
                }
            } catch (error) {
                console.error('[CLIENT_PROMPT_API] executeLeadStream() error', {
                    promptId,
                    error: error.message || String(error),
                    timestamp: new Date().toISOString()
                });
                if (onError) {
                    onError(error);
                } else {
                    throw error;
                }
            }
        },

        /**
         * Execute a prompt with streaming response (client-facing)
         * @param {string} clientId - Client ID (UUID)
         * @param {string} promptId - Prompt ID (UUID)
         * @param {Object} vocData - Voice of customer JSON data
         * @param {Function} onChunk - Callback called for each content chunk: (chunk: string) => void
         * @param {Function} onDone - Callback called when streaming completes: (metadata: {tokens_used, model, content}) => void
         * @param {Function} onError - Callback called on error: (error: Error) => void
         * @param {Object} origin - Optional origin metadata (same structure as insight origins)
         * @returns {Promise<void>} Resolves when streaming completes
         */
        async executeStream(clientId, promptId, vocData, onChunk, onDone, onError, origin = null) {
            console.log('[CLIENT_PROMPT_API] executeStream() called', {
                clientId,
                promptId,
                vocDataSize: JSON.stringify(vocData).length,
                hasOrigin: !!origin,
                timestamp: new Date().toISOString()
            });

            const endpoint = `${API_BASE_URL}/api/clients/${clientId}/prompts/${promptId}/execute?stream=true`;
            
            try {
                const authHeaders = getAuthHeaders();
                const requestBody = {
                    voc_data: vocData
                };
                if (origin) {
                    requestBody.origin = origin;
                }
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: authHeaders,
                    body: JSON.stringify(requestBody)
                });

                if (!response.ok) {
                    if (response.status === 403) {
                        let errorData = null;
                        try { errorData = await response.json(); } catch (e) { /* ignore */ }
                        const detail = errorData?.detail;
                        if (detail && typeof detail === 'object' && detail.code === 'trial_limit_exceeded') {
                            const err = new Error(detail.message || 'Trial limit exceeded');
                            err.code = 'trial_limit_exceeded';
                            err.limit = detail.limit;
                            err.used = detail.used;
                            err.remaining = detail.remaining;
                            err.planName = detail.plan_name;
                            throw err;
                        }
                        const errorMsg = (typeof detail === 'string' && detail) ? detail : 'Authentication required';
                        throw new Error(errorMsg);
                    }

                    if (response.status === 401) {
                        throw new Error('Authentication required');
                    }

                    let errorMessage = `Request failed with status ${response.status}`;
                    try {
                        const errorData = await response.json();
                        const detail = errorData.detail || errorData.message;
                        errorMessage = typeof detail === 'string' ? detail : (detail ? JSON.stringify(detail) : errorMessage);
                    } catch (e) {
                        const errorText = await response.text();
                        if (errorText) errorMessage = errorText;
                    }
                    throw new Error(errorMessage);
                }

                // Read the stream
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();
                    
                    if (done) {
                        break;
                    }

                    // Decode chunk and add to buffer
                    buffer += decoder.decode(value, { stream: true });

                    // Process complete SSE messages (lines ending with \n\n)
                    const lines = buffer.split('\n\n');
                    buffer = lines.pop() || ''; // Keep incomplete line in buffer

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.substring(6)); // Remove 'data: ' prefix
                                
                                if (data.type === 'chunk' && data.content) {
                                    // Content chunk
                                    if (onChunk) {
                                        onChunk(data.content);
                                    }
                                } else if (data.type === 'done') {
                                    if (window.subStateDecrementTrialUse) {
                                        window.subStateDecrementTrialUse();
                                    }
                                    if (onDone) {
                                        onDone({
                                            tokens_used: data.tokens_used,
                                            model: data.model,
                                            content: data.content
                                        });
                                    }
                                    return;
                                } else if (data.type === 'error') {
                                    // Error from server
                                    const error = new Error(data.error || 'Streaming error');
                                    if (onError) {
                                        onError(error);
                                    } else {
                                        throw error;
                                    }
                                    return;
                                }
                            } catch (parseError) {
                                console.error('[CLIENT_PROMPT_API] Failed to parse SSE message:', parseError, 'Line:', line);
                            }
                        }
                    }
                }

                // If we exit the loop without a 'done' message, something went wrong
                if (buffer.trim()) {
                    console.warn('[CLIENT_PROMPT_API] Stream ended with incomplete buffer:', buffer);
                }

            } catch (error) {
                console.error('[CLIENT_PROMPT_API] executeStream() error', {
                    clientId,
                    promptId,
                    error: error.message || String(error),
                    errorStack: error.stack,
                    errorName: error.name,
                    timestamp: new Date().toISOString()
                });
                
                if (onError) {
                    onError(error);
                } else {
                    throw error;
                }
            }
        }
    };

    // Export API
    window.ClientPromptAPI = ClientPromptAPI;
})();
