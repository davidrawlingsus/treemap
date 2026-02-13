/**
 * Creative MRI report API service
 * Handles API calls for Creative MRI reports
 */

import { getBaseUrl } from './api-config.js';

/**
 * Update a Creative MRI report (e.g. after inline edits)
 * @param {string} clientId - Client UUID
 * @param {string} reportId - Report UUID
 * @param {object} report - Full report object including edited_sections
 * @param {Function} getAuthHeaders - Function to get auth headers
 * @returns {Promise<object>} Updated report response
 */
export async function updateCreativeMriReport(clientId, reportId, report, getAuthHeaders) {
    const res = await fetch(
        `${getBaseUrl()}/api/clients/${clientId}/creative-mri/reports/${reportId}`,
        {
            method: 'PATCH',
            headers: {
                ...(getAuthHeaders?.() || {}),
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ report }),
        }
    );
    if (!res.ok) {
        throw new Error(`Failed to save: ${res.status}`);
    }
    return res.json();
}
