#!/usr/bin/env python3
"""
Real API Harvester for 100K Insights Goal
Uses actual APIs to collect insights from multiple platforms
"""

import os
import csv
import json
import requests
import time
from datetime import datetime
from typing import List, Dict, Any
import praw
import pandas as pd

class RealHarvester:
    def __init__(self):
        self.insights = []
        self.api_keys = self.load_api_keys()
        
    def load_api_keys(self):
        """Load API keys from environment or .env file"""
        keys = {}
        
        # Reddit API
        keys['reddit_client_id'] = os.getenv('REDDIT_CLIENT_ID')
        keys['reddit_client_secret'] = os.getenv('REDDIT_CLIENT_SECRET')
        keys['reddit_user_agent'] = os.getenv('REDDIT_USER_AGENT', 'WisdomHarvester/1.0')
        
        # GitHub API
        keys['github_token'] = os.getenv('GITHUB_TOKEN')
        
        # Stack Exchange API
        keys['stackexchange_key'] = os.getenv('STACKEXCHANGE_KEY')
        
        return keys
    
    def harvest_reddit_real(self, subreddits: List[str], limit_per_sub: int = 100):
        """Harvest real insights from Reddit"""
        if not self.api_keys['reddit_client_id']:
            print("⚠️  Reddit API credentials not found. Skipping Reddit harvesting.")
            return
        
        print(f"🔴 Harvesting from {len(subreddits)} subreddits...")
        
        try:
            reddit = praw.Reddit(
                client_id=self.api_keys['reddit_client_id'],
                client_secret=self.api_keys['reddit_client_secret'],
                user_agent=self.api_keys['reddit_user_agent']
            )
            
            for subreddit_name in subreddits:
                print(f"📥 Processing r/{subreddit_name}...")
                
                try:
                    subreddit = reddit.subreddit(subreddit_name)
                    
                    # Get top posts
                    for post in subreddit.top(limit=limit_per_sub):
                        if post.selftext and len(post.selftext) > 100:
                            insight = {
                                'description': post.title[:200] + "..." if len(post.title) > 200 else post.title,
                                'rationale': post.selftext[:500] + "..." if len(post.selftext) > 500 else post.selftext,
                                'use_case': f"Reddit community knowledge from r/{subreddit_name}",
                                'impact_area': 'Community',
                                'transferability_score': 3,
                                'actionability_rating': 3,
                                'evidence_strength': 'Community-shared',
                                'type_(form)': 'community-insight',
                                'tag_(application)': f'Reddit_{subreddit_name}',
                                'source': 'Reddit',
                                'date': datetime.fromtimestamp(post.created_utc).strftime('%Y-%m-%d'),
                                'link': f'https://reddit.com{post.permalink}',
                                'notes': f'Score: {post.score}, Comments: {post.num_comments}'
                            }
                            self.insights.append(insight)
                    
                    # Rate limiting
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"❌ Error processing r/{subreddit_name}: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Reddit API error: {e}")
    
    def harvest_github_real(self, repos: List[str], limit_per_repo: int = 50):
        """Harvest real insights from GitHub"""
        if not self.api_keys['github_token']:
            print("⚠️  GitHub API token not found. Skipping GitHub harvesting.")
            return
        
        print(f"🐙 Harvesting from {len(repos)} GitHub repos...")
        
        headers = {
            'Authorization': f'token {self.api_keys["github_token"]}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        for repo in repos:
            print(f"📥 Processing {repo}...")
            
            try:
                # Get issues
                issues_url = f'https://api.github.com/repos/{repo}/issues'
                params = {
                    'state': 'closed',
                    'sort': 'comments',
                    'per_page': limit_per_repo
                }
                
                response = requests.get(issues_url, headers=headers, params=params)
                response.raise_for_status()
                
                issues = response.json()
                
                for issue in issues:
                    if issue['body'] and len(issue['body']) > 100:
                        insight = {
                            'description': issue['title'][:200] + "..." if len(issue['title']) > 200 else issue['title'],
                            'rationale': issue['body'][:500] + "..." if len(issue['body']) > 500 else issue['body'],
                            'use_case': f"GitHub issue resolution from {repo}",
                            'impact_area': 'Efficiency',
                            'transferability_score': 4,
                            'actionability_rating': 4,
                            'evidence_strength': 'Code-validated',
                            'type_(form)': 'issue-solution',
                            'tag_(application)': f'GitHub_{repo.split("/")[-1]}',
                            'source': 'GitHub',
                            'date': issue['closed_at'][:10] if issue['closed_at'] else datetime.now().strftime('%Y-%m-%d'),
                            'link': issue['html_url'],
                            'notes': f'Comments: {issue["comments"]}, Labels: {", ".join([l["name"] for l in issue["labels"]])}'
                        }
                        self.insights.append(insight)
                
                # Rate limiting
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ Error processing {repo}: {e}")
                continue
    
    def harvest_stackexchange_real(self, sites: List[str], limit_per_site: int = 50):
        """Harvest real insights from Stack Exchange"""
        print(f"📚 Harvesting from {len(sites)} Stack Exchange sites...")
        
        for site in sites:
            print(f"📥 Processing {site}...")
            
            try:
                # Get top questions
                url = f'https://api.stackexchange.com/2.3/questions'
                params = {
                    'site': site,
                    'sort': 'votes',
                    'order': 'desc',
                    'pagesize': limit_per_site,
                    'filter': 'withbody'
                }
                
                if self.api_keys['stackexchange_key']:
                    params['key'] = self.api_keys['stackexchange_key']
                
                response = requests.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                for question in data.get('items', []):
                    if question.get('body') and len(question['body']) > 100:
                        # Clean HTML tags
                        body = question['body'].replace('<p>', '').replace('</p>', '\n').replace('<br>', '\n')
                        body = ' '.join(body.split())[:500] + "..." if len(body) > 500 else body
                        
                        insight = {
                            'description': question['title'][:200] + "..." if len(question['title']) > 200 else question['title'],
                            'rationale': body,
                            'use_case': f"Stack Exchange Q&A from {site}",
                            'impact_area': 'Knowledge',
                            'transferability_score': 4,
                            'actionability_rating': 4,
                            'evidence_strength': 'Community-voted',
                            'type_(form)': 'qa-solution',
                            'tag_(application)': f'StackExchange_{site}',
                            'source': 'StackExchange',
                            'date': datetime.fromtimestamp(question['creation_date']).strftime('%Y-%m-%d'),
                            'link': question['link'],
                            'notes': f'Score: {question["score"]}, Answers: {question["answer_count"]}, Tags: {", ".join(question["tags"][:3])}'
                        }
                        self.insights.append(insight)
                
                # Rate limiting
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ Error processing {site}: {e}")
                continue
    
    def harvest_web_content(self, urls: List[str], limit_per_url: int = 20):
        """Harvest insights from web content"""
        print(f"🌐 Harvesting from {len(urls)} web sources...")
        
        for url in urls:
            print(f"📥 Processing {url}...")
            
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                # Simple text extraction (you could use BeautifulSoup for better parsing)
                content = response.text[:5000]  # Limit content size
                
                # Create insights from content chunks
                chunks = [content[i:i+500] for i in range(0, len(content), 500)]
                
                for i, chunk in enumerate(chunks[:limit_per_url]):
                    if len(chunk) > 100:
                        insight = {
                            'description': f"Web insight from {url} #{i+1}",
                            'rationale': chunk,
                            'use_case': f"Web content analysis",
                            'impact_area': 'Information',
                            'transferability_score': 3,
                            'actionability_rating': 3,
                            'evidence_strength': 'Web-published',
                            'type_(form)': 'web-content',
                            'tag_(application)': f'Web_{url.split("//")[1].split("/")[0]}',
                            'source': 'Web',
                            'date': datetime.now().strftime('%Y-%m-%d'),
                            'link': url,
                            'notes': f'Content chunk {i+1}'
                        }
                        self.insights.append(insight)
                
                # Rate limiting
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ Error processing {url}: {e}")
                continue
    
    def save_insights(self, filename: str = "data/real_harvested_insights.csv"):
        """Save all harvested insights"""
        if not self.insights:
            print("❌ No insights to save")
            return False
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            if self.insights:
                writer = csv.DictWriter(f, fieldnames=self.insights[0].keys())
                writer.writeheader()
                writer.writerows(self.insights)
        
        print(f"✅ Saved {len(self.insights)} insights to {filename}")
        return True

def main():
    print("🚀 Real API Harvester for 100K Insights Goal")
    print("=" * 50)
    
    harvester = RealHarvester()
    
    # Define target sources
    reddit_subreddits = [
        'entrepreneur', 'startups', 'business', 'marketing', 'sales',
        'productivity', 'leadership', 'management', 'finance', 'investing'
    ]
    
    github_repos = [
        'facebook/react', 'microsoft/vscode', 'google/tensorflow',
        'kubernetes/kubernetes', 'docker/docker-ce', 'hashicorp/terraform'
    ]
    
    stackexchange_sites = [
        'stackoverflow', 'serverfault', 'superuser', 'askubuntu',
        'datascience', 'ai', 'softwareengineering'
    ]
    
    web_urls = [
        'https://www.entrepreneur.com/',
        'https://www.inc.com/',
        'https://www.fastcompany.com/',
        'https://www.forbes.com/entrepreneurs/'
    ]
    
    # Start harvesting
    print(f"🎯 Target: 100,000 insights")
    print(f"📊 Current: ~2,000 insights")
    print(f"📈 Need: ~98,000 more insights")
    print()
    
    # Harvest from all sources
    harvester.harvest_reddit_real(reddit_subreddits, 50)
    harvester.harvest_github_real(github_repos, 30)
    harvester.harvest_stackexchange_real(stackexchange_sites, 40)
    harvester.harvest_web_content(web_urls, 10)
    
    # Save results
    harvester.save_insights()
    
    print(f"\n🎉 Real Harvesting Complete!")
    print(f"📊 Total insights harvested: {len(harvester.insights)}")
    print(f"📈 New total: ~{2000 + len(harvester.insights):,} insights")
    print(f"🎯 Progress toward 100K: {((2000 + len(harvester.insights)) / 100000 * 100):.1f}%")
    
    print(f"\n📋 Next steps:")
    print(f"1. Set up API keys for more sources")
    print(f"2. Run OpenAI processing for quality filtering")
    print(f"3. Integrate with search system")
    print(f"4. Scale up harvesting with more sources")

if __name__ == "__main__":
    main()
