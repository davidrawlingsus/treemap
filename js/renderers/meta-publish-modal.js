/**
 * Meta Publish Modal Renderer
 * Modal dialog for publishing ads to Meta/Facebook Ads Manager.
 */

import { escapeHtml } from '/js/utils/dom.js';
import {
    checkMetaTokenStatus,
    openMetaOAuthPopup,
    disconnectMeta,
    fetchMetaAdAccounts,
    setDefaultMetaAdAccount,
    fetchMetaCampaigns,
    createMetaCampaign,
    fetchMetaAdsets,
    createMetaAdset,
    fetchMetaPages,
    fetchMetaPixels,
    publishAdToMeta,
} from '/js/services/api-meta.js';
import {
    getMetaTokenStatus,
    setMetaTokenStatus,
    isMetaConnected,
    clearMetaState,
    getMetaAdAccounts,
    setMetaAdAccounts,
    getSelectedAdAccountId,
    setSelectedAdAccountId,
    getMetaCampaigns,
    setMetaCampaigns,
    getSelectedCampaignId,
    setSelectedCampaignId,
    addCampaignToCache,
    getMetaAdsets,
    setMetaAdsets,
    getSelectedAdsetId,
    setSelectedAdsetId,
    addAdsetToCache,
    getMetaPages,
    setMetaPages,
    getSelectedPageId,
    setSelectedPageId,
    initMetaStateFromToken,
    isPublishConfigComplete,
} from '/js/state/meta-state.js';

let modalElement = null;
let currentAdId = null;
let currentClientId = null;
let cachedPixels = []; // Local cache for pixels

/**
 * Show the Meta publish modal for an ad
 * @param {string} adId - Local ad UUID
 * @param {Object} adData - Ad data for preview
 */
export async function showMetaPublishModal(adId, adData = {}) {
    currentAdId = adId;
    currentClientId = window.appStateGet?.('currentClientId') || 
                      document.getElementById('clientSelect')?.value;
    
    if (!currentClientId) {
        alert('Please select a client first');
        return;
    }
    
    // Create modal if it doesn't exist
    if (!modalElement) {
        createModalElement();
    }
    
    // Show modal with loading state
    modalElement.classList.add('active');
    renderLoadingState();
    
    try {
        // Check token status
        const tokenStatus = await checkMetaTokenStatus(currentClientId);
        initMetaStateFromToken(tokenStatus);
        
        if (!isMetaConnected()) {
            // Show connect UI
            renderConnectState();
        } else {
            // Load data and show publish UI
            await loadInitialData();
            renderPublishState(adData);
        }
    } catch (error) {
        console.error('[MetaPublishModal] Error:', error);
        renderErrorState(error.message);
    }
}

/**
 * Hide the modal
 */
export function hideMetaPublishModal() {
    if (modalElement) {
        modalElement.classList.remove('active');
    }
    currentAdId = null;
}

/**
 * Create the modal DOM element
 */
function createModalElement() {
    modalElement = document.createElement('div');
    modalElement.className = 'meta-publish-modal-overlay';
    modalElement.innerHTML = `
        <div class="meta-publish-modal">
            <div class="meta-publish-modal__header">
                <h2 class="meta-publish-modal__title">Publish to Facebook Ads</h2>
                <button class="meta-publish-modal__close" aria-label="Close">&times;</button>
            </div>
            <div class="meta-publish-modal__content">
                <!-- Content will be rendered dynamically -->
            </div>
        </div>
    `;
    
    document.body.appendChild(modalElement);
    
    // Event listeners
    modalElement.querySelector('.meta-publish-modal__close').addEventListener('click', hideMetaPublishModal);
    modalElement.addEventListener('click', (e) => {
        if (e.target === modalElement) {
            hideMetaPublishModal();
        }
    });
}

/**
 * Get the content container
 * @returns {HTMLElement}
 */
function getContentContainer() {
    return modalElement.querySelector('.meta-publish-modal__content');
}

/**
 * Render loading state
 */
function renderLoadingState() {
    const container = getContentContainer();
    container.innerHTML = `
        <div class="meta-publish-modal__loading">
            <div class="meta-publish-modal__spinner"></div>
            <p>Loading...</p>
        </div>
    `;
}

/**
 * Render error state
 * @param {string} message - Error message
 */
function renderErrorState(message) {
    const container = getContentContainer();
    container.innerHTML = `
        <div class="meta-publish-modal__error">
            <p class="meta-publish-modal__error-text">${escapeHtml(message)}</p>
            <button class="meta-publish-modal__btn meta-publish-modal__btn--secondary" onclick="window.hideMetaPublishModal()">Close</button>
        </div>
    `;
}

/**
 * Render connect to Meta state
 */
function renderConnectState() {
    const container = getContentContainer();
    const tokenStatus = getMetaTokenStatus();
    const isExpired = tokenStatus?.is_expired;
    
    container.innerHTML = `
        <div class="meta-publish-modal__connect">
            <div class="meta-publish-modal__connect-icon">
                <img src="https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/meta-icon-YwRwyV12gzJo5FDTWOXR0fOX1nb6Ch.webp" alt="Meta" width="48" height="48">
            </div>
            <h3 class="meta-publish-modal__connect-title">
                ${isExpired ? 'Meta Connection Expired' : 'Connect to Meta'}
            </h3>
            <p class="meta-publish-modal__connect-text">
                ${isExpired 
                    ? 'Your Meta connection has expired. Please reconnect to continue publishing ads.'
                    : 'Connect your Meta account to publish ads directly to Facebook Ads Manager.'}
            </p>
            <button class="meta-publish-modal__btn meta-publish-modal__btn--primary meta-publish-modal__connect-btn">
                ${isExpired ? 'Reconnect to Meta' : 'Connect to Meta'}
            </button>
        </div>
    `;
    
    container.querySelector('.meta-publish-modal__connect-btn').addEventListener('click', handleConnectClick);
}

/**
 * Handle connect button click
 */
async function handleConnectClick() {
    const container = getContentContainer();
    const btn = container.querySelector('.meta-publish-modal__connect-btn');
    
    btn.disabled = true;
    btn.textContent = 'Connecting...';
    
    try {
        await openMetaOAuthPopup(currentClientId);
        
        // Refresh token status
        const tokenStatus = await checkMetaTokenStatus(currentClientId);
        initMetaStateFromToken(tokenStatus);
        
        if (isMetaConnected()) {
            await loadInitialData();
            renderPublishState({});
        } else {
            btn.disabled = false;
            btn.textContent = 'Connect to Meta';
        }
    } catch (error) {
        console.error('[MetaPublishModal] OAuth error:', error);
        btn.disabled = false;
        btn.textContent = 'Connect to Meta';
        alert('Failed to connect: ' + error.message);
    }
}

/**
 * Load initial data (ad accounts, pages)
 */
async function loadInitialData() {
    // Load ad accounts
    const accountsResponse = await fetchMetaAdAccounts(currentClientId);
    setMetaAdAccounts(accountsResponse.items || []);
    
    // Load pages
    const pagesResponse = await fetchMetaPages(currentClientId);
    setMetaPages(pagesResponse.items || []);
    
    // Set default selections from token status
    const tokenStatus = getMetaTokenStatus();
    if (tokenStatus?.default_ad_account_id) {
        setSelectedAdAccountId(tokenStatus.default_ad_account_id);
        // Load campaigns for default account
        await loadCampaigns(tokenStatus.default_ad_account_id);
    }
    
    // Auto-select first page if only one
    const pages = getMetaPages();
    if (pages.length === 1) {
        setSelectedPageId(pages[0].id);
    }
}

/**
 * Load campaigns for an ad account
 * @param {string} adAccountId - Ad account ID
 */
async function loadCampaigns(adAccountId) {
    const response = await fetchMetaCampaigns(currentClientId, adAccountId);
    setMetaCampaigns(response.items || []);
}

/**
 * Load adsets for a campaign
 * @param {string} campaignId - Campaign ID
 */
async function loadAdsets(campaignId) {
    const response = await fetchMetaAdsets(currentClientId, campaignId);
    setMetaAdsets(response.items || []);
}

/**
 * Load pixels for the ad account and render in selector
 */
async function loadPixels() {
    const container = getContentContainer();
    const pixelSelect = container.querySelector('#newAdsetPixel');
    
    if (!pixelSelect) return;
    
    pixelSelect.innerHTML = '<option value="">Loading pixels...</option>';
    
    try {
        const response = await fetchMetaPixels(currentClientId);
        cachedPixels = response.items || [];
        
        if (cachedPixels.length === 0) {
            pixelSelect.innerHTML = '<option value="">No pixels found - create one in Meta Business Manager</option>';
        } else {
            pixelSelect.innerHTML = `
                <option value="">Select a pixel...</option>
                ${cachedPixels.map(p => `
                    <option value="${escapeHtml(p.id)}">${escapeHtml(p.name)}</option>
                `).join('')}
            `;
        }
    } catch (error) {
        console.error('[MetaPublishModal] Failed to load pixels:', error);
        pixelSelect.innerHTML = '<option value="">Failed to load pixels</option>';
    }
}

/**
 * Render the main publish state
 * @param {Object} adData - Ad data for preview
 */
function renderPublishState(adData) {
    const container = getContentContainer();
    const tokenStatus = getMetaTokenStatus();
    const adAccounts = getMetaAdAccounts();
    const campaigns = getMetaCampaigns();
    const adsets = getMetaAdsets();
    const pages = getMetaPages();
    const selectedAdAccountId = getSelectedAdAccountId();
    const selectedCampaignId = getSelectedCampaignId();
    const selectedAdsetId = getSelectedAdsetId();
    const selectedPageId = getSelectedPageId();
    
    container.innerHTML = `
        <div class="meta-publish-modal__form">
            <div class="meta-publish-modal__connected-as">
                <span class="meta-publish-modal__connected-label">Connected as:</span>
                <span class="meta-publish-modal__connected-name">${escapeHtml(tokenStatus?.meta_user_name || 'Meta User')}</span>
                <a href="#" class="meta-publish-modal__disconnect" id="disconnectMetaLink">Disconnect</a>
            </div>
            
            <div class="meta-publish-modal__section">
                <label class="meta-publish-modal__label">Ad Account</label>
                <select class="meta-publish-modal__select" id="metaAdAccountSelect">
                    <option value="">Select ad account...</option>
                    ${adAccounts.map(acc => `
                        <option value="${escapeHtml(acc.id)}" ${acc.id === selectedAdAccountId ? 'selected' : ''}>
                            ${escapeHtml(acc.name)} (${escapeHtml(acc.id)})
                        </option>
                    `).join('')}
                </select>
            </div>
            
            <div class="meta-publish-modal__section">
                <label class="meta-publish-modal__label">Facebook Page</label>
                <select class="meta-publish-modal__select" id="metaPageSelect">
                    <option value="">Select page...</option>
                    ${pages.map(page => `
                        <option value="${escapeHtml(page.id)}" ${page.id === selectedPageId ? 'selected' : ''}>
                            ${escapeHtml(page.name)}
                        </option>
                    `).join('')}
                </select>
                ${pages.length === 0 ? '<p class="meta-publish-modal__hint">No pages found. Make sure you have admin access to a Facebook page.</p>' : ''}
            </div>
            
            <div class="meta-publish-modal__section">
                <label class="meta-publish-modal__label">Campaign</label>
                <select class="meta-publish-modal__select" id="metaCampaignSelect" ${!selectedAdAccountId ? 'disabled' : ''}>
                    <option value="">Select campaign...</option>
                    <option value="__new__">+ Create New Campaign</option>
                    ${campaigns.map(c => `
                        <option value="${escapeHtml(c.id)}" ${c.id === selectedCampaignId ? 'selected' : ''}>
                            ${escapeHtml(c.name)} (${escapeHtml(c.status)})
                        </option>
                    `).join('')}
                </select>
                <div class="meta-publish-modal__create-form" id="createCampaignForm" style="display: none;">
                    <input type="text" class="meta-publish-modal__input" id="newCampaignName" placeholder="Campaign name">
                    
                    <div class="meta-publish-modal__field-group">
                        <label class="meta-publish-modal__field-label">Objective <span class="meta-publish-modal__locked-badge">locked after creation</span></label>
                        <select class="meta-publish-modal__select meta-publish-modal__select--nested" id="newCampaignObjective">
                            <option value="OUTCOME_TRAFFIC">Traffic (link clicks)</option>
                            <option value="OUTCOME_AWARENESS">Awareness (reach & impressions)</option>
                            <option value="OUTCOME_ENGAGEMENT">Engagement (likes, comments, shares)</option>
                            <option value="OUTCOME_LEADS">Leads (form submissions)</option>
                            <option value="OUTCOME_SALES">Sales (conversions & purchases)</option>
                        </select>
                    </div>
                    
                    <div class="meta-publish-modal__field-group">
                        <label class="meta-publish-modal__field-label">Special Ad Category <span class="meta-publish-modal__locked-badge">locked after creation</span></label>
                        <select class="meta-publish-modal__select meta-publish-modal__select--nested" id="newCampaignSpecialCategory">
                            <option value="">None (standard ad)</option>
                            <option value="HOUSING">Housing (real estate, rentals)</option>
                            <option value="CREDIT">Credit (loans, credit cards)</option>
                            <option value="EMPLOYMENT">Employment (job listings)</option>
                            <option value="ISSUES_ELECTIONS_POLITICS">Political / Social Issues</option>
                        </select>
                        <p class="meta-publish-modal__field-hint">Required by law for certain ad types. Limits targeting options.</p>
                    </div>
                    
                    <div class="meta-publish-modal__create-actions">
                        <button class="meta-publish-modal__btn meta-publish-modal__btn--small" id="createCampaignBtn">Create</button>
                        <button class="meta-publish-modal__btn meta-publish-modal__btn--small meta-publish-modal__btn--secondary" id="cancelCampaignBtn">Cancel</button>
                    </div>
                </div>
            </div>
            
            <div class="meta-publish-modal__section">
                <label class="meta-publish-modal__label">Ad Set</label>
                <select class="meta-publish-modal__select" id="metaAdsetSelect" ${!selectedCampaignId ? 'disabled' : ''}>
                    <option value="">Select ad set...</option>
                    <option value="__new__">+ Create New Ad Set</option>
                    ${adsets.map(a => `
                        <option value="${escapeHtml(a.id)}" ${a.id === selectedAdsetId ? 'selected' : ''}>
                            ${escapeHtml(a.name)} (${escapeHtml(a.status)})
                        </option>
                    `).join('')}
                </select>
                <div class="meta-publish-modal__create-form" id="createAdsetForm" style="display: none;">
                    <input type="text" class="meta-publish-modal__input" id="newAdsetName" placeholder="Ad set name">
                    <input type="number" class="meta-publish-modal__input" id="newAdsetBudget" placeholder="Daily budget (USD)" min="1" step="1">
                    
                    <div class="meta-publish-modal__field-group">
                        <label class="meta-publish-modal__field-label">Optimization Goal <span class="meta-publish-modal__locked-badge">locked after creation</span></label>
                        <select class="meta-publish-modal__select meta-publish-modal__select--nested" id="newAdsetOptimizationGoal">
                            <option value="LINK_CLICKS">Link Clicks</option>
                            <option value="LANDING_PAGE_VIEWS">Landing Page Views</option>
                            <option value="IMPRESSIONS">Impressions</option>
                            <option value="REACH">Reach</option>
                            <option value="POST_ENGAGEMENT">Post Engagement</option>
                            <option value="THRUPLAY">ThruPlay (video views)</option>
                            <option value="LEAD_GENERATION">Lead Generation</option>
                            <option value="OFFSITE_CONVERSIONS">Conversions</option>
                        </select>
                    </div>
                    
                    <div class="meta-publish-modal__field-group" id="pixelSelectorGroup" style="display: none;">
                        <label class="meta-publish-modal__field-label">Facebook Pixel <span class="meta-publish-modal__locked-badge">required for conversions</span></label>
                        <select class="meta-publish-modal__select meta-publish-modal__select--nested" id="newAdsetPixel">
                            <option value="">Loading pixels...</option>
                        </select>
                        <p class="meta-publish-modal__field-hint">Select the pixel to track conversions from your website.</p>
                    </div>
                    
                    <div class="meta-publish-modal__field-group">
                        <label class="meta-publish-modal__field-label">Billing Event <span class="meta-publish-modal__locked-badge">locked after creation</span></label>
                        <select class="meta-publish-modal__select meta-publish-modal__select--nested" id="newAdsetBillingEvent">
                            <option value="IMPRESSIONS">Impressions (CPM)</option>
                            <option value="LINK_CLICKS">Link Clicks (CPC)</option>
                            <option value="THRUPLAY">ThruPlay (video)</option>
                        </select>
                        <p class="meta-publish-modal__field-hint">How you'll be charged. Most ads use Impressions.</p>
                    </div>
                    
                    <div class="meta-publish-modal__create-actions">
                        <button class="meta-publish-modal__btn meta-publish-modal__btn--small" id="createAdsetBtn">Create</button>
                        <button class="meta-publish-modal__btn meta-publish-modal__btn--small meta-publish-modal__btn--secondary" id="cancelAdsetBtn">Cancel</button>
                    </div>
                </div>
            </div>
            
            <div class="meta-publish-modal__actions">
                <button class="meta-publish-modal__btn meta-publish-modal__btn--secondary" id="cancelPublishBtn">Cancel</button>
                <button class="meta-publish-modal__btn meta-publish-modal__btn--primary" id="publishBtn" ${!isPublishConfigComplete() ? 'disabled' : ''}>
                    Publish to Facebook
                </button>
            </div>
        </div>
    `;
    
    // Attach event listeners
    attachFormListeners();
}

/**
 * Attach event listeners to the form
 */
function attachFormListeners() {
    const container = getContentContainer();
    
    // Disconnect link
    const disconnectLink = container.querySelector('#disconnectMetaLink');
    disconnectLink?.addEventListener('click', async (e) => {
        e.preventDefault();
        if (confirm('Disconnect from Meta? You will need to reconnect to publish ads.')) {
            try {
                await disconnectMeta(currentClientId);
                clearMetaState();
                renderConnectState();
            } catch (error) {
                console.error('[MetaPublishModal] Disconnect error:', error);
                alert('Failed to disconnect: ' + error.message);
            }
        }
    });
    
    // Ad account select
    const adAccountSelect = container.querySelector('#metaAdAccountSelect');
    adAccountSelect?.addEventListener('change', async (e) => {
        const adAccountId = e.target.value;
        setSelectedAdAccountId(adAccountId || null);
        
        if (adAccountId) {
            // Save as default
            const account = getMetaAdAccounts().find(a => a.id === adAccountId);
            await setDefaultMetaAdAccount(currentClientId, adAccountId, account?.name);
            
            // Load campaigns
            renderLoadingInSelect('#metaCampaignSelect');
            await loadCampaigns(adAccountId);
        }
        
        updateFormState();
    });
    
    // Page select
    const pageSelect = container.querySelector('#metaPageSelect');
    pageSelect?.addEventListener('change', (e) => {
        setSelectedPageId(e.target.value || null);
        updatePublishButton();
    });
    
    // Campaign select
    const campaignSelect = container.querySelector('#metaCampaignSelect');
    campaignSelect?.addEventListener('change', async (e) => {
        const value = e.target.value;
        
        if (value === '__new__') {
            container.querySelector('#createCampaignForm').style.display = 'block';
            setSelectedCampaignId(null);
        } else {
            container.querySelector('#createCampaignForm').style.display = 'none';
            setSelectedCampaignId(value || null);
            
            if (value) {
                renderLoadingInSelect('#metaAdsetSelect');
                await loadAdsets(value);
            }
        }
        
        updateFormState();
    });
    
    // Adset select
    const adsetSelect = container.querySelector('#metaAdsetSelect');
    adsetSelect?.addEventListener('change', (e) => {
        const value = e.target.value;
        
        if (value === '__new__') {
            container.querySelector('#createAdsetForm').style.display = 'block';
            setSelectedAdsetId(null);
        } else {
            container.querySelector('#createAdsetForm').style.display = 'none';
            setSelectedAdsetId(value || null);
        }
        
        updatePublishButton();
    });
    
    // Create campaign button
    container.querySelector('#createCampaignBtn')?.addEventListener('click', handleCreateCampaign);
    container.querySelector('#cancelCampaignBtn')?.addEventListener('click', () => {
        container.querySelector('#createCampaignForm').style.display = 'none';
        container.querySelector('#metaCampaignSelect').value = '';
        // Reset form fields to defaults
        container.querySelector('#newCampaignName').value = '';
        container.querySelector('#newCampaignObjective').value = 'OUTCOME_TRAFFIC';
        container.querySelector('#newCampaignSpecialCategory').value = '';
    });
    
    // Create adset button
    container.querySelector('#createAdsetBtn')?.addEventListener('click', handleCreateAdset);
    container.querySelector('#cancelAdsetBtn')?.addEventListener('click', () => {
        container.querySelector('#createAdsetForm').style.display = 'none';
        container.querySelector('#metaAdsetSelect').value = '';
        // Reset form fields to defaults
        container.querySelector('#newAdsetName').value = '';
        container.querySelector('#newAdsetBudget').value = '';
        container.querySelector('#newAdsetOptimizationGoal').value = 'LINK_CLICKS';
        container.querySelector('#newAdsetBillingEvent').value = 'IMPRESSIONS';
        container.querySelector('#pixelSelectorGroup').style.display = 'none';
    });
    
    // Optimization goal change - show/hide pixel selector
    container.querySelector('#newAdsetOptimizationGoal')?.addEventListener('change', async (e) => {
        const pixelGroup = container.querySelector('#pixelSelectorGroup');
        if (e.target.value === 'OFFSITE_CONVERSIONS') {
            pixelGroup.style.display = 'block';
            await loadPixels();
        } else {
            pixelGroup.style.display = 'none';
        }
    });
    
    // Cancel button
    container.querySelector('#cancelPublishBtn')?.addEventListener('click', hideMetaPublishModal);
    
    // Publish button
    container.querySelector('#publishBtn')?.addEventListener('click', handlePublish);
}

/**
 * Show loading indicator in a select
 * @param {string} selector - Select element selector
 */
function renderLoadingInSelect(selector) {
    const container = getContentContainer();
    const select = container.querySelector(selector);
    if (select) {
        select.innerHTML = '<option value="">Loading...</option>';
        select.disabled = true;
    }
}

/**
 * Update form state after selection changes
 */
function updateFormState() {
    const container = getContentContainer();
    const campaigns = getMetaCampaigns();
    const adsets = getMetaAdsets();
    const selectedAdAccountId = getSelectedAdAccountId();
    const selectedCampaignId = getSelectedCampaignId();
    
    // Update campaign select
    const campaignSelect = container.querySelector('#metaCampaignSelect');
    if (campaignSelect) {
        campaignSelect.disabled = !selectedAdAccountId;
        campaignSelect.innerHTML = `
            <option value="">Select campaign...</option>
            <option value="__new__">+ Create New Campaign</option>
            ${campaigns.map(c => `
                <option value="${escapeHtml(c.id)}" ${c.id === selectedCampaignId ? 'selected' : ''}>
                    ${escapeHtml(c.name)} (${escapeHtml(c.status)})
                </option>
            `).join('')}
        `;
    }
    
    // Update adset select
    const adsetSelect = container.querySelector('#metaAdsetSelect');
    const selectedAdsetId = getSelectedAdsetId();
    if (adsetSelect) {
        adsetSelect.disabled = !selectedCampaignId;
        adsetSelect.innerHTML = `
            <option value="">Select ad set...</option>
            <option value="__new__">+ Create New Ad Set</option>
            ${adsets.map(a => `
                <option value="${escapeHtml(a.id)}" ${a.id === selectedAdsetId ? 'selected' : ''}>
                    ${escapeHtml(a.name)} (${escapeHtml(a.status)})
                </option>
            `).join('')}
        `;
    }
    
    updatePublishButton();
}

/**
 * Update publish button state
 */
function updatePublishButton() {
    const container = getContentContainer();
    const publishBtn = container.querySelector('#publishBtn');
    if (publishBtn) {
        publishBtn.disabled = !isPublishConfigComplete();
    }
}

/**
 * Handle create campaign
 */
async function handleCreateCampaign() {
    const container = getContentContainer();
    const nameInput = container.querySelector('#newCampaignName');
    const objectiveSelect = container.querySelector('#newCampaignObjective');
    const specialCategorySelect = container.querySelector('#newCampaignSpecialCategory');
    
    const name = nameInput?.value?.trim();
    const objective = objectiveSelect?.value || 'OUTCOME_TRAFFIC';
    const specialCategory = specialCategorySelect?.value || '';
    
    if (!name) {
        alert('Please enter a campaign name');
        return;
    }
    
    const btn = container.querySelector('#createCampaignBtn');
    btn.disabled = true;
    btn.textContent = 'Creating...';
    
    try {
        const campaignData = {
            ad_account_id: getSelectedAdAccountId(),
            name: name,
            objective: objective,
            status: 'PAUSED',
        };
        
        // Only include special_ad_categories if one is selected
        if (specialCategory) {
            campaignData.special_ad_categories = [specialCategory];
        }
        
        const result = await createMetaCampaign(currentClientId, campaignData);
        
        // Add to cache and select
        addCampaignToCache({ id: result.id, name: result.name, status: 'PAUSED' });
        setSelectedCampaignId(result.id);
        
        // Hide form and reset fields
        container.querySelector('#createCampaignForm').style.display = 'none';
        nameInput.value = '';
        objectiveSelect.value = 'OUTCOME_TRAFFIC';
        specialCategorySelect.value = '';
        
        // Load adsets for new campaign (will be empty)
        await loadAdsets(result.id);
        updateFormState();
        
    } catch (error) {
        console.error('[MetaPublishModal] Create campaign error:', error);
        alert('Failed to create campaign: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Create';
    }
}

/**
 * Handle create adset
 */
async function handleCreateAdset() {
    const container = getContentContainer();
    const nameInput = container.querySelector('#newAdsetName');
    const budgetInput = container.querySelector('#newAdsetBudget');
    const optimizationGoalSelect = container.querySelector('#newAdsetOptimizationGoal');
    const billingEventSelect = container.querySelector('#newAdsetBillingEvent');
    const pixelSelect = container.querySelector('#newAdsetPixel');
    
    const name = nameInput?.value?.trim();
    const budgetUsd = parseFloat(budgetInput?.value) || 0;
    const optimizationGoal = optimizationGoalSelect?.value || 'LINK_CLICKS';
    const billingEvent = billingEventSelect?.value || 'IMPRESSIONS';
    const pixelId = pixelSelect?.value || null;
    
    if (!name) {
        alert('Please enter an ad set name');
        return;
    }
    
    if (budgetUsd < 1) {
        alert('Please enter a daily budget of at least $1');
        return;
    }
    
    // Validate pixel is selected for conversion optimization
    if (optimizationGoal === 'OFFSITE_CONVERSIONS' && !pixelId) {
        alert('Please select a Facebook Pixel for conversion optimization');
        return;
    }
    
    const btn = container.querySelector('#createAdsetBtn');
    btn.disabled = true;
    btn.textContent = 'Creating...';
    
    try {
        const adsetData = {
            campaign_id: getSelectedCampaignId(),
            name: name,
            daily_budget: Math.round(budgetUsd * 100), // Convert to cents
            billing_event: billingEvent,
            optimization_goal: optimizationGoal,
            status: 'PAUSED',
        };
        
        // Add promoted_object for optimization goals that require it
        if (optimizationGoal === 'OFFSITE_CONVERSIONS' && pixelId) {
            adsetData.promoted_object = {
                pixel_id: pixelId,
                custom_event_type: 'PURCHASE', // Default to PURCHASE, could make configurable
            };
        }
        
        const result = await createMetaAdset(currentClientId, adsetData);
        
        // Add to cache and select
        addAdsetToCache({ id: result.id, name: result.name, status: 'PAUSED' });
        setSelectedAdsetId(result.id);
        
        // Hide form and reset fields
        container.querySelector('#createAdsetForm').style.display = 'none';
        container.querySelector('#pixelSelectorGroup').style.display = 'none';
        nameInput.value = '';
        budgetInput.value = '';
        optimizationGoalSelect.value = 'LINK_CLICKS';
        billingEventSelect.value = 'IMPRESSIONS';
        if (pixelSelect) pixelSelect.value = '';
        
        updateFormState();
        
    } catch (error) {
        console.error('[MetaPublishModal] Create adset error:', error);
        alert('Failed to create ad set: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Create';
    }
}

/**
 * Handle publish button click
 */
async function handlePublish() {
    const container = getContentContainer();
    const btn = container.querySelector('#publishBtn');
    
    btn.disabled = true;
    btn.textContent = 'Publishing...';
    
    try {
        const result = await publishAdToMeta(
            currentClientId,
            currentAdId,
            getSelectedAdsetId(),
            getSelectedAdAccountId(),
            getSelectedPageId()
        );
        
        if (result.success) {
            alert(`Ad published successfully!\nMeta Ad ID: ${result.meta_ad_id}`);
            hideMetaPublishModal();
            
            // Refresh ads page if available
            if (window.renderAdsPage) {
                window.renderAdsPage();
            }
        } else {
            throw new Error(result.error || 'Publishing failed');
        }
        
    } catch (error) {
        console.error('[MetaPublishModal] Publish error:', error);
        alert('Failed to publish ad: ' + error.message);
        btn.disabled = false;
        btn.textContent = 'Publish to Facebook';
    }
}

// Expose globally for inline event handlers
window.hideMetaPublishModal = hideMetaPublishModal;
