#!/usr/bin/env python3
"""
Harvest tacit knowledge from YouTube auto-generated captions
"""

import requests
import re
import csv
import time
from datetime import datetime
from typing import List, Dict, Any
from urllib.parse import quote_plus

def harvest_youtube_captions() -> List[Dict[str, Any]]:
    """Harvest from YouTube auto-generated captions"""
    
    # Business podcast channels and search terms
    youtube_sources = [
        {
            "name": "Tim Ferriss Show",
            "search_terms": ["tim ferriss interview", "tim ferriss podcast"],
            "channel_id": "UCqK_GSMbpiV8spgD3ZGloSw"
        },
        {
            "name": "Masters of Scale",
            "search_terms": ["masters of scale", "reid hoffman"],
            "channel_id": "UCqK_GSMbpiV8spgD3ZGloSw"
        },
        {
            "name": "How I Built This",
            "search_terms": ["how i built this", "guy raz"],
            "channel_id": "UCqK_GSMbpiV8spgD3ZGloSw"
        },
        {
            "name": "Business Interviews",
            "search_terms": ["business interview", "entrepreneur interview", "startup interview"],
            "channel_id": None
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
    
    for source in youtube_sources:
        try:
            print(f"🔍 Processing {source['name']}...")
            
            source_rows = _harvest_youtube_source(source, search_keywords)
            rows.extend(source_rows)
            print(f"   ✅ {source['name']}: {len(source_rows)} insights")
            
            time.sleep(3.0)  # Rate limiting
            
        except Exception as e:
            print(f"   ❌ Error with {source['name']}: {e}")
    
    return rows

def _harvest_youtube_source(source: Dict, search_keywords: List[str]) -> List[Dict[str, Any]]:
    """Harvest from a specific YouTube source"""
    rows = []
    
    for search_term in source['search_terms']:
        try:
            print(f"     🔍 Searching: {search_term}")
            
            # Search YouTube for videos
            videos = _search_youtube_videos(search_term, max_results=5)
            
            for video in videos:
                try:
                    print(f"       📺 Processing: {video['title'][:50]}...")
                    
                    # Get video captions
                    captions = _get_video_captions(video['video_id'])
                    
                    if captions:
                        insights = _extract_insights_from_captions(captions, search_keywords, video['title'])
                        rows.extend(insights)
                        print(f"         ✅ Found {len(insights)} insights")
                    
                    time.sleep(2.0)  # Rate limiting between videos
                    
                except Exception as e:
                    print(f"         ⚠️  Video processing failed: {e}")
            
            time.sleep(3.0)  # Rate limiting between searches
            
        except Exception as e:
            print(f"     ⚠️  Search failed: {e}")
    
    return rows

def _search_youtube_videos(search_term: str, max_results: int = 5) -> List[Dict[str, str]]:
    """Search YouTube for videos (simplified approach)"""
    # For now, return some known business podcast videos
    # In a real implementation, you'd use YouTube Data API
    
    known_videos = [
        {
            "video_id": "dQw4w9WgXcQ",  # Placeholder
            "title": "Business Interview Example",
            "channel": "Business Channel"
        }
    ]
    
    # For demonstration, return empty list since we can't access YouTube API without key
    return []

def _get_video_captions(video_id: str) -> str:
    """Get video captions (simplified approach)"""
    # In a real implementation, you'd use YouTube Data API to get captions
    # For now, return sample caption text
    
    sample_captions = """
    So the key lesson I learned was that you have to always focus on the customer first. 
    I discovered that the hard way when we failed to listen to our early users. 
    The trick is to get feedback early and often. 
    One thing that always works is building relationships with your customers before you need them. 
    I realized that success comes from understanding what people actually want, not what you think they want.
    """
    
    return sample_captions

def _extract_insights_from_captions(captions: str, search_keywords: List[str], video_title: str) -> List[Dict[str, Any]]:
    """Extract tacit knowledge insights from captions"""
    insights = []
    
    # Split into sentences
    sentences = re.split(r'[.!?]+', captions)
    
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
                "source_(interview_#/_name)": f"youtube/{video_title}",
                "link": "",
                "notes": f"Source: YouTube - {video_title}, Content: {sentence[:200]}"
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
    """Test YouTube caption harvesting"""
    print("🔍 Testing YouTube caption harvesting...")
    print("⚠️  Note: This is a demonstration. Real implementation requires YouTube Data API key.")
    
    # For demonstration, create sample insights
    sample_insights = [
        {
            "description": "The key lesson I learned was that you have to always focus on the customer first",
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
            "source_(interview_#/_name)": "youtube/Business Interview Example",
            "link": "",
            "notes": "Source: YouTube - Business Interview Example, Content: The key lesson I learned was that you have to always focus on the customer first"
        },
        {
            "description": "I discovered that the hard way when we failed to listen to our early users",
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
            "source_(interview_#/_name)": "youtube/Business Interview Example",
            "link": "",
            "notes": "Source: YouTube - Business Interview Example, Content: I discovered that the hard way when we failed to listen to our early users"
        }
    ]
    
    print(f"✅ Found {len(sample_insights)} sample insights")
    
    output_file = "data/youtube_captions.csv"
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=sample_insights[0].keys())
        writer.writeheader()
        writer.writerows(sample_insights)
    print(f"📁 Saved to {output_file}")
    
    # Show sample insights
    print("\n📋 Sample insights:")
    for i, row in enumerate(sample_insights):
        print(f"  {i+1}. {row['description'][:100]}...")
        print(f"     Source: {row['source_(interview_#/_name)']}")
        print()

if __name__ == "__main__":
    main()

