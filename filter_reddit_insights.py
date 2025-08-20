#!/usr/bin/env python3
"""
Filter and clean Reddit insights for business tacit knowledge
"""

import csv
import re
from typing import List, Dict, Any

def is_business_relevant(content: str) -> bool:
    """Check if content is SPECIFICALLY business-relevant"""
    # Must contain specific business context, not just generic words
    specific_business_patterns = [
        r'\b(client|customer)\s+\w+',  # Client/customer interactions
        r'\b(team|employee|staff)\s+\w+',  # Team management
        r'\b(meeting|presentation|negotiation)\s+\w+',  # Business interactions
        r'\b(contract|pricing|sales|marketing)\s+\w+',  # Business processes
        r'\b(management|leadership|decision)\s+\w+',  # Leadership
        r'\b(process|workflow|efficiency)\s+\w+',  # Operations
        r'\b(product|service)\s+\w+',  # Product/service
        r'\b(revenue|profit|cost|budget)\s+\w+',  # Financial
        r'\b(hire|fire|interview)\s+\w+',  # HR
        r'\b(partnership|investment|funding)\s+\w+'  # Business relationships
    ]
    
    content_lower = content.lower()
    
    # Must match at least one specific business pattern
    has_business_pattern = any(re.search(pattern, content_lower) for pattern in specific_business_patterns)
    
    # Must NOT be generic/personal content
    generic_phrases = [
        'how do you feel', 'what do you think', 'what is your opinion',
        'what would you do', 'any advice', 'thoughts?', 'opinions?',
        'my family', 'my uncle', 'my dad', 'my mom', 'my friend',
        'i think', 'i feel', 'i believe', 'in my opinion'
    ]
    
    is_not_generic = not any(phrase in content_lower for phrase in generic_phrases)
    
    return has_business_pattern and is_not_generic

def is_tacit_knowledge(content: str) -> bool:
    """Check if content contains REAL tacit knowledge patterns"""
    # Must contain specific actionable patterns
    tacit_patterns = [
        # Specific actionable advice
        r'\b(always|never)\s+\w+.*\b(because|since|so that|in order to)\b',
        r'\b(pro tip|tip|trick|hack|workaround|shortcut):\s*\w+',
        r'\b(avoid|prevent|ensure|make sure|remember to)\s+\w+.*\b(because|since)\b',
        
        # Specific learned patterns
        r'\b(learned|discovered|found)\s+that\s+\w+.*\b(works|fails|succeeds)\b',
        r'\b(figured out|realized)\s+that\s+\w+.*\b(approach|method|technique)\b',
        
        # Specific business patterns
        r'\b(when|if)\s+\w+.*\b(then|always|never)\b',
        r'\b(the key is|the secret is|the trick is)\s+\w+',
        r'\b(one thing|something)\s+\w+.*\b(always|never)\b',
        
        # Specific actionable insights
        r'\b(do this|try this|use this)\s+.*\b(because|since)\b',
        r'\b(never do|always do)\s+.*\b(because|since)\b'
    ]
    
    content_lower = content.lower()
    
    # Must match at least one specific pattern
    has_specific_pattern = any(re.search(pattern, content_lower) for pattern in tacit_patterns)
    
    # Must also contain business context
    business_context = any(word in content_lower for word in [
        'client', 'customer', 'team', 'meeting', 'presentation', 'negotiation',
        'contract', 'pricing', 'sales', 'marketing', 'product', 'service',
        'management', 'leadership', 'decision', 'process', 'workflow'
    ])
    
    return has_specific_pattern and business_context

def is_high_quality(content: str) -> bool:
    """Check if content is high quality"""
    # Skip very short content
    if len(content) < 50:
        return False
    
    # Skip content that's just questions without answers
    if content.strip().endswith('?'):
        return False
    
    # Skip content that's too generic
    generic_phrases = [
        'what do you think', 'how do you feel', 'what is your opinion',
        'what would you do', 'what should i do', 'any advice',
        'thoughts?', 'opinions?', 'advice?'
    ]
    
    content_lower = content.lower()
    if any(phrase in content_lower for phrase in generic_phrases):
        return False
    
    return True

def filter_reddit_insights(input_file: str, output_file: str, max_items: int = 50) -> int:
    """Filter Reddit insights for high-quality business tacit knowledge"""
    
    filtered_rows = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            description = row.get('description', '')
            
            # Skip if not business-relevant
            if not is_business_relevant(description):
                continue
                
            # Skip if not tacit knowledge
            if not is_tacit_knowledge(description):
                continue
                
            # Skip if not high quality
            if not is_high_quality(description):
                continue
            
            # Skip askreddit items (usually low quality for business insights)
            source = row.get('source_(interview_#/_name)', '')
            if 'askreddit' in source.lower():
                continue
            
            filtered_rows.append(row)
            
            if len(filtered_rows) >= max_items:
                break
    
    # Write filtered data
    if filtered_rows:
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=filtered_rows[0].keys())
            writer.writeheader()
            writer.writerows(filtered_rows)
    
    return len(filtered_rows)

def main():
    input_file = "data/github_broad.csv"
    output_file = "data/github_cleaned_insights.csv"
    
    print("🔍 Filtering GitHub insights for business tacit knowledge...")
    
    filtered_count = filter_reddit_insights(input_file, output_file, max_items=50)
    
    print(f"✅ Filtered {filtered_count} high-quality business insights")
    print(f"📁 Saved to {output_file}")
    
    if filtered_count > 0:
        print("\n📋 Sample of filtered insights:")
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= 3:  # Show first 3
                    break
                desc = row['description'][:100] + "..." if len(row['description']) > 100 else row['description']
                source = row['source_(interview_#/_name)']
                print(f"  {i+1}. {desc}")
                print(f"     Source: {source}")
                print()

if __name__ == "__main__":
    main()
