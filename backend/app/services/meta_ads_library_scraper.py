"""
Meta Ads Library Scraper Service.
Scrapes media (images and videos) from Meta Ads Library pages using Playwright.
"""

import logging
import asyncio
import httpx
import os
import time
import random
import string
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, parse_qs
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MediaItem:
    """Represents a media item scraped from the Ads Library."""
    url: str
    media_type: str  # 'image' or 'video'
    filename: Optional[str] = None


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
                    
                    logger.info(f"Scroll {scroll_num + 1}: Found {len(new_media)} new media items")
                    
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
                
                logger.info(f"Total media items found: {len(media_items)}")
                
            finally:
                await browser.close()
        
        return media_items
    
    async def _extract_media_from_page(self, page, seen_urls: set) -> List[MediaItem]:
        """
        Extract media URLs from the current page state.
        
        Args:
            page: Playwright page object
            seen_urls: Set of already seen URLs to avoid duplicates
            
        Returns:
            List of new MediaItem objects
        """
        media_items = []
        
        # Extract image URLs from ad cards
        # Meta Ads Library uses various image containers
        images = await page.evaluate('''
            () => {
                const images = [];
                
                // Find all images in the page
                const imgElements = document.querySelectorAll('img[src]');
                for (const img of imgElements) {
                    const src = img.src;
                    // Filter for ad images (usually from scontent or fbcdn)
                    if (src && (
                        src.includes('scontent') || 
                        src.includes('fbcdn') ||
                        src.includes('external')
                    )) {
                        // Skip tiny images (likely icons)
                        if (img.naturalWidth > 100 || img.width > 100) {
                            images.push({
                                url: src,
                                type: 'image'
                            });
                        }
                    }
                }
                
                // Find video sources
                const videoElements = document.querySelectorAll('video source[src], video[src]');
                for (const video of videoElements) {
                    const src = video.src || video.getAttribute('src');
                    if (src && (src.includes('video') || src.includes('fbcdn'))) {
                        images.push({
                            url: src,
                            type: 'video'
                        });
                    }
                }
                
                // Also check for background images in ad cards
                const divs = document.querySelectorAll('[style*="background-image"]');
                for (const div of divs) {
                    const style = div.getAttribute('style') || '';
                    const match = style.match(/url\\(['"']?([^'"')]+)['"']?\\)/);
                    if (match && match[1] && (
                        match[1].includes('scontent') || 
                        match[1].includes('fbcdn')
                    )) {
                        images.push({
                            url: match[1],
                            type: 'image'
                        });
                    }
                }
                
                return images;
            }
        ''')
        
        for item in images:
            url = item['url']
            if url not in seen_urls:
                seen_urls.add(url)
                media_items.append(MediaItem(
                    url=url,
                    media_type=item['type']
                ))
        
        return media_items


async def download_and_upload_media(
    media_url: str,
    client_id: str,
    blob_token: str,
) -> Dict[str, Any]:
    """
    Download media from URL and upload to Vercel Blob.
    
    Args:
        media_url: URL of the media to download
        client_id: Client UUID for organizing storage
        blob_token: Vercel Blob API token
        
    Returns:
        Dict with url, filename, file_size, content_type
    """
    import vercel_blob
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Download the media
        response = await client.get(media_url, follow_redirects=True)
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
        
        return {
            "url": blob_url,
            "filename": filename,
            "file_size": len(content),
            "content_type": content_type,
        }
