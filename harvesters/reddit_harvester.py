"""
Reddit Harvester Module

Harvests insights from Reddit posts and comments.
"""

import os
from typing import Any, Dict, List, Optional

import praw
from praw.exceptions import PRAWException

from .base_harvester import BaseHarvester, HarvesterError, ConfigurationError


class RedditHarvester(BaseHarvester):
    """Harvester for Reddit content"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config, "Reddit")
        
        # Initialize Reddit client
        try:
            self.reddit = praw.Reddit(
                client_id=os.getenv("REDDIT_CLIENT_ID"),
                client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
                user_agent=os.getenv("REDDIT_USER_AGENT", "WisdomIndexHarvester/1.0")
            )
            
            if not os.getenv("REDDIT_CLIENT_ID") or not os.getenv("REDDIT_CLIENT_SECRET"):
                raise ConfigurationError("Reddit API credentials not found in environment variables")
                
        except Exception as e:
            raise HarvesterError(f"Failed to initialize Reddit client: {e}")
    
    def harvest(self) -> List[Dict[str, Any]]:
        """Harvest insights from Reddit"""
        results = []
        
        try:
            reddit_config = self.config.get("reddit", {})
            subreddits = reddit_config.get("subreddits", [])
            harvest_config = reddit_config.get("harvest", {})
            
            if not subreddits:
                self.logger.warning("No subreddits configured for Reddit harvesting")
                return results
            
            for subreddit_name in subreddits:
                try:
                    subreddit_results = self._harvest_subreddit(subreddit_name, harvest_config)
                    results.extend(subreddit_results)
                    self.logger.info(f"Harvested {len(subreddit_results)} items from r/{subreddit_name}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to harvest from r/{subreddit_name}: {e}")
                    continue
            
            return results
            
        except Exception as e:
            raise HarvesterError(f"Reddit harvest failed: {e}")
    
    def _harvest_subreddit(self, subreddit_name: str, harvest_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Harvest from a specific subreddit"""
        results = []
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # Get configuration parameters
            limit = harvest_config.get("limit", 30)
            time_filter = harvest_config.get("time_filter", "month")
            sort = harvest_config.get("sort", "top")
            scan_comments = harvest_config.get("scan_comments", True)
            min_post_score = harvest_config.get("min_post_score", 5)
            min_comment_score = harvest_config.get("min_comment_score", 5)
            throttle_sec = harvest_config.get("throttle_sec", 0.7)
            
            # Get posts
            if sort == "top":
                posts = subreddit.top(time_filter=time_filter, limit=limit)
            elif sort == "hot":
                posts = subreddit.hot(limit=limit)
            elif sort == "new":
                posts = subreddit.new(limit=limit)
            else:
                posts = subreddit.top(time_filter=time_filter, limit=limit)
            
            for post in posts:
                try:
                    # Check post score
                    if post.score < min_post_score:
                        continue
                    
                    # Process post
                    post_result = self._process_post(post, subreddit_name)
                    if post_result:
                        results.append(post_result)
                    
                    # Process comments if enabled
                    if scan_comments:
                        comment_results = self._harvest_comments(post, subreddit_name, harvest_config)
                        results.extend(comment_results)
                    
                    # Throttle requests
                    self._throttle(throttle_sec)
                    
                except Exception as e:
                    self.logger.warning(f"Error processing post {post.id}: {e}")
                    continue
            
            return results
            
        except PRAWException as e:
            raise HarvesterError(f"PRAW error harvesting r/{subreddit_name}: {e}")
        except Exception as e:
            raise HarvesterError(f"Error harvesting r/{subreddit_name}: {e}")
    
    def _process_post(self, post, subreddit_name: str) -> Optional[Dict[str, Any]]:
        """Process a Reddit post"""
        try:
            # Check if post contains tacit knowledge
            keywords = self.config.get("keywords", [])
            content = f"{post.title} {post.selftext}"
            
            if not self._contains_tacit_knowledge(content, keywords):
                return None
            
            return {
                "site": "reddit",
                "subreddit": subreddit_name,
                "title": self._safe_text(post.title, 200),
                "description": self._safe_text(post.selftext, 500),
                "author": post.author.name if post.author else "deleted",
                "score": post.score,
                "url": f"https://reddit.com{post.permalink}",
                "created_utc": post.created_utc,
                "num_comments": post.num_comments,
                "source_(interview_#/_name)": f"reddit/{subreddit_name}/{post.author.name if post.author else 'deleted'}",
                "link": f"https://reddit.com{post.permalink}",
                "notes": f"subreddit: {subreddit_name} | score: {post.score} | comments: {post.num_comments}"
            }
            
        except Exception as e:
            self.logger.warning(f"Error processing post {post.id}: {e}")
            return None
    
    def _harvest_comments(self, post, subreddit_name: str, harvest_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Harvest comments from a post"""
        results = []
        
        try:
            min_comment_score = harvest_config.get("min_comment_score", 5)
            per_thread_comment_limit = harvest_config.get("per_thread_comment_limit", 5)
            comment_min_chars = harvest_config.get("comment_min_chars", 120)
            comment_max_chars = harvest_config.get("comment_max_chars", 1200)
            
            # Get comments
            post.comments.replace_more(limit=0)  # Don't expand MoreComments
            comments = post.comments.list()[:per_thread_comment_limit]
            
            for comment in comments:
                try:
                    # Check comment score and length
                    if comment.score < min_comment_score:
                        continue
                    
                    comment_text = comment.body
                    if len(comment_text) < comment_min_chars or len(comment_text) > comment_max_chars:
                        continue
                    
                    # Check if comment contains tacit knowledge
                    keywords = self.config.get("keywords", [])
                    if not self._contains_tacit_knowledge(comment_text, keywords):
                        continue
                    
                    result = {
                        "site": "reddit",
                        "subreddit": subreddit_name,
                        "title": f"Comment on: {self._safe_text(post.title, 100)}",
                        "description": self._safe_text(comment_text, 500),
                        "author": comment.author.name if comment.author else "deleted",
                        "score": comment.score,
                        "url": f"https://reddit.com{comment.permalink}",
                        "created_utc": comment.created_utc,
                        "num_comments": 0,
                        "source_(interview_#/_name)": f"reddit/comment/{comment.author.name if comment.author else 'deleted'}",
                        "link": f"https://reddit.com{comment.permalink}",
                        "notes": f"subreddit: {subreddit_name} | parent: {post.title[:50]} | score: {comment.score}"
                    }
                    
                    results.append(result)
                    
                except Exception as e:
                    self.logger.warning(f"Error processing comment {comment.id}: {e}")
                    continue
            
            return results
            
        except Exception as e:
            self.logger.warning(f"Error harvesting comments from post {post.id}: {e}")
            return results
