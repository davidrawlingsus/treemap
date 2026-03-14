import {
    fetchShopifyStoreConnections,
    upsertShopifyStoreConnection,
    deleteShopifyStoreConnection,
    fetchShopifyRawResponses,
    fetchVocClients,
} from '/js/services/api-shopify.js';
import {
    getFounderUser,
    setFounderUser,
    getClients,
    setClients,
    getStoreConnections,
    setStoreConnections,
    getRawResponses,
    setRawResponses,
    getSelectedClientUuid,
    setSelectedClientUuid,
    getSelectedShopDomain,
    setSelectedShopDomain,
} from '/js/state/shopify-admin-state.js';
import {
    renderClientOptions,
    renderRawResponses,
    renderStatus,
    renderStoreConnections,
} from '/js/renderers/shopify-admin-renderer.js';

const elements = {
    appShell: document.getElementById('appShell'),
    founderEmail: document.getElementById('founderEmail'),
    logoutButton: document.getElementById('logoutButton'),
    statusMessage: document.getElementById('statusMessage'),
    mappingForm: document.getElementById('mappingForm'),
    shopDomainInput: document.getElementById('shopDomainInput'),
    clientSelect: document.getElementById('clientSelect'),
    statusSelect: document.getElementById('statusSelect'),
    filterClientSelect: document.getElementById('filterClientSelect'),
    filterShopDomainInput: document.getElementById('filterShopDomainInput'),
    applyFilterButton: document.getElementById('applyFilterButton'),
    refreshButton: document.getElementById('refreshButton'),
    storeConnectionsList: document.getElementById('storeConnectionsList'),
    responsesContainer: document.getElementById('responsesContainer'),
};

function showStatus(message, type = 'success') {
    renderStatus(elements.statusMessage, message, type);
}

async function loadClients() {
    const clients = await fetchVocClients();
    setClients(clients);
    renderClientOptions(elements.clientSelect, getClients(), getSelectedClientUuid());
    renderClientOptions(elements.filterClientSelect, getClients(), getSelectedClientUuid());
}

async function loadStoreConnections() {
    const connections = await fetchShopifyStoreConnections();
    setStoreConnections(connections);
    renderStoreConnections(elements.storeConnectionsList, getStoreConnections());
}

async function loadRawResponses() {
    const payload = await fetchShopifyRawResponses({
        clientUuid: getSelectedClientUuid() || undefined,
        shopDomain: getSelectedShopDomain() || undefined,
        limit: 150,
        offset: 0,
    });
    setRawResponses(payload.items || []);
    renderRawResponses(elements.responsesContainer, getRawResponses());
}

async function refreshData() {
    showStatus('Loading Shopify mappings and responses...');
    await Promise.all([loadClients(), loadStoreConnections(), loadRawResponses()]);
    showStatus();
}

async function handleMappingSubmit(event) {
    event.preventDefault();
    const shopDomain = String(elements.shopDomainInput.value || '').trim().toLowerCase();
    const clientUuid = String(elements.clientSelect.value || '').trim();
    const status = String(elements.statusSelect.value || 'active');

    if (!shopDomain) {
        showStatus('Shop domain is required.', 'error');
        return;
    }

    showStatus('Saving Shopify store mapping...');
    await upsertShopifyStoreConnection({
        shop_domain: shopDomain,
        client_uuid: clientUuid || null,
        status,
        installed_at: null,
        uninstalled_at: status === 'uninstalled' ? new Date().toISOString() : null,
    });
    elements.mappingForm.reset();
    await Promise.all([loadStoreConnections(), loadRawResponses()]);
    showStatus('Store mapping saved.');
}

async function handleDeleteConnectionClick(event) {
    const button = event.target.closest('.delete-connection-button');
    if (!button) return;
    const shopDomain = String(button.getAttribute('data-shop-domain') || '').trim();
    if (!shopDomain) return;
    if (!window.confirm(`Delete Shopify mapping for ${shopDomain}?`)) return;

    showStatus(`Deleting mapping for ${shopDomain}...`);
    await deleteShopifyStoreConnection(shopDomain);
    await Promise.all([loadStoreConnections(), loadRawResponses()]);
    showStatus('Store mapping deleted.');
}

async function handleApplyFilters() {
    setSelectedClientUuid(String(elements.filterClientSelect.value || ''));
    setSelectedShopDomain(String(elements.filterShopDomainInput.value || '').trim().toLowerCase());
    showStatus('Applying filters...');
    await loadRawResponses();
    showStatus();
}

function initializePage(userInfo) {
    setFounderUser(userInfo);
    elements.founderEmail.textContent = getFounderUser()?.email || '';
    window.Auth?.hideLogin?.();
    elements.appShell.style.display = 'flex';

    elements.mappingForm.addEventListener('submit', (event) => {
        handleMappingSubmit(event).catch((error) => {
            showStatus(error.message || 'Failed to save mapping.', 'error');
        });
    });

    elements.storeConnectionsList.addEventListener('click', (event) => {
        handleDeleteConnectionClick(event).catch((error) => {
            showStatus(error.message || 'Failed to delete mapping.', 'error');
        });
    });

    elements.applyFilterButton.addEventListener('click', () => {
        handleApplyFilters().catch((error) => {
            showStatus(error.message || 'Failed to apply filters.', 'error');
        });
    });

    elements.refreshButton.addEventListener('click', () => {
        refreshData().catch((error) => {
            showStatus(error.message || 'Failed to refresh Shopify data.', 'error');
        });
    });

    elements.logoutButton.addEventListener('click', () => window.Auth?.handleLogout?.());

    refreshData().catch((error) => {
        showStatus(error.message || 'Failed to load Shopify admin data.', 'error');
    });
}

function initializeAuth() {
    window.Auth.checkAuth().then((authenticated) => {
        if (!authenticated) return;
        const userInfo = window.Auth.getStoredUserInfo();
        if (!userInfo?.is_founder) {
            window.Auth.showLogin();
            const errorEl = document.getElementById('loginError');
            if (errorEl) {
                errorEl.textContent = 'Access denied: founder privileges required.';
                errorEl.style.display = 'block';
            }
            return;
        }
        initializePage(userInfo);
    });

    window.addEventListener('auth:authenticated', (event) => {
        const userInfo = event.detail?.user;
        if (userInfo?.is_founder) {
            initializePage(userInfo);
        }
    });
}

initializeAuth();
