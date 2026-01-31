/**
 * Meta State Management Module
 * Manages Meta/Facebook OAuth and Ads Manager state.
 */

// ==================== State ====================

let metaTokenStatus = null;
let metaAdAccounts = [];
let metaCampaigns = [];
let metaAdsets = [];
let metaPages = [];
let selectedAdAccountId = null;
let selectedCampaignId = null;
let selectedAdsetId = null;
let selectedPageId = null;

// ==================== Token Status ====================

/**
 * Get current Meta token status
 * @returns {Object|null} Token status or null
 */
export function getMetaTokenStatus() {
    return metaTokenStatus;
}

/**
 * Set Meta token status
 * @param {Object|null} status - Token status from API
 */
export function setMetaTokenStatus(status) {
    metaTokenStatus = status;
}

/**
 * Check if client is connected to Meta
 * @returns {boolean}
 */
export function isMetaConnected() {
    return metaTokenStatus?.has_token && !metaTokenStatus?.is_expired;
}

/**
 * Clear all Meta state (used when disconnecting)
 */
export function clearMetaState() {
    metaTokenStatus = null;
    metaAdAccounts = [];
    metaCampaigns = [];
    metaAdsets = [];
    metaPages = [];
    selectedAdAccountId = null;
    selectedCampaignId = null;
    selectedAdsetId = null;
    selectedPageId = null;
}

// ==================== Ad Accounts ====================

/**
 * Get cached ad accounts
 * @returns {Array} Ad accounts array
 */
export function getMetaAdAccounts() {
    return metaAdAccounts;
}

/**
 * Set ad accounts cache
 * @param {Array} accounts - Ad accounts from API
 */
export function setMetaAdAccounts(accounts) {
    metaAdAccounts = accounts || [];
}

/**
 * Get selected ad account ID
 * @returns {string|null}
 */
export function getSelectedAdAccountId() {
    return selectedAdAccountId;
}

/**
 * Set selected ad account ID
 * @param {string|null} id - Ad account ID
 */
export function setSelectedAdAccountId(id) {
    selectedAdAccountId = id;
    // Clear dependent selections when ad account changes
    selectedCampaignId = null;
    selectedAdsetId = null;
    metaCampaigns = [];
    metaAdsets = [];
}

/**
 * Get selected ad account object
 * @returns {Object|null}
 */
export function getSelectedAdAccount() {
    if (!selectedAdAccountId) return null;
    return metaAdAccounts.find(acc => acc.id === selectedAdAccountId) || null;
}

// ==================== Campaigns ====================

/**
 * Get cached campaigns
 * @returns {Array} Campaigns array
 */
export function getMetaCampaigns() {
    return metaCampaigns;
}

/**
 * Set campaigns cache
 * @param {Array} campaigns - Campaigns from API
 */
export function setMetaCampaigns(campaigns) {
    metaCampaigns = campaigns || [];
}

/**
 * Get selected campaign ID
 * @returns {string|null}
 */
export function getSelectedCampaignId() {
    return selectedCampaignId;
}

/**
 * Set selected campaign ID
 * @param {string|null} id - Campaign ID
 */
export function setSelectedCampaignId(id) {
    selectedCampaignId = id;
    // Clear dependent selections when campaign changes
    selectedAdsetId = null;
    metaAdsets = [];
}

/**
 * Get selected campaign object
 * @returns {Object|null}
 */
export function getSelectedCampaign() {
    if (!selectedCampaignId) return null;
    return metaCampaigns.find(c => c.id === selectedCampaignId) || null;
}

/**
 * Add a newly created campaign to the cache
 * @param {Object} campaign - Campaign object with id, name
 */
export function addCampaignToCache(campaign) {
    metaCampaigns = [campaign, ...metaCampaigns];
}

// ==================== AdSets ====================

/**
 * Get cached adsets
 * @returns {Array} Adsets array
 */
export function getMetaAdsets() {
    return metaAdsets;
}

/**
 * Set adsets cache
 * @param {Array} adsets - Adsets from API
 */
export function setMetaAdsets(adsets) {
    metaAdsets = adsets || [];
}

/**
 * Get selected adset ID
 * @returns {string|null}
 */
export function getSelectedAdsetId() {
    return selectedAdsetId;
}

/**
 * Set selected adset ID
 * @param {string|null} id - Adset ID
 */
export function setSelectedAdsetId(id) {
    selectedAdsetId = id;
}

/**
 * Get selected adset object
 * @returns {Object|null}
 */
export function getSelectedAdset() {
    if (!selectedAdsetId) return null;
    return metaAdsets.find(a => a.id === selectedAdsetId) || null;
}

/**
 * Add a newly created adset to the cache
 * @param {Object} adset - Adset object with id, name
 */
export function addAdsetToCache(adset) {
    metaAdsets = [adset, ...metaAdsets];
}

// ==================== Pages ====================

/**
 * Get cached Facebook pages
 * @returns {Array} Pages array
 */
export function getMetaPages() {
    return metaPages;
}

/**
 * Set pages cache
 * @param {Array} pages - Pages from API
 */
export function setMetaPages(pages) {
    metaPages = pages || [];
}

/**
 * Get selected page ID
 * @returns {string|null}
 */
export function getSelectedPageId() {
    return selectedPageId;
}

/**
 * Set selected page ID
 * @param {string|null} id - Page ID
 */
export function setSelectedPageId(id) {
    selectedPageId = id;
}

/**
 * Get selected page object
 * @returns {Object|null}
 */
export function getSelectedPage() {
    if (!selectedPageId) return null;
    return metaPages.find(p => p.id === selectedPageId) || null;
}

// ==================== Initialization ====================

/**
 * Initialize Meta state from token status
 * Sets default ad account if one is saved
 * @param {Object} tokenStatus - Token status from API
 */
export function initMetaStateFromToken(tokenStatus) {
    setMetaTokenStatus(tokenStatus);
    
    // Set default ad account if saved
    if (tokenStatus?.default_ad_account_id) {
        selectedAdAccountId = tokenStatus.default_ad_account_id;
    }
}

/**
 * Get current publish configuration
 * Returns the selected account, campaign, adset, and page
 * @returns {Object} Configuration object
 */
export function getPublishConfig() {
    return {
        adAccountId: selectedAdAccountId,
        campaignId: selectedCampaignId,
        adsetId: selectedAdsetId,
        pageId: selectedPageId,
        adAccount: getSelectedAdAccount(),
        campaign: getSelectedCampaign(),
        adset: getSelectedAdset(),
        page: getSelectedPage(),
    };
}

/**
 * Check if publish configuration is complete
 * @returns {boolean}
 */
export function isPublishConfigComplete() {
    return !!(selectedAdAccountId && selectedCampaignId && selectedAdsetId && selectedPageId);
}
