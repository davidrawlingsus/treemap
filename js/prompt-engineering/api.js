/**
 * Prompt Engineering API Module
 * All API calls for prompts management with caching
 */

(function() {
    'use strict';

    if (!window.FounderAdmin) {
        console.error('[PROMPT_API] FounderAdmin utilities must be loaded first');
        return;
    }

    const { API } = window.FounderAdmin;

    // Constants
    const CACHE_TTL = 30000; // 30 seconds
    const USER_MESSAGE_LOG_PREVIEW_LENGTH = 100; // characters

    // Simple cache with TTL
    const cache = new Map();

    function getCacheKey(endpoint, params) {
        const paramStr = params ? JSON.stringify(params) : '';
        return `${endpoint}${paramStr}`;
    }

    function getCached(key) {
        const cached = cache.get(key);
        if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
            return cached.data;
        }
        cache.delete(key);
        return null;
    }

    function setCache(key, data) {
        cache.set(key, { data, timestamp: Date.now() });
    }

    // Export clearCache function for external use
    window.PromptAPICache = { clear: () => cache.clear() };

    /**
     * Prompt API methods
     */
    const PromptAPI = {
        /**
         * Get all prompts with optional filters
         * @param {Object} filters - Filter options (status, prompt_purpose)
         * @param {boolean} useCache - Whether to use cache (default: true)
         * @returns {Promise<Array>} Array of prompts
         */
        async list(filters = {}, useCache = true) {
            const cacheKey = getCacheKey('/api/founder/prompts', filters);
            if (useCache) {
                const cached = getCached(cacheKey);
                if (cached) return cached;
            }
            const result = await API.get('/api/founder/prompts', filters);
            if (useCache) {
                setCache(cacheKey, result);
            }
            return result;
        },

        /**
         * Get a single prompt by ID
         * @param {number} promptId - Prompt ID
         * @returns {Promise<Object>} Prompt object
         */
        async get(promptId) {
            return API.get(`/api/founder/prompts/${promptId}`);
        },

        /**
         * Create a new prompt
         * @param {Object} data - Prompt data
         * @returns {Promise<Object>} Created prompt
         */
        async create(data) {
            const result = await API.post('/api/founder/prompts', data);
            // Clear cache since prompts list changed
            cache.clear();
            return result;
        },

        /**
         * Update an existing prompt
         * @param {number} promptId - Prompt ID
         * @param {Object} data - Updated prompt data
         * @returns {Promise<Object>} Updated prompt
         */
        async update(promptId, data) {
            const result = await API.put(`/api/founder/prompts/${promptId}`, data);
            // Clear cache since prompts list changed
            cache.clear();
            return result;
        },

        /**
         * Delete a prompt
         * @param {number} promptId - Prompt ID
         * @returns {Promise<void>}
         */
        async delete(promptId) {
            const result = await API.delete(`/api/founder/prompts/${promptId}`);
            // Clear cache since prompts list changed
            cache.clear();
            return result;
        },

        /**
         * Execute a prompt
         * @param {number} promptId - Prompt ID
         * @param {string} userMessage - User message to send with prompt
         * @returns {Promise<Object>} Execution result
         */
        async execute(promptId, userMessage = '') {
            console.log('[PROMPT_API] execute() called', {
                promptId,
                userMessage: userMessage.substring(0, USER_MESSAGE_LOG_PREVIEW_LENGTH) + (userMessage.length > USER_MESSAGE_LOG_PREVIEW_LENGTH ? '...' : ''),
                userMessageLength: userMessage.length,
                timestamp: new Date().toISOString()
            });

            try {
                const endpoint = `/api/founder/prompts/${promptId}/execute`;
                const payload = {
                    user_message: userMessage
                };

                console.log('[PROMPT_API] Making POST request', {
                    endpoint,
                    payload: {
                        ...payload,
                        user_message: payload.user_message.substring(0, USER_MESSAGE_LOG_PREVIEW_LENGTH) + (payload.user_message.length > USER_MESSAGE_LOG_PREVIEW_LENGTH ? '...' : '')
                    }
                });

                const result = await API.post(endpoint, payload);

                console.log('[PROMPT_API] execute() success', {
                    promptId,
                    result: result ? (typeof result === 'object' ? JSON.stringify(result).substring(0, 200) + '...' : result) : 'null/undefined',
                    resultType: typeof result,
                    timestamp: new Date().toISOString()
                });

                return result;
            } catch (error) {
                console.error('[PROMPT_API] execute() error', {
                    promptId,
                    error: error.message || String(error),
                    errorStack: error.stack,
                    errorName: error.name,
                    errorResponse: error.response || error.data || 'no response data',
                    timestamp: new Date().toISOString()
                });
                throw error;
            }
        },

        /**
         * Execute a prompt with streaming response
         * @param {number} promptId - Prompt ID
         * @param {string} userMessage - User message to send with prompt
         * @param {Function} onChunk - Callback called for each content chunk: (chunk: string) => void
         * @param {Function} onDone - Callback called when streaming completes: (metadata: {tokens_used, model, content}) => void
         * @param {Function} onError - Callback called on error: (error: Error) => void
         * @returns {Promise<void>} Resolves when streaming completes
         */
        async executeStream(promptId, userMessage = '', onChunk, onDone, onError) {
            console.log('[PROMPT_API] executeStream() called', {
                promptId,
                userMessage: userMessage.substring(0, USER_MESSAGE_LOG_PREVIEW_LENGTH) + (userMessage.length > USER_MESSAGE_LOG_PREVIEW_LENGTH ? '...' : ''),
                userMessageLength: userMessage.length,
                timestamp: new Date().toISOString()
            });

            const API_BASE_URL = window.APP_CONFIG?.API_BASE_URL || 'http://localhost:8000';
            const endpoint = `${API_BASE_URL}/api/founder/prompts/${promptId}/execute?stream=true`;
            
            try {
                const authHeaders = API.getAuthHeaders();
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: {
                        ...authHeaders,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        user_message: userMessage
                    })
                });

                if (!response.ok) {
                    // Handle auth errors
                    if (response.status === 401 || response.status === 403) {
                        if (typeof Auth !== 'undefined') {
                            Auth.showLogin();
                        }
                        throw new Error('Authentication required');
                    }

                    // Try to parse error response
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
                                    // Streaming complete
                                    if (onDone) {
                                        onDone({
                                            tokens_used: data.tokens_used,
                                            model: data.model,
                                            content: data.content
                                        });
                                    }
                                    return; // Exit loop
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
                                console.error('[PROMPT_API] Failed to parse SSE message:', parseError, 'Line:', line);
                            }
                        }
                    }
                }

                // If we exit the loop without a 'done' message, something went wrong
                if (buffer.trim()) {
                    console.warn('[PROMPT_API] Stream ended with incomplete buffer:', buffer);
                }

            } catch (error) {
                console.error('[PROMPT_API] executeStream() error', {
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
        },

        /**
         * Get all actions for a specific prompt
         * @param {number} promptId - Prompt ID
         * @returns {Promise<Array>} Array of actions
         */
        async getActions(promptId) {
            return API.get(`/api/founder/prompts/${promptId}/actions`);
        },

        /**
         * Get all actions from all prompts
         * @param {boolean} useCache - Whether to use cache (default: false, actions change frequently)
         * @returns {Promise<Array>} Array of all actions
         */
        async getAllActions(useCache = false) {
            const cacheKey = getCacheKey('/api/founder/prompts/all/actions', {});
            if (useCache) {
                const cached = getCached(cacheKey);
                if (cached) return cached;
            }
            const result = await API.get('/api/founder/prompts/all/actions');
            if (useCache) {
                setCache(cacheKey, result);
            }
            return result;
        },

        /**
         * Clear API cache
         */
        clearCache() {
            cache.clear();
        },

        /**
         * Delete an action
         * @param {number} actionId - Action ID
         * @returns {Promise<void>}
         */
        async deleteAction(actionId) {
            const result = await API.delete(`/api/founder/prompts/actions/${actionId}`);
            // Clear actions cache
            cache.clear();
            return result;
        }
    };

    // Export API
    window.PromptAPI = PromptAPI;
})();

