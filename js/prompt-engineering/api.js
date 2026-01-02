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

    // Simple cache with TTL
    const cache = new Map();
    const CACHE_TTL = 30000; // 30 seconds

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
                userMessage: userMessage.substring(0, 100) + (userMessage.length > 100 ? '...' : ''),
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
                        user_message: payload.user_message.substring(0, 100) + (payload.user_message.length > 100 ? '...' : '')
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

