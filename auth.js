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

    if (!response.ok) {
      let message = 'Unable to send magic link.';
      try {
        const error = await response.json();
        message = error.detail || error.message || message;
      } catch (error) {
        console.error('Failed to parse magic-link error', error);
      }
      throw new Error(message);
    }

    return response.json();
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
      showLoginMessages({
        error:
          error.message ||
          'We could not send a magic link. Please contact support.',
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

  const processMagicLinkIfPresent = async () => {
    const params = new URLSearchParams(global.location.search);
    const token = params.get('token');
    const email = params.get('email');

    if (!token || !email) {
      return false;
    }

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

      // Remove magic link params from URL
      const cleanUrl = global.location.pathname + global.location.hash;
      global.history.replaceState({}, global.document.title, cleanUrl);

      global.dispatchEvent(
        new CustomEvent('auth:magicVerified', { detail: { user: userInfo } })
      );
      return true;
    } catch (error) {
      console.error('Failed to process magic link', error);
      clearAuth();
      showLoginMessages({
        error:
          error.message ||
          'We could not verify your magic link. Please request a new one.',
        success: null,
      });
      return false;
    }
  };

  const checkAuth = async () => {
    const impersonated = await processImpersonationTokenIfPresent();
    if (impersonated) {
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


