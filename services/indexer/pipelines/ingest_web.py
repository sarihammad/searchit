"""
Web ingestion pipeline for SearchIt
"""

import asyncio
import logging
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import aiohttp
from bs4 import BeautifulSoup
import yaml

logger = logging.getLogger(__name__)

class WebIngester:
    """Web content ingestion with robots.txt compliance"""
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.session = None
        self.robots_cache = {}
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        default_config = {
            "user_agent": "SearchIt-Bot/1.0",
            "timeout": 30,
            "max_content_length": 10 * 1024 * 1024,  # 10MB
            "respect_robots": True,
            "allowed_domains": [],
            "max_pages": 100
        }
        
        if config_path:
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    default_config.update(config)
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
        
        return default_config
    
    async def __aenter__(self):
        """Async context manager entry"""
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=self.config["timeout"])
        headers = {"User-Agent": self.config["user_agent"]}
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def fetch_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch and parse a single URL"""
        try:
            # Check robots.txt compliance
            if self.config["respect_robots"] and not await self._can_fetch(url):
                logger.info(f"Robots.txt disallows fetching: {url}")
                return None
            
            logger.info(f"Fetching URL: {url}")
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return None
                
                # Check content length
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > self.config["max_content_length"]:
                    logger.warning(f"Content too large: {url}")
                    return None
                
                # Get content
                content = await response.text()
                content_type = response.headers.get('content-type', '')
                
                # Parse HTML
                if 'text/html' in content_type:
                    return await self._parse_html(url, content)
                else:
                    logger.warning(f"Unsupported content type: {content_type}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None
    
    async def _parse_html(self, url: str, html: str) -> Dict[str, Any]:
        """Parse HTML content and extract text"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Extract title
            title_elem = soup.find('title')
            title = title_elem.get_text().strip() if title_elem else ""
            
            # Extract main content
            # Try to find main content area
            main_content = None
            for selector in ['main', 'article', '.content', '#content', 'body']:
                main_content = soup.select_one(selector)
                if main_content:
                    break
            
            if not main_content:
                main_content = soup.body
            
            # Extract text
            text = main_content.get_text(separator='\n', strip=True)
            
            # Clean up text
            text = self._clean_text(text)
            
            # Extract metadata
            meta_description = ""
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                meta_description = meta_desc.get('content', '').strip()
            
            # Extract links for potential crawling
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(url, href)
                if self._is_valid_url(absolute_url):
                    links.append(absolute_url)
            
            return {
                "url": url,
                "title": title,
                "text": text,
                "meta_description": meta_description,
                "links": links,
                "source": "web"
            }
            
        except Exception as e:
            logger.error(f"Failed to parse HTML from {url}: {e}")
            return None
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # Normalize unicode
        text = text.encode('utf-8', errors='ignore').decode('utf-8')
        
        return text.strip()
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid for crawling"""
        try:
            parsed = urlparse(url)
            
            # Must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Must be HTTP or HTTPS
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Check allowed domains
            allowed_domains = self.config.get("allowed_domains", [])
            if allowed_domains and parsed.netloc not in allowed_domains:
                return False
            
            # Skip common non-content URLs
            skip_patterns = [
                r'\.(pdf|doc|docx|xls|xlsx|ppt|pptx|zip|tar|gz)$',
                r'\.(jpg|jpeg|png|gif|svg|ico)$',
                r'\.(css|js|xml|json)$'
            ]
            
            for pattern in skip_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return False
            
            return True
            
        except Exception:
            return False
    
    async def _can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt"""
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            
            # Check cache first
            if robots_url in self.robots_cache:
                return self._check_robots_rule(self.robots_cache[robots_url], url)
            
            # Fetch robots.txt
            try:
                async with self.session.get(robots_url) as response:
                    if response.status == 200:
                        robots_content = await response.text()
                        self.robots_cache[robots_url] = robots_content
                        return self._check_robots_rule(robots_content, url)
            except Exception:
                pass
            
            # Default to allowing if robots.txt not accessible
            return True
            
        except Exception:
            return True
    
    def _check_robots_rule(self, robots_content: str, url: str) -> bool:
        """Check if URL is allowed by robots.txt rules"""
        try:
            user_agent = self.config["user_agent"]
            lines = robots_content.split('\n')
            
            current_user_agent = None
            disallowed_patterns = []
            allowed_patterns = []
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if line.lower().startswith('user-agent:'):
                    current_user_agent = line[11:].strip()
                elif line.lower().startswith('disallow:'):
                    if current_user_agent == '*' or current_user_agent == user_agent:
                        pattern = line[9:].strip()
                        if pattern:
                            disallowed_patterns.append(pattern)
                elif line.lower().startswith('allow:'):
                    if current_user_agent == '*' or current_user_agent == user_agent:
                        pattern = line[6:].strip()
                        if pattern:
                            allowed_patterns.append(pattern)
            
            # Check if URL matches any disallowed patterns
            parsed = urlparse(url)
            path = parsed.path
            
            for pattern in disallowed_patterns:
                if self._matches_pattern(path, pattern):
                    # Check if there's an allow pattern that overrides
                    for allow_pattern in allowed_patterns:
                        if self._matches_pattern(path, allow_pattern):
                            return True
                    return False
            
            return True
            
        except Exception:
            return True
    
    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if path matches robots.txt pattern"""
        if not pattern:
            return False
        
        # Convert robots.txt pattern to regex
        regex_pattern = pattern.replace('*', '.*')
        if not regex_pattern.endswith('$'):
            regex_pattern += '.*'
        
        return re.match(regex_pattern, path) is not None

async def ingest_website(url: str, max_pages: int = 10) -> List[Dict[str, Any]]:
    """Ingest a website starting from a URL"""
    documents = []
    visited_urls = set()
    urls_to_visit = [url]
    
    async with WebIngester() as ingester:
        while urls_to_visit and len(documents) < max_pages:
            current_url = urls_to_visit.pop(0)
            
            if current_url in visited_urls:
                continue
            
            visited_urls.add(current_url)
            
            doc = await ingester.fetch_url(current_url)
            if doc:
                documents.append(doc)
                
                # Add new URLs to visit queue
                for link in doc.get("links", []):
                    if link not in visited_urls and len(urls_to_visit) < max_pages * 2:
                        urls_to_visit.append(link)
    
    logger.info(f"Ingested {len(documents)} documents from {url}")
    return documents

if __name__ == "__main__":
    import asyncio
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python ingest_web.py <url> [max_pages]")
        sys.exit(1)
    
    url = sys.argv[1]
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    documents = asyncio.run(ingest_website(url, max_pages))
    
    for doc in documents:
        print(f"Title: {doc['title']}")
        print(f"URL: {doc['url']}")
        print(f"Text length: {len(doc['text'])}")
        print("---")
