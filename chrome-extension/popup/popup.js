/**
 * Vizualizd Ad Library Importer — Popup Script
 * Handles auth, client selection, extraction trigger, and import.
 */

const API_BASE = "https://api.mapthegap.ai";
// const API_BASE = "http://localhost:8000"; // uncomment for local dev

const $ = (sel) => document.querySelector(sel);

// ---- State ----
let extractedAds = null;
let extractedUrl = null;

// ---- DOM refs ----
const loginSection = $("#loginSection");
const mainSection = $("#mainSection");
const wrongPageSection = $("#wrongPageSection");
const emailInput = $("#emailInput");
const sendLinkBtn = $("#sendLinkBtn");
const loginMessage = $("#loginMessage");
const verifySection = $("#verifySection");
const tokenInput = $("#tokenInput");
const verifyBtn = $("#verifyBtn");
const userEmail = $("#userEmail");
const logoutBtn = $("#logoutBtn");
const clientSelect = $("#clientSelect");
const extractBtn = $("#extractBtn");
const extractResult = $("#extractResult");
const extractCount = $("#extractCount");
const importBtn = $("#importBtn");
const statusMessage = $("#statusMessage");

// ---- Helpers ----
function showMessage(el, text, type = "info") {
  el.textContent = text;
  el.className = `message message--${type}`;
  el.style.display = "block";
}

function hideMessage(el) {
  el.style.display = "none";
}

async function getToken() {
  const data = await chrome.storage.local.get("vzd_token");
  return data.vzd_token || null;
}

async function setToken(token) {
  await chrome.storage.local.set({ vzd_token: token });
}

async function clearToken() {
  await chrome.storage.local.remove("vzd_token");
}

async function apiFetch(path, options = {}) {
  const token = await getToken();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  return res;
}

// ---- Auth ----
async function checkAuth() {
  const token = await getToken();
  if (!token) {
    showLogin();
    return;
  }
  try {
    const res = await apiFetch("/api/auth/me");
    if (!res.ok) {
      await clearToken();
      showLogin();
      return;
    }
    const user = await res.json();
    showMain(user);
  } catch {
    showLogin();
  }
}

function showLogin() {
  loginSection.style.display = "block";
  mainSection.style.display = "none";
  wrongPageSection.style.display = "none";
}

async function showMain(user) {
  loginSection.style.display = "none";
  mainSection.style.display = "block";
  wrongPageSection.style.display = "none";
  userEmail.textContent = user.email || "";

  // Check if we're on a Meta Ads Library page
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const isAdsLibrary = tab?.url?.includes("facebook.com/ads/library");
  if (!isAdsLibrary) {
    mainSection.style.display = "none";
    wrongPageSection.style.display = "block";
    return;
  }

  await loadClients(user);
}

async function loadClients(user) {
  clientSelect.innerHTML = '<option value="">Select a brand</option>';

  // Use accessible_clients from /me response, plus fetch all clients if founder
  let clients = user.accessible_clients || [];

  // If founder, also fetch all clients (which includes ad_library_only)
  if (user.is_founder) {
    try {
      const res = await apiFetch("/api/clients");
      if (res.ok) {
        const allClients = await res.json();
        // Merge, dedup by id
        const seen = new Set(clients.map((c) => c.id || c.client_id));
        for (const c of allClients) {
          const cid = c.id || c.client_id;
          if (!seen.has(cid)) {
            clients.push(c);
            seen.add(cid);
          }
        }
      }
    } catch {}
  }

  for (const c of clients) {
    const opt = document.createElement("option");
    opt.value = c.id || c.client_id;
    const label = c.name || c.client_name || "Unknown";
    const suffix = c.ad_library_only ? " (Diagnosis)" : "";
    opt.textContent = label + suffix;
    clientSelect.appendChild(opt);
  }

  clientSelect.addEventListener("change", () => {
    extractBtn.disabled = !clientSelect.value;
    extractResult.style.display = "none";
    hideMessage(statusMessage);
  });
}

// ---- Magic link auth ----
sendLinkBtn.addEventListener("click", async () => {
  const email = emailInput.value.trim();
  if (!email) return;
  sendLinkBtn.disabled = true;
  hideMessage(loginMessage);
  try {
    const res = await fetch(`${API_BASE}/api/auth/magic-link/request`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    if (res.ok) {
      showMessage(loginMessage, "Check your email for the magic link.", "success");
      verifySection.style.display = "block";
    } else {
      const data = await res.json().catch(() => ({}));
      showMessage(loginMessage, data.detail || "Failed to send magic link.", "error");
    }
  } catch (err) {
    showMessage(loginMessage, "Network error. Check your connection.", "error");
  } finally {
    sendLinkBtn.disabled = false;
  }
});

verifyBtn.addEventListener("click", async () => {
  const email = emailInput.value.trim();
  let token = tokenInput.value.trim();
  if (!email || !token) return;

  // If they pasted the full URL, extract the token param
  if (token.includes("token=")) {
    try {
      const url = new URL(token);
      token = url.searchParams.get("token") || token;
    } catch {
      const match = token.match(/token=([^&]+)/);
      if (match) token = decodeURIComponent(match[1]);
    }
  }

  verifyBtn.disabled = true;
  try {
    const res = await fetch(`${API_BASE}/api/auth/magic-link/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, token }),
    });
    if (res.ok) {
      const data = await res.json();
      await setToken(data.access_token);
      await checkAuth();
    } else {
      const data = await res.json().catch(() => ({}));
      showMessage(loginMessage, data.detail || "Invalid or expired token.", "error");
    }
  } catch {
    showMessage(loginMessage, "Network error.", "error");
  } finally {
    verifyBtn.disabled = false;
  }
});

// ---- Logout ----
logoutBtn.addEventListener("click", async () => {
  await clearToken();
  extractedAds = null;
  extractResult.style.display = "none";
  hideMessage(statusMessage);
  showLogin();
});

// ---- Extract ----
extractBtn.addEventListener("click", async () => {
  extractBtn.disabled = true;
  extractBtn.textContent = "Extracting...";
  hideMessage(statusMessage);
  extractResult.style.display = "none";

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const response = await chrome.tabs.sendMessage(tab.id, { action: "extractAds" });

    if (!response || !response.success) {
      showMessage(statusMessage, response?.error || "Extraction failed. Try refreshing the page.", "error");
      return;
    }

    extractedAds = response.ads;
    extractedUrl = response.url;

    const mediaCount = extractedAds.reduce(
      (sum, ad) => sum + (ad.media_items?.length || 0), 0
    );
    extractCount.textContent = `Found ${extractedAds.length} ads with ${mediaCount} media items`;
    extractResult.style.display = "block";
  } catch (err) {
    showMessage(
      statusMessage,
      "Could not connect to page. Try refreshing the Meta Ads Library page.",
      "error"
    );
  } finally {
    extractBtn.disabled = !clientSelect.value;
    extractBtn.textContent = "Extract Ads from Page";
  }
});

// ---- Import ----
importBtn.addEventListener("click", async () => {
  if (!extractedAds || !clientSelect.value) return;
  importBtn.disabled = true;
  importBtn.textContent = "Importing...";
  hideMessage(statusMessage);

  try {
    const res = await apiFetch(
      `/api/clients/${clientSelect.value}/ad-library-imports/from-extension`,
      {
        method: "POST",
        body: JSON.stringify({
          source_url: extractedUrl || window.location.href,
          ads: extractedAds,
        }),
      }
    );

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      showMessage(statusMessage, data.detail || `Import failed (${res.status})`, "error");
      return;
    }

    const data = await res.json();
    let msg = `Imported ${data.ad_count} ads with ${data.media_count} media items.`;
    if (data.skipped_count > 0) {
      msg += ` ${data.skipped_count} duplicates skipped.`;
    }
    msg += " Media files are being processed in the background.";
    showMessage(statusMessage, msg, "success");
    extractResult.style.display = "none";
    extractedAds = null;
  } catch (err) {
    showMessage(statusMessage, "Network error: " + err.message, "error");
  } finally {
    importBtn.disabled = false;
    importBtn.textContent = "Import";
  }
});

// ---- Init ----
checkAuth();
