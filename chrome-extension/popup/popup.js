/**
 * MapTheGap Ad Library Importer — Popup Script
 * Handles auth, client selection, extraction trigger, import, and ad analysis.
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
const analysisSection = $("#analysisSection");
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
const analyzeBtn = $("#analyzeBtn");
const statusMessage = $("#statusMessage");
const progressFill = $("#progressFill");
const progressLabel = $("#progressLabel");
const leadgenToggle = $("#leadgenToggle");
const leadgenInfo = $("#leadgenInfo");
const leadgenEmail = $("#leadgenEmail");
const clientGroup = $("#clientGroup");
const analysisBackBtn = $("#analysisBackBtn");

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
  analysisSection.style.display = "none";
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
  let msg;
  if (state.leadgenStarted) {
    msg = `Lead gen pipeline started for ${state.companyName || "company"}. Results will be sent to ${userEmail.textContent}.`;
  } else {
    msg = `Imported ${state.adCount} ads with ${state.mediaCount} media items.`;
    if (state.skippedCount > 0) msg += ` ${state.skippedCount} duplicates skipped.`;
  }
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

  // Only show lead gen toggle for founder users
  const leadgenLabel = $("#leadgenLabel");
  if (leadgenLabel) {
    leadgenLabel.style.display = user.is_founder ? "flex" : "none";
  }

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
          // Skip lead clients (auto-generated from lead gen pipeline)
          if (c.is_lead) continue;
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
    extractBtn.disabled = !leadgenToggle.checked && !clientSelect.value;
    extractResult.style.display = "none";
    hideMessage(statusMessage);
  });
}

// ---- Lead gen toggle ----
leadgenToggle.addEventListener("change", () => {
  const checked = leadgenToggle.checked;
  clientGroup.style.display = checked ? "none" : "block";
  leadgenInfo.style.display = checked ? "block" : "none";
  if (checked) {
    leadgenEmail.textContent = userEmail.textContent;
    extractBtn.disabled = false;
  } else {
    extractBtn.disabled = !clientSelect.value;
  }
  extractResult.style.display = "none";
  hideMessage(statusMessage);
});

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
    extractBtn.disabled = !leadgenToggle.checked && !clientSelect.value;
    extractBtn.textContent = "Extract Ads from Page";
  }
});

// ---- Import (delegate to service worker) ----
importBtn.addEventListener("click", async () => {
  const isLeadgen = leadgenToggle.checked;
  if (!extractedAds || (!isLeadgen && !clientSelect.value)) return;
  hideMessage(statusMessage);

  // Get the FB Ads Library tab ID so service worker can route video downloads
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  // Send to service worker for background processing
  const response = await chrome.runtime.sendMessage({
    action: "startImport",
    ads: extractedAds,
    sourceUrl: extractedUrl || "",
    clientId: isLeadgen ? null : clientSelect.value,
    tabId: tab?.id || null,
    leadgen: isLeadgen,
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

// =========================================================================
// ANALYSIS FLOW
// =========================================================================

// ---- Tab switching ----
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    const panelId = tab.dataset.tab + "Panel";
    document.getElementById(panelId)?.classList.add("active");
  });
});

// ---- Back button ----
analysisBackBtn.addEventListener("click", () => {
  hideAllSections();
  mainSection.style.display = "block";
});

// ---- Analyze button ----
analyzeBtn.addEventListener("click", async () => {
  if (!extractedAds || extractedAds.length === 0) return;

  hideAllSections();
  analysisSection.style.display = "block";

  // Reset panels
  $("#adAnalysisLoading").style.display = "block";
  $("#adAnalysisResults").innerHTML = "";
  $("#reviewEngineLoading").style.display = "block";
  $("#reviewEngineResults").innerHTML = "";
  $("#reviewSignalLoading").style.display = "block";
  $("#reviewSignalResults").innerHTML = "";

  // Find a destination URL for review detection
  let destinationUrl = null;
  for (const ad of extractedAds) {
    if (ad.destination_url && !ad.destination_url.includes("facebook.com")) {
      destinationUrl = ad.destination_url;
      break;
    }
  }

  // Fire all 3 API calls in parallel
  runAdAnalysis();
  if (destinationUrl) {
    runReviewDetection(destinationUrl);
    runReviewSignal(destinationUrl);
  } else {
    $("#reviewEngineLoading").style.display = "none";
    $("#reviewEngineResults").innerHTML =
      '<div class="panel-empty">No destination URL found in ads — cannot detect review platforms.</div>';
    $("#reviewSignalLoading").style.display = "none";
    $("#reviewSignalResults").innerHTML =
      '<div class="panel-empty">No destination URL found in ads — cannot analyze reviews.</div>';
  }
});

// ---- Ad Analysis ----
async function runAdAnalysis() {
  try {
    const res = await apiFetch("/api/extension/analyze-ads", {
      method: "POST",
      body: JSON.stringify({
        ads: extractedAds.map((ad) => ({
          library_id: ad.library_id || null,
          primary_text: ad.primary_text || "",
          headline: ad.headline || null,
          description: ad.description || null,
          cta: ad.cta || null,
          ad_format: ad.ad_format || null,
          started_running_on: ad.started_running_on || null,
          ad_delivery_end_time: ad.ad_delivery_end_time || null,
          status: ad.status || null,
          destination_url: ad.destination_url || null,
        })),
      }),
    });

    $("#adAnalysisLoading").style.display = "none";

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      $("#adAnalysisResults").innerHTML =
        `<div class="panel-error">Analysis failed: ${err.detail || res.status}</div>`;
      return;
    }

    const data = await res.json();
    renderAdAnalysis(data.results);
  } catch (err) {
    $("#adAnalysisLoading").style.display = "none";
    $("#adAnalysisResults").innerHTML =
      `<div class="panel-error">Network error: ${err.message}</div>`;
  }
}

function scoreClass(n) {
  if (n >= 7) return "score-high";
  if (n >= 4) return "score-mid";
  return "score-low";
}

function renderAdAnalysis(results) {
  const container = $("#adAnalysisResults");
  if (!results || results.length === 0 || results[0]?.error) {
    container.innerHTML = `<div class="panel-error">${results?.[0]?.error || "No results returned."}</div>`;
    return;
  }

  container.innerHTML = results
    .map((r, i) => {
      const grade = r.overall_grade || "?";
      const gradeClass = `grade-${grade}`;
      const latencyClass = `latency-${(r.latency_rating || "medium").toLowerCase()}`;
      const funnelClass = `funnel-${r.funnel_stage || "TOF"}`;

      return `
        <div class="ad-card" id="adCard${i}">
          <div class="ad-card-header">
            <span class="ad-card-id">${r.library_id ? "ID: " + r.library_id : "Ad " + (i + 1)}</span>
            <span class="grade-badge ${gradeClass}">${grade}</span>
          </div>
          <div class="verdict-line">${escHtml(r.one_line_verdict || "")}</div>
          ${r.biggest_weakness ? `<div class="weakness-line">Weakness: ${escHtml(r.biggest_weakness)}</div>` : ""}
          <div class="score-grid">
            <div class="score-row">
              <span class="score-label">Hook</span>
              <span class="score-value ${scoreClass(r.hook_score)}">${r.hook_score ?? "-"}/10</span>
            </div>
            <div class="score-row">
              <span class="score-label">Mind Movie</span>
              <span class="score-value ${scoreClass(r.mind_movie_score)}">${r.mind_movie_score ?? "-"}/10</span>
            </div>
            <div class="score-row">
              <span class="score-label">Specificity</span>
              <span class="score-value ${scoreClass(r.specificity_score)}">${r.specificity_score ?? "-"}/10</span>
            </div>
            <div class="score-row">
              <span class="score-label">Emotion</span>
              <span class="score-value ${scoreClass(r.emotional_charge)}">${r.emotional_charge ?? "-"}/10</span>
            </div>
            <div class="score-row">
              <span class="score-label">VoC Density</span>
              <span class="score-value ${scoreClass(r.voc_density)}">${r.voc_density ?? "-"}/10</span>
            </div>
            <div class="score-row">
              <span class="score-label">Latency</span>
              <span class="latency-badge ${latencyClass}">${r.latency_rating || "?"}</span>
            </div>
            <div class="score-row">
              <span class="score-label">Funnel</span>
              <span class="funnel-badge ${funnelClass}">${r.funnel_stage || "?"}</span>
            </div>
            ${r.ad_age_days != null ? `
            <div class="score-row">
              <span class="score-label">Age</span>
              <span class="score-value">${r.ad_age_days}d</span>
            </div>` : ""}
          </div>
          <button class="expand-btn" onclick="toggleAdDetail(${i})">Show detail</button>
          <div class="score-detail">
            ${r.hook_analysis ? `<p><strong>Hook:</strong> ${escHtml(r.hook_analysis)}</p>` : ""}
            ${r.mind_movie_analysis ? `<p><strong>Mind Movie:</strong> ${escHtml(r.mind_movie_analysis)}</p>` : ""}
            ${r.specificity_analysis ? `<p><strong>Specificity:</strong> ${escHtml(r.specificity_analysis)}</p>` : ""}
            ${r.emotional_analysis ? `<p><strong>Emotion:</strong> ${escHtml(r.emotional_analysis)}</p>` : ""}
            ${r.voc_analysis ? `<p><strong>VoC:</strong> ${escHtml(r.voc_analysis)}</p>` : ""}
            ${r.latency_analysis ? `<p><strong>Latency:</strong> ${escHtml(r.latency_analysis)}</p>` : ""}
            ${r.funnel_reasoning ? `<p><strong>Funnel:</strong> ${escHtml(r.funnel_reasoning)}</p>` : ""}
            ${r.longevity_signal ? `<p><strong>Longevity:</strong> ${escHtml(r.longevity_signal)}</p>` : ""}
          </div>
        </div>
      `;
    })
    .join("");
}

// Toggle expand/collapse for ad detail
window.toggleAdDetail = function (i) {
  const card = document.getElementById(`adCard${i}`);
  if (!card) return;
  card.classList.toggle("expanded");
  const btn = card.querySelector(".expand-btn");
  if (btn) btn.textContent = card.classList.contains("expanded") ? "Hide detail" : "Show detail";
};

// ---- Review Engine Detection ----
async function runReviewDetection(destinationUrl) {
  try {
    const res = await apiFetch("/api/extension/detect-reviews", {
      method: "POST",
      body: JSON.stringify({ destination_url: destinationUrl }),
    });

    $("#reviewEngineLoading").style.display = "none";

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      $("#reviewEngineResults").innerHTML =
        `<div class="panel-error">Detection failed: ${err.detail || res.status}</div>`;
      return;
    }

    const data = await res.json();
    renderReviewEngine(data);
  } catch (err) {
    $("#reviewEngineLoading").style.display = "none";
    $("#reviewEngineResults").innerHTML =
      `<div class="panel-error">Network error: ${err.message}</div>`;
  }
}

function renderReviewEngine(data) {
  const container = $("#reviewEngineResults");

  if (!data.platforms || data.platforms.length === 0) {
    container.innerHTML = '<div class="panel-empty">No review platforms detected.</div>';
    return;
  }

  let html = `<div class="platform-domain">Domain: ${escHtml(data.company_domain)}</div>`;

  html += data.platforms
    .map(
      (p) => `
    <div class="platform-card">
      <div class="platform-row">
        <span class="platform-name">${escHtml(p.platform_display)}</span>
        <span class="confidence-badge confidence-${p.confidence}">${p.confidence}</span>
      </div>
      <div class="platform-row">
        <span class="scrapable-badge scrapable-${p.scrapable ? "yes" : "no"}">${p.scrapable ? "Scrapable" : "Not scrapable"}</span>
      </div>
      <div class="platform-notes">${escHtml(p.scraper_notes)}</div>
    </div>
  `
    )
    .join("");

  container.innerHTML = html;
}

// ---- Review Signal Analysis ----
async function runReviewSignal(destinationUrl) {
  try {
    const res = await apiFetch("/api/extension/analyze-review-signal", {
      method: "POST",
      body: JSON.stringify({ destination_url: destinationUrl, max_reviews: 20 }),
    });

    $("#reviewSignalLoading").style.display = "none";

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      $("#reviewSignalResults").innerHTML =
        `<div class="panel-error">Signal analysis failed: ${err.detail || res.status}</div>`;
      return;
    }

    const data = await res.json();
    renderReviewSignal(data);
  } catch (err) {
    $("#reviewSignalLoading").style.display = "none";
    $("#reviewSignalResults").innerHTML =
      `<div class="panel-error">Network error: ${err.message}</div>`;
  }
}

function renderReviewSignal(data) {
  const container = $("#reviewSignalResults");

  if (data.review_count === 0) {
    container.innerHTML = `<div class="panel-empty">No reviews found on ${escHtml(data.platform_display || "any platform")}.</div>`;
    return;
  }

  const summary = data.signal_results?.find((r) => r.summary);
  const reviews = data.signal_results?.filter((r) => !r.summary) || [];

  let html = "";

  // Summary card
  if (summary) {
    html += `
      <div class="signal-summary">
        <div class="signal-summary-header">
          <span class="signal-summary-title">Signal Report — ${escHtml(data.platform_display)}</span>
          <span class="grade-badge grade-${summary.overall_signal_grade || "C"}">${summary.overall_signal_grade || "?"}</span>
        </div>
        <div class="signal-counts">
          <span class="signal-count signal-count-high">High: ${summary.high_signal_count ?? 0}</span>
          <span class="signal-count signal-count-medium">Med: ${summary.medium_signal_count ?? 0}</span>
          <span class="signal-count signal-count-low">Low: ${summary.low_signal_count ?? 0}</span>
        </div>
        <div class="signal-verdict">${escHtml(summary.verdict || "")}</div>
        ${
          summary.top_themes?.length
            ? `<div class="signal-themes">${summary.top_themes.map((t) => `<span class="theme-tag">${escHtml(t)}</span>`).join("")}</div>`
            : ""
        }
      </div>
    `;
  }

  // Per-review cards (show high/medium first)
  const sorted = [...reviews].sort((a, b) => {
    const order = { high: 0, medium: 1, low: 2 };
    return (order[a.signal_level] ?? 1) - (order[b.signal_level] ?? 1);
  });

  html += sorted
    .map(
      (r) => `
    <div class="review-signal-card">
      <div class="review-signal-row">
        <span class="review-signal-label">Review ${(r.review_index ?? 0) + 1}</span>
        <span class="signal-badge signal-${r.signal_level || "low"}">${r.signal_level || "?"} (${r.signal_score ?? "?"})</span>
      </div>
      <div class="review-reason">${escHtml(r.reason || "")}</div>
      ${r.usable_quote ? `<div class="usable-quote">"${escHtml(r.usable_quote)}"</div>` : ""}
    </div>
  `
    )
    .join("");

  container.innerHTML = html;
}

// ---- Util ----
function escHtml(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}

// ---- Init ----
checkAuth();
