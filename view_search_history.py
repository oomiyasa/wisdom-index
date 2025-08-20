#!/usr/bin/env python3
"""
View and manage search history for the Wisdom Index harvester
"""

import json
import os
from datetime import datetime
from typing import Dict, List

def load_search_log() -> Dict:
    """Load search history from JSON file"""
    log_file = "search_history.json"
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading search log: {e}")
            return {"searches": [], "last_run": None}
    return {"searches": [], "last_run": None}

def display_search_history():
    """Display all previous searches"""
    log_data = load_search_log()
    
    if not log_data["searches"]:
        print("📝 No search history found.")
        return
    
    print(f"📊 Search History ({len(log_data['searches'])} searches)")
    print("=" * 60)
    
    for i, search in enumerate(reversed(log_data["searches"]), 1):
        timestamp = datetime.fromisoformat(search["timestamp"]).strftime("%Y-%m-%d %H:%M")
        print(f"\n🔍 Search #{i} - {timestamp}")
        # Show enabled platforms
        platforms = search.get('platforms', {})
        enabled_platforms = [k for k, v in platforms.items() if v]
        if enabled_platforms:
            print(f"   🌐 Platforms: {', '.join(enabled_platforms)}")
        
        print(f"   📍 Subreddits: {', '.join(search.get('subreddits', []))}")
        print(f"   🔑 Keywords: {', '.join(search.get('keywords', [])[:5])}{'...' if len(search.get('keywords', [])) > 5 else ''}")
        print(f"   ⏰ Time Filter: {search.get('time_filter', 'unknown')}")
        print(f"   📊 Sort: {search.get('sort', 'unknown')}")
        print(f"   📈 Results: {search.get('results_count', 0)} entries")
        print("-" * 40)

def find_similar_searches(target_config: Dict) -> List[Dict]:
    """Find searches similar to the target configuration"""
    log_data = load_search_log()
    similar = []
    
    for search in log_data["searches"]:
        # Check if subreddits and keywords match
        if (set(search["subreddits"]) == set(target_config["subreddits"]) and
            set(search["keywords"]) == set(target_config["keywords"])):
            similar.append(search)
    
    return similar

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="View and manage search history")
    parser.add_argument("--list", action="store_true", help="List all searches")
    parser.add_argument("--check", help="Check if a specific config would be duplicate")
    parser.add_argument("--clear", action="store_true", help="Clear search history")
    
    args = parser.parse_args()
    
    if args.list:
        display_search_history()
    
    elif args.check:
        # This would check against a specific config file
        print("Checking for duplicates...")
        # Implementation would go here
    
    elif args.clear:
        if os.path.exists("search_history.json"):
            os.remove("search_history.json")
            print("🗑️  Search history cleared.")
        else:
            print("📝 No search history to clear.")
    
    else:
        display_search_history()

if __name__ == "__main__":
    main()
