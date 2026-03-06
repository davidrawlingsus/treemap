/**
 * Parse and normalize Facebook ad JSON from LLM output.
 * Handles malformed JSON (repair) and inconsistent structure (normalize).
 * Load before markdown-converter.js; exposes ParseFbAdJson on window.
 */
(function () {
    'use strict';

    /**
     * Apply heuristics to repair common LLM JSON mistakes.
     * @param {string} raw - Raw string between ```json and ```
     * @returns {string} Repaired string (best-effort)
     */
    function repairJsonString(raw) {
        if (!raw || typeof raw !== 'string') return raw;
        let s = raw.trim();

        // Fix LLM output where \\" was used for an escaped quote inside a string: in JSON,
        // \\ is one backslash and " then closes the string. Replace \\" with \\\" so the
        // quote is escaped and remains inside the string (position 113 / "Expected ',' or '}'").
        s = s.replace(/\\\\"/g, '\\\\\\"');

        // Remove trailing commas before } or ]
        s = s.replace(/,(\s*[}\]])/g, '$1');

        // Fix: "media": {} followed by "type": "image" and "image_hash": null at same level.
        const mediaEmptyThenType = /"media"\s*:\s*\{\s*\}\s*,?\s*"type"\s*:\s*"image"\s*,?\s*"image_hash"\s*:\s*null/;
        if (mediaEmptyThenType.test(s)) {
            s = s.replace(mediaEmptyThenType, '"media": { "type": "image", "image_hash": null }');
        }

        // Fix: "media": {} then "type" and "image_hash" on separate lines (no comma after })
        const mediaEmptyNewlineType = /"media"\s*:\s*\{\s*\}\s*\n\s*"type"\s*:\s*"image"\s*,?\s*\n\s*"image_hash"\s*:\s*null/;
        if (mediaEmptyNewlineType.test(s)) {
            s = s.replace(mediaEmptyNewlineType, '"media": { "type": "image", "image_hash": null }');
        }

        // Fix: extra } that leaves "testType"/"angle"/"origin" outside root object (remove one })
        s = s.replace(/}\s*}\s*(\s*"(?:testType|angle|origin)"\s*:)/g, '}$1');

        return s;
    }

    /**
     * Parse JSON block; on failure try repair then parse again.
     * @param {string} jsonContent - Content between ```json and ```
     * @returns {object} Parsed object
     * @throws {Error} If parse fails after repair attempt
     */
    function parseJsonBlock(jsonContent) {
        const raw = jsonContent != null ? String(jsonContent).trim() : '';
        if (!raw) {
            throw new Error('Empty JSON content');
        }
        try {
            return JSON.parse(raw);
        } catch (firstErr) {
            try {
                const repaired = repairJsonString(raw);
                return JSON.parse(repaired);
            } catch (secondErr) {
                throw firstErr;
            }
        }
    }

    /**
     * Detect if object looks like a Facebook ad idea (has required fields).
     * @param {object} idea
     * @returns {boolean}
     */
    function isFacebookAdIdea(idea) {
        return !!(
            idea &&
            typeof idea === 'object' &&
            idea.primary_text != null &&
            idea.headline != null &&
            idea.call_to_action != null
        );
    }

    /**
     * Normalize Facebook ad idea so media is a single object and root-level
     * type/image_hash are merged in. Aligns testType -> angle.
     * Mutates idea in place and returns it.
     * @param {object} idea - Parsed idea object (may have media empty or type/image_hash at root)
     * @returns {object} Same object, normalized
     */
    function normalizeFacebookAdIdea(idea) {
        if (!idea || typeof idea !== 'object') return idea;
        if (!isFacebookAdIdea(idea)) return idea;

        if (!idea.media || typeof idea.media !== 'object') {
            idea.media = {};
        }
        const media = idea.media;

        if (media.type == null && idea.type != null) {
            media.type = idea.type;
            delete idea.type;
        }
        if (media.type == null) {
            media.type = 'image';
        }
        if (media.image_hash === undefined && idea.image_hash !== undefined) {
            media.image_hash = idea.image_hash;
            delete idea.image_hash;
        }
        if (media.image_hash === undefined) {
            media.image_hash = null;
        }

        if (idea.angle == null && idea.testType != null) {
            idea.angle = idea.testType;
        }

        return idea;
    }

    window.ParseFbAdJson = {
        parseJsonBlock,
        normalizeFacebookAdIdea
    };
})();
