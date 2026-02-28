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
    fetchMetaMediaLibrary,
    fetchMetaMediaLibraryCounts,
    importMetaMedia,
    openMetaOAuthPopup,
} from '/js/services/api-meta.js';
import { addImageToCache } from '/js/state/images-state.js';
import { renderFbConnectorPicker } from '/js/renderers/fb-connector-media-picker.js';

// ============ Module-level state for background polling ============

// Track active jobs and their polling intervals
const activeJobs = new Map(); // jobId -> { interval, addedImageIds, onComplete }

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
                            placeholder="https://www.facebook.com/ads/library/?...&view_all_page_id=..."
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
        } else if (tabName === 'fb-connector') {
            metaSubmitBtn.style.display = 'none';
            refreshFbConnectorTab();
        } else {
            metaSubmitBtn.style.display = 'block';
            const url = metaUrlInput.value.trim();
            metaSubmitBtn.disabled = !url || !isValidMetaAdsLibraryUrl(url);
        }
    }

    // ============ FB Connector tab state and refresh ============
    let fbConnectorTokenStatus = null;
    let fbConnectorFilter = 'all';
    let fbConnectorItems = [];
    let fbConnectorPaging = { after: null, hasMore: false };
    let fbConnectorSelectedIds = new Set();
    let fbConnectorLoading = false;
    let fbConnectorImporting = false;
    /** When Load All is running: { loaded, total } (total may be null if API has no count). */
    let fbConnectorLoadAllProgress = null;
    /** Error message when initial media fetch fails (e.g. rate limit). Cleared on retry or successful load. */
    let fbConnectorLoadError = null;

    async function refreshFbConnectorTab() {
        const panel = overlay.querySelector('#importMediaFbConnectorPanel');
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/0ea04ade-be37-4438-ba64-4de28c7d11e9',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'6da1c5'},body:JSON.stringify({sessionId:'6da1c5',location:'import-media-modal.js:refreshFbConnectorTab:entry',message:'FB Connector refresh',data:{panelFound:!!panel},timestamp:Date.now()})}).catch(()=>{});
        // #endregion
        if (!panel) return;
        fbConnectorLoading = true;
        try {
            fbConnectorTokenStatus = await checkMetaTokenStatus(clientId);
        } catch (e) {
            fbConnectorTokenStatus = { has_token: false, is_expired: false };
            console.error('[ImportMediaModal] FB Connector token check failed:', e);
        }
        fbConnectorLoading = false;
        const willFetch = !!(fbConnectorTokenStatus?.has_token && !fbConnectorTokenStatus?.is_expired);
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/0ea04ade-be37-4438-ba64-4de28c7d11e9',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'6da1c5'},body:JSON.stringify({sessionId:'6da1c5',location:'import-media-modal.js:refreshFbConnectorTab:afterToken',message:'Token check done',data:{has_token:!!fbConnectorTokenStatus?.has_token,is_expired:!!fbConnectorTokenStatus?.is_expired,willFetch},timestamp:Date.now()})}).catch(()=>{});
        // #endregion
        if (willFetch) {
            fbConnectorLoading = true;
            fbConnectorLoadError = null;
            fbConnectorItems = [];
            fbConnectorPaging = { after: null, hasMore: false };
            fbConnectorSelectedIds = new Set();
            try {
                const res = await fetchMetaMediaLibrary(clientId, {
                    mediaType: fbConnectorFilter,
                    limit: 24,
                });
                fbConnectorItems = res.items || [];
                const p = res.paging;
                fbConnectorPaging = {
                    after: p?.after || null,
                    image_after: p?.image_after || null,
                    video_after: p?.video_after || null,
                    hasMore: !!(p && (p.after || p.image_after || p.video_after)),
                };
                // #region agent log
                fetch('http://127.0.0.1:7242/ingest/0ea04ade-be37-4438-ba64-4de28c7d11e9',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'6da1c5'},body:JSON.stringify({sessionId:'6da1c5',location:'import-media-modal.js:refreshFbConnectorTab:fetchOk',message:'Media fetch success',data:{itemsLength:fbConnectorItems.length,hasMore:fbConnectorPaging.hasMore},timestamp:Date.now()})}).catch(()=>{});
                // #endregion
            } catch (e) {
                // #region agent log
                fetch('http://127.0.0.1:7242/ingest/0ea04ade-be37-4438-ba64-4de28c7d11e9',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'6da1c5'},body:JSON.stringify({sessionId:'6da1c5',location:'import-media-modal.js:refreshFbConnectorTab:fetchCatch',message:'Media fetch failed',data:{error:String(e?.message||e)},timestamp:Date.now()})}).catch(()=>{});
                // #endregion
                console.error('[ImportMediaModal] FB Connector fetch failed:', e);
                const msg = e?.message || String(e);
                fbConnectorLoadError = msg.includes('too many calls') || msg.includes('rate')
                    ? 'Meta is temporarily limiting requests for this ad account. Please try again in a few minutes.'
                    : (msg.length > 120 ? msg.slice(0, 120) + '…' : msg);
                if (typeof window.onImportMediaFbConnectorError === 'function') {
                    window.onImportMediaFbConnectorError(e);
                }
            }
            fbConnectorLoading = false;
        }
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/0ea04ade-be37-4438-ba64-4de28c7d11e9',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'6da1c5'},body:JSON.stringify({sessionId:'6da1c5',location:'import-media-modal.js:refreshFbConnectorTab:beforeRender',message:'About to render',data:{itemsLength:fbConnectorItems.length,loading:fbConnectorLoading},timestamp:Date.now()})}).catch(()=>{});
        // #endregion
        renderFbConnectorContent();
    }

    function renderFbConnectorContent() {
        const panel = overlay.querySelector('#importMediaFbConnectorPanel');
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/0ea04ade-be37-4438-ba64-4de28c7d11e9',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'6da1c5'},body:JSON.stringify({sessionId:'6da1c5',location:'import-media-modal.js:renderFbConnectorContent:entry',message:'Render content',data:{panelFound:!!panel,itemsLength:fbConnectorItems.length,loading:fbConnectorLoading},timestamp:Date.now()})}).catch(()=>{});
        // #endregion
        if (!panel) return;
        const connected = !!(fbConnectorTokenStatus?.has_token && !fbConnectorTokenStatus?.is_expired);
        renderFbConnectorPicker(panel, {
            connected,
            accountName: fbConnectorTokenStatus?.meta_user_name || '',
            adAccountName: fbConnectorTokenStatus?.default_ad_account_name || '',
            items: fbConnectorItems,
            selectedIds: fbConnectorSelectedIds,
            loading: fbConnectorLoading,
            importing: fbConnectorImporting,
            paging: fbConnectorPaging,
            mediaFilter: fbConnectorFilter,
            loadAllProgress: fbConnectorLoadAllProgress,
            loadError: fbConnectorLoadError,
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
                    const opts = {
                        mediaType: fbConnectorFilter,
                        limit: 24,
                    };
                    if (fbConnectorFilter === 'all' && typeof cursorOrPaging === 'object' && cursorOrPaging !== null) {
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
            onLoadAll: async () => {
                try {
                    fbConnectorLoading = true;
                    fbConnectorLoadAllProgress = null;
                    renderFbConnectorContent();
                    let total = null;
                    try {
                        const counts = await fetchMetaMediaLibraryCounts(clientId, fbConnectorFilter);
                        if (fbConnectorFilter === 'all') {
                            const ic = counts.image_count ?? 0;
                            const vc = counts.video_count ?? 0;
                            total = (counts.image_count != null || counts.video_count != null) ? ic + vc : null;
                        } else if (fbConnectorFilter === 'image') {
                            total = counts.image_count ?? null;
                        } else {
                            total = counts.video_count ?? null;
                        }
                    } catch (_) {
                        total = null;
                    }
                    fbConnectorLoadAllProgress = { loaded: fbConnectorItems.length, total };
                    renderFbConnectorContent();
                    let iter = 0;
                    const maxLoadAllIterations = 100;
                    while (fbConnectorPaging.hasMore && iter < maxLoadAllIterations) {
                        iter++;
                        const opts = {
                            mediaType: fbConnectorFilter,
                            limit: 50,
                        };
                        if (fbConnectorFilter === 'all') {
                            if (fbConnectorPaging.image_after) opts.image_after = fbConnectorPaging.image_after;
                            if (fbConnectorPaging.video_after) opts.video_after = fbConnectorPaging.video_after;
                        } else {
                            opts.after = fbConnectorPaging.after;
                        }
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
                        fbConnectorLoadAllProgress = { loaded: fbConnectorItems.length, total };
                        renderFbConnectorContent();
                    }
                    fbConnectorPaging.hasMore = false;
                } catch (e) {
                    console.error('[ImportMediaModal] FB Connector load all failed:', e);
                } finally {
                    fbConnectorLoading = false;
                    fbConnectorLoadAllProgress = null;
                    renderFbConnectorContent();
                }
            },
            onImport: async (toImport) => {
                if (!toImport.length) return;
                fbConnectorImporting = true;
                renderFbConnectorContent();
                try {
                    const res = await importMetaMedia(clientId, toImport);
                    (res.items || []).forEach((img) => {
                        addImageToCache(img);
                        if (onImageAdded) onImageAdded(img);
                    });
                    fbConnectorSelectedIds.clear();
                    fbConnectorImporting = false;
                    renderFbConnectorContent();
                    setTimeout(() => closeModal(), 500);
                } catch (e) {
                    fbConnectorImporting = false;
                    renderFbConnectorContent();
                    console.error('[ImportMediaModal] FB Connector import failed:', e);
                    alert('Import failed: ' + (e.message || e));
                }
            },
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
            onFilterChange: (filter) => {
                fbConnectorFilter = filter;
                fbConnectorItems = [];
                fbConnectorPaging = { after: null, hasMore: false };
                fbConnectorSelectedIds = new Set();
                refreshFbConnectorTab();
            },
        });
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
