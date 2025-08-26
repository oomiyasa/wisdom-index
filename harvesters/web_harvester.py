"""
Web Harvester Module

Harvests insights from web forums and discussion boards.
"""

import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .base_harvester import BaseHarvester, HarvesterError, ConfigurationError


class WebHarvester(BaseHarvester):
    """Harvester for web forum content"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config, "Web")
        
        # Set up headers to mimic a real browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def harvest(self) -> List[Dict[str, Any]]:
        """Harvest insights from web forums"""
        results = []
        
        try:
            web_config = self.config.get("web", {})
            sites = web_config.get("sites", [])
            harvest_config = web_config.get("harvest", {})
            
            if not sites:
                self.logger.warning("No web sites configured for web harvesting")
                return results
            
            for site_config in sites:
                try:
                    site_results = self._harvest_site(site_config, harvest_config)
                    results.extend(site_results)
                    self.logger.info(f"Harvested {len(site_results)} items from {site_config.get('name', 'Unknown')}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to harvest from {site_config.get('name', 'Unknown')}: {e}")
                    continue
            
            return results
            
        except Exception as e:
            raise HarvesterError(f"Web harvest failed: {e}")
    
    def _harvest_site(self, site_config: Dict[str, Any], harvest_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Harvest from a specific web site"""
        results = []
        
        try:
            site_name = site_config.get("name", "Unknown")
            base_url = site_config.get("url")
            forum_urls = site_config.get("forum_urls", [])
            selectors = site_config.get("selectors", {})
            
            if not base_url:
                self.logger.warning(f"No base URL configured for {site_name}")
                return results
            
            # Get configuration parameters
            limit_per_forum = harvest_config.get("limit_per_forum", 20)
            throttle_sec = harvest_config.get("throttle_sec", 2.0)
            min_content_length = harvest_config.get("min_content_length", 50)
            
            for forum_url in forum_urls:
                try:
                    full_url = urljoin(base_url, forum_url)
                    forum_results = self._harvest_forum_page(
                        full_url, site_name, selectors, limit_per_forum, min_content_length
                    )
                    results.extend(forum_results)
                    
                    # Throttle between requests
                    self._throttle(throttle_sec)
                    
                except Exception as e:
                    self.logger.error(f"Failed to harvest forum {forum_url}: {e}")
                    continue
            
            return results
            
        except Exception as e:
            raise HarvesterError(f"Site harvest failed: {e}")
    
    def _harvest_forum_page(self, url: str, site_name: str, selectors: Dict[str, str],
                           limit: int, min_content_length: int) -> List[Dict[str, Any]]:
        """Harvest from a specific forum page"""
        results = []

        try:
            # Check if this is a JavaScript-heavy site that needs Selenium
            if "kaggle.com" in url:
                return self._harvest_with_selenium(url, site_name, selectors, limit, min_content_length)
            
            # Make request to the forum page
            response = self._make_request(url, headers=self.headers)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract threads/posts based on selectors
            thread_selector = selectors.get("thread", ".thread, .post, .topic")
            title_selector = selectors.get("title", ".title, .subject, h1, h2, h3")
            content_selector = selectors.get("content", ".content, .message, .body, .text")
            author_selector = selectors.get("author", ".author, .username, .user")
            date_selector = selectors.get("date", ".date, .timestamp, .time")

            # Find thread elements
            threads = soup.select(thread_selector)
            
            for i, thread in enumerate(threads[:limit]):
                try:
                    # Extract thread information
                    title_elem = thread.select_one(title_selector)
                    content_elem = thread.select_one(content_selector)
                    author_elem = thread.select_one(author_selector)
                    date_elem = thread.select_one(date_selector)
                    
                    if not content_elem:
                        continue
                    
                    title = self._safe_text(title_elem.get_text()) if title_elem else ""
                    content = self._safe_text(content_elem.get_text())
                    author = self._safe_text(author_elem.get_text()) if author_elem else "Anonymous"
                    date = self._safe_text(date_elem.get_text()) if date_elem else ""
                    
                    # Skip if content is too short
                    if len(content) < min_content_length:
                        continue
                    
                    # Check for tacit knowledge
                    keywords = self.config.get("keywords", [])
                    contains_tacit = self._contains_tacit_knowledge(content, keywords)
                    
                    if contains_tacit:
                        result = {
                            'site': 'web',
                            'subreddit': site_name,  # Using subreddit field for consistency
                            'title': title,
                            'description': content,
                            'author': author,
                            'score': 1,  # Default score for web content
                            'url': url,
                            'created_utc': time.time(),
                            'num_comments': 0,
                            'source_(interview_#/_name)': f'web/{site_name}/{author}',
                            'link': url,
                            'notes': f'site: {site_name} | author: {author} | tacit: {contains_tacit}'
                        }
                        results.append(result)
                
                except Exception as e:
                    self.logger.warning(f"Failed to process thread {i}: {e}")
                    continue
            
            return results
            
        except Exception as e:
            raise HarvesterError(f"Forum page harvest failed: {e}")
    
    def _extract_contractortalk_content(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract content specifically from contractortalk.com"""
        results = []
        
        try:
            # Contractortalk.com specific selectors
            # These would need to be adjusted based on the actual HTML structure
            threads = soup.select('.thread, .post, .topic, .message')
            
            for thread in threads:
                try:
                    # Extract title
                    title_elem = thread.select_one('.title, .subject, h1, h2, h3')
                    title = self._safe_text(title_elem.get_text()) if title_elem else ""
                    
                    # Extract content
                    content_elem = thread.select_one('.content, .message, .body, .text, .post-content')
                    if not content_elem:
                        continue
                    
                    content = self._safe_text(content_elem.get_text())
                    
                    # Extract author
                    author_elem = thread.select_one('.author, .username, .user, .member-name')
                    author = self._safe_text(author_elem.get_text()) if author_elem else "Anonymous"
                    
                    # Extract date
                    date_elem = thread.select_one('.date, .timestamp, .time, .post-date')
                    date = self._safe_text(date_elem.get_text()) if date_elem else ""
                    
                    # Check for tacit knowledge
                    keywords = self.config.get("keywords", [])
                    contains_tacit = self._contains_tacit_knowledge(content, keywords)
                    
                    if contains_tacit and len(content) > 50:
                        result = {
                            'site': 'web',
                            'subreddit': 'contractortalk',
                            'title': title,
                            'description': content,
                            'author': author,
                            'score': 1,
                            'url': 'https://contractortalk.com',
                            'created_utc': time.time(),
                            'num_comments': 0,
                            'source_(interview_#/_name)': f'web/contractortalk/{author}',
                            'link': 'https://contractortalk.com',
                            'notes': f'site: contractortalk | author: {author} | tacit: {contains_tacit}'
                        }
                        results.append(result)
                
                except Exception as e:
                    self.logger.warning(f"Failed to process contractortalk thread: {e}")
                    continue
            
            return results
            
        except Exception as e:
            raise HarvesterError(f"Contractortalk content extraction failed: {e}")

    def _harvest_with_selenium(self, url: str, site_name: str, selectors: Dict[str, str],
                             limit: int, min_content_length: int) -> List[Dict[str, Any]]:
        """Harvest from JavaScript-heavy sites using Selenium"""
        results = []
        driver = None

        try:
            # Set up Chrome options for headless browsing
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument(f"--user-agent={self.headers['User-Agent']}")

            # Initialize driver
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(url)

            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Additional wait for dynamic content
            time.sleep(3)

            # Extract threads/posts based on selectors
            thread_selector = selectors.get("thread", ".thread, .post, .topic")
            title_selector = selectors.get("title", ".title, .subject, h1, h2, h3")
            content_selector = selectors.get("content", ".content, .message, .body, .text")
            author_selector = selectors.get("author", ".author, .username, .user")
            date_selector = selectors.get("date", ".date, .timestamp, .time")

            # Get the page source after JavaScript has loaded
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Find thread elements using BeautifulSoup instead of Selenium
            threads = soup.select(thread_selector)

            for i, thread in enumerate(threads[:limit]):
                try:
                    # Extract thread information using BeautifulSoup
                    title_elems = thread.select(title_selector)
                    content_elems = thread.select(content_selector)
                    author_elems = thread.select(author_selector)
                    date_elems = thread.select(date_selector)
                    
                    # Extract text
                    title = self._safe_text(title_elems[0].get_text()) if title_elems else ""
                    content = self._safe_text(" ".join([elem.get_text() for elem in content_elems]))
                    author = self._safe_text(author_elems[0].get_text()) if author_elems else "Anonymous"
                    date = self._safe_text(date_elems[0].get_text()) if date_elems else ""
                    
                    # Skip if content is too short
                    if len(content) < min_content_length:
                        continue

                    # Check for tacit knowledge
                    keywords = self.config.get("keywords", [])
                    contains_tacit = self._contains_tacit_knowledge(content, keywords)

                    if contains_tacit:
                        result = {
                            'site': 'web',
                            'subreddit': site_name,  # Using subreddit field for consistency
                            'title': title,
                            'description': content,
                            'author': author,
                            'score': 1,  # Default score for web content
                            'url': url,
                            'created_utc': time.time(),
                            'num_comments': 0,
                            'source_(interview_#/_name)': f'web/{site_name}/{author}',
                            'link': url,
                            'notes': f'site: {site_name} | author: {author} | tacit: {contains_tacit}'
                        }
                        results.append(result)

                except Exception as e:
                    self.logger.warning(f"Failed to process thread {i}: {e}")
                    continue

        except Exception as e:
            raise HarvesterError(f"Selenium harvest failed: {e}")
        finally:
            if driver:
                driver.quit()

        return results
