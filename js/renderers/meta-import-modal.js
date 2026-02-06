/**
 * Meta Ads Library Import Modal Module
 * Handles importing media from Meta Ads Library URLs using background jobs.
 */

import { 
    startMetaImportJob, 
    getImportJobStatus, 
    getImportJobImages 
} from '/js/services/api-meta-import.js';
import { addImageToCache, getImagesCache } from '/js/state/images-state.js';

// Store active polling intervals
let activePollingInterval = null;
let lastImageTimestamp = null;

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
 * Stop any active polling
 */
function stopPolling() {
    if (activePollingInterval) {
        clearInterval(activePollingInterval);
        activePollingInterval = null;
    }
}

/**
 * Append a new image to the masonry grid in real-time
 * @param {Object} image - Image data
 */
function appendImageToGrid(image) {
    // Use existing appendImageToGrid if available, otherwise use renderImages
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
    
    // Stop any existing polling
    stopPolling();
    
    // Create modal overlay
    const overlay = document.createElement('div');
    overlay.className = 'meta-import-overlay';
    overlay.innerHTML = `
        <div class="meta-import-modal">
            <div class="meta-import-modal__header">
                <h2>Import from Meta Ads Library</h2>
                <button class="meta-import-modal__close" onclick="this.closest('.meta-import-overlay').remove()">×</button>
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
                <button class="meta-import-modal__cancel" onclick="this.closest('.meta-import-overlay').remove()">Cancel</button>
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
    
    // Focus input
    urlInput.focus();
    
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
    
    // Track images we've already added to avoid duplicates
    const addedImageIds = new Set();
    
    /**
     * Poll for job status and new images
     */
    async function pollJobStatus(jobId) {
        try {
            const statusResponse = await getImportJobStatus(jobId);
            const job = statusResponse.job;
            
            // Update progress display
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
            }
            
            // Add any new images to the grid in real-time
            if (statusResponse.recent_images && statusResponse.recent_images.length > 0) {
                for (const image of statusResponse.recent_images) {
                    if (!addedImageIds.has(image.id)) {
                        addedImageIds.add(image.id);
                        appendImageToGrid(image);
                    }
                }
            }
            
            // Check if complete
            if (job.status === 'complete' || job.status === 'failed') {
                stopPolling();
                
                // Ensure we have all images
                const allImages = await getImportJobImages(jobId);
                for (const image of allImages.items || []) {
                    if (!addedImageIds.has(image.id)) {
                        addedImageIds.add(image.id);
                        appendImageToGrid(image);
                    }
                }
                
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
                    <button class="meta-import-modal__submit" onclick="this.closest('.meta-import-overlay').remove()">Done</button>
                `;
                
                // Notify caller
                if (onImportComplete) {
                    onImportComplete({
                        imported: job.total_imported,
                        total_found: job.total_found,
                        status: job.status,
                    });
                }
            }
            
        } catch (error) {
            console.error('[MetaImportModal] Polling error:', error);
            // Don't stop polling on transient errors
        }
    }
    
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
            <button class="meta-import-modal__cancel" onclick="this.closest('.meta-import-overlay').remove()">Close</button>
        `;
        
        try {
            progressText.textContent = 'Starting import job...';
            progressDetail.textContent = '';
            
            // Start the import job
            const job = await startMetaImportJob(clientId, url);
            
            if (!job || !job.id) {
                throw new Error('Failed to create import job');
            }
            
            console.log('[MetaImportModal] Import job started:', job.id);
            
            // Start polling for status
            lastImageTimestamp = null;
            activePollingInterval = setInterval(() => pollJobStatus(job.id), 2000);
            
            // Do initial poll immediately
            await pollJobStatus(job.id);
            
        } catch (error) {
            console.error('[MetaImportModal] Import failed:', error);
            
            stopPolling();
            progressEl.style.display = 'none';
            formEl.style.display = 'block';
            errorEl.textContent = error.message || 'Failed to start import. Please try again.';
            errorEl.style.display = 'block';
            submitBtn.disabled = false;
            submitBtn.textContent = 'Import Media';
            
            footerEl.innerHTML = `
                <button class="meta-import-modal__cancel" onclick="this.closest('.meta-import-overlay').remove()">Cancel</button>
                <button class="meta-import-modal__submit" id="metaImportSubmit">Import Media</button>
            `;
        }
    });
    
    // Handle Enter key
    urlInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !submitBtn.disabled) {
            submitBtn.click();
        }
    });
    
    // Clean up on close
    const cleanup = () => {
        stopPolling();
    };
    
    // Close on overlay click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            cleanup();
            overlay.remove();
        }
    });
    
    // Handle close button clicks
    overlay.addEventListener('click', (e) => {
        if (e.target.classList.contains('meta-import-modal__close') ||
            e.target.classList.contains('meta-import-modal__cancel')) {
            cleanup();
        }
    });
    
    // Close on Escape
    const handleEscape = (e) => {
        if (e.key === 'Escape') {
            cleanup();
            overlay.remove();
            document.removeEventListener('keydown', handleEscape);
        }
    };
    document.addEventListener('keydown', handleEscape);
}
