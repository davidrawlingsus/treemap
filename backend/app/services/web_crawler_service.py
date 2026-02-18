"""
Web crawler service for extracting brand copy from websites.
Used for generating tone of voice guides.
"""

import logging
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Patterns for discovering key brand pages
KEY_PAGE_PATTERNS = [
    '/about', '/about-us', '/our-story', '/who-we-are',
    '/products', '/services', '/solutions', '/what-we-do',
    '/team', '/people', '/leadership',
    '/mission', '/values', '/culture', '/why-us',
    '/brand', '/story'
]


class WebCrawlerService:
    """Service for crawling brand websites and extracting copy."""
    
    def __init__(self, timeout: int = 10, max_chars_per_page: int = 3000):
        self.timeout = timeout
        self.max_chars_per_page = max_chars_per_page
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def fetch_single_page(self, url: str, max_chars: int = 10000) -> Optional[str]:
        """
        Fetch and extract text content from a single page (e.g. a PDP).
        Uses a higher character limit than crawl_brand_pages for content-heavy pages.

        Args:
            url: The page URL to fetch
            max_chars: Maximum characters to return (default 10000 for PDPs)

        Returns:
            Extracted text content, or None on error
        """
        original_limit = self.max_chars_per_page
        self.max_chars_per_page = max_chars
        try:
            text, _ = self._fetch_page_content(url)
            return text
        finally:
            self.max_chars_per_page = original_limit

    def crawl_brand_pages(self, base_url: str, max_pages: int = 4) -> Dict:
        """
        Crawl a brand's website and extract copy from key pages.
        
        Args:
            base_url: The brand's website URL
            max_pages: Maximum number of pages to crawl (including homepage)
            
        Returns:
            Dict with:
                - pages_crawled: List of page info (url, title, content_length)
                - combined_copy: All extracted copy combined
                - error: Error message if any page failed
        """
        result = {
            'pages_crawled': [],
            'combined_copy': '',
            'errors': []
        }
        
        # Normalize base URL
        if not base_url.startswith(('http://', 'https://')):
            base_url = 'https://' + base_url
        
        parsed_base = urlparse(base_url)
        base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
        
        # Start with homepage
        homepage_content, homepage_soup = self._fetch_page_content(base_url)
        
        if homepage_content:
            result['pages_crawled'].append({
                'url': base_url,
                'title': self._get_page_title(homepage_soup),
                'content_length': len(homepage_content)
            })
            result['combined_copy'] = f"=== Homepage ===\n{homepage_content}\n\n"
        else:
            result['errors'].append(f"Failed to fetch homepage: {base_url}")
            return result
        
        # Discover and crawl key pages
        if homepage_soup and max_pages > 1:
            key_pages = self._discover_key_pages(homepage_soup, base_domain)
            
            pages_remaining = max_pages - 1
            for page_url, page_name in key_pages[:pages_remaining]:
                page_content, page_soup = self._fetch_page_content(page_url)
                
                if page_content:
                    result['pages_crawled'].append({
                        'url': page_url,
                        'title': self._get_page_title(page_soup) or page_name,
                        'content_length': len(page_content)
                    })
                    result['combined_copy'] += f"=== {page_name.title()} Page ===\n{page_content}\n\n"
                else:
                    result['errors'].append(f"Failed to fetch {page_name} page: {page_url}")
        
        logger.info(f"Crawled {len(result['pages_crawled'])} pages from {base_url}")
        return result
    
    def _fetch_page_content(self, url: str) -> tuple[Optional[str], Optional[BeautifulSoup]]:
        """
        Fetch and extract text content from a single page.
        
        Returns:
            Tuple of (extracted_text, soup) or (None, None) on error
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove non-content elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 
                                 'noscript', 'iframe', 'form', 'button']):
                element.decompose()
            
            # Extract text content
            text = soup.get_text(separator='\n', strip=True)
            
            # Clean up excessive whitespace
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            text = '\n'.join(lines)
            
            # Limit content length
            if len(text) > self.max_chars_per_page:
                text = text[:self.max_chars_per_page] + '...'
            
            return text, soup
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return None, None
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            return None, None
    
    def _discover_key_pages(self, soup: BeautifulSoup, base_domain: str) -> List[tuple[str, str]]:
        """
        Discover key brand pages from homepage links.
        
        Returns:
            List of (url, page_name) tuples
        """
        discovered = []
        seen_paths = set()
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').lower()
            
            # Check if this link matches any key page patterns
            for pattern in KEY_PAGE_PATTERNS:
                if pattern in href:
                    # Normalize the URL
                    full_url = urljoin(base_domain, link.get('href'))
                    parsed = urlparse(full_url)
                    
                    # Only include same-domain links
                    if parsed.netloc == urlparse(base_domain).netloc:
                        path = parsed.path.rstrip('/')
                        
                        # Avoid duplicates
                        if path not in seen_paths:
                            seen_paths.add(path)
                            # Extract page name from pattern
                            page_name = pattern.strip('/').replace('-', ' ')
                            discovered.append((full_url, page_name))
                            break  # Found a match, move to next link
        
        logger.debug(f"Discovered {len(discovered)} key pages: {[p[1] for p in discovered]}")
        return discovered
    
    def _get_page_title(self, soup: Optional[BeautifulSoup]) -> Optional[str]:
        """Extract page title from soup."""
        if soup:
            title_tag = soup.find('title')
            if title_tag:
                return title_tag.get_text(strip=True)
        return None
