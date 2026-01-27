/**
 * Ads Find & Replace Service
 * Handles search and replace logic for ad fields.
 * Follows service pattern - pure functions, no DOM manipulation.
 */

/**
 * Search ads for text matches
 * @param {Array} ads - Array of ad objects
 * @param {string} searchText - Text to search for
 * @param {Object} fieldsToSearch - Object with boolean flags for each field
 * @returns {Array} Array of match objects: { ad, adId, matches: [{ field, value, newValue, matchCount }] }
 */
export function searchAdsForText(ads, searchText, fieldsToSearch) {
    if (!searchText || !searchText.trim()) {
        return [];
    }

    const searchTerm = searchText.trim();
    const results = [];

    ads.forEach(ad => {
        const matches = [];
        let totalMatchCount = 0;

        // Search primary_text
        if (fieldsToSearch.primary_text && ad.primary_text) {
            const matchCount = countMatches(ad.primary_text, searchTerm);
            if (matchCount > 0) {
                const newValue = ad.primary_text.replace(new RegExp(escapeRegex(searchTerm), 'gi'), (match) => {
                    return match; // Keep original case for preview
                });
                matches.push({
                    field: 'primary_text',
                    fieldLabel: 'Primary Text',
                    value: ad.primary_text,
                    newValue: newValue,
                    matchCount: matchCount
                });
                totalMatchCount += matchCount;
            }
        }

        // Search headline
        if (fieldsToSearch.headline && ad.headline) {
            const matchCount = countMatches(ad.headline, searchTerm);
            if (matchCount > 0) {
                const newValue = ad.headline.replace(new RegExp(escapeRegex(searchTerm), 'gi'), (match) => {
                    return match;
                });
                matches.push({
                    field: 'headline',
                    fieldLabel: 'Headline',
                    value: ad.headline,
                    newValue: newValue,
                    matchCount: matchCount
                });
                totalMatchCount += matchCount;
            }
        }

        // Search description
        if (fieldsToSearch.description && ad.description) {
            const matchCount = countMatches(ad.description, searchTerm);
            if (matchCount > 0) {
                const newValue = ad.description.replace(new RegExp(escapeRegex(searchTerm), 'gi'), (match) => {
                    return match;
                });
                matches.push({
                    field: 'description',
                    fieldLabel: 'Description',
                    value: ad.description,
                    newValue: newValue,
                    matchCount: matchCount
                });
                totalMatchCount += matchCount;
            }
        }

        // Search call_to_action
        if (fieldsToSearch.call_to_action && ad.call_to_action) {
            const matchCount = countMatches(ad.call_to_action, searchTerm);
            if (matchCount > 0) {
                const newValue = ad.call_to_action.replace(new RegExp(escapeRegex(searchTerm), 'gi'), (match) => {
                    return match;
                });
                matches.push({
                    field: 'call_to_action',
                    fieldLabel: 'Call to Action',
                    value: ad.call_to_action,
                    newValue: newValue,
                    matchCount: matchCount
                });
                totalMatchCount += matchCount;
            }
        }

        // Search destination_url
        if (fieldsToSearch.destination_url && ad.destination_url) {
            const matchCount = countMatches(ad.destination_url, searchTerm);
            if (matchCount > 0) {
                const newValue = ad.destination_url.replace(new RegExp(escapeRegex(searchTerm), 'gi'), (match) => {
                    return match;
                });
                matches.push({
                    field: 'destination_url',
                    fieldLabel: 'Destination URL',
                    value: ad.destination_url,
                    newValue: newValue,
                    matchCount: matchCount
                });
                totalMatchCount += matchCount;
            }
        }

        // Search full_json (recursively search string values)
        if (fieldsToSearch.full_json && ad.full_json) {
            const jsonMatches = searchInObject(ad.full_json, searchTerm);
            if (jsonMatches.length > 0) {
                jsonMatches.forEach(jsonMatch => {
                    matches.push({
                        field: `full_json.${jsonMatch.path}`,
                        fieldLabel: `Full JSON: ${jsonMatch.path}`,
                        value: jsonMatch.value,
                        newValue: jsonMatch.value.replace(new RegExp(escapeRegex(searchTerm), 'gi'), (match) => {
                            return match;
                        }),
                        matchCount: jsonMatch.matchCount,
                        jsonPath: jsonMatch.path,
                        jsonValue: jsonMatch.value
                    });
                    totalMatchCount += jsonMatch.matchCount;
                });
            }
        }

        if (matches.length > 0) {
            results.push({
                ad: ad,
                adId: ad.id,
                matches: matches,
                totalMatchCount: totalMatchCount
            });
        }
    });

    return results;
}

/**
 * Replace text in a single ad
 * @param {Object} ad - Ad object
 * @param {string} searchText - Text to find
 * @param {string} replaceText - Text to replace with
 * @param {Object} fieldsToSearch - Object with boolean flags for each field
 * @returns {Object} Updated ad object
 */
export function replaceInAd(ad, searchText, replaceText, fieldsToSearch) {
    if (!searchText || !searchText.trim()) {
        return { ...ad };
    }

    const searchTerm = searchText.trim();
    const updatedAd = { ...ad };

    // Replace in primary_text
    if (fieldsToSearch.primary_text && updatedAd.primary_text) {
        updatedAd.primary_text = updatedAd.primary_text.replace(
            new RegExp(escapeRegex(searchTerm), 'gi'),
            replaceText
        );
    }

    // Replace in headline
    if (fieldsToSearch.headline && updatedAd.headline) {
        updatedAd.headline = updatedAd.headline.replace(
            new RegExp(escapeRegex(searchTerm), 'gi'),
            replaceText
        );
    }

    // Replace in description
    if (fieldsToSearch.description && updatedAd.description) {
        updatedAd.description = updatedAd.description.replace(
            new RegExp(escapeRegex(searchTerm), 'gi'),
            replaceText
        );
    }

    // Replace in call_to_action
    if (fieldsToSearch.call_to_action && updatedAd.call_to_action) {
        updatedAd.call_to_action = updatedAd.call_to_action.replace(
            new RegExp(escapeRegex(searchTerm), 'gi'),
            replaceText
        );
    }

    // Replace in destination_url
    if (fieldsToSearch.destination_url && updatedAd.destination_url) {
        updatedAd.destination_url = updatedAd.destination_url.replace(
            new RegExp(escapeRegex(searchTerm), 'gi'),
            replaceText
        );
    }

    // Replace in full_json
    if (fieldsToSearch.full_json && updatedAd.full_json) {
        updatedAd.full_json = replaceInObject(updatedAd.full_json, searchTerm, replaceText);
    }

    return updatedAd;
}

/**
 * Replace text in all matching ads
 * @param {Array} ads - Array of ad objects
 * @param {string} searchText - Text to find
 * @param {string} replaceText - Text to replace with
 * @param {Object} fieldsToSearch - Object with boolean flags for each field
 * @returns {Array} Array of updated ad objects
 */
export function replaceAllInAds(ads, searchText, replaceText, fieldsToSearch) {
    const matches = searchAdsForText(ads, searchText, fieldsToSearch);
    const updatedAds = [];

    matches.forEach(match => {
        const updatedAd = replaceInAd(match.ad, searchText, replaceText, fieldsToSearch);
        updatedAds.push(updatedAd);
    });

    return updatedAds;
}

/**
 * Get preview text with highlighted matches
 * @param {string} text - Text to preview
 * @param {string} searchText - Text to highlight
 * @param {number} maxLength - Maximum length of preview
 * @returns {string} HTML string with highlighted matches
 */
export function getMatchPreview(text, searchText, maxLength = 100) {
    if (!text || !searchText) return '';

    const regex = new RegExp(escapeRegex(searchText), 'gi');
    const matches = text.match(regex);
    
    if (!matches || matches.length === 0) return '';

    // Find first match position
    const firstMatchIndex = text.toLowerCase().indexOf(searchText.toLowerCase());
    
    // Get context around first match
    const start = Math.max(0, firstMatchIndex - 20);
    const end = Math.min(text.length, firstMatchIndex + searchText.length + 20);
    
    let preview = text.substring(start, end);
    if (start > 0) preview = '...' + preview;
    if (end < text.length) preview = preview + '...';

    // Highlight matches
    preview = preview.replace(regex, (match) => {
        return `<span class="highlight">${match}</span>`;
    });

    return preview;
}

/**
 * Count occurrences of search term in text (case-insensitive)
 * @param {string} text - Text to search
 * @param {string} searchTerm - Term to find
 * @returns {number} Number of matches
 */
function countMatches(text, searchTerm) {
    if (!text || !searchTerm) return 0;
    const regex = new RegExp(escapeRegex(searchTerm), 'gi');
    const matches = text.match(regex);
    return matches ? matches.length : 0;
}

/**
 * Escape special regex characters
 * @param {string} str - String to escape
 * @returns {string} Escaped string
 */
function escapeRegex(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Recursively search for text in an object
 * @param {Object} obj - Object to search
 * @param {string} searchTerm - Text to find
 * @param {string} [path=''] - Current path in object
 * @returns {Array} Array of match objects: { path, value, matchCount }
 */
function searchInObject(obj, searchTerm, path = '') {
    const results = [];

    if (obj === null || obj === undefined) {
        return results;
    }

    if (typeof obj === 'string') {
        const matchCount = countMatches(obj, searchTerm);
        if (matchCount > 0) {
            results.push({
                path: path || 'root',
                value: obj,
                matchCount: matchCount
            });
        }
    } else if (Array.isArray(obj)) {
        obj.forEach((item, index) => {
            if (typeof item === 'string') {
                const matchCount = countMatches(item, searchTerm);
                if (matchCount > 0) {
                    results.push({
                        path: `${path}[${index}]`,
                        value: item,
                        matchCount: matchCount
                    });
                }
            } else if (typeof item === 'object' && item !== null) {
                results.push(...searchInObject(item, searchTerm, `${path}[${index}]`));
            }
        });
    } else if (typeof obj === 'object') {
        Object.keys(obj).forEach(key => {
            const value = obj[key];
            const newPath = path ? `${path}.${key}` : key;

            if (typeof value === 'string') {
                const matchCount = countMatches(value, searchTerm);
                if (matchCount > 0) {
                    results.push({
                        path: newPath,
                        value: value,
                        matchCount: matchCount
                    });
                }
            } else if (typeof value === 'object' && value !== null) {
                results.push(...searchInObject(value, searchTerm, newPath));
            }
        });
    }

    return results;
}

/**
 * Recursively replace text in an object
 * @param {Object} obj - Object to modify
 * @param {string} searchTerm - Text to find
 * @param {string} replaceText - Text to replace with
 * @returns {Object} Modified object
 */
function replaceInObject(obj, searchTerm, replaceText) {
    if (obj === null || obj === undefined) {
        return obj;
    }

    if (typeof obj === 'string') {
        return obj.replace(new RegExp(escapeRegex(searchTerm), 'gi'), replaceText);
    }

    if (Array.isArray(obj)) {
        return obj.map(item => {
            if (typeof item === 'string') {
                return item.replace(new RegExp(escapeRegex(searchTerm), 'gi'), replaceText);
            } else if (typeof item === 'object' && item !== null) {
                return replaceInObject(item, searchTerm, replaceText);
            }
            return item;
        });
    }

    if (typeof obj === 'object') {
        const result = {};
        Object.keys(obj).forEach(key => {
            const value = obj[key];
            if (typeof value === 'string') {
                result[key] = value.replace(new RegExp(escapeRegex(searchTerm), 'gi'), replaceText);
            } else if (typeof value === 'object' && value !== null) {
                result[key] = replaceInObject(value, searchTerm, replaceText);
            } else {
                result[key] = value;
            }
        });
        return result;
    }

    return obj;
}