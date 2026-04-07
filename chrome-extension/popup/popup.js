/**
 * Vizualizd Ad Library Importer — Popup Script
 * Handles auth, client selection, extraction trigger, and import.
 * Media upload runs in the service worker so it survives popup close.
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
const progressSection = $("#progressSection");
const emailInput = $("#emailInput");
const sendLinkBtn = $("#sendLinkBtn");
const loginMessage = $("#loginMessage");
const waitingSection = $("#waitingSection");
const waitingEmail = $("#waitingEmail");
const userEmail = $("#userEmail");
const logoutBtn = $("#logoutBtn");
const clientSelect = $("#clientSelect");
const extractBtn = $("#extractBtn");
const extractResult = $("#extractResult");
const extractCount = $("#extractCount");
const importBtn = $("#importBtn");
const statusMessage = $("#statusMessage");
const progressFill = $("#progressFill");
const progressLabel = $("#progressLabel");

// ---- Helpers ----
function showMessage(el, text, type = "info") {
  el.textContent = text;
  el.className = `message message--${type}`;
  el.style.display = "block";
}

function hideMessage(el) {
  el.style.display = "none";
}

function hideAllSections() {
  loginSection.style.display = "none";
  mainSection.style.display = "none";
  wrongPageSection.style.display = "none";
  waitingSection.style.display = "none";
  progressSection.style.display = "none";
}

async function getToken() {
  const data = await chrome.storage.local.get("vzd_token");
  return data.vzd_token || null;
}

async function setToken(token) {
  await chrome.storage.local.set({ vzd_token: token });
}

async function clearToken() {
  await chrome.storage.local.remove(["vzd_token", "vzd_email", "vzd_magic_link_pending"]);
}

async function apiFetch(path, options = {}) {
  const token = await getToken();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  return res;
}

// ---- Check if import is in progress ----
async function checkImportState() {
  try {
    const response = await chrome.runtime.sendMessage({ action: "getImportState" });
    const state = response?.state;
    if (!state || state.status === "idle") return false;

    if (state.status === "uploading" || state.status === "importing") {
      showProgress(state);
      return true;
    }

    if (state.status === "done") {
      showDone(state);
      return true;
    }

    if (state.status === "error") {
      showError(state);
      return true;
    }
  } catch {
    // Service worker not responding
  }
  return false;
}

function showProgress(state) {
  hideAllSections();
  progressSection.style.display = "block";
  const pct = state.totalMedia > 0 ? Math.round((state.uploadedMedia / state.totalMedia) * 100) : 0;
  progressFill.style.width = pct + "%";
  if (state.status === "uploading") {
    progressLabel.textContent = `Uploading media ${state.uploadedMedia}/${state.totalMedia}`;
  } else {
    progressLabel.textContent = "Saving import...";
  }
}

function showDone(state) {
  hideAllSections();
  mainSection.style.display = "block";
  let msg = `Imported ${state.adCount} ads with ${state.mediaCount} media items.`;
  if (state.skippedCount > 0) msg += ` ${state.skippedCount} duplicates skipped.`;
  showMessage(statusMessage, msg, "success");
  extractResult.style.display = "none";
  extractedAds = null;
  // Reset service worker state
  chrome.runtime.sendMessage({ action: "resetImportState" }).catch(() => {});
}

function showError(state) {
  hideAllSections();
  mainSection.style.display = "block";
  showMessage(statusMessage, "Import failed: " + (state.error || "Unknown error"), "error");
  // Reset service worker state
  chrome.runtime.sendMessage({ action: "resetImportState" }).catch(() => {});
}

// ---- Auth ----
async function checkAuth() {
  // First check if an import is running
  const importing = await checkImportState();
  if (importing) return;

  const token = await getToken();
  if (!token) {
    const { vzd_magic_link_pending } = await chrome.storage.local.get("vzd_magic_link_pending");
    if (vzd_magic_link_pending) {
      showWaiting(vzd_magic_link_pending);
    } else {
      showLogin();
    }
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
    await chrome.storage.local.remove("vzd_magic_link_pending");
    showMain(user);
  } catch {
    showLogin();
  }
}

function showLogin() {
  hideAllSections();
  loginSection.style.display = "block";
}

function showWaiting(email) {
  hideAllSections();
  waitingSection.style.display = "block";
  waitingEmail.textContent = email;
}

async function showMain(user) {
  hideAllSections();
  mainSection.style.display = "block";
  userEmail.textContent = user.email || "";

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
  let clients = user.accessible_clients || [];

  if (user.is_founder) {
    try {
      const res = await apiFetch("/api/clients");
      if (res.ok) {
        const allClients = await res.json();
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

  clients.sort((a, b) => {
    const nameA = (a.name || a.client_name || "").toLowerCase();
    const nameB = (b.name || b.client_name || "").toLowerCase();
    return nameA.localeCompare(nameB);
  });

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
      await chrome.storage.local.set({ vzd_magic_link_pending: email });
      showWaiting(email);
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

$("#resetAuthBtn")?.addEventListener("click", async () => {
  await chrome.storage.local.remove("vzd_magic_link_pending");
  showLogin();
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

// ---- Import (delegate to service worker) ----
importBtn.addEventListener("click", async () => {
  if (!extractedAds || !clientSelect.value) return;
  hideMessage(statusMessage);

  // Get the FB Ads Library tab ID so service worker can route video downloads
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  // Send to service worker for background processing
  const response = await chrome.runtime.sendMessage({
    action: "startImport",
    ads: extractedAds,
    sourceUrl: extractedUrl || "",
    clientId: clientSelect.value,
    tabId: tab?.id || null,
  });

  if (response?.started === false) {
    showMessage(statusMessage, response.error || "Cannot start import right now.", "error");
    return;
  }

  // Show progress immediately
  showProgress({ status: "uploading", uploadedMedia: 0, totalMedia: 0 });
});

// ---- Listen for progress updates from service worker ----
chrome.runtime.onMessage.addListener((message) => {
  if (message.action === "importProgress") {
    const state = message.state;
    if (state.status === "uploading" || state.status === "importing") {
      showProgress(state);
    } else if (state.status === "done") {
      showDone(state);
    } else if (state.status === "error") {
      showError(state);
    }
  }
});

// ---- Listen for auth changes ----
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "local" && changes.vzd_token?.newValue) {
    checkAuth();
  }
});

// ---- Init ----
checkAuth();
