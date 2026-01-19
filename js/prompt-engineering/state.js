/**
 * Prompt Engineering State Management
 * Centralized state with event-driven updates
 */

(function() {
    'use strict';

    if (!window.FounderAdmin) {
        console.error('[PROMPT_STATE] FounderAdmin utilities must be loaded first');
        return;
    }

    const { StateManager } = window.FounderAdmin;

    // Initial state
    const initialState = {
        founder: null,
        prompts: [],
        currentMode: 'create', // 'create' or 'edit'
        currentPromptId: null,
        actionMode: 'save-and-run', // 'save-and-run' or 'save-only'
        slideoutPromptId: null, // Track which prompt is being viewed in slideout
        allActions: [], // All actions from all prompts
        filterState: {
            promptNames: new Set(), // Selected prompt names
            promptVersions: new Set(), // Selected prompt versions (format: "name:v1")
            models: new Set(), // Selected models
        },
        statusFilter: '',
        purposeFilter: '',
        viewMode: 'cards', // 'cards' or 'table'
        tableSortColumn: 'updated_at', // Default sort column
        tableSortDirection: 'desc' // 'asc' or 'desc'
    };

    // Create state manager
    const state = StateManager.create(initialState);

    // Export state manager
    window.PromptEngineeringState = state;
})();

