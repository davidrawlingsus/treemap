/**
 * MapTheGap Ad Library Importer — Service Worker
 * Handles background media upload so the user can close the popup
 * and navigate freely while media is being processed.
 */

const API_BASE = "https://api.mapthegap.ai";
// const API_BASE = "http://localhost:8000";

// ---- Open side panel on icon click ----
chrome.action.onClicked.addListener(async (tab) => {
  await chrome.sidePanel.open({ tabId: tab.id });
});

// ---- State ----
let importState = {
  status: "idle", // idle | uploading | importing | done | error
  totalMedia: 0,
  uploadedMedia: 0,
  adCount: 0,
  skippedCount: 0,
  mediaCount: 0,
  error: null,
  importId: null,
  leadgen: false,
  leadgenStarted: false,
  companyName: null,
};

function resetState() {
  importState = {
    status: "idle",
    totalMedia: 0,
    uploadedMedia: 0,
    adCount: 0,
    skippedCount: 0,
    mediaCount: 0,
    error: null,
    importId: null,
    leadgen: false,
    leadgenStarted: false,
    companyName: null,
  };
}

function broadcastState() {
  chrome.runtime.sendMessage({ action: "importProgress", state: importState }).catch(() => {});
}

// ---- Media upload ----
// Tab ID of the Facebook Ads Library page (for content script communication)
let sourceTabId = null;

async function uploadMediaFile(url, clientId, token, mediaType) {
  if (mediaType === "video" && sourceTabId) {
    // Videos: route through content script (has FB page context/cookies)
    return uploadViaContentScript(url, clientId, token, mediaType);
  }
  // Images: direct fetch works from service worker
  return uploadDirect(url, clientId, token, mediaType);
}

async function uploadViaContentScript(url, clientId, token, mediaType) {
  // Step 1: Content script downloads from FB CDN (has page context)
  const dlResponse = await chrome.tabs.sendMessage(sourceTabId, {
    action: "downloadMedia",
    url,
  });
  if (!dlResponse?.success) {
    throw new Error(dlResponse?.error || "Content script download failed");
  }

  // Step 2: Convert data URL back to blob in service worker
  const fetchResponse = await fetch(dlResponse.dataUrl);
  const blob = await fetchResponse.blob();

  // Step 3: Upload from service worker (has CORS bypass via host_permissions)
  const isVideo = mediaType === "video" || (dlResponse.type || "").includes("video");
  const ext = isVideo ? "mp4" : "jpg";
  const uploadType = isVideo ? "video/mp4" : (dlResponse.type || "image/jpeg");
  const filename = `ext-import-${Date.now()}-${Math.random().toString(36).slice(2, 9)}.${ext}`;

  const uploadBlob = new Blob([blob], { type: uploadType });
  const formData = new FormData();
  formData.append("file", uploadBlob, filename);

  const uploadUrl = clientId
    ? `${API_BASE}/api/upload-ad-image?client_id=${clientId}`
    : `${API_BASE}/api/upload-ad-image`;
  const uploadRes = await fetch(uploadUrl, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });

  if (!uploadRes.ok) {
    const err = await uploadRes.json().catch(() => ({}));
    throw new Error(err.error || `Upload failed: ${uploadRes.status}`);
  }

  const data = await uploadRes.json();
  return data.url;
}

async function uploadDirect(url, clientId, token, mediaType) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Fetch failed: ${response.status}`);
  const blob = await response.blob();

  const contentType = blob.type || "image/jpeg";
  let ext = "jpg";
  if (mediaType === "video" || contentType.includes("video")) ext = "mp4";
  else if (contentType.includes("png")) ext = "png";
  else if (contentType.includes("webp")) ext = "webp";
  else if (contentType.includes("gif")) ext = "gif";

  const uploadType = mediaType === "video" ? "video/mp4" : contentType;
  const filename = `ext-import-${Date.now()}-${Math.random().toString(36).slice(2, 9)}.${ext}`;

  const uploadBlob = new Blob([blob], { type: uploadType });
  const formData = new FormData();
  formData.append("file", uploadBlob, filename);

  const uploadUrl = clientId
    ? `${API_BASE}/api/upload-ad-image?client_id=${clientId}`
    : `${API_BASE}/api/upload-ad-image`;
  const uploadRes = await fetch(uploadUrl, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });

  if (!uploadRes.ok) {
    const err = await uploadRes.json().catch(() => ({}));
    throw new Error(err.error || `Upload failed: ${uploadRes.status}`);
  }

  const data = await uploadRes.json();
  return data.url;
}

// ---- Main import flow ----
async function runImport(ads, sourceUrl, clientId, leadgen = false, analysisData = {}) {
  const { vzd_token: token } = await chrome.storage.local.get("vzd_token");
  if (!token) {
    importState.status = "error";
    importState.error = "Not authenticated";
    broadcastState();
    return;
  }

  // Count total media items to upload
  let totalMedia = 0;
  for (const ad of ads) {
    totalMedia += (ad.media_items || []).length;
    if (ad.media_thumbnail_url) totalMedia++;
    if (ad.page_profile_image_url) totalMedia++;
  }

  importState.status = "uploading";
  importState.totalMedia = totalMedia;
  importState.uploadedMedia = 0;
  broadcastState();

  // Upload all media, replacing FB CDN URLs with permanent Blob URLs
  for (const ad of ads) {
    // Upload media items
    for (const media of ad.media_items || []) {
      if (media.url) {
        try {
          media.url = await uploadMediaFile(media.url, clientId, token, media.media_type);
        } catch (e) {
          console.warn("Failed to upload media:", media.media_type, media.url?.substring(0, 60), e.message);
          // Keep original URL as fallback
        }
        importState.uploadedMedia++;
        broadcastState();
      }
      // Upload poster_url for videos
      if (media.poster_url) {
        try {
          media.poster_url = await uploadMediaFile(media.poster_url, clientId, token, "image");
        } catch (e) {
          // Non-critical, keep original
        }
      }
    }

    // Upload thumbnail
    if (ad.media_thumbnail_url) {
      try {
        ad.media_thumbnail_url = await uploadMediaFile(ad.media_thumbnail_url, clientId, token, "image");
      } catch (e) {
        // Non-critical
      }
      importState.uploadedMedia++;
      broadcastState();
    }

    // Upload profile image
    if (ad.page_profile_image_url) {
      try {
        ad.page_profile_image_url = await uploadMediaFile(ad.page_profile_image_url, clientId, token, "image");
      } catch (e) {
        // Non-critical
      }
      importState.uploadedMedia++;
      broadcastState();
    }
  }

  // Now POST the ad data with permanent URLs
  importState.status = "importing";
  broadcastState();

  try {
    let postUrl, postBody;
    const payload = {
      source_url: sourceUrl,
      ads,
      synthesis_text: analysisData.synthesisText || null,
      signal_text: analysisData.signalText || null,
      ad_copy_score: analysisData.adCopyScore || null,
      signal_score: analysisData.signalScore || null,
      opportunity_score: analysisData.opportunityScore || null,
    };
    if (leadgen) {
      postUrl = `${API_BASE}/api/ad-library-imports/from-extension-leadgen`;
    } else {
      postUrl = `${API_BASE}/api/clients/${clientId}/ad-library-imports/from-extension`;
    }
    postBody = JSON.stringify(payload);

    const res = await fetch(postUrl, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: postBody,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Import failed: ${res.status}`);
    }

    const data = await res.json();
    importState.status = "done";
    importState.adCount = data.ad_count;
    importState.skippedCount = data.skipped_count;
    importState.mediaCount = data.media_count;
    importState.importId = data.import_id;

    if (leadgen) {
      importState.leadgenStarted = true;
      importState.companyName = data.company_name || null;
    }

    broadcastState();
  } catch (e) {
    importState.status = "error";
    importState.error = e.message;
    broadcastState();
  }
}

// ---- Message handling ----
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "startImport") {
    if (importState.status === "uploading" || importState.status === "importing") {
      sendResponse({ started: false, error: "An import is already in progress" });
      return true;
    }
    const { ads, sourceUrl, clientId, tabId, leadgen, synthesisText, signalText, adCopyScore, signalScore, opportunityScore } = message;
    sourceTabId = tabId || null;
    resetState();
    importState.leadgen = !!leadgen;
    runImport(ads, sourceUrl, clientId, !!leadgen, { synthesisText, signalText, adCopyScore, signalScore, opportunityScore });
    sendResponse({ started: true });
    return true;
  }

  if (message.action === "getImportState") {
    sendResponse({ state: importState });
    return true;
  }

  if (message.action === "resetImportState") {
    resetState();
    sendResponse({ ok: true });
    return true;
  }

  if (message.action === "fetchPageHtml") {
    // Fetch destination URL to extract review platform signatures.
    // No custom headers — avoids CORS preflight issues.
    // Normalise http → https to avoid mixed-content blocks.
    const url = (message.url || "").replace(/^http:\/\//i, "https://");
    fetch(url, { redirect: "follow" })
      .then((resp) => resp.ok ? resp.text() : null)
      .then((html) => sendResponse({ success: true, html }))
      .catch(() => sendResponse({ success: false }));
    return true; // async
  }

  if (message.action === "switchToAdsLibraryTab") {
    // Find and activate the FB Ads Library tab after magic link auth
    chrome.tabs.query({ url: "*://www.facebook.com/ads/library/*" }, (tabs) => {
      if (tabs.length > 0) {
        const tab = tabs[0];
        chrome.tabs.update(tab.id, { active: true });
        chrome.windows.update(tab.windowId, { focused: true });
      }
    });
    sendResponse({ ok: true });
    return true;
  }
});
