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
 * @param {Function} [options.onLoadAll] - Called when user clicks Load All (loads all remaining pages)
 * @param {Function} options.onImport - Called with array of selected items to import
 * @param {Function} options.onToggleSelection - Called with item key (type:id) when card is toggled
 * @param {Function} options.onSelectAll - Select all visible items
 * @param {Function} options.onDeselectAll - Deselect all
 * @param {Function} [options.onFilterChange] - Called with 'all'|'image'|'video' when filter tab changes
 * @param {string} [options.mediaFilter='all'] - Current filter for active tab state
 * @param {Object} [options.loadAllProgress] - When Load All is running: { loaded: number, total: number|null }
 * @param {string} [options.loadError] - Error message when initial/media load failed (e.g. rate limit)
 * @param {Function} [options.onRetryLoad] - Called when user clicks Retry after a load error
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
        mediaFilter = 'all',
        loadAllProgress = null,
        loadError = null,
        onRetryLoad,
        onConnect,
        onLoadMore,
        onLoadAll,
        onImport,
        onToggleSelection,
        onSelectAll,
        onDeselectAll,
        onFilterChange,
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

    const filterRow = document.createElement('div');
    filterRow.className = 'fb-connector-filter';
    filterRow.innerHTML = `
        <span class="fb-connector-filter__label">Show:</span>
        <div class="fb-connector-filter__tabs" role="tablist">
            <button type="button" class="fb-connector-filter__tab ${mediaFilter === 'all' ? 'active' : ''}" data-filter="all">All</button>
            <button type="button" class="fb-connector-filter__tab ${mediaFilter === 'image' ? 'active' : ''}" data-filter="image">Images</button>
            <button type="button" class="fb-connector-filter__tab ${mediaFilter === 'video' ? 'active' : ''}" data-filter="video">Videos</button>
        </div>
    `;
    filterRow.querySelectorAll('.fb-connector-filter__tab').forEach((tab) => {
        tab.addEventListener('click', () => {
            const filter = tab.dataset.filter;
            if (typeof onFilterChange === 'function') onFilterChange(filter);
        });
    });
    container.appendChild(filterRow);

    if (loadError) {
        const errorBanner = document.createElement('div');
        errorBanner.className = 'fb-connector-load-error';
        errorBanner.innerHTML = `
            <p class="fb-connector-load-error__message">${escapeHtml(loadError)}</p>
            <button type="button" class="fb-connector-load-error__retry">Try again</button>
        `;
        const retryBtn = errorBanner.querySelector('.fb-connector-load-error__retry');
        if (retryBtn && typeof onRetryLoad === 'function') {
            retryBtn.addEventListener('click', () => onRetryLoad());
        }
        container.appendChild(errorBanner);
    }

    const actionsRow = document.createElement('div');
    actionsRow.className = 'fb-connector-actions';
    const selectedCount = items.filter((it) => selectedIds.has(itemKey(it))).length;
    actionsRow.innerHTML = `
        <button type="button" class="fb-connector-action-btn" data-action="select-all">Select All</button>
        <button type="button" class="fb-connector-action-btn" data-action="deselect-all">Deselect All</button>
        <span class="fb-connector-selected-count">${selectedCount} selected</span>
        <button type="button" class="fb-connector-import-btn" data-action="import" ${selectedCount === 0 || importing ? 'disabled' : ''}>Import Selected (${selectedCount})</button>
    `;
    container.appendChild(actionsRow);

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
                </div>
                <div class="fb-connector-card__check" aria-hidden="true">${isSelected ? '✓' : ''}</div>
                <div class="fb-connector-card__name">${escapeHtml(String(name).slice(0, 40))}${String(name).length > 40 ? '…' : ''}</div>
            `;
            grid.appendChild(card);
        });
        gridWrap.appendChild(grid);

        if (paging.hasMore) {
            const loadMore = document.createElement('button');
            loadMore.type = 'button';
            loadMore.className = 'fb-connector-load-more';
            loadMore.textContent = 'Load More';
            loadMore.addEventListener('click', () => {
                if (typeof onLoadMore === 'function') onLoadMore(paging);
            });
            gridWrap.appendChild(loadMore);
            if (typeof onLoadAll === 'function') {
                const loadAll = document.createElement('button');
                loadAll.type = 'button';
                loadAll.className = 'fb-connector-load-all';
                loadAll.textContent = 'Load All';
                loadAll.addEventListener('click', () => onLoadAll());
                gridWrap.appendChild(loadAll);
            }
        }
    }
    container.appendChild(gridWrap);

    if (importing) {
        const progress = document.createElement('div');
        progress.className = 'fb-connector-import-progress';
        progress.textContent = 'Importing…';
        container.appendChild(progress);
    }

    // Event delegation: grid click -> toggle selection
    const grid = gridWrap.querySelector('.fb-connector-grid');
    if (grid && typeof onToggleSelection === 'function') {
        grid.addEventListener('click', (e) => {
            const card = e.target.closest('.fb-connector-card');
            if (card && card.dataset.itemKey) {
                onToggleSelection(card.dataset.itemKey);
            }
        });
    }

    // Actions
    actionsRow.querySelector('[data-action="select-all"]')?.addEventListener('click', () => {
        if (typeof onSelectAll === 'function') onSelectAll();
    });
    actionsRow.querySelector('[data-action="deselect-all"]')?.addEventListener('click', () => {
        if (typeof onDeselectAll === 'function') onDeselectAll();
    });
    actionsRow.querySelector('[data-action="import"]')?.addEventListener('click', () => {
        if (importing || selectedCount === 0) return;
        const toImport = items.filter((it) => selectedIds.has(itemKey(it))).map((it) => ({
            type: it.type,
            hash: it.type === 'image' ? it.id : undefined,
            video_id: it.type === 'video' ? it.id : undefined,
            original_url: it.original_url || it.source || '',
            filename: it.name ? `${it.name}.${it.type === 'video' ? 'mp4' : 'jpg'}` : undefined,
            thumbnail_url: it.type === 'video' ? it.thumbnail_url : undefined,
        }));
        if (typeof onImport === 'function') onImport(toImport);
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
