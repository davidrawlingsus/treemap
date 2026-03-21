/**
 * Creative Selection Logic — deterministic topic selection and rich payload assembly.
 * Passes full raw reviews (not thin briefs) so the creative prompt can mine its own gold.
 */

const LANE_PRIORITY = [
    'LANE:TRANSFORMATION',
    'LANE:STORY',
    'LANE:SURPRISE',
    'LANE:PROOF',
    'LANE:CURIOSITY',
    'LANE:MISTAKE_AVOIDANCE',
    'LANE:INSTRUCTIONAL',
];

/**
 * Determine if a topic qualifies for ad generation.
 */
function qualifiesForAds(topic) {
    const priority = topic.creative_priority;
    if (priority === 'PRIMARY') return true;
    if (priority === 'SECONDARY') {
        const cv = topic.creative_value_summary || {};
        return (cv.HIGH || 0) >= 1 || (cv.MEDIUM || 0) >= 3;
    }
    return false;
}

/**
 * Select lanes for a topic, respecting the cap.
 */
function selectLanes(topic) {
    const cap = topic.creative_priority === 'PRIMARY' ? 3 : 2;
    const available = (topic.usable_as || []).filter(t => t.startsWith('LANE:'));
    const sorted = LANE_PRIORITY.filter(l => available.includes(l));
    return sorted.slice(0, cap);
}

/**
 * Map review_ids to full raw review text from the original reviews array.
 */
function assembleFullReviews(reviewIds, reviews) {
    if (!reviewIds?.length || !reviews?.length) return [];

    // Build lookups by both respondent_id AND positional R-XXX format
    const byRespondentId = new Map();
    const byPositionalId = new Map();
    reviews.forEach((r, idx) => {
        if (r.respondent_id) byRespondentId.set(r.respondent_id, r);
        // The Extract prompt assigns R-001, R-002... sequentially
        const positionalId = `R-${String(idx + 1).padStart(3, '0')}`;
        byPositionalId.set(positionalId, r);
    });

    const results = [];
    const seen = new Set();
    for (const rid of reviewIds) {
        if (seen.has(rid)) continue;
        seen.add(rid);
        // Try respondent_id first, then positional R-XXX
        const review = byRespondentId.get(rid) || byPositionalId.get(rid);
        if (review) {
            results.push({
                review_id: rid,
                text: review.value || '',
                rating: review.survey_metadata?.rating || null,
            });
        }
    }
    return results;
}

/**
 * Build rich payloads for ad generation from a validated taxonomy.
 * Each payload contains full raw reviews, not thin briefs.
 *
 * @param {Object} taxonomy - Prompt 3 validated output
 * @param {Array} reviews - Full reviews array from studioInputs
 * @param {Object} businessContext - { brand, product, website, ... }
 * @returns {Array} Array of payload objects
 */
export function buildCreativePayloads(taxonomy, reviews, businessContext) {
    const payloads = [];
    const categories = taxonomy.categories || [];
    const singletons = taxonomy.singletons || [];

    for (const cat of categories) {
        for (const topic of cat.topics || []) {
            if (!qualifiesForAds(topic)) continue;

            const lanes = selectLanes(topic);
            if (lanes.length === 0) continue;

            // Gather all review_ids: topic + same-category secondary + relevant singletons
            const allReviewIds = new Set(topic.review_ids || []);
            const secondaryLabels = [];
            for (const t of cat.topics || []) {
                if (t.label !== topic.label && t.creative_priority === 'SECONDARY') {
                    secondaryLabels.push(t.label);
                    (t.review_ids || []).forEach(id => allReviewIds.add(id));
                }
            }
            for (const s of singletons) {
                if (s.nearest_category === cat.category && s.review_id) {
                    allReviewIds.add(s.review_id);
                }
            }

            const fullReviews = assembleFullReviews(Array.from(allReviewIds), reviews);
            const usableAs = topic.usable_as || [];
            const proofTags = usableAs.filter(t => t.startsWith('PROOF:')).join(', ');
            const blockTags = usableAs.filter(t => t.startsWith('BLOCK:')).join(', ');
            const laneNames = lanes.map(l => l.replace('LANE:', '')).join(', ');
            const verbatimBullets = (topic.verbatims || [])
                .map(v => `- "${v.text}" (${v.review_id})`)
                .join('\n');

            payloads.push({
                topic_label: topic.label,
                category: cat.category,
                creative_priority: topic.creative_priority,
                signal_count: topic.signal_count,
                lanes,
                lane_names: laneNames,
                full_reviews: fullReviews,
                secondary_labels: secondaryLabels,
                proof_tags: proofTags,
                block_tags: blockTags,
                verbatim_bullets: verbatimBullets,
                business_context: businessContext,
            });
        }
    }
    return payloads;
}

/**
 * Assemble the user prompt for a single topic payload.
 */
export function assembleUserPrompt(template, payload) {
    const bc = payload.business_context || {};
    const businessContextText = [
        bc.brand ? `Brand: ${bc.brand}` : '',
        bc.product ? `Product/Business Context: ${bc.product}` : '',
        bc.category ? `Category: ${bc.category}` : '',
        bc.website ? `Website: ${bc.website}` : '',
        bc.primary_claims ? `Primary Claims: ${bc.primary_claims}` : '',
        bc.target_customer ? `Target Customer: ${bc.target_customer}` : '',
        bc.competitors ? `Key Competitors / Alternatives: ${bc.competitors}` : '',
    ].filter(Boolean).join('\n');

    const reviewsText = payload.full_reviews
        .map(r => `Review ${r.review_id} (Rating: ${r.rating || 'N/A'}):\n"${r.text}"`)
        .join('\n\n---\n\n');

    const secondaryList = payload.secondary_labels.length
        ? payload.secondary_labels.join(', ')
        : 'None';

    return template
        .replace('{BUSINESS_CONTEXT}', businessContextText)
        .replace('{FULL_RAW_REVIEWS_FOR_THIS_TOPIC}', reviewsText)
        .replace('{TOPIC_LABEL}', payload.topic_label)
        .replace('{CATEGORY}', payload.category)
        .replace('{LIST_OF_SECONDARY_TOPIC_LABELS_IN_SAME_CATEGORY}', secondaryList)
        .replace('{VERBATIM_BULLETS}', payload.verbatim_bullets)
        .replace('{PROOF_TAGS}', payload.proof_tags || 'None specified')
        .replace('{BLOCK_TAGS}', payload.block_tags || 'None specified')
        .replace('{COMMA_SEPARATED_LANE_NAMES}', payload.lane_names);
}

/**
 * Get a summary of what the selection logic produced.
 */
export function summarizePayloads(payloads) {
    const totalAds = payloads.reduce((sum, p) => sum + p.lanes.length, 0);
    const primaryCount = payloads.filter(p => p.creative_priority === 'PRIMARY').length;
    const secondaryCount = payloads.filter(p => p.creative_priority === 'SECONDARY').length;
    const totalReviews = payloads.reduce((sum, p) => sum + p.full_reviews.length, 0);
    return { total_payloads: payloads.length, total_ads: totalAds, primary: primaryCount, secondary: secondaryCount, total_reviews: totalReviews };
}
