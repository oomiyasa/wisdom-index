"""
Base Harvester Class

Provides common functionality and improved exception handling for all platform harvesters.
"""

import csv
import json
import logging
import os
import re
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HarvesterError(Exception):
    """Base exception for harvester errors"""
    pass


class ConfigurationError(HarvesterError):
    """Raised when harvester configuration is invalid"""
    pass


class RateLimitError(HarvesterError):
    """Raised when API rate limit is exceeded"""
    pass


class BaseHarvester(ABC):
    """Base class for all platform harvesters"""
    
    def __init__(self, config: Dict[str, Any], platform_name: str):
        self.config = config
        self.platform_name = platform_name
        self.logger = logging.getLogger(f"{__name__}.{platform_name}")
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate harvester configuration"""
        if not isinstance(self.config, dict):
            raise ConfigurationError(f"Invalid config for {self.platform_name}: must be a dictionary")
    
    def _safe_text(self, text: Any, max_length: Optional[int] = None) -> str:
        """Safely process text content"""
        if text is None:
            return ""
        
        try:
            text = str(text).replace("\r", " ").replace("\n", " ").strip()
            text = re.sub(r"\s+", " ", text)
            
            if max_length and len(text) > max_length:
                return text[:max_length-1] + "…"
            
            return text
        except Exception as e:
            self.logger.warning(f"Error processing text: {e}")
            return ""
    
    def _make_request(self, url: str, headers: Optional[Dict] = None, 
                     timeout: int = 10, retries: int = 3) -> requests.Response:
        """Make HTTP request with proper error handling and retries"""
        for attempt in range(retries):
            try:
                response = requests.get(url, headers=headers, timeout=timeout)
                response.raise_for_status()
                return response
                
            except Timeout:
                self.logger.warning(f"Request timeout (attempt {attempt + 1}/{retries})")
                if attempt == retries - 1:
                    raise HarvesterError(f"Request timeout after {retries} attempts")
                    
            except ConnectionError as e:
                self.logger.warning(f"Connection error (attempt {attempt + 1}/{retries}): {e}")
                if attempt == retries - 1:
                    raise HarvesterError(f"Connection error after {retries} attempts: {e}")
                    
            except RequestException as e:
                if response.status_code == 429:  # Rate limit
                    retry_after = int(response.headers.get('Retry-After', 60))
                    self.logger.warning(f"Rate limited, waiting {retry_after} seconds")
                    time.sleep(retry_after)
                    continue
                else:
                    raise HarvesterError(f"Request failed: {e}")
            
            # Exponential backoff
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
        
        raise HarvesterError(f"Request failed after {retries} attempts")
    
    def _throttle(self, delay: float = 1.0):
        """Throttle requests to respect rate limits"""
        time.sleep(delay)
    
    def _save_results(self, results: List[Dict[str, Any]], output_file: str):
        """Save results to CSV file"""
        if not results:
            self.logger.warning("No results to save")
            return
        
        try:
            # Ensure output directory exists
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)
            
            self.logger.info(f"Saved {len(results)} results to {output_file}")
            
        except Exception as e:
            raise HarvesterError(f"Failed to save results: {e}")
    
    def _contains_tacit_knowledge(self, text: str, keywords: List[str]) -> bool:
        """Check if text contains tacit knowledge indicators"""
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Check for keywords (if provided)
        if keywords:
            keyword_found = False
            for keyword in keywords:
                # Handle different keyword formats
                keyword_variants = [
                    keyword.lower(),
                    keyword.lower().replace('_', ' '),
                    keyword.lower().replace('_', ''),
                    keyword.lower().replace('_', '-')
                ]
                for variant in keyword_variants:
                    if variant in text_lower:
                        keyword_found = True
                        break
                if keyword_found:
                    break
            
            if keyword_found:
                return True  # If we found a keyword match, return True immediately
        
        # Check for tacit knowledge patterns
        tacit_patterns = [
            r'\b(pro tip|tip|trick|hack|workaround|shortcut)\b',
            r'\b(lesson learned|learned that|found that)\b',
            r'\b(the key is|the secret is|the trick is)\b',
            r'\b(my approach|my method|my strategy)\b',
            r'\b(always|never|avoid|make sure)\b',
            r'\b(because|so that|reason|works when)\b',
            r'\b(wish i knew|should have|would have)\b',
            r'\b(experience shows|in practice|actually works)\b',
            r'\b(common mistake|typical problem|usual issue)\b',
            r'\b(quick fix|easy solution|simple trick)\b'
        ]
        
        return any(re.search(pattern, text_lower) for pattern in tacit_patterns)
    
    @abstractmethod
    def harvest(self) -> List[Dict[str, Any]]:
        """Harvest insights from the platform"""
        pass
    
    def run(self, output_file: Optional[str] = None) -> List[Dict[str, Any]]:
        """Run the harvester and optionally save results"""
        try:
            self.logger.info(f"Starting {self.platform_name} harvest")
            results = self.harvest()
            self.logger.info(f"Completed {self.platform_name} harvest: {len(results)} results")
            
            if output_file:
                self._save_results(results, output_file)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Harvest failed: {e}")
            raise
