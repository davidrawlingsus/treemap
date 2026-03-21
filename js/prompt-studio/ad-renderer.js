/**
 * Ad Renderer — renders Facebook ad preview cards using the shared fb-ad-mockup module.
 */

import { renderFBAdMockup, formatPrimaryText, extractDomain } from '/js/renderers/fb-ad-mockup.js';

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

const LANE_COLORS = {
    'LANE:TRANSFORMATION': '#8B5CF6',
    'LANE:STORY': '#EC4899',
    'LANE:SURPRISE': '#F59E0B',
    'LANE:PROOF': '#3B82F6',
    'LANE:CURIOSITY': '#10B981',
    'LANE:MISTAKE_AVOIDANCE': '#EF4444',
    'LANE:INSTRUCTIONAL': '#14B8A6',
};

/**
 * Render a single ad as a Facebook ad mockup card with metadata.
 */
function renderAdCard(ad, briefId, topicLabel, category, brandName) {
    // Support both schema formats: old (body, close.text) and FB spec (primary_text, description, testType)
    const lane = ad.lane || (ad.testType ? `LANE:${ad.testType.toUpperCase()}` : '');
    const laneColor = LANE_COLORS[lane] || '#6366F1';
    const laneName = ad.lane_name || ad.testType || lane.replace('LANE:', '') || 'Unknown';

    const bodyText = ad.primary_text || ad.body || '';
    const primaryText = formatPrimaryText(bodyText);
    const headline = escapeHtml(ad.headline || '');
    const description = escapeHtml(ad.description || ad.close?.text || '');
    const ctaRaw = ad.call_to_action || 'LEARN_MORE';
    const cta = ctaRaw.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()).replace(/\B\w+/g, w => w.toLowerCase());
    const origin = ad.origin || '';
    const destUrl = ad.destination_url || '';

    // Build the Facebook ad mockup
    const mockupHtml = renderFBAdMockup({
        adId: ad.ad_id || ad.id || briefId,
        primaryText,
        headline,
        description,
        cta,
        displayUrl: destUrl ? extractDomain(destUrl) : (brandName || 'brand.com'),
        logoSrc: '',
        clientName: brandName || 'Brand',
        imageUrl: '',
        readOnly: true,
    });

    // VoC evidence — support array of strings (new) or voc_usage object (legacy)
    const vocEvidence = ad.voc_evidence || [];
    const vocUsage = ad.voc_usage || {};
    const primary = vocUsage.primary_verbatim;
    const supporting = vocUsage.supporting_verbatims || [];

    let vocHtml = '';
    if (vocEvidence.length) {
        vocHtml = `<details class="ad-details">
            <summary>VoC Evidence (${vocEvidence.length} quotes)</summary>
            <div class="ad-voc-grounding">
                ${vocEvidence.map(q => `<div class="ad-voc-item">"${escapeHtml(q)}"</div>`).join('')}
            </div>
        </details>`;
    } else if (primary || supporting.length) {
        vocHtml = `<details class="ad-details">
            <summary>VoC Grounding</summary>
            <div class="ad-voc-grounding">
                ${primary ? `<div class="ad-voc-item primary">
                    <span class="ad-voc-badge">${escapeHtml(primary.usage || 'VERBATIM')}</span>
                    <span class="ad-voc-id">${escapeHtml(primary.review_id || '')}</span>
                    "${escapeHtml(primary.text || '')}"
                </div>` : ''}
                ${supporting.map(s => `<div class="ad-voc-item">
                    <span class="ad-voc-badge">${escapeHtml(s.usage || 'SUPPORTING')}</span>
                    <span class="ad-voc-id">${escapeHtml(s.review_id || '')}</span>
                    "${escapeHtml(s.text || '')}"
                </div>`).join('')}
            </div>
        </details>`;
    }

    return `
        <div class="ad-card" data-lane="${escapeHtml(lane)}" data-brief="${escapeHtml(briefId)}" data-category="${escapeHtml(category)}">
            <div class="ad-card-header">
                <span class="ad-lane-badge" style="background:${laneColor}">${escapeHtml(laneName)}</span>
                <span class="ad-topic-label">${escapeHtml(topicLabel)}</span>
                <span class="ad-category-label">${escapeHtml(category)}</span>
                ${origin ? `<span class="ad-origin-label">${escapeHtml(origin)}</span>` : ''}
            </div>
            <div class="ad-mockup-wrapper">
                ${mockupHtml}
            </div>
            <div class="ad-card-meta">
                <div class="ad-hypothesis">${escapeHtml(ad.test_hypothesis || '')}</div>
                <details class="ad-details">
                    <summary>Strategic Memo</summary>
                    <div class="ad-memo">${escapeHtml(ad.strategic_memo || '')}</div>
                </details>
                ${vocHtml}
                <div class="ad-meta-row">
                    ${ad.estimated_word_count ? `<span>${ad.estimated_word_count} words</span>` : ''}
                    ${ad.reading_level ? `<span>${escapeHtml(ad.reading_level)}</span>` : ''}
                    ${ad.proof_modality_used ? `<span>${escapeHtml(ad.proof_modality_used.replace('PROOF:', ''))}</span>` : ''}
                </div>
            </div>
        </div>
    `;
}

/**
 * Render all generated ads into a container.
 * @param {HTMLElement} container - Target DOM element
 * @param {Array} adBatches - Array of Prompt 6 outputs
 * @param {Array} briefs - The creative briefs
 * @param {string} brandName - Brand name for the mockup header
 */
export function renderAds(container, adBatches, briefs, brandName) {
    if (!adBatches || adBatches.length === 0) {
        container.innerHTML = '<div class="ads-placeholder">No ads generated yet. Run the Generate step to create ad concepts.</div>';
        return;
    }

    const allAds = [];
    adBatches.forEach(batch => {
        const category = batch._category || batch.topic_label || '';
        const topicLabel = batch._topic_label || batch.topic_label || '';
        const briefId = batch.brief_id || topicLabel;
        // Find the ads array — could be .ads, .ad_concepts, or any array value
        let ads = batch.ads;
        if (!Array.isArray(ads)) {
            ads = batch.ad_concepts;
        }
        if (!Array.isArray(ads)) {
            // Last resort: find first array property
            for (const key of Object.keys(batch)) {
                if (key.startsWith('_')) continue;
                if (Array.isArray(batch[key]) && batch[key].length && typeof batch[key][0] === 'object') {
                    ads = batch[key];
                    break;
                }
            }
        }
        (ads || []).forEach(ad => {
            allAds.push({ ad, briefId, topicLabel, category });
        });
    });

    // Group by category
    const byCategory = new Map();
    allAds.forEach(item => {
        if (!byCategory.has(item.category)) byCategory.set(item.category, []);
        byCategory.get(item.category).push(item);
    });

    const lanes = new Set(allAds.map(a => {
        const l = a.ad.lane || (a.ad.testType ? `LANE:${a.ad.testType.toUpperCase()}` : '');
        return l;
    }).filter(Boolean));
    let html = `
        <div class="ads-summary">
            <span class="ads-count">${allAds.length} ads generated</span>
            <span class="ads-topics">${adBatches.length} topics</span>
            <span class="ads-categories">${byCategory.size} categories</span>
        </div>
        <div class="ads-filters">
            <button class="ads-filter-btn active" data-filter="all">All</button>
            ${Array.from(lanes).map(l => {
                const name = l.replace('LANE:', '');
                const color = LANE_COLORS[l] || '#6366F1';
                return `<button class="ads-filter-btn" data-filter="${escapeHtml(l)}" style="border-color:${color}">${escapeHtml(name)}</button>`;
            }).join('')}
        </div>
    `;

    for (const [category, items] of byCategory) {
        html += `<div class="ads-category-group">
            <h4 class="ads-category-title">${escapeHtml(category)}</h4>
            <div class="ads-grid">
                ${items.map(i => renderAdCard(i.ad, i.briefId, i.topicLabel, i.category, brandName)).join('')}
            </div>
        </div>`;
    }

    container.innerHTML = html;

    // Wire up filter buttons
    container.addEventListener('click', (e) => {
        const filterBtn = e.target.closest('.ads-filter-btn');
        if (!filterBtn) return;
        const filter = filterBtn.dataset.filter;
        container.querySelectorAll('.ads-filter-btn').forEach(b => b.classList.remove('active'));
        filterBtn.classList.add('active');
        container.querySelectorAll('.ad-card').forEach(card => {
            card.style.display = (filter === 'all' || card.dataset.lane === filter) ? '' : 'none';
        });
    });
}
