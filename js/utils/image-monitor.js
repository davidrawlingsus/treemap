/**
 * Image Loading Monitor
 * 
 * Tracks image loading success/failure for Vercel Blob Storage images
 * to help debug intermittent loading issues.
 * 
 * Enable monitoring by calling window.ImageMonitor.enable() or 
 * setting localStorage.setItem('imageMonitorEnabled', 'true')
 */

(function() {
    'use strict';

    // Configuration
    const VERCEL_BLOB_DOMAIN = 'neeuv3c4wu4qzcdw.public.blob.vercel-storage.com';
    const LOG_TO_CONSOLE = true;
    const MAX_LOG_ENTRIES = 500;
    const DEBUG_SERVER_ENDPOINT = 'http://127.0.0.1:7242/ingest/0ea04ade-be37-4438-ba64-4de28c7d11e9';

    // State
    let isEnabled = false;
    let observer = null;
    const loadLogs = [];
    const trackedImages = new WeakSet();
    let sessionId = null;
    let networkMonitorInterval = null;
    let lastNetworkState = null;

    /**
     * Generate a unique session ID for grouping logs
     */
    function generateSessionId() {
        return `img-session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Check if URL is from Vercel Blob Storage
     */
    function isVercelBlobUrl(url) {
        if (!url) return false;
        try {
            const urlObj = new URL(url, window.location.origin);
            return urlObj.hostname === VERCEL_BLOB_DOMAIN;
        } catch {
            return url.includes(VERCEL_BLOB_DOMAIN);
        }
    }

    /**
     * Extract filename/path from URL for easier identification
     */
    function getImagePath(url) {
        if (!url) return 'unknown';
        try {
            const urlObj = new URL(url, window.location.origin);
            return urlObj.pathname;
        } catch {
            return url.split(VERCEL_BLOB_DOMAIN)[1] || url;
        }
    }

    /**
     * Get element context (what part of the UI it's in)
     */
    function getElementContext(img) {
        const contexts = [];
        
        // Check for specific known containers
        if (img.closest('#aiBtn')) contexts.push('AI Button');
        if (img.closest('#filterBtn')) contexts.push('Filter Button');
        if (img.closest('#slideoutExpandButton')) contexts.push('Slideout Expand');
        if (img.closest('#slideoutPanel')) contexts.push('Slideout Panel');
        if (img.closest('.pe-fb-ad')) contexts.push('FB Ad Preview');
        if (img.closest('.pe-fb-ad__profile-pic')) contexts.push('Client Logo');
        if (img.closest('.prompt-output-actions')) contexts.push('Prompt Actions');
        if (img.closest('.slideout-to-top-btn')) contexts.push('To Top Button');
        if (img.closest('.marketably-header')) contexts.push('Header');
        if (img.closest('.app-navigation')) contexts.push('Navigation');
        
        // Fallback to parent ID or class
        if (contexts.length === 0) {
            const parent = img.parentElement;
            if (parent?.id) contexts.push(`#${parent.id}`);
            else if (parent?.className) contexts.push(`.${parent.className.split(' ')[0]}`);
            else contexts.push('unknown');
        }
        
        return contexts.join(' > ');
    }

    /**
     * Log an image event
     */
    function logImageEvent(type, img, details = {}) {
        const timestamp = Date.now();
        const entry = {
            type, // 'load_start', 'load_success', 'load_error', 'load_timeout'
            timestamp,
            iso: new Date(timestamp).toISOString(),
            sessionId,
            url: img.src,
            path: getImagePath(img.src),
            context: getElementContext(img),
            naturalWidth: img.naturalWidth || 0,
            naturalHeight: img.naturalHeight || 0,
            complete: img.complete,
            ...details
        };

        loadLogs.push(entry);
        
        // Trim old logs
        if (loadLogs.length > MAX_LOG_ENTRIES) {
            loadLogs.shift();
        }

        // Console logging
        if (LOG_TO_CONSOLE) {
            const color = type === 'load_success' ? '#4CAF50' : 
                         type === 'load_error' ? '#f44336' :
                         type === 'load_timeout' ? '#ff9800' : '#2196F3';
            console.log(
                `%c[ImageMonitor] ${type}`,
                `color: ${color}; font-weight: bold;`,
                entry.path,
                entry.context,
                details
            );
        }

        // #region agent log
        // Send to debug server if available (hypothesisId: network/cdn issues, race conditions, timeouts)
        try {
            fetch(DEBUG_SERVER_ENDPOINT, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    location: 'image-monitor.js:logImageEvent',
                    message: `Image ${type}`,
                    data: entry,
                    timestamp,
                    sessionId,
                    hypothesisId: type === 'load_error' ? 'H1-network' : 
                                  type === 'load_timeout' ? 'H5-timeout' : 'tracking',
                    runId: sessionId
                })
            }).catch(() => {}); // Silently fail if server not running
        } catch {}
        // #endregion agent log
    }

    /**
     * Track an image element
     */
    function trackImage(img) {
        // Skip if already tracked or not a Vercel Blob image
        if (trackedImages.has(img) || !isVercelBlobUrl(img.src)) {
            return;
        }
        
        trackedImages.add(img);
        
        const startTime = performance.now();
        let loadTimeout = null;

        // Log load start
        logImageEvent('load_start', img, {
            startTime,
            alreadyComplete: img.complete,
            alreadyHasNaturalSize: img.naturalWidth > 0
        });

        // If already complete with natural size, it's already loaded successfully
        if (img.complete && img.naturalWidth > 0) {
            logImageEvent('load_success', img, {
                duration: 0,
                cached: true,
                fromComplete: true
            });
            return;
        }

        // Set a timeout to detect stalled loads (hypothesis H5)
        loadTimeout = setTimeout(() => {
            if (!img.complete || img.naturalWidth === 0) {
                logImageEvent('load_timeout', img, {
                    duration: 10000,
                    complete: img.complete,
                    naturalWidth: img.naturalWidth,
                    hypothesisId: 'H5-timeout'
                });
            }
        }, 10000); // 10 second timeout

        // Track load success
        img.addEventListener('load', function onLoad() {
            clearTimeout(loadTimeout);
            const duration = performance.now() - startTime;
            
            // #region agent log
            // Check if image actually loaded with dimensions (hypothesis H2 - race condition)
            const hasValidDimensions = img.naturalWidth > 0 && img.naturalHeight > 0;
            // #endregion agent log
            
            logImageEvent('load_success', img, {
                duration: Math.round(duration),
                cached: duration < 50,
                hasValidDimensions,
                hypothesisId: hasValidDimensions ? 'success' : 'H2-race-condition'
            });
            
            img.removeEventListener('load', onLoad);
        });

        // Track load error
        img.addEventListener('error', function onError(e) {
            clearTimeout(loadTimeout);
            const duration = performance.now() - startTime;
            
            logImageEvent('load_error', img, {
                duration: Math.round(duration),
                errorType: e.type,
                // #region agent log
                // Check network state (hypothesis H4 - DNS)
                // #endregion agent log
                networkState: navigator.onLine ? 'online' : 'offline',
                hypothesisId: navigator.onLine ? 'H1-network' : 'H4-dns'
            });
            
            img.removeEventListener('error', onError);
        });
    }

    /**
     * Scan document for existing images
     */
    function scanExistingImages() {
        const images = document.querySelectorAll('img');
        images.forEach(img => {
            if (isVercelBlobUrl(img.src)) {
                trackImage(img);
            }
        });
    }

    /**
     * Setup MutationObserver to catch dynamically added images
     */
    function setupObserver() {
        if (observer) return;

        observer = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                // Check added nodes
                for (const node of mutation.addedNodes) {
                    if (node.nodeType !== Node.ELEMENT_NODE) continue;
                    
                    // Check if the added node is an image
                    if (node.tagName === 'IMG' && isVercelBlobUrl(node.src)) {
                        trackImage(node);
                    }
                    
                    // Check for images within added nodes
                    const images = node.querySelectorAll?.('img') || [];
                    images.forEach(img => {
                        if (isVercelBlobUrl(img.src)) {
                            trackImage(img);
                        }
                    });
                }
                
                // Check for src attribute changes (hypothesis H2 - race condition from innerHTML replacement)
                if (mutation.type === 'attributes' && 
                    mutation.attributeName === 'src' &&
                    mutation.target.tagName === 'IMG') {
                    const img = mutation.target;
                    if (isVercelBlobUrl(img.src)) {
                        // #region agent log
                        logImageEvent('src_changed', img, {
                            oldSrc: mutation.oldValue,
                            newSrc: img.src,
                            hypothesisId: 'H2-race-condition'
                        });
                        // #endregion agent log
                        // Re-track with new src
                        trackedImages.delete(img);
                        trackImage(img);
                    }
                }
            }
        });

        observer.observe(document.documentElement, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['src'],
            attributeOldValue: true
        });
    }

    /**
     * Monitor network conditions (hypothesis H3 - browser resource constraints, H4 - DNS)
     */
    function startNetworkMonitor() {
        if (networkMonitorInterval) return;
        
        const checkNetwork = () => {
            const networkState = {
                online: navigator.onLine,
                connection: null,
                timestamp: Date.now()
            };
            
            // Get Network Information API data if available (hypothesis H3)
            if (navigator.connection) {
                networkState.connection = {
                    effectiveType: navigator.connection.effectiveType,
                    downlink: navigator.connection.downlink,
                    rtt: navigator.connection.rtt,
                    saveData: navigator.connection.saveData
                };
            }
            
            // Only log if state changed significantly
            const stateChanged = !lastNetworkState || 
                lastNetworkState.online !== networkState.online ||
                lastNetworkState.connection?.effectiveType !== networkState.connection?.effectiveType;
            
            if (stateChanged) {
                lastNetworkState = networkState;
                
                // #region agent log
                fetch(DEBUG_SERVER_ENDPOINT, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        location: 'image-monitor.js:networkMonitor',
                        message: 'Network state changed',
                        data: networkState,
                        timestamp: Date.now(),
                        sessionId,
                        hypothesisId: networkState.online ? 'H3-network-quality' : 'H4-dns-offline'
                    })
                }).catch(() => {});
                // #endregion agent log
                
                console.log('%c[ImageMonitor] Network state', 'color: #FF9800;', networkState);
            }
        };
        
        // Initial check
        checkNetwork();
        
        // Check every 5 seconds
        networkMonitorInterval = setInterval(checkNetwork, 5000);
        
        // Also listen for online/offline events
        window.addEventListener('online', checkNetwork);
        window.addEventListener('offline', checkNetwork);
    }
    
    /**
     * Stop network monitor
     */
    function stopNetworkMonitor() {
        if (networkMonitorInterval) {
            clearInterval(networkMonitorInterval);
            networkMonitorInterval = null;
        }
    }

    /**
     * Enable monitoring
     */
    function enable() {
        if (isEnabled) return;
        
        sessionId = generateSessionId();
        isEnabled = true;
        localStorage.setItem('imageMonitorEnabled', 'true');
        
        console.log('%c[ImageMonitor] Enabled', 'color: #4CAF50; font-weight: bold;', { sessionId });
        
        // #region agent log
        fetch(DEBUG_SERVER_ENDPOINT, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                location: 'image-monitor.js:enable',
                message: 'Image monitoring enabled',
                data: { sessionId, userAgent: navigator.userAgent, url: window.location.href },
                timestamp: Date.now(),
                sessionId,
                hypothesisId: 'session-start'
            })
        }).catch(() => {});
        // #endregion agent log
        
        setupObserver();
        scanExistingImages();
        startNetworkMonitor();
    }

    /**
     * Disable monitoring
     */
    function disable() {
        if (!isEnabled) return;
        
        isEnabled = false;
        localStorage.removeItem('imageMonitorEnabled');
        
        if (observer) {
            observer.disconnect();
            observer = null;
        }
        
        stopNetworkMonitor();
        
        console.log('%c[ImageMonitor] Disabled', 'color: #f44336; font-weight: bold;');
    }

    /**
     * Get all logged events
     */
    function getLogs() {
        return [...loadLogs];
    }

    /**
     * Get summary of load events
     */
    function getSummary() {
        const summary = {
            total: loadLogs.length,
            byType: {},
            byContext: {},
            errors: [],
            timeouts: [],
            avgLoadTime: 0
        };
        
        let totalLoadTime = 0;
        let loadCount = 0;
        
        loadLogs.forEach(log => {
            // Count by type
            summary.byType[log.type] = (summary.byType[log.type] || 0) + 1;
            
            // Count by context
            summary.byContext[log.context] = (summary.byContext[log.context] || 0) + 1;
            
            // Collect errors
            if (log.type === 'load_error') {
                summary.errors.push(log);
            }
            
            // Collect timeouts
            if (log.type === 'load_timeout') {
                summary.timeouts.push(log);
            }
            
            // Calculate avg load time
            if (log.type === 'load_success' && log.duration) {
                totalLoadTime += log.duration;
                loadCount++;
            }
        });
        
        summary.avgLoadTime = loadCount > 0 ? Math.round(totalLoadTime / loadCount) : 0;
        
        return summary;
    }

    /**
     * Clear logs
     */
    function clearLogs() {
        loadLogs.length = 0;
        console.log('%c[ImageMonitor] Logs cleared', 'color: #2196F3; font-weight: bold;');
    }

    /**
     * Print summary to console
     */
    function printSummary() {
        const summary = getSummary();
        console.group('%c[ImageMonitor] Summary', 'color: #2196F3; font-weight: bold;');
        console.log('Session:', sessionId);
        console.log('Total events:', summary.total);
        console.log('By type:', summary.byType);
        console.log('By context:', summary.byContext);
        console.log('Avg load time:', summary.avgLoadTime + 'ms');
        if (summary.errors.length > 0) {
            console.log('%cErrors:', 'color: #f44336; font-weight: bold;', summary.errors);
        }
        if (summary.timeouts.length > 0) {
            console.log('%cTimeouts:', 'color: #ff9800; font-weight: bold;', summary.timeouts);
        }
        console.groupEnd();
        return summary;
    }

    /**
     * Check Vercel Blob Storage connectivity (hypothesis H1 - CDN issues, H4 - DNS)
     */
    async function checkBlobConnectivity() {
        const testUrl = '/images/filter_list.svg';
        const startTime = performance.now();
        
        try {
            const response = await fetch(testUrl, { 
                method: 'HEAD', 
                cache: 'no-store' // Force fresh request
            });
            
            const duration = Math.round(performance.now() - startTime);
            const result = {
                success: response.ok,
                status: response.status,
                duration,
                headers: {
                    'cache-control': response.headers.get('cache-control'),
                    'x-vercel-cache': response.headers.get('x-vercel-cache'),
                    'age': response.headers.get('age')
                },
                timestamp: Date.now()
            };
            
            // #region agent log
            fetch(DEBUG_SERVER_ENDPOINT, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    location: 'image-monitor.js:checkBlobConnectivity',
                    message: 'Blob connectivity check',
                    data: result,
                    timestamp: Date.now(),
                    sessionId,
                    hypothesisId: result.success ? 'H1-cdn-ok' : 'H1-cdn-fail'
                })
            }).catch(() => {});
            // #endregion agent log
            
            console.log('%c[ImageMonitor] Blob connectivity check', 
                        result.success ? 'color: #4CAF50;' : 'color: #f44336;', 
                        result);
            
            return result;
        } catch (error) {
            const duration = Math.round(performance.now() - startTime);
            const result = {
                success: false,
                error: error.message,
                duration,
                timestamp: Date.now()
            };
            
            // #region agent log
            fetch(DEBUG_SERVER_ENDPOINT, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    location: 'image-monitor.js:checkBlobConnectivity',
                    message: 'Blob connectivity check failed',
                    data: result,
                    timestamp: Date.now(),
                    sessionId,
                    hypothesisId: 'H1-cdn-error'
                })
            }).catch(() => {});
            // #endregion agent log
            
            console.log('%c[ImageMonitor] Blob connectivity check FAILED', 'color: #f44336;', result);
            
            return result;
        }
    }

    /**
     * Force reload all Vercel Blob images (useful when debugging)
     */
    function reloadAllImages() {
        const images = document.querySelectorAll('img');
        let count = 0;
        
        images.forEach(img => {
            if (isVercelBlobUrl(img.src)) {
                // Add cache-busting parameter
                const url = new URL(img.src);
                url.searchParams.set('_reload', Date.now());
                img.src = url.toString();
                count++;
            }
        });
        
        console.log(`%c[ImageMonitor] Reloaded ${count} Vercel Blob images`, 'color: #2196F3;');
        
        return count;
    }

    // Export API
    window.ImageMonitor = {
        enable,
        disable,
        getLogs,
        getSummary,
        printSummary,
        clearLogs,
        checkBlobConnectivity,
        reloadAllImages,
        isEnabled: () => isEnabled,
        getSessionId: () => sessionId
    };

    // Auto-enable if previously enabled
    if (localStorage.getItem('imageMonitorEnabled') === 'true') {
        // Delay to ensure DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', enable);
        } else {
            enable();
        }
    }

    console.log('%c[ImageMonitor] Module loaded. Call ImageMonitor.enable() to start monitoring.', 
                'color: #9E9E9E; font-style: italic;');
})();
