/**
 * Custom Purposes Management
 * Handles localStorage operations for custom prompt purposes
 */

(function() {
    'use strict';

    const STORAGE_KEY = 'customPromptPurposes';
    const DEFAULT_PURPOSES = ['summarize', 'headlines', 'ux-fixes', 'risk-reversal', 'microcopy'];

    /**
     * Purposes Manager
     */
    const PurposesManager = {
        /**
         * Get all custom purposes from localStorage
         * @returns {Array<string>} Array of purpose strings
         */
        getCustomPurposes() {
            try {
                const stored = localStorage.getItem(STORAGE_KEY);
                return stored ? JSON.parse(stored) : [];
            } catch (error) {
                console.error('[PURPOSES] Error reading from localStorage:', error);
                return [];
            }
        },

        /**
         * Save custom purposes to localStorage
         * @param {Array<string>} purposes - Array of purpose strings
         */
        saveCustomPurposes(purposes) {
            try {
                localStorage.setItem(STORAGE_KEY, JSON.stringify(purposes));
            } catch (error) {
                console.error('[PURPOSES] Error saving to localStorage:', error);
            }
        },

        /**
         * Add a new custom purpose
         * @param {string} purpose - Purpose name
         * @returns {string} Normalized purpose name
         */
        addPurpose(purpose) {
            if (!purpose) return null;

            // Normalize to lowercase with hyphens
            const normalizedPurpose = purpose.toLowerCase().trim().replace(/\s+/g, '-');

            // Get existing custom purposes
            const customPurposes = this.getCustomPurposes();

            // Add if not already present
            if (!customPurposes.includes(normalizedPurpose)) {
                customPurposes.push(normalizedPurpose);
                this.saveCustomPurposes(customPurposes);
            }

            return normalizedPurpose;
        },

        /**
         * Remove a custom purpose
         * @param {string} purpose - Purpose name to remove
         */
        removePurpose(purpose) {
            const customPurposes = this.getCustomPurposes();
            const index = customPurposes.indexOf(purpose);
            
            if (index !== -1) {
                customPurposes.splice(index, 1);
                this.saveCustomPurposes(customPurposes);
            }
        },

        /**
         * Update a purpose name
         * @param {string} oldPurpose - Old purpose name
         * @param {string} newPurpose - New purpose name
         * @returns {string|null} Normalized new purpose name or null if error
         */
        updatePurpose(oldPurpose, newPurpose) {
            if (!oldPurpose || !newPurpose) return null;

            const normalizedPurpose = newPurpose.toLowerCase().trim().replace(/\s+/g, '-');
            const customPurposes = this.getCustomPurposes();

            // Check if new name already exists (and it's not the same as the old one)
            if (customPurposes.includes(normalizedPurpose) && normalizedPurpose !== oldPurpose) {
                return null; // Duplicate
            }

            // Update in array
            const index = customPurposes.indexOf(oldPurpose);
            if (index !== -1) {
                customPurposes[index] = normalizedPurpose;
                this.saveCustomPurposes(customPurposes);
                return normalizedPurpose;
            }

            return null;
        },

        /**
         * Get all purposes (default + custom)
         * @returns {Array<string>} Array of all purposes
         */
        getAllPurposes() {
            const customPurposes = this.getCustomPurposes();
            return [...DEFAULT_PURPOSES, ...customPurposes];
        },

        /**
         * Get display name for a purpose
         * @param {string} purpose - Purpose name (e.g., "email-copy")
         * @returns {string} Display name (e.g., "Email Copy")
         */
        getDisplayName(purpose) {
            return purpose.split('-').map(word => 
                word.charAt(0).toUpperCase() + word.slice(1)
            ).join(' ');
        },

        /**
         * Populate a select element with purposes
         * @param {HTMLSelectElement} selectElement - Select element to populate
         * @param {boolean} includeEmpty - Whether to include empty option
         * @param {Array} prompts - Optional array of prompts to extract purposes from
         */
        populateSelect(selectElement, includeEmpty = false, prompts = null) {
            if (!selectElement) return;

            // Clear existing options except default ones
            const defaultValues = includeEmpty ? [''] : [];
            const defaultOptions = [...defaultValues, ...DEFAULT_PURPOSES];
            
            Array.from(selectElement.options).forEach(option => {
                if (!defaultOptions.includes(option.value)) {
                    option.remove();
                }
            });

            // Get all purposes to include
            const allPurposes = new Set([...DEFAULT_PURPOSES]);
            
            // Add custom purposes from localStorage
            const customPurposes = this.getCustomPurposes();
            customPurposes.forEach(purpose => allPurposes.add(purpose));
            
            // Add purposes from existing prompts if provided
            if (prompts && Array.isArray(prompts)) {
                prompts.forEach(prompt => {
                    if (prompt.prompt_purpose) {
                        allPurposes.add(prompt.prompt_purpose);
                    }
                });
            }

            // Add all purposes to select
            Array.from(allPurposes).sort().forEach(purpose => {
                const existingOptions = Array.from(selectElement.options).map(opt => opt.value);
                if (!existingOptions.includes(purpose)) {
                    const option = document.createElement('option');
                    option.value = purpose;
                    option.textContent = this.getDisplayName(purpose);
                    selectElement.appendChild(option);
                }
            });
        }
    };

    // Export
    window.PurposesManager = PurposesManager;
})();

