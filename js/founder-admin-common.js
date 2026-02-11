/**
 * Founder Admin Common Utilities
 * Shared functionality for all founder admin pages
 */

(function() {
    'use strict';

    // API Configuration
    const API_BASE_URL = window.APP_CONFIG?.API_BASE_URL || 'http://localhost:8000';

    /**
     * DOM Utilities
     */
    const DOM = {
        /**
         * Get element by ID with optional error handling
         * @param {string} id - Element ID
         * @param {boolean} required - Whether element is required
         * @returns {HTMLElement|null}
         */
        getElement(id, required = true) {
            const el = document.getElementById(id);
            if (required && !el) {
                console.error(`[FOUNDER_ADMIN] Required element not found: #${id}`);
            }
            return el;
        },

        /**
         * Get multiple elements by IDs
         * @param {string[]} ids - Array of element IDs
         * @returns {Object} Object with element IDs as keys
         */
        getElements(ids) {
            const elements = {};
            ids.forEach(id => {
                elements[id] = this.getElement(id, false);
            });
            return elements;
        },

        /**
         * Show status message
         * @param {HTMLElement} element - Status message element
         * @param {string} message - Message text
         * @param {string} type - 'success' or 'error'
         */
        showStatus(element, message, type = 'success') {
            if (!element) return;
            
            if (!message) {
                element.style.display = 'none';
                element.textContent = '';
                element.classList.remove('success', 'error');
                return;
            }

            element.textContent = message;
            element.style.display = 'block';
            element.classList.remove('success', 'error');
            element.classList.add(type);
        },

        /**
         * Escape HTML to prevent XSS
         * @param {string} text - Text to escape
         * @returns {string} Escaped HTML
         */
        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        },

        /**
         * Escape HTML for use in attributes
         * @param {string} text - Text to escape
         * @returns {string} Escaped text
         */
        escapeHtmlForAttribute(text) {
            return String(text)
                .replace(/&/g, '&amp;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
        }
    };

    /**
     * API Client with error handling
     */
    const API = {
        /**
         * Get authentication headers
         * @returns {Object} Headers object
         */
        getAuthHeaders() {
            return Auth.getAuthHeaders();
        },

        /**
         * Make API request with error handling
         * @param {string} endpoint - API endpoint
         * @param {Object} options - Fetch options
         * @returns {Promise} Response data
         */
        async request(endpoint, options = {}) {
            const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
            
            // Enhanced logging for execute endpoint
            const isExecuteRequest = endpoint.includes('/execute');
            if (isExecuteRequest) {
                console.log('[API] Making execute request', {
                    url,
                    method: options.method || 'GET',
                    hasBody: !!options.body,
                    bodyPreview: options.body ? (typeof options.body === 'string' ? options.body.substring(0, 200) : JSON.stringify(options.body).substring(0, 200)) : 'none',
                    timestamp: new Date().toISOString()
                });
            }
            
            try {
                const requestHeaders = {
                    ...this.getAuthHeaders(),
                    'Content-Type': 'application/json',
                    ...options.headers
                };

                if (isExecuteRequest) {
                    console.log('[API] Request headers', {
                        hasAuth: !!requestHeaders['Authorization'],
                        contentType: requestHeaders['Content-Type'],
                        headerKeys: Object.keys(requestHeaders)
                    });
                }

                const requestBody = options.body ? (typeof options.body === 'string' ? options.body : JSON.stringify(options.body)) : undefined;

                const response = await fetch(url, {
                    ...options,
                    headers: requestHeaders,
                    body: requestBody
                });

                if (isExecuteRequest) {
                    console.log('[API] Response received', {
                        status: response.status,
                        statusText: response.statusText,
                        ok: response.ok,
                        headers: Object.fromEntries(response.headers.entries()),
                        timestamp: new Date().toISOString()
                    });
                }

                if (!response.ok) {
                    // Handle auth errors
                    if (response.status === 401 || response.status === 403) {
                        if (isExecuteRequest) {
                            console.error('[API] Authentication error', { status: response.status });
                        }
                        Auth.showLogin();
                        const errorEl = document.getElementById('loginError');
                        if (errorEl) {
                            errorEl.textContent = 'Session expired. Please log in again.';
                            errorEl.style.display = 'block';
                        }
                        throw new Error('Authentication required');
                    }

                    // Try to parse error response
                    let errorMessage = `Request failed with status ${response.status}`;
                    let errorData = null;
                    try {
                        errorData = await response.json();
                        const detail = errorData.detail || errorData.message;
                        // Ensure errorMessage is always a string, not an object
                        if (typeof detail === 'string') {
                            errorMessage = detail;
                        } else if (detail) {
                            errorMessage = JSON.stringify(detail);
                        }
                    } catch (e) {
                        const errorText = await response.text();
                        if (errorText) errorMessage = errorText;
                    }

                    if (isExecuteRequest) {
                        console.error('[API] Request failed with error response', {
                            status: response.status,
                            statusText: response.statusText,
                            errorMessage,
                            errorData,
                            timestamp: new Date().toISOString()
                        });
                    }

                    // Ensure errorMessage is a string before creating Error
                    const finalErrorMessage = typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage);
                    throw new Error(finalErrorMessage);
                }

                // Handle 204 No Content responses (common for DELETE operations)
                if (response.status === 204) {
                    if (isExecuteRequest) {
                        console.log('[API] 204 No Content response, returning null', {
                            timestamp: new Date().toISOString()
                        });
                    }
                    return null;
                }

                // Handle empty responses
                const contentType = response.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {
                    if (isExecuteRequest) {
                        console.warn('[API] Response is not JSON', {
                            contentType,
                            returningNull: true
                        });
                    }
                    return null;
                }

                // Check if response has content before parsing
                const contentLength = response.headers.get('content-length');
                if (contentLength === '0') {
                    if (isExecuteRequest) {
                        console.log('[API] Empty response body, returning null', {
                            timestamp: new Date().toISOString()
                        });
                    }
                    return null;
                }

                // Try to parse JSON, but handle empty responses gracefully
                let jsonData;
                try {
                    const text = await response.text();
                    if (!text || text.trim() === '') {
                        if (isExecuteRequest) {
                            console.log('[API] Empty response text, returning null', {
                                timestamp: new Date().toISOString()
                            });
                        }
                        return null;
                    }
                    jsonData = JSON.parse(text);
                } catch (parseError) {
                    // If JSON parsing fails and it's not a critical error, return null
                    // This handles cases where the response is empty or malformed
                    if (isExecuteRequest) {
                        console.warn('[API] Failed to parse JSON response', {
                            error: parseError.message,
                            returningNull: true,
                            timestamp: new Date().toISOString()
                        });
                    }
                    return null;
                }
                
                if (isExecuteRequest) {
                    console.log('[API] Response JSON parsed successfully', {
                        dataType: typeof jsonData,
                        dataPreview: jsonData ? (typeof jsonData === 'object' ? JSON.stringify(jsonData).substring(0, 200) + '...' : jsonData) : 'null',
                        timestamp: new Date().toISOString()
                    });
                }

                return jsonData;
            } catch (error) {
                if (isExecuteRequest) {
                    console.error('[API] Request exception', {
                        error: error.message || String(error),
                        errorStack: error.stack,
                        errorName: error.name,
                        timestamp: new Date().toISOString()
                    });
                } else {
                    console.error('[API] Request failed:', error);
                }
                throw error;
            }
        },

        /**
         * GET request
         * @param {string} endpoint - API endpoint
         * @param {Object} params - Query parameters
         * @returns {Promise} Response data
         */
        async get(endpoint, params = {}) {
            const queryString = new URLSearchParams(params).toString();
            const url = queryString ? `${endpoint}?${queryString}` : endpoint;
            return this.request(url, { method: 'GET' });
        },

        /**
         * POST request
         * @param {string} endpoint - API endpoint
         * @param {Object} data - Request body
         * @returns {Promise} Response data
         */
        async post(endpoint, data = {}) {
            return this.request(endpoint, {
                method: 'POST',
                body: data
            });
        },

        /**
         * PUT request
         * @param {string} endpoint - API endpoint
         * @param {Object} data - Request body
         * @returns {Promise} Response data
         */
        async put(endpoint, data = {}) {
            return this.request(endpoint, {
                method: 'PUT',
                body: data
            });
        },

        /**
         * PATCH request
         * @param {string} endpoint - API endpoint
         * @param {Object} data - Request body
         * @returns {Promise} Response data
         */
        async patch(endpoint, data = {}) {
            return this.request(endpoint, {
                method: 'PATCH',
                body: data
            });
        },

        /**
         * DELETE request
         * @param {string} endpoint - API endpoint
         * @returns {Promise} Response data
         */
        async delete(endpoint) {
            return this.request(endpoint, { method: 'DELETE' });
        }
    };

    /**
     * Authentication Utilities
     */
    const AuthUtils = {
        /**
         * Wait for Auth module to be ready
         * @returns {Promise} Resolves when Auth is ready
         */
        waitForAuth() {
            return new Promise((resolve) => {
                if (typeof Auth !== 'undefined' && typeof Auth.checkAuth === 'function') {
                    resolve();
                } else {
                    const checkInterval = setInterval(() => {
                        if (typeof Auth !== 'undefined' && typeof Auth.checkAuth === 'function') {
                            clearInterval(checkInterval);
                            resolve();
                        }
                    }, 50);
                    
                    setTimeout(() => {
                        clearInterval(checkInterval);
                        console.warn('[FOUNDER_ADMIN] Auth did not load within 2 seconds');
                        resolve(); // Continue anyway
                    }, 2000);
                }
            });
        },

        /**
         * Initialize authentication check for founder pages
         * @param {Function} onAuthenticated - Callback when authenticated
         * @param {Function} onUnauthenticated - Callback when not authenticated
         */
        async initializeAuth(onAuthenticated, onUnauthenticated) {
            await this.waitForAuth();

            try {
                const authenticated = await Auth.checkAuth();
                
                if (authenticated) {
                    const userInfo = Auth.getStoredUserInfo();
                    
                    if (!userInfo?.is_founder) {
                        Auth.showLogin();
                        const errorEl = document.getElementById('loginError');
                        if (errorEl) {
                            errorEl.textContent = 'Access denied: founder privileges required.';
                            errorEl.style.display = 'block';
                        }
                        if (onUnauthenticated) onUnauthenticated();
                    } else {
                        if (onAuthenticated) onAuthenticated(userInfo);
                    }
                } else {
                    if (onUnauthenticated) onUnauthenticated();
                }
            } catch (error) {
                console.error('[FOUNDER_ADMIN] Auth initialization error:', error);
                if (onUnauthenticated) onUnauthenticated();
            }
        },

        /**
         * Setup auth event listeners
         * @param {Function} onAuthenticated - Callback when authenticated
         */
        setupAuthListeners(onAuthenticated) {
            window.addEventListener('auth:authenticated', (e) => {
                const userInfo = e.detail.user;
                if (userInfo?.is_founder) {
                    if (onAuthenticated) onAuthenticated(userInfo);
                } else {
                    Auth.showLogin();
                    const errorEl = document.getElementById('loginError');
                    if (errorEl) {
                        errorEl.textContent = 'Access denied: founder privileges required.';
                        errorEl.style.display = 'block';
                    }
                }
            });
        }
    };

    /**
     * State Management Utilities
     */
    const StateManager = {
        /**
         * Create a state manager with event-driven updates
         * @param {Object} initialState - Initial state object
         * @returns {Object} State manager instance
         */
        create(initialState = {}) {
            const state = { ...initialState };
            const listeners = new Map();

            return {
                /**
                 * Get state value
                 * @param {string} key - State key
                 * @returns {*} State value
                 */
                get(key) {
                    return key ? state[key] : state;
                },

                /**
                 * Set state value and notify listeners
                 * @param {string} key - State key
                 * @param {*} value - New value
                 */
                set(key, value) {
                    const oldValue = state[key];
                    state[key] = value;
                    
                    // Notify listeners
                    if (listeners.has(key)) {
                        listeners.get(key).forEach(callback => {
                            try {
                                callback(value, oldValue);
                            } catch (error) {
                                console.error(`[StateManager] Listener error for ${key}:`, error);
                            }
                        });
                    }

                    // Dispatch global state change event
                    window.dispatchEvent(new CustomEvent('state:changed', {
                        detail: { key, value, oldValue }
                    }));
                },

                /**
                 * Subscribe to state changes
                 * @param {string} key - State key to watch
                 * @param {Function} callback - Callback function
                 * @returns {Function} Unsubscribe function
                 */
                subscribe(key, callback) {
                    if (!listeners.has(key)) {
                        listeners.set(key, []);
                    }
                    listeners.get(key).push(callback);

                    // Return unsubscribe function
                    return () => {
                        const callbacks = listeners.get(key);
                        const index = callbacks.indexOf(callback);
                        if (index > -1) {
                            callbacks.splice(index, 1);
                        }
                    };
                },

                /**
                 * Update multiple state values at once
                 * @param {Object} updates - Object with key-value pairs
                 */
                update(updates) {
                    Object.keys(updates).forEach(key => {
                        this.set(key, updates[key]);
                    });
                }
            };
        }
    };

    /**
     * Debounce utility
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in milliseconds
     * @returns {Function} Debounced function
     */
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Throttle utility
     * @param {Function} func - Function to throttle
     * @param {number} limit - Time limit in milliseconds
     * @returns {Function} Throttled function
     */
    function throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    // Export to global scope
    window.FounderAdmin = {
        DOM,
        API,
        AuthUtils,
        StateManager,
        debounce,
        throttle,
        API_BASE_URL
    };
})();

