import { escapeHtml } from '/js/utils/dom.js';

export function renderStatus(element, message, type = 'success') {
    if (!element) return;
    if (!message) {
        element.textContent = '';
        element.style.display = 'none';
        element.classList.remove('success', 'error');
        return;
    }
    element.textContent = message;
    element.style.display = 'block';
    element.classList.remove('success', 'error');
    element.classList.add(type);
}

export function renderClientOptions(selectElement, clients, selectedClientUuid = '') {
    if (!selectElement) return;
    const optionsMarkup = clients
        .map((client) => {
            const clientUuid = String(client.client_uuid || client.id || '');
            const clientName = String(client.client_name || client.name || clientUuid);
            const isSelected = clientUuid && clientUuid === selectedClientUuid;
            return `<option value="${escapeHtml(clientUuid)}" ${isSelected ? 'selected' : ''}>${escapeHtml(clientName)}</option>`;
        })
        .join('');

    selectElement.innerHTML = `
        <option value="">Select a client...</option>
        ${optionsMarkup}
    `;
}

export function renderStoreConnections(container, connections) {
    if (!container) return;
    if (!connections.length) {
        container.innerHTML = '<div class="empty-state">No Shopify store mappings yet.</div>';
        return;
    }

    container.innerHTML = connections
        .map((item) => {
            const clientUuid = item.client_uuid ? String(item.client_uuid) : 'Unmapped';
            const status = String(item.status || 'unknown');
            return `
                <article class="shopify-card">
                    <div class="shopify-card-content">
                        <h3>${escapeHtml(item.shop_domain || '')}</h3>
                        <p>Client: ${escapeHtml(clientUuid)}</p>
                        <p>Status: ${escapeHtml(status)}</p>
                    </div>
                    <button
                        class="btn btn-secondary delete-connection-button"
                        data-shop-domain="${escapeHtml(item.shop_domain || '')}"
                        type="button"
                    >
                        Delete
                    </button>
                </article>
            `;
        })
        .join('');
}

export function renderRawResponses(container, items) {
    if (!container) return;
    if (!items.length) {
        container.innerHTML = '<div class="empty-state">No raw survey responses found for current filters.</div>';
        return;
    }

    container.innerHTML = `
        <table class="responses-table">
            <thead>
                <tr>
                    <th>Submitted</th>
                    <th>Shop</th>
                    <th>Client UUID</th>
                    <th>Order</th>
                    <th>Survey</th>
                    <th>Answer Keys</th>
                </tr>
            </thead>
            <tbody>
                ${items
                    .map((row) => {
                        const answerKeys = Object.keys(row.answers_json || {}).join(', ') || '-';
                        return `
                            <tr>
                                <td>${escapeHtml(row.submitted_at || '')}</td>
                                <td>${escapeHtml(row.shop_domain || '')}</td>
                                <td>${escapeHtml(row.client_uuid || 'Unmapped')}</td>
                                <td>${escapeHtml(row.shopify_order_id || row.order_gid || '-')}</td>
                                <td>${escapeHtml(row.survey_version || 'v1')}</td>
                                <td>${escapeHtml(answerKeys)}</td>
                            </tr>
                        `;
                    })
                    .join('')}
            </tbody>
        </table>
    `;
}
