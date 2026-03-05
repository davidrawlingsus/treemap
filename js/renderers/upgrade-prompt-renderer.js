/**
 * Upgrade Prompt Renderer
 * Reusable UI components for trial limits and upgrade prompts.
 */

const MODAL_ID = 'upgradeModal';

/**
 * Show a full-screen upgrade modal when trial is exhausted.
 * @param {Object} error - Error object with .code, .limit, .used, .remaining, .planName
 */
export function showUpgradeModal(error = {}) {
    dismissUpgradeModal();

    const limit = error.limit || 5;
    const overlay = document.createElement('div');
    overlay.id = MODAL_ID;
    overlay.className = 'upgrade-modal-overlay';
    overlay.innerHTML = `
        <div class="upgrade-modal">
            <button class="upgrade-modal__close" aria-label="Close">&times;</button>
            <div class="upgrade-modal__icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
                </svg>
            </div>
            <h2 class="upgrade-modal__title">You've used all ${limit} free generations</h2>
            <p class="upgrade-modal__body">
                Upgrade to Pro for unlimited access to turn your voice-of-customer insights into
                high-converting Facebook ads, email sequences, and SEO strategy.
            </p>
            <div class="upgrade-modal__features">
                <div class="upgrade-modal__feature">Unlimited AI generations</div>
                <div class="upgrade-modal__feature">Facebook Ads &amp; Email creation</div>
                <div class="upgrade-modal__feature">SEO strategy from VoC data</div>
                <div class="upgrade-modal__feature">Full Settings &amp; Product Context</div>
            </div>
            <a href="/pricing.html" class="upgrade-modal__cta">View Plans &amp; Upgrade</a>
            <button class="upgrade-modal__dismiss">Maybe later</button>
        </div>
    `;

    overlay.querySelector('.upgrade-modal__close').addEventListener('click', dismissUpgradeModal);
    overlay.querySelector('.upgrade-modal__dismiss').addEventListener('click', dismissUpgradeModal);
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) dismissUpgradeModal();
    });

    document.body.appendChild(overlay);
    requestAnimationFrame(() => overlay.classList.add('visible'));
}

/**
 * Dismiss the upgrade modal if open.
 */
export function dismissUpgradeModal() {
    const existing = document.getElementById(MODAL_ID);
    if (existing) existing.remove();
}

/**
 * Render a trial counter element for embedding in the context menu.
 * Only renders if the user is on a trial-limited plan.
 * @param {HTMLElement} container - Element to prepend the counter into
 */
export function renderTrialCounter(container) {
    if (!container) return;

    const existing = container.querySelector('.ctx-trial-counter');
    if (existing) existing.remove();

    const isBasic = window.subStateIsBasicPlan?.();
    if (!isBasic) return;

    const remaining = window.subStateGetTrialUsesRemaining?.();
    const limit = window.subStateGetTrialLimit?.();
    if (remaining === null || remaining === undefined || !limit) return;

    const exhausted = remaining <= 0;
    const used = limit - remaining;
    const pct = Math.min((used / limit) * 100, 100);

    const el = document.createElement('div');
    el.className = 'ctx-trial-counter';
    el.innerHTML = `
        <div class="ctx-trial-counter__bar">
            <div class="ctx-trial-counter__fill ${exhausted ? 'ctx-trial-counter__fill--exhausted' : ''}" style="width: ${pct}%"></div>
        </div>
        <span class="ctx-trial-counter__label">${remaining} of ${limit} free</span>
        ${exhausted ? '<a href="/pricing.html" class="ctx-trial-counter__upgrade">Upgrade</a>' : ''}
    `;

    container.prepend(el);
}

/**
 * Render an upgrade banner at the top of a section (Ads, Emails).
 * Idempotent -- won't add duplicate banners.
 * @param {HTMLElement} container - Section container to prepend banner into
 * @param {string} feature - Feature name for the message (e.g. "ad", "email")
 */
export function renderUpgradeBanner(container, feature = 'content') {
    if (!container) return;

    const existing = container.querySelector('.upgrade-banner');
    if (existing) return;

    const isBasic = window.subStateIsBasicPlan?.();
    if (!isBasic) return;

    const userInfo = window.Auth?.getStoredUserInfo?.();
    if (userInfo?.is_founder) return;

    const banner = document.createElement('div');
    banner.className = 'upgrade-banner';
    banner.innerHTML = `
        <span class="upgrade-banner__text">Upgrade to Pro for unlimited ${feature} generation</span>
        <a href="/pricing.html" class="upgrade-banner__cta">View Plans</a>
    `;

    container.prepend(banner);
}
