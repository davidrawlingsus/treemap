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
                const response = await fetch(`${API_BASE_URL}/api/clients/${clientId}/prompts`, {
                    method: 'GET',
                    headers: getAuthHeaders()
                });

                if (!response.ok) {
                    if (response.status === 401 || response.status === 403) {
                        throw new Error('Authentication required');
                    }
                    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
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
                    // Handle auth errors
                    if (response.status === 401 || response.status === 403) {
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
                                
                                if (data.type === 'started') {
                                    // Stream started - ignore, just confirms connection is active
                                    console.log('[CLIENT_PROMPT_API] Stream started:', data.message);
                                } else if (data.type === 'chunk' && data.content) {
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
