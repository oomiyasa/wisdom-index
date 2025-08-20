#!/usr/bin/env python3
"""
Harvest tacit knowledge from Usenet archives via Google Groups
"""

import requests
import re
import csv
import time
from datetime import datetime
from typing import List, Dict, Any
from urllib.parse import quote_plus

def harvest_usenet_groups(config) -> List[Dict[str, Any]]:
    """Harvest from Usenet groups via Google Groups"""
    usenet_cfg = config.get("usenet", {})
    harvest_cfg = usenet_cfg.get("harvest", {})
    
    groups = harvest_cfg.get("groups", [])
    search_keywords = harvest_cfg.get("search_keywords", [])
    
    if not groups:
        print("⚠️  No Usenet groups configured")
        return []
    
    print(f"🔍 Harvesting from Usenet groups...")
    print(f"   Groups: {groups}")
    
    rows = []
    
    for group in groups:
        try:
            group_rows = _harvest_usenet_group(group, search_keywords, harvest_cfg)
            rows.extend(group_rows)
            print(f"   📝 {group}: {len(group_rows)} posts")
            
            # Rate limiting
            time.sleep(harvest_cfg.get("throttle_sec", 2.0))
            
        except Exception as e:
            print(f"   ❌ Error harvesting {group}: {e}")
    
    return rows

def _harvest_usenet_group(group: str, search_keywords: List[str], harvest_cfg: Dict) -> List[Dict[str, Any]]:
    """Harvest posts from a specific Usenet group"""
    rows = []
    
    max_posts = harvest_cfg.get("max_posts_per_group", 30)
    max_retries = harvest_cfg.get("max_retries", 3)
    retry_delay = harvest_cfg.get("retry_delay", 5.0)
    
    # Google Groups search URL
    base_url = "https://groups.google.com/g"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    
    for keyword in search_keywords:
        if len(rows) >= max_posts:
            break
            
        # Try with retries
        for attempt in range(max_retries):
            try:
                print(f"     🔍 Searching '{group}' for '{keyword}' (attempt {attempt + 1}/{max_retries})...")
                
                # Construct search URL
                search_query = f"{keyword} group:{group}"
                encoded_query = quote_plus(search_query)
                search_url = f"{base_url}/{group}/search?q={encoded_query}"
                
                response = requests.get(search_url, headers=headers, timeout=15)
                
                # Check for rate limiting
                if response.status_code == 429:
                    print(f"       ⚠️  Rate limited (429). Waiting {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                
                response.raise_for_status()
                
                # Extract posts from HTML
                posts = _extract_posts_from_html(response.text, group, keyword)
                
                for post in posts:
                    if len(rows) >= max_posts:
                        break
                    
                    if _contains_tacit_knowledge(post.get("content", ""), search_keywords):
                        row = {
                            "description": post.get("title", "")[:200],
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
                            "date": post.get("date", datetime.now().strftime("%Y-%m-%d")),
                            "source_(interview_#/_name)": f"usenet/{group}",
                            "link": post.get("url", ""),
                            "notes": f"Group: {group}, Keyword: {keyword}, Content: {post.get('content', '')[:200]}"
                        }
                        rows.append(row)
                        print(f"       ✅ Found post: {post.get('title', '')[:50]}...")
                
                # Success, break out of retry loop
                break
                
            except requests.exceptions.RequestException as e:
                print(f"       ❌ Request error with {group} (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    print(f"         ⏳ Waiting {retry_delay} seconds before retry...")
                    time.sleep(retry_delay)
                continue
            except Exception as e:
                print(f"       ❌ Error harvesting {group} (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    print(f"         ⏳ Waiting {retry_delay} seconds before retry...")
                    time.sleep(retry_delay)
                continue
    
    return rows

def _extract_posts_from_html(html_content: str, group: str, keyword: str) -> List[Dict[str, Any]]:
    """Extract post information from Google Groups HTML"""
    posts = []
    
    # Look for post patterns in Google Groups HTML
    # This is a simplified approach - Google Groups HTML structure can be complex
    
    # Pattern for post titles and content
    post_patterns = [
        r'<h3[^>]*>([^<]+)</h3>.*?<div[^>]*class="[^"]*content[^"]*"[^>]*>([^<]+)</div>',
        r'<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>.*?<div[^>]*>([^<]+)</div>',
        r'<div[^>]*class="[^"]*subject[^"]*"[^>]*>([^<]+)</div>.*?<div[^>]*class="[^"]*body[^"]*"[^>]*>([^<]+)</div>'
    ]
    
    for pattern in post_patterns:
        matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            if len(match) >= 2:
                title = match[0].strip()
                content = match[1].strip()
                
                # Basic filtering
                if len(title) > 10 and len(content) > 50:
                    posts.append({
                        "title": title,
                        "content": content,
                        "url": f"https://groups.google.com/g/{group}",
                        "date": datetime.now().strftime("%Y-%m-%d")
                    })
    
    return posts

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
        r'\b(pattern|approach|method|technique|strategy)\b'
    ]
    
    has_tacit_pattern = any(re.search(pattern, content_lower) for pattern in tacit_patterns)
    
    return has_keyword and has_tacit_pattern

def main():
    """Test the Usenet harvester"""
    config = {
        "usenet": {
            "harvest": {
                "groups": [
                    "comp.management",
                    "biz.general", 
                    "misc.business"
                ],
                "search_keywords": [
                    "lesson learned",
                    "best practice",
                    "pro tip",
                    "workaround",
                    "gotcha",
                    "trick",
                    "pattern",
                    "approach",
                    "method"
                ],
                "max_posts_per_group": 20,
                "max_retries": 3,
                "retry_delay": 5.0,
                "throttle_sec": 2.0
            }
        }
    }
    
    print("🔍 Testing Usenet harvester...")
    rows = harvest_usenet_groups(config)
    
    print(f"✅ Found {len(rows)} posts")
    
    if rows:
        output_file = "data/usenet_test.csv"
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        print(f"📁 Saved to {output_file}")

if __name__ == "__main__":
    main()
