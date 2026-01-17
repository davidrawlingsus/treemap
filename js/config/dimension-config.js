/**
 * Dimension Configuration
 * Predefined dimension options and configuration constants
 */

/**
 * Predefined dimension options
 * @type {Array<string>}
 */
export const DIMENSION_OPTIONS = [
    'Original Desire',
    'Triggers',
    'False Beliefs',
    'Competitors',
    'Appeal',
    'Exclusivity',
    'Objections',
    'Proof Elements',
    'Trusted Personalities',
    'Trusted Media',
    'Usability Friction',
    'Relevant Features',
    'Relevant Benefits',
    'Product Ideas',
    'Service Ideas'
];

/**
 * Get dimension options
 * @returns {Array<string>}
 */
export function getDimensionOptions() {
    return [...DIMENSION_OPTIONS];
}

/**
 * Check if a dimension option exists
 * @param {string} option
 * @returns {boolean}
 */
export function hasDimensionOption(option) {
    return DIMENSION_OPTIONS.includes(option);
}

/**
 * Add a dimension option (if not already present)
 * @param {string} option
 */
export function addDimensionOption(option) {
    if (option && !DIMENSION_OPTIONS.includes(option)) {
        DIMENSION_OPTIONS.push(option);
    }
}
