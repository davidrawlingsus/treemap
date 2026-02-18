/**
 * Renders the Product Context card in Settings.
 */

import { escapeHtml, escapeHtmlForAttribute } from '/js/utils/dom.js';
import { renderSettingsMarkdown } from '/js/utils/markdown.js';
import {
    getProductContextsList,
    getProductContextSelectedId,
    setProductContextSelectedId,
    getProductContextExtractedData,
    getProductContextShowUrlInput,
    setProductContextDirty
} from '/js/state/product-context-state.js';

/**
 * Render the Product Context card content into the container.
 * @param {HTMLElement} container - The productContextContainer element
 */
export function renderProductContextCard(container) {
    if (!container) return;

    const clientId = window.settingsStateGetSettingsCurrentClientId?.();
    if (!clientId) return;

    const productContextsList = getProductContextsList();
    const extractedData = getProductContextExtractedData();
    const showUrlInput = getProductContextShowUrlInput();

    if (extractedData) {
        container.innerHTML = renderAddFormHtml(extractedData);
        return;
    }

    if (showUrlInput) {
        container.innerHTML = renderUrlInputHtml();
        const input = container.querySelector('#productContextUrlInput');
        if (input) input.focus();
        return;
    }

    if (!productContextsList || productContextsList.length === 0) {
        container.innerHTML = renderEmptyStateHtml();
        return;
    }

    const liveProduct = productContextsList.find(p => p.is_live) || productContextsList[0];
    const selectedId = getProductContextSelectedId() || liveProduct.id;
    const selected = productContextsList.find(p => p.id === selectedId) || productContextsList[0];
    setProductContextSelectedId(selected.id);

    container.innerHTML = renderProductListHtml(productContextsList, selected);

    const rendered = container.querySelector('#productContextRendered');
    const textarea = container.querySelector('#productContextText');
    if (textarea && rendered) {
        textarea.value = selected.context_text || '';
        const content = (selected.context_text || '').trim();
        if (content) {
            rendered.innerHTML = renderSettingsMarkdown(content);
            rendered.classList.remove('empty-state');
            rendered.style.display = 'block';
            textarea.style.display = 'none';
        } else {
            rendered.innerHTML = 'No content yet. Click the edit button to add.';
            rendered.classList.add('empty-state');
            rendered.style.display = 'block';
            textarea.style.display = 'none';
        }
    }
    setProductContextDirty(false);

    const textareaEl = container.querySelector('#productContextText');
    if (textareaEl) {
        textareaEl.addEventListener('input', () => setProductContextDirty(true));
    }
}

function renderAddFormHtml(extractedData) {
    return `
        <div class="product-context-add-form">
            <div class="settings-field">
                <label for="productContextAddName">Product name</label>
                <input type="text" id="productContextAddName" value="${escapeHtml(extractedData.name)}" placeholder="Product name" />
            </div>
            <div class="settings-field settings-field--toggleable" id="productContextAddField">
                <div class="settings-field-header">
                    <label>Extracted context</label>
                </div>
                <textarea id="productContextAddText" rows="8">${escapeHtml(extractedData.context_text)}</textarea>
            </div>
            <div class="product-context-add-actions">
                <button type="button" class="settings-save-btn" data-action="product-context-add">Save product context</button>
                <button type="button" class="settings-cancel-btn" data-action="product-context-cancel">Discard</button>
            </div>
        </div>
    `;
}

function renderEmptyStateHtml() {
    return `
        <div class="product-context-empty">
            <button type="button" class="settings-save-btn" data-action="product-context-create">Create product context</button>
        </div>
    `;
}

function renderUrlInputHtml() {
    return `
        <div class="product-context-url-form">
            <div class="settings-field">
                <label for="productContextUrlInput">Product page URL</label>
                <input type="url" id="productContextUrlInput" placeholder="https://example.com/products/my-product" />
            </div>
            <div class="product-context-add-actions">
                <button type="button" class="settings-save-btn" data-action="product-context-submit-url">Extract context</button>
                <button type="button" class="settings-cancel-btn" data-action="product-context-cancel-url">Cancel</button>
            </div>
        </div>
    `;
}

function renderProductListHtml(list, selected) {
    const dropdownOptions = list.map(p =>
        `<option value="${p.id}" ${p.id === selected.id ? 'selected' : ''}>${escapeHtml(p.name)}</option>`
    ).join('');
    const sourceUrlHtml = selected.source_url
        ? `<p class="product-context-source-url">Source: <a href="${escapeHtmlForAttribute(selected.source_url)}" target="_blank" rel="noopener">${escapeHtml(selected.source_url)}</a></p>`
        : '';
    const dropdownHtml = list.length > 1
        ? `
            <div class="product-context-select-row">
                <label for="productContextSelect">Live product</label>
                <select id="productContextSelect" class="product-context-select">${dropdownOptions}</select>
            </div>
        `
        : `<div class="product-context-select-row"><span class="product-context-single-name">${escapeHtml(selected.name)}</span></div>`;

    return `
        ${dropdownHtml}
        <div class="settings-field settings-field--toggleable" id="productContextField">
            <div class="settings-field-header">
                <label for="productContextText">Product Context</label>
                <div class="settings-field-actions">
                    <button type="button" class="settings-copy-btn" data-action="product-context-copy" title="Copy to clipboard">
                        <img src="/images/copy_button.png" alt="Copy" width="14" height="14">
                    </button>
                    <button type="button" class="settings-edit-btn" data-action="product-context-toggle-edit" title="Edit">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                        </svg>
                    </button>
                </div>
            </div>
            <div class="settings-rendered-view" id="productContextRendered"></div>
            <textarea id="productContextText" rows="6" style="display: none;" data-product-id="${selected.id}"></textarea>
        </div>
        ${sourceUrlHtml}
        <div class="product-context-actions">
            <button type="button" class="settings-delete-btn" data-action="product-context-delete">Delete this product</button>
            <button type="button" class="settings-secondary-btn" data-action="product-context-add-another">Add another product</button>
        </div>
    `;
}
