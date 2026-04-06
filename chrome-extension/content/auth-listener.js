/**
 * Vizualizd Auth Listener — Content Script
 * Runs on the Vizualizd app domain.
 *
 * When the user clicks a magic link in their email, the app verifies it and
 * stores the JWT in localStorage. This script detects that and copies the
 * token to chrome.storage.local so the extension popup can use it.
 *
 * This avoids competing with the app's own verify call (token can only be
 * used once).
 */

(() => {
  const AUTH_TOKEN_KEY = "visualizd_auth_token";
  const CHECK_INTERVAL = 500;
  const MAX_CHECKS = 30; // 15 seconds max

  let checks = 0;

  function checkForToken() {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    if (token) {
      chrome.storage.local.set({
        vzd_token: token,
      });
      return;
    }

    checks++;
    if (checks < MAX_CHECKS) {
      setTimeout(checkForToken, CHECK_INTERVAL);
    }
  }

  // Only run if the page was loaded with magic link params
  const params = new URLSearchParams(window.location.search);
  if (params.has("token") && params.has("email")) {
    // Wait a moment for the app's auth flow to complete, then start checking
    setTimeout(checkForToken, 1000);
  } else {
    // Even without magic link params, check if there's already a token
    // (user might already be logged into the app)
    const existingToken = localStorage.getItem(AUTH_TOKEN_KEY);
    if (existingToken) {
      chrome.storage.local.get("vzd_token", (data) => {
        if (!data.vzd_token) {
          chrome.storage.local.set({ vzd_token: existingToken });
        }
      });
    }
  }
})();
