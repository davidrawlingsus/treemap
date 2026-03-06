const STORAGE_KEYS = {
    visitorToken: 'help_chat_visitor_token',
    conversationId: 'help_chat_conversation_id',
    isOpen: 'help_chat_is_open',
};

let initialized = false;
let messages = [];
let unreadCount = 0;
let stream = null;

function readStorage(key) {
    try {
        return window.localStorage.getItem(key);
    } catch (_) {
        return null;
    }
}

function writeStorage(key, value) {
    try {
        if (value == null || value === '') {
            window.localStorage.removeItem(key);
            return;
        }
        window.localStorage.setItem(key, value);
    } catch (_) {
        // Ignore storage errors so the widget still works.
    }
}

export function isInitialized() {
    return initialized;
}

export function setInitialized(value) {
    initialized = Boolean(value);
}

export function getVisitorToken() {
    return readStorage(STORAGE_KEYS.visitorToken);
}

export function setVisitorToken(visitorToken) {
    writeStorage(STORAGE_KEYS.visitorToken, visitorToken);
}

export function getConversationId() {
    return readStorage(STORAGE_KEYS.conversationId);
}

export function setConversationId(conversationId) {
    writeStorage(STORAGE_KEYS.conversationId, conversationId);
}

export function isOpen() {
    return readStorage(STORAGE_KEYS.isOpen) === 'true';
}

export function setIsOpen(value) {
    writeStorage(STORAGE_KEYS.isOpen, value ? 'true' : 'false');
}

export function getMessages() {
    return messages.slice();
}

export function setMessages(nextMessages) {
    messages = Array.isArray(nextMessages) ? nextMessages.slice() : [];
}

export function appendMessage(message) {
    if (!message || !message.id) {
        return false;
    }

    if (messages.some((existingMessage) => existingMessage.id === message.id)) {
        return false;
    }

    messages = messages.concat(message).sort((left, right) => {
        return new Date(left.created_at).getTime() - new Date(right.created_at).getTime();
    });
    return true;
}

export function getLastMessageTimestamp() {
    if (!messages.length) {
        return null;
    }
    return messages[messages.length - 1].created_at || null;
}

export function getUnreadCount() {
    return unreadCount;
}

export function setUnreadCount(value) {
    unreadCount = Math.max(0, Number(value) || 0);
}

export function incrementUnreadCount() {
    unreadCount += 1;
}

export function clearUnreadCount() {
    unreadCount = 0;
}

export function getStream() {
    return stream;
}

export function setStream(nextStream) {
    if (stream && stream !== nextStream) {
        stream.close();
    }
    stream = nextStream || null;
}
