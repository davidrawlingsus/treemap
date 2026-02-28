/**
 * FB Connector media picker renderer.
 * Renders the FB Connector tab content: connect prompt or thumbnail grid with selection.
 * No API calls; parent passes data and callbacks. Uses event delegation.
 */
import { escapeHtml } from '/js/utils/dom.js';

/**
 * Render the FB Connector picker into the container.
 * @param {HTMLElement} container - Container element
 * @param {Object} options - Options
 * @param {boolean} options.connected - Whether Meta is connected
 * @param {string} [options.accountName] - Meta user name (for display)
 * @param {string} [options.adAccountName] - Default ad account name (for display)
 * @param {Array<{type: string, id?: string, name?: string, thumbnail_url?: string, original_url?: string, source?: string}>} options.items - Media items from API
 * @param {Set<string>} options.selectedIds - Set of selected item ids (type + id)
 * @param {boolean} [options.loading] - Show loading spinner
 * @param {boolean} [options.importing] - Show import in progress
 * @param {Object} [options.paging] - { after, image_after, video_after, hasMore }
 * @param {Function} options.onConnect - Called when user clicks Connect to Meta
 * @param {Function} options.onLoadMore - Called when user clicks Load More (receives full paging object)
 * @param {Function} options.onImport - Called with array of selected items to import (may be triggered from footer)
 * @param {Function} options.onToggleSelection - Called with item key (type:id) when card is toggled
 * @param {Function} options.onSelectAll - Select all visible items
 * @param {Function} options.onDeselectAll - Deselect all
 * @param {Object} [options.loadAllProgress] - When Load All is running: { loaded: number, total: number|null }
 * @param {string} [options.loadError] - Error message when initial/media load failed (e.g. rate limit)
 * @param {boolean} [options.loadAllPaused] - True when Load All was paused (e.g. rate limit); show Resume
 * @param {Function} [options.onRetryLoad] - Called when user clicks Try again after a load error
 * @param {Function} [options.onResumeLoadAll] - Called when user clicks Resume after Load All paused
 * @param {Object} [options.importProgress] - When Import all is running: { imported, failed } for progress text
 * @param {Function} [options.onError] - Called with error message
 */
export function renderFbConnectorPicker(container, options) {
    const {
        connected = false,
        accountName = '',
        adAccountName = '',
        items = [],
        selectedIds = new Set(),
        loading = false,
        importing = false,
        paging = {},
        loadAllProgress = null,
        loadError = null,
        loadAllPaused = false,
        importProgress = null,
        onRetryLoad,
        onResumeLoadAll,
        onConnect,
        onLoadMore,
        onImport,
        onToggleSelection,
        onSelectAll,
        onDeselectAll,
    } = options;

    container.innerHTML = '';
    container.className = 'fb-connector-picker';

    if (!connected) {
        const notConnected = document.createElement('div');
        notConnected.className = 'fb-connector-not-connected';
        notConnected.innerHTML = `
            <p class="fb-connector-not-connected__message">Connect your Facebook ad account to import full-resolution images and videos from your media library.</p>
            <button type="button" class="fb-connector-connect-btn">Connect to Meta</button>
        `;
        const btn = notConnected.querySelector('.fb-connector-connect-btn');
        if (btn && typeof onConnect === 'function') {
            btn.addEventListener('click', () => onConnect());
        }
        container.appendChild(notConnected);
        return;
    }

    const header = document.createElement('div');
    header.className = 'fb-connector-header';
    header.innerHTML = `
        <p class="fb-connector-header__account">${escapeHtml(accountName || 'Meta account')}${adAccountName ? ` · ${escapeHtml(adAccountName)}` : ''}</p>
    `;
    container.appendChild(header);

    if (loadError) {
        const errorBanner = document.createElement('div');
        errorBanner.className = 'fb-connector-load-error';
        const actionLabel = loadAllPaused ? 'Resume' : 'Try again';
        errorBanner.innerHTML = `
            <p class="fb-connector-load-error__message">${escapeHtml(loadError)}</p>
            <button type="button" class="fb-connector-load-error__retry" data-action="${loadAllPaused ? 'resume' : 'retry'}">${escapeHtml(actionLabel)}</button>
        `;
        const actionBtn = errorBanner.querySelector('.fb-connector-load-error__retry');
        if (actionBtn) {
            if (loadAllPaused && typeof onResumeLoadAll === 'function') {
                actionBtn.addEventListener('click', () => onResumeLoadAll());
            } else if (!loadAllPaused && typeof onRetryLoad === 'function') {
                actionBtn.addEventListener('click', () => onRetryLoad());
            }
        }
        container.appendChild(errorBanner);
    }

    const selectedCount = items.filter((it) => selectedIds.has(itemKey(it))).length;
    const allSelected = items.length > 0 && selectedCount === items.length;
    const showSelectToggle = items.length > 0 && selectedCount > 0;
    const actionsRow = document.createElement('div');
    actionsRow.className = 'fb-connector-actions';
    actionsRow.innerHTML = `
        ${showSelectToggle ? `<button type="button" class="fb-connector-action-btn fb-connector-select-toggle" data-action="select-deselect">${allSelected ? 'Deselect all' : 'Select all'}</button>` : ''}
    `;
    if (actionsRow.innerHTML.trim()) container.appendChild(actionsRow);

    const gridWrap = document.createElement('div');
    gridWrap.className = 'fb-connector-grid-wrap';
    if (loading) {
        const loadingEl = document.createElement('div');
        loadingEl.className = 'fb-connector-loading';
        if (loadAllProgress && loadAllProgress.loaded >= 0) {
            const loaded = loadAllProgress.loaded;
            const total = loadAllProgress.total;
            const label = total != null
                ? `Loading… ${loaded} of ${total} items`
                : `Loading… ${loaded} items`;
            const pct = total != null && total > 0 ? Math.min(100, (loaded / total) * 100) : 0;
            loadingEl.style.setProperty('--progress-pct', String(pct));
            loadingEl.innerHTML = `
                <span class="fb-connector-loading__text">${escapeHtml(label)}</span>
                <div class="fb-connector-loading__bar-wrap">
                    <div class="fb-connector-loading__bar"></div>
                </div>
            `;
        } else {
            loadingEl.textContent = 'Loading media…';
        }
        gridWrap.appendChild(loadingEl);
    } else {
        const grid = document.createElement('div');
        grid.className = 'fb-connector-grid';
        grid.setAttribute('role', 'list');
        items.forEach((item) => {
            const key = itemKey(item);
            const isSelected = selectedIds.has(key);
            const card = document.createElement('div');
            card.className = `fb-connector-card fb-connector-card--${item.type}${isSelected ? ' fb-connector-card--selected' : ''}`;
            card.dataset.itemKey = key;
            card.setAttribute('role', 'listitem');
            const thumb = item.thumbnail_url || item.original_url || item.source || '';
            const name = item.name || item.id || (item.type === 'image' ? 'Image' : 'Video');
            card.innerHTML = `
                <div class="fb-connector-card__thumb">
                    ${item.type === 'video' && thumb
                        ? `<img src="${escapeHtmlForAttribute(thumb)}" alt="" loading="lazy" />`
                        : thumb
                            ? `<img src="${escapeHtmlForAttribute(thumb)}" alt="" loading="lazy" />`
                            : '<span class="fb-connector-card__placeholder">No preview</span>'}
                    <label class="fb-connector-card__checkbox" data-item-key="${escapeHtmlForAttribute(key)}">
                        <input type="checkbox" ${isSelected ? 'checked' : ''}>
                        <span class="fb-connector-card__checkbox-mark"></span>
                    </label>
                </div>
                <div class="fb-connector-card__name">${escapeHtml(String(name).slice(0, 40))}${String(name).length > 40 ? '…' : ''}</div>
            `;
            grid.appendChild(card);
        });
        gridWrap.appendChild(grid);
    }
    container.appendChild(gridWrap);

    if (!loading && items.length > 0 && paging.hasMore) {
        const paginationRow = document.createElement('div');
        paginationRow.className = 'fb-connector-pagination';
        const loadMore = document.createElement('button');
        loadMore.type = 'button';
        loadMore.className = 'fb-connector-load-more';
        loadMore.textContent = 'Load More';
        loadMore.addEventListener('click', () => {
            if (typeof onLoadMore === 'function') onLoadMore(paging);
        });
        paginationRow.appendChild(loadMore);
        container.appendChild(paginationRow);
    }

    if (importing) {
        const progress = document.createElement('div');
        progress.className = 'fb-connector-import-progress';
        if (importProgress && (importProgress.imported > 0 || importProgress.failed > 0)) {
            progress.textContent = `Importing… ${importProgress.imported} imported${importProgress.failed > 0 ? `, ${importProgress.failed} failed` : ''}`;
        } else {
            progress.textContent = 'Importing…';
        }
        container.appendChild(progress);
    }

    // Event delegation: grid click -> toggle selection (card or checkbox)
    const grid = gridWrap.querySelector('.fb-connector-grid');
    if (grid && typeof onToggleSelection === 'function') {
        grid.addEventListener('click', (e) => {
            const checkboxLabel = e.target.closest('.fb-connector-card__checkbox');
            const card = e.target.closest('.fb-connector-card');
            const key = checkboxLabel?.dataset.itemKey || card?.dataset?.itemKey;
            if (key) {
                e.preventDefault();
                onToggleSelection(key);
            }
        });
    }

    // Actions
    actionsRow.querySelector('[data-action="select-deselect"]')?.addEventListener('click', () => {
        if (allSelected && typeof onDeselectAll === 'function') onDeselectAll();
        else if (typeof onSelectAll === 'function') onSelectAll();
    });
}

function itemKey(item) {
    return `${item.type}:${item.id || ''}`;
}

function escapeHtmlForAttribute(text) {
    if (text == null) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}
