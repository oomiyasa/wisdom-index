#!/usr/bin/env python3
"""
Harvest tacit knowledge from podcast platform APIs
"""

import requests
import re
import csv
import time
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class PodcastPlatformHarvester:
    def __init__(self):
        self.spotify_token = os.getenv('SPOTIFY_TOKEN')
        self.spotify_client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.spotify_client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        self.apple_podcast_token = os.getenv('APPLE_PODCAST_TOKEN')
        
    def harvest_spotify_podcasts(self, search_terms: List[str], max_results: int = 20) -> List[Dict[str, Any]]:
        """Harvest from Spotify Podcasts API"""
        if not self.spotify_token:
            print(f"🔍 Debug: Client ID exists: {bool(self.spotify_client_id)}")
            print(f"🔍 Debug: Client Secret exists: {bool(self.spotify_client_secret)}")
            if self.spotify_client_id and self.spotify_client_secret:
                print("🔄 Getting Spotify access token...")
                self.spotify_token = self._get_spotify_token()
                if not self.spotify_token:
                    print("⚠️  Failed to get Spotify token. Skipping Spotify harvest.")
                    return []
            else:
                print("⚠️  No Spotify credentials found. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env file.")
                return []
        
        print("🔍 Harvesting from Spotify Podcasts...")
        
        headers = {
            'Authorization': f'Bearer {self.spotify_token}',
            'Content-Type': 'application/json'
        }
        
        all_episodes = []
        
        for search_term in search_terms:
            try:
                print(f"   🔍 Searching Spotify for: {search_term}")
                
                # Search for podcasts
                search_url = f"https://api.spotify.com/v1/search?q={quote_plus(search_term)}&type=show&market=US&limit=10"
                response = requests.get(search_url, headers=headers)
                
                if response.status_code == 200:
                    shows = response.json().get('shows', {}).get('items', [])
                    
                    for show in shows:
                        show_id = show['id']
                        show_name = show['name']
                        
                        # Get episodes for this show
                        episodes_url = f"https://api.spotify.com/v1/shows/{show_id}/episodes?market=US&limit=5"
                        episodes_response = requests.get(episodes_url, headers=headers)
                        
                        if episodes_response.status_code == 200:
                            episodes = episodes_response.json().get('items', [])
                            
                            for episode in episodes:
                                episode_info = {
                                    'platform': 'spotify',
                                    'show_name': show_name,
                                    'episode_name': episode['name'],
                                    'episode_id': episode['id'],
                                    'description': episode.get('description', ''),
                                    'duration_ms': episode.get('duration_ms', 0),
                                    'release_date': episode.get('release_date', ''),
                                    'search_term': search_term
                                }
                                all_episodes.append(episode_info)
                
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                print(f"   ❌ Error searching Spotify for '{search_term}': {e}")
        
        return all_episodes
    
    def harvest_apple_podcasts(self, search_terms: List[str], max_results: int = 20) -> List[Dict[str, Any]]:
        """Harvest from Apple Podcasts API"""
        print("🔍 Harvesting from Apple Podcasts...")
        
        all_episodes = []
        
        for search_term in search_terms:
            try:
                print(f"   🔍 Searching Apple Podcasts for: {search_term}")
                
                # Apple Podcasts search API
                search_url = f"https://itunes.apple.com/search?term={quote_plus(search_term)}&entity=podcast&country=US&limit=10"
                response = requests.get(search_url)
                
                if response.status_code == 200:
                    results = response.json().get('results', [])
                    
                    for podcast in results:
                        podcast_id = podcast.get('collectionId')
                        podcast_name = podcast.get('collectionName')
                        
                        if podcast_id:
                            # Get episodes for this podcast
                            episodes_url = f"https://itunes.apple.com/lookup?id={podcast_id}&entity=podcastEpisode&country=US&limit=5"
                            episodes_response = requests.get(episodes_url)
                            
                            if episodes_response.status_code == 200:
                                episodes_data = episodes_response.json().get('results', [])
                                
                                for episode in episodes_data:
                                    if episode.get('kind') == 'podcast-episode':
                                        episode_info = {
                                            'platform': 'apple_podcasts',
                                            'show_name': podcast_name,
                                            'episode_name': episode.get('trackName', ''),
                                            'episode_id': episode.get('trackId', ''),
                                            'description': episode.get('description', ''),
                                            'duration_ms': episode.get('trackTimeMillis', 0),
                                            'release_date': episode.get('releaseDate', ''),
                                            'search_term': search_term
                                        }
                                        all_episodes.append(episode_info)
                
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                print(f"   ❌ Error searching Apple Podcasts for '{search_term}': {e}")
        
        return all_episodes
    
    def harvest_google_podcasts(self, search_terms: List[str], max_results: int = 20) -> List[Dict[str, Any]]:
        """Harvest from Google Podcasts (using web scraping approach)"""
        print("🔍 Harvesting from Google Podcasts...")
        
        all_episodes = []
        
        for search_term in search_terms:
            try:
                print(f"   🔍 Searching Google Podcasts for: {search_term}")
                
                # Google Podcasts search URL
                search_url = f"https://podcasts.google.com/search/{quote_plus(search_term)}"
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive'
                }
                
                response = requests.get(search_url, headers=headers)
                
                if response.status_code == 200:
                    # Extract podcast information from HTML
                    # This is a simplified approach - in practice, you'd need more sophisticated parsing
                    content = response.text
                    
                    # Look for podcast patterns in the HTML
                    podcast_patterns = [
                        r'<div[^>]*class="[^"]*podcast[^"]*"[^>]*>(.*?)</div>',
                        r'<div[^>]*class="[^"]*show[^"]*"[^>]*>(.*?)</div>',
                        r'<div[^>]*class="[^"]*episode[^"]*"[^>]*>(.*?)</div>'
                    ]
                    
                    for pattern in podcast_patterns:
                        matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
                        for match in matches:
                            # Clean HTML tags
                            clean_text = re.sub(r'<[^>]+>', ' ', match)
                            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                            
                            if len(clean_text) > 50:
                                episode_info = {
                                    'platform': 'google_podcasts',
                                    'show_name': 'Unknown Show',
                                    'episode_name': clean_text[:100],
                                    'episode_id': '',
                                    'description': clean_text,
                                    'duration_ms': 0,
                                    'release_date': '',
                                    'search_term': search_term
                                }
                                all_episodes.append(episode_info)
                
                time.sleep(2)  # Rate limiting
                
            except Exception as e:
                print(f"   ❌ Error searching Google Podcasts for '{search_term}': {e}")
        
        return all_episodes
    
    def extract_insights_from_descriptions(self, episodes: List[Dict[str, Any]], search_keywords: List[str]) -> List[Dict[str, Any]]:
        """Extract tacit knowledge insights from episode descriptions"""
        insights = []
        
        for episode in episodes:
            description = episode.get('description', '')
            if not description or len(description) < 100:
                continue
            
            # Split into sentences
            sentences = re.split(r'[.!?]+', description)
            
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) < 50:
                    continue
                
                # Check for tacit knowledge
                if self._contains_tacit_knowledge(sentence, search_keywords):
                    insight = {
                        "description": sentence,
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
                        "source_(interview_#/_name)": f"podcast/{episode['platform']}/{episode['show_name']}",
                        "link": "",
                        "notes": f"Episode: {episode['episode_name']}, Platform: {episode['platform']}, Content: {sentence}"
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
    
    def _get_spotify_token(self) -> Optional[str]:
        """Get Spotify access token using client credentials flow"""
        import base64
        
        if not self.spotify_client_id or not self.spotify_client_secret:
            return None
        
        # Encode credentials
        credentials = f"{self.spotify_client_id}:{self.spotify_client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        # Request token
        url = "https://accounts.spotify.com/api/token"
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "client_credentials"
        }
        
        try:
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            access_token = token_data.get('access_token')
            
            if access_token:
                print(f"✅ Spotify token obtained successfully!")
                return access_token
            else:
                print("❌ Failed to get Spotify token")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error getting Spotify token: {e}")
            return None

def harvest_podcast_platforms() -> List[Dict[str, Any]]:
    """Main function to harvest from podcast platforms"""
    
    harvester = PodcastPlatformHarvester()
    
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
        "startup founder interview",
        "business success story",
        "entrepreneurial wisdom",
        "business insights",
        "startup lessons",
        "business strategy interview",
        "entrepreneur advice",
        "business growth tips",
        "startup scaling",
        "business leadership",
        "entrepreneurial journey",
        "business innovation",
        "startup funding",
        "business development",
        "entrepreneurial mindset",
        "business operations",
        "startup marketing",
        "business management",
        "entrepreneurial success",
        "business transformation"
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
    
    print("🔍 Starting podcast platform harvest...")
    
    all_episodes = []
    all_insights = []
    
    # Harvest from Spotify
    spotify_episodes = harvester.harvest_spotify_podcasts(search_terms[:10], max_results=15)
    all_episodes.extend(spotify_episodes)
    print(f"   ✅ Spotify: {len(spotify_episodes)} episodes")
    
    # Harvest from Apple Podcasts
    apple_episodes = harvester.harvest_apple_podcasts(search_terms[:15], max_results=20)
    all_episodes.extend(apple_episodes)
    print(f"   ✅ Apple Podcasts: {len(apple_episodes)} episodes")
    
    # Harvest from Google Podcasts
    google_episodes = harvester.harvest_google_podcasts(search_terms[:10], max_results=15)
    all_episodes.extend(google_episodes)
    print(f"   ✅ Google Podcasts: {len(google_episodes)} episodes")
    
    print(f"📺 Processing {len(all_episodes)} episodes for insights...")
    
    # Extract insights from episode descriptions
    insights = harvester.extract_insights_from_descriptions(all_episodes, search_keywords)
    all_insights.extend(insights)
    
    print(f"✅ Podcast platform processing complete! Found {len(all_insights)} insights")
    
    return all_insights

def main():
    """Test the podcast platform harvester"""
    print("🔍 Testing podcast platform harvesting...")
    
    try:
        # Harvest insights
        insights = harvest_podcast_platforms()
        
        if insights:
            # Save to CSV
            output_file = "data/podcast_platforms.csv"
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
                print()
        else:
            print("❌ No insights found")
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
