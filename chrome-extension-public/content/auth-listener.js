/**
 * MapTheGap Auth Listener — Content Script
 * Runs on the MapTheGap app domain.
 *
 * Polls localStorage for the JWT after the app's auth flow completes.
 * Copies it to chrome.storage.local so the extension popup can use it.
 *
 * We can't check URL params because the app strips ?token=&email= via
 * history.replaceState before this content script runs.
 */

(() => {
  const AUTH_TOKEN_KEY = "visualizd_auth_token";
  const CHECK_INTERVAL = 500;
  const MAX_CHECKS = 30; // 15 seconds max
  let checks = 0;

  function checkForToken() {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    if (token) {
      console.log("[MTG auth-listener] Found token in localStorage, copying to chrome.storage");
      chrome.storage.local.get("vzd_token", (data) => {
        if (data.vzd_token !== token) {
          console.log("[MTG auth-listener] Token is new, setting chrome.storage.local.vzd_token");
          chrome.storage.local.set({ vzd_token: token });
        } else {
          console.log("[MTG auth-listener] Token already matches chrome.storage");
        }
      });
      return;
    }
    checks++;
    if (checks < MAX_CHECKS) {
      setTimeout(checkForToken, CHECK_INTERVAL);
    }
  }

  // Always poll — don't rely on URL params (app strips them before we run)
  checkForToken();
})();
