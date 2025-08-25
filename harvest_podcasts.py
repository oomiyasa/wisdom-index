#!/usr/bin/env python3
"""
Harvest tacit knowledge from podcast transcripts at scale
"""

import requests
import re
import csv
import time
import json
from datetime import datetime
from typing import List, Dict, Any
from urllib.parse import urljoin, urlparse
import feedparser

def harvest_podcast_transcripts(config) -> List[Dict[str, Any]]:
    """Harvest from podcast transcripts"""
    podcast_cfg = config.get("podcasts", {})
    harvest_cfg = podcast_cfg.get("harvest", {})
    
    podcasts = harvest_cfg.get("podcasts", [])
    search_keywords = harvest_cfg.get("search_keywords", [])
    
    if not podcasts:
        print("⚠️  No podcasts configured")
        return []
    
    print(f"🔍 Harvesting from podcast transcripts...")
    print(f"   Podcasts: {len(podcasts)}")
    
    rows = []
    
    for podcast in podcasts:
        try:
            podcast_rows = _harvest_podcast_transcript(podcast, search_keywords, harvest_cfg)
            rows.extend(podcast_rows)
            print(f"   🎧 {podcast['name']}: {len(podcast_rows)} insights")
            
            # Rate limiting
            time.sleep(harvest_cfg.get("throttle_sec", 3.0))
            
        except Exception as e:
            print(f"   ❌ Error harvesting {podcast.get('name', 'Unknown')}: {e}")
    
    return rows

def _harvest_podcast_transcript(podcast: Dict, search_keywords: List[str], harvest_cfg: Dict) -> List[Dict[str, Any]]:
    """Harvest transcripts from a specific podcast"""
    rows = []
    
    podcast_name = podcast.get("name", "Unknown")
    rss_url = podcast.get("rss_url", "")
    transcript_urls = podcast.get("transcript_urls", [])
    max_episodes = harvest_cfg.get("max_episodes_per_podcast", 20)
    
    print(f"     🔍 Processing {podcast_name}...")
    
    # Method 1: Try RSS feed to get episode URLs
    if rss_url:
        try:
            print(f"       📡 Parsing RSS feed...")
            feed = feedparser.parse(rss_url)
            
            episode_count = 0
            for entry in feed.entries:
                if episode_count >= max_episodes:
                    break
                
                episode_title = entry.get("title", "")
                episode_link = entry.get("link", "")
                episode_date = entry.get("published", "")
                
                # Try to get transcript from episode page
                transcript = _extract_transcript_from_episode(episode_link, podcast_name)
                
                if transcript:
                    insights = _extract_insights_from_transcript(transcript, search_keywords, episode_title)
                    rows.extend(insights)
                    episode_count += 1
                    print(f"         ✅ Episode: {episode_title[:50]}... ({len(insights)} insights)")
                
                time.sleep(harvest_cfg.get("episode_throttle_sec", 1.0))
                
        except Exception as e:
            print(f"       ❌ RSS parsing error: {e}")
    
    # Method 2: Direct transcript URLs
    for transcript_url in transcript_urls:
        try:
            print(f"       📄 Fetching transcript: {transcript_url}")
            transcript = _fetch_transcript_from_url(transcript_url)
            
            if transcript:
                insights = _extract_insights_from_transcript(transcript, search_keywords, podcast_name)
                rows.extend(insights)
                print(f"         ✅ Transcript: {len(insights)} insights")
            
            time.sleep(harvest_cfg.get("transcript_throttle_sec", 2.0))
            
        except Exception as e:
            print(f"       ❌ Transcript fetch error: {e}")
    
    return rows

def _extract_transcript_from_episode(episode_url: str, podcast_name: str) -> str:
    """Extract transcript from episode page"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }
        
        response = requests.get(episode_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Look for transcript patterns
        transcript_patterns = [
            r'<div[^>]*class="[^"]*transcript[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*id="[^"]*transcript[^"]*"[^>]*>(.*?)</div>',
            r'<section[^>]*class="[^"]*transcript[^"]*"[^>]*>(.*?)</section>',
            r'<article[^>]*class="[^"]*transcript[^"]*"[^>]*>(.*?)</article>',
            r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
        ]
        
        for pattern in transcript_patterns:
            matches = re.findall(pattern, response.text, re.DOTALL | re.IGNORECASE)
            if matches:
                # Clean HTML tags
                transcript = re.sub(r'<[^>]+>', ' ', matches[0])
                transcript = re.sub(r'\s+', ' ', transcript).strip()
                if len(transcript) > 500:  # Minimum length
                    return transcript
        
        return ""
        
    except Exception as e:
        print(f"         ⚠️  Episode transcript extraction failed: {e}")
        return ""

def _fetch_transcript_from_url(transcript_url: str) -> str:
    """Fetch transcript from direct URL"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }
        
        response = requests.get(transcript_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Clean HTML tags
        transcript = re.sub(r'<[^>]+>', ' ', response.text)
        transcript = re.sub(r'\s+', ' ', transcript).strip()
        
        return transcript if len(transcript) > 500 else ""
        
    except Exception as e:
        print(f"         ⚠️  Transcript fetch failed: {e}")
        return ""

def _extract_insights_from_transcript(transcript: str, search_keywords: List[str], source_name: str) -> List[Dict[str, Any]]:
    """Extract tacit knowledge insights from transcript"""
    insights = []
    
    # Split transcript into sentences/paragraphs
    sentences = re.split(r'[.!?]+', transcript)
    
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 50:  # Skip short sentences
            continue
        
        # Check if sentence contains tacit knowledge
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
                "source_(interview_#/_name)": f"podcast/{source_name}",
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
    """Test the podcast transcript harvester"""
    config = {
        "podcasts": {
            "harvest": {
                "podcasts": [
                    {
                        "name": "Masters of Scale",
                        "rss_url": "https://feeds.megaphone.fm/mastersofscale",
                        "transcript_urls": []
                    },
                    {
                        "name": "The Tim Ferriss Show",
                        "rss_url": "https://rss.art19.com/tim-ferriss-show",
                        "transcript_urls": []
                    },
                    {
                        "name": "How I Built This",
                        "rss_url": "https://feeds.npr.org/510313/podcast.xml",
                        "transcript_urls": []
                    }
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
                    "method",
                    "technique",
                    "strategy",
                    "learned",
                    "discovered",
                    "found",
                    "realized",
                    "figured out",
                    "worked",
                    "failed",
                    "succeeded",
                    "mistake",
                    "success",
                    "failure"
                ],
                "max_episodes_per_podcast": 10,
                "throttle_sec": 3.0,
                "episode_throttle_sec": 1.0,
                "transcript_throttle_sec": 2.0
            }
        }
    }
    
    print("🔍 Testing podcast transcript harvester...")
    rows = harvest_podcast_transcripts(config)
    
    print(f"✅ Found {len(rows)} insights")
    
    if rows:
        output_file = "data/podcast_transcripts.csv"
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        print(f"📁 Saved to {output_file}")

if __name__ == "__main__":
    main()

