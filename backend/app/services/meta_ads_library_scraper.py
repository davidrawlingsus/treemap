"""
Meta Ads Library Scraper Service.
Scrapes media (images and videos) from Meta Ads Library pages using Playwright.
Targets only ad card containers to avoid UI sprite sheets and icons.
"""

import logging
import asyncio
import httpx
import re
import time
import random
import string
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse, parse_qs
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MediaItem:
    """Represents a media item scraped from the Ads Library."""
    url: str
    media_type: str  # 'image' or 'video'
    filename: Optional[str] = None
    started_running_on: Optional[str] = None  # Date string like "Jan 15, 2024"
    library_id: Optional[str] = None


@dataclass
class MediaItemInfo:
    """Single media item (video or image) within an ad card."""
    media_type: str  # 'image' or 'video'
    url: str
    poster_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    sort_order: int = 0


@dataclass
class AdCopyItem:
    """Full ad card scraped from Ads Library (copy, metadata, media)."""
    primary_text: str
    headline: Optional[str] = None
    description: Optional[str] = None
    library_id: Optional[str] = None
    started_running_on: Optional[str] = None
    ad_delivery_start_time: Optional[str] = None
    ad_delivery_end_time: Optional[str] = None
    ad_format: Optional[str] = None
    cta: Optional[str] = None
    destination_url: Optional[str] = None
    media_thumbnail_url: Optional[str] = None
    # Extended: status, platforms, page, ads count
    status: Optional[str] = None  # Active | Paused | Ended
    platforms: Optional[List[str]] = None  # ["meta","instagram",...]
    ads_using_creative_count: Optional[int] = None
    page_name: Optional[str] = None
    page_url: Optional[str] = None
    page_profile_image_url: Optional[str] = None
    media_items: Optional[List[MediaItemInfo]] = None  # Full media URLs per ad


class MetaAdsLibraryScraper:
    """Service for scraping media from Meta Ads Library."""
    
    def __init__(self, headless: bool = True, timeout: int = 60000):
        """
        Initialize the scraper.
        
        Args:
            headless: Run browser in headless mode
            timeout: Page load timeout in milliseconds
        """
        self.headless = headless
        self.timeout = timeout
    
    def validate_url(self, url: str) -> bool:
        """
        Validate that the URL is a Meta Ads Library URL with a page ID.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid
        """
        try:
            parsed = urlparse(url)
            is_meta_domain = parsed.netloc in ('www.facebook.com', 'facebook.com')
            is_ads_library = '/ads/library' in parsed.path
            
            # Check for view_all_page_id parameter
            params = parse_qs(parsed.query)
            has_page_id = 'view_all_page_id' in params
            
            return is_meta_domain and is_ads_library and has_page_id
        except Exception:
            return False
    
    def get_page_id_from_url(self, url: str) -> Optional[str]:
        """Extract page ID from URL."""
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            page_ids = params.get('view_all_page_id', [])
            return page_ids[0] if page_ids else None
        except Exception:
            return None
    
    async def scrape_ads_library(self, url: str, max_scrolls: int = 5) -> List[MediaItem]:
        """
        Scrape media from a Meta Ads Library page.
        
        Args:
            url: Meta Ads Library URL with view_all_page_id
            max_scrolls: Maximum number of scroll operations to load more ads
            
        Returns:
            List of MediaItem objects
        """
        if not self.validate_url(url):
            raise ValueError("Invalid Meta Ads Library URL. Must include view_all_page_id parameter.")
        
        media_items = []
        seen_urls = set()
        
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError(
                "Playwright is not installed. Run: pip install playwright && playwright install chromium"
            )
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=self.headless)
            
            try:
                # Create context with realistic viewport
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                page = await context.new_page()
                
                # Navigate to the URL
                logger.info(f"Navigating to Meta Ads Library: {url}")
                await page.goto(url, timeout=self.timeout, wait_until='networkidle')
                
                # Wait for ad cards to load
                await page.wait_for_timeout(3000)
                
                # Scroll to load more ads
                for scroll_num in range(max_scrolls):
                    # Extract media from current page state
                    new_media = await self._extract_media_from_page(page, seen_urls)
                    media_items.extend(new_media)
                    
                    logger.info(f"Scroll {scroll_num + 1}: Found {len(new_media)} new ad media items")
                    
                    # Scroll down
                    await page.evaluate('window.scrollBy(0, window.innerHeight * 2)')
                    await page.wait_for_timeout(2000)
                    
                    # Check if we've reached the bottom
                    at_bottom = await page.evaluate('''
                        () => {
                            return (window.innerHeight + window.scrollY) >= document.body.scrollHeight - 100;
                        }
                    ''')
                    
                    if at_bottom:
                        # One more extraction in case new content loaded
                        final_media = await self._extract_media_from_page(page, seen_urls)
                        media_items.extend(final_media)
                        break
                
                logger.info(f"Total ad media items found: {len(media_items)}")
                
            finally:
                await browser.close()
        
        return media_items
    
    async def scrape_ads_library_copy(self, url: str, max_scrolls: int = 5) -> List[AdCopyItem]:
        """
        Scrape ad copy only (primary text, headline) from a Meta Ads Library page.
        Returns list of AdCopyItem; no media download.
        """
        if not self.validate_url(url):
            raise ValueError("Invalid Meta Ads Library URL. Must include view_all_page_id parameter.")
        
        all_copy: List[AdCopyItem] = []
        seen_keys: set = set()  # (library_id or "", primary_text[:50]) to dedupe
        
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError(
                "Playwright is not installed. Run: pip install playwright && playwright install chromium"
            )
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            try:
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
                page = await context.new_page()
                await page.goto(url, timeout=self.timeout, wait_until='networkidle')
                await page.wait_for_timeout(3000)
                
                for scroll_num in range(max_scrolls):
                    new_items = await self._extract_copy_from_page(page, seen_keys)
                    all_copy.extend(new_items)
                    logger.info(f"Scroll {scroll_num + 1}: Found {len(new_items)} ad copy items")
                    await page.evaluate('window.scrollBy(0, window.innerHeight * 2)')
                    await page.wait_for_timeout(2000)
                    at_bottom = await page.evaluate(
                        '() => (window.innerHeight + window.scrollY) >= document.body.scrollHeight - 100'
                    )
                    if at_bottom:
                        final = await self._extract_copy_from_page(page, seen_keys)
                        all_copy.extend(final)
                        break
                
                logger.info(f"Total ad copy items found: {len(all_copy)}")
            finally:
                await browser.close()
        
        return all_copy
    
    async def _extract_copy_from_page(self, page, seen_keys: set) -> List[AdCopyItem]:
        """Extract full ad card: copy, metadata, status, page info, media."""
        raw = await page.evaluate('''
            () => {
                const results = [];
                const allSpans = document.querySelectorAll('span');
                const adCards = new Map();
                
                for (const span of allSpans) {
                    const text = span.textContent?.trim() || '';
                    const libraryIdMatch = text.match(/^Library ID:\\s*(\\d+)$/);
                    if (libraryIdMatch) {
                        let container = span;
                        for (let i = 0; i < 15 && container.parentElement; i++) {
                            container = container.parentElement;
                            const hasVideo = container.querySelector('video[src]');
                            const hasImage = container.querySelector('img[src*="scontent"], img[src*="fbcdn"]');
                            if (hasVideo || hasImage) break;
                        }
                        const key = container;
                        if (!adCards.has(key)) adCards.set(key, { libraryId: null, startedRunningOn: null, endedRunningOn: null, status: null, adsUsingCreative: null });
                        adCards.get(key).libraryId = libraryIdMatch[1];
                    }
                    const dateMatch = text.match(/^Started running on\\s+([A-Za-z]+\\s+\\d{1,2},?\\s+\\d{4})$/);
                    if (dateMatch) {
                        let container = span;
                        for (let i = 0; i < 15 && container.parentElement; i++) {
                            container = container.parentElement;
                            const hasVideo = container.querySelector('video[src]');
                            const hasImage = container.querySelector('img[src*="scontent"], img[src*="fbcdn"]');
                            if (hasVideo || hasImage) break;
                        }
                        const key = container;
                        if (!adCards.has(key)) adCards.set(key, { libraryId: null, startedRunningOn: null, endedRunningOn: null, status: null, adsUsingCreative: null });
                        adCards.get(key).startedRunningOn = dateMatch[1];
                    }
                    const endedMatch = text.match(/Ended\\s+([A-Za-z]+\\s+\\d{1,2},?\\s+\\d{4})/);
                    if (endedMatch) {
                        let container = span;
                        for (let i = 0; i < 15 && container.parentElement; i++) {
                            container = container.parentElement;
                            const hasVideo = container.querySelector('video[src]');
                            const hasImage = container.querySelector('img[src*="scontent"], img[src*="fbcdn"]');
                            if (hasVideo || hasImage) break;
                        }
                        const key = container;
                        if (adCards.has(key)) adCards.get(key).endedRunningOn = endedMatch[1];
                    }
                    if (/^Active$|^Paused$|^Ended$/i.test(text)) {
                        let container = span;
                        for (let i = 0; i < 15 && container.parentElement; i++) {
                            container = container.parentElement;
                            const hasVideo = container.querySelector('video[src]');
                            const hasImage = container.querySelector('img[src*="scontent"], img[src*="fbcdn"]');
                            if (hasVideo || hasImage) break;
                        }
                        const key = container;
                        if (!adCards.has(key)) adCards.set(key, { libraryId: null, startedRunningOn: null, endedRunningOn: null, status: null, adsUsingCreative: null });
                        adCards.get(key).status = text;
                    }
                    const adsMatch = text.match(/(\\d+)\\s+ads?\\s+use this creative/i);
                    if (adsMatch) {
                        let container = span;
                        for (let i = 0; i < 15 && container.parentElement; i++) {
                            container = container.parentElement;
                            const hasVideo = container.querySelector('video[src]');
                            const hasImage = container.querySelector('img[src*="scontent"], img[src*="fbcdn"]');
                            if (hasVideo || hasImage) break;
                        }
                        const key = container;
                        if (!adCards.has(key)) adCards.set(key, { libraryId: null, startedRunningOn: null, endedRunningOn: null, status: null, adsUsingCreative: null });
                        adCards.get(key).adsUsingCreative = parseInt(adsMatch[1], 10);
                    }
                }
                
                const META_MEDIA_URL = /(scontent|fbcdn\\.net|video\\.\\d+\\.fbcdn|cdninstagram)/i;
                const isAdMediaUrl = (url) => {
                    if (!url || typeof url !== 'string') return false;
                    const u = url.toLowerCase();
                    if (u.includes('s60x60') || u.includes('_s60x60')) return false;
                    return META_MEDIA_URL.test(url);
                };
                const findMediaInContainer = (el) => {
                    const videos = [], images = [];
                    const seen = new Set();
                    const walk = (node, depth) => {
                        if (depth > 25) return;
                        if (node.nodeType !== 1) return;
                        if (node.tagName === 'VIDEO') {
                            const src = node.src || node.getAttribute('src');
                            const poster = node.poster || node.getAttribute('poster');
                            const url = src || poster;
                            if (url && isAdMediaUrl(url) && !seen.has(url)) {
                                seen.add(url);
                                videos.push({ url, poster: poster || null });
                            }
                            return;
                        }
                        if (node.tagName === 'IMG') {
                            const src = node.src || node.getAttribute('src');
                            if (src && isAdMediaUrl(src) && !seen.has(src)) {
                                seen.add(src);
                                images.push({ url: src });
                            }
                            return;
                        }
                        for (const c of node.children || []) walk(c, depth + 1);
                    };
                    walk(el, 0);
                    if (videos.length === 0 && images.length === 0 && el.parentElement) {
                        walk(el.parentElement, 0);
                    }
                    return { videos, images };
                };
                for (const [container, data] of adCards) {
                    let bodyText = '';
                    let headlineText = '';
                    
                    const preWrapDivs = container.querySelectorAll('div[style*="white-space: pre-wrap"]');
                    for (const div of preWrapDivs) {
                        const t = (div.innerText || div.textContent || '').trim();
                        if (t.length > bodyText.length && t.length > 20) bodyText = t;
                    }
                    
                    const lineClampDivs = container.querySelectorAll('div[style*="line-clamp"]');
                    for (const div of lineClampDivs) {
                        const t = (div.innerText || div.textContent || '').trim();
                        const withoutSponsored = t.replace(/^Sponsored\\s*/i, '').trim();
                        if (withoutSponsored.length > 0 && withoutSponsored.length <= 200)
                            headlineText = withoutSponsored;
                    }
                    
                    const fullText = (container.innerText || container.textContent || '').trim();
                    if (bodyText.length < 10 && fullText.length >= 10) bodyText = fullText;
                    
                    if (bodyText.length < 5) continue;
                    
                    let adFormat = 'image';
                    const { videos, images } = findMediaInContainer(container);
                    const video = videos[0];
                    const largeImages = images;
                    if (video) adFormat = 'video';
                    else if (largeImages.length > 1) adFormat = 'carousel';
                    
                    let mediaThumbnailUrl = null;
                    if (video && video.poster) mediaThumbnailUrl = video.poster;
                    else if (video && video.url) mediaThumbnailUrl = video.url;
                    else if (largeImages.length > 0 && largeImages[0].url) mediaThumbnailUrl = largeImages[0].url;
                    
                    let cta = null;
                    let destinationUrl = null;
                    let pageName = null;
                    let pageUrl = null;
                    let pageProfileImageUrl = null;
                    const links = container.querySelectorAll('a[target="_blank"][href]');
                    for (const a of links) {
                        const href = (a.getAttribute('href') || a.href || '').trim();
                        if (!href || href.startsWith('#')) continue;
                        const text = (a.innerText || a.textContent || '').trim();
                        if (href.includes('facebook.com') && !href.includes('l.php') && text && text.length > 0 && text.length <= 100) {
                            pageUrl = href;
                            pageName = text;
                        }
                        if (href.includes('l.facebook.com/l.php') || href.includes('l.php')) {
                            try {
                                const u = new URL(href);
                                const uParam = u.searchParams.get('u');
                                destinationUrl = uParam ? decodeURIComponent(uParam) : href;
                            } catch (_) { destinationUrl = href; }
                        } else if (href.startsWith('http') && !href.includes('facebook.com')) {
                            destinationUrl = href;
                        }
                        if (destinationUrl && text && text.length <= 100) cta = text;
                        if (destinationUrl) break;
                    }
                    const profileImg = container.querySelector('img[alt][src*="scontent"], img[alt][src*="fbcdn"]');
                    if (profileImg && profileImg.alt && pageName && (profileImg.alt === pageName || profileImg.alt.includes(pageName))) {
                        pageProfileImageUrl = profileImg.src;
                    } else if (largeImages.length > 0 && !video) {
                        pageProfileImageUrl = null;
                    } else {
                        const smallImg = container.querySelector('img[src*="s60x60"], img[src*="_s60x60"]');
                        if (smallImg) pageProfileImageUrl = smallImg.src;
                    }
                    
                    const mediaItems = [];
                    if (video && video.url) {
                        let durSec = null;
                        const fullText = container.innerText || '';
                        const slashMatch = fullText.match(/\\/\\s*(\\d+):(\\d+)/);
                        if (slashMatch) durSec = parseInt(slashMatch[1], 10) * 60 + parseInt(slashMatch[2], 10);
                        else {
                            const m = fullText.match(/(\\d+):(\\d+)/);
                            if (m) durSec = parseInt(m[1], 10) * 60 + parseInt(m[2], 10);
                        }
                        mediaItems.push({ type: 'video', url: video.url, posterUrl: video.poster || null, durationSeconds: durSec, sortOrder: 0 });
                    }
                    for (let i = 0; i < largeImages.length; i++) {
                        const src = largeImages[i].url;
                        if (src && !mediaItems.some(m => m.url === src)) {
                            mediaItems.push({ type: 'image', url: src, posterUrl: null, durationSeconds: null, sortOrder: i });
                        }
                    }
                    
                    results.push({
                        libraryId: data.libraryId,
                        startedRunningOn: data.startedRunningOn,
                        endedRunningOn: data.endedRunningOn || null,
                        status: data.status || null,
                        adsUsingCreative: data.adsUsingCreative || null,
                        bodyText: bodyText,
                        headlineText: headlineText || null,
                        adFormat: adFormat,
                        mediaThumbnailUrl: mediaThumbnailUrl,
                        cta: cta,
                        destinationUrl: destinationUrl,
                        pageName: pageName,
                        pageUrl: pageUrl,
                        pageProfileImageUrl: pageProfileImageUrl,
                        mediaItems: mediaItems
                    });
                }
                return results;
            }
        ''')
        
        items = []
        for r in raw:
            body_text = (r.get('bodyText') or '').strip()
            headline_text = (r.get('headlineText') or '').strip() or None
            if not body_text:
                continue
            body_clean = re.sub(r'Library ID:\s*\d+', '', body_text, flags=re.IGNORECASE).strip()
            body_clean = re.sub(r'Started running on\s+[A-Za-z]+\s+\d{1,2},?\s+\d{4}', '', body_clean, flags=re.IGNORECASE).strip()
            body_clean = re.sub(r'\n\s*\n', '\n', body_clean).strip()
            if len(body_clean) < 5:
                continue
            if not headline_text:
                lines = [ln.strip() for ln in body_clean.split('\n') if ln.strip()]
                short_lines = [ln for ln in lines if len(ln) <= 120]
                headline_text = short_lines[0] if short_lines else (lines[0] if lines else None)
            key = (r.get('libraryId') or '', body_clean[:80])
            if key in seen_keys:
                continue
            seen_keys.add(key)
            media_items = []
            for m in (r.get('mediaItems') or []):
                media_items.append(MediaItemInfo(
                    media_type=m.get('type', 'image'),
                    url=(m.get('url') or '').strip(),
                    poster_url=(m.get('posterUrl') or '').strip() or None,
                    duration_seconds=m.get('durationSeconds'),
                    sort_order=int(m.get('sortOrder', 0)),
                ))
            platforms = r.get('platforms')
            if isinstance(platforms, list):
                pass
            else:
                platforms = None
            items.append(AdCopyItem(
                primary_text=body_clean[:5000],
                headline=headline_text,
                description=None,
                library_id=r.get('libraryId'),
                started_running_on=r.get('startedRunningOn'),
                ad_delivery_start_time=r.get('startedRunningOn'),
                ad_delivery_end_time=r.get('endedRunningOn'),
                ad_format=r.get('adFormat') or None,
                cta=(r.get('cta') or '').strip() or None,
                destination_url=(r.get('destinationUrl') or '').strip() or None,
                media_thumbnail_url=(r.get('mediaThumbnailUrl') or '').strip() or None,
                status=(r.get('status') or '').strip() or None,
                platforms=platforms,
                ads_using_creative_count=r.get('adsUsingCreative'),
                page_name=(r.get('pageName') or '').strip() or None,
                page_url=(r.get('pageUrl') or '').strip() or None,
                page_profile_image_url=(r.get('pageProfileImageUrl') or '').strip() or None,
                media_items=media_items if media_items else None,
            ))
        return items
    
    async def _extract_media_from_page(self, page, seen_urls: set) -> List[MediaItem]:
        """
        Extract media URLs from ad card containers only.
        This targets the actual ad creatives, not UI elements or sprite sheets.
        Uses text-based matching for metadata since Meta obfuscates class names.
        
        Args:
            page: Playwright page object
            seen_urls: Set of already seen URLs to avoid duplicates
            
        Returns:
            List of new MediaItem objects
        """
        media_items = []
        
        # Extract ad card data using text-based approach
        # Meta obfuscates class names, so we search for constant text patterns
        ad_data = await page.evaluate('''
            () => {
                const results = [];
                
                // Exclusion patterns for URLs we don't want
                const excludePatterns = [
                    '/rsrc.php/',      // Static resources
                    '/static/',        // Static files
                    '/emoji/',         // Emoji sprites
                    '/images/reaction', // Reaction icons
                    '/images/messaging', // Messaging icons
                    'data:image/',     // Data URIs (often small icons)
                    '/platform/',      // Platform icons
                    '/ajax/',          // AJAX resources
                    'sprite',          // Sprite sheets
                    '/share_icons/',   // Share icons
                    '/icons/',         // General icons
                    'transparent.gif', // Tracking pixels
                    'pixel',           // Tracking pixels
                    '/badge/',         // Badges
                    '/logo/',          // Logos (not ad content)
                    's60x60',          // Small thumbnails (like profile pics)
                    '_s60x60',         // Small thumbnails variant
                ];
                
                // Strategy: Find text elements containing "Library ID:" and "Started running on"
                // then find the nearest ad card container, then find media within that container
                
                // Get all text nodes containing our target patterns
                const allSpans = document.querySelectorAll('span');
                const adCards = new Map(); // Map of container -> {libraryId, startedRunningOn, media[]}
                
                for (const span of allSpans) {
                    const text = span.textContent?.trim() || '';
                    
                    // Look for "Library ID: {number}"
                    const libraryIdMatch = text.match(/^Library ID:\\s*(\\d+)$/);
                    if (libraryIdMatch) {
                        // Walk up to find a reasonable container (go up ~10-15 levels)
                        let container = span;
                        for (let i = 0; i < 15 && container.parentElement; i++) {
                            container = container.parentElement;
                            // Stop if we find a container that has both media and metadata
                            const hasVideo = container.querySelector('video[src]');
                            const hasImage = container.querySelector('img[src*="scontent"], img[src*="fbcdn"]');
                            if (hasVideo || hasImage) break;
                        }
                        
                        const key = container;
                        if (!adCards.has(key)) {
                            adCards.set(key, { libraryId: null, startedRunningOn: null, media: [] });
                        }
                        adCards.get(key).libraryId = libraryIdMatch[1];
                    }
                    
                    // Look for "Started running on {date}"
                    const dateMatch = text.match(/^Started running on\\s+([A-Za-z]+\\s+\\d{1,2},?\\s+\\d{4})$/);
                    if (dateMatch) {
                        // Walk up to find container
                        let container = span;
                        for (let i = 0; i < 15 && container.parentElement; i++) {
                            container = container.parentElement;
                            const hasVideo = container.querySelector('video[src]');
                            const hasImage = container.querySelector('img[src*="scontent"], img[src*="fbcdn"]');
                            if (hasVideo || hasImage) break;
                        }
                        
                        const key = container;
                        if (!adCards.has(key)) {
                            adCards.set(key, { libraryId: null, startedRunningOn: null, media: [] });
                        }
                        adCards.get(key).startedRunningOn = dateMatch[1];
                    }
                }
                
                // Now extract media from each identified ad card container
                for (const [container, cardData] of adCards) {
                    // Find videos in this container
                    const videos = container.querySelectorAll('video[src]');
                    for (const video of videos) {
                        const src = video.src;
                        if (!src) continue;
                        
                        // Check if from Meta CDN
                        const isMetaCDN = src.includes('fbcdn') || src.includes('video');
                        if (!isMetaCDN) continue;
                        
                        cardData.media.push({ url: src, type: 'video' });
                    }
                    
                    // Find images in this container
                    const images = container.querySelectorAll('img[src]');
                    for (const img of images) {
                        const src = img.src;
                        if (!src) continue;
                        
                        // Skip excluded patterns
                        const isExcluded = excludePatterns.some(pattern => 
                            src.toLowerCase().includes(pattern.toLowerCase())
                        );
                        if (isExcluded) continue;
                        
                        // Must be from Meta's content delivery
                        const isMetaCDN = src.includes('scontent') || 
                                         src.includes('fbcdn.net') ||
                                         src.includes('xx.fbcdn');
                        if (!isMetaCDN) continue;
                        
                        // Size check - skip small images (icons, profile pics)
                        const width = img.naturalWidth || img.width || 0;
                        const height = img.naturalHeight || img.height || 0;
                        if (width < 100 && height < 100) continue;
                        
                        cardData.media.push({ url: src, type: 'image' });
                    }
                    
                    // Add results for each media item with the card's metadata
                    for (const media of cardData.media) {
                        results.push({
                            url: media.url,
                            type: media.type,
                            startedRunningOn: cardData.startedRunningOn,
                            libraryId: cardData.libraryId
                        });
                    }
                }
                
                // Fallback: Also find media that might not be in identified containers
                // (in case some cards don't have the metadata text visible)
                const allVideos = document.querySelectorAll('video[src]');
                for (const video of allVideos) {
                    const src = video.src;
                    if (!src) continue;
                    if (!src.includes('fbcdn') && !src.includes('video')) continue;
                    
                    // Check if already found
                    const alreadyFound = results.some(r => r.url === src);
                    if (alreadyFound) continue;
                    
                    // Try to find metadata in ancestor text
                    let startedRunningOn = null;
                    let libraryId = null;
                    let ancestor = video.parentElement;
                    for (let i = 0; i < 20 && ancestor; i++) {
                        const text = ancestor.textContent || '';
                        if (!libraryId) {
                            const idMatch = text.match(/Library ID:\\s*(\\d+)/);
                            if (idMatch) libraryId = idMatch[1];
                        }
                        if (!startedRunningOn) {
                            const dateMatch = text.match(/Started running on\\s+([A-Za-z]+\\s+\\d{1,2},?\\s+\\d{4})/);
                            if (dateMatch) startedRunningOn = dateMatch[1];
                        }
                        if (libraryId && startedRunningOn) break;
                        ancestor = ancestor.parentElement;
                    }
                    
                    results.push({
                        url: src,
                        type: 'video',
                        startedRunningOn: startedRunningOn,
                        libraryId: libraryId
                    });
                }
                
                const allImages = document.querySelectorAll('img[src]');
                for (const img of allImages) {
                    const src = img.src;
                    if (!src) continue;
                    
                    // Skip excluded patterns
                    const isExcluded = excludePatterns.some(pattern => 
                        src.toLowerCase().includes(pattern.toLowerCase())
                    );
                    if (isExcluded) continue;
                    
                    // Must be from Meta's CDN
                    const isMetaCDN = src.includes('scontent') || 
                                     src.includes('fbcdn.net') ||
                                     src.includes('xx.fbcdn');
                    if (!isMetaCDN) continue;
                    
                    // Size check
                    const width = img.naturalWidth || img.width || 0;
                    const height = img.naturalHeight || img.height || 0;
                    if (width < 100 && height < 100) continue;
                    
                    // Check if already found
                    const alreadyFound = results.some(r => r.url === src);
                    if (alreadyFound) continue;
                    
                    // Try to find metadata in ancestor text
                    let startedRunningOn = null;
                    let libraryId = null;
                    let ancestor = img.parentElement;
                    for (let i = 0; i < 20 && ancestor; i++) {
                        const text = ancestor.textContent || '';
                        if (!libraryId) {
                            const idMatch = text.match(/Library ID:\\s*(\\d+)/);
                            if (idMatch) libraryId = idMatch[1];
                        }
                        if (!startedRunningOn) {
                            const dateMatch = text.match(/Started running on\\s+([A-Za-z]+\\s+\\d{1,2},?\\s+\\d{4})/);
                            if (dateMatch) startedRunningOn = dateMatch[1];
                        }
                        if (libraryId && startedRunningOn) break;
                        ancestor = ancestor.parentElement;
                    }
                    
                    results.push({
                        url: src,
                        type: 'image',
                        startedRunningOn: startedRunningOn,
                        libraryId: libraryId
                    });
                }
                
                // Deduplicate results by URL
                const uniqueResults = [];
                const seenUrls = new Set();
                for (const result of results) {
                    if (!seenUrls.has(result.url)) {
                        seenUrls.add(result.url);
                        uniqueResults.push(result);
                    }
                }
                
                return uniqueResults;
            }
        ''')
        
        # Log extraction stats
        items_with_metadata = sum(1 for item in ad_data if item.get('libraryId') or item.get('startedRunningOn'))
        logger.info(f"Extracted {len(ad_data)} media items, {items_with_metadata} with metadata")
        
        for item in ad_data:
            url = item['url']
            if url not in seen_urls:
                seen_urls.add(url)
                lib_id = item.get('libraryId')
                date = item.get('startedRunningOn')
                if lib_id or date:
                    logger.debug(f"Media item with metadata - Library ID: {lib_id}, Date: {date}")
                media_items.append(MediaItem(
                    url=url,
                    media_type=item['type'],
                    started_running_on=item.get('startedRunningOn'),
                    library_id=item.get('libraryId')
                ))
        
        return media_items


def parse_date_string(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse a date string like "Jan 15, 2024" into a datetime.
    
    Args:
        date_str: Date string from Meta Ads Library
        
    Returns:
        datetime or None if parsing fails
    """
    if not date_str:
        return None
    
    # Common date formats in Meta Ads Library
    formats = [
        "%b %d, %Y",    # Jan 15, 2024
        "%b %d %Y",     # Jan 15 2024
        "%B %d, %Y",    # January 15, 2024
        "%B %d %Y",     # January 15 2024
        "%d %b %Y",     # 15 Jan 2024
        "%d %B %Y",     # 15 January 2024
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    
    logger.warning(f"Could not parse date string: {date_str}")
    return None


async def download_and_upload_media(
    media_item: MediaItem,
    client_id: str,
    blob_token: str,
) -> Dict[str, Any]:
    """
    Download media from URL and upload to Vercel Blob.
    
    Args:
        media_item: MediaItem with URL and metadata
        client_id: Client UUID for organizing storage
        blob_token: Vercel Blob API token
        
    Returns:
        Dict with url, filename, file_size, content_type, and metadata
    """
    import vercel_blob
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Download the media
        response = await client.get(media_item.url, follow_redirects=True)
        response.raise_for_status()
        
        content = response.content
        content_type = response.headers.get('content-type', 'image/jpeg')
        
        # Generate filename
        ext = 'jpg'
        if 'video' in content_type:
            ext = 'mp4'
        elif 'png' in content_type:
            ext = 'png'
        elif 'gif' in content_type:
            ext = 'gif'
        elif 'webp' in content_type:
            ext = 'webp'
        
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=7))
        filename = f"meta-import-{int(time.time())}-{random_suffix}.{ext}"
        blob_path = f"ad-images/{client_id}/{filename}"
        
        # Upload to Vercel Blob
        blob = vercel_blob.put(blob_path, content, {
            "access": "public",
            "contentType": content_type,
            "token": blob_token,
        })
        
        blob_url = blob.get("url") if isinstance(blob, dict) else getattr(blob, 'url', str(blob))
        
        # Parse the date string into a datetime
        started_running_on = parse_date_string(media_item.started_running_on)
        
        return {
            "url": blob_url,
            "filename": filename,
            "file_size": len(content),
            "content_type": content_type,
            "started_running_on": started_running_on,
            "library_id": media_item.library_id,
        }
