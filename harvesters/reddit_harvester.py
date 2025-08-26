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
        """Harvest from a specific subreddit using multi-mode approach"""
        results = []
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # Check if multi-mode harvesting is configured
            modes = harvest_config.get("modes")
            if modes:
                self.logger.info(f"Using multi-mode harvesting for r/{subreddit_name}")
                for mode in modes:
                    try:
                        mode_results = self._harvest_mode(subreddit, subreddit_name, mode, harvest_config)
                        results.extend(mode_results)
                        self.logger.info(f"Mode '{mode['name']}': {len(mode_results)} items")
                    except Exception as e:
                        self.logger.error(f"Failed to harvest mode '{mode['name']}': {e}")
                        continue
            else:
                # Fallback to legacy single-mode harvesting
                self.logger.info(f"Using legacy harvesting for r/{subreddit_name}")
                results = self._harvest_legacy(subreddit, subreddit_name, harvest_config)
            
            return results
            
        except PRAWException as e:
            raise HarvesterError(f"PRAW error harvesting r/{subreddit_name}: {e}")
        except Exception as e:
            raise HarvesterError(f"Error harvesting r/{subreddit_name}: {e}")
    
    def _harvest_mode(self, subreddit, subreddit_name: str, mode: Dict[str, Any], harvest_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Harvest using a specific mode"""
        results = []
        mode_name = mode.get("name", "unknown")
        mode_type = mode.get("type", "listing")
        
        try:
            if mode_type == "search":
                # Keyword search mode
                queries = mode.get("queries", [])
                time_filters = mode.get("time_filters", ["all"])
                posts_per_query = mode.get("posts_per_query_per_sub", 20)
                
                for query in queries:
                    for time_filter in time_filters:
                        try:
                            search_results = subreddit.search(query, time_filter=time_filter, limit=posts_per_query)
                            for post in search_results:
                                if self._should_process_post(post, harvest_config):
                                    post_result = self._process_post(post, subreddit_name)
                                    if post_result:
                                        results.append(post_result)
                                    
                                    # Process comments
                                    comment_results = self._harvest_comments_enhanced(post, subreddit_name, harvest_config)
                                    results.extend(comment_results)
                                    
                                    self._throttle(harvest_config.get("throttle_sec", 1.0))
                        except Exception as e:
                            self.logger.warning(f"Error in search mode '{mode_name}' with query '{query}': {e}")
                            continue
                            
            elif mode_type == "listing":
                # Listing mode (top, new, controversial, etc.)
                listing_type = mode.get("listing", "top")
                time_filters = mode.get("time_filters", ["year"])
                posts_per_sub = mode.get("posts_per_sub", 40)
                
                for time_filter in time_filters:
                    try:
                        if listing_type == "top":
                            posts = subreddit.top(time_filter=time_filter, limit=posts_per_sub)
                        elif listing_type == "new":
                            posts = subreddit.new(limit=posts_per_sub)
                        elif listing_type == "hot":
                            posts = subreddit.hot(limit=posts_per_sub)
                        elif listing_type == "controversial":
                            posts = subreddit.controversial(time_filter=time_filter, limit=posts_per_sub)
                        else:
                            posts = subreddit.top(time_filter=time_filter, limit=posts_per_sub)
                        
                        for post in posts:
                            if self._should_process_post(post, harvest_config):
                                post_result = self._process_post(post, subreddit_name)
                                if post_result:
                                    results.append(post_result)
                                
                                # Process comments
                                comment_results = self._harvest_comments_enhanced(post, subreddit_name, harvest_config)
                                results.extend(comment_results)
                                
                                self._throttle(harvest_config.get("throttle_sec", 1.0))
                    except Exception as e:
                        self.logger.warning(f"Error in listing mode '{mode_name}' with time_filter '{time_filter}': {e}")
                        continue
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in harvest mode '{mode_name}': {e}")
            return []
    
    def _should_process_post(self, post, harvest_config: Dict[str, Any]) -> bool:
        """Check if post should be processed based on filters"""
        filters = harvest_config.get("filters", {})
        
        # Check minimum score
        min_post_score = filters.get("min_post_score", 0)
        if post.score < min_post_score:
            return False
        
        # Check minimum comments
        min_comments = filters.get("min_comments", 0)
        if post.num_comments < min_comments:
            return False
        
        # Check if self post is required
        require_self_post = filters.get("require_self_post", False)
        if require_self_post and not post.is_self:
            return False
        
        # Check flairs
        allowed_flairs = filters.get("allowed_flairs", [])
        if allowed_flairs and post.link_flair_text not in allowed_flairs:
            return False
        
        return True
    
    def _harvest_legacy(self, subreddit, subreddit_name: str, harvest_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Legacy single-mode harvesting"""
        results = []
        
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
    
    def _harvest_comments_enhanced(self, post, subreddit_name: str, harvest_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Enhanced comment harvesting with keyword boosting and confidence sorting"""
        results = []
        
        try:
            comments_config = harvest_config.get("comments", {})
            if not comments_config:
                # Fallback to legacy comment harvesting
                return self._harvest_comments(post, subreddit_name, harvest_config)
            
            # Get comment configuration
            top_level_limit = comments_config.get("top_level_limit", 30)
            child_limit = comments_config.get("child_limit", 15)
            keyword_boost = comments_config.get("keyword_boost", [])
            max_depth = comments_config.get("max_depth", 2)
            
            # Replace more comments to get more content
            post.comment_sort = "confidence"  # Sort by confidence
            post.comments.replace_more(limit=top_level_limit)
            
            # Process top-level comments
            for comment in post.comments[:top_level_limit]:
                if self._should_process_comment(comment, harvest_config):
                    comment_result = self._process_comment(comment, subreddit_name, post)
                    if comment_result:
                        # Boost score if comment contains keywords
                        if keyword_boost and any(keyword.lower() in comment.body.lower() for keyword in keyword_boost):
                            comment_result["score"] = comment_result.get("score", 0) + 5  # Boost score
                        results.append(comment_result)
                    
                    # Process child comments if depth allows
                    if max_depth > 1:
                        child_results = self._harvest_child_comments(comment, subreddit_name, post, harvest_config, max_depth - 1, child_limit)
                        results.extend(child_results)
            
            return results
            
        except Exception as e:
            self.logger.warning(f"Error harvesting comments for post {post.id}: {e}")
            return []
    
    def _harvest_child_comments(self, parent_comment, subreddit_name: str, post, harvest_config: Dict[str, Any], depth: int, limit: int) -> List[Dict[str, Any]]:
        """Harvest child comments recursively"""
        results = []
        
        if depth <= 0 or limit <= 0:
            return results
        
        try:
            # Replace more replies
            parent_comment.replies.replace_more(limit=limit)
            
            for reply in parent_comment.replies[:limit]:
                if self._should_process_comment(reply, harvest_config):
                    comment_result = self._process_comment(reply, subreddit_name, post)
                    if comment_result:
                        results.append(comment_result)
                    
                    # Recursively process deeper replies
                    if depth > 1:
                        child_results = self._harvest_child_comments(reply, subreddit_name, post, harvest_config, depth - 1, limit // 2)
                        results.extend(child_results)
            
            return results
            
        except Exception as e:
            self.logger.warning(f"Error harvesting child comments: {e}")
            return []
    
    def _should_process_comment(self, comment, harvest_config: Dict[str, Any]) -> bool:
        """Check if comment should be processed"""
        try:
            # Skip deleted comments
            if comment.author is None:
                return False
            
            # Check minimum score
            min_comment_score = harvest_config.get("filters", {}).get("min_comment_score", 1)
            if comment.score < min_comment_score:
                return False
            
            # Check minimum length
            comment_min_chars = harvest_config.get("comment_min_chars", 30)
            if len(comment.body) < comment_min_chars:
                return False
            
            # Check maximum length
            comment_max_chars = harvest_config.get("comment_max_chars", 2500)
            if len(comment.body) > comment_max_chars:
                return False
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Error checking comment: {e}")
            return False
    
    def _process_comment(self, comment, subreddit_name: str, post) -> Optional[Dict[str, Any]]:
        """Process a Reddit comment"""
        try:
            # Check if comment contains tacit knowledge
            keywords = self.config.get("keywords", [])
            content = comment.body
            
            if not self._contains_tacit_knowledge(content, keywords):
                return None
            
            return {
                "site": "reddit",
                "subreddit": subreddit_name,
                "title": f"Comment on: {self._safe_text(post.title, 100)}",
                "description": self._safe_text(comment.body, 500),
                "author": comment.author.name if comment.author else "deleted",
                "score": comment.score,
                "url": f"https://reddit.com{comment.permalink}",
                "created_utc": comment.created_utc,
                "num_comments": 0,
                "source_(interview_#/_name)": f"reddit/comment/{comment.author.name if comment.author else 'deleted'}",
                "link": f"https://reddit.com{comment.permalink}",
                "notes": f"subreddit: {subreddit_name} | parent: {self._safe_text(post.title, 50)} | score: {comment.score} | tacit: {self._contains_tacit_knowledge(content, keywords)}"
            }
            
        except Exception as e:
            self.logger.warning(f"Error processing comment {comment.id}: {e}")
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
                    # Check comment score and length - be more lenient
                    if comment.score < min_comment_score:
                        continue
                    
                    comment_text = comment.body
                    if len(comment_text) < comment_min_chars or len(comment_text) > comment_max_chars:
                        continue
                    
                    # For technician subreddits, be more aggressive about capturing content
                    # Check if comment contains tacit knowledge OR if it's from a technician subreddit
                    keywords = self.config.get("keywords", [])
                    contains_tacit = self._contains_tacit_knowledge(comment_text, keywords)
                    
                    # If it's a technician subreddit, also capture comments that might have tacit knowledge
                    technician_subreddits = ['HVAC', 'Plumbing', 'electricians', 'Maintenance', 'Machinists', 'Technicians']
                    is_technician_sub = subreddit_name in technician_subreddits
                    
                    # Capture if it has tacit knowledge OR if it's from a technician subreddit with decent score
                    if contains_tacit or (is_technician_sub and comment.score >= 10):
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
                            "notes": f"subreddit: {subreddit_name} | parent: {post.title[:50]} | score: {comment.score} | tacit: {contains_tacit}"
                        }
                        
                        results.append(result)
                    
                except Exception as e:
                    self.logger.warning(f"Error processing comment {comment.id}: {e}")
                    continue
            
            return results
            
        except Exception as e:
            self.logger.warning(f"Error harvesting comments from post {post.id}: {e}")
            return results
