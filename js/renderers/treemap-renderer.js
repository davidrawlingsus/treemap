/**
 * Treemap Renderer
 * Handles D3 treemap visualization rendering
 */

import { adjustBrightness } from '/js/utils/colors.js';

// Module-level state for dimensions
let width = 800;
let height = 600;
let resizeHandlerAttached = false;

/**
 * Get debounce function with fallback
 */
function getDebounce() {
    return window.debounce || ((fn, delay) => {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => fn(...args), delay);
        };
    });
}

/**
 * Get adjustBrightness function with fallback
 */
function getAdjustBrightness() {
    return adjustBrightness || window.adjustBrightness || ((color, amount) => {
        if (!color || amount === undefined) return color;
        const num = parseInt(color.replace('#', ''), 16);
        const amt = Math.round(amount * 2.55);
        const R = Math.min(255, Math.max(0, (num >> 16) + amt));
        const G = Math.min(255, Math.max(0, ((num >> 8) & 0x00FF) + amt));
        const B = Math.min(255, Math.max(0, (num & 0x0000FF) + amt));
        return '#' + (0x1000000 + (R << 16) + (G << 8) + B).toString(16).slice(1);
    });
}

/**
 * Collect all verbatims from a category
 * @param {Object} categoryData - Category data object
 * @returns {Array} - Array of verbatims
 */
function collectCategoryVerbatims(categoryData) {
    if (!categoryData) return [];
    const allVerbatims = [];
    if (categoryData.children && Array.isArray(categoryData.children)) {
        categoryData.children.forEach(topic => {
            if (topic && topic.verbatims && Array.isArray(topic.verbatims)) {
                allVerbatims.push(...topic.verbatims);
            }
        });
    }
    return allVerbatims;
}

/**
 * Render treemap visualization
 * @param {Object} data - Hierarchy data to render
 * @param {Object} options - Rendering options
 * @param {Object} options.colorSchemes - Color schemes object
 * @param {string} options.currentProjectName - Current project name
 * @param {string} options.currentDataSourceId - Current data source ID
 * @param {string} options.currentQuestionRefKey - Current dimension ref key
 * @param {Function} options.getDimensionDisplayName - Function to get dimension display name
 * @param {Function} options.showVerbatims - Function to show verbatims
 * @param {Function} options.showContextMenu - Function to show context menu
 * @param {Function} options.handleNodeClick - Function to handle node click
 * @param {Object} options.hierarchyData - Reference to hierarchyData for resize handler
 */
export function renderTreemap(data, options = {}) {
    
    const {
        colorSchemes,
        currentProjectName,
        currentDataSourceId,
        currentQuestionRefKey,
        getDimensionDisplayName,
        showVerbatims,
        showContextMenu,
        handleNodeClick,
        hierarchyData
    } = options;
    
    // Recalculate container dimensions
    const container = document.querySelector('.treemap-svg-container');
    if (container) {
        width = container.clientWidth || container.offsetWidth;
        height = container.clientHeight || container.offsetHeight;
    }
    
    // Ensure minimum dimensions
    if (!width || width < 100) width = 800;
    if (!height || height < 100) height = 600;
    
    
    const svg = d3.select('#treemap');
    svg.selectAll('*').remove();
    svg.attr('width', width).attr('height', height);
    
    // Set up resize handler (once)
    if (!resizeHandlerAttached) {
        const debounceFn = getDebounce();
        const treemapResizeHandler = debounceFn(() => {
            const currentHierarchyData = hierarchyData || window.hierarchyData;
            if (currentHierarchyData) {
                const container = document.querySelector('.treemap-svg-container');
                if (container) {
                    const newWidth = container.clientWidth;
                    const newHeight = container.clientHeight;
                    if (newWidth && newHeight && (Math.abs(newWidth - width) > 2 || Math.abs(newHeight - height) > 2)) {
                        width = newWidth;
                        height = newHeight;
                        // Call wrapper function which will call this module again
                        if (typeof window.renderTreemap === 'function') {
                            window.renderTreemap(currentHierarchyData);
                        }
                    }
                }
            }
        }, 250);
        window.addEventListener('resize', treemapResizeHandler);
        resizeHandlerAttached = true;
    }

    document.getElementById('verbatims').style.display = 'none';

    const root = d3.hierarchy(data)
        .sum(d => d.value || 0)
        .sort((a, b) => b.value - a.value);

    const totalValue = root.value || 0;
    
    // Handle empty data case
    if (!root.children || root.children.length === 0 || totalValue === 0) {
        svg.append('text')
            .attr('x', width / 2)
            .attr('y', height / 2)
            .attr('text-anchor', 'middle')
            .attr('dominant-baseline', 'middle')
            .style('font-size', '16px')
            .style('fill', '#999')
            .text('No data available for this dimension');
        return;
    }

    // Responsive padding
    const isMobile = width < 768;
    const outerPadding = isMobile ? 5 : 10;
    const topPadding = root.children && root.depth === 0 ? (isMobile ? 28 : 30) : (isMobile ? 2 : 3);
    const innerPadding = isMobile ? 2 : 3;

    d3.treemap()
        .size([width, height])
        .paddingOuter(outerPadding)
        .paddingTop(topPadding)
        .paddingInner(innerPadding)
        .round(true)
        (root);

    // Get color schemes with fallback
    const categoryColors = colorSchemes?.categories || window.colorSchemes?.categories || (() => '#cccccc');
    
    // Get dimension display name function with fallback
    const getDimNameFn = getDimensionDisplayName || window.getDimensionDisplayName || ((key) => key);

    // Draw category groups (parent rectangles)
    if (root.children && root.depth === 0) {
        const categoryGroups = svg.selectAll('.category-group')
            .data(root.children)
            .join('g')
            .attr('class', 'category-group')
            .style('cursor', 'pointer')
            .on('click', (event, d) => {
                try {
                    if (d && d.data) {
                        const allVerbatims = collectCategoryVerbatims(d.data);
                        if (allVerbatims.length > 0) {
                            const showVerbatimsFn = showVerbatims || window.showVerbatims;
                            if (showVerbatimsFn) {
                                showVerbatimsFn(allVerbatims, d.data.name || 'Category', d.data.name || 'Category');
                            }
                        }
                    }
                } catch (error) {
                    console.error('Error handling category click:', error);
                }
            })
            .on('contextmenu', (event, d) => {
                event.preventDefault();
                event.stopPropagation();
                if (d && d.data) {
                    const contextData = {
                        type: 'category',
                        category: d.data.name,
                        project_name: currentProjectName,
                        data_source: currentDataSourceId,
                        dimension_ref: currentQuestionRefKey,
                        dimension_name: currentQuestionRefKey ? getDimNameFn(currentQuestionRefKey) : null,
                    };
                    const showCtxMenuFn = showContextMenu || window.showContextMenu;
                    if (showCtxMenuFn) {
                        showCtxMenuFn(event, contextData);
                    }
                }
            });

        // Category background rectangles
        categoryGroups.append('rect')
            .attr('x', d => d.x0)
            .attr('y', d => d.y0)
            .attr('width', d => d.x1 - d.x0)
            .attr('height', d => d.y1 - d.y0)
            .attr('fill', 'none')
            .attr('stroke', '#ddd')
            .attr('stroke-width', 1)
            .attr('rx', 5)
            .attr('ry', 5)
            .attr('opacity', 0.6);

        // Category label bar
        categoryGroups.append('rect')
            .attr('x', d => d.x0)
            .attr('y', d => d.y0)
            .attr('width', d => d.x1 - d.x0)
            .attr('height', 26)
            .attr('fill', d => categoryColors(d.data.name))
            .attr('rx', 5)
            .attr('ry', 5)
            .attr('opacity', 0.95);

        // Category labels with percentage
        categoryGroups.append('text')
            .attr('class', 'category-label')
            .attr('x', d => d.x0 + (width < 768 ? 8 : 10))
            .attr('y', d => d.y0 + 17)
            .text(d => {
                const percent = totalValue > 0 ? ((d.value / totalValue) * 100).toFixed(1) : '0.0';
                const maxWidth = d.x1 - d.x0 - 20;
                const mobile = width < 768;
                let text = `${d.data.name} (${percent}%)`;
                
                if (mobile && maxWidth < 120) {
                    text = d.data.name.substring(0, 8) + '...';
                } else if (maxWidth < 150) {
                    text = d.data.name.substring(0, 12) + '...';
                } else if (maxWidth < 200) {
                    text = `${d.data.name.substring(0, 15)}... (${percent}%)`;
                }
                return text;
            });
    }

    // Draw leaf nodes (topics)
    const nodes = svg.selectAll('.leaf-node')
        .data(root.leaves())
        .join('g')
        .attr('class', 'leaf-node');

    const adjustBrightnessFn = getAdjustBrightness();

    // Add rectangles
    nodes.append('rect')
        .attr('class', 'node')
        .attr('x', d => d.x0)
        .attr('y', d => d.y0)
        .attr('width', d => d.x1 - d.x0)
        .attr('height', d => d.y1 - d.y0)
        .attr('rx', 5)
        .attr('ry', 5)
        .attr('fill', d => {
            if (!d.parent || !d.parent.data) {
                return '#cccccc';
            }
            const baseColor = categoryColors(d.parent.data.name);
            const siblings = d.parent.children;
            const index = siblings.indexOf(d);
            const brightnessAdjust = -10 + (index % 3) * 10;
            return adjustBrightnessFn(baseColor, brightnessAdjust);
        })
        .on('click', (event, d) => {
            const handleClickFn = handleNodeClick || window.handleNodeClick;
            if (handleClickFn) {
                handleClickFn(d);
            }
        })
        .on('contextmenu', (event, d) => {
            event.preventDefault();
            event.stopPropagation();
            if (d && d.data) {
                const categoryName = d.parent?.data?.name || 'Unknown Category';
                const contextData = {
                    type: 'topic',
                    category: categoryName,
                    topic_label: d.data.name,
                    project_name: currentProjectName,
                    data_source: currentDataSourceId,
                    dimension_ref: currentQuestionRefKey,
                    dimension_name: currentQuestionRefKey ? getDimNameFn(currentQuestionRefKey) : null,
                };
                const showCtxMenuFn = showContextMenu || window.showContextMenu;
                if (showCtxMenuFn) {
                    showCtxMenuFn(event, contextData);
                }
            }
        });

    // Add text labels
    nodes.each(function(d) {
        const nodeWidth = d.x1 - d.x0;
        const nodeHeight = d.y1 - d.y0;
        const centerX = (d.x0 + d.x1) / 2;
        const centerY = (d.y0 + d.y1) / 2;
        
        const mobile = width < 768;
        const minWidth = mobile ? 40 : 50;
        const minHeight = mobile ? 25 : 30;
        
        if (nodeWidth < minWidth || nodeHeight < minHeight) return;
        
        const percent = totalValue > 0 ? ((d.value / totalValue) * 100).toFixed(1) : '0.0';
        const node = d3.select(this);
        
        let displayName = d.data.name;
        const mobileBreakpoint = mobile ? 60 : 100;
        const tabletBreakpoint = mobile ? 100 : 150;
        
        if (nodeWidth < mobileBreakpoint) {
            displayName = displayName.substring(0, 8) + '...';
        } else if (nodeWidth < tabletBreakpoint) {
            displayName = displayName.substring(0, 15) + (displayName.length > 15 ? '...' : '');
        } else if (nodeWidth < 200) {
            displayName = displayName.substring(0, 25) + (displayName.length > 25 ? '...' : '');
        }
        
        const baseFontSize = mobile ? 10 : 12;
        const maxFontSize = mobile ? 12 : 14;
        const fontSize = Math.min(maxFontSize, Math.max(baseFontSize, nodeWidth / (mobile ? 10 : 15)));
        
        node.append('text')
            .attr('class', 'node-text')
            .attr('x', centerX)
            .attr('y', nodeHeight > (mobile ? 40 : 50) ? centerY - 8 : centerY)
            .style('font-size', `${fontSize}px`)
            .text(displayName);
        
        if (nodeHeight > (mobile ? 40 : 50)) {
            node.append('text')
                .attr('class', 'node-label')
                .attr('x', centerX)
                .attr('y', centerY + 10)
                .style('font-size', `${fontSize - 2}px`)
                .text(`(${percent}%)`);
        }
    });
    
        categoriesCount: root.children?.length || 0,
        leavesCount: root.leaves().length
    });
}

/**
 * Get current treemap dimensions
 */
export function getTreemapDimensions() {
    return { width, height };
}

/**
 * Set treemap dimensions
 */
export function setTreemapDimensions(w, h) {
    width = w;
    height = h;
}
