/**
 * Ads Find & Replace Controller
 * UI orchestration for find & replace functionality.
 * Follows controller pattern - coordinates between UI, services, and state.
 */

import { searchAdsForText, replaceInAd, replaceAllInAds, getMatchPreview } from '/js/services/ads-find-replace.js';
import { getAdsCache, updateAdInCache } from '/js/state/ads-state.js';
import { updateFacebookAd } from '/js/services/api-facebook-ads.js';
import { escapeHtml, debounce } from '/js/utils/dom.js';

// Current search state
let currentSearchResults = [];
let currentSearchText = '';
let currentReplaceText = '';
let currentFieldsToSearch = {
    primary_text: true,
    headline: true,
    description: true,
    call_to_action: true,
    destination_url: true,
    full_json: true
};

// Debounced search function
const debouncedSearch = debounce(() => {
    performSearch();
}, 300);

/**
 * Open find & replace modal
 */
export function openAdsFindReplaceModal() {
    const overlay = document.getElementById('adsFindReplaceOverlay');
    const dialog = document.getElementById('adsFindReplaceDialog');
    
    if (!overlay || !dialog) {
        console.error('[AdsFindReplace] Modal elements not found');
        return;
    }

    // Reset state
    currentSearchResults = [];
    currentSearchText = '';
    currentReplaceText = '';
    
    // Reset UI
    const findInput = document.getElementById('adsFindReplaceFindInput');
    const replaceInput = document.getElementById('adsFindReplaceReplaceInput');
    const previewSection = document.getElementById('adsFindReplacePreviewSection');
    const errorDiv = document.getElementById('adsFindReplaceError');
    const replaceBtn = document.getElementById('adsFindReplaceReplaceBtn');
    const replaceAllBtn = document.getElementById('adsFindReplaceReplaceAllBtn');

    if (findInput) findInput.value = '';
    if (replaceInput) replaceInput.value = '';
    if (previewSection) previewSection.style.display = 'none';
    if (errorDiv) {
        errorDiv.style.display = 'none';
        errorDiv.textContent = '';
    }
    if (replaceBtn) replaceBtn.disabled = true;
    if (replaceAllBtn) replaceAllBtn.disabled = true;

    // Reset field checkboxes to all checked
    const fieldIds = [
        'adsFindReplaceFieldPrimaryText',
        'adsFindReplaceFieldHeadline',
        'adsFindReplaceFieldDescription',
        'adsFindReplaceFieldCTA',
        'adsFindReplaceFieldDestinationUrl',
        'adsFindReplaceFieldFullJson'
    ];
    
    fieldIds.forEach(fieldId => {
        const checkbox = document.getElementById(fieldId);
        if (checkbox) {
            checkbox.checked = true;
        }
    });

    currentFieldsToSearch = {
        primary_text: true,
        headline: true,
        description: true,
        call_to_action: true,
        destination_url: true,
        full_json: true
    };

    // Show modal
    overlay.classList.add('active');
    dialog.classList.add('active');

    // Focus find input
    if (findInput) {
        setTimeout(() => findInput.focus(), 100);
    }
}

/**
 * Close find & replace modal
 */
export function closeAdsFindReplaceModal() {
    const overlay = document.getElementById('adsFindReplaceOverlay');
    const dialog = document.getElementById('adsFindReplaceDialog');
    
    if (overlay) overlay.classList.remove('active');
    if (dialog) dialog.classList.remove('active');
}

/**
 * Handle search input (debounced)
 */
export function handleAdsFindReplaceSearch() {
    debouncedSearch();
}

/**
 * Perform the actual search
 */
function performSearch() {
    const findInput = document.getElementById('adsFindReplaceFindInput');
    const searchText = findInput?.value?.trim() || '';
    
    currentSearchText = searchText;

    // Get selected fields
    const fieldsToSearch = getSelectedFields();
    currentFieldsToSearch = fieldsToSearch;

    // Check if at least one field is selected
    const hasSelectedFields = Object.values(fieldsToSearch).some(v => v === true);
    if (!hasSelectedFields) {
        showError('Please select at least one field to search');
        hidePreview();
        return;
    }

    if (!searchText) {
        hidePreview();
        return;
    }

    // Perform search
    const ads = getAdsCache();
    const results = searchAdsForText(ads, searchText, fieldsToSearch);
    currentSearchResults = results;

    // Update preview
    updateMatchPreview(results, searchText);
}

/**
 * Get selected fields from checkboxes
 * @returns {Object} Fields to search object
 */
function getSelectedFields() {
    return {
        primary_text: document.getElementById('adsFindReplaceFieldPrimaryText')?.checked || false,
        headline: document.getElementById('adsFindReplaceFieldHeadline')?.checked || false,
        description: document.getElementById('adsFindReplaceFieldDescription')?.checked || false,
        call_to_action: document.getElementById('adsFindReplaceFieldCTA')?.checked || false,
        destination_url: document.getElementById('adsFindReplaceFieldDestinationUrl')?.checked || false,
        full_json: document.getElementById('adsFindReplaceFieldFullJson')?.checked || false
    };
}

/**
 * Update match preview UI
 * @param {Array} results - Search results
 * @param {string} searchText - Search text
 */
function updateMatchPreview(results, searchText) {
    const previewSection = document.getElementById('adsFindReplacePreviewSection');
    const matchCountDiv = document.getElementById('adsFindReplaceMatchCount');
    const previewContent = document.getElementById('adsFindReplacePreviewContent');
    const replaceBtn = document.getElementById('adsFindReplaceReplaceBtn');
    const replaceAllBtn = document.getElementById('adsFindReplaceReplaceAllBtn');
    const errorDiv = document.getElementById('adsFindReplaceError');

    if (!previewSection || !matchCountDiv || !previewContent) return;

    // Hide error
    if (errorDiv) {
        errorDiv.style.display = 'none';
        errorDiv.textContent = '';
    }

    if (results.length === 0) {
        previewSection.style.display = 'none';
        if (replaceBtn) replaceBtn.disabled = true;
        if (replaceAllBtn) replaceAllBtn.disabled = true;
        return;
    }

    // Calculate total matches
    const totalMatches = results.reduce((sum, result) => sum + result.totalMatchCount, 0);
    const adsWithMatches = results.length;

    // Update match count
    matchCountDiv.textContent = `Found ${totalMatches} match${totalMatches !== 1 ? 'es' : ''} in ${adsWithMatches} ad${adsWithMatches !== 1 ? 's' : ''}`;

    // Show preview items (limit to first 5 ads)
    const previewItems = results.slice(0, 5).map(result => {
        const adMatches = result.matches.slice(0, 3).map(match => {
            const preview = getMatchPreview(match.value, searchText, 80);
            return `
                <div class="ads-find-replace-preview-item">
                    <div class="ads-find-replace-preview-field">${escapeHtml(match.fieldLabel)}</div>
                    <div class="ads-find-replace-preview-text">${preview}</div>
                </div>
            `;
        }).join('');

        return adMatches;
    }).join('');

    previewContent.innerHTML = previewItems || '<div style="padding: 12px; color: rgba(55, 53, 47, 0.6);">No preview available</div>';

    // Show preview section
    previewSection.style.display = 'block';

    // Enable buttons
    if (replaceBtn) replaceBtn.disabled = false;
    if (replaceAllBtn) replaceAllBtn.disabled = false;
}

/**
 * Hide preview
 */
function hidePreview() {
    const previewSection = document.getElementById('adsFindReplacePreviewSection');
    const replaceBtn = document.getElementById('adsFindReplaceReplaceBtn');
    const replaceAllBtn = document.getElementById('adsFindReplaceReplaceAllBtn');

    if (previewSection) previewSection.style.display = 'none';
    if (replaceBtn) replaceBtn.disabled = true;
    if (replaceAllBtn) replaceAllBtn.disabled = true;
}

/**
 * Show error message
 * @param {string} message - Error message
 */
function showError(message) {
    const errorDiv = document.getElementById('adsFindReplaceError');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    }
}

/**
 * Handle replace (single match - cycles through)
 */
export async function handleAdsFindReplaceReplace() {
    if (currentSearchResults.length === 0) {
        showError('No matches to replace');
        return;
    }

    const replaceInput = document.getElementById('adsFindReplaceReplaceInput');
    const replaceText = replaceInput?.value || '';

    if (!currentSearchText) {
        showError('Please enter text to find');
        return;
    }

    // For now, replace all matches in the first ad with matches
    // In a more advanced version, we could cycle through individual matches
    const firstResult = currentSearchResults[0];
    if (!firstResult) return;

    await replaceAd(firstResult.ad, currentSearchText, replaceText, currentFieldsToSearch);

    // Re-run search to update results (use direct call, not debounced)
    performSearch();
}

/**
 * Handle replace all
 */
export async function handleAdsFindReplaceReplaceAll() {
    if (currentSearchResults.length === 0) {
        showError('No matches to replace');
        return;
    }

    const replaceInput = document.getElementById('adsFindReplaceReplaceInput');
    const replaceText = replaceInput?.value || '';

    if (!currentSearchText) {
        showError('Please enter text to find');
        return;
    }

    // Confirm before replacing all
    const totalMatches = currentSearchResults.reduce((sum, result) => sum + result.totalMatchCount, 0);
    const adsCount = currentSearchResults.length;
    
    const confirmed = confirm(
        `Replace all ${totalMatches} match${totalMatches !== 1 ? 'es' : ''} in ${adsCount} ad${adsCount !== 1 ? 's' : ''}?`
    );

    if (!confirmed) return;

    // Disable buttons during operation
    const replaceBtn = document.getElementById('adsFindReplaceReplaceBtn');
    const replaceAllBtn = document.getElementById('adsFindReplaceReplaceAllBtn');
    if (replaceBtn) replaceBtn.disabled = true;
    if (replaceAllBtn) replaceAllBtn.disabled = true;

    try {
        // Replace in all matching ads
        let successCount = 0;
        let errorCount = 0;
        const errors = [];

        for (const result of currentSearchResults) {
            try {
                await replaceAd(result.ad, currentSearchText, replaceText, currentFieldsToSearch);
                successCount++;
            } catch (error) {
                errorCount++;
                errors.push(`Ad ${result.ad.headline || result.ad.id}: ${error.message}`);
                console.error('[AdsFindReplace] Failed to replace in ad:', error);
            }
        }

        // Show result
        if (errorCount > 0) {
            showError(`Updated ${successCount} ad${successCount !== 1 ? 's' : ''}, ${errorCount} failed. ${errors.slice(0, 2).join('; ')}`);
        } else {
            // Clear error if successful
            const errorDiv = document.getElementById('adsFindReplaceError');
            if (errorDiv) {
                errorDiv.style.display = 'none';
                errorDiv.textContent = '';
            }
        }

        // Re-run search to update results (use direct call, not debounced)
        performSearch();

        // Re-render ads page
        if (window.renderAdsPage) {
            window.renderAdsPage();
        }
    } catch (error) {
        console.error('[AdsFindReplace] Replace all failed:', error);
        showError('Failed to replace: ' + error.message);
    } finally {
        // Re-enable buttons
        if (replaceBtn) replaceBtn.disabled = false;
        if (replaceAllBtn) replaceAllBtn.disabled = false;
    }
}

/**
 * Replace text in an ad and update via API
 * @param {Object} ad - Ad object
 * @param {string} searchText - Text to find
 * @param {string} replaceText - Text to replace with
 * @param {Object} fieldsToSearch - Fields to search
 */
async function replaceAd(ad, searchText, replaceText, fieldsToSearch) {
    const updatedAd = replaceInAd(ad, searchText, replaceText, fieldsToSearch);

    // Prepare update data (only include changed fields)
    const updateData = {};
    
    if (fieldsToSearch.primary_text && updatedAd.primary_text !== ad.primary_text) {
        updateData.primary_text = updatedAd.primary_text;
    }
    if (fieldsToSearch.headline && updatedAd.headline !== ad.headline) {
        updateData.headline = updatedAd.headline;
    }
    if (fieldsToSearch.description && updatedAd.description !== ad.description) {
        updateData.description = updatedAd.description;
    }
    if (fieldsToSearch.call_to_action && updatedAd.call_to_action !== ad.call_to_action) {
        updateData.call_to_action = updatedAd.call_to_action;
    }
    if (fieldsToSearch.destination_url && updatedAd.destination_url !== ad.destination_url) {
        updateData.destination_url = updatedAd.destination_url;
    }
    if (fieldsToSearch.full_json && JSON.stringify(updatedAd.full_json) !== JSON.stringify(ad.full_json)) {
        // For full_json, send the entire updated object
        // The backend should accept this via setattr
        updateData.full_json = updatedAd.full_json;
    }

    // Update via API
    if (Object.keys(updateData).length > 0) {
        try {
            await updateFacebookAd(ad.id, updateData);
            
            // Update cache
            updateAdInCache(ad.id, updateData);
        } catch (error) {
            // If full_json update fails, try without it
            if (updateData.full_json) {
                const { full_json, ...restUpdateData } = updateData;
                if (Object.keys(restUpdateData).length > 0) {
                    await updateFacebookAd(ad.id, restUpdateData);
                    updateAdInCache(ad.id, restUpdateData);
                    throw new Error('Updated other fields, but full_json update not supported by backend');
                }
            }
            throw error;
        }
    }
}