#!/usr/bin/env python3
"""
Wisdom Index Complete Workflow

This script demonstrates the complete workflow:
1. Harvest raw data from platforms
2. Filter for quality
3. Transform with OpenAI

Usage:
  python3 workflow.py --config wi_config_unified.yaml
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any

import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkflowManager:
    """Manages the complete Wisdom Index workflow"""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self._load_config()
    
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
    
    def step_1_harvest(self) -> bool:
        """Step 1: Harvest raw data from platforms"""
        logger.info("=" * 60)
        logger.info("STEP 1: HARVESTING RAW DATA")
        logger.info("=" * 60)
        
        try:
            # Import here to avoid circular imports
            from harvester_main import HarvesterManager
            
            manager = HarvesterManager(self.config_path)
            results = manager.run_workflow()
            
            total_items = sum(len(items) for items in results.values())
            logger.info(f"✅ Harvest completed successfully. Total items: {total_items}")
            
            for platform, items in results.items():
                if items:
                    logger.info(f"  📊 {platform}: {len(items)} items")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Harvest failed: {e}")
            return False
    
    def step_2_filter(self) -> bool:
        """Step 2: Filter data for quality"""
        logger.info("=" * 60)
        logger.info("STEP 2: QUALITY FILTERING")
        logger.info("=" * 60)
        
        try:
            # Check if filter_quality.py exists
            if not os.path.exists("filter_quality.py"):
                logger.warning("filter_quality.py not found. Skipping filtering step.")
                return True
            
            # Run quality filtering
            import subprocess
            result = subprocess.run([sys.executable, "filter_quality.py"], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Quality filtering completed successfully")
                return True
            else:
                logger.error(f"❌ Quality filtering failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Quality filtering failed: {e}")
            return False
    
    def step_3_transform(self) -> bool:
        """Step 3: Transform with OpenAI"""
        logger.info("=" * 60)
        logger.info("STEP 3: OPENAI TRANSFORMATION")
        logger.info("=" * 60)
        
        try:
            # Check if OpenAI API key is set
            if not os.getenv("OPENAI_API_KEY"):
                logger.error("❌ OPENAI_API_KEY not set in environment variables")
                return False
            
            # Check if transform script exists
            if not os.path.exists("transform_wisdom_index_openai.py"):
                logger.warning("transform_wisdom_index_openai.py not found. Skipping transformation step.")
                return True
            
            # Run transformation
            import subprocess
            result = subprocess.run([sys.executable, "transform_wisdom_index_openai.py"], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ OpenAI transformation completed successfully")
                return True
            else:
                logger.error(f"❌ OpenAI transformation failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ OpenAI transformation failed: {e}")
            return False
    
    def run_workflow(self) -> bool:
        """Run the complete workflow"""
        logger.info("🚀 Starting Wisdom Index Complete Workflow")
        logger.info(f"📁 Configuration: {self.config_path}")
        
        # Step 1: Harvest
        if not self.step_1_harvest():
            logger.error("❌ Workflow failed at Step 1")
            return False
        
        # Step 2: Filter
        if not self.step_2_filter():
            logger.error("❌ Workflow failed at Step 2")
            return False
        
        # Step 3: Transform
        if not self.step_3_transform():
            logger.error("❌ Workflow failed at Step 3")
            return False
        
        logger.info("=" * 60)
        logger.info("🎉 WORKFLOW COMPLETED SUCCESSFULLY!")
        logger.info("=" * 60)
        logger.info("📊 Next steps:")
        logger.info("  1. Review the generated wisdom insights")
        logger.info("  2. Use wisdom_search.py to search the database")
        logger.info("  3. Start web interface with: python3 web_search.py")
        
        return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Wisdom Index Complete Workflow")
    parser.add_argument(
        "--config", 
        default="wi_config_unified.yaml",
        help="Configuration file path"
    )
    parser.add_argument(
        "--step",
        choices=["harvest", "filter", "transform", "all"],
        default="all",
        help="Which step to run (default: all)"
    )
    
    args = parser.parse_args()
    
    try:
        # Check if config file exists
        if not os.path.exists(args.config):
            logger.error(f"Configuration file not found: {args.config}")
            sys.exit(1)
        
        # Initialize workflow manager
        manager = WorkflowManager(args.config)
        
        # Run workflow based on step argument
        if args.step == "harvest":
            success = manager.step_1_harvest()
        elif args.step == "filter":
            success = manager.step_2_filter()
        elif args.step == "transform":
            success = manager.step_3_transform()
        else:  # all
            success = manager.run_workflow()
        
        if success:
            logger.info("✅ Workflow completed successfully")
            sys.exit(0)
        else:
            logger.error("❌ Workflow failed")
            sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("⏹️  Workflow interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Workflow failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
