/**
 * Meta Ads Library Import Modal Module
 * Handles importing media from Meta Ads Library URLs.
 */

import { importFromMetaAdsLibrary } from '/js/services/api-meta-import.js';
import { addImageToCache } from '/js/state/images-state.js';

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
                    <p class="meta-import-progress__text" id="metaImportProgressText">Scanning ads library...</p>
                    <p class="meta-import-progress__detail" id="metaImportProgressDetail"></p>
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
        
        try {
            progressText.textContent = 'Connecting to Meta Ads Library...';
            progressDetail.textContent = 'This may take a moment';
            
            const result = await importFromMetaAdsLibrary(clientId, url);
            
            // Add imported images to cache
            if (result.media && result.media.length > 0) {
                result.media.forEach(image => {
                    addImageToCache(image);
                });
            }
            
            // Show results
            progressEl.style.display = 'none';
            resultsEl.style.display = 'flex';
            
            if (result.imported > 0) {
                resultsText.textContent = `Successfully imported ${result.imported} media file${result.imported > 1 ? 's' : ''}`;
            } else {
                resultsEl.querySelector('.meta-import-results__icon').textContent = '⚠️';
                resultsText.textContent = 'No media found on this page';
            }
            
            // Update footer
            footerEl.innerHTML = `
                <button class="meta-import-modal__submit" onclick="this.closest('.meta-import-overlay').remove()">Done</button>
            `;
            
            // Notify caller
            if (onImportComplete) {
                onImportComplete(result);
            }
            
        } catch (error) {
            console.error('[MetaImportModal] Import failed:', error);
            
            progressEl.style.display = 'none';
            formEl.style.display = 'block';
            errorEl.textContent = error.message || 'Failed to import media. Please try again.';
            errorEl.style.display = 'block';
            submitBtn.disabled = false;
            submitBtn.textContent = 'Import Media';
        }
    });
    
    // Handle Enter key
    urlInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !submitBtn.disabled) {
            submitBtn.click();
        }
    });
    
    // Close on overlay click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.remove();
        }
    });
    
    // Close on Escape
    const handleEscape = (e) => {
        if (e.key === 'Escape') {
            overlay.remove();
            document.removeEventListener('keydown', handleEscape);
        }
    };
    document.addEventListener('keydown', handleEscape);
}
