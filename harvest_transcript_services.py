#!/usr/bin/env python3
"""
Harvest from specific transcript services and repositories
"""

import requests
import re
import csv
import time
from datetime import datetime
from typing import List, Dict, Any

def harvest_transcript_services() -> List[Dict[str, Any]]:
    """Harvest from specific transcript services"""
    
    # Known transcript sources
    transcript_sources = [
        {
            "name": "Rev.com Transcripts",
            "url": "https://www.rev.com/blog/transcripts",
            "type": "transcript_service"
        },
        {
            "name": "Tim Ferriss Blog",
            "url": "https://tim.blog/",
            "type": "blog_search"
        },
        {
            "name": "Paul Graham Essays",
            "url": "http://www.paulgraham.com/",
            "type": "essays"
        },
        {
            "name": "Seth Godin Blog",
            "url": "https://seths.blog/",
            "type": "blog"
        }
    ]
    
    search_keywords = [
        "lesson learned", "best practice", "pro tip", "workaround", "gotcha",
        "trick", "pattern", "approach", "method", "technique", "strategy",
        "learned", "discovered", "found", "realized", "figured out",
        "worked", "failed", "succeeded", "mistake", "success", "failure",
        "always", "never", "because", "since", "therefore", "avoid",
        "prevent", "ensure", "make sure", "remember to", "experience",
        "insight", "wisdom", "advice", "the key is", "the secret is"
    ]
    
    rows = []
    
    for source in transcript_sources:
        try:
            print(f"🔍 Processing {source['name']}...")
            
            if source['type'] == 'transcript_service':
                source_rows = _harvest_transcript_service(source, search_keywords)
            elif source['type'] == 'blog_search':
                source_rows = _harvest_blog_search(source, search_keywords)
            elif source['type'] == 'essays':
                source_rows = _harvest_essays(source, search_keywords)
            elif source['type'] == 'blog':
                source_rows = _harvest_blog(source, search_keywords)
            
            rows.extend(source_rows)
            print(f"   ✅ {source['name']}: {len(source_rows)} insights")
            
            time.sleep(3.0)  # Rate limiting
            
        except Exception as e:
            print(f"   ❌ Error with {source['name']}: {e}")
    
    return rows

def _harvest_transcript_service(source: Dict, search_keywords: List[str]) -> List[Dict[str, Any]]:
    """Harvest from transcript service websites"""
    rows = []
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }
        
        response = requests.get(source['url'], headers=headers, timeout=15)
        response.raise_for_status()
        
        # Look for transcript content
        content_patterns = [
            r'<div[^>]*class="[^"]*transcript[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
            r'<article[^>]*>(.*?)</article>',
            r'<div[^>]*class="[^"]*post[^"]*"[^>]*>(.*?)</div>'
        ]
        
        for pattern in content_patterns:
            matches = re.findall(pattern, response.text, re.DOTALL | re.IGNORECASE)
            for match in matches:
                content = re.sub(r'<[^>]+>', ' ', match)
                content = re.sub(r'\s+', ' ', content).strip()
                
                if len(content) > 500:
                    insights = _extract_insights_from_text(content, search_keywords, source['name'])
                    rows.extend(insights)
        
    except Exception as e:
        print(f"     ⚠️  Transcript service harvest failed: {e}")
    
    return rows

def _harvest_blog_search(source: Dict, search_keywords: List[str]) -> List[Dict[str, Any]]:
    """Harvest from blog search results"""
    rows = []
    
    try:
        # Search for specific keywords on the blog
        search_terms = ["lesson learned", "best practice", "pro tip", "workaround", "trick", "pattern"]
        
        for term in search_terms:
            search_url = f"{source['url']}?s={term.replace(' ', '+')}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive"
            }
            
            response = requests.get(search_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Extract content from search results
            content = re.sub(r'<[^>]+>', ' ', response.text)
            content = re.sub(r'\s+', ' ', content).strip()
            
            if len(content) > 1000:
                insights = _extract_insights_from_text(content, search_keywords, f"{source['name']} - {term}")
                rows.extend(insights)
            
            time.sleep(2.0)  # Rate limiting between searches
        
    except Exception as e:
        print(f"     ⚠️  Blog search harvest failed: {e}")
    
    return rows

def _harvest_essays(source: Dict, search_keywords: List[str]) -> List[Dict[str, Any]]:
    """Harvest from essay collections"""
    rows = []
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }
        
        response = requests.get(source['url'], headers=headers, timeout=15)
        response.raise_for_status()
        
        # Extract all text content
        content = re.sub(r'<[^>]+>', ' ', response.text)
        content = re.sub(r'\s+', ' ', content).strip()
        
        if len(content) > 1000:
            insights = _extract_insights_from_text(content, search_keywords, source['name'])
            rows.extend(insights)
        
    except Exception as e:
        print(f"     ⚠️  Essays harvest failed: {e}")
    
    return rows

def _harvest_blog(source: Dict, search_keywords: List[str]) -> List[Dict[str, Any]]:
    """Harvest from blog content"""
    rows = []
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }
        
        response = requests.get(source['url'], headers=headers, timeout=15)
        response.raise_for_status()
        
        # Look for blog post content
        content_patterns = [
            r'<div[^>]*class="[^"]*entry[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*post[^"]*"[^>]*>(.*?)</div>',
            r'<article[^>]*>(.*?)</article>',
            r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>'
        ]
        
        for pattern in content_patterns:
            matches = re.findall(pattern, response.text, re.DOTALL | re.IGNORECASE)
            for match in matches:
                content = re.sub(r'<[^>]+>', ' ', match)
                content = re.sub(r'\s+', ' ', content).strip()
                
                if len(content) > 500:
                    insights = _extract_insights_from_text(content, search_keywords, source['name'])
                    rows.extend(insights)
        
    except Exception as e:
        print(f"     ⚠️  Blog harvest failed: {e}")
    
    return rows

def _extract_insights_from_text(text: str, search_keywords: List[str], source_name: str) -> List[Dict[str, Any]]:
    """Extract tacit knowledge insights from text"""
    insights = []
    
    # Split into sentences
    sentences = re.split(r'[.!?]+', text)
    
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 50:
            continue
        
        # Check for tacit knowledge
        if _contains_tacit_knowledge(sentence, search_keywords):
            insight = {
                "description": sentence[:200],
                "rationale": "",
                "use_case": "",
                "impact_area": "",
                "transferability_score": "",
                "actionability_rating": "",
                "evidence_strength": "Anecdotal",
                "type_(form)": "pattern",
                "tag_(application)": "",
                "unique?": "",
                "role": "",
                "function": "",
                "company": "",
                "industry": "",
                "country": "",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "source_(interview_#/_name)": f"transcript/{source_name}",
                "link": "",
                "notes": f"Source: {source_name}, Content: {sentence[:200]}"
            }
            insights.append(insight)
    
    return insights

def _contains_tacit_knowledge(content: str, search_keywords: List[str]) -> bool:
    """Check if content contains tacit knowledge patterns"""
    content_lower = content.lower()
    
    # Must contain at least one search keyword
    has_keyword = any(keyword.lower() in content_lower for keyword in search_keywords)
    
    # Must contain tacit knowledge patterns
    tacit_patterns = [
        r'\b(learned|discovered|found|realized|figured out|worked|failed|succeeded)\b',
        r'\b(always|never|usually|typically|generally)\b',
        r'\b(because|since|therefore|so that|in order to)\b',
        r'\b(pro tip|tip|trick|hack|workaround|shortcut)\b',
        r'\b(avoid|prevent|ensure|make sure|remember to)\b',
        r'\b(experience|lesson|insight|wisdom|advice)\b',
        r'\b(pattern|approach|method|technique|strategy)\b',
        r'\b(the key is|the secret is|the trick is)\b',
        r'\b(one thing|something)\s+\w+.*\b(always|never)\b',
        r'\b(when|if)\s+\w+.*\b(then|always|never)\b'
    ]
    
    has_tacit_pattern = any(re.search(pattern, content_lower) for pattern in tacit_patterns)
    
    return has_keyword and has_tacit_pattern

def main():
    """Test transcript service harvesting"""
    print("🔍 Testing transcript service harvesting...")
    
    rows = harvest_transcript_services()
    
    print(f"✅ Found {len(rows)} insights")
    
    if rows:
        output_file = "data/transcript_services.csv"
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        print(f"📁 Saved to {output_file}")
        
        # Show sample insights
        print("\n📋 Sample insights:")
        for i, row in enumerate(rows[:3]):
            print(f"  {i+1}. {row['description'][:100]}...")
            print(f"     Source: {row['source_(interview_#/_name)']}")
            print()

if __name__ == "__main__":
    main()
