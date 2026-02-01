/**
 * Frontend Configuration
 * This static file provides defaults for local development.
 * In production, the backend serves this dynamically with environment-specific values.
 * If the dynamic route isn't available, this auto-detects the environment.
 */
window.APP_CONFIG = {
    API_BASE_URL: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
        ? 'http://localhost:8000'
        : 'https://www.mapthegap.ai'
};
