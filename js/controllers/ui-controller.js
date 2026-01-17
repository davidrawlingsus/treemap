/**
 * UI Controller
 * Handles simple UI toggle and interaction functions
 */

/**
 * Toggle chart visibility
 * @param {HTMLElement} button - The button that triggered the toggle
 */
export function toggleChart(button) {
    const chart = button.closest('.chart');
    if (chart) {
        chart.classList.toggle('collapsed');
    }
}

/**
 * Toggle treemap visibility
 * @param {HTMLElement} button - The button that triggered the toggle
 */
export function toggleTreemap(button) {
    const container = button.closest('.treemap-container');
    if (container) {
        container.classList.toggle('collapsed');
    }
}

/**
 * Toggle settings panel
 */
export function toggleSettingsPanel() {
    const panel = document.getElementById('settingsPanel');
    const button = document.querySelector('.settings-button');
    const isActive = panel.classList.contains('active');
    
    if (isActive) {
        panel.classList.remove('active');
        button.classList.remove('active');
    } else {
        panel.classList.add('active');
        button.classList.add('active');
    }
}

/**
 * Toggle insights panel
 */
export function toggleInsightsPanel() {
    const body = document.getElementById('insightsPanelBody');
    const container = document.querySelector('.insights-panel-container');
    if (body.classList.contains('collapsed')) {
        body.classList.remove('collapsed');
        if (container) container.classList.remove('collapsed');
    } else {
        body.classList.add('collapsed');
        if (container) container.classList.add('collapsed');
    }
}

/**
 * Toggle insights add dropdown
 * @param {Event} event - The click event
 */
export function toggleInsightsAddDropdown(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const menu = document.getElementById('insightsAddDropdownMenu');
    if (!menu) return;
    const isOpen = menu.classList.contains('open');
    menu.classList.toggle('open', !isOpen);
}

/**
 * Close insights add dropdown
 */
export function closeInsightsAddDropdown() {
    const menu = document.getElementById('insightsAddDropdownMenu');
    if (menu) {
        menu.classList.remove('open');
    }
}
