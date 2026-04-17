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
let signalGrade = null; // numeric 1-10 score, set when signal analysis completes
let adSynthesisText = null; // raw synthesis stream text, set when ad analysis completes
let signalStreamText = null; // raw signal stream text, set when signal completes
let adCopyScore = 0; // extracted from synthesis
let opportunityFired = false; // prevent double-firing
let adAnalysisBlocks = new Map(); // library_id → { json, text } for import

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

  // Enrich ads with analysis data (if analysis has run)
  // Build index-based fallback: adAnalysisBlocks may be keyed by LLM ID field
  // which doesn't always match library_id exactly
  const blocksByIndex = [...adAnalysisBlocks.values()];

  const enrichedAds = extractedAds.map((ad, idx) => {
    const key = ad.library_id || `Ad ${idx + 1}`;
    const analysis = adAnalysisBlocks.get(key) || blocksByIndex[idx] || null;
    return {
      ...ad,
      analysis_json: analysis?.json || null,
      analysis_text: analysis?.text || null,
    };
  });

  // Compute opportunity score for import-level data
  const oppResult = computeOpportunity(adCopyScore, signalGrade);

  // Send to service worker for background processing
  const response = await chrome.runtime.sendMessage({
    action: "startImport",
    ads: enrichedAds,
    sourceUrl: extractedUrl || "",
    clientId: isLeadgen ? null : clientSelect.value,
    tabId: tab?.id || null,
    leadgen: isLeadgen,
    synthesisText: adSynthesisText || null,
    signalText: signalStreamText || null,
    adCopyScore: adCopyScore || null,
    signalScore: signalGrade || null,
    opportunityScore: oppResult?.score || null,
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
async function startAnalysis() {
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

  // Fire ad analysis immediately
  streamAdAnalysis();
  if (destinationUrl) {
    // Pre-fetch destination page HTML once, share with both review endpoints
    let pageHtml = null;
    try {
      const fetchResp = await chrome.runtime.sendMessage({ action: "fetchPageHtml", url: destinationUrl });
      if (fetchResp?.success && fetchResp.html) pageHtml = fetchResp.html;
    } catch (e) { /* backend will use its own fetch */ }

    runReviewDetection(destinationUrl, pageHtml);
    streamReviewSignal(destinationUrl, pageHtml);
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

  // Analyze up to 50 ads (show loading on those)
  const adsToAnalyze = Math.min(extractedAds.length, 50);

  if (tabId) {
    for (let i = 0; i < adsToAnalyze; i++) {
      chrome.tabs.sendMessage(tabId, { action: "injectLoading", adIndex: i }).catch(() => {});
    }
  } else {
    console.warn("[VZD] No active tab found for injection");
  }

  let injectedCount = 0;
  let lastInjectedCount = 0;

  function injectCompletedBlocks(text) {
    const completedBlocks = parseCompletedAdBlocks(text);
    for (let i = lastInjectedCount; i < completedBlocks.length; i++) {
      const block = completedBlocks[i];
      const html = buildAdCardHtml(block);
      const grade = getField(block, "GRADE");
      if (tabId) {
        chrome.tabs.sendMessage(tabId, { action: "injectAnalysis", adIndex: i, html, grade }).catch(() => {});
      }
      // Store parsed analysis for import
      const blockId = getField(block, "ID") || (extractedAds?.[i]?.library_id) || `Ad ${i + 1}`;
      adAnalysisBlocks.set(blockId, { json: parseAnalysisToJson(block), text: block });
      injectedCount++;
    }
    lastInjectedCount = completedBlocks.length;
  }

  streamSSE(
    "/api/extension/analyze-ads",
    {
      ads: extractedAds.slice(0, 50).map((ad) => ({
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
      extractCount.style.display = "none"; // hide "Found X ads" once progress starts
      injectCompletedBlocks(text);
      container.innerHTML = `<div class="panel-status">Analyzing ${injectedCount} of ${adsToAnalyze} ads...</div>`;
    },
    // onDone
    (text) => {
      $("#adAnalysisLoading").style.display = "none";
      injectCompletedBlocks(text);
      // Remove orphaned loading indicators from ads that didn't get analyzed
      if (tabId) {
        for (let i = injectedCount; i < adsToAnalyze; i++) {
          chrome.tabs.sendMessage(tabId, { action: "removeLoading", adIndex: i }).catch(() => {});
        }
      }
      container.innerHTML = `<div class="panel-status">${injectedCount} of ${adsToAnalyze} ads analyzed — generating synthesis...</div>`;
      // Set up grade filters on the FB page
      if (tabId) {
        chrome.tabs.sendMessage(tabId, { action: "setupGradeFilters" }).catch(() => {});
      }
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

// ---- Opportunity score: composite of headroom + signal leverage, normalized 1-10 ----
function computeOpportunity(adCopy, signal) {
  if (!adCopy || !signal) return null;
  const headroom = 10 - adCopy;
  const raw = headroom * (1 + signal / 10);
  const score = Math.round((1 + (raw / 18) * 9) * 10) / 10;
  return { score, headroom, raw };
}

function parseAnalysisToJson(block) {
  return {
    grade: getField(block, "GRADE"),
    verdict: getField(block, "VERDICT"),
    weakness: getField(block, "WEAKNESS"),
    hook: getField(block, "HOOK"),
    mind_movie: getField(block, "MIND MOVIE"),
    specificity: getField(block, "SPECIFICITY"),
    emotion: getField(block, "EMOTION"),
    voc_density: getField(block, "VOC DENSITY"),
    latency: getField(block, "LATENCY"),
    funnel: getField(block, "FUNNEL"),
    longevity: getField(block, "LONGEVITY"),
  };
}

function buildOpportunityExplanation(adCopy, signal) {
  let copyPart;
  if (adCopy <= 3) copyPart = "Your ad copy has significant room to improve";
  else if (adCopy <= 5) copyPart = "Your ad copy has clear room to improve";
  else if (adCopy <= 7) copyPart = "Your ads are decent but not fully optimized";
  else copyPart = "Your ads are already strong";

  let sigPart;
  if (signal <= 3) sigPart = "limited review signal to draw from.";
  else if (signal <= 5) sigPart = "moderate review signal to work with.";
  else if (signal <= 7) sigPart = "solid customer voice data available.";
  else sigPart = "rich customer voice data to fuel improvement.";

  return copyPart + ", with " + sigPart;
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
  const adSkeleton = $("#adAnalysisSkeleton");
  if (adSkeleton) adSkeleton.style.display = "none";

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
      adSynthesisText = text;
      // Extract ad copy score for opportunity check
      const block = text.replace(/===SYNTHESIS===/g, "").replace(/===END===/g, "");
      const scoreMatch = (getField(block, "AD_COPY_SCORE") || "").match(/^(\d+)/);
      adCopyScore = scoreMatch ? parseInt(scoreMatch[1], 10) : 0;
      checkAndFireOpportunity();
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

  const adCopyRaw = getField(block, "AD_COPY_SCORE");
  const copyMatch = adCopyRaw.match(/^(\d+)/);
  const copyScore = copyMatch ? parseInt(copyMatch[1], 10) : 0;
  const copyExplanation = adCopyRaw.replace(/^\d+\s*(?:\/10)?\s*[—–-]?\s*/, "").trim();
  const isJustNumber = /^\d+$/.test(copyExplanation);

  const summary = getField(block, "SUMMARY");

  const getMultiline = (label) => {
    const re = new RegExp(`^${label}:\\s*(.+(?:\\n(?![A-Z_]+:).+)*)`, "m");
    const m = block.match(re);
    return m ? m[1].trim() : "";
  };

  const patterns = getMultiline("PATTERNS");
  const playbook = getMultiline("PLAYBOOK");

  const copyClass = copyScore >= 7 ? "score-high" : copyScore >= 4 ? "score-mid" : "score-low";
  const sigScore = typeof signalGrade === "number" ? signalGrade : 0;
  const sigDisplay = sigScore ? sigScore + "/10" : "—";
  const sigClass = sigScore >= 7 ? "score-high" : sigScore >= 4 ? "score-mid" : "score-low";

  const opp = computeOpportunity(copyScore, sigScore);
  const oppDisplay = opp !== null ? "+" + Math.round(opp.score * 10) + "%" : "—";
  const oppClass = opp !== null ? (opp.score >= 7 ? "gap-high" : opp.score >= 4 ? "gap-mid" : "gap-low") : "";
  const oppExplanation = opp ? buildOpportunityExplanation(copyScore, sigScore) : "";

  // Render the three scores into the top-level Scores section
  const scoresSection = $("#scoresSection");
  const scoresResults = $("#scoresResults");
  if (scoresSection && scoresResults) {
    scoresSection.style.display = "block";
    scoresResults.innerHTML = `
      <div class="synthesis-scores-row">
        <div class="synthesis-score-box">
          <span class="synthesis-score-label">Ad Copy Score</span>
          <span class="synthesis-score-value ${copyClass}">${copyScore ? copyScore + "/10" : "—"}</span>
        </div>
        <div class="synthesis-score-box">
          <span class="synthesis-score-label">Review Signal</span>
          <span class="synthesis-score-value synthesis-signal-value ${sigClass}">${sigDisplay}</span>
        </div>
        <div class="synthesis-score-box synthesis-gap-box">
          <span class="synthesis-score-label">Opportunity</span>
          <span class="synthesis-score-value synthesis-gap-value ${oppClass}">${oppDisplay}</span>
        </div>
      </div>
      ${oppExplanation ? `<p class="synthesis-explanation">${oppExplanation}</p>` : ""}
    `;
  }

  // Render the rest into the Ad Analysis section
  let html = `<div class="synthesis-card">`;
  if (copyExplanation && !isJustNumber) {
    html += `<div class="synthesis-summary">${mdToHtml(copyExplanation)}</div>`;
  }
  if (summary) {
    html += `<div class="synthesis-summary">${mdToHtml(summary)}</div>`;
  }
  if (patterns) {
    html += `<div class="synthesis-section-label">Patterns</div><div class="synthesis-bullets">${mdToHtml(patterns)}</div>`;
  }
  if (playbook) {
    html += `<div class="synthesis-section-label">Playbook</div><div class="synthesis-bullets">${mdToHtml(playbook)}</div>`;
  }
  if (streaming) {
    html += `<div class="synthesis-streaming">...</div>`;
  }
  html += `</div>`;
  return html;
}

// Update gap score when signal arrives after synthesis already rendered
function updateGapScore() {
  const gapEl = document.querySelector(".synthesis-gap-value");
  const copyEl = document.querySelector(".synthesis-score-value:not(.synthesis-signal-value):not(.synthesis-gap-value)");
  if (!gapEl || !copyEl) return;

  const copyMatch = (copyEl.textContent || "").match(/(\d+)/);
  const copyScore = copyMatch ? parseInt(copyMatch[1], 10) : 0;
  const sigScore = typeof signalGrade === "number" ? signalGrade : 0;

  if (copyScore && sigScore) {
    const opp = computeOpportunity(copyScore, sigScore);
    if (opp) {
      gapEl.textContent = "+" + Math.round(opp.score * 10) + "%";
      gapEl.className = `synthesis-score-value synthesis-gap-value ${opp.score >= 7 ? "gap-high" : opp.score >= 4 ? "gap-mid" : "gap-low"}`;
      // Update explanation too
      const explEl = document.querySelector(".synthesis-explanation");
      const explanation = buildOpportunityExplanation(copyScore, sigScore);
      if (explEl) {
        explEl.textContent = explanation;
      } else {
        const row = document.querySelector(".synthesis-scores-row");
        if (row && explanation) {
          row.insertAdjacentHTML("afterend", `<p class="synthesis-explanation">${explanation}</p>`);
        }
      }
    }
  }
}

// ---- Opportunity overlay (fires when both analyses complete and opportunity >= 5) ----
async function checkAndFireOpportunity() {
  if (opportunityFired) return;
  if (!adSynthesisText || !signalStreamText) return;
  if (!adCopyScore || !signalGrade) return;

  const opp = computeOpportunity(adCopyScore, signalGrade);
  if (!opp || opp.score < 5) return;

  opportunityFired = true;

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const tabId = tab?.id;

  streamSSE(
    "/api/extension/opportunity",
    {
      ad_synthesis_text: adSynthesisText,
      signal_text: signalStreamText,
      ad_copy_score: adCopyScore,
      signal_score: signalGrade,
      opportunity_score: opp.score,
    },
    // onChunk — don't render partial
    () => {},
    // onDone — inject overlay on the FB page
    (text) => {
      if (tabId) {
        const html = buildOpportunityOverlayHtml(text, adCopyScore, signalGrade, opp.score);
        chrome.tabs.sendMessage(tabId, { action: "injectOpportunityOverlay", html }).catch(() => {});
      }
    },
    // onError
    () => {}
  );
}

function buildOpportunityOverlayHtml(raw, copyScore, sigScore, oppScore) {
  const block = raw.replace(/===OPPORTUNITY===/g, "").replace(/===END===/g, "").trim();
  const get = (label) => {
    const m = block.match(new RegExp(`^${label}:\\s*(.+)`, "m"));
    return m ? m[1].trim() : "";
  };

  const headline = get("HEADLINE");
  const contrast = get("CONTRAST");
  const unlock = get("UNLOCK");
  const explanation = buildOpportunityExplanation(copyScore, sigScore);

  return `
    <div class="vzd-opp-overlay">
      <div class="vzd-opp-card">
        <div class="vzd-opp-slider">
          <div class="vzd-opp-panels">
            <div class="vzd-opp-panel">
              <div class="vzd-opp-panel-content">
                <button class="vzd-opp-close">&times;</button>
                ${headline ? `<h2 class="vzd-opp-headline">${escHtml(headline)}</h2>` : ""}
                <div class="vzd-opp-scores">
                  <div class="vzd-opp-score-item">
                    <span class="vzd-opp-score-label">Ad Copy</span>
                    <span class="vzd-opp-score-num vzd-opp-low">${copyScore}/10</span>
                  </div>
                  <div class="vzd-opp-score-item">
                    <span class="vzd-opp-score-label">Review Signal</span>
                    <span class="vzd-opp-score-num vzd-opp-high">${sigScore}/10</span>
                  </div>
                  <div class="vzd-opp-score-item">
                    <span class="vzd-opp-score-label">Opportunity</span>
                    <span class="vzd-opp-score-num vzd-opp-gap">+${Math.round(oppScore * 10)}%</span>
                  </div>
                </div>
                ${explanation ? `<p class="vzd-opp-explanation">${escHtml(explanation)}</p>` : ""}
                ${contrast ? `<p class="vzd-opp-contrast">${escHtml(contrast)}</p>` : ""}
                ${unlock ? `<p class="vzd-opp-unlock">${escHtml(unlock)}</p>` : ""}
                <button class="vzd-opp-cta vzd-opp-book-btn">Book a Free Strategy Call</button>
                <p class="vzd-opp-subtext">You'll get a personalized strategy and free ad rewrites that unlock this opportunity.</p>
              </div>
            </div>
            <div class="vzd-opp-panel vzd-opp-calendly-panel">
              <button class="vzd-opp-calendly-back">&#8592; Back</button>
              <button class="vzd-opp-calendly-close">&times;</button>
              <iframe class="vzd-opp-calendly-frame" src="https://calendly.com/david-rawlings-gfm7/mapthegap-strategy-call?embed=true"></iframe>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}

// ---- Review Engine Detection (still JSON, not streamed) ----
async function runReviewDetection(destinationUrl, pageHtml) {
  try {
    const body = { destination_url: destinationUrl };
    if (pageHtml) body.page_html = pageHtml;

    const res = await apiFetch("/api/extension/detect-reviews", {
      method: "POST",
      body: JSON.stringify(body),
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

  const count = data.platforms.length;
  let html = `<p class="extract-count">Found ${count} review platform${count !== 1 ? "s" : ""} on ${escHtml(data.company_domain)}</p>`;

  html += data.platforms
    .map(
      (p) => `
    <div class="platform-card">
      <div class="platform-row">
        <span class="platform-name">${p.review_url ? `<a href="${escHtml(p.review_url)}" target="_blank" class="platform-link">${escHtml(p.platform_display)}</a>` : escHtml(p.platform_display)}</span>
        <span class="confidence-badge confidence-${p.confidence}">Detected</span>
      </div>
    </div>
  `
    )
    .join("");

  container.innerHTML = html;
}

// ---- Review Signal Analysis (streaming) ----
function streamReviewSignal(destinationUrl, pageHtml) {
  const container = $("#reviewSignalResults");
  const section = $("#reviewSignalSection");
  if (section) section.style.display = "block";

  const body = { destination_url: destinationUrl, max_reviews: 50 };
  if (pageHtml) body.page_html = pageHtml;

  streamSSE(
    "/api/extension/analyze-review-signal",
    body,
    // onChunk
    (text) => {
      $("#reviewSignalLoading").style.display = "none";
      const sigSkeleton = $("#reviewSignalSkeleton");
      if (sigSkeleton) sigSkeleton.style.display = "none";
      container.innerHTML = renderSignalText(text);
    },
    // onDone
    (text) => {
      $("#reviewSignalLoading").style.display = "none";
      container.innerHTML = renderSignalText(text);
      signalStreamText = text;
      checkAndFireOpportunity();
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

  // Parse source block (which platform was selected)
  const sourceMatch = raw.match(/===SOURCE===([\s\S]*?)===END===/);
  if (sourceMatch) {
    const srcBlock = sourceMatch[1];
    const getSrc = (label) => {
      const m = srcBlock.match(new RegExp(`^${label}:\\s*(.+)$`, "m"));
      return m ? m[1].trim() : "";
    };
    const platform = getSrc("PLATFORM");
    const reviewCount = getSrc("REVIEWS");
    if (platform && platform !== "None") {
      html += `<div class="signal-source">Analyzing ${reviewCount} reviews from <strong>${escHtml(platform)}</strong></div>`;
      // Update review engine section to show only the chosen platform
      const engineContainer = $("#reviewEngineResults");
      if (engineContainer) {
        engineContainer.innerHTML = `
          <div class="platform-card">
            <div class="platform-row">
              <span class="platform-name">${escHtml(platform)}</span>
              <span class="confidence-badge confidence-high">Extracting</span>
            </div>
          </div>`;
      }
    }
  }

  // Parse summary block
  const summaryMatch = raw.match(/===SUMMARY===([\s\S]*?)===END===/);
  if (summaryMatch) {
    const block = summaryMatch[1];
    const get = (label) => {
      const m = block.match(new RegExp(`^${label}:\\s*(.+)$`, "m"));
      return m ? m[1].trim() : "";
    };
    const signalScoreRaw = get("SIGNAL_SCORE") || get("GRADE");
    // Parse numeric score, or convert letter grade to number
    const sigMatch = signalScoreRaw.match(/^(\d+)/);
    let sigNum = sigMatch ? parseInt(sigMatch[1], 10) : 0;
    if (!sigNum && signalScoreRaw) {
      // Convert letter grade to numeric: A=9, B=7, C=5, D=3, F=1
      const letterMap = { A: 9, B: 7, C: 5, D: 3, F: 1 };
      const letter = signalScoreRaw.charAt(0).toUpperCase();
      sigNum = letterMap[letter] || 0;
    }
    if (sigNum) {
      signalGrade = sigNum;
      // Update the synthesis card if it already rendered before signal finished
      const sigEl = document.querySelector(".synthesis-signal-value");
      if (sigEl) {
        sigEl.textContent = sigNum + "/10";
        const cls = sigNum >= 7 ? "score-high" : sigNum >= 4 ? "score-mid" : "score-low";
        sigEl.className = `synthesis-score-value synthesis-signal-value ${cls}`;
      }
      // Also update the gap
      updateGapScore();
    }
    const high = get("HIGH");
    const medium = get("MEDIUM");
    const low = get("LOW");
    const themes = get("THEMES");
    const verdict = get("VERDICT");

    const sigClass = sigNum >= 7 ? "score-high" : sigNum >= 4 ? "score-mid" : "score-low";

    html += `
      <div class="signal-summary">
        <div class="signal-summary-header">
          <span class="signal-summary-title">Signal Report</span>
          ${sigNum ? `<span class="signal-score-badge ${sigClass}">${sigNum}/10</span>` : ""}
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

// Simple markdown → HTML (bold, bullets, line breaks)
function mdToHtml(str) {
  return escHtml(str || "")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/^[•●]\s*/gm, '<span class="md-bullet">•</span> ')
    .replace(/\n/g, "<br>");
}

// ---- Init ----
checkAuth();
