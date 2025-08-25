#!/usr/bin/env python3
"""
Pre-filter content for quality before OpenAI processing
"""

import csv
import re
from typing import List, Dict

def is_high_quality_content(text: str) -> bool:
    """Check if content is likely to contain tacit knowledge"""
    if not text or len(text) < 50:
        return False
    
    text_lower = text.lower()
    
    # Reject obvious/personal content
    obvious_phrases = [
        "work hard", "be honest", "set boundaries", "communicate", 
        "be professional", "be respectful", "be organized", "be prepared",
        "work life balance", "time management", "stress management",
        "be patient", "be persistent", "be confident", "be positive",
        "personal", "family", "relationship", "marriage", "dating",
        "health", "exercise", "diet", "sleep", "hobby", "vacation",
        "episode", "podcast", "show", "interview", "discussion", "conversation",
        "timestamps", "sponsor", "advertisement", "subscribe", "follow"
    ]
    
    if any(phrase in text_lower for phrase in obvious_phrases):
        return False
    
    # Look for promising indicators (expanded for podcast content)
    promising_indicators = [
        "i use", "i found", "i learned", "i discovered", "i figured out",
        "the key is", "the trick is", "the secret is", "the hack is",
        "what works", "what i do", "my approach", "my method", "my technique",
        "i always", "i never", "i make sure", "i ensure", "i create",
        "i establish", "i set up", "i organize", "i structure", "i manage",
        "because", "reason", "works when", "avoid this", "instead of",
        "rather than", "instead", "alternative", "workaround", "solution",
        "experience", "lesson", "insight", "wisdom", "advice", "tip",
        "strategy", "approach", "method", "technique", "pattern",
        "learned", "discovered", "found", "realized", "figured out",
        "worked", "failed", "succeeded", "mistake", "success", "failure",
        "always", "never", "usually", "typically", "generally",
        "years of", "decades of", "since", "therefore", "so that",
        "in order to", "pro tip", "trick", "hack", "shortcut"
    ]
    
    # Count promising indicators
    indicator_count = sum(1 for indicator in promising_indicators if indicator in text_lower)
    
    # Must have at least 1 promising indicator for podcast content
    return indicator_count >= 1

def filter_csv(input_file: str, output_file: str, max_rows: int = 200):
    """Filter CSV for high-quality content"""
    filtered_rows = []
    
    with open(input_file, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        
        for row in reader:
            description = row.get('description', '')
            
            if is_high_quality_content(description):
                filtered_rows.append(row)
                
                if len(filtered_rows) >= max_rows:
                    break
    
    # Write filtered results
    with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        if filtered_rows:
            writer = csv.DictWriter(outfile, fieldnames=filtered_rows[0].keys())
            writer.writeheader()
            writer.writerows(filtered_rows)
    
    print(f"✅ Filtered {len(filtered_rows)} high-quality rows from {input_file}")
    print(f"📁 Saved to {output_file}")
    
    return len(filtered_rows)

if __name__ == "__main__":
    import argparse
    from pathlib import Path
    
    parser = argparse.ArgumentParser(description="Filter content for quality")
    parser.add_argument("--input", default="comments_test.csv", help="Input CSV file")
    parser.add_argument("--output", default="quality_filtered.csv", help="Output CSV file")
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
    
    filter_csv(args.input, args.output, args.max)
