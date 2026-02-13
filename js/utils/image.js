/**
 * Image utility functions
 * Shared helpers for image optimization and thumbnails.
 */

/**
 * Generate an optimized image URL using wsrv.nl proxy.
 * Resizes and converts to WebP for faster loading.
 * Works with Vercel Blob and any public image URL.
 *
 * @param {string} url - Original image URL
 * @param {number} [width=500] - Desired width in pixels
 * @param {number} [quality=80] - Quality (1-100)
 * @returns {string} Optimized URL, or original if not optimizable
 */
export function getOptimizedImageUrl(url, width = 500, quality = 80) {
    if (!url || typeof url !== 'string') return url || '';
    if (url.includes('video') || !url.match(/\.(jpg|jpeg|png|gif|webp)($|\?)/i)) {
        return url;
    }
    return `https://wsrv.nl/?url=${encodeURIComponent(url)}&w=${width}&q=${quality}&output=webp`;
}
