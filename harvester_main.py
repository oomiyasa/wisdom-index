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
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

import yaml
from dotenv import load_dotenv

# Import modular harvesters
from harvesters import (
    RedditHarvester, GitHubHarvester, StackExchangeHarvester,
    MediumHarvester, YouTubeHarvester, PodcastHarvester
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
        
        # Step 1: Harvest raw data
        logger.info("Step 1: Harvesting raw data from platforms")
        results = self.harvest_all()
        
        # Step 2: Save raw data
        logger.info("Step 2: Saving raw data")
        self.save_raw_data(results, output_dir)
        
        # Step 3: Provide next steps
        logger.info("Step 3: Harvest workflow completed")
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
