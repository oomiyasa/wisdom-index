#!/usr/bin/env python3
"""
Main Harvester - Modular Wisdom Index Harvester

Usage:
  python3 harvester_main.py --config wi_config_unified.yaml

This script follows the workflow:
1. Harvest raw data from platforms
2. Filter for quality
3. Transform with OpenAI
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import yaml
from dotenv import load_dotenv

# Import modular harvesters
from harvesters import (
    RedditHarvester, GitHubHarvester, StackExchangeHarvester,
    MediumHarvester, YouTubeHarvester, PodcastHarvester, WebHarvester
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HarvesterManager:
    """Manages the harvesting workflow"""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self._load_config()
        self.harvesters = {}
        self._initialize_harvesters()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _load_search_history(self) -> Optional[Dict[str, Any]]:
        """Load search history from JSON file"""
        history_file = "search_history.json"
        if not os.path.exists(history_file):
            logger.warning(f"Search history file not found: {history_file}")
            return None
        
        try:
            with open(history_file, 'r') as f:
                history = json.load(f)
            logger.info(f"Loaded search history with {len(history.get('searches', []))} previous searches")
            return history
        except Exception as e:
            logger.error(f"Failed to load search history: {e}")
            return None
    
    def _save_search_history(self, results: Dict[str, List[Dict[str, Any]]]):
        """Save current search configuration to history"""
        try:
            # Load existing history
            history = self._load_search_history() or {"searches": []}
            
            # Extract current configuration
            current_config = self._extract_current_search_config()
            
            # Add results count
            total_results = sum(len(items) for items in results.values())
            current_config['results_count'] = total_results
            
            # Add to history
            history['searches'].append(current_config)
            
            # Save back to file
            with open("search_history.json", 'w') as f:
                json.dump(history, f, indent=2)
            
            logger.info(f"Saved search configuration to history (total results: {total_results})")
            
        except Exception as e:
            logger.error(f"Failed to save search history: {e}")
    
    def _check_for_duplicate_searches(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """Check if current configuration duplicates previous searches"""
        history = self._load_search_history()
        if not history:
            return False, []
        
        current_config = self._extract_current_search_config()
        duplicates = []
        
        for search in history.get('searches', []):
            if self._is_duplicate_search(current_config, search):
                duplicates.append(search)
        
        return len(duplicates) > 0, duplicates
    
    def _extract_current_search_config(self) -> Dict[str, Any]:
        """Extract current search configuration for comparison"""
        config = {
            'platforms': [],
            'sources': {},
            'keywords': self.config.get('keywords', []),
            'industry_modifiers': self.config.get('industry_modifiers', []),
            'timestamp': datetime.now().isoformat()
        }
        
        # Extract platform-specific configurations
        sources = self.config.get('sources', {})
        
        if sources.get('reddit', False):
            config['platforms'].append('reddit')
            reddit_config = self.config.get('reddit', {})
            config['sources']['reddit'] = {
                'subreddits': reddit_config.get('subreddits', []),
                'harvest': reddit_config.get('harvest', {}),
                'modes': reddit_config.get('harvest', {}).get('modes', []),
                'comments': reddit_config.get('harvest', {}).get('comments', {}),
                'filters': reddit_config.get('harvest', {}).get('filters', {})
            }
        
        if sources.get('web', False):
            config['platforms'].append('web')
            config['sources']['web'] = {
                'sites': self.config.get('web', {}).get('sites', []),
                'harvest': self.config.get('web', {}).get('harvest', {})
            }
        
        if sources.get('github', False):
            config['platforms'].append('github')
            config['sources']['github'] = {
                'repos': self.config.get('github', {}).get('repos', []),
                'harvest': self.config.get('github', {}).get('harvest', {})
            }
        
        if sources.get('stackexchange', False):
            config['platforms'].append('stackexchange')
            config['sources']['stackexchange'] = {
                'sites': self.config.get('stackexchange', {}).get('sites', []),
                'harvest': self.config.get('stackexchange', {}).get('harvest', {})
            }
        
        return config
    
    def _is_duplicate_search(self, current: Dict[str, Any], previous: Dict[str, Any]) -> bool:
        """Check if current search configuration duplicates a previous search"""
        
        # Check Reddit subreddit overlap (most important for community-specific detection)
        if 'reddit' in current['platforms'] and 'reddit' in previous.get('sources', {}):
            current_subreddits = set(current['sources']['reddit']['subreddits'])
            previous_subreddits = set(previous['sources']['reddit'].get('subreddits', []))
            
            # If there's significant overlap in subreddits, consider it a duplicate
            if current_subreddits and previous_subreddits:
                overlap = current_subreddits.intersection(previous_subreddits)
                overlap_ratio = len(overlap) / max(len(current_subreddits), len(previous_subreddits))
                if overlap_ratio >= 0.7:  # 70% overlap threshold
                    return True
        
        # Legacy support: check old format subreddits
        elif 'subreddits' in previous and 'reddit' in current['platforms']:
            current_subreddits = set(current['sources']['reddit']['subreddits'])
            previous_subreddits = set(previous.get('subreddits', []))
            
            if current_subreddits and previous_subreddits:
                overlap = current_subreddits.intersection(previous_subreddits)
                overlap_ratio = len(overlap) / max(len(current_subreddits), len(previous_subreddits))
                if overlap_ratio >= 0.7:  # 70% overlap threshold
                    return True
        
        # Check if same web sites are being searched
        if 'web' in current['platforms']:
            current_sites = [site.get('name', '') for site in current['sources']['web']['sites']]
            # Web searches are typically unique, but we can check for exact matches
            if current_sites and any(site in str(previous) for site in current_sites):
                return True
        
        # Check if same keywords are being used (with some tolerance for minor variations)
        if 'keywords' in previous:
            current_keywords = set(current['keywords'])
            previous_keywords = set(previous.get('keywords', []))
            
            if current_keywords and previous_keywords:
                overlap = current_keywords.intersection(previous_keywords)
                overlap_ratio = len(overlap) / max(len(current_keywords), len(previous_keywords))
                if overlap_ratio >= 0.8:  # 80% keyword overlap
                    return True
        
        return False
    
    def _prompt_user_for_guidance(self, duplicates: List[Dict[str, Any]]) -> bool:
        """Prompt user for guidance when duplicates are found"""
        print("\n" + "="*80)
        print("⚠️  DUPLICATE SEARCH DETECTED ⚠️")
        print("="*80)
        print(f"Found {len(duplicates)} previous searches that overlap with current configuration:")
        
        for i, duplicate in enumerate(duplicates[:3], 1):  # Show first 3 duplicates
            print(f"\n{i}. Previous search from {duplicate.get('timestamp', 'Unknown')}:")
            if 'subreddits' in duplicate:
                print(f"   Subreddits: {', '.join(duplicate['subreddits'][:5])}{'...' if len(duplicate['subreddits']) > 5 else ''}")
            if 'keywords' in duplicate:
                print(f"   Keywords: {', '.join(duplicate['keywords'][:5])}{'...' if len(duplicate['keywords']) > 5 else ''}")
            print(f"   Results: {duplicate.get('results_count', 'Unknown')} items")
        
        print("\nOptions:")
        print("1. Continue anyway (may duplicate data)")
        print("2. Modify configuration to avoid duplicates")
        print("3. Cancel and return to configuration")
        
        while True:
            choice = input("\nEnter your choice (1-3): ").strip()
            if choice == '1':
                print("Proceeding with duplicate search...")
                return True
            elif choice == '2':
                print("Please modify your configuration and run again.")
                return False
            elif choice == '3':
                print("Cancelling search.")
                return False
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
    
    def _initialize_harvesters(self):
        """Initialize platform harvesters based on configuration"""
        sources = self.config.get("sources", {})
        
        if sources.get("reddit", False):
            try:
                self.harvesters["reddit"] = RedditHarvester(self.config)
                logger.info("Initialized Reddit harvester")
            except Exception as e:
                logger.error(f"Failed to initialize Reddit harvester: {e}")
        
        if sources.get("github", False):
            try:
                self.harvesters["github"] = GitHubHarvester(self.config)
                logger.info("Initialized GitHub harvester")
            except Exception as e:
                logger.error(f"Failed to initialize GitHub harvester: {e}")
        
        if sources.get("stackexchange", False):
            try:
                self.harvesters["stackexchange"] = StackExchangeHarvester(self.config)
                logger.info("Initialized StackExchange harvester")
            except Exception as e:
                logger.error(f"Failed to initialize StackExchange harvester: {e}")
        
        if sources.get("medium", False):
            try:
                self.harvesters["medium"] = MediumHarvester(self.config)
                logger.info("Initialized Medium harvester")
            except Exception as e:
                logger.error(f"Failed to initialize Medium harvester: {e}")
        
        if sources.get("youtube", False):
            try:
                self.harvesters["youtube"] = YouTubeHarvester(self.config)
                logger.info("Initialized YouTube harvester")
            except Exception as e:
                logger.error(f"Failed to initialize YouTube harvester: {e}")
        
        if sources.get("podcasts", False):
            try:
                self.harvesters["podcasts"] = PodcastHarvester(self.config)
                logger.info("Initialized Podcast harvester")
            except Exception as e:
                logger.error(f"Failed to initialize Podcast harvester: {e}")
        
        if sources.get("web", False):
            try:
                self.harvesters["web"] = WebHarvester(self.config)
                logger.info("Initialized Web harvester")
            except Exception as e:
                logger.error(f"Failed to initialize Web harvester: {e}")
    
    def harvest_all(self) -> Dict[str, List[Dict[str, Any]]]:
        """Harvest from all enabled platforms"""
        results = {}
        
        for platform, harvester in self.harvesters.items():
            try:
                logger.info(f"Starting harvest from {platform}")
                platform_results = harvester.harvest()
                results[platform] = platform_results
                logger.info(f"Completed {platform} harvest: {len(platform_results)} items")
                
            except Exception as e:
                logger.error(f"Harvest failed for {platform}: {e}")
                results[platform] = []
        
        return results
    
    def save_raw_data(self, results: Dict[str, List[Dict[str, Any]]], output_dir: str = "data/raw"):
        """Save raw harvested data to CSV files"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        for platform, platform_results in results.items():
            if not platform_results:
                continue
            
            output_file = f"{output_dir}/{platform}_data.csv"
            try:
                harvester = self.harvesters[platform]
                harvester._save_results(platform_results, output_file)
                logger.info(f"Saved {len(platform_results)} {platform} results to {output_file}")
                
            except Exception as e:
                logger.error(f"Failed to save {platform} results: {e}")
    
    def run_workflow(self, output_dir: str = "data/raw"):
        """Run the complete harvest workflow"""
        logger.info("Starting Wisdom Index harvest workflow")
        
        # Step 0: Check for duplicate searches
        logger.info("Step 0: Checking for duplicate searches")
        has_duplicates, duplicates = self._check_for_duplicate_searches()
        
        if has_duplicates:
            logger.warning(f"Found {len(duplicates)} potential duplicate searches")
            if not self._prompt_user_for_guidance(duplicates):
                logger.info("Search cancelled by user")
                return {}
        else:
            logger.info("No duplicate searches detected - proceeding")
        
        # Step 1: Harvest raw data
        logger.info("Step 1: Harvesting raw data from platforms")
        results = self.harvest_all()
        
        # Step 2: Save raw data
        logger.info("Step 2: Saving raw data")
        self.save_raw_data(results, output_dir)
        
        # Step 3: Save search history
        logger.info("Step 3: Saving search history")
        self._save_search_history(results)
        
        # Step 4: Provide next steps
        logger.info("Step 4: Harvest workflow completed")
        logger.info("Next steps:")
        logger.info("1. Run quality filtering: python3 filter_quality.py")
        logger.info("2. Run OpenAI transformation: python3 transform_wisdom_index_openai.py")
        
        return results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Wisdom Index Harvester")
    parser.add_argument(
        "--config", 
        default="wi_config_unified.yaml",
        help="Configuration file path"
    )
    parser.add_argument(
        "--output-dir",
        default="data/raw",
        help="Output directory for raw data"
    )
    
    args = parser.parse_args()
    
    try:
        # Check if config file exists
        if not os.path.exists(args.config):
            logger.error(f"Configuration file not found: {args.config}")
            sys.exit(1)
        
        # Initialize harvester manager
        manager = HarvesterManager(args.config)
        
        # Run workflow
        results = manager.run_workflow(args.output_dir)
        
        # Print summary
        total_items = sum(len(items) for items in results.values())
        logger.info(f"Harvest workflow completed. Total items: {total_items}")
        
        for platform, items in results.items():
            logger.info(f"  {platform}: {len(items)} items")
        
    except KeyboardInterrupt:
        logger.info("Harvest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Harvest failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
