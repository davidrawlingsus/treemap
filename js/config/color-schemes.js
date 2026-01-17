/**
 * Color Schemes Configuration
 * D3 color scales and color configuration for visualizations
 */

/**
 * Category colors for treemap visualization
 * @type {Array<string>}
 */
export const CATEGORY_COLORS = [
    '#8B5CF6', // Purple
    '#EC4899', // Pink
    '#F59E0B', // Amber
    '#10B981', // Emerald
    '#3B82F6', // Blue
    '#F97316', // Orange
    '#EF4444', // Red
    '#14B8A6', // Teal
    '#6366F1', // Indigo
    '#F8A04C', // Amber-orange
    '#58B3F0', // Bright blue
    '#6ED49B', // Fresh green
    '#F47280', // Coral pink
    '#9A7B6C', // Warm neutral
    '#FFB366', // Peach
    '#B794F6', // Lavender
    '#4ECDC4', // Turquoise
];

/**
 * Get color schemes object with D3 scales
 * @param {Object} d3 - D3 library (must be available globally or passed in)
 * @returns {Object} Color schemes object with category scale
 */
export function getColorSchemes(d3 = window.d3) {
    if (!d3) {
        console.warn('D3 not available, returning empty color schemes');
        return { categories: null };
    }
    
    return {
        categories: d3.scaleOrdinal(CATEGORY_COLORS)
    };
}

/**
 * Category colors array (exported for direct access if needed)
 */
export { CATEGORY_COLORS };
