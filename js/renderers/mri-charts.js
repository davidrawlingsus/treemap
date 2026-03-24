/**
 * MRI Charts Renderer (v2)
 * D3 visualizations for Creative MRI report.
 * Charts 1-6: launch cadence, rotation depth, creative half-life, format/funnel mix, hook×funnel (unchanged).
 * Chart 7: 13-dimension horizontal bar chart (from batch_synthesis.dimensions).
 * Chart 8: Top-3 / Bottom-3 findings display (from batch_synthesis).
 */

const MRI_CHART_COLORS = [
    '#8B5CF6', '#EC4899', '#F59E0B', '#10B981', '#3B82F6', '#F97316',
    '#EF4444', '#14B8A6', '#6366F1', '#74c7e8', '#6fd4a1',
];

// Dimension score color thresholds
function dimensionColor(score) {
    if (score >= 70) return '#10B981'; // green
    if (score >= 40) return '#F59E0B'; // amber
    return '#EF4444'; // red
}

/**
 * Parse date strings from Meta format ("Jan 15, 2024") or ISO
 */
function parseDate(s) {
    if (!s) return null;
    if (typeof s !== 'string') return s instanceof Date ? s : null;
    const d = new Date(s);
    return isNaN(d.getTime()) ? null : d;
}

/**
 * Get start of week (Monday) for a date
 */
function weekKey(d) {
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1);
    const mon = new Date(d);
    mon.setDate(diff);
    return mon.toISOString().slice(0, 10);
}

/**
 * Get normalized ads array: prefer analysis.analysis.ads, fallback to report.ads with mapping
 */
function getAdsForCharts(report) {
    const structured = report?.analysis?.analysis?.ads || [];
    const flat = report?.ads || [];
    if (structured.length > 0) return structured;
    return flat.map(a => ({
        ad_id: a.id,
        started_running_on: a.started_running_on,
        ad_delivery_start_time: a.ad_delivery_start_time,
        ad_delivery_end_time: a.ad_delivery_end_time,
        labels: { format: (a.ad_format || 'unknown').toLowerCase() },
        funnel: { stage: (a.funnel_stage || 'tofu').toLowerCase() },
        hook: {
            hook_types: [{ type: a.hook_type || 'unknown' }],
        },
    }));
}

/** Prep chart 1: launches per week */
function prepLaunchCadence(ads) {
    const byWeek = {};
    ads.forEach(a => {
        const d = parseDate(a.started_running_on || a.ad_delivery_start_time);
        if (!d) return;
        const wk = weekKey(d);
        byWeek[wk] = (byWeek[wk] || 0) + 1;
    });
    return Object.entries(byWeek)
        .map(([week, count]) => ({ week, date: new Date(week), count }))
        .sort((a, b) => a.date - b.date);
}

/** Default run length (days) for ads without end date. */
const ROTATION_DEPTH_DEFAULT_RUN_DAYS = 90;

/** Prep chart 2: active creatives per week */
function prepRotationDepth(ads) {
    const byWeek = {};
    ads.forEach(a => {
        const start = parseDate(a.ad_delivery_start_time || a.started_running_on);
        const end = parseDate(a.ad_delivery_end_time);
        if (!start) return;
        let endDate;
        if (end && end >= start) {
            endDate = end;
        } else {
            const assumedEnd = new Date(start);
            assumedEnd.setDate(assumedEnd.getDate() + ROTATION_DEPTH_DEFAULT_RUN_DAYS);
            endDate = assumedEnd;
        }
        let d = new Date(start);
        while (d <= endDate) {
            const wk = weekKey(d);
            byWeek[wk] = (byWeek[wk] || 0) + 1;
            d.setDate(d.getDate() + 7);
        }
    });
    return Object.entries(byWeek)
        .map(([week, count]) => ({ week, date: new Date(week), count }))
        .sort((a, b) => a.date - b.date);
}

/** Prep chart 3: run length in days (histogram) */
function prepCreativeHalfLife(ads) {
    let datasetCutoff = null;
    ads.forEach(a => {
        const start = parseDate(a.ad_delivery_start_time || a.started_running_on);
        const end = parseDate(a.ad_delivery_end_time);
        if (start && (!datasetCutoff || start > datasetCutoff)) datasetCutoff = new Date(start);
        if (end && (!datasetCutoff || end > datasetCutoff)) datasetCutoff = new Date(end);
    });
    if (!datasetCutoff) return [];

    const days = [];
    ads.forEach(a => {
        const start = parseDate(a.ad_delivery_start_time || a.started_running_on);
        const end = parseDate(a.ad_delivery_end_time);
        if (!start) return;
        const endDate = end && end >= start ? end : datasetCutoff;
        const diff = Math.round((endDate - start) / (1000 * 60 * 60 * 24));
        if (diff >= 0) days.push(diff);
    });
    return days;
}

/** Prep chart 4: format mix by week (100% stacked) */
function prepFormatMixOverTime(ads) {
    const byWeek = {};
    ads.forEach(a => {
        const d = parseDate(a.started_running_on || a.ad_delivery_start_time);
        if (!d) return;
        const wk = weekKey(d);
        if (!byWeek[wk]) byWeek[wk] = {};
        const fmt = (a.labels?.format || 'unknown').toLowerCase();
        byWeek[wk][fmt] = (byWeek[wk][fmt] || 0) + 1;
    });
    const formats = [...new Set(Object.values(byWeek).flatMap(w => Object.keys(w)))].sort();
    return {
        keys: formats,
        data: Object.entries(byWeek)
            .map(([week, counts]) => {
                const total = Object.values(counts).reduce((s, n) => s + n, 0) || 1;
                const row = { week, date: new Date(week) };
                formats.forEach(f => { row[f] = (counts[f] || 0) / total; });
                return row;
            })
            .sort((a, b) => a.date - b.date),
    };
}

/** Prep chart 5: funnel mix by week (normalized stacked) */
function prepFunnelMixOverTime(ads) {
    const byWeek = {};
    ads.forEach(a => {
        const d = parseDate(a.started_running_on || a.ad_delivery_start_time);
        if (!d) return;
        const wk = weekKey(d);
        if (!byWeek[wk]) byWeek[wk] = { tofu: 0, mofu: 0, bofu: 0 };
        const stage = ((a.funnel?.stage || 'tofu') + '').toLowerCase();
        const s = ['tofu', 'mofu', 'bofu'].includes(stage) ? stage : 'tofu';
        byWeek[wk][s] = (byWeek[wk][s] || 0) + 1;
    });
    return Object.entries(byWeek)
        .map(([week, counts]) => {
            const t = counts.tofu || 0, m = counts.mofu || 0, b = counts.bofu || 0;
            const total = t + m + b || 1;
            return {
                week,
                date: new Date(week),
                tofu: t / total,
                mofu: m / total,
                bofu: b / total,
            };
        })
        .sort((a, b) => a.date - b.date);
}

/** Prep chart 6: hook x funnel counts */
function prepHookFunnel(ads) {
    const counts = {};
    ads.forEach(a => {
        const h = ((a.hook?.hook_types?.[0]?.type) || a.hook_type || 'unknown').toLowerCase();
        const f = ((a.funnel?.stage) || a.funnel_stage || 'tofu').toLowerCase();
        const stage = ['tofu', 'mofu', 'bofu'].includes(f) ? f : 'tofu';
        const key = `${h}|${stage}`;
        counts[key] = (counts[key] || 0) + 1;
    });
    const hooks = [...new Set(Object.keys(counts).map(k => k.split('|')[0]))].sort();
    const stages = ['tofu', 'mofu', 'bofu'];
    return { hooks, stages, counts };
}

function renderEmpty(container, msg = 'No data available') {
    if (!container) return;
    const el = typeof container === 'string' ? document.getElementById(container) : container;
    if (!el) return;
    el.innerHTML = `<div class="mri-chart-empty" style="padding:24px;text-align:center;color:var(--muted,#718096);font-size:13px;">${msg}</div>`;
}

/**
 * Render D3 line chart (charts 1 & 2)
 */
export function renderLaunchCadence(container, data, yLabel = 'Launches') {
    const el = typeof container === 'string' ? document.getElementById(container) : container;
    if (!el || !window.d3) {
        renderEmpty(el, 'Chart unavailable');
        return;
    }
    el.innerHTML = '';
    if (!data || data.length === 0) {
        renderEmpty(el);
        return;
    }
    const d3 = window.d3;
    const width = Math.max(200, el.clientWidth || 280);
    const height = 160;
    const margin = { top: 12, right: 12, bottom: 28, left: 36 };
    const innerW = width - margin.left - margin.right;
    const innerH = height - margin.top - margin.bottom;

    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height).attr('viewBox', `0 0 ${width} ${height}`);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const x = d3.scaleTime().domain(d3.extent(data, d => d.date)).range([0, innerW]);
    const y = d3.scaleLinear().domain([0, d3.max(data, d => d.count) || 1]).nice().range([innerH, 0]);

    g.append('g').attr('transform', `translate(0,${innerH})`).call(d3.axisBottom(x).ticks(5).tickFormat(d3.timeFormat('%b %d')));
    g.append('g').call(d3.axisLeft(y).ticks(4));

    const line = d3.line().x(d => x(d.date)).y(d => y(d.count));
    g.append('path').datum(data).attr('fill', 'none').attr('stroke', MRI_CHART_COLORS[0]).attr('stroke-width', 2).attr('d', line);

    g.selectAll('.dot').data(data).join('circle').attr('class', 'dot').attr('cx', d => x(d.date)).attr('cy', d => y(d.count)).attr('r', 3).attr('fill', MRI_CHART_COLORS[0]);

    d3.selectAll('.mri-chart-tooltip').remove();
    const tooltip = d3.select('body').append('div').attr('class', 'mri-chart-tooltip').style('position', 'absolute').style('pointer-events', 'none').style('opacity', 0).style('background', '#1a202c').style('color', '#fff').style('padding', '6px 10px').style('border-radius', '6px').style('font-size', '12px').style('z-index', 1000);

    g.selectAll('.dot').on('mouseover', (ev, d) => {
        tooltip.style('opacity', 1).html(`${d3.timeFormat('%b %d, %Y')(d.date)}<br><strong>${d.count}</strong> ${yLabel}`);
    }).on('mousemove', ev => {
        tooltip.style('left', (ev.pageX + 10) + 'px').style('top', (ev.pageY + 10) + 'px');
    }).on('mouseout', () => tooltip.style('opacity', 0));
}

/**
 * Render creative half-life histogram (chart 3)
 */
export function renderCreativeHalfLife(container, daysArray) {
    const el = typeof container === 'string' ? document.getElementById(container) : container;
    if (!el || !window.d3) {
        renderEmpty(el, 'Chart unavailable');
        return;
    }
    el.innerHTML = '';
    if (!daysArray || daysArray.length === 0) {
        renderEmpty(el);
        return;
    }
    const d3 = window.d3;
    const width = Math.max(200, el.clientWidth || 280);
    const height = 160;
    const margin = { top: 12, right: 12, bottom: 28, left: 36 };
    const innerW = width - margin.left - margin.right;
    const innerH = height - margin.top - margin.bottom;

    const bins = d3.bin().thresholds(12)(daysArray);
    const x = d3.scaleLinear().domain([0, d3.max(daysArray) || 1]).range([0, innerW]);
    const y = d3.scaleLinear().domain([0, d3.max(bins, b => b.length) || 1]).nice().range([innerH, 0]);

    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height).attr('viewBox', `0 0 ${width} ${height}`);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    g.append('g').attr('transform', `translate(0,${innerH})`).call(d3.axisBottom(x).ticks(6)).append('text').attr('x', innerW / 2).attr('y', 22).attr('fill', '#718096').attr('text-anchor', 'middle').style('font-size', '11px').text('Run length (days)');
    g.append('g').call(d3.axisLeft(y).ticks(4));

    g.selectAll('rect').data(bins).join('rect').attr('x', d => x(d.x0)).attr('y', d => y(d.length)).attr('width', d => Math.max(0, x(d.x1) - x(d.x0) - 2)).attr('height', d => innerH - y(d.length)).attr('fill', MRI_CHART_COLORS[1]);
}

/**
 * Render stacked area (chart 4) or normalized stacked area (chart 5)
 */
function renderStackedArea(container, data, keys, normalized = false, keyFormatter = k => k) {
    const el = typeof container === 'string' ? document.getElementById(container) : container;
    if (!el || !window.d3) {
        renderEmpty(el, 'Chart unavailable');
        return;
    }
    el.innerHTML = '';
    const series = (data && data.data) ? data : { keys: keys || [], data: data || [] };
    const keysArr = series.keys || [];
    const arr = series.data || [];
    if (arr.length === 0 || keysArr.length === 0) {
        renderEmpty(el);
        return;
    }
    const d3 = window.d3;
    const width = Math.max(200, el.clientWidth || 280);
    const height = 160;
    const margin = { top: 12, right: 80, bottom: 28, left: 36 };
    const innerW = width - margin.left - margin.right;
    const innerH = height - margin.top - margin.bottom;

    const stack = d3.stack().keys(keysArr).offset(normalized ? d3.stackOffsetExpand : d3.stackOffsetNone);
    const stacked = stack(arr.map(d => {
        const out = { ...d };
        keysArr.forEach(k => { out[k] = Math.max(0, Number(d[k]) || 0); });
        return out;
    }));

    const x = d3.scaleTime().domain(d3.extent(arr, d => d.date)).range([0, innerW]);
    const yMax = normalized ? 1 : Math.max(0.001, d3.max(stacked, s => d3.max(s, d => d[1])) || 0);
    const y = d3.scaleLinear().domain([0, yMax]).range([innerH, 0]);

    const area = d3.area()
        .x(d => x(d.data.date))
        .y0(d => y(Math.max(0, d[0])))
        .y1(d => y(Math.max(0, d[1])))
        .defined(d => d[0] <= d[1]);
    const color = d3.scaleOrdinal(keysArr, MRI_CHART_COLORS);

    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height).attr('viewBox', `0 0 ${width} ${height}`);
    const defs = svg.append('defs');
    const clipId = 'stacked-area-clip-' + (el.id || Math.random().toString(36).slice(2));
    defs.append('clipPath').attr('id', clipId).append('rect').attr('width', innerW).attr('height', innerH);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    g.append('g').attr('transform', `translate(0,${innerH})`).call(d3.axisBottom(x).ticks(5).tickFormat(d3.timeFormat('%b %d')));
    g.append('g').call(d3.axisLeft(y).ticks(4).tickFormat(normalized ? d3.format('.0%') : d3.format('d')));

    g.selectAll('path').data(stacked).join('path').attr('clip-path', `url(#${clipId})`).attr('fill', d => color(d.key)).attr('opacity', 0.85).attr('d', area);

    const legend = g.append('g').attr('transform', `translate(${innerW + 6},0)`);
    keysArr.forEach((k, i) => {
        legend.append('rect').attr('y', i * 16).attr('width', 10).attr('height', 10).attr('fill', color(k));
        legend.append('text').attr('x', 14).attr('y', i * 16 + 9).attr('font-size', 10).attr('fill', '#4a5568').text(keyFormatter(k));
    });
}

export function renderFormatMixOverTime(container, stackData) {
    if (!stackData?.keys?.length) {
        renderEmpty(container);
        return;
    }
    const fmt = k => k.charAt(0).toUpperCase() + k.slice(1);
    renderStackedArea(container, stackData, stackData.keys, true, fmt);
}

export function renderFunnelMixOverTime(container, data) {
    if (!data || data.length === 0) {
        renderEmpty(container);
        return;
    }
    renderStackedArea(container, { keys: ['tofu', 'mofu', 'bofu'], data }, ['tofu', 'mofu', 'bofu'], true, k => k.toUpperCase());
}

/**
 * Render hook x funnel grouped bar (chart 6)
 */
export function renderHookFunnel(container, prep) {
    const el = typeof container === 'string' ? document.getElementById(container) : container;
    if (!el || !window.d3) {
        renderEmpty(el, 'Chart unavailable');
        return;
    }
    el.innerHTML = '';
    if (!prep || !prep.hooks?.length) {
        renderEmpty(el);
        return;
    }
    const d3 = window.d3;
    const width = Math.max(200, el.clientWidth || 280);
    const height = 180;
    const margin = { top: 12, right: 12, bottom: 60, left: 36 };
    const innerW = width - margin.left - margin.right;
    const innerH = height - margin.top - margin.bottom;

    const stages = prep.stages || ['tofu', 'mofu', 'bofu'];
    const x0 = d3.scaleBand().domain(prep.hooks).range([0, innerW]).padding(0.2);
    const x1 = d3.scaleBand().domain(stages).range([0, x0.bandwidth()]).padding(0.05);
    const y = d3.scaleLinear().domain([0, d3.max(prep.hooks.map(h => stages.reduce((s, st) => s + (prep.counts[`${h}|${st}`] || 0), 0))) || 1]).nice().range([innerH, 0]);
    const color = d3.scaleOrdinal(stages, [MRI_CHART_COLORS[2], MRI_CHART_COLORS[3], MRI_CHART_COLORS[4]]);

    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height).attr('viewBox', `0 0 ${width} ${height}`);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    g.append('g').attr('transform', `translate(0,${innerH})`).call(d3.axisBottom(x0).tickValues(prep.hooks.slice(0, 8))).selectAll('text').attr('transform', 'rotate(-35)').style('text-anchor', 'end');
    g.append('g').call(d3.axisLeft(y).ticks(4));

    prep.hooks.slice(0, 10).forEach(h => {
        const grp = g.append('g').attr('transform', `translate(${x0(h)},0)`);
        stages.forEach(st => {
            const v = prep.counts[`${h}|${st}`] || 0;
            grp.append('rect').attr('x', x1(st)).attr('y', y(v)).attr('width', x1.bandwidth()).attr('height', innerH - y(v)).attr('fill', color(st));
        });
    });
}

// ─── v2 Charts: Dimensions ──────────────────────────────────────────────────

/** Dimension labels for display */
const DIMENSION_LABELS = {
    reading_level: 'Reading Level',
    claim_to_proof_ratio: 'Claim:Proof Ratio',
    proof_specificity: 'Proof Specificity',
    belief_count: 'Belief Count',
    product_timing: 'Product Timing',
    specificity_score: 'Specificity',
    close_pattern_variety: 'Close Variety',
    close_anti_patterns: 'Close Anti-Patterns',
    qualifier_density: 'Qualifier Density',
    social_context_density: 'Social Context',
    emotional_dimensionality: 'Emotional Depth',
    conversational_markers: 'Conversational Tone',
    pain_benefit_balance: 'Pain/Benefit Balance',
};

/** Dimension display order (highest-weighted first) */
const DIMENSION_ORDER = [
    'specificity_score',
    'claim_to_proof_ratio',
    'proof_specificity',
    'belief_count',
    'close_anti_patterns',
    'pain_benefit_balance',
    'reading_level',
    'emotional_dimensionality',
    'qualifier_density',
    'social_context_density',
    'product_timing',
    'conversational_markers',
    'close_pattern_variety',
];

/**
 * Render 13-dimension horizontal bar chart (chart 7)
 * @param {HTMLElement|string} container
 * @param {Object} dimensions - from batch_synthesis.dimensions: { name: { score, finding } }
 */
export function renderDimensionBars(container, dimensions) {
    const el = typeof container === 'string' ? document.getElementById(container) : container;
    if (!el || !window.d3) {
        renderEmpty(el, 'Chart unavailable');
        return;
    }
    el.innerHTML = '';
    if (!dimensions || Object.keys(dimensions).length === 0) {
        renderEmpty(el);
        return;
    }

    const d3 = window.d3;
    const data = DIMENSION_ORDER
        .filter(name => dimensions[name])
        .map(name => ({
            name,
            label: DIMENSION_LABELS[name] || name,
            score: dimensions[name].score || 0,
        }));

    if (data.length === 0) {
        renderEmpty(el);
        return;
    }

    const width = Math.max(300, el.clientWidth || 400);
    const barHeight = 22;
    const gap = 4;
    const height = data.length * (barHeight + gap) + 20;
    const margin = { top: 8, right: 50, bottom: 8, left: 150 };
    const innerW = width - margin.left - margin.right;

    const svg = d3.select(el).append('svg')
        .attr('width', width)
        .attr('height', height)
        .attr('viewBox', `0 0 ${width} ${height}`);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const x = d3.scaleLinear().domain([0, 100]).range([0, innerW]);

    data.forEach((d, i) => {
        const y = i * (barHeight + gap);

        // Label
        g.append('text')
            .attr('x', -8)
            .attr('y', y + barHeight / 2 + 1)
            .attr('text-anchor', 'end')
            .attr('font-size', 11)
            .attr('fill', '#4a5568')
            .attr('dominant-baseline', 'middle')
            .text(d.label);

        // Background bar
        g.append('rect')
            .attr('x', 0)
            .attr('y', y)
            .attr('width', innerW)
            .attr('height', barHeight)
            .attr('fill', '#edf2f7')
            .attr('rx', 3);

        // Score bar
        g.append('rect')
            .attr('x', 0)
            .attr('y', y)
            .attr('width', x(d.score))
            .attr('height', barHeight)
            .attr('fill', dimensionColor(d.score))
            .attr('rx', 3)
            .attr('opacity', 0.85);

        // Score text
        g.append('text')
            .attr('x', x(d.score) + 6)
            .attr('y', y + barHeight / 2 + 1)
            .attr('font-size', 11)
            .attr('font-weight', 600)
            .attr('fill', '#2d3748')
            .attr('dominant-baseline', 'middle')
            .text(d.score);
    });
}

/**
 * Render top-3 and bottom-3 findings (chart 8)
 * @param {HTMLElement|string} container
 * @param {Object} batchSynthesis - full batch_synthesis object
 */
export function renderTopBottomFindings(container, batchSynthesis) {
    const el = typeof container === 'string' ? document.getElementById(container) : container;
    if (!el) return;

    const top3 = batchSynthesis?.top_3 || [];
    const bottom3 = batchSynthesis?.bottom_3 || [];

    if (top3.length === 0 && bottom3.length === 0) {
        renderEmpty(el);
        return;
    }

    const renderCard = (item, type) => {
        const label = DIMENSION_LABELS[item.dimension] || item.dimension;
        const color = type === 'strength' ? '#10B981' : '#EF4444';
        const bgColor = type === 'strength' ? '#f0fdf4' : '#fef2f2';
        const icon = type === 'strength' ? '\u2191' : '\u2193';
        return `
            <div style="padding:12px 16px;border-left:3px solid ${color};background:${bgColor};border-radius:0 8px 8px 0;margin-bottom:8px;">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                    <span style="font-size:14px;color:${color};font-weight:700;">${icon} ${item.score}/100</span>
                    <span style="font-size:12px;color:#718096;font-weight:600;">${label}</span>
                </div>
                <div style="font-size:13px;color:#2d3748;line-height:1.5;">${item.finding || ''}</div>
            </div>`;
    };

    let html = '';
    if (bottom3.length > 0) {
        html += '<div style="margin-bottom:16px;"><div style="font-size:11px;font-weight:700;color:#EF4444;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">Biggest Leaks</div>';
        bottom3.forEach(item => { html += renderCard(item, 'leak'); });
        html += '</div>';
    }
    if (top3.length > 0) {
        html += '<div><div style="font-size:11px;font-weight:700;color:#10B981;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">Top Strengths</div>';
        top3.forEach(item => { html += renderCard(item, 'strength'); });
        html += '</div>';
    }

    el.innerHTML = html;
}

/**
 * Render all MRI charts into their containers
 * @param {Object} report - Full report from pipeline
 */
export function renderAllMriCharts(report) {
    const ads = getAdsForCharts(report);
    if (ads.length === 0) return;

    // Charts 1-6: temporal/structural (unchanged)
    const launchData = prepLaunchCadence(ads);
    const rotationData = prepRotationDepth(ads);
    const halfLifeDays = prepCreativeHalfLife(ads);
    const formatData = prepFormatMixOverTime(ads);
    const funnelData = prepFunnelMixOverTime(ads);
    const hookFunnelPrep = prepHookFunnel(ads);

    renderLaunchCadence('mriChartLaunchCadence', launchData, 'launches');
    renderLaunchCadence('mriChartRotationDepth', rotationData, 'active creatives');
    renderCreativeHalfLife('mriChartHalfLife', halfLifeDays);
    renderFormatMixOverTime('mriChartFormatMix', formatData);
    renderFunnelMixOverTime('mriChartFunnelMix', funnelData);
    renderHookFunnel('mriChartHookFunnel', hookFunnelPrep);

    // Charts 7-8: v2 dimension charts (from batch_synthesis)
    const synth = report?.batch_synthesis;
    if (synth) {
        renderDimensionBars('mriChartDimensions', synth.dimensions);
        renderTopBottomFindings('mriChartFindings', synth);
    } else {
        // Legacy v1 fallback — render empty for new chart containers
        renderEmpty('mriChartDimensions', 'Dimension scores not available (v1 report)');
        renderEmpty('mriChartFindings', 'Findings not available (v1 report)');
    }
}
