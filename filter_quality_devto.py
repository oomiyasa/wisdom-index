#!/usr/bin/env python3
"""
Pre-filter Dev.to content for quality before OpenAI processing
More lenient than the main filter to capture project management insights
"""

import csv
import re
from typing import List, Dict

def is_high_quality_devto_content(text: str) -> bool:
    """Check if Dev.to content is likely to contain project management insights"""
    if not text or len(text) < 150:
        return False
    
    text_lower = text.lower()
    
    # Reject obvious/personal content
    obvious_phrases = [
        "work hard", "be honest", "set boundaries", "be professional", 
        "be respectful", "be prepared", "work life balance", "stress management",
        "be patient", "be persistent", "be confident", "be positive",
        "personal", "family", "relationship", "marriage", "dating",
        "health", "exercise", "diet", "sleep", "hobby", "vacation"
    ]
    
    if any(phrase in text_lower for phrase in obvious_phrases):
        return False
    
    # Look for project management and leadership indicators
    pm_indicators = [
        # Project management terms
        "project management", "team management", "leadership", "strategy",
        "process", "workflow", "methodology", "framework", "approach",
        "planning", "coordination", "collaboration", "communication",
        "stakeholder", "timeline", "deadline", "milestone", "deliverable",
        "resource", "budget", "scope", "risk", "quality", "efficiency",
        
        # Action-oriented terms
        "how to", "best practice", "technique", "method", "strategy",
        "solution", "approach", "system", "tool", "platform", "software",
        "automation", "optimization", "improvement", "enhancement",
        
        # Experience-based terms
        "i use", "i found", "i learned", "i discovered", "i figured out",
        "experience", "lesson", "insight", "observation", "finding",
        "what works", "what i do", "my approach", "my method", "my technique",
        
        # Problem-solving terms
        "challenge", "problem", "issue", "obstacle", "difficulty",
        "solve", "resolve", "address", "overcome", "mitigate",
        "avoid", "prevent", "reduce", "minimize", "eliminate",
        
        # Success indicators
        "success", "effective", "efficient", "productive", "successful",
        "improve", "increase", "boost", "enhance", "optimize",
        "better", "faster", "smoother", "easier", "simpler"
    ]
    
    # Count PM indicators
    indicator_count = sum(1 for indicator in pm_indicators if indicator in text_lower)
    
    # Must have at least 3 PM indicators for Dev.to content
    return indicator_count >= 3

def filter_devto_csv(input_file: str, output_file: str, max_rows: int = 200):
    """Filter Dev.to CSV for high-quality project management content"""
    filtered_rows = []
    
    with open(input_file, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        
        for row in reader:
            description = row.get('description', '')
            
            if is_high_quality_devto_content(description):
                filtered_rows.append(row)
                
                if len(filtered_rows) >= max_rows:
                    break
    
    # Write filtered results
    with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        if filtered_rows:
            writer = csv.DictWriter(outfile, fieldnames=filtered_rows[0].keys())
            writer.writeheader()
            writer.writerows(filtered_rows)
    
    print(f"✅ Filtered {len(filtered_rows)} high-quality Dev.to rows from {input_file}")
    print(f"📁 Saved to {output_file}")
    
    return len(filtered_rows)

if __name__ == "__main__":
    import argparse
    from pathlib import Path
    
    parser = argparse.ArgumentParser(description="Filter Dev.to content for quality")
    parser.add_argument("--input", default="devto_final.csv", help="Input CSV file")
    parser.add_argument("--output", default="devto_quality_filtered.csv", help="Output CSV file")
    parser.add_argument("--max", type=int, default=200, help="Maximum rows to keep")
    
    args = parser.parse_args()
    
    # Ensure data directory exists
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Update paths to use data directory
    if not args.input.startswith("data/"):
        args.input = str(data_dir / args.input)
    if not args.output.startswith("data/"):
        args.output = str(data_dir / args.output)
    
    filter_devto_csv(args.input, args.output, args.max)
