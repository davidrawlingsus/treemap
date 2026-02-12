/**
 * Central configuration for icon and image URLs.
 * Uses local /images/ paths to avoid dependency on external blob storage for static assets.
 * This ensures icons load reliably regardless of Vercel Blob status.
 */
const IMAGES = '/images';

export const ICON_URLS = {
  add: `${IMAGES}/add.png`,
  filterList: `${IMAGES}/filter_list.svg`,
  deleteButton: `${IMAGES}/delete_button.png`,
  edit: `${IMAGES}/edit.png`,
  settings: `${IMAGES}/settings.svg`,
  closeButton: `${IMAGES}/close_button.png`,
  sendIcon: `${IMAGES}/send%20icon.png`,
  doneIcon: `${IMAGES}/done%20icon.png`,
  copyButton: `${IMAGES}/copy_button.png`,
  doneCheck: `${IMAGES}/done_check_black.png`,
  expansion: `${IMAGES}/expansion_icon.png`,
  toTop: `${IMAGES}/arrow_up.png`,
  pinned: `${IMAGES}/pinned_item.svg`,
  aiInsights: `${IMAGES}/ai_insights.png`,
  metaIcon: `${IMAGES}/meta-icon.webp`,
  prevArrow: `${IMAGES}/arrow_up.png`,
  nextArrow: `${IMAGES}/arrow_down.png`,
};

// Expose for non-module scripts (HTML inline, header.js, etc.)
if (typeof window !== 'undefined') {
  window.ICON_URLS = ICON_URLS;
}
