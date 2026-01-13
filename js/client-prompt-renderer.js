/**
 * Client-Facing Prompt Renderer
 * Minimal renderer that provides only streaming functionality needed for AI Expert feature
 * (Doesn't require PromptListRenderer or ActionRenderer)
 */

(function() {
    'use strict';

    let rendererInitialized = false;
    let ClientPromptRenderer = null;

    function initializeRenderer() {
        if (rendererInitialized) {
            return ClientPromptRenderer;
        }

        // Check dependencies with detailed logging
        if (!window.FounderAdmin) {
            console.error('[CLIENT_PROMPT_RENDERER] FounderAdmin not available');
            return null;
        }
        
        if (!window.MarkdownConverter) {
            console.error('[CLIENT_PROMPT_RENDERER] MarkdownConverter not available. Check if markdown-converter.js loaded and FounderAdmin was available when it initialized.');
            return null;
        }
        
        if (!window.StreamingRenderer) {
            console.error('[CLIENT_PROMPT_RENDERER] StreamingRenderer not available. Check if streaming-renderer.js loaded and MarkdownConverter was available when it initialized.');
            return null;
        }

        try {
            // Import streaming renderer functions
            const { 
                getStreamingContent, 
                createStreamingResultItem, 
                appendToStreamingItem, 
                finalizeStreamingItem 
            } = window.StreamingRenderer;

            if (!getStreamingContent || !createStreamingResultItem || !appendToStreamingItem || !finalizeStreamingItem) {
                console.error('[CLIENT_PROMPT_RENDERER] StreamingRenderer missing required functions:', {
                    getStreamingContent: !!getStreamingContent,
                    createStreamingResultItem: !!createStreamingResultItem,
                    appendToStreamingItem: !!appendToStreamingItem,
                    finalizeStreamingItem: !!finalizeStreamingItem
                });
                return null;
            }

            // Import markdown converter
            const { convertMarkdown } = window.MarkdownConverter;
            
            if (!convertMarkdown) {
                console.error('[CLIENT_PROMPT_RENDERER] MarkdownConverter missing convertMarkdown function');
                return null;
            }

            /**
             * Client Prompt Renderer - Minimal interface
             * Provides only the streaming functions needed for AI Expert
             */
            ClientPromptRenderer = {
                // Streaming functionality
                getStreamingContent,
                createStreamingResultItem,
                appendToStreamingItem,
                finalizeStreamingItem,
                
                // Markdown conversion (for direct use if needed)
                convertMarkdown
            };

            rendererInitialized = true;
            console.log('[CLIENT_PROMPT_RENDERER] Renderer initialized successfully');
            return ClientPromptRenderer;
        } catch (error) {
            console.error('[CLIENT_PROMPT_RENDERER] Error initializing renderer:', error);
            return null;
        }
    }

    // Try to initialize immediately
    ClientPromptRenderer = initializeRenderer();

    // If not initialized, try again when DOM is ready
    if (!ClientPromptRenderer) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function() {
                ClientPromptRenderer = initializeRenderer();
                if (ClientPromptRenderer) {
                    window.ClientPromptRenderer = ClientPromptRenderer;
                    window.PromptUIRenderer = ClientPromptRenderer;
                }
            });
        } else {
            // DOM already loaded, try again after a short delay
            setTimeout(function() {
                ClientPromptRenderer = initializeRenderer();
                if (ClientPromptRenderer) {
                    window.ClientPromptRenderer = ClientPromptRenderer;
                    window.PromptUIRenderer = ClientPromptRenderer;
                }
            }, 100);
        }
    } else {
        // Export immediately if initialized
        window.ClientPromptRenderer = ClientPromptRenderer;
        window.PromptUIRenderer = ClientPromptRenderer;
    }

    // Also provide a getter function that tries to initialize if needed
    window.getClientPromptRenderer = function() {
        if (!rendererInitialized) {
            ClientPromptRenderer = initializeRenderer();
            if (ClientPromptRenderer) {
                window.ClientPromptRenderer = ClientPromptRenderer;
                window.PromptUIRenderer = ClientPromptRenderer;
            }
        }
        return ClientPromptRenderer;
    };
})();
