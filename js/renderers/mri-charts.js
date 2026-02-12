/**
 * MRI Charts Renderer
 * D3 visualizations for Creative MRI report: launch cadence, rotation depth,
 * creative half-life, format/funnel mix over time, hook×funnel, hook quality, copy tradeoff.
 */

const MRI_CHART_COLORS = [
    '#8B5CF6', '#EC4899', '#F59E0B', '#10B981', '#3B82F6', '#F97316',
    '#EF4444', '#14B8A6', '#6366F1', '#74c7e8', '#6fd4a1',
];

/**
 * Parse date strings from Meta format ("Jan 15, 2024") or ISO
 * @param {string} s
 * @returns {Date|null}
 */
function parseDate(s) {
    if (!s) return null;
    if (typeof s !== 'string') return s instanceof Date ? s : null;
    const d = new Date(s);
    return isNaN(d.getTime()) ? null : d;
}

/**
 * Get start of week (Monday) for a date
 * @param {Date} d
 * @returns {string} ISO week key "YYYY-MM-DD"
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
 * @param {Object} report
 * @returns {Array}
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
            scores: a.llm?.hook_scores || { specificity: 50, emotional_pull: 50, overall: a.overall_score || 50 },
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

/** Prep chart 2: active creatives per week (between start and end) */
function prepRotationDepth(ads) {
    const byWeek = {};
    ads.forEach(a => {
        const start = parseDate(a.ad_delivery_start_time || a.started_running_on);
        const end = parseDate(a.ad_delivery_end_time || a.ad_delivery_start_time || a.started_running_on);
        if (!start) return;
        const endDate = end || start;
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
    const days = [];
    ads.forEach(a => {
        const start = parseDate(a.ad_delivery_start_time || a.started_running_on);
        const end = parseDate(a.ad_delivery_end_time || a.ad_delivery_start_time);
        if (!start || !end) return;
        const diff = Math.round((end - start) / (1000 * 60 * 60 * 24));
        if (diff >= 0) days.push(diff);
    });
    return days;
}

/** Prep chart 4: format mix by week (stacked) */
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
    const formats = new Set();
    Object.values(byWeek).forEach(w => Object.keys(w).forEach(k => formats.add(k)));
    return {
        keys: Array.from(formats).sort(),
        data: Object.entries(byWeek)
            .map(([week, counts]) => {
                const row = { week, date: new Date(week) };
                formats.forEach(f => { row[f] = counts[f] || 0; });
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

/** Prep chart 6: hook × funnel counts */
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

/** Prep chart 7 & 8: points for beeswarm / scatter */
function prepHookScores(ads) {
    return ads
        .map(a => {
            const h = (a.hook?.hook_types?.[0]?.type || a.hook_type || 'unknown').toLowerCase();
            const scores = a.hook?.scores || a.llm?.hook_scores || {};
            const overall = +scores.overall || +a.overall_score || 50;
            const specificity = +scores.specificity || 50;
            const emotional_pull = +scores.emotional_pull || 50;
            return { hook_type: h, overall, specificity, emotional_pull, ad_id: a.ad_id || a.id };
        })
        .filter(p => p.hook_type && p.hook_type !== 'unknown');
}

function renderEmpty(container, msg = 'No data available') {
    if (!container) return;
    const el = typeof container === 'string' ? document.getElementById(container) : container;
    if (!el) return;
    el.innerHTML = `<div class="mri-chart-empty" style="padding:24px;text-align:center;color:var(--muted,#718096);font-size:13px;">${msg}</div>`;
}

/**
 * Render D3 line chart (charts 1 & 2)
 * @param {HTMLElement|string} container
 * @param {Array} data [{date, count}, ...]
 * @param {string} yLabel
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
function renderStackedArea(container, data, keys, normalized = false) {
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
        keysArr.forEach(k => { if (out[k] == null) out[k] = 0; });
        return out;
    }));

    const x = d3.scaleTime().domain(d3.extent(arr, d => d.date)).range([0, innerW]);
    const y = d3.scaleLinear().domain(normalized ? [0, 1] : [0, d3.max(stacked, s => d3.max(s, d => d[1]))]).range([innerH, 0]);

    const area = d3.area().x(d => x(d.data.date)).y0(d => y(d[0])).y1(d => y(d[1]));
    const color = d3.scaleOrdinal(keysArr, MRI_CHART_COLORS);

    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height).attr('viewBox', `0 0 ${width} ${height}`);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    g.append('g').attr('transform', `translate(0,${innerH})`).call(d3.axisBottom(x).ticks(5).tickFormat(d3.timeFormat('%b %d')));
    g.append('g').call(d3.axisLeft(y).ticks(4).tickFormat(normalized ? d3.format('.0%') : d3.format('d')));

    g.selectAll('path').data(stacked).join('path').attr('fill', d => color(d.key)).attr('opacity', 0.85).attr('d', area);

    const legend = g.append('g').attr('transform', `translate(${innerW + 6},0)`);
    keysArr.forEach((k, i) => {
        legend.append('rect').attr('y', i * 16).attr('width', 10).attr('height', 10).attr('fill', color(k));
        legend.append('text').attr('x', 14).attr('y', i * 16 + 9).attr('font-size', 10).attr('fill', '#4a5568').text(k);
    });
}

/**
 * Render format mix over time (chart 4)
 */
export function renderFormatMixOverTime(container, stackData) {
    renderStackedArea(container, stackData, stackData?.keys, false);
}

/**
 * Render funnel mix over time (chart 5) - normalized
 */
export function renderFunnelMixOverTime(container, data) {
    if (!data || data.length === 0) {
        renderEmpty(container);
        return;
    }
    renderStackedArea(container, { keys: ['tofu', 'mofu', 'bofu'], data }, ['tofu', 'mofu', 'bofu'], true);
}

/**
 * Render hook × funnel grouped bar (chart 6)
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

/**
 * Render hook quality strip/beeswarm (chart 7)
 */
export function renderHookQuality(container, points) {
    const el = typeof container === 'string' ? document.getElementById(container) : container;
    if (!el || !window.d3) {
        renderEmpty(el, 'Chart unavailable');
        return;
    }
    el.innerHTML = '';
    if (!points || points.length === 0) {
        renderEmpty(el);
        return;
    }
    const d3 = window.d3;
    const width = Math.max(200, el.clientWidth || 280);
    const height = 180;
    const margin = { top: 12, right: 12, bottom: 40, left: 36 };
    const innerW = width - margin.left - margin.right;
    const innerH = height - margin.top - margin.bottom;

    const hooks = [...new Set(points.map(p => p.hook_type))].sort();
    const x = d3.scalePoint().domain(hooks).range([0, innerW]).padding(0.3);
    const y = d3.scaleLinear().domain([0, 100]).range([innerH, 0]);

    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height).attr('viewBox', `0 0 ${width} ${height}`);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    g.append('g').attr('transform', `translate(0,${innerH})`).call(d3.axisBottom(x).tickValues(hooks.slice(0, 8)));
    g.append('g').call(d3.axisLeft(y).ticks(5));

    const jitter = () => (Math.random() - 0.5) * (x.step() * 0.6);
    g.selectAll('circle').data(points).join('circle').attr('cx', d => x(d.hook_type) + jitter()).attr('cy', d => y(d.overall)).attr('r', 4).attr('fill', MRI_CHART_COLORS[5]).attr('opacity', 0.7);
}

/**
 * Render copy tradeoff scatter: specificity vs emotional_pull (chart 8)
 */
export function renderCopyTradeoff(container, points) {
    const el = typeof container === 'string' ? document.getElementById(container) : container;
    if (!el || !window.d3) {
        renderEmpty(el, 'Chart unavailable');
        return;
    }
    el.innerHTML = '';
    if (!points || points.length === 0) {
        renderEmpty(el);
        return;
    }
    const d3 = window.d3;
    const width = Math.max(200, el.clientWidth || 280);
    const height = 180;
    const margin = { top: 12, right: 12, bottom: 28, left: 36 };
    const innerW = width - margin.left - margin.right;
    const innerH = height - margin.top - margin.bottom;

    const x = d3.scaleLinear().domain([0, 100]).nice().range([0, innerW]);
    const y = d3.scaleLinear().domain([0, 100]).nice().range([innerH, 0]);

    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height).attr('viewBox', `0 0 ${width} ${height}`);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    g.append('g').attr('transform', `translate(0,${innerH})`).call(d3.axisBottom(x)).append('text').attr('x', innerW / 2).attr('y', 22).attr('fill', '#718096').attr('text-anchor', 'middle').style('font-size', '10px').text('Specificity');
    g.append('g').call(d3.axisLeft(y)).append('text').attr('transform', 'rotate(-90)').attr('y', -24).attr('x', -innerH / 2).attr('fill', '#718096').attr('text-anchor', 'middle').style('font-size', '10px').text('Emotional pull');

    g.selectAll('circle').data(points).join('circle').attr('cx', d => x(d.specificity)).attr('cy', d => y(d.emotional_pull)).attr('r', 5).attr('fill', MRI_CHART_COLORS[6]).attr('opacity', 0.7);
}

/**
 * Render all 8 MRI charts into their containers
 * @param {Object} report - Full report from pipeline
 */
export function renderAllMriCharts(report) {
    const ads = getAdsForCharts(report);
    if (ads.length === 0) return;

    const launchData = prepLaunchCadence(ads);
    const rotationData = prepRotationDepth(ads);
    const halfLifeDays = prepCreativeHalfLife(ads);
    const formatData = prepFormatMixOverTime(ads);
    const funnelData = prepFunnelMixOverTime(ads);
    const hookFunnelPrep = prepHookFunnel(ads);
    const hookScoresData = prepHookScores(ads);

    renderLaunchCadence('mriChartLaunchCadence', launchData, 'launches');
    renderLaunchCadence('mriChartRotationDepth', rotationData, 'active creatives');
    renderCreativeHalfLife('mriChartHalfLife', halfLifeDays);
    renderFormatMixOverTime('mriChartFormatMix', formatData);
    renderFunnelMixOverTime('mriChartFunnelMix', funnelData);
    renderHookFunnel('mriChartHookFunnel', hookFunnelPrep);
    renderHookQuality('mriChartHookQuality', hookScoresData);
    renderCopyTradeoff('mriChartCopyTradeoff', hookScoresData);
}
