/**
 * Controller for Product Context in Settings.
 * Orchestrates loading, rendering, and user actions.
 */

import {
    getProductContextsList,
    setProductContextsList,
    getProductContextSelectedId,
    setProductContextSelectedId,
    getProductContextDirty,
    setProductContextExtractedData,
    setProductContextDirty,
    getProductContextExtractedData,
    setProductContextShowUrlInput
} from '/js/state/product-context-state.js';
import { renderProductContextCard } from '/js/renderers/product-context-renderer.js';
import { renderSettingsMarkdown } from '/js/utils/markdown.js';

/**
 * Load product contexts from API and render the card.
 */
export async function loadAndRenderProductContext() {
    const clientId = window.settingsStateGetSettingsCurrentClientId?.();
    if (!clientId) return;

    const container = document.getElementById('productContextContainer');
    if (!container) return;

    try {
        const list = await window.productContextApiFetch(clientId);
        setProductContextsList(list);
        setProductContextExtractedData(null);
        renderProductContextCard(container);
    } catch (error) {
        console.error('[Settings] Failed to load product contexts:', error);
        container.innerHTML = '<div class="product-context-error">Failed to load product contexts.</div>';
    }
}

/**
 * Create product context from PDP URL (extract via API).
 */
export function createProductContextFromUrl() {
    setProductContextShowUrlInput(true);
    const container = document.getElementById('productContextContainer');
    if (container) renderProductContextCard(container);
}

/**
 * Submit the URL from the inline input form and extract product context.
 */
export async function submitProductContextUrl() {
    const clientId = window.settingsStateGetSettingsCurrentClientId?.();
    if (!clientId) {
        window.showSettingsStatus?.('No client selected', true);
        return;
    }
    const input = document.getElementById('productContextUrlInput');
    const url = input?.value?.trim();
    if (!url) {
        window.showSettingsStatus?.('Please enter a URL', true);
        return;
    }

    setProductContextShowUrlInput(false);
    const container = document.getElementById('productContextContainer');
    if (container) container.innerHTML = '<div class="product-context-loading">Extracting product context...</div>';

    try {
        const result = await window.productContextApiExtract(clientId, url);
        setProductContextExtractedData(result);
        if (container) renderProductContextCard(container);
    } catch (error) {
        window.showSettingsStatus?.(error.message || 'Failed to extract', true);
        loadAndRenderProductContext();
    }
}

/**
 * Cancel the URL input form.
 */
export function cancelProductContextUrlInput() {
    setProductContextShowUrlInput(false);
    loadAndRenderProductContext();
}

/**
 * Add product from extracted data (persist to API).
 */
export async function addProductContextFromExtraction() {
    const clientId = window.settingsStateGetSettingsCurrentClientId?.();
    const extractedData = getProductContextExtractedData();
    if (!clientId || !extractedData) return;

    const nameInput = document.getElementById('productContextAddName');
    const textInput = document.getElementById('productContextAddText');
    const name = nameInput?.value.trim() || extractedData.name || 'Product';
    const contextText = textInput?.value.trim() ?? extractedData.context_text ?? '';

    try {
        await window.productContextApiCreate(clientId, {
            name,
            context_text: contextText,
            source_url: extractedData.source_url || null
        });
        setProductContextExtractedData(null);
        window.showSettingsStatus?.('Product context added');
        loadAndRenderProductContext();
    } catch (error) {
        window.showSettingsStatus?.(error.message || 'Failed to add', true);
    }
}

/**
 * Cancel adding product from extraction.
 */
export function cancelProductContextAdd() {
    setProductContextExtractedData(null);
    loadAndRenderProductContext();
}

/**
 * Handle product dropdown change (switch live product).
 */
export async function onProductContextDropdownChange() {
    const clientId = window.settingsStateGetSettingsCurrentClientId?.();
    const select = document.getElementById('productContextSelect');
    if (!clientId || !select) return;

    const newId = select.value;
    const prevId = getProductContextSelectedId();
    if (newId === prevId) return;

    if (getProductContextDirty() && prevId) {
        const textarea = document.getElementById('productContextText');
        if (textarea) {
            try {
                await window.productContextApiUpdate(clientId, prevId, { context_text: textarea.value.trim() });
            } catch (e) {
                console.error('[Settings] Failed to save product context:', e);
            }
        }
    }

    try {
        await window.productContextApiSetLive(clientId, newId);
        const list = await window.productContextApiFetch(clientId);
        setProductContextsList(list);
        setProductContextSelectedId(newId);
        setProductContextDirty(false);
        const container = document.getElementById('productContextContainer');
        if (container) renderProductContextCard(container);
    } catch (error) {
        window.showSettingsStatus?.(error.message || 'Failed to switch product', true);
    }
}

/**
 * Copy product context content to clipboard.
 */
export function copyProductContextContent() {
    const textarea = document.getElementById('productContextText');
    const rendered = document.getElementById('productContextRendered');
    const content = textarea?.value.trim() || rendered?.textContent.trim() || '';
    if (!content) return;

    navigator.clipboard.writeText(content).then(() => {
        const copyBtn = document.querySelector('#productContextField .settings-copy-btn');
        if (copyBtn) {
            copyBtn.classList.add('copied');
            copyBtn.title = 'Copied!';
            setTimeout(() => {
                copyBtn.classList.remove('copied');
                copyBtn.title = 'Copy to clipboard';
            }, 1500);
        }
    }).catch(err => console.error('[Settings] Failed to copy:', err));
}

/**
 * Toggle between view and edit mode for product context.
 */
export async function toggleProductContextEdit() {
    const textarea = document.getElementById('productContextText');
    const rendered = document.getElementById('productContextRendered');
    const editBtn = document.querySelector('#productContextField .settings-edit-btn:not(.settings-copy-btn)');
    if (!textarea || !rendered) return;

    const isEditing = textarea.style.display !== 'none';

    if (isEditing) {
        const content = textarea.value.trim();
        rendered.innerHTML = content ? renderSettingsMarkdown(content) : 'No content yet. Click the edit button to add.';
        rendered.classList.toggle('empty-state', !content);
        rendered.style.display = 'block';
        textarea.style.display = 'none';
        editBtn?.classList.remove('active');
        await saveProductContextCurrent();
    } else {
        rendered.style.display = 'none';
        textarea.style.display = 'block';
        textarea.focus();
        editBtn?.classList.add('active');
    }
}

/**
 * Save current product context to API.
 */
async function saveProductContextCurrent() {
    const clientId = window.settingsStateGetSettingsCurrentClientId?.();
    const textarea = document.getElementById('productContextText');
    const selectedId = getProductContextSelectedId();
    if (!clientId || !textarea || !selectedId) return;

    const id = textarea.getAttribute('data-product-id') || selectedId;
    try {
        await window.productContextApiUpdate(clientId, id, { context_text: textarea.value.trim() });
        setProductContextDirty(false);
    } catch (e) {
        console.error('[Settings] Failed to save product context:', e);
    }
}

/**
 * Delete current product context.
 */
export async function deleteCurrentProductContext() {
    const clientId = window.settingsStateGetSettingsCurrentClientId?.();
    const selectedId = getProductContextSelectedId();
    if (!clientId || !selectedId) return;
    if (!confirm('Delete this product context?')) return;

    try {
        await window.productContextApiDelete(clientId, selectedId);
        setProductContextSelectedId(null);
        window.showSettingsStatus?.('Product context deleted');
        loadAndRenderProductContext();
    } catch (error) {
        window.showSettingsStatus?.(error.message || 'Failed to delete', true);
    }
}

/**
 * Add another product (same as create from URL).
 */
export function addAnotherProductContext() {
    createProductContextFromUrl();
}

let productContextEventDelegationInitialized = false;

/**
 * Set up event delegation for Product Context container.
 * Call once when Settings section is loaded.
 */
export function initProductContextEventDelegation() {
    if (productContextEventDelegationInitialized) return;
    const container = document.getElementById('productContextContainer');
    const card = document.getElementById('productContextCard');
    if (!container || !card) return;
    productContextEventDelegationInitialized = true;

    card.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;
        const action = btn.getAttribute('data-action');
        if (!action?.startsWith('product-context-')) return;

        e.preventDefault();
        switch (action) {
            case 'product-context-create':
                createProductContextFromUrl();
                break;
            case 'product-context-add':
                addProductContextFromExtraction();
                break;
            case 'product-context-cancel':
                cancelProductContextAdd();
                break;
            case 'product-context-copy':
                copyProductContextContent();
                break;
            case 'product-context-toggle-edit':
                toggleProductContextEdit();
                break;
            case 'product-context-delete':
                deleteCurrentProductContext();
                break;
            case 'product-context-add-another':
                addAnotherProductContext();
                break;
            case 'product-context-submit-url':
                submitProductContextUrl();
                break;
            case 'product-context-cancel-url':
                cancelProductContextUrlInput();
                break;
        }
    });

    card.addEventListener('change', (e) => {
        if (e.target.id === 'productContextSelect') {
            onProductContextDropdownChange();
        }
    });

    card.addEventListener('keydown', (e) => {
        if (e.target.id === 'productContextUrlInput' && e.key === 'Enter') {
            e.preventDefault();
            submitProductContextUrl();
        }
    });
}
