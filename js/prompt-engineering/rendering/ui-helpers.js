/**
 * UI Helpers - Main Entry Point
 * Combines all rendering modules and provides the UIRenderer interface
 */

(function() {
    'use strict';

    if (!window.MarkdownConverter || !window.StreamingRenderer || 
        !window.PromptListRenderer || !window.ActionRenderer) {
        console.error('[UI_HELPERS] Rendering modules must be loaded first');
        return;
    }

    // Import all renderer modules
    const { convertMarkdown, generateIdeaCardHTML } = window.MarkdownConverter;
    const { 
        getStreamingContent, 
        createStreamingResultItem, 
        appendToStreamingItem, 
        finalizeStreamingItem 
    } = window.StreamingRenderer;
    const { renderPrompts, getStatusBadge } = window.PromptListRenderer;
    const { 
        renderActions, 
        renderActionItem, 
        attachSystemMessageToggles, 
        attachIdeaCardListeners,
        renderLoading,
        renderError
    } = window.ActionRenderer;

    /**
     * UI Renderer - Main Interface
     * Provides the same interface as the original ui.js file
     */
    const UIRenderer = {
        // Markdown conversion
        convertMarkdown,
        _generateIdeaCardHTML: generateIdeaCardHTML,

        // Streaming functionality
        getStreamingContent,
        createStreamingResultItem,
        appendToStreamingItem,
        finalizeStreamingItem,

        // Prompt list rendering
        renderPrompts,
        getStatusBadge,

        // Action rendering
        renderActions,
        renderActionItem,
        attachSystemMessageToggles,
        attachIdeaCardListeners,

        // Utility rendering
        renderLoading,
        renderError
    };

    // Export with the same name as original
    window.PromptUIRenderer = UIRenderer;
})();
