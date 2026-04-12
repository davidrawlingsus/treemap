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
// analysisSection removed — tabs are inline
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
// analyzeBtn removed — analysis runs automatically after extraction
const statusMessage = $("#statusMessage");
const progressFill = $("#progressFill");
const progressLabel = $("#progressLabel");
const leadgenToggle = $("#leadgenToggle");
const leadgenInfo = $("#leadgenInfo");
const leadgenEmail = $("#leadgenEmail");
const clientGroup = $("#clientGroup");
// analysisSection removed — analysis is now inline in mainSection

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

  // Auto-extract and analyze on open
  autoExtractAndAnalyze(tab);
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
    importBtn.disabled = !leadgenToggle.checked && !clientSelect.value;
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
    importBtn.disabled = false;
  } else {
    importBtn.disabled = !clientSelect.value;
  }
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
logoutBtn?.addEventListener("click", async () => {
  await clearToken();
  extractedAds = null;
  extractResult.style.display = "none";
  hideMessage(statusMessage);
  showLogin();
});

// ---- Auto-extract on popup open ----
async function autoExtractAndAnalyze(tab) {
  extractBtn.disabled = true;
  extractBtn.classList.add("btn-icon-spin");
  hideMessage(statusMessage);
  extractResult.style.display = "none";

  try {
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

    startAnalysis();
  } catch (err) {
    showMessage(
      statusMessage,
      "Could not connect to page. Try refreshing the Meta Ads Library page.",
      "error"
    );
  } finally {
    extractBtn.disabled = false;
    extractBtn.classList.remove("btn-icon-spin");
    extractBtn.style.display = "flex";
  }
}

// ---- Manual re-extract ----
extractBtn.addEventListener("click", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  autoExtractAndAnalyze(tab);
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
// ANALYSIS FLOW — SSE streaming with progressive rendering
// =========================================================================

// ---- Auto-analysis after extraction ----
function startAnalysis() {
  if (!extractedAds || extractedAds.length === 0) return;

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
  streamAdAnalysis();
  if (destinationUrl) {
    runReviewDetection(destinationUrl);
    streamReviewSignal(destinationUrl);
  } else {
    $("#reviewEngineLoading").style.display = "none";
    $("#reviewEngineResults").innerHTML =
      '<div class="panel-empty">No destination URL found in ads — cannot detect review platforms.</div>';
    $("#reviewSignalLoading").style.display = "none";
    $("#reviewSignalResults").innerHTML =
      '<div class="panel-empty">No destination URL found in ads — cannot analyze reviews.</div>';
  }
}

// ---- SSE helper: stream a POST endpoint, accumulate text, call render on each chunk ----
async function streamSSE(path, body, onChunk, onDone, onError) {
  try {
    const token = await getToken();
    const res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const detail = err.detail;
      const msg = typeof detail === "string" ? detail
        : typeof detail === "object" ? JSON.stringify(detail)
        : `HTTP ${res.status}`;
      onError(msg);
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let accumulated = "";
    let lineBuf = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      lineBuf += decoder.decode(value, { stream: true });

      // SSE events are separated by blank lines (\n\n)
      const events = lineBuf.split("\n\n");
      // Last element may be incomplete — keep it in buffer
      lineBuf = events.pop() || "";

      for (const event of events) {
        if (!event.trim()) continue;
        // Each event may have multiple "data: " lines (one per source newline)
        // Reassemble them with newlines to preserve the original text structure
        const dataLines = event.split("\n")
          .filter((l) => l.startsWith("data: "))
          .map((l) => l.slice(6));

        const payload = dataLines.join("\n");
        if (payload === "[DONE]") {
          onDone(accumulated);
          return;
        }
        accumulated += payload;
        onChunk(accumulated);
      }
    }
    onDone(accumulated);
  } catch (err) {
    onError(err.message);
  }
}

// ---- Ad Analysis (streaming → injected onto page) ----
async function streamAdAnalysis() {
  const container = $("#adAnalysisResults");
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const tabId = tab?.id;

  // Show loading indicators on each ad card
  if (tabId) {
    for (let i = 0; i < extractedAds.length; i++) {
      chrome.tabs.sendMessage(tabId, { action: "injectLoading", adIndex: i })
        .catch((e) => console.warn(`[VZD] injectLoading failed for ad ${i}:`, e));
    }
  } else {
    console.warn("[VZD] No active tab found for injection");
  }

  let injectedCount = 0;
  let lastInjectedCount = 0;

  function injectCompletedBlocks(text) {
    const completedBlocks = parseCompletedAdBlocks(text);
    for (let i = lastInjectedCount; i < completedBlocks.length; i++) {
      const html = buildAdCardHtml(completedBlocks[i]);
      if (tabId) {
        chrome.tabs.sendMessage(tabId, { action: "injectAnalysis", adIndex: i, html })
          .then((resp) => console.log(`[VZD] Injected ad ${i}:`, resp))
          .catch((e) => console.warn(`[VZD] injectAnalysis failed for ad ${i}:`, e));
      }
      injectedCount++;
    }
    lastInjectedCount = completedBlocks.length;
  }

  streamSSE(
    "/api/extension/analyze-ads",
    {
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
    },
    // onChunk
    (text) => {
      $("#adAnalysisLoading").style.display = "none";
      injectCompletedBlocks(text);
      container.innerHTML = `<div class="panel-status">Analyzing ${injectedCount} of ${extractedAds.length} ads...</div>`;
    },
    // onDone
    (text) => {
      $("#adAnalysisLoading").style.display = "none";
      injectCompletedBlocks(text);
      container.innerHTML = `<div class="panel-status">All ${injectedCount} ads analyzed — generating synthesis...</div>`;
      // Fire synthesis
      streamSynthesis(text, container);
    },
    // onError
    (msg) => {
      $("#adAnalysisLoading").style.display = "none";
      container.innerHTML = `<div class="panel-error">Analysis failed: ${escHtml(msg)}</div>`;
    }
  );
}

// ---- Parse completed ===AD=== ... ===END=== blocks from streamed text ----
function parseCompletedAdBlocks(raw) {
  const blocks = [];
  const parts = raw.split("===AD===").slice(1); // skip anything before first marker
  for (const part of parts) {
    const endIdx = part.indexOf("===END===");
    if (endIdx === -1) continue; // block not yet complete
    blocks.push(part.substring(0, endIdx).trim());
  }
  return blocks;
}

// ---- Extract a field from a text block ----
function getField(block, label) {
  const re = new RegExp(`^${label}:\\s*(.+)$`, "m");
  const m = block.match(re);
  return m ? m[1].trim() : "";
}

// ---- Build HTML for injection onto the FB page ad card ----
function buildAdCardHtml(block) {
  const grade = getField(block, "GRADE");
  const verdict = getField(block, "VERDICT");
  const weakness = getField(block, "WEAKNESS");
  const longevity = getField(block, "LONGEVITY");

  // Score line: "7 — Analysis text here" → score badge + analysis text
  const scoreHtml = (label, display) => {
    const raw = getField(block, label);
    if (!raw) return "";
    const m = raw.match(/^(\d+)\s*[—–-]\s*(.+)$/);
    if (m) {
      const n = parseInt(m[1], 10);
      const cls = n >= 7 ? "vzd-score-high" : n >= 4 ? "vzd-score-mid" : "vzd-score-low";
      return `
        <div class="vzd-dimension">
          <div class="vzd-score-item">
            <span class="vzd-score-label">${display}</span>
            <span class="vzd-score-val ${cls}">${n}/10</span>
          </div>
          <div class="vzd-score-reason">${escHtml(m[2])}</div>
        </div>`;
    }
    return `<div class="vzd-dimension"><div class="vzd-score-item"><span class="vzd-score-label">${display}</span></div><div class="vzd-score-reason">${escHtml(raw)}</div></div>`;
  };

  // Tag line: "low — Analysis text" → tag badge + analysis text
  const tagHtml = (label, display, prefix) => {
    const raw = getField(block, label);
    if (!raw) return "";
    const m = raw.match(/^(\S+)\s*[—–-]\s*(.+)$/);
    if (m) {
      return `
        <div class="vzd-dimension">
          <div class="vzd-score-item">
            <span class="vzd-score-label">${display}</span>
            <span class="vzd-tag ${prefix}-${m[1].toLowerCase()}">${m[1]}</span>
          </div>
          <div class="vzd-score-reason">${escHtml(m[2])}</div>
        </div>`;
    }
    return `<div class="vzd-dimension"><div class="vzd-score-item"><span class="vzd-score-label">${display}</span></div><div class="vzd-score-reason">${escHtml(raw)}</div></div>`;
  };

  return `
    <div class="vzd-grade-row">
      ${grade ? `<span class="vzd-grade vzd-grade-${grade}">${grade}</span>` : ""}
      ${verdict ? `<span class="vzd-verdict">${escHtml(verdict)}</span>` : ""}
    </div>
    ${weakness ? `<div class="vzd-weakness">Weakness: ${escHtml(weakness)}</div>` : ""}
    ${scoreHtml("HOOK", "Hook")}
    ${scoreHtml("MIND MOVIE", "Mind Movie")}
    ${scoreHtml("SPECIFICITY", "Specificity")}
    ${scoreHtml("EMOTION", "Emotion")}
    ${scoreHtml("VOC DENSITY", "VoC Density")}
    ${tagHtml("LATENCY", "Latency", "vzd-latency")}
    ${tagHtml("FUNNEL", "Funnel", "vzd-funnel")}
    ${longevity ? `<div class="vzd-longevity">${escHtml(longevity)}</div>` : ""}
  `;
}

// ---- Opportunity Synthesis (streams into sidebar after all ads analyzed) ----
function streamSynthesis(analysisText, container) {
  streamSSE(
    "/api/extension/synthesize",
    { analysis_text: analysisText },
    // onChunk
    (text) => {
      container.innerHTML = renderSynthesisText(text, true);
    },
    // onDone
    (text) => {
      container.innerHTML = renderSynthesisText(text, false);
    },
    // onError
    (msg) => {
      container.innerHTML = `<div class="panel-error">Synthesis failed: ${escHtml(msg)}</div>`;
    }
  );
}

function renderSynthesisText(raw, streaming) {
  const block = raw.replace(/===SYNTHESIS===/g, "").replace(/===END===/g, "").trim();
  if (!block) return `<div class="panel-status">Generating synthesis...</div>`;

  const opportunityRaw = getField(block, "OPPORTUNITY");

  // Extract just the number from "7 — long explanation text"
  const oppMatch = opportunityRaw.match(/^(\d+)/);
  const oppNum = oppMatch ? parseInt(oppMatch[1], 10) : 0;
  const oppExplanation = opportunityRaw.replace(/^\d+\s*[—–-]\s*/, "").trim();

  const summary = getField(block, "SUMMARY");

  // Multi-line fields: PATTERNS and PLAYBOOK may have bullet points
  const getMultiline = (label) => {
    const re = new RegExp(`^${label}:\\s*(.+(?:\\n(?![A-Z]+:).+)*)`, "m");
    const m = block.match(re);
    return m ? m[1].trim() : "";
  };

  const patterns = getMultiline("PATTERNS");
  const playbook = getMultiline("PLAYBOOK");

  const oppClass = oppNum >= 7 ? "opp-high" : oppNum >= 4 ? "opp-mid" : "opp-low";

  let html = `<div class="synthesis-card">`;
  if (oppNum) {
    html += `<div class="synthesis-opp-row"><span class="synthesis-label">Opportunity Score</span><span class="synthesis-opp ${oppClass}">${oppNum}/10</span></div>`;
  }
  if (oppExplanation) {
    html += `<div class="synthesis-summary">${escHtml(oppExplanation)}</div>`;
  }
  if (summary) {
    html += `<div class="synthesis-summary">${escHtml(summary)}</div>`;
  }
  if (patterns) {
    html += `<div class="synthesis-section-label">Patterns</div><div class="synthesis-bullets">${escHtml(patterns)}</div>`;
  }
  if (playbook) {
    html += `<div class="synthesis-section-label">Playbook</div><div class="synthesis-bullets">${escHtml(playbook)}</div>`;
  }
  if (streaming) {
    html += `<div class="synthesis-streaming">...</div>`;
  }
  html += `</div>`;
  return html;
}

// ---- Review Engine Detection (still JSON, not streamed) ----
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
        <span class="platform-name">${p.review_url ? `<a href="${escHtml(p.review_url)}" target="_blank" class="platform-link">${escHtml(p.platform_display)}</a>` : escHtml(p.platform_display)}</span>
        <span class="confidence-badge confidence-${p.confidence}">${p.confidence === "high" ? "Embedded" : p.confidence === "medium" ? "Detected" : "Fallback"}</span>
      </div>
      <div class="platform-notes">${escHtml(p.scraper_notes)}</div>
    </div>
  `
    )
    .join("");

  container.innerHTML = html;
}

// ---- Review Signal Analysis (streaming) ----
function streamReviewSignal(destinationUrl) {
  const container = $("#reviewSignalResults");
  const section = $("#reviewSignalSection");
  if (section) section.style.display = "block";

  streamSSE(
    "/api/extension/analyze-review-signal",
    { destination_url: destinationUrl, max_reviews: 20 },
    // onChunk
    (text) => {
      $("#reviewSignalLoading").style.display = "none";
      container.innerHTML = renderSignalText(text);
    },
    // onDone
    (text) => {
      $("#reviewSignalLoading").style.display = "none";
      container.innerHTML = renderSignalText(text);
    },
    // onError
    (msg) => {
      $("#reviewSignalLoading").style.display = "none";
      container.innerHTML = `<div class="panel-error">Signal analysis failed: ${escHtml(msg)}</div>`;
    }
  );
}

// ---- Parse and render review signal text ----
function renderSignalText(raw) {
  let html = "";

  // Parse summary block
  const summaryMatch = raw.match(/===SUMMARY===([\s\S]*?)===END===/);
  if (summaryMatch) {
    const block = summaryMatch[1];
    const get = (label) => {
      const m = block.match(new RegExp(`^${label}:\\s*(.+)$`, "m"));
      return m ? m[1].trim() : "";
    };
    const grade = get("GRADE");
    const high = get("HIGH");
    const medium = get("MEDIUM");
    const low = get("LOW");
    const themes = get("THEMES");
    const verdict = get("VERDICT");

    html += `
      <div class="signal-summary">
        <div class="signal-summary-header">
          <span class="signal-summary-title">Signal Report</span>
          ${grade ? `<span class="grade-badge grade-${grade}">${grade}</span>` : ""}
        </div>
        <div class="signal-counts">
          <span class="signal-count signal-count-high">High: ${high || 0}</span>
          <span class="signal-count signal-count-medium">Med: ${medium || 0}</span>
          <span class="signal-count signal-count-low">Low: ${low || 0}</span>
        </div>
        ${verdict ? `<div class="signal-verdict">${escHtml(verdict)}</div>` : ""}
        ${themes && themes !== "none" ? `<div class="signal-themes">${themes.split(",").map((t) => `<span class="theme-tag">${escHtml(t.trim())}</span>`).join("")}</div>` : ""}
      </div>
    `;
  } else if (raw.includes("===SUMMARY===")) {
    // Summary started but not finished yet — show what we have
    html += '<div class="signal-summary"><div class="stream-text">' + escHtml(raw.replace("===SUMMARY===", "").trim()) + "</div></div>";
    return html;
  }

  // Parse review blocks
  const reviewBlocks = raw.split("===REVIEW===").slice(1);
  for (const block of reviewBlocks) {
    const clean = block.replace(/===END===/g, "").trim();
    if (!clean) continue;
    const get = (label) => {
      const m = clean.match(new RegExp(`^${label}:\\s*(.+)$`, "m"));
      return m ? m[1].trim() : "";
    };

    const index = get("INDEX");
    const signal = get("SIGNAL");
    const score = get("SCORE");
    const reason = get("REASON");
    const quote = get("QUOTE");

    html += `
      <div class="review-signal-card">
        <div class="review-signal-row">
          <span class="review-signal-label">Review ${escHtml(index || "?")}</span>
          ${signal ? `<span class="signal-badge signal-${signal}">${signal}${score ? ` (${score})` : ""}</span>` : ""}
        </div>
        ${reason ? `<div class="review-reason">${escHtml(reason)}</div>` : ""}
        ${quote && quote !== "none" ? `<div class="usable-quote">"${escHtml(quote)}"</div>` : ""}
      </div>
    `;
  }

  return html || '<div class="stream-text">' + escHtml(raw) + "</div>";
}

// ---- Util ----
function escHtml(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}

// ---- Init ----
checkAuth();
