/**
 * Meta Ads Library Import Modal Module
 * Handles importing media from Meta Ads Library URLs using background jobs.
 * Polling continues in the background even if the dialog is closed.
 */

import { 
    startMetaImportJob, 
    getImportJobStatus, 
    getImportJobImages 
} from '/js/services/api-meta-import.js';
import { addImageToCache, getImagesCache } from '/js/state/images-state.js';

// ============ Module-level state for background polling ============

// Track active jobs and their polling intervals
const activeJobs = new Map(); // jobId -> { interval, addedImageIds, onComplete }

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
    // Use existing appendImageToGrid if available
    if (typeof window.appendImageToGrid === 'function') {
        window.appendImageToGrid(image);
    } else if (typeof window.renderImages === 'function') {
        // Get current images and add this one
        addImageToCache(image);
        // Re-render the grid (fallback)
        window.renderImages();
    } else {
        // Just add to cache - will show on refresh
        addImageToCache(image);
    }
}

/**
 * Stop polling for a specific job
 * @param {string} jobId - Job ID to stop
 */
function stopJobPolling(jobId) {
    const jobData = activeJobs.get(jobId);
    if (jobData && jobData.interval) {
        clearInterval(jobData.interval);
        activeJobs.delete(jobId);
        console.log('[MetaImportModal] Stopped polling for job:', jobId);
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
        
        // Update modal UI if still open
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
            // Ensure we have all images before stopping
            try {
                const allImages = await getImportJobImages(jobId);
                for (const image of allImages.items || []) {
                    if (!jobData.addedImageIds.has(image.id)) {
                        jobData.addedImageIds.add(image.id);
                        appendImageToGridRealtime(image);
                    }
                }
            } catch (e) {
                console.warn('[MetaImportModal] Failed to fetch all images:', e);
            }
            
            // Stop polling
            stopJobPolling(jobId);
            
            // Notify completion callback
            if (jobData.onComplete) {
                jobData.onComplete({
                    imported: job.total_imported,
                    total_found: job.total_found,
                    status: job.status,
                    error_message: job.error_message
                });
            }
            
            console.log('[MetaImportModal] Job complete:', jobId, 'imported:', job.total_imported);
        }
        
    } catch (error) {
        console.error('[MetaImportModal] Polling error:', error);
        // Don't stop polling on transient errors
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
    
    // Start interval polling (every 2 seconds)
    jobData.interval = setInterval(() => pollJobStatusBackground(jobId), 2000);
    
    console.log('[MetaImportModal] Started background polling for job:', jobId);
    
    return jobData;
}

/**
 * Show Meta Ads Library import modal
 * @param {Function} onImportComplete - Callback when import is complete
 */
export function showMetaImportModal(onImportComplete) {
    const clientId = window.appStateGet?.('currentClientId') || 
                     document.getElementById('clientSelect')?.value;
    
    if (!clientId) {
        alert('Please select a client first');
        return;
    }
    
    // Create modal overlay
    const overlay = document.createElement('div');
    overlay.className = 'meta-import-overlay';
    overlay.innerHTML = `
        <div class="meta-import-modal">
            <div class="meta-import-modal__header">
                <h2>Import from Meta Ads Library</h2>
                <button class="meta-import-modal__close">×</button>
            </div>
            <div class="meta-import-modal__body">
                <div class="meta-import-form" id="metaImportForm">
                    <label class="meta-import-label" for="metaAdsLibraryUrl">
                        Meta Ads Library URL
                    </label>
                    <input 
                        type="url" 
                        id="metaAdsLibraryUrl" 
                        class="meta-import-input"
                        placeholder="https://www.facebook.com/ads/library/?...&view_all_page_id=..."
                    >
                    <p class="meta-import-hint">
                        Paste a Meta Ads Library URL with a page ID to import all media from that page's ads.
                    </p>
                    <p class="meta-import-error" id="metaImportError" style="display: none;"></p>
                </div>
                <div class="meta-import-progress" id="metaImportProgress" style="display: none;">
                    <div class="meta-import-progress__spinner"></div>
                    <p class="meta-import-progress__text" id="metaImportProgressText">Starting import...</p>
                    <p class="meta-import-progress__detail" id="metaImportProgressDetail"></p>
                    <div class="meta-import-progress__bar-container" id="metaImportProgressBarContainer" style="display: none;">
                        <div class="meta-import-progress__bar" id="metaImportProgressBar"></div>
                    </div>
                    <div class="meta-import-background-notice">
                        <p>You can close this dialog - the import will continue in the background.</p>
                        <p class="meta-import-background-notice__hint">Imported media will appear automatically as they're processed.</p>
                    </div>
                </div>
                <div class="meta-import-results" id="metaImportResults" style="display: none;">
                    <div class="meta-import-results__icon">✓</div>
                    <p class="meta-import-results__text" id="metaImportResultsText"></p>
                </div>
            </div>
            <div class="meta-import-modal__footer" id="metaImportFooter">
                <button class="meta-import-modal__cancel">Cancel</button>
                <button class="meta-import-modal__submit" id="metaImportSubmit">Import Media</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(overlay);
    
    const urlInput = overlay.querySelector('#metaAdsLibraryUrl');
    const submitBtn = overlay.querySelector('#metaImportSubmit');
    const errorEl = overlay.querySelector('#metaImportError');
    const formEl = overlay.querySelector('#metaImportForm');
    const progressEl = overlay.querySelector('#metaImportProgress');
    const progressText = overlay.querySelector('#metaImportProgressText');
    const progressDetail = overlay.querySelector('#metaImportProgressDetail');
    const progressBarContainer = overlay.querySelector('#metaImportProgressBarContainer');
    const progressBar = overlay.querySelector('#metaImportProgressBar');
    const resultsEl = overlay.querySelector('#metaImportResults');
    const resultsText = overlay.querySelector('#metaImportResultsText');
    const footerEl = overlay.querySelector('#metaImportFooter');
    const closeBtn = overlay.querySelector('.meta-import-modal__close');
    const cancelBtn = overlay.querySelector('.meta-import-modal__cancel');
    
    // Track current job for this modal
    let currentJobId = null;
    
    // Focus input
    urlInput.focus();
    
    // Close modal helper (does NOT stop polling)
    const closeModal = () => {
        overlay.remove();
        document.removeEventListener('keydown', handleEscape);
    };
    
    // Validate on input
    urlInput.addEventListener('input', () => {
        const url = urlInput.value.trim();
        if (url && !isValidMetaAdsLibraryUrl(url)) {
            errorEl.textContent = 'Please enter a valid Meta Ads Library URL with a page ID (view_all_page_id parameter)';
            errorEl.style.display = 'block';
            submitBtn.disabled = true;
        } else {
            errorEl.style.display = 'none';
            submitBtn.disabled = !url;
        }
    });
    
    /**
     * Update modal UI with job status (called from polling)
     */
    const updateModalUI = (job) => {
        // Only update if modal is still in DOM
        if (!document.body.contains(overlay)) return;
        
        if (job.status === 'running') {
            progressText.textContent = 'Importing media...';
            if (job.total_found > 0) {
                progressBarContainer.style.display = 'block';
                const percent = Math.round((job.total_imported / job.total_found) * 100);
                progressBar.style.width = `${percent}%`;
                progressDetail.textContent = `${job.total_imported} of ${job.total_found} items imported`;
            } else {
                progressDetail.textContent = `${job.total_imported} items imported`;
            }
        } else if (job.status === 'pending') {
            progressText.textContent = 'Connecting to Meta Ads Library...';
            progressDetail.textContent = 'Scanning page for ads';
        } else if (job.status === 'complete' || job.status === 'failed') {
            // Show results
            progressEl.style.display = 'none';
            resultsEl.style.display = 'flex';
            
            if (job.status === 'complete') {
                if (job.total_imported > 0) {
                    resultsText.textContent = `Successfully imported ${job.total_imported} media file${job.total_imported > 1 ? 's' : ''}`;
                } else {
                    resultsEl.querySelector('.meta-import-results__icon').textContent = '⚠️';
                    resultsText.textContent = 'No media found on this page';
                }
            } else {
                resultsEl.querySelector('.meta-import-results__icon').textContent = '❌';
                resultsText.textContent = job.error_message || 'Import failed';
            }
            
            // Update footer
            footerEl.innerHTML = `
                <button class="meta-import-modal__submit meta-import-done-btn">Done</button>
            `;
            footerEl.querySelector('.meta-import-done-btn').addEventListener('click', closeModal);
        }
    };
    
    // Handle submit
    submitBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        
        if (!isValidMetaAdsLibraryUrl(url)) {
            errorEl.textContent = 'Please enter a valid Meta Ads Library URL';
            errorEl.style.display = 'block';
            return;
        }
        
        // Show progress
        formEl.style.display = 'none';
        progressEl.style.display = 'flex';
        submitBtn.disabled = true;
        submitBtn.textContent = 'Importing...';
        
        // Update footer to allow closing while import runs
        footerEl.innerHTML = `
            <button class="meta-import-modal__cancel meta-import-close-btn">Close</button>
        `;
        footerEl.querySelector('.meta-import-close-btn').addEventListener('click', closeModal);
        
        try {
            progressText.textContent = 'Starting import job...';
            progressDetail.textContent = '';
            
            // Start the import job
            const job = await startMetaImportJob(clientId, url);
            
            if (!job || !job.id) {
                throw new Error('Failed to create import job');
            }
            
            currentJobId = job.id;
            console.log('[MetaImportModal] Import job started:', job.id);
            
            // Start background polling with UI updates and completion callback
            const jobData = startBackgroundPolling(job.id, (result) => {
                // Notify caller on complete
                if (onImportComplete) {
                    onImportComplete(result);
                }
            });
            
            // Override the polling function to also update modal UI
            if (jobData.interval) {
                clearInterval(jobData.interval);
            }
            jobData.interval = setInterval(() => pollJobStatusBackground(job.id, updateModalUI), 2000);
            
            // Do initial poll immediately
            await pollJobStatusBackground(job.id, updateModalUI);
            
        } catch (error) {
            console.error('[MetaImportModal] Import failed:', error);
            
            if (currentJobId) {
                stopJobPolling(currentJobId);
            }
            
            progressEl.style.display = 'none';
            formEl.style.display = 'block';
            errorEl.textContent = error.message || 'Failed to start import. Please try again.';
            errorEl.style.display = 'block';
            submitBtn.disabled = false;
            submitBtn.textContent = 'Import Media';
            
            footerEl.innerHTML = `
                <button class="meta-import-modal__cancel meta-import-cancel-btn">Cancel</button>
                <button class="meta-import-modal__submit" id="metaImportSubmit">Import Media</button>
            `;
            footerEl.querySelector('.meta-import-cancel-btn').addEventListener('click', closeModal);
        }
    });
    
    // Handle Enter key
    urlInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !submitBtn.disabled) {
            submitBtn.click();
        }
    });
    
    // Close button handlers (do NOT stop polling - import continues in background)
    closeBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);
    
    // Close on overlay click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            closeModal();
        }
    });
    
    // Close on Escape
    const handleEscape = (e) => {
        if (e.key === 'Escape') {
            closeModal();
        }
    };
    document.addEventListener('keydown', handleEscape);
}
