/**
 * Streaming Renderer Module
 * Handles streaming content updates and management
 */

(function() {
    'use strict';

    if (!window.FounderAdmin || !window.MarkdownConverter) {
        console.error('[STREAMING_RENDERER] Dependencies not loaded');
        return;
    }

    const { DOM } = window.FounderAdmin;
    const { convertMarkdown } = window.MarkdownConverter;

    // Constants
    const USER_MESSAGE_PREVIEW_LENGTH = 200; // characters
    const SCROLL_BOTTOM_THRESHOLD = 50; // px
    const SCROLL_TO_TOP_THRESHOLD = 3; // px

    // Store streaming content in memory instead of data attributes to avoid size limits
    // Use WeakMap so elements can be garbage collected when removed from DOM
    const streamingContentStore = new WeakMap();

    /**
     * Get raw text content from streaming content store (for copy functionality)
     * @param {HTMLElement} contentElement - Content element
     * @returns {string} Raw text content or empty string
     */
    function getStreamingContent(contentElement) {
        return streamingContentStore.get(contentElement) || '';
    }

    /**
     * Create a streaming result item placeholder
     * @param {HTMLElement} container - Container element to append to
     * @param {string} promptName - Prompt name
     * @param {string|number} promptVersion - Prompt version
     * @param {string} userMessage - User message (optional)
     * @returns {HTMLElement} The created streaming item element
     */
    function createStreamingResultItem(container, promptName, promptVersion, userMessage = '') {
        if (!container) return null;

        const streamingId = `streaming-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const createdAt = new Date().toLocaleString();
        const versionStr = promptVersion !== null && promptVersion !== undefined ? `v${promptVersion}` : '';

        const itemHTML = `
            <div class="prompt-output-item" data-streaming-id="${streamingId}" data-prompt-name="${DOM.escapeHtmlForAttribute(promptName)}" data-prompt-version="${promptVersion || ''}">
                <div class="prompt-output-header" data-streaming-header="${streamingId}">
                    <div class="prompt-output-meta">
                        <div style="margin-bottom: 4px;">
                            <strong>${DOM.escapeHtml(promptName)} ${versionStr}</strong>
                            <span style="color: var(--muted); font-size: 12px; margin-left: 12px;">${createdAt}</span>
                            <span style="color: var(--muted); font-size: 12px; margin-left: 8px;">• Streaming...</span>
                        </div>
                        ${userMessage ? `
                            <div style="margin-top: 8px;">
                                <div style="font-size: 12px; color: var(--text); margin-top: 4px;">
                                    <strong>User Message:</strong> 
                                    <span>${DOM.escapeHtml(userMessage.length > USER_MESSAGE_PREVIEW_LENGTH ? userMessage.substring(0, USER_MESSAGE_PREVIEW_LENGTH) + '...' : userMessage)}</span>
                                </div>
                            </div>
                        ` : ''}
                    </div>
                    <div class="prompt-output-actions">
                        <div class="ai-loading-spinner" style="width: 16px; height: 16px; border-width: 2px; margin-right: 8px;"></div>
                    </div>
                </div>
                <div class="prompt-result-content" data-streaming-content="${streamingId}"></div>
            </div>
        `;

        // Append to container (newest items appear at bottom, which is the natural order)
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = itemHTML;
        const itemElement = tempDiv.firstElementChild;
        container.appendChild(itemElement);

        // Initialize auto-scroll state: enabled by default, user can disable by scrolling
        itemElement.dataset.autoScrollEnabled = 'true';
        itemElement.dataset.lastScrollTop = container.scrollTop.toString();

        // Add scroll event listener to detect manual scrolling
        let scrollTimeout = null;
        const handleScroll = () => {
            const currentScrollTop = container.scrollTop;
            const lastScrollTop = parseFloat(itemElement.dataset.lastScrollTop || '0');
            
            // If user scrolled down manually (away from top), disable auto-scroll
            if (currentScrollTop > lastScrollTop + 5) { // 5px threshold to account for minor adjustments
                console.log('[STREAMING] User scrolled down manually, disabling auto-scroll for streaming item', {
                    streamingId,
                    currentScrollTop,
                    lastScrollTop
                });
                itemElement.dataset.autoScrollEnabled = 'false';
            }
            
            itemElement.dataset.lastScrollTop = currentScrollTop.toString();
            
            // Clear timeout and set new one to detect when scrolling stops
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                // After scrolling stops, check if user is at top
                if (container.scrollTop <= 10) {
                    // Re-enable auto-scroll if user scrolled back to top
                    console.log('[STREAMING] User scrolled back to top, re-enabling auto-scroll', { streamingId });
                    itemElement.dataset.autoScrollEnabled = 'true';
                }
            }, 150);
        };

        container.addEventListener('scroll', handleScroll, { passive: true });
        
        // Store cleanup function on element
        itemElement._cleanupScrollListener = () => {
            container.removeEventListener('scroll', handleScroll);
            if (scrollTimeout) clearTimeout(scrollTimeout);
        };

        // Initial scroll to bottom to show the new streaming item
        requestAnimationFrame(() => {
            if (container) {
                container.scrollTop = container.scrollHeight;
                itemElement.dataset.lastScrollTop = container.scrollTop.toString();
            }
        });

        return itemElement;
    }

    /**
     * Check if container is scrolled to bottom (within threshold)
     * @param {HTMLElement} container - Container element
     * @param {number} threshold - Threshold in pixels (default: 50)
     * @returns {boolean} True if at bottom
     */
    function _isAtBottom(container, threshold = SCROLL_BOTTOM_THRESHOLD) {
        if (!container) return false;
        const scrollTop = container.scrollTop;
        const scrollHeight = container.scrollHeight;
        const clientHeight = container.clientHeight;
        const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
        return distanceFromBottom <= threshold;
    }

    /**
     * Check if streaming header is at or above the top of the container viewport
     * @param {HTMLElement} itemElement - Streaming item element
     * @param {HTMLElement} container - Container element
     * @returns {boolean} True if header is at or above top of viewport
     */
    function _isHeaderAtTop(itemElement, container) {
        if (!itemElement || !container) return false;
        
        const header = itemElement.querySelector('[data-streaming-header]');
        if (!header) return false;

        // Use getBoundingClientRect to get current viewport positions
        const containerRect = container.getBoundingClientRect();
        const headerRect = header.getBoundingClientRect();
        
        // When the header reaches the top of the container, headerRect.top should equal containerRect.top
        // We want to stop when header's top edge is at or just above the container's top edge
        // Add a small threshold to account for subpixel rendering and rounding
        const headerTopRelativeToContainer = headerRect.top - containerRect.top;
        const isAtTop = headerTopRelativeToContainer <= SCROLL_TO_TOP_THRESHOLD;
        
        // Only log when we're close to the top to avoid spam
        if (headerTopRelativeToContainer <= 50) {
            console.log('[STREAMING] Header position check', {
                headerTop: headerRect.top,
                containerTop: containerRect.top,
                headerTopRelativeToContainer,
                scrollTop: container.scrollTop,
                isAtTop,
                threshold: SCROLL_TO_TOP_THRESHOLD
            });
        }
        
        return isAtTop;
    }

    /**
     * Append content to a streaming result item
     * @param {HTMLElement} itemElement - The streaming item element
     * @param {string} chunk - Content chunk to append
     */
    function appendToStreamingItem(itemElement, chunk) {
        if (!itemElement || !chunk) return;

        const contentElement = itemElement.querySelector(`[data-streaming-content]`);
        if (!contentElement) return;

        // Accumulate text for markdown rendering
        // Store raw text in WeakMap to avoid data attribute size limits
        const currentText = streamingContentStore.get(contentElement) || '';
        const newText = currentText + chunk;
        
        try {
            // Store in WeakMap instead of data attribute
            streamingContentStore.set(contentElement, newText);

            // Render markdown to get new HTML
            const markdownHTML = convertMarkdown(newText);
            
            // OPTIMIZATION: Detect if idea cards have changed to avoid unnecessary re-rendering
            // that destroys button DOM elements (breaks click events during streaming)
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = markdownHTML;
            
            // Handle both regular idea cards AND FB ad cards
            const newCards = Array.from(tempDiv.querySelectorAll('.pe-idea-card, .pe-fb-ad-wrapper'));
            const existingCards = Array.from(contentElement.querySelectorAll('.pe-idea-card, .pe-fb-ad-wrapper'));
            
            // Create signatures to compare cards by their IDs (if available) or by title/headline
            const getCardSignature = (card) => {
                // Check for idea-id attribute (works for both card types)
                const id = card.getAttribute('data-idea-id');
                if (id) return `id:${id}`;
                // Check for FB ad unique ID
                const fbAdId = card.getAttribute('data-fb-ad-id');
                if (fbAdId) return `fb:${fbAdId}`;
                // Fallback to title for regular idea cards
                const title = card.querySelector('.pe-idea-card__title')?.textContent?.trim();
                if (title) return `title:${title}`;
                // Fallback to headline for FB ad cards
                const headline = card.querySelector('.pe-fb-ad__headline')?.textContent?.trim();
                return headline ? `headline:${headline}` : null;
            };
            
            const newCardSignatures = new Set(newCards.map(getCardSignature).filter(Boolean));
            const existingCardSignatures = new Set(existingCards.map(getCardSignature).filter(Boolean));
            
            // Check if the cards have actually changed (count or signatures differ)
            const cardsChanged = newCards.length !== existingCards.length ||
                                newCardSignatures.size !== existingCardSignatures.size ||
                                !Array.from(newCardSignatures).every(sig => existingCardSignatures.has(sig));
            
            if (!cardsChanged && existingCards.length > 0) {
                // Cards haven't changed - preserve existing card DOM elements entirely
                // and only update the streaming content that appears after the last card
                const lastExistingCard = existingCards[existingCards.length - 1];
                const lastNewCard = newCards[newCards.length - 1];
                
                if (lastExistingCard && lastNewCard) {
                    // Get all content after the last card in the new HTML
                    // We need to find the last card in the DOM tree and get everything after it
                    const nodesAfterLastCard = [];
                    let foundLastCard = false;
                    
                    // Use a recursive walker to find the last card and collect nodes after it
                    function walkNodes(parent) {
                        for (let node of parent.childNodes) {
                            if (foundLastCard) {
                                // We've found the last card, collect this node
                                nodesAfterLastCard.push(node.cloneNode(true));
                            } else if (node === lastNewCard) {
                                // Found it! Mark and continue to collect siblings
                                foundLastCard = true;
                            } else if (node.nodeType === Node.ELEMENT_NODE) {
                                // Check children
                                walkNodes(node);
                                // If we found it in children, collect remaining siblings
                                if (foundLastCard) {
                                    let sibling = node.nextSibling;
                                    while (sibling) {
                                        nodesAfterLastCard.push(sibling.cloneNode(true));
                                        sibling = sibling.nextSibling;
                                    }
                                    return; // Done with this level
                                }
                            }
                        }
                    }
                    
                    walkNodes(tempDiv);
                    
                    // Only proceed if we actually found the last card
                    if (foundLastCard) {
                        // Remove content after the last existing card
                        let currentNode = lastExistingCard.nextSibling;
                        while (currentNode) {
                            const nextNode = currentNode.nextSibling;
                            contentElement.removeChild(currentNode);
                            currentNode = nextNode;
                        }
                        
                        // Append new content after the last card
                        nodesAfterLastCard.forEach(node => {
                            contentElement.appendChild(node);
                        });
                        
                        return; // Skip full re-render
                    }
                    // If we didn't find the last card, fall through to full re-render
                }
            }
            
            // Cards have changed OR no cards exist - do full re-render with preservation
            const preservedCards = new Map();
            existingCards.forEach(card => {
                const signature = getCardSignature(card);
                if (signature) {
                    preservedCards.set(signature, card);
                }
            });
            
            // Replace new cards with preserved cards where signatures match
            newCards.forEach(newCard => {
                const signature = getCardSignature(newCard);
                const preservedCard = signature ? preservedCards.get(signature) : null;
                
                if (preservedCard && newCard.parentNode) {
                    newCard.parentNode.replaceChild(preservedCard, newCard);
                }
            });
            
            // Clear existing content
            while (contentElement.firstChild) {
                contentElement.removeChild(contentElement.firstChild);
            }
            
            // Append all nodes from tempDiv (this preserves the actual DOM elements we swapped in)
            while (tempDiv.firstChild) {
                contentElement.appendChild(tempDiv.firstChild);
            }
        } catch (error) {
            console.error('[STREAMING] Error in appendToStreamingItem:', error);
            throw error;
        }

        // Check if auto-scroll is enabled
        const autoScrollEnabled = itemElement.dataset.autoScrollEnabled === 'true';
        if (!autoScrollEnabled) {
            // Auto-scroll disabled, don't scroll
            return;
        }

        const container = itemElement.closest('.slideout-content') || itemElement.parentElement;
        if (!container) return;

        // Check if user is at bottom before auto-scrolling
        const isAtBottom = _isAtBottom(container);
        if (!isAtBottom) {
            // User is not at bottom, don't auto-scroll
            console.log('[STREAMING] User not at bottom, skipping auto-scroll', {
                streamingId: itemElement.dataset.streamingId,
                scrollTop: container.scrollTop,
                scrollHeight: container.scrollHeight,
                clientHeight: container.clientHeight
            });
            return;
        }

        // User is at bottom and auto-scroll is enabled, scroll to bottom
        // But first check if header will reach top after this scroll
        requestAnimationFrame(() => {
            if (container && itemElement.dataset.autoScrollEnabled === 'true') {
                // Store current scroll position
                const scrollBefore = container.scrollTop;
                
                // Scroll to bottom
                container.scrollTop = container.scrollHeight;
                itemElement.dataset.lastScrollTop = container.scrollTop.toString();
                
                // Check if header is now at top AFTER scrolling
                // Use requestAnimationFrame to ensure DOM has updated
                requestAnimationFrame(() => {
                    if (_isHeaderAtTop(itemElement, container)) {
                        console.log('[STREAMING] Streaming header reached top of viewport after scroll, disabling auto-scroll', {
                            streamingId: itemElement.dataset.streamingId,
                            scrollBefore,
                            scrollAfter: container.scrollTop
                        });
                        itemElement.dataset.autoScrollEnabled = 'false';
                    }
                });
            }
        });
    }

    /**
     * Finalize a streaming result item (remove loading, add metadata)
     * @param {HTMLElement} itemElement - The streaming item element
     * @param {Object} metadata - Metadata object with tokens_used, model, etc.
     */
    function finalizeStreamingItem(itemElement, metadata = {}) {
        if (!itemElement) return;

        // Clean up scroll listener
        if (itemElement._cleanupScrollListener) {
            itemElement._cleanupScrollListener();
            delete itemElement._cleanupScrollListener;
        }

        // Remove streaming ID attribute
        const streamingId = itemElement.getAttribute('data-streaming-id');
        if (streamingId) {
            itemElement.removeAttribute('data-streaming-id');
        }

        // Remove streaming header attribute
        const header = itemElement.querySelector('[data-streaming-header]');
        if (header) {
            header.removeAttribute('data-streaming-header');
        }

        // Update header to remove loading indicator and add metadata
        const metaDiv = header?.querySelector('.prompt-output-meta > div');
        const actionsDiv = header?.querySelector('.prompt-output-actions');

        if (metaDiv) {
            // Remove "Streaming..." text
            const streamingSpan = metaDiv.querySelector('span:last-child');
            if (streamingSpan && streamingSpan.textContent.includes('Streaming')) {
                streamingSpan.remove();
            }

            // Add metadata if available
            if (metadata.model || metadata.tokens_used) {
                const metadataHTML = [];
                if (metadata.model) {
                    metadataHTML.push(`<span style="color: var(--muted); font-size: 12px; margin-left: 8px;">• ${DOM.escapeHtml(metadata.model)}</span>`);
                }
                if (metadata.tokens_used) {
                    metadataHTML.push(`<span style="color: var(--muted); font-size: 12px; margin-left: 8px;">• ${metadata.tokens_used} tokens</span>`);
                }
                if (metadataHTML.length > 0) {
                    metaDiv.insertAdjacentHTML('beforeend', metadataHTML.join(''));
                }
            }
        }

        // Remove loading spinner and add action buttons
        if (actionsDiv) {
            actionsDiv.innerHTML = `
                <button class="btn-nav-prev" data-action-id="streaming-${streamingId}" title="Previous message">
                    <img src="https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/insights/1767496461750-8ikag.png" alt="Previous" width="16" height="16">
                </button>
                <button class="btn-nav-next" data-action-id="streaming-${streamingId}" title="Next message">
                    <img src="https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/insights/1767496465023-xx3hee.png" alt="Next" width="16" height="16">
                </button>
                <button class="btn-copy-output" data-action-id="streaming-${streamingId}" title="Copy to clipboard">
                    <img src="https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/icons/copy_button.png" alt="Copy" width="16" height="16">
                </button>
                <button class="btn-delete-output" data-action-id="streaming-${streamingId}" title="Delete">
                    <img src="https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/icons/delete_button.png" alt="Delete" width="16" height="16">
                </button>
            `;
        }

        // Move raw text from WeakMap to data-raw-text attribute for copy functionality
        const contentElementFinal = itemElement.querySelector(`[data-streaming-content]`);
        if (contentElementFinal) {
            const rawText = streamingContentStore.get(contentElementFinal) || '';
            if (rawText) {
                contentElementFinal.setAttribute('data-raw-text', rawText);
            }
            contentElementFinal.removeAttribute('data-streaming-content');
            // Clean up WeakMap entry (WeakMap will automatically clean up when element is GC'd, but we can clear it explicitly)
            streamingContentStore.delete(contentElementFinal);
        }

        // Clean up auto-scroll tracking attributes
        delete itemElement.dataset.autoScrollEnabled;
        delete itemElement.dataset.lastScrollTop;
    }

    // Export
    window.StreamingRenderer = {
        getStreamingContent,
        createStreamingResultItem,
        appendToStreamingItem,
        finalizeStreamingItem
    };
})();
