/**
 * Unified Import Media Modal Module
 * Combines file upload and Meta Ads Library import in a tabbed interface.
 * Meta import polling continues in the background even if the dialog is closed.
 */

import { uploadAdImage } from '/js/services/api-ad-images.js';
import {
    startMetaImportJob,
    getImportJobStatus,
    getImportJobImages
} from '/js/services/api-meta-import.js';
import {
    checkMetaTokenStatus,
    fetchMetaAdAccounts,
    fetchMetaMediaLibrary,
    fetchMetaMediaLibraryCounts,
    importMetaMediaStream,
    importAllMetaMediaStream,
    openMetaOAuthPopup,
} from '/js/services/api-meta.js';
import { addImageToCache } from '/js/state/images-state.js';
import { renderFbConnectorPicker } from '/js/renderers/fb-connector-media-picker.js';

// ============ Module-level state for background polling ============

// Track active jobs and their polling intervals
const activeJobs = new Map(); // jobId -> { interval, addedImageIds, onComplete }

// Persistent progress bar for FB Connector import (survives modal close)
let globalImportProgressEl = null;
/** AbortController for the current in-flight import; cleared when import ends or is cancelled. */
let currentImportAbortController = null;

function getOrCreatePersistentImportProgressEl() {
    if (!globalImportProgressEl || !globalImportProgressEl.isConnected) {
        globalImportProgressEl = document.createElement('div');
        globalImportProgressEl.className = 'import-media-global-progress';
        globalImportProgressEl.innerHTML = '<span class="import-media-global-progress__text"></span><div class="import-media-global-progress__bar-wrap"><div class="import-media-global-progress__bar"></div></div><button type="button" class="import-media-global-progress__cancel">Cancel</button>';
        document.body.appendChild(globalImportProgressEl);
        const cancelBtn = globalImportProgressEl.querySelector('.import-media-global-progress__cancel');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => {
                if (currentImportAbortController) {
                    currentImportAbortController.abort();
                }
            });
        }
    }
    return globalImportProgressEl;
}

function updatePersistentImportProgress(opts) {
    if (opts === null) {
        currentImportAbortController = null;
        if (globalImportProgressEl?.isConnected) {
            globalImportProgressEl.remove();
        }
        globalImportProgressEl = null;
        return;
    }
    const el = getOrCreatePersistentImportProgressEl();
    const textEl = el.querySelector('.import-media-global-progress__text');
    const bar = el.querySelector('.import-media-global-progress__bar');
    const cancelBtn = el.querySelector('.import-media-global-progress__cancel');
    if (textEl) textEl.textContent = opts.text || '';
    if (bar) {
        const pct = opts.total != null && opts.total > 0 ? Math.min(100, ((opts.imported ?? 0) / opts.total) * 100) : 0;
        bar.style.width = `${pct}%`;
    }
    if (opts.complete) {
        el.classList.add('import-media-global-progress--complete');
        if (cancelBtn) cancelBtn.style.display = 'none';
    } else if (cancelBtn) {
        cancelBtn.style.display = '';
    }
}

// ============ Utility Functions ============

/**
 * Format file size for display
 * @param {number} bytes - File size in bytes
 * @returns {string} Formatted size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Validate Meta Ads Library URL
 * @param {string} url - URL to validate
 * @returns {boolean} True if valid
 */
function isValidMetaAdsLibraryUrl(url) {
    try {
        const parsed = new URL(url);
        const isMetaDomain = parsed.hostname === 'www.facebook.com' || 
                            parsed.hostname === 'facebook.com';
        const isAdsLibrary = parsed.pathname.includes('/ads/library');
        const hasPageId = parsed.searchParams.has('view_all_page_id');
        return isMetaDomain && isAdsLibrary && hasPageId;
    } catch {
        return false;
    }
}

/**
 * Append a new image to the masonry grid in real-time
 * @param {Object} image - Image data
 */
function appendImageToGridRealtime(image) {
    if (typeof window.appendImageToGrid === 'function') {
        window.appendImageToGrid(image);
    } else if (typeof window.renderImages === 'function') {
        addImageToCache(image);
        window.renderImages();
    } else {
        addImageToCache(image);
    }
}

// ============ Meta Import Background Polling ============

/**
 * Stop polling for a specific job
 * @param {string} jobId - Job ID to stop
 */
function stopJobPolling(jobId) {
    const jobData = activeJobs.get(jobId);
    if (jobData && jobData.interval) {
        clearInterval(jobData.interval);
        activeJobs.delete(jobId);
        console.log('[ImportMediaModal] Stopped polling for job:', jobId);
    }
}

/**
 * Poll for job status and new images (runs in background)
 * @param {string} jobId - Job ID to poll
 * @param {Function|null} updateModalUI - Optional function to update modal UI
 */
async function pollJobStatusBackground(jobId, updateModalUI = null) {
    const jobData = activeJobs.get(jobId);
    if (!jobData) return;
    
    try {
        const statusResponse = await getImportJobStatus(jobId);
        const job = statusResponse.job;
        
        if (updateModalUI) {
            updateModalUI(job);
        }
        
        // Add any new images to the grid in real-time
        if (statusResponse.recent_images && statusResponse.recent_images.length > 0) {
            for (const image of statusResponse.recent_images) {
                if (!jobData.addedImageIds.has(image.id)) {
                    jobData.addedImageIds.add(image.id);
                    appendImageToGridRealtime(image);
                }
            }
        }
        
        // Check if complete
        if (job.status === 'complete' || job.status === 'failed') {
            try {
                const allImages = await getImportJobImages(jobId);
                for (const image of allImages.items || []) {
                    if (!jobData.addedImageIds.has(image.id)) {
                        jobData.addedImageIds.add(image.id);
                        appendImageToGridRealtime(image);
                    }
                }
            } catch (e) {
                console.warn('[ImportMediaModal] Failed to fetch all images:', e);
            }
            
            stopJobPolling(jobId);
            
            if (jobData.onComplete) {
                jobData.onComplete({
                    imported: job.total_imported,
                    total_found: job.total_found,
                    status: job.status,
                    error_message: job.error_message
                });
            }
            
            console.log('[ImportMediaModal] Job complete:', jobId, 'imported:', job.total_imported);
        }
        
    } catch (error) {
        console.error('[ImportMediaModal] Polling error:', error);
    }
}

/**
 * Start background polling for a job
 * @param {string} jobId - Job ID to poll
 * @param {Function|null} onComplete - Callback when job completes
 * @returns {Object} Job tracking data
 */
function startBackgroundPolling(jobId, onComplete = null) {
    const jobData = {
        addedImageIds: new Set(),
        onComplete: onComplete,
        interval: null
    };
    
    activeJobs.set(jobId, jobData);
    jobData.interval = setInterval(() => pollJobStatusBackground(jobId), 2000);
    
    console.log('[ImportMediaModal] Started background polling for job:', jobId);
    
    return jobData;
}

// ============ Main Modal Function ============

/**
 * Show unified import media modal with tabs
 * @param {Function} onImageAdded - Callback when an image is added (upload or import)
 */
export function showImportMediaModal(onImageAdded) {
    const clientId = window.appStateGet?.('currentClientId') || 
                     document.getElementById('clientSelect')?.value;
    
    if (!clientId) {
        alert('Please select a client first');
        return;
    }

    if (typeof onImageAdded !== 'function') {
        onImageAdded = (img) => {
            addImageToCache(img);
            appendImageToGridRealtime(img);
        };
    }
    
    // Create modal overlay
    const overlay = document.createElement('div');
    overlay.className = 'import-media-overlay';
    overlay.innerHTML = `
        <div class="import-media-modal">
            <div class="import-media-modal__header">
                <h2>Import Media</h2>
                <button class="import-media-modal__close">×</button>
            </div>
            
            <div class="import-media-tabs">
                <button class="import-media-tab import-media-tab--active" data-tab="upload">File Upload</button>
                <button class="import-media-tab" data-tab="meta">Meta Ads Library</button>
                <button class="import-media-tab" data-tab="fb-connector">FB Connector</button>
            </div>
            
            <div class="import-media-modal__body">
                <!-- File Upload Tab Content -->
                <div class="import-media-tab-content import-media-tab-content--active" data-tab-content="upload">
                    <input type="file" id="importMediaFileInput" accept="image/*,video/*" multiple style="display: none;">
                    <div class="import-media-dropzone" id="importMediaDropzone">
                        <div class="import-media-dropzone__content">
                            <div class="import-media-dropzone__icon">📤</div>
                            <p>Click to select or drag and drop</p>
                            <p class="import-media-dropzone__hint">Supports images and videos up to 50MB</p>
                        </div>
                    </div>
                    <div class="import-media-upload-progress" id="importMediaUploadProgress" style="display: none;">
                        <div class="import-media-upload-progress__bar" id="importMediaUploadProgressBar"></div>
                        <p class="import-media-upload-progress__text" id="importMediaUploadProgressText">Uploading...</p>
                    </div>
                </div>
                
                <!-- Meta Ads Library Tab Content -->
                <div class="import-media-tab-content" data-tab-content="meta">
                    <div class="import-media-meta-form" id="importMediaMetaForm">
                        <label class="import-media-label" for="importMediaMetaUrl">
                            Meta Ads Library URL
                        </label>
                        <input 
                            type="url" 
                            id="importMediaMetaUrl" 
                            class="import-media-input"
                        >
                        <p class="import-media-hint">
                            Paste a Meta Ads Library URL with a page ID to import all media from that page's ads.
                        </p>
                        <p class="import-media-error" id="importMediaMetaError" style="display: none;"></p>
                    </div>
                    <div class="import-media-meta-progress" id="importMediaMetaProgress" style="display: none;">
                        <div class="import-media-meta-progress__spinner"></div>
                        <p class="import-media-meta-progress__text" id="importMediaMetaProgressText">Starting import...</p>
                        <p class="import-media-meta-progress__detail" id="importMediaMetaProgressDetail"></p>
                        <div class="import-media-meta-progress__bar-container" id="importMediaMetaProgressBarContainer" style="display: none;">
                            <div class="import-media-meta-progress__bar" id="importMediaMetaProgressBar"></div>
                        </div>
                        <div class="import-media-background-notice">
                            <p>You can close this dialog - the import will continue in the background.</p>
                            <p class="import-media-background-notice__hint">Imported media will appear automatically as they're processed.</p>
                        </div>
                    </div>
                    <div class="import-media-meta-results" id="importMediaMetaResults" style="display: none;">
                        <div class="import-media-meta-results__icon">✓</div>
                        <p class="import-media-meta-results__text" id="importMediaMetaResultsText"></p>
                    </div>
                </div>
                <!-- FB Connector Tab Content -->
                <div class="import-media-tab-content" data-tab-content="fb-connector">
                    <div id="importMediaFbConnectorPanel" class="import-media-fb-connector-panel"></div>
                </div>
            </div>
            
            <div class="import-media-modal__footer" id="importMediaFooter">
                <button class="import-media-modal__cancel">Cancel</button>
                <button class="import-media-modal__submit import-media-modal__submit--secondary import-media-fb-import-all" id="importMediaFbConnectorImportAllBtn" style="display: none;">Import all</button>
                <button class="import-media-modal__submit import-media-fb-import-selected" id="importMediaFbConnectorImportBtn" style="display: none;" disabled>Import Selected (0)</button>
                <button class="import-media-modal__submit" id="importMediaMetaSubmit" style="display: none;">Import from Meta</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(overlay);
    
    // Get references to elements
    const closeBtn = overlay.querySelector('.import-media-modal__close');
    const cancelBtn = overlay.querySelector('.import-media-modal__cancel');
    const tabs = overlay.querySelectorAll('.import-media-tab');
    const tabContents = overlay.querySelectorAll('.import-media-tab-content');
    const footerEl = overlay.querySelector('#importMediaFooter');
    
    // Upload tab elements
    const fileInput = overlay.querySelector('#importMediaFileInput');
    const dropzone = overlay.querySelector('#importMediaDropzone');
    const uploadProgress = overlay.querySelector('#importMediaUploadProgress');
    const uploadProgressBar = overlay.querySelector('#importMediaUploadProgressBar');
    const uploadProgressText = overlay.querySelector('#importMediaUploadProgressText');
    
    // Meta tab elements
    const metaUrlInput = overlay.querySelector('#importMediaMetaUrl');
    const metaSubmitBtn = overlay.querySelector('#importMediaMetaSubmit');
    const metaErrorEl = overlay.querySelector('#importMediaMetaError');
    const metaFormEl = overlay.querySelector('#importMediaMetaForm');
    const metaProgressEl = overlay.querySelector('#importMediaMetaProgress');
    const metaProgressText = overlay.querySelector('#importMediaMetaProgressText');
    const metaProgressDetail = overlay.querySelector('#importMediaMetaProgressDetail');
    const metaProgressBarContainer = overlay.querySelector('#importMediaMetaProgressBarContainer');
    const metaProgressBar = overlay.querySelector('#importMediaMetaProgressBar');
    const metaResultsEl = overlay.querySelector('#importMediaMetaResults');
    const metaResultsText = overlay.querySelector('#importMediaMetaResultsText');
    
    let currentJobId = null;
    let currentTab = 'upload';
    
    // Close modal helper
    const closeModal = () => {
        overlay.remove();
        document.removeEventListener('keydown', handleEscape);
    };
    
    // ============ Tab Switching ============
    
    function switchTab(tabName) {
        currentTab = tabName;
        
        // Update tab buttons
        tabs.forEach(tab => {
            if (tab.dataset.tab === tabName) {
                tab.classList.add('import-media-tab--active');
            } else {
                tab.classList.remove('import-media-tab--active');
            }
        });
        
        // Update tab content
        tabContents.forEach(content => {
            if (content.dataset.tabContent === tabName) {
                content.classList.add('import-media-tab-content--active');
            } else {
                content.classList.remove('import-media-tab-content--active');
            }
        });
        
        // Update footer buttons based on tab
        if (tabName === 'upload') {
            metaSubmitBtn.style.display = 'none';
            const fbImportBtn = overlay.querySelector('#importMediaFbConnectorImportBtn');
            const fbImportAllBtn = overlay.querySelector('#importMediaFbConnectorImportAllBtn');
            if (fbImportBtn) fbImportBtn.style.display = 'none';
            if (fbImportAllBtn) fbImportAllBtn.style.display = 'none';
        } else if (tabName === 'fb-connector') {
            metaSubmitBtn.style.display = 'none';
            const fbImportBtn = overlay.querySelector('#importMediaFbConnectorImportBtn');
            const fbImportAllBtn = overlay.querySelector('#importMediaFbConnectorImportAllBtn');
            if (fbImportBtn) {
                fbImportBtn.style.display = '';
                fbImportBtn.disabled = true;
                fbImportBtn.textContent = 'Import Selected (0)';
            }
            if (fbImportAllBtn) {
                fbImportAllBtn.style.display = '';
                fbImportAllBtn.disabled = fbConnectorImporting;
            }
            refreshFbConnectorTab();
        } else {
            const fbImportBtn = overlay.querySelector('#importMediaFbConnectorImportBtn');
            const fbImportAllBtn = overlay.querySelector('#importMediaFbConnectorImportAllBtn');
            if (fbImportBtn) fbImportBtn.style.display = 'none';
            if (fbImportAllBtn) fbImportAllBtn.style.display = 'none';
            metaSubmitBtn.style.display = 'block';
            const url = metaUrlInput.value.trim();
            metaSubmitBtn.disabled = !url || !isValidMetaAdsLibraryUrl(url);
        }
    }

    // ============ FB Connector tab state and refresh ============
    let fbConnectorTokenStatus = null;
    let fbConnectorItems = [];
    let fbConnectorPaging = { after: null, hasMore: false };
    let fbConnectorSelectedIds = new Set();
    let fbConnectorLoading = false;
    let fbConnectorImporting = false;
    /** When Load All is running: { loaded, total } (total may be null if API has no count). */
    let fbConnectorLoadAllProgress = null;
    /** Error message when initial media fetch fails (e.g. rate limit). Cleared on retry or successful load. */
    let fbConnectorLoadError = null;
    /** True when Load All was paused due to rate limit; user can Resume. */
    let fbConnectorLoadAllPaused = false;
    /** When Import all is running: { imported, failed } for progress display. */
    let fbConnectorImportProgress = null;
    /** True when we should show the ad account selector (no default or user clicked Change). */
    let fbConnectorNeedsAdAccount = false;
    /** List of ad accounts from fetchMetaAdAccounts. */
    let fbConnectorAdAccounts = [];
    /** Selected ad account id in the dropdown. */
    let fbConnectorSelectedAdAccountId = null;
    /** Error message when set default ad account fails (shown in selector view). */
    let fbConnectorSetAdAccountError = null;
    /** Ad account used for this modal session only (not persisted). When set, overrides token default for media/import calls. */
    let fbConnectorSessionAdAccountId = null;
    /** Display name for session ad account (for header). */
    let fbConnectorSessionAdAccountName = null;

    function getFbConnectorAdAccountId() {
        return fbConnectorSessionAdAccountId || fbConnectorTokenStatus?.default_ad_account_id || null;
    }

    async function runLoadAllLoop() {
        let iter = 0;
        const maxLoadAllIterations = 250;
        while (fbConnectorPaging.hasMore && iter < maxLoadAllIterations) {
            iter++;
            const opts = { mediaType: 'all', limit: 50 };
            if (fbConnectorPaging.image_after) opts.image_after = fbConnectorPaging.image_after;
            if (fbConnectorPaging.video_after) opts.video_after = fbConnectorPaging.video_after;
            const adId = getFbConnectorAdAccountId();
            if (adId) opts.ad_account_id = adId;
            try {
                const res = await fetchMetaMediaLibrary(clientId, opts);
                const newItems = res.items || [];
                fbConnectorItems = fbConnectorItems.concat(newItems);
                const p = res.paging;
                const hasCursors = p && (p.after || p.image_after || p.video_after);
                const noMoreData = newItems.length === 0;
                fbConnectorPaging = {
                    after: p?.after || null,
                    image_after: p?.image_after || null,
                    video_after: p?.video_after || null,
                    hasMore: hasCursors && !noMoreData,
                };
                fbConnectorLoadAllProgress = { loaded: fbConnectorItems.length, total: fbConnectorLoadAllProgress?.total ?? null };
                renderFbConnectorContent();
            } catch (e) {
                const msg = e?.message || String(e);
                const isRateLimit = msg.includes('too many calls') || msg.includes('rate');
                fbConnectorLoadError = isRateLimit
                    ? 'Load All paused: Meta is limiting requests. Wait 1–2 minutes, then click Resume to continue.'
                    : `Load All paused after ${fbConnectorItems.length} items. Click Resume to continue.`;
                fbConnectorLoadAllPaused = true;
                return;
            }
        }
        fbConnectorPaging.hasMore = false;
    }

    async function refreshFbConnectorTab() {
        const panel = overlay.querySelector('#importMediaFbConnectorPanel');
        if (!panel) return;
        fbConnectorLoading = true;
        fbConnectorSetAdAccountError = null;
        renderFbConnectorContent();
        try {
            fbConnectorTokenStatus = await checkMetaTokenStatus(clientId);
        } catch (e) {
            fbConnectorTokenStatus = { has_token: false, is_expired: false };
            console.error('[ImportMediaModal] FB Connector token check failed:', e);
        }
        // #region agent log (production: check console for [DEBUG-FB])
        console.info('[DEBUG-FB] refreshFbConnectorTab token', { defaultId: fbConnectorTokenStatus?.default_ad_account_id ?? null, defaultName: fbConnectorTokenStatus?.default_ad_account_name ?? null, hasToken: !!fbConnectorTokenStatus?.has_token });
        // #endregion
        fbConnectorLoading = false;
        const connected = !!(fbConnectorTokenStatus?.has_token && !fbConnectorTokenStatus?.is_expired);
        const hasDefaultAdAccount = !!(fbConnectorTokenStatus?.default_ad_account_id);

        if (connected && hasDefaultAdAccount && !fbConnectorTokenStatus?.default_ad_account_name) {
            try {
                const accountsRes = await fetchMetaAdAccounts(clientId);
                fbConnectorAdAccounts = accountsRes?.items || [];
            } catch (e) {
                console.warn('[ImportMediaModal] Fetch ad accounts for display name failed:', e);
            }
        }

        if (connected && !hasDefaultAdAccount) {
            fbConnectorNeedsAdAccount = true;
            fbConnectorLoadError = null;
            try {
                const accountsRes = await fetchMetaAdAccounts(clientId);
                fbConnectorAdAccounts = accountsRes?.items || [];
                fbConnectorSelectedAdAccountId = fbConnectorAdAccounts.length === 1 ? fbConnectorAdAccounts[0].id : null;
            } catch (e) {
                console.error('[ImportMediaModal] Fetch ad accounts failed:', e);
                fbConnectorAdAccounts = [];
                fbConnectorSetAdAccountError = e?.message || 'Failed to load ad accounts.';
            }
            renderFbConnectorContent();
            return;
        }

        if (connected && hasDefaultAdAccount && !fbConnectorNeedsAdAccount) {
            fbConnectorLoading = true;
            fbConnectorLoadError = null;
            fbConnectorItems = [];
            fbConnectorPaging = { after: null, hasMore: false };
            fbConnectorSelectedIds = new Set();
            const adId = getFbConnectorAdAccountId();
            const fetchOpts = { mediaType: 'all', limit: 24 };
            if (adId) fetchOpts.ad_account_id = adId;
            try {
                const res = await fetchMetaMediaLibrary(clientId, fetchOpts);
                fbConnectorItems = res.items || [];
                const p = res.paging;
                fbConnectorPaging = {
                    after: p?.after || null,
                    image_after: p?.image_after || null,
                    video_after: p?.video_after || null,
                    hasMore: !!(p && (p.after || p.image_after || p.video_after)),
                };
            } catch (e) {
                console.error('[ImportMediaModal] FB Connector fetch failed:', e);
                const msg = e?.message || String(e);
                const isNoDefault = msg.includes('No default ad account set');
                if (isNoDefault) {
                    fbConnectorNeedsAdAccount = true;
                    fbConnectorLoadError = null;
                    try {
                        const accountsRes = await fetchMetaAdAccounts(clientId);
                        fbConnectorAdAccounts = accountsRes?.items || [];
                        fbConnectorSelectedAdAccountId = fbConnectorAdAccounts.length === 1 ? fbConnectorAdAccounts[0].id : null;
                    } catch (err) {
                        console.error('[ImportMediaModal] Fetch ad accounts failed:', err);
                        fbConnectorAdAccounts = [];
                        fbConnectorSetAdAccountError = err?.message || 'Failed to load ad accounts.';
                    }
                } else {
                    fbConnectorLoadError = msg.includes('too many calls') || msg.includes('rate')
                        ? 'Meta is temporarily limiting requests for this ad account. Please try again in a few minutes.'
                        : (msg.length > 120 ? msg.slice(0, 120) + '…' : msg);
                }
                if (typeof window.onImportMediaFbConnectorError === 'function') {
                    window.onImportMediaFbConnectorError(e);
                }
            }
            fbConnectorLoading = false;
        }
        renderFbConnectorContent();
    }

    async function fetchFbConnectorAdAccountsAndShowSelector() {
        fbConnectorNeedsAdAccount = true;
        fbConnectorSetAdAccountError = null;
        try {
            const accountsRes = await fetchMetaAdAccounts(clientId);
            fbConnectorAdAccounts = accountsRes?.items || [];
            fbConnectorSelectedAdAccountId = fbConnectorTokenStatus?.default_ad_account_id || (fbConnectorAdAccounts.length === 1 ? fbConnectorAdAccounts[0].id : null);
        } catch (e) {
            console.error('[ImportMediaModal] Fetch ad accounts failed:', e);
            fbConnectorAdAccounts = [];
            fbConnectorSetAdAccountError = e?.message || 'Failed to load ad accounts.';
        }
        renderFbConnectorContent();
    }

    function updateFbConnectorFooterImportButton() {
        if (currentTab !== 'fb-connector') return;
        const btn = overlay.querySelector('#importMediaFbConnectorImportBtn');
        const importAllBtn = overlay.querySelector('#importMediaFbConnectorImportAllBtn');
        if (btn) {
            const selectedCount = fbConnectorItems.filter((it) => fbConnectorSelectedIds.has(`${it.type}:${it.id || ''}`)).length;
            btn.textContent = `Import Selected (${selectedCount})`;
            btn.disabled = selectedCount === 0 || fbConnectorImporting;
        }
        if (importAllBtn) importAllBtn.disabled = fbConnectorImporting;
    }

    async function doFbConnectorImport(toImport) {
        if (!toImport.length) return;
        const total = toImport.length;
        fbConnectorImporting = true;
        fbConnectorImportProgress = { imported: 0, failed: 0, total };
        currentImportAbortController = new AbortController();
        renderFbConnectorContent();
        updatePersistentImportProgress({ text: `Importing… 0 of ${total}`, imported: 0, failed: 0, total });
        try {
            const res = await importMetaMediaStream(
                clientId,
                toImport,
                (p) => {
                    fbConnectorImportProgress = { imported: p.imported ?? 0, failed: p.failed ?? 0, total };
                    if (overlay.isConnected) renderFbConnectorContent();
                    updatePersistentImportProgress({
                        text: `Importing… ${p.imported ?? 0} of ${total}${(p.failed ?? 0) > 0 ? ` (${p.failed} failed)` : ''}`,
                        imported: p.imported ?? 0,
                        failed: p.failed ?? 0,
                        total,
                    });
                },
                (img) => {
                    onImageAdded(img);
                },
                currentImportAbortController.signal,
                getFbConnectorAdAccountId()
            );
            currentImportAbortController = null;
            const imported = (res.items || []).length;
            const failed = res.failed_count ?? 0;
            fbConnectorImporting = false;
            fbConnectorImportProgress = null;
            fbConnectorSelectedIds.clear();
            if (overlay.isConnected) renderFbConnectorContent();
            updatePersistentImportProgress({
                complete: true,
                text: `Import complete. ${imported} item${imported !== 1 ? 's' : ''} added.${failed > 0 ? ` ${failed} failed.` : ''}`,
            });
            setTimeout(() => {
                updatePersistentImportProgress(null);
                if (overlay.isConnected) setTimeout(closeModal, 0);
            }, 3000);
            if (failed > 0 && overlay.isConnected) {
                alert(`Imported ${imported} items. ${failed} failed (e.g. rate limit). Try again later for failed items.`);
            }
        } catch (e) {
            currentImportAbortController = null;
            fbConnectorImporting = false;
            fbConnectorImportProgress = null;
            if (overlay.isConnected) renderFbConnectorContent();
            const cancelled = e.name === 'AbortError';
            updatePersistentImportProgress({
                complete: true,
                text: cancelled ? 'Import cancelled.' : `Import failed: ${e?.message || e}`,
            });
            setTimeout(() => updatePersistentImportProgress(null), cancelled ? 3000 : 4000);
            if (!cancelled) {
                console.error('[ImportMediaModal] FB Connector import failed:', e);
                if (overlay.isConnected) alert('Import failed: ' + (e.message || e));
            }
        }
    }

    async function doFbConnectorImportAll() {
        fbConnectorImporting = true;
        fbConnectorImportProgress = null;
        currentImportAbortController = new AbortController();
        renderFbConnectorContent();
        updatePersistentImportProgress({ text: 'Importing… 0 imported', imported: 0, failed: 0 });
        try {
            const res = await importAllMetaMediaStream(
                clientId,
                'all',
                (p) => {
                    const imported = p.imported ?? 0;
                    const failed = p.failed ?? 0;
                    fbConnectorImportProgress = { imported, failed };
                    if (overlay.isConnected) renderFbConnectorContent();
                    updatePersistentImportProgress({
                        text: `Importing… ${imported} imported${failed > 0 ? `, ${failed} failed` : ''}`,
                        imported,
                        failed,
                    });
                },
                (img) => {
                    onImageAdded(img);
                },
                currentImportAbortController.signal,
                getFbConnectorAdAccountId()
            );
            currentImportAbortController = null;
            const imported = (res.items || []).length;
            const failed = res.failed_count ?? 0;
            fbConnectorImporting = false;
            fbConnectorImportProgress = null;
            if (overlay.isConnected) renderFbConnectorContent();
            updatePersistentImportProgress({
                complete: true,
                text: `Import complete. ${imported} item${imported !== 1 ? 's' : ''} added.${failed > 0 ? ` ${failed} failed.` : ''}`,
            });
            setTimeout(() => {
                updatePersistentImportProgress(null);
                if (overlay.isConnected) setTimeout(closeModal, 0);
            }, 3000);
            if (failed > 0 && overlay.isConnected) {
                alert(`Imported ${imported} items. ${failed} failed (e.g. rate limit). Try again later for failed items.`);
            }
        } catch (e) {
            currentImportAbortController = null;
            fbConnectorImporting = false;
            fbConnectorImportProgress = null;
            if (overlay.isConnected) renderFbConnectorContent();
            const cancelled = e.name === 'AbortError';
            updatePersistentImportProgress({
                complete: true,
                text: cancelled ? 'Import cancelled.' : `Import failed: ${e?.message || e}`,
            });
            setTimeout(() => updatePersistentImportProgress(null), cancelled ? 3000 : 4000);
            if (!cancelled) {
                console.error('[ImportMediaModal] Import all failed:', e);
                if (overlay.isConnected) alert('Import all failed: ' + (e.message || e));
            }
        }
    }

    async function handleSetAdAccount(adAccountId, adAccountName) {
        fbConnectorSetAdAccountError = null;
        fbConnectorSessionAdAccountId = adAccountId;
        fbConnectorSessionAdAccountName = adAccountName || null;
        fbConnectorNeedsAdAccount = false;
        fbConnectorLoading = true;
        fbConnectorLoadError = null;
        fbConnectorItems = [];
        fbConnectorPaging = { after: null, hasMore: false };
        fbConnectorSelectedIds = new Set();
        renderFbConnectorContent();
        try {
            const res = await fetchMetaMediaLibrary(clientId, { mediaType: 'all', limit: 24, ad_account_id: adAccountId });
            fbConnectorItems = res.items || [];
            const p = res.paging;
            fbConnectorPaging = {
                after: p?.after || null,
                image_after: p?.image_after || null,
                video_after: p?.video_after || null,
                hasMore: !!(p && (p.after || p.image_after || p.video_after)),
            };
        } catch (e) {
            console.error('[ImportMediaModal] Fetch media failed:', e);
            fbConnectorSetAdAccountError = e?.message || 'Failed to load media.';
        }
        fbConnectorLoading = false;
        renderFbConnectorContent();
    }

    function renderFbConnectorContent() {
        const panel = overlay.querySelector('#importMediaFbConnectorPanel');
        if (!panel) return;
        const connected = !!(fbConnectorTokenStatus?.has_token && !fbConnectorTokenStatus?.is_expired);
        const effectiveAdAccountId = getFbConnectorAdAccountId();
        let adAccountName = fbConnectorSessionAdAccountName || fbConnectorTokenStatus?.default_ad_account_name || '';
        if (!adAccountName && effectiveAdAccountId && fbConnectorAdAccounts?.length) {
            const acc = fbConnectorAdAccounts.find((a) => a.id === effectiveAdAccountId);
            adAccountName = acc ? (acc.name || acc.id) : `Account (${effectiveAdAccountId})`;
        } else if (!adAccountName && effectiveAdAccountId) {
            adAccountName = `Account (${effectiveAdAccountId})`;
        }
        // #region agent log (production: check console for [DEBUG-FB])
        console.info('[DEBUG-FB] renderFbConnectorContent', { defaultId: fbConnectorTokenStatus?.default_ad_account_id ?? null, defaultName: fbConnectorTokenStatus?.default_ad_account_name ?? null, adAccountNamePassed: adAccountName, needsAdAccount: fbConnectorNeedsAdAccount, adAccountsLength: fbConnectorAdAccounts?.length ?? 0, loadError: !!fbConnectorLoadError });
        // #endregion
        renderFbConnectorPicker(panel, {
            connected,
            accountName: fbConnectorTokenStatus?.meta_user_name || '',
            adAccountName,
            needsAdAccount: fbConnectorNeedsAdAccount,
            adAccounts: fbConnectorAdAccounts,
            selectedAdAccountId: fbConnectorSelectedAdAccountId,
            setAdAccountError: fbConnectorSetAdAccountError,
            items: fbConnectorItems,
            selectedIds: fbConnectorSelectedIds,
            loading: fbConnectorLoading,
            importing: fbConnectorImporting,
            paging: fbConnectorPaging,
            loadAllProgress: fbConnectorLoadAllProgress,
            loadError: fbConnectorLoadError,
            loadAllPaused: fbConnectorLoadAllPaused,
            importProgress: fbConnectorImportProgress,
            onSetAdAccount: handleSetAdAccount,
            onAdAccountSelectionChange: (id) => {
                fbConnectorSelectedAdAccountId = id || null;
                renderFbConnectorContent();
            },
            onChangeAdAccount: () => fetchFbConnectorAdAccountsAndShowSelector(),
            onRetryLoad: () => {
                fbConnectorLoadError = null;
                refreshFbConnectorTab();
            },
            onConnect: async () => {
                try {
                    await openMetaOAuthPopup(clientId);
                    await refreshFbConnectorTab();
                } catch (e) {
                    console.error('[ImportMediaModal] Meta OAuth failed:', e);
                }
            },
            onLoadMore: async (cursorOrPaging) => {
                try {
                    const opts = { mediaType: 'all', limit: 24 };
                    const adId = getFbConnectorAdAccountId();
                    if (adId) opts.ad_account_id = adId;
                    if (typeof cursorOrPaging === 'object' && cursorOrPaging !== null) {
                        if (cursorOrPaging.image_after) opts.image_after = cursorOrPaging.image_after;
                        if (cursorOrPaging.video_after) opts.video_after = cursorOrPaging.video_after;
                    } else {
                        opts.after = typeof cursorOrPaging === 'object' ? cursorOrPaging?.after : cursorOrPaging;
                    }
                    const res = await fetchMetaMediaLibrary(clientId, opts);
                    fbConnectorItems = fbConnectorItems.concat(res.items || []);
                    const p = res.paging;
                    fbConnectorPaging = {
                        after: p?.after || null,
                        image_after: p?.image_after || null,
                        video_after: p?.video_after || null,
                        hasMore: !!(p && (p.after || p.image_after || p.video_after)),
                    };
                    renderFbConnectorContent();
                } catch (e) {
                    console.error('[ImportMediaModal] FB Connector load more failed:', e);
                }
            },
            onImport: (toImport) => doFbConnectorImport(toImport),
            onToggleSelection: (key) => {
                if (fbConnectorSelectedIds.has(key)) {
                    fbConnectorSelectedIds.delete(key);
                } else {
                    fbConnectorSelectedIds.add(key);
                }
                renderFbConnectorContent();
            },
            onSelectAll: () => {
                fbConnectorItems.forEach((it) => fbConnectorSelectedIds.add(`${it.type}:${it.id || ''}`));
                renderFbConnectorContent();
            },
            onDeselectAll: () => {
                fbConnectorSelectedIds.clear();
                renderFbConnectorContent();
            },
        });
        updateFbConnectorFooterImportButton();
    }
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            switchTab(tab.dataset.tab);
        });
    });
    
    // ============ File Upload Tab ============
    
    async function handleMediaUpload(file) {
        if (!file.type.startsWith('image/') && !file.type.startsWith('video/')) {
            alert('Please select an image or video file');
            return;
        }
        
        const MAX_SIZE = 50 * 1024 * 1024;
        if (file.size > MAX_SIZE) {
            alert(`File is too large. Maximum size is 50MB. Your file is ${formatFileSize(file.size)}.`);
            return;
        }
        
        dropzone.style.display = 'none';
        uploadProgress.style.display = 'block';
        uploadProgressBar.style.width = '0%';
        uploadProgressText.textContent = 'Uploading...';
        
        try {
            let progressValue = 0;
            const progressInterval = setInterval(() => {
                progressValue += 10;
                if (progressValue < 90) {
                    uploadProgressBar.style.width = progressValue + '%';
                }
            }, 100);
            
            const image = await uploadAdImage(clientId, file);
            
            clearInterval(progressInterval);
            uploadProgressBar.style.width = '100%';
            uploadProgressText.textContent = 'Upload complete!';
            
            addImageToCache(image);
            
            if (onImageAdded) {
                onImageAdded(image);
            }
            
            setTimeout(() => {
                closeModal();
            }, 500);
        } catch (error) {
            console.error('[ImportMediaModal] Upload failed:', error);
            alert('Failed to upload: ' + error.message);
            dropzone.style.display = 'block';
            uploadProgress.style.display = 'none';
        }
    }
    
    async function handleBulkMediaUpload(files) {
        const MAX_SIZE = 50 * 1024 * 1024;
        const oversizedFiles = files.filter(f => f.size > MAX_SIZE);
        if (oversizedFiles.length > 0) {
            const names = oversizedFiles.map(f => `${f.name} (${formatFileSize(f.size)})`).join(', ');
            alert(`Some files are too large (max 50MB): ${names}`);
            files = files.filter(f => f.size <= MAX_SIZE);
            if (files.length === 0) return;
        }
        
        dropzone.style.display = 'none';
        uploadProgress.style.display = 'block';
        uploadProgressBar.style.width = '0%';
        
        const totalFiles = files.length;
        let successCount = 0;
        let failCount = 0;
        const errors = [];
        
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const progressPercent = Math.round((i / totalFiles) * 100);
            uploadProgressBar.style.width = progressPercent + '%';
            uploadProgressText.textContent = `Uploading ${i + 1} of ${totalFiles}...`;
            
            try {
                const image = await uploadAdImage(clientId, file);
                addImageToCache(image);
                
                if (onImageAdded) {
                    onImageAdded(image);
                }
                
                successCount++;
            } catch (error) {
                failCount++;
                errors.push(`${file.name}: ${error.message}`);
            }
        }
        
        uploadProgressBar.style.width = '100%';
        
        if (failCount === 0) {
            uploadProgressText.textContent = `Successfully uploaded ${successCount} file(s)`;
            setTimeout(() => {
                closeModal();
            }, 1500);
        } else {
            uploadProgressText.textContent = `Uploaded ${successCount}, failed ${failCount}`;
            alert(`Upload complete:\n\nSuccess: ${successCount}\nFailed: ${failCount}\n\nErrors:\n${errors.join('\n')}`);
            dropzone.style.display = 'block';
            uploadProgress.style.display = 'none';
        }
    }
    
    // Click to select file
    dropzone.addEventListener('click', () => fileInput.click());
    
    // File input change
    fileInput.addEventListener('change', async (e) => {
        const files = Array.from(e.target.files || []);
        if (files.length > 0) {
            if (files.length === 1) {
                await handleMediaUpload(files[0]);
            } else {
                await handleBulkMediaUpload(files);
            }
        }
    });
    
    // Drag and drop
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('is-dragover');
    });
    
    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('is-dragover');
    });
    
    dropzone.addEventListener('drop', async (e) => {
        e.preventDefault();
        dropzone.classList.remove('is-dragover');
        const files = Array.from(e.dataTransfer.files).filter(f => 
            f.type.startsWith('image/') || f.type.startsWith('video/')
        );
        if (files.length > 0) {
            if (files.length === 1) {
                await handleMediaUpload(files[0]);
            } else {
                await handleBulkMediaUpload(files);
            }
        }
    });
    
    // ============ Meta Ads Library Tab ============
    
    // Validate on input
    metaUrlInput.addEventListener('input', () => {
        const url = metaUrlInput.value.trim();
        if (url && !isValidMetaAdsLibraryUrl(url)) {
            metaErrorEl.textContent = 'Please enter a valid Meta Ads Library URL with a page ID (view_all_page_id parameter)';
            metaErrorEl.style.display = 'block';
            metaSubmitBtn.disabled = true;
        } else {
            metaErrorEl.style.display = 'none';
            metaSubmitBtn.disabled = !url;
        }
    });
    
    // Handle Enter key in URL input
    metaUrlInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !metaSubmitBtn.disabled) {
            metaSubmitBtn.click();
        }
    });
    
    /**
     * Update modal UI with job status
     */
    const updateMetaModalUI = (job) => {
        if (!document.body.contains(overlay)) return;
        
        if (job.status === 'running') {
            metaProgressText.textContent = 'Importing media...';
            if (job.total_found > 0) {
                metaProgressBarContainer.style.display = 'block';
                const percent = Math.round((job.total_imported / job.total_found) * 100);
                metaProgressBar.style.width = `${percent}%`;
                metaProgressDetail.textContent = `${job.total_imported} of ${job.total_found} items imported`;
            } else {
                metaProgressDetail.textContent = `${job.total_imported} items imported`;
            }
        } else if (job.status === 'pending') {
            metaProgressText.textContent = 'Connecting to Meta Ads Library...';
            metaProgressDetail.textContent = 'Scanning page for ads';
        } else if (job.status === 'complete' || job.status === 'failed') {
            metaProgressEl.style.display = 'none';
            metaResultsEl.style.display = 'flex';
            
            if (job.status === 'complete') {
                if (job.total_imported > 0) {
                    metaResultsText.textContent = `Successfully imported ${job.total_imported} media file${job.total_imported > 1 ? 's' : ''}`;
                } else {
                    metaResultsEl.querySelector('.import-media-meta-results__icon').textContent = '⚠️';
                    metaResultsText.textContent = 'No media found on this page';
                }
            } else {
                metaResultsEl.querySelector('.import-media-meta-results__icon').textContent = '❌';
                metaResultsText.textContent = job.error_message || 'Import failed';
            }
            
            footerEl.innerHTML = `
                <button class="import-media-modal__submit import-media-done-btn">Done</button>
            `;
            footerEl.querySelector('.import-media-done-btn').addEventListener('click', closeModal);
        }
    };
    
    // Handle meta submit
    metaSubmitBtn.addEventListener('click', async () => {
        const url = metaUrlInput.value.trim();
        
        if (!isValidMetaAdsLibraryUrl(url)) {
            metaErrorEl.textContent = 'Please enter a valid Meta Ads Library URL';
            metaErrorEl.style.display = 'block';
            return;
        }
        
        // Disable tab switching during import
        tabs.forEach(tab => tab.disabled = true);
        
        metaFormEl.style.display = 'none';
        metaProgressEl.style.display = 'flex';
        metaSubmitBtn.disabled = true;
        metaSubmitBtn.textContent = 'Importing...';
        
        footerEl.innerHTML = `
            <button class="import-media-modal__cancel import-media-close-btn">Close</button>
        `;
        footerEl.querySelector('.import-media-close-btn').addEventListener('click', closeModal);
        
        try {
            metaProgressText.textContent = 'Starting import job...';
            metaProgressDetail.textContent = '';
            
            const job = await startMetaImportJob(clientId, url);
            
            if (!job || !job.id) {
                throw new Error('Failed to create import job');
            }
            
            currentJobId = job.id;
            console.log('[ImportMediaModal] Import job started:', job.id);
            
            const jobData = startBackgroundPolling(job.id, (result) => {
                if (onImageAdded) {
                    onImageAdded(result);
                }
            });
            
            if (jobData.interval) {
                clearInterval(jobData.interval);
            }
            jobData.interval = setInterval(() => pollJobStatusBackground(job.id, updateMetaModalUI), 2000);
            
            await pollJobStatusBackground(job.id, updateMetaModalUI);
            
        } catch (error) {
            console.error('[ImportMediaModal] Import failed:', error);
            
            if (currentJobId) {
                stopJobPolling(currentJobId);
            }
            
            // Re-enable tabs
            tabs.forEach(tab => tab.disabled = false);
            
            metaProgressEl.style.display = 'none';
            metaFormEl.style.display = 'block';
            metaErrorEl.textContent = error.message || 'Failed to start import. Please try again.';
            metaErrorEl.style.display = 'block';
            metaSubmitBtn.disabled = false;
            metaSubmitBtn.textContent = 'Import from Meta';
            
            footerEl.innerHTML = `
                <button class="import-media-modal__cancel">Cancel</button>
                <button class="import-media-modal__submit" id="importMediaMetaSubmit">Import from Meta</button>
            `;
            footerEl.querySelector('.import-media-modal__cancel').addEventListener('click', closeModal);
        }
    });
    
    // ============ FB Connector footer buttons ============
    const fbConnectorImportBtn = overlay.querySelector('#importMediaFbConnectorImportBtn');
    const fbConnectorImportAllBtn = overlay.querySelector('#importMediaFbConnectorImportAllBtn');
    if (fbConnectorImportBtn) {
        fbConnectorImportBtn.addEventListener('click', () => {
            const toImport = fbConnectorItems
                .filter((it) => fbConnectorSelectedIds.has(`${it.type}:${it.id || ''}`))
                .map((it) => ({
                    type: it.type,
                    hash: it.type === 'image' ? it.id : undefined,
                    video_id: it.type === 'video' ? it.id : undefined,
                    original_url: it.original_url || it.source || '',
                    filename: it.name ? `${it.name}.${it.type === 'video' ? 'mp4' : 'jpg'}` : undefined,
                    thumbnail_url: it.type === 'video' ? it.thumbnail_url : undefined,
                }));
            doFbConnectorImport(toImport);
        });
    }
    if (fbConnectorImportAllBtn) {
        fbConnectorImportAllBtn.addEventListener('click', () => doFbConnectorImportAll());
    }

    // ============ Modal Close Handlers ============
    
    closeBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);
    
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            closeModal();
        }
    });
    
    const handleEscape = (e) => {
        if (e.key === 'Escape') {
            closeModal();
        }
    };
    document.addEventListener('keydown', handleEscape);
}
