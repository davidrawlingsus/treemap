/**
 * Chart Renderer
 * Handles bar chart, topics chart, and horizontal bar chart rendering
 */

/**
 * Generate category color palette
 * @returns {Object} Color map
 */
export function generateCategoryColorPalette() {
    return {
        'GENERAL INFORMATION': '#A98CFD',
        'BOOKING/PRICE': '#74C7E8',
        'TOUR/ITINERARY': '#6FD4A1',
        'ACCOMMODATION': '#F4A85B',
        'FLIGHTS': '#F07D8C',
        'AVAILABILITY': '#B794F6',
        'TRAVELLER DETAILS': '#77D9D6',
        'HELP': '#FFB366',
        'NPD': '#9A7B6C'
    };
}

/**
 * Adjust color lightness
 * @param {string} color - Hex color
 * @param {number} percent - Lightness adjustment percent
 * @returns {string} Adjusted color
 */
export function adjustColorLightness(color, percent) {
    const num = parseInt(color.replace('#', ''), 16);
    const amt = Math.round(2.55 * percent);
    const R = Math.min(255, Math.max(0, (num >> 16) + amt));
    const G = Math.min(255, Math.max(0, ((num >> 8) & 0x00FF) + amt));
    const B = Math.min(255, Math.max(0, (num & 0x0000FF) + amt));
    return '#' + ((1 << 24) + (R << 16) + (G << 8) + B).toString(16).slice(1);
}

/**
 * Process raw data into bar chart format
 * @param {Array} rawData - Raw data array
 * @returns {Object} { categories, totalTopicInstances }
 */
export function processBarChartData(rawData) {
    const categoryMap = new Map();
    let totalTopicInstances = 0;

    rawData.forEach(row => {
        const topics = row.topics || [];
        topics.forEach(topic => {
            if (!topic.category) return;

            totalTopicInstances++;

            if (!categoryMap.has(topic.category)) {
                categoryMap.set(topic.category, {
                    name: topic.category,
                    count: 0,
                    topics: new Map()
                });
            }

            const category = categoryMap.get(topic.category);
            category.count++;

            if (!category.topics.has(topic.label)) {
                category.topics.set(topic.label, {
                    name: topic.label,
                    count: 0,
                    verbatims: []
                });
            }

            const topicData = category.topics.get(topic.label);
            topicData.count++;
            
            topicData.verbatims.push({
                text: row.text || '',
                sentiment: row.sentiment || 'neutral',
                index: row.row_id,
                country: row.metadata?.country || '',
                city: row.metadata?.city || '',
                date: row.metadata?.created_at || '',
                ...(row.metadata || {})
            });
        });
    });

    const categories = Array.from(categoryMap.values()).map(cat => ({
        name: cat.name,
        count: cat.count,
        percent: (cat.count / totalTopicInstances) * 100,
        topics: Array.from(cat.topics.values()).map(topic => ({
            name: topic.name,
            count: topic.count,
            percent: (topic.count / totalTopicInstances) * 100,
            verbatims: topic.verbatims
        })).sort((a, b) => b.count - a.count)
    })).sort((a, b) => b.count - a.count);

    return { categories, totalTopicInstances };
}

/**
 * Process raw data into topics chart format
 * @param {Array} rawData - Raw data array
 * @returns {Object} { topics, totalTopicInstances }
 */
export function processTopicsData(rawData) {
    const topicsMap = new Map();
    let totalTopicInstances = 0;

    rawData.forEach(row => {
        const topics = row.topics || [];
        topics.forEach(topic => {
            if (!topic.label) return;

            totalTopicInstances++;

            if (!topicsMap.has(topic.label)) {
                topicsMap.set(topic.label, {
                    name: topic.label,
                    category: topic.category || 'Unknown',
                    count: 0,
                    verbatims: []
                });
            }

            const topicData = topicsMap.get(topic.label);
            topicData.count++;
            
            topicData.verbatims.push({
                text: row.text || '',
                sentiment: row.sentiment || 'neutral',
                index: row.row_id,
                country: row.metadata?.country || '',
                city: row.metadata?.city || '',
                date: row.metadata?.created_at || '',
                ...(row.metadata || {})
            });
        });
    });

    const topics = Array.from(topicsMap.values()).map(topic => ({
        name: topic.name,
        category: topic.category,
        count: topic.count,
        percent: (topic.count / totalTopicInstances) * 100,
        verbatims: topic.verbatims
    })).sort((a, b) => b.count - a.count);

    return { topics, totalTopicInstances };
}

/**
 * Toggle category expansion in bar chart
 * @param {string} categoryId - Category element ID
 * @param {HTMLElement} toggleButton - Toggle button element
 */
export function toggleCategory(categoryId, toggleButton) {
    const panel = document.getElementById(categoryId);
    const barsPanel = document.getElementById(categoryId + '-bars');

    if (panel && panel.hasAttribute('hidden')) {
        panel.removeAttribute('hidden');
        if (barsPanel) barsPanel.removeAttribute('hidden');
        toggleButton.textContent = '−';
        toggleButton.setAttribute('aria-expanded', 'true');
    } else if (panel) {
        panel.setAttribute('hidden', '');
        if (barsPanel) barsPanel.setAttribute('hidden', '');
        toggleButton.textContent = '+';
        toggleButton.setAttribute('aria-expanded', 'false');
    }
}

/**
 * Create gridlines for chart
 * @param {HTMLElement} container - Container element
 */
function createGridlines(container) {
    const gridlinesContainer = document.createElement('div');
    gridlinesContainer.className = 'gridlines';
    const ticks = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100];
    ticks.forEach(tick => {
        const line = document.createElement('div');
        line.className = 'gridline';
        line.style.left = `${tick}%`;
        gridlinesContainer.appendChild(line);
    });
    container.appendChild(gridlinesContainer);
    return ticks;
}

/**
 * Create axis labels for chart
 * @param {HTMLElement} container - Container element
 * @param {Array} ticks - Tick values
 */
function createAxisLabels(container, ticks) {
    const axisContainer = document.createElement('div');
    axisContainer.className = 'axis--bottom';
    ticks.forEach(tick => {
        const label = document.createElement('span');
        label.className = 'axis__label';
        label.style.left = `${tick}%`;
        label.textContent = `${tick}%`;
        axisContainer.appendChild(label);
    });
    container.appendChild(axisContainer);
}

/**
 * Render horizontal bar chart for multi-choice and numeric question types
 * @param {Array} data - Chart data
 * @param {string} containerId - Container element ID prefix
 * @param {number} totalCount - Total count for percentage calculation
 * @param {boolean} isMultiChoice - Whether this is a multi-choice chart
 */
export function renderHorizontalBarChart(data, containerId, totalCount, isMultiChoice = false) {
    const labelsContainer = document.getElementById(`${containerId}Labels`);
    const barsContainer = document.getElementById(`${containerId}Bars`);
    
    if (!labelsContainer || !barsContainer) {
        console.error(`Containers not found for ${containerId}`);
        return;
    }
    
    labelsContainer.innerHTML = '';
    barsContainer.innerHTML = '';
    
    if (!data || data.length === 0) {
        labelsContainer.innerHTML = '<div style="padding: 20px; text-align: center; color: #999;">No data available</div>';
        return;
    }
    
    const maxPercent = Math.max(...data.map(item => item.percent));
    const scale = maxPercent > 0 ? 100 / maxPercent : 1;
    
    const ticks = createGridlines(barsContainer);
    
    const barsContent = document.createElement('div');
    barsContent.style.position = 'relative';
    barsContent.style.zIndex = '1';
    barsContainer.appendChild(barsContent);
    
    createAxisLabels(barsContainer, ticks);
    
    const categoryColors = window.colorSchemesCATEGORY_COLORS || [
        '#A97FFF', '#77D9D6', '#F8A04C', '#58B3F0', '#6ED49B', '#F47280', '#9A7B6C', '#FFB366', '#B794F6', '#4ECDC4'
    ];
    
    data.forEach((item, index) => {
        const baseColor = categoryColors[index % categoryColors.length];
        
        // Labels
        const labelRow = document.createElement('div');
        labelRow.className = 'topic';
        labelRow.style.marginBottom = '6px';
        
        const labelWrapper = document.createElement('div');
        labelWrapper.className = 'topic__label-wrapper';
        labelWrapper.style.width = '240px';
        labelWrapper.style.paddingLeft = '0';
        
        const bullet = document.createElement('div');
        bullet.className = 'bullet';
        bullet.style.background = baseColor;
        bullet.style.opacity = '0.6';
        
        const label = document.createElement('div');
        label.className = 'topic__label';
        label.textContent = item.label || item.name;
        
        labelWrapper.appendChild(bullet);
        labelWrapper.appendChild(label);
        labelRow.appendChild(labelWrapper);
        labelsContainer.appendChild(labelRow);
        
        // Bars
        const barRow = document.createElement('div');
        barRow.className = 'topic__bar-container';
        barRow.style.marginBottom = '6px';
        
        const track = document.createElement('div');
        track.className = 'bar__track';
        
        const fill = document.createElement('div');
        fill.className = 'bar__fill';
        fill.style.background = baseColor;
        fill.style.width = '0%';
        
        const barWidthPercent = (item.percent / maxPercent) * 100;
        
        const value = document.createElement('div');
        value.textContent = `${item.percent.toFixed(1)}%`;
        
        const estimatedLabelWidth = 40;
        const containerWidth = barsContainer.clientWidth || 600;
        const barWidthPixels = (barWidthPercent / 100) * containerWidth;
        
        if (barWidthPixels > estimatedLabelWidth + 16) {
            value.className = 'bar__value bar__value--inside';
            fill.appendChild(value);
        } else {
            value.className = 'bar__value bar__value--outside';
            value.style.left = `${barWidthPercent}%`;
            barRow.appendChild(value);
        }
        
        setTimeout(() => {
            fill.style.width = `${barWidthPercent}%`;
        }, 50 + index * 20);
        
        barRow.appendChild(track);
        barRow.appendChild(fill);
        barsContent.appendChild(barRow);
    });
}

/**
 * Render bar chart with categories and topics
 * @param {Object} options - Rendering options
 * @param {Array} options.rawData - Raw data array
 * @param {Function} options.showVerbatims - Function to show verbatims
 * @param {Function} options.showContextMenu - Function to show context menu
 * @param {Function} options.getDimensionDisplayName - Function to get dimension name
 * @param {string} options.currentProjectName - Current project name
 * @param {string} options.currentDataSourceId - Current data source ID
 * @param {string} options.currentQuestionRefKey - Current question ref key
 */
export function renderBarChart(options = {}) {
    const {
        rawData = [],
        showVerbatims,
        showContextMenu,
        getDimensionDisplayName,
        currentProjectName,
        currentDataSourceId,
        currentQuestionRefKey
    } = options;
    
    const { categories, totalTopicInstances } = processBarChartData(rawData);
    const colorPalette = generateCategoryColorPalette();
    
    const totalCountEl = document.getElementById('totalCount');
    if (totalCountEl) totalCountEl.textContent = totalTopicInstances;

    const maxPercent = Math.max(...categories.map(c => c.percent));
    
    const labelsContainer = document.getElementById('barChartLabels');
    const barsContainer = document.getElementById('barChartBars');
    
    if (!labelsContainer || !barsContainer) return;
    
    labelsContainer.innerHTML = '';
    barsContainer.innerHTML = '';

    const ticks = createGridlines(barsContainer);
    
    const barsContent = document.createElement('div');
    barsContent.style.position = 'relative';
    barsContent.style.zIndex = '1';
    barsContainer.appendChild(barsContent);
    
    createAxisLabels(barsContainer, ticks);

    const categoryColorsLocal = window.colorSchemesCATEGORY_COLORS || [
        '#A97FFF', '#77D9D6', '#F8A04C', '#58B3F0', '#6ED49B', '#F47280', '#9A7B6C', '#FFB366', '#B794F6', '#4ECDC4'
    ];
    
    const getDimNameFn = getDimensionDisplayName || window.getDimensionDisplayName || ((key) => key);
    const showVerbatimsFn = showVerbatims || window.showVerbatims;
    const showCtxMenuFn = showContextMenu || window.showContextMenu;
    
    categories.forEach((category, catIndex) => {
        const categoryId = `cat-${catIndex}`;
        const baseColor = colorPalette[category.name] || categoryColorsLocal[catIndex % categoryColorsLocal.length];

        const collectAllCategoryVerbatims = () => {
            const allVerbatims = [];
            category.topics.forEach(topic => {
                if (topic.verbatims && Array.isArray(topic.verbatims)) {
                    allVerbatims.push(...topic.verbatims);
                }
            });
            return allVerbatims;
        };

        // Labels column
        const labelGroup = document.createElement('div');
        labelGroup.className = 'group';

        const headerRow = document.createElement('div');
        headerRow.className = 'group__header';
        headerRow.style.cursor = 'pointer';

        const toggle = document.createElement('button');
        toggle.className = 'toggle';
        toggle.setAttribute('aria-expanded', 'false');
        toggle.setAttribute('aria-controls', categoryId);
        toggle.textContent = '+';
        toggle.onclick = (e) => {
            e.stopPropagation();
            toggleCategory(categoryId, toggle);
        };

        headerRow.onclick = (e) => {
            if (e.target === toggle || toggle.contains(e.target)) return;
            const allVerbatims = collectAllCategoryVerbatims();
            if (allVerbatims.length > 0 && showVerbatimsFn) {
                showVerbatimsFn(allVerbatims, category.name, category.name);
            }
        };
        
        headerRow.oncontextmenu = (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (showCtxMenuFn) {
                showCtxMenuFn(e, {
                    type: 'category',
                    category: category.name,
                    project_name: currentProjectName,
                    data_source: currentDataSourceId,
                    dimension_ref: currentQuestionRefKey,
                    dimension_name: currentQuestionRefKey ? getDimNameFn(currentQuestionRefKey) : null,
                });
            }
        };
        
        headerRow.setAttribute('role', 'button');
        headerRow.setAttribute('tabindex', '0');
        headerRow.setAttribute('aria-label', `View all conversations in ${category.name}`);
        headerRow.onkeydown = (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                const allVerbatims = collectAllCategoryVerbatims();
                if (allVerbatims.length > 0 && showVerbatimsFn) {
                    showVerbatimsFn(allVerbatims, category.name, category.name);
                }
            }
        };

        const labelWrapper = document.createElement('div');
        labelWrapper.className = 'group__label-wrapper';

        const label = document.createElement('div');
        label.className = 'group__label';
        label.textContent = category.name;

        labelWrapper.appendChild(label);
        headerRow.appendChild(toggle);
        headerRow.appendChild(labelWrapper);
        labelGroup.appendChild(headerRow);

        // Topics panel
        const panel = document.createElement('div');
        panel.className = 'group__panel';
        panel.id = categoryId;
        panel.setAttribute('hidden', '');
        panel.setAttribute('role', 'region');
        panel.setAttribute('aria-labelledby', categoryId + '-label');
        panel.setAttribute('data-category-id', categoryId);

        category.topics.forEach((topic, topicIndex) => {
            const topicRow = document.createElement('div');
            topicRow.className = 'topic';
            
            topicRow.onclick = () => {
                if (showVerbatimsFn) showVerbatimsFn(topic.verbatims, topic.name, category.name);
            };
            
            topicRow.oncontextmenu = (e) => {
                e.preventDefault();
                e.stopPropagation();
                if (showCtxMenuFn) {
                    showCtxMenuFn(e, {
                        type: 'topic',
                        category: category.name,
                        topic_label: topic.name,
                        project_name: currentProjectName,
                        data_source: currentDataSourceId,
                        dimension_ref: currentQuestionRefKey,
                        dimension_name: currentQuestionRefKey ? getDimNameFn(currentQuestionRefKey) : null,
                    });
                }
            };
            
            topicRow.setAttribute('role', 'button');
            topicRow.setAttribute('tabindex', '0');
            topicRow.setAttribute('aria-label', `View ${topic.count} conversations about ${topic.name}`);

            const topicLabelWrapper = document.createElement('div');
            topicLabelWrapper.className = 'topic__label-wrapper';
            topicLabelWrapper.style.width = '240px';

            const bullet = document.createElement('div');
            bullet.className = 'bullet';
            const topicColor = adjustColorLightness(baseColor, (topicIndex % 3 - 1) * 15);
            bullet.style.background = topicColor;
            bullet.style.opacity = '0.4';

            const topicLabel = document.createElement('div');
            topicLabel.className = 'topic__label';
            topicLabel.textContent = topic.name;

            topicLabelWrapper.appendChild(bullet);
            topicLabelWrapper.appendChild(topicLabel);
            topicRow.appendChild(topicLabelWrapper);
            panel.appendChild(topicRow);
            
            topicRow.onkeydown = (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    if (showVerbatimsFn) showVerbatimsFn(topic.verbatims, topic.name, category.name);
                }
            };
        });

        labelGroup.appendChild(panel);
        labelsContainer.appendChild(labelGroup);

        // Bars column
        const barGroup = document.createElement('div');
        barGroup.className = 'group';

        const barHeaderRow = document.createElement('div');
        barHeaderRow.className = 'group__header';
        barHeaderRow.style.cursor = 'pointer';
        
        barHeaderRow.onclick = () => {
            const allVerbatims = collectAllCategoryVerbatims();
            if (allVerbatims.length > 0 && showVerbatimsFn) {
                showVerbatimsFn(allVerbatims, category.name, category.name);
            }
        };
        
        barHeaderRow.oncontextmenu = (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (showCtxMenuFn) {
                showCtxMenuFn(e, {
                    type: 'category',
                    category: category.name,
                    project_name: currentProjectName,
                    data_source: currentDataSourceId,
                    dimension_ref: currentQuestionRefKey,
                    dimension_name: currentQuestionRefKey ? getDimNameFn(currentQuestionRefKey) : null,
                });
            }
        };

        const track = document.createElement('div');
        track.className = 'bar__track';

        const fill = document.createElement('div');
        fill.className = 'bar__fill';
        fill.style.background = baseColor;
        fill.style.width = '0%';

        const barWidthPercent = (category.percent / maxPercent) * 100;

        const value = document.createElement('div');
        value.textContent = `${category.percent.toFixed(1)}%`;

        const estimatedLabelWidth = 40;
        const containerWidth = barsContainer.clientWidth || 600;
        const barWidthPixels = (barWidthPercent / 100) * containerWidth;

        if (barWidthPixels > estimatedLabelWidth + 16) {
            value.className = 'bar__value bar__value--inside';
            fill.appendChild(value);
        } else {
            value.className = 'bar__value bar__value--outside';
            value.style.left = `${barWidthPercent}%`;
            barHeaderRow.appendChild(value);
        }

        setTimeout(() => {
            fill.style.width = `${barWidthPercent}%`;
        }, 50 + catIndex * 30);

        barHeaderRow.appendChild(track);
        barHeaderRow.appendChild(fill);
        barGroup.appendChild(barHeaderRow);

        // Topic bars panel
        const barsPanel = document.createElement('div');
        barsPanel.className = 'group__panel';
        barsPanel.id = categoryId + '-bars';
        barsPanel.setAttribute('hidden', '');
        barsPanel.setAttribute('data-category-id', categoryId + '-bars');

        category.topics.forEach((topic, topicIndex) => {
            const topicBarRow = document.createElement('div');
            topicBarRow.className = 'topic__bar-container';
            topicBarRow.style.cursor = 'pointer';
            
            topicBarRow.onclick = () => {
                if (showVerbatimsFn) showVerbatimsFn(topic.verbatims, topic.name, category.name);
            };
            
            topicBarRow.oncontextmenu = (e) => {
                e.preventDefault();
                e.stopPropagation();
                if (showCtxMenuFn) {
                    showCtxMenuFn(e, {
                        type: 'topic',
                        category: category.name,
                        topic_label: topic.name,
                        project_name: currentProjectName,
                        data_source: currentDataSourceId,
                        dimension_ref: currentQuestionRefKey,
                        dimension_name: currentQuestionRefKey ? getDimNameFn(currentQuestionRefKey) : null,
                    });
                }
            };

            const topicTrack = document.createElement('div');
            topicTrack.className = 'bar__track';

            const topicFill = document.createElement('div');
            topicFill.className = 'bar__fill';
            const topicColor = adjustColorLightness(baseColor, (topicIndex % 3 - 1) * 15);
            topicFill.style.background = topicColor;
            topicFill.style.width = '0%';

            const topicBarWidthPercent = (topic.percent / maxPercent) * 100;

            const topicValue = document.createElement('div');
            topicValue.textContent = `${topic.percent.toFixed(1)}%`;

            const topicBarWidthPixels = (topicBarWidthPercent / 100) * containerWidth;

            if (topicBarWidthPixels > estimatedLabelWidth + 16) {
                topicValue.className = 'bar__value bar__value--inside';
                topicFill.appendChild(topicValue);
            } else {
                topicValue.className = 'bar__value bar__value--outside';
                topicValue.style.left = `${topicBarWidthPercent}%`;
                topicBarRow.appendChild(topicValue);
            }

            setTimeout(() => {
                topicFill.style.width = `${topicBarWidthPercent}%`;
            }, 100 + catIndex * 30 + topicIndex * 20);

            topicBarRow.appendChild(topicTrack);
            topicBarRow.appendChild(topicFill);
            barsPanel.appendChild(topicBarRow);
        });

        barGroup.appendChild(barsPanel);
        barsContent.appendChild(barGroup);
    });
}

/**
 * Render topics chart (flat list of topics)
 * @param {Object} options - Rendering options
 * @param {Array} options.rawData - Raw data array
 * @param {Function} options.showVerbatims - Function to show verbatims
 * @param {Function} options.showContextMenu - Function to show context menu
 * @param {Function} options.getDimensionDisplayName - Function to get dimension name
 * @param {string} options.currentProjectName - Current project name
 * @param {string} options.currentDataSourceId - Current data source ID
 * @param {string} options.currentQuestionRefKey - Current question ref key
 */
export function renderTopicsChart(options = {}) {
    const {
        rawData = [],
        showVerbatims,
        showContextMenu,
        getDimensionDisplayName,
        currentProjectName,
        currentDataSourceId,
        currentQuestionRefKey
    } = options;
    
    const { topics, totalTopicInstances } = processTopicsData(rawData);
    const colorPalette = generateCategoryColorPalette();
    
    const topicsCountEl = document.getElementById('topicsCount');
    if (topicsCountEl) topicsCountEl.textContent = totalTopicInstances;

    const maxPercent = Math.max(...topics.map(t => t.percent));

    const labelsContainer = document.getElementById('topicsChartLabels');
    const barsContainer = document.getElementById('topicsChartBars');
    
    if (!labelsContainer || !barsContainer) return;
    
    labelsContainer.innerHTML = '';
    barsContainer.innerHTML = '';

    const ticks = createGridlines(barsContainer);
    
    const barsContent = document.createElement('div');
    barsContent.style.position = 'relative';
    barsContent.style.zIndex = '1';
    barsContainer.appendChild(barsContent);
    
    createAxisLabels(barsContainer, ticks);

    const categoryColorsLocal = window.colorSchemesCATEGORY_COLORS || [
        '#A97FFF', '#77D9D6', '#F8A04C', '#58B3F0', '#6ED49B', '#F47280', '#9A7B6C', '#FFB366', '#B794F6', '#4ECDC4'
    ];
    
    const getDimNameFn = getDimensionDisplayName || window.getDimensionDisplayName || ((key) => key);
    const showVerbatimsFn = showVerbatims || window.showVerbatims;
    const showCtxMenuFn = showContextMenu || window.showContextMenu;
    
    topics.forEach((topic, index) => {
        const baseColor = colorPalette[topic.category] || categoryColorsLocal[index % categoryColorsLocal.length];
        
        // Labels column
        const labelRow = document.createElement('div');
        labelRow.className = 'topic';
        labelRow.style.marginBottom = '6px';
        
        labelRow.onclick = () => {
            if (showVerbatimsFn) showVerbatimsFn(topic.verbatims, topic.name, topic.category);
        };
        
        labelRow.oncontextmenu = (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (showCtxMenuFn) {
                showCtxMenuFn(e, {
                    type: 'topic',
                    category: topic.category,
                    topic_label: topic.name,
                    project_name: currentProjectName,
                    data_source: currentDataSourceId,
                    dimension_ref: currentQuestionRefKey,
                    dimension_name: currentQuestionRefKey ? getDimNameFn(currentQuestionRefKey) : null,
                });
            }
        };
        
        labelRow.setAttribute('role', 'button');
        labelRow.setAttribute('tabindex', '0');
        labelRow.setAttribute('aria-label', `View ${topic.count} conversations about ${topic.name}`);

        const labelWrapper = document.createElement('div');
        labelWrapper.className = 'topic__label-wrapper';
        labelWrapper.style.width = '240px';
        labelWrapper.style.paddingLeft = '0';

        const bullet = document.createElement('div');
        bullet.className = 'bullet';
        bullet.style.background = baseColor;
        bullet.style.opacity = '0.6';

        const label = document.createElement('div');
        label.className = 'topic__label';
        label.textContent = topic.name;

        labelWrapper.appendChild(bullet);
        labelWrapper.appendChild(label);
        labelRow.appendChild(labelWrapper);
        labelsContainer.appendChild(labelRow);
        
        labelRow.onkeydown = (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                if (showVerbatimsFn) showVerbatimsFn(topic.verbatims, topic.name, topic.category);
            }
        };

        // Bars column
        const barRow = document.createElement('div');
        barRow.className = 'topic__bar-container';
        barRow.style.marginBottom = '6px';
        barRow.style.cursor = 'pointer';
        
        barRow.onclick = () => {
            if (showVerbatimsFn) showVerbatimsFn(topic.verbatims, topic.name, topic.category);
        };
        
        barRow.oncontextmenu = (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (showCtxMenuFn) {
                showCtxMenuFn(e, {
                    type: 'topic',
                    category: topic.category,
                    topic_label: topic.name,
                    project_name: currentProjectName,
                    data_source: currentDataSourceId,
                    dimension_ref: currentQuestionRefKey,
                    dimension_name: currentQuestionRefKey ? getDimNameFn(currentQuestionRefKey) : null,
                });
            }
        };

        const track = document.createElement('div');
        track.className = 'bar__track';

        const fill = document.createElement('div');
        fill.className = 'bar__fill';
        fill.style.background = baseColor;
        fill.style.width = '0%';
        
        const barWidthPercent = (topic.percent / maxPercent) * 100;
        
        const value = document.createElement('div');
        value.textContent = `${topic.percent.toFixed(1)}%`;
        
        const estimatedLabelWidth = 40;
        const containerWidth = barsContainer.clientWidth || 600;
        const barWidthPixels = (barWidthPercent / 100) * containerWidth;
        
        if (barWidthPixels > estimatedLabelWidth + 16) {
            value.className = 'bar__value bar__value--inside';
            fill.appendChild(value);
        } else {
            value.className = 'bar__value bar__value--outside';
            value.style.left = `${barWidthPercent}%`;
            barRow.appendChild(value);
        }

        setTimeout(() => {
            fill.style.width = `${barWidthPercent}%`;
        }, 50 + index * 20);

        barRow.appendChild(track);
        barRow.appendChild(fill);
        barsContent.appendChild(barRow);
    });
}
