/**
 * Formatting utility functions
 * Pure functions for data formatting and transformation
 */

/**
 * US state name to code mapping for geo visualizations
 */
export const stateNameToCode = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
    'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA',
    'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
    'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
    'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO',
    'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ',
    'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH',
    'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
    'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT',
    'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY',
    'District of Columbia': 'DC'
};

/**
 * FIPS code to state code mapping for TopoJSON
 */
export const fipsToStateCode = {
    '01': 'AL', '02': 'AK', '04': 'AZ', '05': 'AR', '06': 'CA',
    '08': 'CO', '09': 'CT', '10': 'DE', '11': 'DC', '12': 'FL', '13': 'GA',
    '15': 'HI', '16': 'ID', '17': 'IL', '18': 'IN', '19': 'IA',
    '20': 'KS', '21': 'KY', '22': 'LA', '23': 'ME', '24': 'MD',
    '25': 'MA', '26': 'MI', '27': 'MN', '28': 'MS', '29': 'MO',
    '30': 'MT', '31': 'NE', '32': 'NV', '33': 'NH', '34': 'NJ',
    '35': 'NM', '36': 'NY', '37': 'NC', '38': 'ND', '39': 'OH',
    '40': 'OK', '41': 'OR', '42': 'PA', '44': 'RI', '45': 'SC',
    '46': 'SD', '47': 'TN', '48': 'TX', '49': 'UT', '50': 'VT',
    '51': 'VA', '53': 'WA', '54': 'WV', '55': 'WI', '56': 'WY'
};

/**
 * Get state code from state name (case-insensitive)
 * @param {string} stateName - Full state name (e.g., "California")
 * @returns {string|null} Two-letter state code (e.g., "CA") or null if not found
 */
export function getStateCode(stateName) {
    if (!stateName) return null;
    const normalizedName = stateName.trim();
    // Try exact match first
    if (stateNameToCode[normalizedName]) {
        return stateNameToCode[normalizedName];
    }
    // Try case-insensitive match
    for (const [name, code] of Object.entries(stateNameToCode)) {
        if (name.toLowerCase() === normalizedName.toLowerCase()) {
            return code;
        }
    }
    return null;
}

/**
 * Get display name for a dimension (custom name if available, otherwise formatted ref_key)
 * @param {string} refKey - The dimension reference key
 * @param {Object} dimensionNamesMap - Map of ref_key -> custom_name (optional, will use global if not provided)
 * @returns {string} Display name
 */
export function getDimensionDisplayName(refKey, dimensionNamesMap = null) {
    // If dimensionNamesMap is provided, use it; otherwise try to get from global state
    let map = dimensionNamesMap;
    if (!map && typeof window !== 'undefined' && window.apiCacheGetDimensionNamesMap) {
        map = window.apiCacheGetDimensionNamesMap();
    }
    return (map && map[refKey]) || refKey.replace('ref_', 'Q');
}

/**
 * Highlight search terms in text (case-insensitive, supports multiple words)
 * @param {string} text - Text to search in
 * @param {string} searchTerm - Search term(s) to highlight
 * @param {Function} escapeHtmlFn - HTML escaping function (optional, will use global if not provided)
 * @returns {string} HTML with highlighted terms
 */
export function highlightSearchTerms(text, searchTerm, escapeHtmlFn = null) {
    if (!text || !searchTerm) {
        const escapeFn = escapeHtmlFn || (typeof window !== 'undefined' && window.escapeHtml) || ((s) => s);
        return escapeFn(text || '');
    }
    
    // Get escapeHtml function
    const escapeHtml = escapeHtmlFn || (typeof window !== 'undefined' && window.escapeHtml) || ((s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;'));
    
    // Escape the text first for safety
    const escapedText = escapeHtml(text);
    const trimmedSearch = searchTerm.trim();
    if (!trimmedSearch) {
        return escapedText;
    }
    
    // Split search term into words (handle multiple words)
    const searchWords = trimmedSearch.split(/\s+/).filter(word => word.length > 0);
    
    // Build regex pattern that matches any of the search words (case-insensitive)
    const pattern = searchWords.map(word => {
        // Escape special regex characters in the search word
        const escapedWord = word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        return escapedWord;
    }).join('|');
    
    const regex = new RegExp(`(${pattern})`, 'gi');
    
    // Replace matches with highlighted versions
    return escapedText.replace(regex, '<mark class="search-highlight">$1</mark>');
}

/** Marketing/funnel abbreviations that stay uppercase in PascalCase output */
const PASCAL_CASE_ABBREVIATIONS = new Set(['US', 'USA', 'SEO', 'CRO', 'UX', 'UI', 'API', 'CRM', 'CMS', 'CTA', 'ROI', 'KPI', 'A/B', 'AB', 'A', 'B', 'PPC', 'SEM', 'SERP', 'SaaS', 'B2B', 'B2C', 'BOFU', 'MOFU', 'TOFU', 'GDPR', 'LTV', 'CAC', 'MVP', 'FAQ', 'URL', 'HTML', 'CSS', 'JS', 'JSON', 'XML', 'REST', 'HTTP', 'HTTPS', 'SSL', 'TLS', 'CDN', 'DNS', 'IP', 'PDF', 'CSV', 'XLS', 'XLSX']);

/**
 * Convert text to PascalCase
 * @param {string} text - Text to convert
 * @returns {string} PascalCase text
 */
export function toPascalCase(text) {
    if (!text) return '';
    return text
        .split(/[\s_-]+/)
        .map(word => {
            // A&b, A&B, a&b etc. -> A & B (no spaces means it's one token)
            if (/^[Aa]&[Bb]$/.test(word)) {
                return 'A & B';
            }
            const upperWord = word.toUpperCase();
            if (PASCAL_CASE_ABBREVIATIONS.has(upperWord)) {
                return upperWord;
            }
            return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
        })
        .join(' ');
}
