/**
 * Color utility functions
 * Pure functions for color manipulation
 */

/**
 * Adjust the brightness of a hex color
 * @param {string} color - Hex color string (e.g., "#FF0000")
 * @param {number} percent - Brightness adjustment percentage (-100 to 100)
 * @returns {string} Adjusted hex color string
 */
export function adjustBrightness(color, percent) {
    const num = parseInt(color.replace("#",""), 16);
    const amt = Math.round(2.55 * percent);
    const R = (num >> 16) + amt;
    const G = (num >> 8 & 0x00FF) + amt;
    const B = (num & 0x0000FF) + amt;
    return "#" + (0x1000000 + (R<255?R<1?0:R:255)*0x10000 +
        (G<255?G<1?0:G:255)*0x100 +
        (B<255?B<1?0:B:255))
        .toString(16).slice(1);
}
