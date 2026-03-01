import { escapeHtml } from '/js/utils/dom.js';
import { renderFBAdMockup, formatCTA, extractDomain, formatPrimaryText } from '/js/renderers/fb-ad-mockup.js';

const HOVER_DELAY = 320;
let hoverTimeout = null;
let previewContainer = null;

const COLUMN_DEFS = {
    revenue: { label: 'Revenue', formatter: (v) => formatCurrency(v) },
    roas: { label: 'ROAS', formatter: (v) => formatNumber(v, 2) },
    ctr: { label: 'CTR', formatter: (v) => formatPercent(v) },
    clicks: { label: 'Clicks', formatter: (v) => formatInt(v) },
    impressions: { label: 'Impressions', formatter: (v) => formatInt(v) },
    spend: { label: 'Spend', formatter: (v) => formatCurrency(v) },
    purchases: { label: 'Purchases', formatter: (v) => formatInt(v) },
    startedDate: {
        label: 'Started',
        formatter: (v) => {
            if (!v) return '-';
            const date = new Date(v);
            if (Number.isNaN(date.getTime())) return '-';
            return date.toLocaleDateString();
        }
    },
};

const COLUMN_ORDER = ['revenue', 'roas', 'ctr', 'clicks', 'impressions', 'spend', 'purchases', 'startedDate'];

function formatCurrency(value) {
    const num = Number(value);
    if (!Number.isFinite(num)) return '-';
    return new Intl.NumberFormat(undefined, {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 2
    }).format(num);
}

function formatPercent(value) {
    const num = Number(value);
    if (!Number.isFinite(num)) return '-';
    return `${(num * 100).toFixed(2)}%`;
}

function formatNumber(value, decimals = 2) {
    const num = Number(value);
    if (!Number.isFinite(num)) return '-';
    return num.toFixed(decimals);
}

function formatInt(value) {
    const num = Number(value);
    if (!Number.isFinite(num)) return '-';
    return new Intl.NumberFormat().format(Math.round(num));
}

function getPreviewContainer() {
    if (!previewContainer) {
        previewContainer = document.createElement('div');
        previewContainer.className = 'ads-kanban__preview images-table__preview';
        document.body.appendChild(previewContainer);
    }
    return previewContainer;
}

function positionPreview(anchorEl, previewEl) {
    const rect = anchorEl.getBoundingClientRect();
    const previewWidth = 380;
    const padding = 12;
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    let left = rect.right + padding;
    if (left + previewWidth > viewportWidth - padding) {
        left = rect.left - previewWidth - padding;
    }
    if (left < padding) {
        left = Math.max(padding, (viewportWidth - previewWidth) / 2);
    }

    previewEl.style.visibility = 'hidden';
    previewEl.style.display = 'block';
    const previewHeight = previewEl.offsetHeight;
    previewEl.style.visibility = '';

    let top = rect.top + (rect.height / 2) - (previewHeight / 2);
    const minTop = padding;
    const maxTop = viewportHeight - previewHeight - padding;
    top = Math.max(minTop, Math.min(top, maxTop));
    if (previewHeight > viewportHeight - (2 * padding)) {
        top = padding;
    }

    previewEl.style.left = `${left}px`;
    previewEl.style.top = `${top}px`;
}

function showPreview(row, thumbEl) {
    if (!row) return;
    const preview = getPreviewContainer();
    const navLogo = document.getElementById('navClientLogo');
    const logoSrc = navLogo ? navLogo.src : '';
    const clientSelect = document.getElementById('clientSelect');
    const clientName = clientSelect?.selectedOptions?.[0]?.textContent?.trim() || 'Sponsored';
    const mediaUrl = row.url || null;
    const posterUrl = row.meta_thumbnail_url || null;

    preview.innerHTML = renderFBAdMockup({
        adId: row.meta_ad_id || row.id,
        primaryText: formatPrimaryText(row.ad_primary_text || ''),
        headline: escapeHtml(row.ad_headline || ''),
        description: escapeHtml(row.ad_description || ''),
        cta: formatCTA(row.ad_call_to_action),
        displayUrl: extractDomain(row.destination_url || ''),
        logoSrc,
        clientName,
        imageUrl: mediaUrl,
        posterUrl,
        readOnly: true,
        muted: false,
    });
    const videoEl = preview.querySelector('video');
    if (videoEl) {
        videoEl.muted = false;
        videoEl.volume = 1;
        videoEl.play().catch(() => {
            // Some browsers block autoplay with sound unless user gesture.
            videoEl.muted = true;
            videoEl.play().catch(() => {});
        });
    }
    positionPreview(thumbEl, preview);
    preview.classList.add('visible');
}

function hidePreview() {
    if (hoverTimeout) {
        clearTimeout(hoverTimeout);
        hoverTimeout = null;
    }
    if (previewContainer) {
        const videoEl = previewContainer.querySelector('video');
        if (videoEl) {
            videoEl.pause();
            videoEl.currentTime = 0;
            videoEl.muted = true;
        }
        previewContainer.classList.remove('visible');
    }
}

function renderCellValue(image, key) {
    if (key === 'startedDate') {
        return COLUMN_DEFS.startedDate.formatter(image.started_running_on_best_ad || image.started_running_on);
    }
    return COLUMN_DEFS[key]?.formatter(image[key]);
}

function renderThumbCell(image) {
    const contentType = image.content_type || '';
    const isVideo = contentType.startsWith('video');
    const thumbUrl = isVideo ? (image.meta_thumbnail_url || image.url) : image.url;
    if (!thumbUrl) return '<span class="images-table__thumb-empty">-</span>';
    return `
        <button type="button" class="images-table__thumb-btn" data-image-id="${escapeHtml(image.id || '')}" aria-label="Preview ad">
            <img src="${escapeHtml(thumbUrl)}" alt="${escapeHtml(image.filename || 'Media')}" class="images-table__thumb-img" loading="lazy">
            ${isVideo ? '<span class="images-table__thumb-play">▶</span>' : ''}
        </button>
    `;
}

function renderColumnPicker(currentColumns) {
    const remaining = COLUMN_ORDER.filter((key) => !currentColumns.includes(key));
    if (!remaining.length) {
        return `
            <div class="images-table__column-picker">
                <button type="button" class="images-table__column-picker-btn" disabled title="No more metrics">+</button>
            </div>
        `;
    }
    return `
        <div class="images-table__column-picker">
            <button type="button" class="images-table__column-picker-btn" id="imagesTableColumnPickerBtn" aria-label="Add metric column">+</button>
            <div class="images-table__column-picker-menu" id="imagesTableColumnPickerMenu">
                ${remaining.map((key) => `
                    <button type="button" class="images-table__column-picker-item" data-add-column="${escapeHtml(key)}">
                        ${escapeHtml(COLUMN_DEFS[key].label)}
                    </button>
                `).join('')}
            </div>
        </div>
    `;
}

export function renderImagesTable(container, images, options = {}) {
    const { columns = [], onColumnsChange = null } = options;
    const validColumns = columns.filter((key) => !!COLUMN_DEFS[key]);

    if (!images || images.length === 0) {
        container.innerHTML = `
            <div class="images-empty">
                <div class="images-empty__icon">📊</div>
                <h3 class="images-empty__title">No media rows yet</h3>
                <p class="images-empty__text">Import media to populate performance rows.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = `
        <div class="images-table-wrap">
            <table class="images-table">
                <thead>
                    <tr>
                        <th>Media</th>
                        ${validColumns.map((key) => `
                            <th>
                                <div class="images-table__th-content">
                                    <span>${escapeHtml(COLUMN_DEFS[key].label)}</span>
                                    <button type="button" class="images-table__remove-col" data-remove-column="${escapeHtml(key)}" aria-label="Remove column">×</button>
                                </div>
                            </th>
                        `).join('')}
                        <th class="images-table__plus-col">${renderColumnPicker(validColumns)}</th>
                    </tr>
                </thead>
                <tbody>
                    ${images.map((image) => `
                        <tr data-image-id="${escapeHtml(image.id || '')}">
                            <td class="images-table__media-col">
                                ${renderThumbCell(image)}
                                <div class="images-table__media-meta">
                                    <div class="images-table__filename" title="${escapeHtml(image.filename || '')}">${escapeHtml(image.filename || 'Untitled')}</div>
                                    ${image.meta_ad_id ? `<div class="images-table__meta-id" title="Meta ad id">${escapeHtml(image.meta_ad_id)}</div>` : ''}
                                </div>
                            </td>
                            ${validColumns.map((key) => `<td>${escapeHtml(String(renderCellValue(image, key)))}</td>`).join('')}
                            <td class="images-table__plus-col"></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;

    const imageMap = new Map((images || []).map((img) => [img.id, img]));

    container.querySelectorAll('.images-table__remove-col').forEach((btn) => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const col = btn.dataset.removeColumn;
            if (!col || typeof onColumnsChange !== 'function') return;
            const next = validColumns.filter((c) => c !== col);
            onColumnsChange(next);
        });
    });

    const pickerBtn = container.querySelector('#imagesTableColumnPickerBtn');
    const pickerMenu = container.querySelector('#imagesTableColumnPickerMenu');
    if (pickerBtn && pickerMenu) {
        pickerBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            pickerMenu.classList.toggle('is-open');
        });
        pickerMenu.querySelectorAll('[data-add-column]').forEach((item) => {
            item.addEventListener('click', () => {
                const col = item.dataset.addColumn;
                if (!col || typeof onColumnsChange !== 'function') return;
                const next = [...validColumns, col];
                onColumnsChange(next);
            });
        });
        document.addEventListener('click', () => {
            pickerMenu.classList.remove('is-open');
        }, { once: true });
    }

    container.querySelectorAll('.images-table__thumb-btn').forEach((btn) => {
        btn.addEventListener('mouseenter', () => {
            const row = imageMap.get(btn.dataset.imageId);
            if (!row) return;
            if (hoverTimeout) clearTimeout(hoverTimeout);
            hoverTimeout = setTimeout(() => showPreview(row, btn), HOVER_DELAY);
        });
        btn.addEventListener('mouseleave', hidePreview);
    });

    const preview = getPreviewContainer();
    if (!preview.dataset.bound) {
        preview.addEventListener('mouseenter', () => {
            if (hoverTimeout) {
                clearTimeout(hoverTimeout);
                hoverTimeout = null;
            }
        });
        preview.addEventListener('mouseleave', hidePreview);
        preview.dataset.bound = '1';
    }
}
