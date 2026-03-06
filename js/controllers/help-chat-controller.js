import {
    ensureHelpChatConversation,
    openHelpChatStream,
    sendHelpChatMessage,
} from '/js/services/help-chat-api.js';
import {
    appendMessage,
    clearUnreadCount,
    getConversationId,
    getLastMessageTimestamp,
    getMessages,
    getStream,
    getUnreadCount,
    getVisitorToken,
    incrementUnreadCount,
    isInitialized,
    isOpen,
    setConversationId,
    setInitialized,
    setIsOpen,
    setMessages,
    setStream,
    setUnreadCount,
    setVisitorToken,
} from '/js/state/help-chat-state.js';
import {
    createHelpChatWidget,
    focusHelpChatInput,
    renderHelpChatMessages,
    setHelpChatHidden,
    setHelpChatOpen,
    setHelpChatSending,
    setHelpChatStatus,
    setHelpChatUnreadCount,
} from '/js/renderers/help-chat-renderer.js';


let refs = null;
let overlayObserver = null;
let hasBootstrappedConversation = false;

function getAuthOverlay() {
    return document.getElementById('loginOverlay');
}

function isHiddenByAuthOverlay() {
    const overlay = getAuthOverlay();
    return Boolean(overlay && !overlay.classList.contains('hidden'));
}

function getUserInfo() {
    return window.Auth?.getStoredUserInfo?.() || null;
}

function getConversationMetadata() {
    const metadata = {
        currentPath: window.location.pathname,
    };

    const currentClientId = window.appStateGetCurrentClientId?.();
    if (currentClientId) {
        metadata.currentClientId = currentClientId;
    }

    return metadata;
}

function syncWidgetVisibility() {
    if (!refs) {
        return;
    }

    const shouldHide = isHiddenByAuthOverlay();
    setHelpChatHidden(refs, shouldHide);

    if (shouldHide) {
        setHelpChatOpen(refs, false);
        setIsOpen(false);
    }
}

function updateUnreadCount() {
    setHelpChatUnreadCount(refs, getUnreadCount());
}

function renderMessages() {
    renderHelpChatMessages(refs, getMessages());
}

function setOpen(nextOpen) {
    setIsOpen(nextOpen);
    setHelpChatOpen(refs, nextOpen);

    if (nextOpen) {
        clearUnreadCount();
        updateUnreadCount();
        focusHelpChatInput(refs);
        renderMessages();
    }
}

function buildEnsurePayload() {
    const userInfo = getUserInfo();
    return {
        conversation_id: getConversationId(),
        visitor_token: getVisitorToken(),
        visitor_name: userInfo?.name || undefined,
        visitor_email: userInfo?.email || undefined,
        source_url: window.location.href,
        source_path: window.location.pathname,
        source_title: document.title,
        referrer_url: document.referrer || undefined,
        metadata: getConversationMetadata(),
    };
}

async function bootstrapConversation() {
    if (isHiddenByAuthOverlay()) {
        return;
    }

    const response = await ensureHelpChatConversation(buildEnsurePayload());
    hasBootstrappedConversation = true;
    setVisitorToken(response.visitor_token);
    setConversationId(response.id);
    setMessages(response.messages || []);
    renderMessages();
    connectStream();
    setHelpChatStatus(refs, '');
}

function handleIncomingMessage(message) {
    if (!appendMessage(message)) {
        return;
    }

    renderMessages();

    if (isOpen()) {
        clearUnreadCount();
    } else if (message.sender_type === 'operator') {
        incrementUnreadCount();
    }

    updateUnreadCount();
}

function connectStream() {
    const conversationId = getConversationId();
    const visitorToken = getVisitorToken();
    if (!conversationId || !visitorToken) {
        return;
    }

    const stream = openHelpChatStream({
        conversationId,
        visitorToken,
        since: getLastMessageTimestamp(),
    });

    stream.onopen = () => {
        setHelpChatStatus(refs, '');
    };

    stream.onmessage = (event) => {
        try {
            const payload = JSON.parse(event.data);
            if (payload.type === 'message' && payload.message) {
                handleIncomingMessage(payload.message);
            }
        } catch (error) {
            console.error('Failed to parse help chat event', error);
        }
    };

    stream.onerror = () => {
        setHelpChatStatus(refs, 'Reconnecting chat...');
    };

    setStream(stream);
}

async function ensureConversationReady() {
    if (!hasBootstrappedConversation || !getConversationId()) {
        await bootstrapConversation();
    }
}

async function handleSubmit(event) {
    event.preventDefault();

    const body = refs.input.value.trim();
    if (!body) {
        return;
    }

    setHelpChatSending(refs, true);
    setHelpChatStatus(refs, '');

    try {
        await ensureConversationReady();
        const message = await sendHelpChatMessage({
            conversationId: getConversationId(),
            visitorToken: getVisitorToken(),
            body,
            clientMessageId: window.crypto?.randomUUID?.() || `help-chat-${Date.now()}`,
        });
        handleIncomingMessage(message);
        refs.input.value = '';
        if (!isOpen()) {
            setOpen(true);
        }
    } catch (error) {
        console.error('Help chat send failed', error);
        setHelpChatStatus(refs, error.message || 'Could not send your message.');
    } finally {
        setHelpChatSending(refs, false);
    }
}

function observeAuthOverlay() {
    const overlay = getAuthOverlay();
    if (!overlay) {
        return;
    }

    overlayObserver = new MutationObserver(() => {
        syncWidgetVisibility();
        if (!isHiddenByAuthOverlay() && !hasBootstrappedConversation) {
            bootstrapConversation().catch((error) => {
                setHelpChatStatus(refs, error.message || 'Help chat is unavailable.');
            });
        }
    });

    overlayObserver.observe(overlay, {
        attributes: true,
        attributeFilter: ['class'],
    });
}

function bindEvents() {
    refs.launcher.addEventListener('click', () => {
        setOpen(!isOpen());
    });

    refs.closeButton.addEventListener('click', () => {
        setOpen(false);
    });

    refs.form.addEventListener('submit', handleSubmit);

    refs.input.addEventListener('keydown', (event) => {
        if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
            handleSubmit(event);
        }
    });

    window.addEventListener('auth:authenticated', async () => {
        syncWidgetVisibility();
        try {
            await bootstrapConversation();
        } catch (error) {
            setHelpChatStatus(refs, error.message || 'Help chat is unavailable.');
        }
    });

    window.addEventListener('auth:magicVerified', async () => {
        syncWidgetVisibility();
        try {
            await bootstrapConversation();
        } catch (error) {
            setHelpChatStatus(refs, error.message || 'Help chat is unavailable.');
        }
    });

    window.addEventListener('auth:logout', () => {
        syncWidgetVisibility();
    });
}

export async function initHelpChat() {
    if (isInitialized()) {
        return;
    }

    refs = createHelpChatWidget();
    setInitialized(true);
    setOpen(isOpen());
    setUnreadCount(0);
    updateUnreadCount();
    bindEvents();
    observeAuthOverlay();
    syncWidgetVisibility();

    if (!isHiddenByAuthOverlay()) {
        try {
            await bootstrapConversation();
        } catch (error) {
            console.error('Help chat bootstrap failed', error);
            setHelpChatStatus(refs, error.message || 'Help chat is unavailable.');
        }
    }
}
