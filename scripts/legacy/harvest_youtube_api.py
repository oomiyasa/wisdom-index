#!/usr/bin/env python3
"""
Harvest tacit knowledge from YouTube using YouTube Data API
"""

import os
import re
import csv
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import requests

class YouTubeHarvester:
    def __init__(self, api_key: str):
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.api_key = api_key
        
    def search_business_podcasts(self, search_terms: List[str], max_results: int = 50) -> List[Dict[str, Any]]:
        """Search for business podcast videos"""
        all_videos = []
        
        for search_term in search_terms:
            try:
                print(f"🔍 Searching YouTube for: {search_term}")
                
                # Search for videos
                search_response = self.youtube.search().list(
                    q=search_term,
                    part='id,snippet',
                    maxResults=min(max_results, 50),  # YouTube API limit
                    type='video',
                    videoDuration='medium',  # 4-20 minutes
                    publishedAfter='2020-01-01T00:00:00Z',  # Recent content
                    relevanceLanguage='en',
                    order='relevance'
                ).execute()
                
                videos = []
                for item in search_response.get('items', []):
                    video_info = {
                        'video_id': item['id']['videoId'],
                        'title': item['snippet']['title'],
                        'channel_title': item['snippet']['channelTitle'],
                        'published_at': item['snippet']['publishedAt'],
                        'description': item['snippet']['description'],
                        'search_term': search_term
                    }
                    videos.append(video_info)
                
                all_videos.extend(videos)
                print(f"   ✅ Found {len(videos)} videos for '{search_term}'")
                
                time.sleep(1)  # Rate limiting
                
            except HttpError as e:
                print(f"   ❌ Error searching for '{search_term}': {e}")
        
        return all_videos
    
    def get_video_captions(self, video_id: str) -> Optional[str]:
        """Get video captions/transcript"""
        try:
            # First, check if captions are available
            captions_response = self.youtube.captions().list(
                part='snippet',
                videoId=video_id
            ).execute()
            
            caption_tracks = captions_response.get('items', [])
            
            # Look for auto-generated English captions first
            auto_caption = None
            manual_caption = None
            
            for caption in caption_tracks:
                if caption['snippet']['language'] == 'en':
                    if caption['snippet']['trackKind'] == 'ASR':  # Auto-generated
                        auto_caption = caption
                    elif caption['snippet']['trackKind'] == 'standard':  # Manual
                        manual_caption = caption
            
            # Prefer manual captions over auto-generated
            target_caption = manual_caption or auto_caption
            
            if target_caption:
                # Download the caption track
                caption_response = self.youtube.captions().download(
                    id=target_caption['id'],
                    tfmt='srt'  # SubRip format
                ).execute()
                
                # Parse SRT format to extract text
                caption_text = self._parse_srt_captions(caption_response)
                return caption_text
            
            return None
            
        except HttpError as e:
            print(f"     ⚠️  Error getting captions for {video_id}: {e}")
            return None
    
    def _parse_srt_captions(self, srt_content: bytes) -> str:
        """Parse SRT caption format to extract text"""
        try:
            content = srt_content.decode('utf-8')
            
            # Remove SRT formatting and extract just the text
            lines = content.split('\n')
            text_lines = []
            
            for line in lines:
                line = line.strip()
                # Skip empty lines, numbers, and timestamps
                if (line and 
                    not line.isdigit() and 
                    not '-->' in line and
                    not line.startswith('WEBVTT')):
                    text_lines.append(line)
            
            return ' '.join(text_lines)
            
        except Exception as e:
            print(f"     ⚠️  Error parsing captions: {e}")
            return ""
    
    def extract_insights_from_captions(self, captions: str, video_info: Dict[str, Any], 
                                     search_keywords: List[str]) -> List[Dict[str, Any]]:
        """Extract tacit knowledge insights from captions"""
        insights = []
        
        if not captions or len(captions) < 100:
            return insights
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', captions)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 50:
                continue
            
            # Check for tacit knowledge
            if self._contains_tacit_knowledge(sentence, search_keywords):
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
                    "source_(interview_#/_name)": f"youtube/{video_info['channel_title']}",
                    "link": f"https://www.youtube.com/watch?v={video_info['video_id']}",
                    "notes": f"Video: {video_info['title']}, Channel: {video_info['channel_title']}, Content: {sentence[:200]}"
                }
                insights.append(insight)
        
        return insights
    
    def _contains_tacit_knowledge(self, content: str, search_keywords: List[str]) -> bool:
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

def harvest_youtube_business_podcasts(api_key: str) -> List[Dict[str, Any]]:
    """Main function to harvest business podcast insights from YouTube"""
    
    harvester = YouTubeHarvester(api_key)
    
    # Business podcast search terms
    search_terms = [
        "tim ferriss interview",
        "masters of scale reid hoffman",
        "how i built this guy raz",
        "startup interview",
        "entrepreneur interview",
        "business lessons learned",
        "startup advice",
        "business tips",
        "entrepreneur tips",
        "business strategy",
        "startup strategy",
        "business insights",
        "entrepreneur insights",
        "business wisdom",
        "startup wisdom"
    ]
    
    # Tacit knowledge keywords
    search_keywords = [
        "lesson learned", "best practice", "pro tip", "workaround", "gotcha",
        "trick", "pattern", "approach", "method", "technique", "strategy",
        "learned", "discovered", "found", "realized", "figured out",
        "worked", "failed", "succeeded", "mistake", "success", "failure",
        "always", "never", "because", "since", "therefore", "avoid",
        "prevent", "ensure", "make sure", "remember to", "experience",
        "insight", "wisdom", "advice", "the key is", "the secret is"
    ]
    
    print("🔍 Starting YouTube business podcast harvest...")
    
    # Search for videos
    videos = harvester.search_business_podcasts(search_terms, max_results=20)
    
    print(f"📺 Found {len(videos)} videos to process")
    
    all_insights = []
    processed_count = 0
    
    for video in videos:
        try:
            print(f"   🔍 Processing: {video['title'][:60]}...")
            
            # Get captions
            captions = harvester.get_video_captions(video['video_id'])
            
            if captions:
                # Extract insights
                insights = harvester.extract_insights_from_captions(captions, video, search_keywords)
                all_insights.extend(insights)
                
                print(f"     ✅ Found {len(insights)} insights")
            else:
                print(f"     ⚠️  No captions available")
            
            processed_count += 1
            time.sleep(2)  # Rate limiting between videos
            
        except Exception as e:
            print(f"     ❌ Error processing video: {e}")
    
    print(f"✅ Processing complete! Found {len(all_insights)} insights from {processed_count} videos")
    
    return all_insights

def main():
    """Test the YouTube harvester"""
    print("🔍 Testing YouTube business podcast harvesting...")
    
    # Check for API key
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        print("⚠️  No YouTube API key found. Set YOUTUBE_API_KEY environment variable.")
        print("   Get your API key from: https://console.cloud.google.com/apis/credentials")
        return
    
    try:
        # Harvest insights
        insights = harvest_youtube_business_podcasts(api_key)
        
        if insights:
            # Save to CSV
            output_file = "data/youtube_business_podcasts.csv"
            with open(output_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=insights[0].keys())
                writer.writeheader()
                writer.writerows(insights)
            
            print(f"📁 Saved {len(insights)} insights to {output_file}")
            
            # Show sample insights
            print("\n📋 Sample insights:")
            for i, insight in enumerate(insights[:3]):
                print(f"  {i+1}. {insight['description'][:100]}...")
                print(f"     Source: {insight['source_(interview_#/_name)']}")
                print(f"     Link: {insight['link']}")
                print()
        else:
            print("❌ No insights found")
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()

