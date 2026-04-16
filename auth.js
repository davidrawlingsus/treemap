(function (global) {
  const AUTH_TOKEN_KEY = 'visualizd_auth_token';
  const USER_INFO_KEY = 'visualizd_user_info';

  const getApiBaseUrl = () =>
    (global.APP_CONFIG && global.APP_CONFIG.API_BASE_URL) ||
    'http://localhost:8000';

  const getAuthToken = () => global.localStorage.getItem(AUTH_TOKEN_KEY);

  const setAuthToken = (token) => {
    if (token) {
      global.localStorage.setItem(AUTH_TOKEN_KEY, token);
    } else {
      global.localStorage.removeItem(AUTH_TOKEN_KEY);
    }
  };

  const setUserInfo = (userInfo) => {
    if (userInfo) {
      global.localStorage.setItem(USER_INFO_KEY, JSON.stringify(userInfo));
    } else {
      global.localStorage.removeItem(USER_INFO_KEY);
    }
  };

  const getStoredUserInfo = () => {
    const raw = global.localStorage.getItem(USER_INFO_KEY);
    if (!raw) {
      return null;
    }
    try {
      return JSON.parse(raw);
    } catch (error) {
      console.error('Failed to parse stored user info', error);
      global.localStorage.removeItem(USER_INFO_KEY);
      return null;
    }
  };

  const clearAuth = () => {
    global.localStorage.removeItem(AUTH_TOKEN_KEY);
    global.localStorage.removeItem(USER_INFO_KEY);
  };

  const getAuthHeaders = () => {
    const token = getAuthToken();
    return token
      ? {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        }
      : { 'Content-Type': 'application/json' };
  };

  const showLoginMessages = ({ error, success }) => {
    const errorEl = global.document.getElementById('loginError');
    const successEl = global.document.getElementById('loginSuccess');

    if (errorEl) {
      if (error) {
        errorEl.textContent = error;
        errorEl.style.display = 'block';
      } else {
        errorEl.textContent = '';
        errorEl.style.display = 'none';
      }
    }

    if (successEl) {
      if (success) {
        successEl.textContent = success;
        successEl.style.display = 'block';
      } else {
        successEl.textContent = '';
        successEl.style.display = 'none';
      }
    }
  };

  const resetLoginForm = () => {
    const emailInput = global.document.getElementById('loginEmail');
    const loginButton = global.document.getElementById('loginButton');
    if (emailInput) {
      emailInput.disabled = false;
    }
    if (loginButton) {
      loginButton.disabled = false;
      loginButton.textContent = 'Send Magic Link';
    }
    showLoginMessages({ error: null, success: null });
  };

  const showLogin = () => {
    const overlay = global.document.getElementById('loginOverlay');
    const mainContainer = global.document.getElementById('mainContainer');
    const formSection = global.document.getElementById('loginFormSection');
    const accountSection = global.document.getElementById(
      'accountSelectionSection'
    );
    const loginContainer = global.document.querySelector('.login-container');
    const accountSelectionList = global.document.getElementById(
      'accountSelectionList'
    );
    const accountSelectionGreeting = global.document.getElementById(
      'accountSelectionGreeting'
    );

    if (mainContainer) {
      mainContainer.style.display = 'none';
    }
    if (overlay) {
      overlay.classList.remove('hidden');
    }
    if (formSection) {
      formSection.classList.remove('hidden');
    }
    if (accountSection) {
      accountSection.classList.add('hidden');
    }
    if (loginContainer) {
      loginContainer.classList.remove('account-selection-mode');
    }
    if (accountSelectionGreeting) {
      accountSelectionGreeting.textContent = '';
    }
    if (accountSelectionList) {
      accountSelectionList.innerHTML = '';
    }
    resetLoginForm();
  };

  const hideLogin = () => {
    const overlay = global.document.getElementById('loginOverlay');
    if (overlay) {
      overlay.classList.add('hidden');
    }
    const formSection = global.document.getElementById('loginFormSection');
    if (formSection) {
      formSection.classList.remove('hidden');
    }
  };

  const requestMagicLink = async (email) => {
    const response = await fetch(
      `${getApiBaseUrl()}/api/auth/magic-link/request`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      }
    );
    const text = await response.text();
    let responseBody = null;
    try { responseBody = JSON.parse(text); } catch (_) { responseBody = { _raw: text.slice(0, 200) }; }
    if (!response.ok) {
      const message = (responseBody && (responseBody.detail || responseBody.message)) || 'Unable to send magic link.';
      throw new Error(message);
    }

    return responseBody;
  };

  const verifyMagicLink = async (email, token) => {
    const response = await fetch(
      `${getApiBaseUrl()}/api/auth/magic-link/verify`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, token }),
      }
    );

    if (!response.ok) {
      let message = 'Invalid or expired magic link.';
      try {
        const error = await response.json();
        message = error.detail || error.message || message;
      } catch (error) {
        console.error('Failed to parse verification error', error);
      }
      throw new Error(message);
    }

    return response.json();
  };

  const fetchCurrentUser = async () => {
    const response = await fetch(`${getApiBaseUrl()}/api/auth/me`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      throw new Error('Unable to fetch current user');
    }
    return response.json();
  };

  const handleLogin = async () => {
    const emailInput = global.document.getElementById('loginEmail');
    const loginButton = global.document.getElementById('loginButton');

    if (!emailInput) {
      throw new Error('Login email input not found');
    }

    const email = (emailInput.value || '').trim().toLowerCase();
    if (!email) {
      showLoginMessages({ error: 'Please enter your email address.' });
      return;
    }

    showLoginMessages({ error: null, success: null });
    emailInput.disabled = true;
    if (loginButton) {
      loginButton.disabled = true;
      loginButton.textContent = 'Sending...';
    }

    try {
      const { expires_at: expiresAt } = await requestMagicLink(email);
      const expiresText = expiresAt
        ? new Date(expiresAt).toLocaleString()
        : 'approximately 1 hour';
      showLoginMessages({
        success: `Magic link sent to ${email}. It expires ${expiresAt ? `at ${expiresText}` : 'soon'}.`,
      });
    } catch (error) {
      console.error('Magic-link request failed', error);
      const isNetworkError = (error && error.message === 'Failed to fetch') ||
        (error && typeof error.message === 'string' && error.message.toLowerCase().includes('network'));
      const userMessage = isNetworkError
        ? 'Could not reach the server. If you\'re running locally, make sure the backend is started (e.g. port 8000).'
        : (error.message || 'We could not send a magic link. Please contact support.');
      showLoginMessages({
        error: userMessage,
      });
    } finally {
      if (emailInput) {
        emailInput.disabled = false;
      }
      if (loginButton) {
        loginButton.disabled = false;
        loginButton.textContent = 'Send Magic Link';
      }
    }
  };

  const processImpersonationTokenIfPresent = async () => {
    const params = new URLSearchParams(global.location.search);
    const impersonationToken = params.get('impersonationToken');

    if (!impersonationToken) {
      return false;
    }

    try {
      setAuthToken(impersonationToken);
      const userInfo = await fetchCurrentUser();
      setUserInfo(userInfo);

      params.delete('impersonationToken');
      const cleanUrl = `${global.location.pathname}${params.toString() ? `?${params.toString()}` : ''}${global.location.hash}`;
      global.history.replaceState({}, global.document.title, cleanUrl);

      global.dispatchEvent(
        new CustomEvent('auth:authenticated', { detail: { user: userInfo } })
      );
      return true;
    } catch (error) {
      console.error('Failed to process impersonation token', error);
      clearAuth();
      showLogin();
      return false;
    }
  };

  const showExtensionRedirect = () => {
    // Replace the entire page to prevent app router from overriding
    global.document.title = 'MapTheGap — Verified';
    global.document.body.innerHTML = `
      <div style="position:fixed;inset:0;background:#0F1B28;display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:Lato,-apple-system,BlinkMacSystemFont,sans-serif;">
        <div style="text-align:center;max-width:400px;padding:40px;">
          <div style="font-size:28px;font-weight:900;margin-bottom:8px;">
            <span style="color:#B9F040;">Map</span><span style="color:#fff;">The</span><span style="color:#B9F040;">Gap</span>
          </div>
          <div style="width:48px;height:48px;background:#B9F040;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:24px auto;">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M5 13l4 4L19 7" stroke="#0F1B28" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </div>
          <h2 style="color:#fff;font-size:22px;font-weight:700;margin:0 0 12px;">You're verified!</h2>
          <p style="color:rgba(255,255,255,0.7);font-size:15px;line-height:1.5;margin:0 0 24px;">Switch back to your <strong style="color:#fff;">Facebook Ads Library</strong> tab to see your full analysis.</p>
          <p style="color:rgba(255,255,255,0.4);font-size:13px;margin:0;">The extension unlocks automatically.</p>
        </div>
      </div>
    `;
  };

  const processMagicLinkIfPresent = async () => {
    const params = new URLSearchParams(global.location.search);
    const token = params.get('token');
    const email = params.get('email');
    const source = params.get('source');

    if (!token || !email) {
      return false;
    }

    // Create unique key for this magic link token
    const magicLinkKey = `magic_link_${token.substring(0, 10)}`;
    
    // Check if this specific token is already being processed or was processed
    const processingState = global.sessionStorage.getItem(magicLinkKey);
    
    if (processingState === 'processing' || processingState === 'completed') {
      console.log('[MAGIC LINK] Already processed, skipping');
      return processingState === 'completed';
    }

    // Mark as processing IMMEDIATELY to prevent duplicate processing
    global.sessionStorage.setItem(magicLinkKey, 'processing');

    // Remove only magic-link params to prevent duplicate verification attempts,
    // while preserving routing params (e.g. mode=leads&run_id=...).
    params.delete('token');
    params.delete('email');
    const cleanUrl = `${global.location.pathname}${params.toString() ? `?${params.toString()}` : ''}${global.location.hash}`;
    global.history.replaceState({}, global.document.title, cleanUrl);

    showLogin();
    showLoginMessages({
      success: 'Verifying your secure link...',
      error: null,
    });

    try {
      const result = await verifyMagicLink(email.trim().toLowerCase(), token);
      setAuthToken(result.access_token);

      const userInfo = await fetchCurrentUser();
      setUserInfo(userInfo);

      showLoginMessages({ error: null, success: null });

      global.dispatchEvent(
        new CustomEvent('auth:magicVerified', { detail: { user: userInfo } })
      );

      // Mark as completed in sessionStorage
      global.sessionStorage.setItem(magicLinkKey, 'completed');

      // If this magic link was initiated from the extension, show a "go back" page
      if (source === 'extension') {
        showExtensionRedirect();
      }

      return true;
    } catch (error) {
      console.error('Failed to process magic link', error);
      
      // Check if we already have a valid session BEFORE clearing auth
      const existingToken = getAuthToken();
      if (existingToken) {
        try {
          const userInfo = await fetchCurrentUser();
          setUserInfo(userInfo);
          global.dispatchEvent(
            new CustomEvent('auth:authenticated', { detail: { user: userInfo } })
          );
          
          // Mark as completed since we have a valid session
          global.sessionStorage.setItem(magicLinkKey, 'completed');
          
          return true;
        } catch (e) {
          // Fall through to show error
        }
      }
      
      clearAuth();
      showLoginMessages({
        error:
          error.message ||
          'We could not verify your magic link. Please request a new one.',
        success: null,
      });
      
      // Remove processing flag on failure to allow retry
      global.sessionStorage.removeItem(magicLinkKey);
      
      return false;
    }
  };

  const processRunAuthTokenIfPresent = async () => {
    const params = new URLSearchParams(global.location.search);
    const authToken = params.get('auth');
    if (!authToken) return false;

    // Prevent duplicate processing
    const authKey = `run_auth_${authToken.substring(0, 10)}`;
    const state = global.sessionStorage.getItem(authKey);
    if (state === 'processing' || state === 'completed') {
      return state === 'completed';
    }
    global.sessionStorage.setItem(authKey, 'processing');

    // Clean auth param from URL, keep client_uuid and hash
    params.delete('auth');
    const cleanUrl = `${global.location.pathname}${params.toString() ? `?${params.toString()}` : ''}${global.location.hash}`;
    global.history.replaceState({}, global.document.title, cleanUrl);

    try {
      const resp = await fetch(`${getApiBaseUrl()}/api/auth/run-token/verify?token=${encodeURIComponent(authToken)}`, {
        method: 'GET',
      });
      if (!resp.ok) throw new Error('Invalid run token');
      const result = await resp.json();
      setAuthToken(result.access_token);

      const userInfo = await fetchCurrentUser();
      setUserInfo(userInfo);

      global.dispatchEvent(
        new CustomEvent('auth:authenticated', { detail: { user: userInfo } })
      );

      global.sessionStorage.setItem(authKey, 'completed');
      return true;
    } catch (error) {
      console.error('[RUN AUTH] Failed to verify run token', error);
      global.sessionStorage.removeItem(authKey);
      return false;
    }
  };

  const checkAuth = async () => {
    const impersonated = await processImpersonationTokenIfPresent();
    if (impersonated) {
      hideLogin();
      return true;
    }

    const runAuthed = await processRunAuthTokenIfPresent();
    if (runAuthed) {
      hideLogin();
      return true;
    }

    await processMagicLinkIfPresent();

    const token = getAuthToken();
    if (!token) {
      showLogin();
      return false;
    }

    try {
      const userInfo = await fetchCurrentUser();
      setUserInfo(userInfo);
      global.dispatchEvent(
        new CustomEvent('auth:authenticated', { detail: { user: userInfo } })
      );
      return true;
    } catch (error) {
      console.error('Authentication validation failed', error);
      clearAuth();
      showLogin();
      return false;
    }
  };

  const handleLogout = () => {
    clearAuth();
    setUserInfo(null);
    showLogin();
    global.dispatchEvent(new Event('auth:logout'));
    global.location.href = 'https://mapthegap.ai';
  };

  const initLoginForm = () => {
    const emailInput = global.document.getElementById('loginEmail');
    const loginButton = global.document.getElementById('loginButton');

    if (emailInput) {
      emailInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
          handleLogin();
        }
      });
    }

    if (loginButton) {
      loginButton.addEventListener('click', handleLogin);
    }
  };

  // Expose API
  const api = {
    AUTH_TOKEN_KEY,
    USER_INFO_KEY,
    getApiBaseUrl,
    getAuthToken,
    setAuthToken,
    clearAuth,
    getAuthHeaders,
    handleLogin,
    checkAuth,
    handleLogout,
    requestMagicLink,
    verifyMagicLink,
    fetchCurrentUser,
    getStoredUserInfo,
    setUserInfo,
    showLogin,
    hideLogin,
    processMagicLinkIfPresent,
    processRunAuthTokenIfPresent,
    initLoginForm,
  };

  global.Auth = api;

  // Backwards compatibility for existing code paths
  global.getAuthToken = getAuthToken;
  global.setAuthToken = setAuthToken;
  global.clearAuth = clearAuth;
  global.getAuthHeaders = getAuthHeaders;
  global.handleLogin = handleLogin;
  global.checkAuth = checkAuth;
  global.handleLogout = handleLogout;
  global.showLogin = showLogin;

  global.addEventListener('DOMContentLoaded', initLoginForm);
})(window);


