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
from typing import List, Dict, Any, Optional
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
    
    async def _extract_media_from_page(self, page, seen_urls: set) -> List[MediaItem]:
        """
        Extract media URLs from ad card containers only.
        This targets the actual ad creatives, not UI elements or sprite sheets.
        
        Args:
            page: Playwright page object
            seen_urls: Set of already seen URLs to avoid duplicates
            
        Returns:
            List of new MediaItem objects
        """
        media_items = []
        
        # Extract ad card data using card-based approach
        # This finds each ad card container and extracts media + metadata together
        ad_data = await page.evaluate('''
            () => {
                const results = [];
                
                // Meta Ads Library structure: ads are in a grid/list layout
                // Look for the ad card containers - these typically have specific structure
                // with the ad preview image/video and metadata
                
                // Strategy: Find all images that are likely ad creatives based on:
                // 1. Size (ad images are typically larger than icons)
                // 2. Parent container structure
                // 3. Presence of nearby date/library ID elements
                // 4. NOT from static resource paths (sprite sheets, icons)
                
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
                ];
                
                // Find all substantial images on the page
                const allImages = document.querySelectorAll('img[src]');
                
                for (const img of allImages) {
                    const src = img.src;
                    if (!src) continue;
                    
                    // Skip excluded patterns
                    const isExcluded = excludePatterns.some(pattern => 
                        src.toLowerCase().includes(pattern.toLowerCase())
                    );
                    if (isExcluded) continue;
                    
                    // Must be from Meta's content delivery (scontent or fbcdn)
                    const isMetaCDN = src.includes('scontent') || 
                                     src.includes('fbcdn.net') ||
                                     src.includes('xx.fbcdn');
                    if (!isMetaCDN) continue;
                    
                    // Size check - ad images are typically larger
                    // Use both natural size and display size
                    const width = img.naturalWidth || img.width || 0;
                    const height = img.naturalHeight || img.height || 0;
                    if (width < 200 && height < 200) continue;
                    
                    // Look for ad container by walking up the DOM
                    // Ad cards typically have specific container structure
                    let container = img.closest('[class*="ad"], [role="article"], [data-ad-preview]');
                    if (!container) {
                        // Try to find a reasonable parent container
                        container = img.parentElement?.parentElement?.parentElement;
                    }
                    
                    // Try to extract metadata from nearby elements
                    let startedRunningOn = null;
                    let libraryId = null;
                    
                    if (container) {
                        // Look for "Started running on" text
                        const textContent = container.textContent || '';
                        const dateMatch = textContent.match(/Started running on\\s+([A-Za-z]+\\s+\\d{1,2},?\\s+\\d{4})/i);
                        if (dateMatch) {
                            startedRunningOn = dateMatch[1];
                        }
                        
                        // Look for library ID in links
                        const links = container.querySelectorAll('a[href*="library"]');
                        for (const link of links) {
                            const href = link.href || '';
                            const idMatch = href.match(/[?&]id=(\\d+)/);
                            if (idMatch) {
                                libraryId = idMatch[1];
                                break;
                            }
                        }
                        
                        // Also try to find "See ad details" link with ID
                        const detailsLink = container.querySelector('a[href*="ad-details"], a[aria-label*="details"]');
                        if (detailsLink && !libraryId) {
                            const href = detailsLink.href || '';
                            const idMatch = href.match(/[?&]id=(\\d+)/);
                            if (idMatch) {
                                libraryId = idMatch[1];
                            }
                        }
                    }
                    
                    results.push({
                        url: src,
                        type: 'image',
                        startedRunningOn: startedRunningOn,
                        libraryId: libraryId
                    });
                }
                
                // Find videos in ad cards
                const allVideos = document.querySelectorAll('video');
                for (const video of allVideos) {
                    // Get video source
                    let src = video.src;
                    if (!src) {
                        const source = video.querySelector('source');
                        src = source?.src;
                    }
                    if (!src) continue;
                    
                    // Check if from Meta CDN
                    const isMetaCDN = src.includes('fbcdn') || src.includes('video');
                    if (!isMetaCDN) continue;
                    
                    // Get parent container for metadata
                    let container = video.closest('[class*="ad"], [role="article"], [data-ad-preview]');
                    if (!container) {
                        container = video.parentElement?.parentElement?.parentElement;
                    }
                    
                    let startedRunningOn = null;
                    let libraryId = null;
                    
                    if (container) {
                        const textContent = container.textContent || '';
                        const dateMatch = textContent.match(/Started running on\\s+([A-Za-z]+\\s+\\d{1,2},?\\s+\\d{4})/i);
                        if (dateMatch) {
                            startedRunningOn = dateMatch[1];
                        }
                        
                        const links = container.querySelectorAll('a[href*="library"]');
                        for (const link of links) {
                            const href = link.href || '';
                            const idMatch = href.match(/[?&]id=(\\d+)/);
                            if (idMatch) {
                                libraryId = idMatch[1];
                                break;
                            }
                        }
                    }
                    
                    results.push({
                        url: src,
                        type: 'video',
                        startedRunningOn: startedRunningOn,
                        libraryId: libraryId
                    });
                }
                
                return results;
            }
        ''')
        
        for item in ad_data:
            url = item['url']
            if url not in seen_urls:
                seen_urls.add(url)
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
