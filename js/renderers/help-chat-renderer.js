import { ICON_URLS } from '/js/config/icon-urls.js';

function createMessageElement(message) {
    const messageEl = document.createElement('div');
    messageEl.className = `help-chat-message help-chat-message--${message.sender_type || 'visitor'}`;
    messageEl.dataset.messageId = message.id;

    const metaEl = document.createElement('div');
    metaEl.className = 'help-chat-message__meta';
    metaEl.textContent = message.sender_label || (message.sender_type === 'operator' ? 'Support' : 'You');

    const bodyEl = document.createElement('div');
    bodyEl.className = 'help-chat-message__body';
    bodyEl.textContent = message.body || '';

    messageEl.appendChild(metaEl);
    messageEl.appendChild(bodyEl);
    return messageEl;
}

export function createHelpChatWidget() {
    const root = document.createElement('aside');
    root.className = 'help-chat-widget';
    root.innerHTML = `
        <button class="help-chat-launcher" type="button" aria-expanded="false" aria-controls="helpChatPanel" aria-label="Open help chat">
            <img class="help-chat-launcher__icon" src="${ICON_URLS.helpChat}" alt="" aria-hidden="true">
            <span class="help-chat-launcher__badge" hidden>0</span>
        </button>
        <section class="help-chat-panel" id="helpChatPanel" aria-hidden="true">
            <header class="help-chat-panel__header">
                <div>
                    <h2>Chat with support</h2>
                    <p>Send a message and it goes straight to Slack.</p>
                </div>
                <button class="help-chat-panel__close" type="button" aria-label="Close help chat">×</button>
            </header>
            <div class="help-chat-panel__status" hidden></div>
            <div class="help-chat-panel__messages"></div>
            <form class="help-chat-panel__composer">
                <label class="help-chat-panel__composer-label" for="helpChatInput">Message</label>
                <textarea id="helpChatInput" class="help-chat-panel__input" rows="3" maxlength="5000" placeholder="How can I help?"></textarea>
                <div class="help-chat-panel__actions">
                    <button class="help-chat-panel__send" type="submit">Send</button>
                </div>
            </form>
        </section>
    `;

    document.body.appendChild(root);

    return {
        root,
        launcher: root.querySelector('.help-chat-launcher'),
        badge: root.querySelector('.help-chat-launcher__badge'),
        panel: root.querySelector('.help-chat-panel'),
        closeButton: root.querySelector('.help-chat-panel__close'),
        status: root.querySelector('.help-chat-panel__status'),
        messages: root.querySelector('.help-chat-panel__messages'),
        form: root.querySelector('.help-chat-panel__composer'),
        input: root.querySelector('.help-chat-panel__input'),
        sendButton: root.querySelector('.help-chat-panel__send'),
    };
}

export function renderHelpChatMessages(refs, messages) {
    const fragment = document.createDocumentFragment();

    if (!messages.length) {
        const emptyState = document.createElement('div');
        emptyState.className = 'help-chat-empty-state';
        emptyState.textContent = 'Ask a question and I will reply here.';
        fragment.appendChild(emptyState);
    } else {
        messages.forEach((message) => {
            fragment.appendChild(createMessageElement(message));
        });
    }

    refs.messages.replaceChildren(fragment);
    refs.messages.scrollTop = refs.messages.scrollHeight;
}

export function setHelpChatOpen(refs, isOpen) {
    refs.root.classList.toggle('is-open', isOpen);
    refs.launcher.setAttribute('aria-expanded', String(isOpen));
    refs.panel.setAttribute('aria-hidden', String(!isOpen));
}

export function setHelpChatHidden(refs, isHidden) {
    refs.root.classList.toggle('help-chat-widget--hidden', isHidden);
}

export function setHelpChatStatus(refs, message) {
    if (!message) {
        refs.status.hidden = true;
        refs.status.textContent = '';
        return;
    }

    refs.status.hidden = false;
    refs.status.textContent = message;
}

export function setHelpChatSending(refs, isSending) {
    refs.input.disabled = isSending;
    refs.sendButton.disabled = isSending;
    refs.sendButton.textContent = isSending ? 'Sending...' : 'Send';
}

export function setHelpChatUnreadCount(refs, unreadCount) {
    const count = Number(unreadCount) || 0;
    refs.badge.hidden = count < 1;
    refs.badge.textContent = String(count);
}

export function focusHelpChatInput(refs) {
    refs.input.focus();
}
