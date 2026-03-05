/**
 * Subscription State Management
 * Tracks the current client's plan, features, and trial usage.
 */

let currentPlan = null;
let planDisplayName = null;
let planFeatures = null;
let trialLimit = null;
let trialUsesRemaining = null;
let clientPlanMap = {};

export function getCurrentPlan() { return currentPlan; }
export function getPlanDisplayName() { return planDisplayName; }
export function getPlanFeatures() { return planFeatures; }
export function getTrialLimit() { return trialLimit; }
export function getTrialUsesRemaining() { return trialUsesRemaining; }

/**
 * Check if the current plan has access to a specific feature.
 * Returns true if no plan is set (permissive until enforcement is wired).
 * @param {string} feature - Feature key from plan features dict
 * @returns {boolean}
 */
export function canAccess(feature) {
    if (!planFeatures) return true;
    return planFeatures[feature] === true;
}

/**
 * Check if the current client is on a trial-limited plan with uses remaining.
 * @returns {boolean}
 */
export function isTrialActive() {
    return trialLimit !== null && trialLimit > 0 && trialUsesRemaining !== null && trialUsesRemaining > 0;
}

/**
 * Check if the trial has been exhausted.
 * @returns {boolean}
 */
export function isTrialExhausted() {
    return trialLimit !== null && trialLimit > 0 && trialUsesRemaining !== null && trialUsesRemaining <= 0;
}

/**
 * Check if the current plan is the free/basic tier.
 * @returns {boolean}
 */
export function isBasicPlan() {
    return currentPlan === 'basic';
}

/**
 * Store plan info for all accessible clients (from /api/auth/me response).
 * @param {Array} clients - accessible_clients array from auth response
 */
export function setClientPlans(clients) {
    clientPlanMap = {};
    if (!Array.isArray(clients)) return;
    for (const c of clients) {
        clientPlanMap[c.id] = {
            plan_name: c.plan_name,
            plan_display_name: c.plan_display_name,
            plan_features: c.plan_features,
            trial_limit: c.trial_limit,
            trial_uses_remaining: c.trial_uses_remaining,
        };
    }
}

/**
 * Set the active client's plan from stored client plan data.
 * Call this when the user selects/switches a client.
 * @param {string} clientId - UUID of the selected client
 */
export function setActivePlan(clientId) {
    const info = clientPlanMap[clientId];
    if (info) {
        currentPlan = info.plan_name;
        planDisplayName = info.plan_display_name;
        planFeatures = info.plan_features;
        trialLimit = info.trial_limit;
        trialUsesRemaining = info.trial_uses_remaining;
    } else {
        currentPlan = null;
        planDisplayName = null;
        planFeatures = null;
        trialLimit = null;
        trialUsesRemaining = null;
    }
}

/**
 * Decrement trial uses remaining (called after a successful prompt execution).
 */
export function decrementTrialUse() {
    if (trialUsesRemaining !== null && trialUsesRemaining > 0) {
        trialUsesRemaining--;
        window.dispatchEvent(new CustomEvent('subscription:trialUpdated', {
            detail: { remaining: trialUsesRemaining, limit: trialLimit }
        }));
    }
}

/**
 * Get plan info for a specific client.
 * @param {string} clientId
 * @returns {object|null}
 */
export function getClientPlanInfo(clientId) {
    return clientPlanMap[clientId] || null;
}
