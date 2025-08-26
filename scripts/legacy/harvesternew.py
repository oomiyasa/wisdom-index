
#!/usr/bin/env python3
"""
harvesternew.py — Multi-platform harvester for the Wisdom Index

Usage:
  python3 harvesternew.py --config wi_config_unified.yaml

Supports: Reddit, GitHub, StackExchange, Medium
"""

import argparse
import csv
import os
import re
import sys
import json
import requests
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from pathlib import Path
from urllib.parse import urljoin, urlparse, quote_plus

try:
    import yaml  # pyyaml
except Exception as e:
    print("ERROR: PyYAML not installed. Try: pip install pyyaml", file=sys.stderr)
    raise

# Optional: load .env if present
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

# PRAW (Reddit)
try:
    import praw
except Exception as e:
    print("ERROR: PRAW not installed. Try: pip install praw", file=sys.stderr)
    raise

# YouTube API
try:
    from googleapiclient.errors import HttpError
except Exception as e:
    print("WARNING: YouTube API not available. Try: pip install google-api-python-client", file=sys.stderr)


# ---------- Helpers ----------

def _cfg(config: Dict[str, Any], path: str, default=None):
    """Read nested keys with dotted path: e.g., 'reddit.harvest.scan_comments'"""
    node = config
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def _safe(s, maxlen=None):
    """Coerce to str, normalize whitespace, optional truncate."""
    if s is None:
        return ""
    text = str(s).replace("\r", " ").replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)
    if maxlen is not None and len(text) > maxlen:
        return text[:maxlen-1] + "…"
    return text


def _now_iso():
    return datetime.utcnow().date().isoformat()

def load_search_log():
    """Load previous search history to avoid duplicates"""
    log_file = "search_history.json"
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                return json.load(f)
        except:
            return {"searches": [], "last_run": None}
    return {"searches": [], "last_run": None}

def save_search_log(search_config, results_count, sources_config=None):
    """Save search configuration and results to avoid duplicates"""
    log_file = "search_history.json"
    log_data = load_search_log()
    
    search_id = {
        "timestamp": datetime.now().isoformat(),
        "platforms": sources_config or {},
        "subreddits": search_config.get("subreddits", []),
        "keywords": search_config.get("keywords", []),
        "time_filter": search_config.get("time_filter", "year"),
        "sort": search_config.get("sort", "top"),
        "limit": search_config.get("limit", 50),
        "results_count": results_count
    }
    
    log_data["searches"].append(search_id)
    log_data["last_run"] = datetime.now().isoformat()
    
    with open(log_file, 'w') as f:
        json.dump(log_data, f, indent=2)
    
    print(f"📝 Search logged to {log_file}")


# Wisdom Index Schema columns (order is IMPORTANT)
SCHEMA = [
    "description",
    "rationale",
    "use_case",
    "impact_area",
    "transferability_score",
    "actionability_rating",
    "evidence_strength",
    "type_(form)",
    "tag_(application)",
    "unique?",
    "role",
    "function",
    "company",
    "industry",
    "country",
    "date",
    "source_(interview_#/_name)",
    "link",
    "notes",
]


# ---------- Reddit Comment Harvest ----------

def harvest_comments_for_submission(config, submission, keywords_lower: List[str]) -> List[Dict[str, Any]]:
    harvest_cfg = _cfg(config, "reddit.harvest", {}) or {}
    if not harvest_cfg.get("scan_comments", False):
        return []

    max_comments = int(harvest_cfg.get("per_thread_comment_limit", 250))
    min_score    = int(harvest_cfg.get("min_comment_score", 0))
    min_chars    = int(harvest_cfg.get("comment_min_chars", 0))
    max_chars    = int(harvest_cfg.get("comment_max_chars", 10000))
    require_kw   = bool(harvest_cfg.get("require_keyword_in_comment", True))

    pat_strings  = harvest_cfg.get("comment_patterns", [])
    patterns = [re.compile(p, re.IGNORECASE) for p in pat_strings if p]

    # Expand all comments lazily and flatten
    try:
        submission.comments.replace_more(limit=0)
        flat = submission.comments.list()
    except Exception as e:
        print(f"  ! Skipping comments due to error: {e}")
        return []

    rows = []
    for c in flat[:max_comments]:
        try:
            if getattr(c, "author", None) is None or c.stickied:
                continue
            body = _safe(c.body)
            if len(body) < min_chars or len(body) > max_chars:
                continue
            if int(getattr(c, "score", 0)) < min_score:
                continue

            text_l = body.lower()
            if require_kw and keywords_lower:
                if not any(k in text_l for k in keywords_lower):
                    continue

            if patterns and not any(p.search(body) for p in patterns):
                continue

            row = {k: "" for k in SCHEMA}
            row.update({
                "description": body,
                "evidence_strength": "Anecdotal",
                "type_(form)": "comment",
                "date": datetime.utcfromtimestamp(getattr(c, "created_utc", 0)).date().isoformat() if getattr(c, "created_utc", None) else _now_iso(),
                "source_(interview_#/_name)": f"u/{getattr(getattr(c, 'author', None), 'name', 'deleted')}",
                "link": f"https://reddit.com{getattr(c, 'permalink', '')}",
                "notes": f"post: {_safe(submission.title, 140)}",
            })
            rows.append(row)
        except Exception:
            # keep going even if one comment is malformed
            continue

    return rows


# ---------- GitHub Harvest ----------

def harvest_github_issues(config) -> List[Dict[str, Any]]:
    """Harvest GitHub issues, discussions, and pull requests for tacit knowledge"""
    github_cfg = _cfg(config, "github", {}) or {}
    repos = github_cfg.get("repos", [])
    harvest_cfg = github_cfg.get("harvest", {}) or {}
    
    if not repos:
        print("⚠️  No GitHub repos configured")
        return []
    
    # GitHub API token (optional, but recommended for higher rate limits)
    github_token = os.getenv("GITHUB_TOKEN")
    headers = {}
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    
    headers["Accept"] = "application/vnd.github.v3+json"
    
    search_in = harvest_cfg.get("search_in", ["issues"])
    states = harvest_cfg.get("states", ["open", "closed"])
    label_includes = harvest_cfg.get("label_includes", [])
    comment_scan = harvest_cfg.get("comment_scan", True)
    min_comment_len = harvest_cfg.get("min_comment_len", 120)
    max_threads_per_repo = harvest_cfg.get("max_threads_per_repo", 20)  # Reduced to avoid rate limits
    throttle_sec = harvest_cfg.get("throttle_sec", 2.0)  # Increased throttle
    
    results = []
    keywords = _cfg(config, "keywords", [])
    
    print(f"🔍 GitHub: Scanning {len(repos)} repos for tacit knowledge...")
    
    for repo in repos:
        try:
            print(f"  • scanning {repo}...")
            
            # Search for issues/discussions with keywords
            for keyword in keywords:
                for search_type in search_in:
                    for state in states:
                        # Build search query
                        query_parts = [f"repo:{repo}", f"state:{state}"]
                        
                        if label_includes:
                            label_query = " OR ".join([f'label:"{label}"' for label in label_includes])
                            query_parts.append(f"({label_query})")
                        
                        query_parts.append(f'"{keyword}"')
                        query = " ".join(query_parts)
                        
                        print(f"    🔍 Searching: {query}")
                        
                        # Search GitHub API
                        search_url = f"https://api.github.com/search/{search_type}"
                        params = {
                            "q": query,
                            "sort": "updated",
                            "order": "desc",
                            "per_page": min(100, max_threads_per_repo)
                        }
                        
                        try:
                            response = requests.get(search_url, headers=headers, params=params)
                            response.raise_for_status()
                            data = response.json()
                            
                            for item in data.get("items", [])[:max_threads_per_repo]:
                                # Extract issue/discussion content
                                title = item.get("title", "")
                                body = item.get("body", "")
                                content = f"{title}\n\n{body}".strip()
                                
                                if len(content) < 100:  # Skip very short content
                                    continue
                                
                                # Create row for the main content
                                row = {k: "" for k in SCHEMA}
                                row.update({
                                    "description": _safe(content, 500),
                                    "evidence_strength": "Anecdotal",
                                    "type_(form)": search_type[:-1],  # "issues" -> "issue"
                                    "date": item.get("created_at", "").split("T")[0] if item.get("created_at") else _now_iso(),
                                    "source_(interview_#/_name)": f"github/{item.get('user', {}).get('login', 'unknown')}",
                                    "link": item.get("html_url", ""),
                                    "notes": f"repo: {repo} | keyword: {keyword} | state: {state}",
                                })
                                results.append(row)
                                
                                # Scan comments if enabled
                                if comment_scan and item.get("comments", 0) > 0:
                                    comments_url = item.get("comments_url", "")
                                    if comments_url:
                                        try:
                                            comments_response = requests.get(comments_url, headers=headers)
                                            comments_response.raise_for_status()
                                            comments_data = comments_response.json()
                                            
                                            for comment in comments_data:
                                                comment_body = comment.get("body", "")
                                                if len(comment_body) >= min_comment_len:
                                                    comment_row = {k: "" for k in SCHEMA}
                                                    comment_row.update({
                                                        "description": _safe(comment_body, 500),
                                                        "evidence_strength": "Anecdotal",
                                                        "type_(form)": "comment",
                                                        "date": comment.get("created_at", "").split("T")[0] if comment.get("created_at") else _now_iso(),
                                                        "source_(interview_#/_name)": f"github/{comment.get('user', {}).get('login', 'unknown')}",
                                                        "link": comment.get("html_url", ""),
                                                        "notes": f"repo: {repo} | issue: {title} | keyword: {keyword}",
                                                    })
                                                    results.append(comment_row)
                                            
                                            time.sleep(throttle_sec)
                                            
                                        except Exception as e:
                                            print(f"    ! Error fetching comments: {e}")
                                            continue
                            
                            time.sleep(throttle_sec)
                            
                        except Exception as e:
                            print(f"    ! Error searching {search_type}: {e}")
                            continue
                            
        except Exception as e:
            print(f"  ! Error scanning {repo}: {e}")
            continue
    
    print(f"✅ GitHub: Found {len(results)} items")
    return results


# ---------- Medium Harvest ----------

def harvest_medium_articles(config) -> List[Dict[str, Any]]:
    """Harvest Medium articles for tacit knowledge"""
    medium_cfg = _cfg(config, "medium", {}) or {}
    harvest_cfg = medium_cfg.get("harvest", {}) or {}
    
    # Medium doesn't have a public API, so we'll use RSS feeds and search
    publications = medium_cfg.get("publications", [])
    search_keywords = harvest_cfg.get("search_keywords", [])
    
    if not publications and not search_keywords:
        print("⚠️  No Medium publications or search keywords configured")
        return []
    
    print(f"🔍 Harvesting from Medium...")
    print(f"   Publications: {publications}")
    print(f"   Search keywords: {search_keywords[:5]}...")  # Show first 5
    
    rows = []
    
    # Harvest from publications
    for publication in publications:
        try:
            pub_rows = _harvest_medium_publication(publication, harvest_cfg, config)
            rows.extend(pub_rows)
            print(f"   📰 {publication}: {len(pub_rows)} articles")
            
            # Aggressive rate limiting between publications
            throttle_sec = harvest_cfg.get("throttle_sec", 8.0)
            print(f"     ⏳ Waiting {throttle_sec} seconds...")
            time.sleep(throttle_sec)
            
        except Exception as e:
            print(f"   ❌ Error harvesting {publication}: {e}")
    
    # Harvest from search keywords (limited to avoid rate limits)
    for keyword in search_keywords[:5]:  # Limit to first 5 keywords
        try:
            search_rows = _harvest_medium_search(keyword, harvest_cfg)
            rows.extend(search_rows)
            print(f"   🔍 '{keyword}': {len(search_rows)} articles")
            
            # Rate limiting between searches
            throttle_sec = harvest_cfg.get("throttle_sec", 8.0)
            print(f"     ⏳ Waiting {throttle_sec} seconds...")
            time.sleep(throttle_sec)
            
        except Exception as e:
            print(f"   ❌ Error searching '{keyword}': {e}")
    
    return rows

def _harvest_medium_publication(publication: str, harvest_cfg: Dict, config: Dict) -> List[Dict[str, Any]]:
    """Harvest articles from a specific Medium publication"""
    rows = []
    
    # Try multiple RSS feed formats for Medium
    rss_urls = [
        f"https://medium.com/feed/{publication}",
        f"https://medium.com/feed/@{publication}",
        f"https://medium.com/feed/tag/{publication}"
    ]
    
    max_articles = harvest_cfg.get("max_articles_per_pub", 10)
    max_retries = harvest_cfg.get("max_retries", 3)
    retry_delay = harvest_cfg.get("retry_delay", 15.0)
    count = 0
    
    # Rotate user agents to avoid detection
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
    ]
    
    for rss_url in rss_urls:
        if count >= max_articles:
            break
            
        # Try with retries
        for attempt in range(max_retries):
            try:
                print(f"     Trying RSS: {rss_url} (attempt {attempt + 1}/{max_retries})")
                
                # Rotate user agent
                user_agent = user_agents[attempt % len(user_agents)]
                headers = {
                    "User-Agent": user_agent,
                    "Accept": "application/rss+xml, application/xml, text/xml, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1"
                }
                
                response = requests.get(rss_url, headers=headers, timeout=15)
                
                # Check for rate limiting
                if response.status_code == 429:
                    print(f"       ⚠️  Rate limited (429). Waiting {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                
                response.raise_for_status()
                
                # Parse RSS feed
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.content)
                
                for item in root.findall(".//item"):
                    if count >= max_articles:
                        break
                        
                    title = item.find("title")
                    link = item.find("link")
                    description = item.find("description")
                    pub_date = item.find("pubDate")
                    
                    if title is not None and link is not None:
                        title_text = title.text or ""
                        link_text = link.text or ""
                        desc_text = description.text if description is not None else ""
                        date_text = pub_date.text if pub_date is not None else ""
                        
                        # Check if content contains tacit knowledge keywords
                        content = f"{title_text} {desc_text}".lower()
                        search_keywords = harvest_cfg.get("search_keywords", [])
                        
                        # More lenient filtering - check for tacit knowledge phrases
                        if any(keyword in content for keyword in search_keywords):
                            # Additional check: reject very generic "how to" articles
                            generic_phrases = ["how to", "guide", "tutorial", "introduction", "overview", "getting started", "step by step"]
                            if not any(phrase in title_text.lower() for phrase in generic_phrases):
                                row = {
                                    "description": title_text,
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
                                    "date": _parse_medium_date(date_text),
                                    "source_(interview_#/_name)": f"medium/{publication}",
                                    "link": link_text,
                                    "notes": desc_text[:200] if desc_text else ""
                                }
                                rows.append(row)
                                count += 1
                                print(f"       ✅ Found: {title_text[:50]}...")
                
                if count > 0:
                    break  # Found articles, no need to try other URLs
                    
                # Success, break out of retry loop
                break
                    
            except requests.exceptions.RequestException as e:
                print(f"       ❌ Request error with {rss_url} (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    print(f"         ⏳ Waiting {retry_delay} seconds before retry...")
                    time.sleep(retry_delay)
                continue
            except Exception as e:
                print(f"       ❌ Error with {rss_url} (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    print(f"         ⏳ Waiting {retry_delay} seconds before retry...")
                    time.sleep(retry_delay)
                continue
    
    return rows

def _harvest_medium_search(search_term: str, harvest_cfg: Dict) -> List[Dict[str, Any]]:
    """Search Medium for articles containing tacit knowledge"""
    rows = []
    
    # Medium search URL
    search_url = f"https://medium.com/search?q={search_term.replace(' ', '%20')}"
    
    max_retries = harvest_cfg.get("max_retries", 3)
    retry_delay = harvest_cfg.get("retry_delay", 15.0)
    max_results = harvest_cfg.get("max_search_results", 8)
    
    # Rotate user agents to avoid detection
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    
    # Try with retries
    for attempt in range(max_retries):
        try:
            print(f"     Searching Medium for '{search_term}' (attempt {attempt + 1}/{max_retries})")
            
            # Rotate user agent
            user_agent = user_agents[attempt % len(user_agents)]
            headers = {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            response = requests.get(search_url, headers=headers, timeout=15)
            
            # Check for rate limiting
            if response.status_code == 429:
                print(f"       ⚠️  Rate limited (429). Waiting {retry_delay} seconds...")
                time.sleep(retry_delay)
                continue
            
            response.raise_for_status()
            
            # Extract article links from search results
            # This is a simplified approach - in production you might want to use a proper HTML parser
            article_pattern = r'href="(https://medium\.com/[^"]*)"[^>]*>([^<]*)</a>'
            matches = re.findall(article_pattern, response.text)
            
            count = 0
            
            for link, title in matches[:max_results]:
                if count >= max_results:
                    break
                    
                # Check if title contains tacit knowledge
                title_lower = title.lower()
                search_keywords = harvest_cfg.get("search_keywords", [])
                
                if any(keyword in title_lower for keyword in search_keywords):
                    # Additional check: reject very generic articles
                    generic_phrases = ["how to", "guide", "tutorial", "introduction", "overview", "getting started", "step by step"]
                    if not any(phrase in title_lower for phrase in generic_phrases):
                        row = {
                            "description": title,
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
                            "source_(interview_#/_name)": f"medium/search/{search_term}",
                            "link": link,
                            "notes": f"Searched for: {search_term}"
                        }
                        rows.append(row)
                        count += 1
                        print(f"       ✅ Found: {title[:50]}...")
            
            # Success, break out of retry loop
            break
                
        except requests.exceptions.RequestException as e:
            print(f"       ❌ Request error searching for '{search_term}' (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                print(f"         ⏳ Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
            continue
        except Exception as e:
            print(f"       ❌ Error searching Medium for '{search_term}' (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                print(f"         ⏳ Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
            continue
    
    return rows

def _parse_medium_date(date_str: str) -> str:
    """Parse Medium RSS date format to YYYY-MM-DD"""
    try:
        # Medium RSS dates are typically in RFC 822 format
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        return dt.strftime("%Y-%m-%d")
    except:
        return datetime.now().strftime("%Y-%m-%d")


# ---------- StackExchange Harvest ----------

def harvest_stackexchange_questions(config) -> List[Dict[str, Any]]:
    """Harvest StackExchange questions and answers for tacit knowledge"""
    se_cfg = _cfg(config, "stackexchange", {}) or {}
    harvest_cfg = se_cfg.get("harvest", {}) or {}
    
    sites = se_cfg.get("sites", [])
    
    if not sites:
        print("⚠️  No StackExchange sites configured")
        return []
    
    print(f"🔍 Harvesting from StackExchange...")
    print(f"   Sites: {sites}")
    
    rows = []
    search_keywords = harvest_cfg.get("search_keywords", [])
    
    for site in sites:
        try:
            site_rows = _harvest_stackexchange_site(site, search_keywords, harvest_cfg)
            rows.extend(site_rows)
            print(f"   📚 {site}: {len(site_rows)} items")
            
            # Rate limiting between sites
            throttle_sec = harvest_cfg.get("throttle_sec", 5.0)
            print(f"     ⏳ Waiting {throttle_sec} seconds...")
            time.sleep(throttle_sec)
            
        except Exception as e:
            print(f"   ❌ Error harvesting {site}: {e}")
    
    return rows

def _harvest_stackexchange_site(site: str, search_keywords: List[str], harvest_cfg: Dict) -> List[Dict[str, Any]]:
    """Harvest from a specific StackExchange site"""
    rows = []
    
    max_retries = harvest_cfg.get("max_retries", 3)
    retry_delay = harvest_cfg.get("retry_delay", 10.0)
    limit_per_site = harvest_cfg.get("limit_per_site", 15)
    min_score = harvest_cfg.get("min_score", 3)
    
    # StackExchange API parameters - using public API
    base_url = "https://api.stackexchange.com/2.3"
    params = {
        "site": site,
        "pagesize": 30,  # Reduced to avoid rate limits
        "sort": "votes",
        "order": "desc",
        "filter": "withbody",
        "fromdate": int((datetime.now() - timedelta(days=365)).timestamp()),  # Last year
        "todate": int(datetime.now().timestamp())
    }
    
    # Try with retries
    for attempt in range(max_retries):
        try:
            print(f"     🔍 Getting top questions from {site} (attempt {attempt + 1}/{max_retries})...")
            
            # Get questions endpoint
            questions_url = f"{base_url}/questions"
            response = requests.get(questions_url, params=params, timeout=15)
            
            # Check for rate limiting
            if response.status_code == 429:
                print(f"       ⚠️  Rate limited (429). Waiting {retry_delay} seconds...")
                time.sleep(retry_delay)
                continue
            
            response.raise_for_status()
            data = response.json()
            
            count = 0
            for item in data.get("items", []):
                if count >= limit_per_site:
                    break
                    
                # Check if question has good answers and score
                if (item.get("answer_count", 0) > 0 and 
                    item.get("score", 0) >= min_score):
                    
                    question_title = item.get("title", "")
                    question_body = item.get("body", "")
                    tags = item.get("tags", [])
                    
                    # Look for tacit knowledge in question or tags
                    content = f"{question_title} {question_body} {' '.join(tags)}".lower()
                    
                    if _contains_tacit_knowledge(content, search_keywords):
                        row = {
                            "description": question_title,
                            "rationale": "",
                            "use_case": "",
                            "impact_area": "",
                            "transferability_score": "",
                            "actionability_rating": "",
                            "evidence_strength": "Peer-validated",
                            "type_(form)": "pattern",
                            "tag_(application)": "",
                            "unique?": "",
                            "role": "",
                            "function": "",
                            "company": "",
                            "industry": "",
                            "country": "",
                            "date": datetime.fromtimestamp(item.get("creation_date", 0)).strftime("%Y-%m-%d"),
                            "source_(interview_#/_name)": f"stackexchange/{site}",
                            "link": item.get("link", ""),
                            "notes": f"Score: {item.get('score', 0)}, Answers: {item.get('answer_count', 0)}, Tags: {', '.join(tags)}"
                        }
                        rows.append(row)
                        count += 1
                        print(f"       ✅ Found question: {question_title[:50]}...")
                    
                    # Also check top answers for tacit knowledge
                    if item.get("answer_count", 0) > 0 and count < limit_per_site:
                        answer_rows = _harvest_stackexchange_answers(item.get("question_id"), site, search_keywords, harvest_cfg)
                        rows.extend(answer_rows[:3])  # Limit to top 3 answers per question
                        count += len(answer_rows[:3])
            
            # Success, break out of retry loop
            break
            
        except requests.exceptions.RequestException as e:
            print(f"       ❌ Request error with {site} (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                print(f"         ⏳ Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
            continue
        except Exception as e:
            print(f"       ❌ Error getting questions from {site} (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                print(f"         ⏳ Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
            continue
    
    return rows

def _harvest_stackexchange_answers(question_id: int, site: str, search_keywords: List[str], harvest_cfg: Dict) -> List[Dict[str, Any]]:
    """Harvest answers for a specific question"""
    rows = []
    
    base_url = "https://api.stackexchange.com/2.3"
    params = {
        "site": site,
        "pagesize": 5,  # Get top 5 answers to avoid rate limits
        "sort": "votes",
        "order": "desc",
        "filter": "withbody"
    }
    
    try:
        answers_url = f"{base_url}/questions/{question_id}/answers"
        response = requests.get(answers_url, params=params, timeout=15)
        
        # Check for rate limiting
        if response.status_code == 429:
            print(f"         ⚠️  Rate limited (429) for answers. Skipping...")
            return rows
        
        response.raise_for_status()
        data = response.json()
        
        for answer in data.get("items", []):
            if answer.get("score", 0) >= harvest_cfg.get("min_score", 3):
                answer_body = answer.get("body", "")
                
                if _contains_tacit_knowledge(answer_body, search_keywords):
                    # Extract a snippet from the answer
                    snippet = _extract_snippet(answer_body, 200)
                    
                    row = {
                        "description": snippet,
                        "rationale": "",
                        "use_case": "",
                        "impact_area": "",
                        "transferability_score": "",
                        "actionability_rating": "",
                        "evidence_strength": "Peer-validated",
                        "type_(form)": "pattern",
                        "tag_(application)": "",
                        "unique?": "",
                        "role": "",
                        "function": "",
                        "company": "",
                        "industry": "",
                        "country": "",
                        "date": datetime.fromtimestamp(answer.get("creation_date", 0)).strftime("%Y-%m-%d"),
                        "source_(interview_#/_name)": f"stackexchange/{site}/answer",
                        "link": answer.get("link", ""),
                        "notes": f"Answer score: {answer.get('score', 0)}"
                    }
                    rows.append(row)
                    print(f"         ✅ Found answer: {snippet[:50]}...")
    
    except Exception as e:
        print(f"       ❌ Error fetching answers for question {question_id}: {e}")
    
    return rows

def _contains_tacit_knowledge(text: str, keywords: List[str]) -> bool:
    """Check if text contains tacit knowledge indicators"""
    text_lower = text.lower()
    
    # Check for keywords
    if any(keyword in text_lower for keyword in keywords):
        return True
    
    # Check for experience-based phrases
    experience_phrases = [
        "i learned", "i found", "i discovered", "i figured out",
        "what worked", "what didn't work", "avoid this", "instead of",
        "the key is", "the trick is", "the secret is", "my approach",
        "based on my experience", "from my experience", "in practice"
    ]
    
    return any(phrase in text_lower for phrase in experience_phrases)

def _extract_snippet(text: str, max_length: int) -> str:
    """Extract a clean snippet from HTML text"""
    # Remove HTML tags
    import re
    clean_text = re.sub(r'<[^>]+>', '', text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    # Return first max_length characters
    return clean_text[:max_length] + "..." if len(clean_text) > max_length else clean_text


# ---------- Hacker News Harvest ----------

def harvest_hackernews_posts(config) -> List[Dict[str, Any]]:
    """Harvest Hacker News posts and comments for tacit knowledge"""
    hn_cfg = _cfg(config, "hackernews", {}) or {}
    harvest_cfg = hn_cfg.get("harvest", {}) or {}
    
    print(f"🔍 Harvesting from Hacker News...")
    
    # Get top stories first
    top_stories = _get_hackernews_top_stories(harvest_cfg)
    
    # Get recent stories
    recent_stories = _get_hackernews_recent_stories(harvest_cfg)
    
    # Combine and filter for tacit knowledge
    all_stories = top_stories + recent_stories
    filtered_stories = _filter_hackernews_for_tacit_knowledge(all_stories, harvest_cfg)
    
    # Get comments for stories with tacit knowledge
    rows = []
    for story in filtered_stories:
        story_row = _create_hackernews_story_row(story)
        rows.append(story_row)
        
        # Get comments if enabled
        if harvest_cfg.get("include_comments", True):
            comments = _get_hackernews_comments(story.get("id"), harvest_cfg)
            for comment in comments:
                comment_row = _create_hackernews_comment_row(comment, story)
                rows.append(comment_row)
    
    print(f"   📰 Found {len(filtered_stories)} stories with tacit knowledge")
    print(f"   💬 Collected {len(rows) - len(filtered_stories)} comments")
    
    return rows

def _get_hackernews_top_stories(harvest_cfg: Dict) -> List[Dict]:
    """Get top stories from Hacker News"""
    stories = []
    max_items = harvest_cfg.get("max_items", 200)
    
    try:
        # Get top stories IDs
        response = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10)
        response.raise_for_status()
        story_ids = response.json()[:max_items//2]
        
        # Get story details
        for story_id in story_ids:
            try:
                story_response = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json", timeout=5)
                story_response.raise_for_status()
                story = story_response.json()
                
                if story and story.get("type") == "story":
                    stories.append(story)
                
                time.sleep(harvest_cfg.get("throttle_sec", 1.0))
                
            except Exception as e:
                print(f"     ❌ Error fetching story {story_id}: {e}")
                continue
    
    except Exception as e:
        print(f"   ❌ Error fetching top stories: {e}")
    
    return stories

def _get_hackernews_recent_stories(harvest_cfg: Dict) -> List[Dict]:
    """Get recent stories from Hacker News"""
    stories = []
    max_items = harvest_cfg.get("max_items", 200)
    
    try:
        # Get new stories IDs
        response = requests.get("https://hacker-news.firebaseio.com/v0/newstories.json", timeout=10)
        response.raise_for_status()
        story_ids = response.json()[:max_items//2]
        
        # Get story details
        for story_id in story_ids:
            try:
                story_response = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json", timeout=5)
                story_response.raise_for_status()
                story = story_response.json()
                
                if story and story.get("type") == "story":
                    stories.append(story)
                
                time.sleep(harvest_cfg.get("throttle_sec", 1.0))
                
            except Exception as e:
                print(f"     ❌ Error fetching story {story_id}: {e}")
                continue
    
    except Exception as e:
        print(f"   ❌ Error fetching recent stories: {e}")
    
    return stories

def _filter_hackernews_for_tacit_knowledge(stories: List[Dict], harvest_cfg: Dict) -> List[Dict]:
    """Filter stories for tacit knowledge content"""
    keywords = harvest_cfg.get("search_keywords", [])
    min_score = harvest_cfg.get("min_score", 10)
    time_range_days = harvest_cfg.get("time_range_days", 365)
    
    cutoff_time = datetime.now().timestamp() - (time_range_days * 24 * 60 * 60)
    filtered_stories = []
    
    for story in stories:
        # Check score
        if story.get("score", 0) < min_score:
            continue
        
        # Check time
        if story.get("time", 0) < cutoff_time:
            continue
        
        # Check title and text for tacit knowledge keywords
        title = story.get("title", "").lower()
        text = story.get("text", "").lower()
        url = story.get("url", "").lower()
        
        content = f"{title} {text} {url}"
        
        if any(keyword in content for keyword in keywords):
            filtered_stories.append(story)
    
    return filtered_stories

def _get_hackernews_comments(story_id: int, harvest_cfg: Dict) -> List[Dict]:
    """Get comments for a story"""
    comments = []
    
    try:
        # Get story details (includes kids/comment IDs)
        response = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json", timeout=5)
        response.raise_for_status()
        story = response.json()
        
        if not story or "kids" not in story:
            return comments
        
        # Get comment details
        for comment_id in story["kids"][:10]:  # Limit to top 10 comments
            try:
                comment_response = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{comment_id}.json", timeout=5)
                comment_response.raise_for_status()
                comment = comment_response.json()
                
                if comment and comment.get("type") == "comment":
                    # Check for tacit knowledge in comment
                    text = comment.get("text", "").lower()
                    keywords = harvest_cfg.get("search_keywords", [])
                    
                    if any(keyword in text for keyword in keywords):
                        comments.append(comment)
                
                time.sleep(harvest_cfg.get("throttle_sec", 1.0))
                
            except Exception as e:
                continue
    
    except Exception as e:
        print(f"     ❌ Error fetching comments for story {story_id}: {e}")
    
    return comments

def _create_hackernews_story_row(story: Dict) -> Dict[str, Any]:
    """Create a row for a Hacker News story"""
    return {
        "description": story.get("title", ""),
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
        "date": datetime.fromtimestamp(story.get("time", 0)).strftime("%Y-%m-%d"),
        "source_(interview_#/_name)": f"hackernews/{story.get('by', 'unknown')}",
        "link": story.get("url", f"https://news.ycombinator.com/item?id={story.get('id')}"),
        "notes": f"Score: {story.get('score', 0)}, Comments: {len(story.get('kids', []))}"
    }

def _create_hackernews_comment_row(comment: Dict, story: Dict) -> Dict[str, Any]:
    """Create a row for a Hacker News comment"""
    # Extract text from HTML comment
    import re
    text = comment.get("text", "")
    clean_text = re.sub(r'<[^>]+>', '', text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    return {
        "description": clean_text[:200] + "..." if len(clean_text) > 200 else clean_text,
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
        "date": datetime.fromtimestamp(comment.get("time", 0)).strftime("%Y-%m-%d"),
        "source_(interview_#/_name)": f"hackernews/comment/{comment.get('by', 'unknown')}",
        "link": f"https://news.ycombinator.com/item?id={comment.get('id')}",
        "notes": f"Comment on: {story.get('title', '')[:50]}..."
    }


# ---------- Substack Harvest ----------

def harvest_substack_newsletters(config) -> List[Dict[str, Any]]:
    """Harvest Substack newsletters for tacit knowledge"""
    substack_cfg = _cfg(config, "substack", {}) or {}
    harvest_cfg = substack_cfg.get("harvest", {}) or {}
    
    newsletters = substack_cfg.get("newsletters", [])
    
    if not newsletters:
        print("⚠️  No Substack newsletters configured")
        return []
    
    print(f"🔍 Harvesting from Substack...")
    print(f"   Newsletters: {newsletters}")
    
    rows = []
    
    for newsletter in newsletters:
        try:
            newsletter_rows = _harvest_substack_newsletter(newsletter, harvest_cfg)
            rows.extend(newsletter_rows)
            print(f"   📰 {newsletter}: {len(newsletter_rows)} articles")
        except Exception as e:
            print(f"   ❌ Error harvesting {newsletter}: {e}")
    
    return rows

def _harvest_substack_newsletter(newsletter: str, harvest_cfg: Dict) -> List[Dict[str, Any]]:
    """Harvest articles from a specific Substack newsletter"""
    rows = []
    
    # Try different RSS feed formats for Substack
    rss_urls = [
        f"https://{newsletter}.substack.com/feed",
        f"https://{newsletter}.substack.com/rss",
        f"https://{newsletter}.substack.com/feed.xml"
    ]
    
    max_articles = harvest_cfg.get("max_articles_per_newsletter", 30)
    keywords = harvest_cfg.get("search_keywords", [])
    
    for rss_url in rss_urls:
        try:
            print(f"     Trying RSS: {rss_url}")
            response = requests.get(rss_url, timeout=10)
            response.raise_for_status()
            
            # Parse RSS feed
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            
            count = 0
            
            for item in root.findall(".//item"):
                if count >= max_articles:
                    break
                    
                title = item.find("title")
                link = item.find("link")
                description = item.find("description")
                pub_date = item.find("pubDate")
                
                if title is not None and link is not None:
                    title_text = title.text or ""
                    link_text = link.text or ""
                    desc_text = description.text if description is not None else ""
                    date_text = pub_date.text if pub_date is not None else ""
                    
                    # Check if content contains tacit knowledge keywords
                    content = f"{title_text} {desc_text}".lower()
                    
                    if any(keyword in content for keyword in keywords):
                        row = {
                            "description": title_text,
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
                            "date": _parse_substack_date(date_text),
                            "source_(interview_#/_name)": f"substack/{newsletter}",
                            "link": link_text,
                            "notes": desc_text[:200] if desc_text else ""
                        }
                        rows.append(row)
                        count += 1
                        print(f"       ✅ Found: {title_text[:50]}...")
            
            if count > 0:
                break  # Found articles, no need to try other URLs
                
        except Exception as e:
            print(f"     ❌ Error with {rss_url}: {e}")
            continue
    
    return rows

def _parse_substack_date(date_str: str) -> str:
    """Parse Substack RSS date format to YYYY-MM-DD"""
    try:
        # Substack RSS dates are typically in RFC 822 format
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        return dt.strftime("%Y-%m-%d")
    except:
        return datetime.now().strftime("%Y-%m-%d")


# ---------- Quora Harvest ----------

def harvest_quora_questions(config) -> List[Dict[str, Any]]:
    """Harvest Quora questions and answers for tacit knowledge"""
    quora_cfg = _cfg(config, "quora", {}) or {}
    harvest_cfg = quora_cfg.get("harvest", {}) or {}
    
    topics = quora_cfg.get("topics", [])
    
    if not topics:
        print("⚠️  No Quora topics configured")
        return []
    
    print(f"🔍 Harvesting from Quora...")
    print(f"   Topics: {topics}")
    
    rows = []
    
    for topic in topics:
        try:
            topic_rows = _harvest_quora_topic(topic, harvest_cfg)
            rows.extend(topic_rows)
            print(f"   📚 {topic}: {len(topic_rows)} items")
        except Exception as e:
            print(f"   ❌ Error harvesting {topic}: {e}")
    
    return rows

def _harvest_quora_topic(topic: str, harvest_cfg: Dict) -> List[Dict[str, Any]]:
    """Harvest questions and answers from a Quora topic"""
    rows = []
    
    # Quora search URL
    search_url = f"https://www.quora.com/search?q={topic.replace(' ', '+')}&type=question"
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        
        print(f"     🔍 Searching topic: {topic}")
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Extract question links from search results
        # This is a simplified approach - in production you might want to use a proper HTML parser
        question_pattern = r'href="(/[^"]*)"[^>]*>([^<]*)</a>'
        matches = re.findall(question_pattern, response.text)
        
        max_questions = harvest_cfg.get("max_questions_per_topic", 50)
        count = 0
        
        for link, title in matches[:max_questions]:
            if count >= max_questions:
                break
                
            # Check if title contains tacit knowledge
            title_lower = title.lower()
            keywords = harvest_cfg.get("search_keywords", [])
            
            if any(keyword in title_lower for keyword in keywords):
                # Get full question URL
                question_url = f"https://www.quora.com{link}"
                
                row = {
                    "description": title,
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
                    "source_(interview_#/_name)": f"quora/{topic}",
                    "link": question_url,
                    "notes": f"Topic: {topic}"
                }
                rows.append(row)
                count += 1
                print(f"       ✅ Found question: {title[:50]}...")
        
        # Rate limiting
        time.sleep(harvest_cfg.get("throttle_sec", 3.0))
        
    except Exception as e:
        print(f"     ❌ Error searching topic '{topic}': {e}")
    
    return rows


# ---------- IndieHackers Harvest ----------

def harvest_indiehackers_posts(config) -> List[Dict[str, Any]]:
    """Harvest IndieHackers posts and comments for tacit knowledge"""
    ih_cfg = _cfg(config, "indiehackers", {}) or {}
    harvest_cfg = ih_cfg.get("harvest", {}) or {}
    
    categories = harvest_cfg.get("categories", [])
    
    if not categories:
        print("⚠️  No IndieHackers categories configured")
        return []
    
    print(f"🔍 Harvesting from IndieHackers...")
    print(f"   Categories: {categories}")
    
    rows = []
    
    for category in categories:
        try:
            category_rows = _harvest_indiehackers_category(category, harvest_cfg)
            rows.extend(category_rows)
            print(f"   📊 {category}: {len(category_rows)} posts")
        except Exception as e:
            print(f"   ❌ Error harvesting {category}: {e}")
    
    return rows

def _harvest_indiehackers_category(category: str, harvest_cfg: Dict) -> List[Dict[str, Any]]:
    """Harvest posts from a specific IndieHackers category"""
    rows = []
    
    # IndieHackers category URL
    category_url = f"https://www.indiehackers.com/category/{category}"
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        
        print(f"     🔍 Scanning category: {category}")
        response = requests.get(category_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Extract post links from the category page
        # This is a simplified approach - in production you might want to use a proper HTML parser
        post_pattern = r'href="(/post/[^"]*)"[^>]*>([^<]*)</a>'
        matches = re.findall(post_pattern, response.text)
        
        max_posts = harvest_cfg.get("max_posts_per_category", 50)
        keywords = harvest_cfg.get("search_keywords", [])
        min_score = harvest_cfg.get("min_score", 5)
        count = 0
        
        for link, title in matches[:max_posts]:
            if count >= max_posts:
                break
                
            # Check if title contains tacit knowledge
            title_lower = title.lower()
            
            if any(keyword in title_lower for keyword in keywords):
                # Get full post URL
                post_url = f"https://www.indiehackers.com{link}"
                
                # Try to get post details
                try:
                    post_response = requests.get(post_url, headers=headers, timeout=10)
                    post_response.raise_for_status()
                    
                    # Extract post content (simplified)
                    content_pattern = r'<div class="post-content">(.*?)</div>'
                    content_match = re.search(content_pattern, post_response.text, re.DOTALL)
                    
                    post_content = ""
                    if content_match:
                        # Clean HTML tags
                        post_content = re.sub(r'<[^>]+>', '', content_match.group(1))
                        post_content = re.sub(r'\s+', ' ', post_content).strip()
                    
                    # Extract score if available
                    score_pattern = r'class="score">(\d+)</span>'
                    score_match = re.search(score_pattern, post_response.text)
                    score = int(score_match.group(1)) if score_match else 0
                    
                    if score >= min_score:
                        row = {
                            "description": title,
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
                            "source_(interview_#/_name)": f"indiehackers/{category}",
                            "link": post_url,
                            "notes": f"Category: {category}, Score: {score}, Content: {post_content[:200]}..."
                        }
                        rows.append(row)
                        count += 1
                        print(f"       ✅ Found post: {title[:50]}... (Score: {score})")
                    
                    # Rate limiting
                    time.sleep(harvest_cfg.get("throttle_sec", 2.0))
                    
                except Exception as e:
                    print(f"       ❌ Error fetching post {post_url}: {e}")
                    continue
        
    except Exception as e:
        print(f"     ❌ Error scanning category '{category}': {e}")
    
    return rows


# ---------- Twitter Harvest ----------

def harvest_twitter_posts(config) -> List[Dict[str, Any]]:
    """Harvest Twitter posts for tacit knowledge"""
    twitter_cfg = _cfg(config, "twitter", {}) or {}
    harvest_cfg = twitter_cfg.get("harvest", {}) or {}
    
    # Get Twitter API credentials
    bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    if not bearer_token:
        print("⚠️  TWITTER_BEARER_TOKEN not set in environment variables")
        return []
    
    accounts = harvest_cfg.get("accounts_to_follow", [])
    
    if not accounts:
        print("⚠️  No Twitter accounts configured")
        return []
    
    print(f"🔍 Harvesting from Twitter...")
    print(f"   Accounts: {accounts}")
    
    rows = []
    
    for account in accounts:
        try:
            account_rows = _harvest_twitter_account(account, harvest_cfg, bearer_token)
            rows.extend(account_rows)
            print(f"   🐦 @{account}: {len(account_rows)} tweets")
        except Exception as e:
            print(f"   ❌ Error harvesting @{account}: {e}")
    
    return rows

def _harvest_twitter_account(account: str, harvest_cfg: Dict, bearer_token: str) -> List[Dict[str, Any]]:
    """Harvest tweets from a specific Twitter account"""
    rows = []
    
    # Twitter API v2 endpoint for user tweets
    url = f"https://api.twitter.com/2/users/by/username/{account}/tweets"
    
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json"
    }
    
    params = {
        "max_results": harvest_cfg.get("max_tweets_per_account", 100),
        "tweet.fields": "created_at,public_metrics,lang",
        "exclude": "retweets,replies" if not harvest_cfg.get("include_replies", False) else "retweets"
    }
    
    try:
        print(f"     🔍 Fetching tweets from @{account}")
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        tweets = data.get("data", [])
        
        keywords = harvest_cfg.get("search_keywords", [])
        min_likes = harvest_cfg.get("min_likes", 10)
        
        for tweet in tweets:
            # Check if tweet contains tacit knowledge
            text = tweet.get("text", "").lower()
            
            if any(keyword in text for keyword in keywords):
                # Check engagement metrics
                metrics = tweet.get("public_metrics", {})
                like_count = metrics.get("like_count", 0)
                
                if like_count >= min_likes:
                    row = {
                        "description": tweet.get("text", ""),
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
                        "date": tweet.get("created_at", "").split("T")[0] if tweet.get("created_at") else datetime.now().strftime("%Y-%m-%d"),
                        "source_(interview_#/_name)": f"twitter/{account}",
                        "link": f"https://twitter.com/{account}/status/{tweet.get('id')}",
                        "notes": f"Likes: {like_count}, Retweets: {metrics.get('retweet_count', 0)}"
                    }
                    rows.append(row)
                    print(f"       ✅ Found tweet: {tweet.get('text', '')[:50]}... (Likes: {like_count})")
        
        # Rate limiting
        time.sleep(harvest_cfg.get("throttle_sec", 3.0))
        
    except Exception as e:
        print(f"     ❌ Error fetching tweets from @{account}: {e}")
    
    return rows


# ---------- LinkedIn Harvest ----------

def harvest_linkedin_posts(config) -> List[Dict[str, Any]]:
    """Harvest LinkedIn posts for tacit knowledge"""
    linkedin_cfg = _cfg(config, "linkedin", {}) or {}
    harvest_cfg = linkedin_cfg.get("harvest", {}) or {}
    
    search_queries = harvest_cfg.get("search_queries", [])
    
    if not search_queries:
        print("⚠️  No LinkedIn search queries configured")
        return []
    
    print(f"🔍 Harvesting from LinkedIn...")
    print(f"   Search queries: {search_queries}")
    
    rows = []
    
    for query in search_queries:
        try:
            query_rows = _harvest_linkedin_search(query, harvest_cfg)
            rows.extend(query_rows)
            print(f"   💼 '{query}': {len(query_rows)} posts")
        except Exception as e:
            print(f"   ❌ Error searching '{query}': {e}")
    
    return rows

def _harvest_linkedin_search(query: str, harvest_cfg: Dict) -> List[Dict[str, Any]]:
    """Harvest LinkedIn posts using search"""
    rows = []
    
    # LinkedIn search URL
    search_url = f"https://www.linkedin.com/search/results/content/?keywords={query.replace(' ', '%20')}"
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        
        print(f"     🔍 Searching: {query}")
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Extract post content from search results
        # This is a simplified approach - LinkedIn may require authentication
        post_pattern = r'<div class="feed-shared-text"[^>]*>(.*?)</div>'
        matches = re.findall(post_pattern, response.text, re.DOTALL)
        
        max_posts = harvest_cfg.get("max_posts_per_query", 50)
        keywords = harvest_cfg.get("search_keywords", [])
        min_reactions = harvest_cfg.get("min_reactions", 5)
        count = 0
        
        for content in matches[:max_posts]:
            if count >= max_posts:
                break
                
            # Clean HTML tags
            clean_content = re.sub(r'<[^>]+>', '', content)
            clean_content = re.sub(r'\s+', ' ', clean_content).strip()
            
            # Check if content contains tacit knowledge
            content_lower = clean_content.lower()
            
            if any(keyword in content_lower for keyword in keywords):
                # Extract reactions if available
                reaction_pattern = r'(\d+)\s*(?:reactions?|likes?)'
                reaction_match = re.search(reaction_pattern, content)
                reactions = int(reaction_match.group(1)) if reaction_match else 0
                
                if reactions >= min_reactions:
                    row = {
                        "description": clean_content[:500] + "..." if len(clean_content) > 500 else clean_content,
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
                        "source_(interview_#/_name)": f"linkedin/search/{query}",
                        "link": search_url,
                        "notes": f"Query: {query}, Reactions: {reactions}"
                    }
                    rows.append(row)
                    count += 1
                    print(f"       ✅ Found post: {clean_content[:50]}... (Reactions: {reactions})")
        
        # Rate limiting
        time.sleep(harvest_cfg.get("throttle_sec", 3.0))
        
    except Exception as e:
        print(f"     ❌ Error searching LinkedIn for '{query}': {e}")
    
    return rows


# ---------- Internet Archive Harvest ----------

def harvest_internet_archive(config) -> List[Dict[str, Any]]:
    """Harvest content from Internet Archive (Wayback Machine)"""
    ia_cfg = _cfg(config, "internetarchive", {}) or {}
    harvest_cfg = ia_cfg.get("harvest", {}) or {}
    
    sources = harvest_cfg.get("sources", [])
    
    if not sources:
        print("⚠️  No Internet Archive sources configured")
        return []
    
    print(f"🔍 Harvesting from Internet Archive...")
    print(f"   Sources: {[s['name'] for s in sources]}")
    
    rows = []
    
    for source in sources:
        try:
            source_rows = _harvest_internet_archive_source(source, harvest_cfg)
            rows.extend(source_rows)
            print(f"   📚 {source['name']}: {len(source_rows)} articles")
        except Exception as e:
            print(f"   ❌ Error harvesting {source['name']}: {e}")
    
    return rows

def _harvest_internet_archive_source(source: Dict, harvest_cfg: Dict) -> List[Dict[str, Any]]:
    """Harvest content from a specific Internet Archive source using CDX API"""
    rows = []
    
    source_name = source.get("name", "Unknown")
    base_url = source.get("url", "")
    years = source.get("years", [])
    paths = source.get("paths", [])
    
    max_pages = harvest_cfg.get("max_pages_per_source", 50)
    min_length = harvest_cfg.get("min_content_length", 200)
    keywords = harvest_cfg.get("search_keywords", [])
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    
    print(f"     🔍 Scanning {source_name} ({base_url})")
    
    for year in years:
        for path in paths:
            try:
                # Use CDX API to get snapshots
                cdx_url = f"https://web.archive.org/cdx/search/cdx"
                params = {
                    "url": f"http://{base_url}{path}",
                    "matchType": "domain",
                    "collapse": "timestamp:8",
                    "output": "json",
                    "fl": "timestamp,original",
                    "filter": f"statuscode:200&timestamp:{year}00000000000000-{year}99999999999999"
                }
                
                print(f"       📅 {year} - {path}")
                response = requests.get(cdx_url, params=params, headers=headers, timeout=15)
                response.raise_for_status()
                
                # Parse CDX response
                data = response.json()
                if len(data) <= 1:  # Only header row
                    continue
                
                snapshots = data[1:]  # Skip header row
                count = 0
                
                for snapshot in snapshots[:max_pages]:
                    if count >= max_pages:
                        break
                    
                    try:
                        timestamp, original_url = snapshot
                        
                        # Construct Wayback Machine URL
                        wayback_url = f"https://web.archive.org/web/{timestamp}/{original_url}"
                        
                        snapshot_response = requests.get(wayback_url, headers=headers, timeout=10)
                        snapshot_response.raise_for_status()
                        
                        # Extract content from the archived page
                        content = _extract_content_from_archived_page(snapshot_response.text)
                        
                        if len(content) >= min_length:
                            # Check for tacit knowledge keywords
                            content_lower = content.lower()
                            
                            if any(keyword in content_lower for keyword in keywords):
                                # Format date from timestamp
                                formatted_date = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}"
                                
                                row = {
                                    "description": content[:500] + "..." if len(content) > 500 else content,
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
                                    "date": formatted_date,
                                    "source_(interview_#/_name)": f"internetarchive/{source_name}",
                                    "link": wayback_url,
                                    "notes": f"Source: {source_name}, Year: {year}, Path: {path}"
                                }
                                rows.append(row)
                                count += 1
                                print(f"         ✅ Found article: {content[:50]}...")
                        
                        # Rate limiting
                        time.sleep(harvest_cfg.get("throttle_sec", 2.0))
                        
                    except Exception as e:
                        print(f"         ❌ Error fetching snapshot: {e}")
                        continue
                
            except Exception as e:
                print(f"       ❌ Error scanning {year}/{path}: {e}")
                continue
    
    return rows

def _extract_content_from_archived_page(html_content: str) -> str:
    """Extract readable content from archived HTML page"""
    # Remove HTML tags
    clean_content = re.sub(r'<[^>]+>', ' ', html_content)
    
    # Remove extra whitespace
    clean_content = re.sub(r'\s+', ' ', clean_content)
    
    # Remove common Wayback Machine elements
    clean_content = re.sub(r'Wayback Machine', '', clean_content)
    clean_content = re.sub(r'Internet Archive', '', clean_content)
    
    # Extract text between common content markers
    content_patterns = [
        r'<body[^>]*>(.*?)</body>',
        r'<main[^>]*>(.*?)</main>',
        r'<article[^>]*>(.*?)</article>',
        r'<div class="content"[^>]*>(.*?)</div>',
        r'<div class="post"[^>]*>(.*?)</div>',
        r'<div class="article"[^>]*>(.*?)</div>'
    ]
    
    for pattern in content_patterns:
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        if match:
            content = re.sub(r'<[^>]+>', ' ', match.group(1))
            content = re.sub(r'\s+', ' ', content).strip()
            if len(content) > 100:
                return content
    
    # Fallback to cleaned HTML
    return clean_content.strip()


# ---------- Dev.to Harvest ----------

def harvest_devto_articles(config) -> List[Dict[str, Any]]:
    """Harvest Dev.to articles for project management and leadership insights"""
    devto_cfg = _cfg(config, "devto", {}) or {}
    harvest_cfg = devto_cfg.get("harvest", {}) or {}
    
    tags = harvest_cfg.get("tags", [])
    
    if not tags:
        print("⚠️  No Dev.to tags configured")
        return []
    
    print(f"🔍 Harvesting from Dev.to...")
    print(f"   Tags: {tags}")
    
    rows = []
    
    for tag in tags:
        try:
            tag_rows = _harvest_devto_tag(tag, harvest_cfg)
            rows.extend(tag_rows)
            print(f"   📝 '{tag}': {len(tag_rows)} articles")
        except Exception as e:
            print(f"   ❌ Error harvesting '{tag}': {e}")
    
    return rows

def _harvest_devto_tag(tag: str, harvest_cfg: Dict) -> List[Dict[str, Any]]:
    """Harvest Dev.to articles by tag"""
    rows = []
    
    max_articles = harvest_cfg.get("max_articles_per_tag", 50)
    min_reactions = harvest_cfg.get("min_reactions", 5)
    min_date = harvest_cfg.get("min_published_date", "2020-01-01")
    keywords = harvest_cfg.get("search_keywords", [])
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    
    print(f"     🔍 Scanning tag: {tag}")
    
    try:
        # Dev.to API endpoint for articles by tag
        api_url = f"https://dev.to/api/articles"
        params = {
            "tag": tag,
            "per_page": 100,
            "page": 1
        }
        
        response = requests.get(api_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        articles = response.json()
        count = 0
        
        for article in articles:
            if count >= max_articles:
                break
            
            try:
                # Check if article meets criteria
                published_at = article.get("published_at", "")
                if published_at and published_at < min_date:
                    continue
                
                reactions_count = article.get("public_reactions_count", 0)
                if reactions_count < min_reactions:
                    continue
                
                title = article.get("title", "")
                description = article.get("description", "")
                
                # Dev.to API doesn't return body_markdown in list view, need to fetch individual article
                article_id = article.get("id")
                body_markdown = ""
                
                if article_id:
                    try:
                        # Fetch full article content
                        article_url = f"https://dev.to/api/articles/{article_id}"
                        article_response = requests.get(article_url, headers=headers, timeout=10)
                        if article_response.status_code == 200:
                            article_data = article_response.json()
                            body_markdown = article_data.get("body_markdown", "")
                            time.sleep(0.5)  # Rate limiting for individual article requests
                    except Exception as e:
                        print(f"         ⚠️  Could not fetch full content for article {article_id}: {e}")
                
                # Combine content for keyword search
                content = f"{title} {description} {body_markdown}".lower()
                
                # Check if content contains project management keywords
                if any(keyword in content for keyword in keywords):
                    # Clean and extract content
                    clean_content = _extract_devto_content(body_markdown)
                    
                    if len(clean_content) > 200:  # Minimum content length
                        # Parse date
                        date_str = published_at[:10] if published_at else datetime.now().strftime("%Y-%m-%d")
                        
                        row = {
                            "description": clean_content[:500] + "..." if len(clean_content) > 500 else clean_content,
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
                            "date": date_str,
                            "source_(interview_#/_name)": f"devto/{tag}",
                            "link": article.get("url", ""),
                            "notes": f"Tag: {tag}, Reactions: {reactions_count}, Title: {title}"
                        }
                        rows.append(row)
                        count += 1
                        print(f"       ✅ Found article: {title[:50]}... (Reactions: {reactions_count})")
                
            except Exception as e:
                print(f"       ❌ Error processing article: {e}")
                continue
        
        # Rate limiting
        time.sleep(harvest_cfg.get("throttle_sec", 2.0))
        
    except Exception as e:
        print(f"     ❌ Error fetching Dev.to articles for '{tag}': {e}")
    
    return rows

def _extract_devto_content(markdown_content: str) -> str:
    """Extract readable content from Dev.to markdown"""
    # Remove markdown formatting
    content = re.sub(r'#+\s*', '', markdown_content)  # Remove headers
    content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)  # Remove bold
    content = re.sub(r'\*(.*?)\*', r'\1', content)  # Remove italic
    content = re.sub(r'`(.*?)`', r'\1', content)  # Remove inline code
    content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)  # Remove code blocks
    content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)  # Convert links to text
    content = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', content)  # Remove images
    
    # Clean up whitespace
    content = re.sub(r'\s+', ' ', content)
    content = content.strip()
    
    return content


# ---------- Product Hunt Harvest ----------

def harvest_producthunt_products(config) -> List[Dict[str, Any]]:
    """Harvest Product Hunt products for product development and management insights"""
    producthunt_cfg = _cfg(config, "producthunt", {}) or {}
    harvest_cfg = producthunt_cfg.get("harvest", {}) or {}
    
    categories = harvest_cfg.get("categories", [])
    
    if not categories:
        print("⚠️  No Product Hunt categories configured")
        return []
    
    print(f"🔍 Harvesting from Product Hunt...")
    print(f"   Categories: {categories}")
    
    rows = []
    
    for category in categories:
        try:
            category_rows = _harvest_producthunt_category(category, harvest_cfg)
            rows.extend(category_rows)
            print(f"   📝 '{category}': {len(category_rows)} products")
        except Exception as e:
            print(f"   ❌ Error harvesting '{category}': {e}")
    
    return rows

def _harvest_producthunt_category(category: str, harvest_cfg: Dict) -> List[Dict[str, Any]]:
    """Harvest Product Hunt products by category"""
    rows = []
    
    max_products = harvest_cfg.get("max_products_per_category", 50)
    min_votes = harvest_cfg.get("min_votes", 10)
    min_comments = harvest_cfg.get("min_comments", 2)
    keywords = harvest_cfg.get("search_keywords", [])
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    
    print(f"     🔍 Scanning category: {category}")
    
    try:
        # Product Hunt GraphQL API endpoint
        api_url = "https://api.producthunt.com/v2/api/graphql"
        
        # GraphQL query for products by category
        query = """
        query GetProductsByCategory($category: String!, $first: Int!) {
          posts(first: $first, topic: $category) {
            edges {
              node {
                id
                name
                tagline
                description
                votesCount
                commentsCount
                url
                createdAt
                makers {
                  name
                }
                topics {
                  name
                }
              }
            }
          }
        }
        """
        
        variables = {
            "category": category,
            "first": max_products
        }
        
        # Note: Product Hunt API requires authentication token
        # For now, we'll use web scraping as a fallback
        print(f"       ⚠️  Product Hunt API requires authentication. Using web scraping approach.")
        
        # Web scraping approach - scrape Product Hunt category pages
        category_url = f"https://www.producthunt.com/topics/{category.lower().replace(' ', '-')}"
        
        try:
            response = requests.get(category_url, headers=headers, timeout=10)
            if response.status_code == 200:
                # Parse the HTML to extract product information
                products = _parse_producthunt_html(response.text, category)
                
                count = 0
                for product in products:
                    if count >= max_products:
                        break
                    
                    try:
                        votes = product.get("votes", 0)
                        comments_count = product.get("comments_count", 0)
                        
                        if votes < min_votes or comments_count < min_comments:
                            continue
                        
                        name = product.get("name", "")
                        description = product.get("description", "")
                        tagline = product.get("tagline", "")
                        
                        # Combine content for keyword search
                        content = f"{name} {description} {tagline}".lower()
                        
                        # Check if content contains product development keywords
                        if any(keyword in content for keyword in keywords):
                            # Clean and extract content
                            clean_content = _extract_producthunt_content(description)
                            
                            if len(clean_content) > 100:  # Minimum content length
                                row = {
                                    "description": clean_content[:500] + "..." if len(clean_content) > 500 else clean_content,
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
                                    "source_(interview_#/_name)": f"producthunt/{category}",
                                    "link": product.get("url", ""),
                                    "notes": f"Category: {category}, Votes: {votes}, Comments: {comments_count}, Name: {name}"
                                }
                                rows.append(row)
                                count += 1
                                print(f"         ✅ Found product: {name[:50]}... (Votes: {votes}, Comments: {comments_count})")
                    
                    except Exception as e:
                        print(f"         ❌ Error processing product: {e}")
                        continue
            else:
                print(f"       ❌ Failed to fetch Product Hunt page: {response.status_code}")
                
        except Exception as e:
            print(f"       ❌ Error scraping Product Hunt: {e}")
        
        # Rate limiting
        time.sleep(harvest_cfg.get("throttle_sec", 2.0))
        
    except Exception as e:
        print(f"     ❌ Error fetching Product Hunt products for '{category}': {e}")
    
    return rows

def _parse_producthunt_html(html_content: str, category: str) -> List[Dict[str, Any]]:
    """Parse Product Hunt HTML to extract product information"""
    products = []
    
    try:
        # Look for product cards in the HTML
        # Product Hunt uses React, so we need to look for specific patterns
        
        # Pattern for product names
        name_pattern = r'<h3[^>]*>([^<]+)</h3>'
        names = re.findall(name_pattern, html_content)
        
        # Pattern for product descriptions/taglines
        desc_pattern = r'<p[^>]*class="[^"]*tagline[^"]*"[^>]*>([^<]+)</p>'
        descriptions = re.findall(desc_pattern, html_content)
        
        # Pattern for vote counts
        vote_pattern = r'(\d+)\s*votes?'
        votes = re.findall(vote_pattern, html_content)
        
        # Create product objects
        for i, name in enumerate(names[:10]):  # Limit to first 10 for testing
            product = {
                "name": name.strip(),
                "description": descriptions[i] if i < len(descriptions) else "",
                "tagline": descriptions[i] if i < len(descriptions) else "",
                "votes": int(votes[i]) if i < len(votes) else 0,
                "comments_count": 0,  # Hard to extract from HTML
                "url": f"https://www.producthunt.com/posts/{name.lower().replace(' ', '-')}"
            }
            products.append(product)
            
    except Exception as e:
        print(f"         ❌ Error parsing Product Hunt HTML: {e}")
    
    return products

def _extract_producthunt_content(content: str) -> str:
    """Extract readable content from Product Hunt product description"""
    # Clean up content
    content = re.sub(r'\s+', ' ', content)
    content = content.strip()
    
    return content


# ---------- Reddit Submission Harvest ----------

def harvest_submissions(config) -> List[Dict[str, Any]]:
    # Credentials from env or YAML
    client_id = os.getenv("REDDIT_CLIENT_ID") or _cfg(config, "reddit.client_id")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET") or _cfg(config, "reddit.client_secret")
    user_agent = os.getenv("REDDIT_USER_AGENT") or _cfg(config, "reddit.user_agent") or "wisdom-index/1.0"

    if not all([client_id, client_secret, user_agent]):
        raise RuntimeError("Missing Reddit credentials. Set in YAML under reddit.* or as env vars REDDIT_CLIENT_ID/SECRET/USER_AGENT.")

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
        check_for_async=False,
    )

    keywords = _cfg(config, "keywords", [])
    if not isinstance(keywords, list) or not keywords:
        raise RuntimeError("Config 'keywords' must be a non-empty list.")

    keywords_lower = [str(k).lower() for k in keywords]

    subs = _cfg(config, "reddit.subreddits") or ["all"]  # keep user's list; default "all"
    if isinstance(subs, str):
        subs = [subs]

    harvest_cfg = _cfg(config, "reddit.harvest", {}) or {}
    limit       = int(harvest_cfg.get("limit", 100))
    sort        = str(harvest_cfg.get("sort", "relevance"))
    time_filter = str(harvest_cfg.get("time_filter", "all"))
    min_post_score = int(harvest_cfg.get("min_post_score", 0))

    results: List[Dict[str, Any]] = []
    seen_ids = set()  # avoid duplicates

    print(f"→ Subreddits: {', '.join(subs)}")
    print(f"→ Keywords: {', '.join(keywords)}")
    print(f"→ Sort={sort}, Time={time_filter}, Limit={limit}")

    for kw in keywords:
        print(f"\n🔎 keyword: {kw}")
        for sub in subs:
            try:
                print(f"  • scanning r/{sub} …")
                sr = reddit.subreddit(sub)

                # Choose listing based on 'sort'
                if sort == "top":
                    candidates = sr.top(time_filter=time_filter, limit=limit)
                elif sort == "new":
                    candidates = sr.new(limit=limit)
                elif sort == "comments":
                    candidates = sr.comments(limit=limit)  # rare
                else:
                    # default to search by keyword
                    candidates = sr.search(kw, sort=sort, time_filter=time_filter, limit=limit)

                for submission in candidates:
                    # Skip if not a self-post title when search returns other types
                    try:
                        if hasattr(submission, "title") and len(submission.title or "") <= 5:
                            continue
                        if int(getattr(submission, "score", 0)) < min_post_score:
                            continue
                        if submission.id in seen_ids:
                            continue
                        seen_ids.add(submission.id)

                        # Build a row for the submission (title as description placeholder)
                        row = {k: "" for k in SCHEMA}
                        row.update({
                            "description": _safe(submission.title, 500),
                            "evidence_strength": "Anecdotal",
                            "type_(form)": "post",
                            "date": datetime.utcfromtimestamp(getattr(submission, "created_utc", 0)).date().isoformat() if getattr(submission, "created_utc", None) else _now_iso(),
                            "source_(interview_#/_name)": f"u/{getattr(getattr(submission, 'author', None), 'name', 'unknown')}",
                            "link": f"https://reddit.com{getattr(submission, 'permalink', '')}" if hasattr(submission, "permalink") else getattr(submission, "url", ""),
                            "notes": f"subreddit: r/{sub} | keyword: {kw}",
                        })
                        results.append(row)

                        # Also harvest comments per submission (filters in YAML)
                        results.extend(harvest_comments_for_submission(config, submission, keywords_lower))

                    except Exception as e:
                        # Keep scanning if one submission blows up
                        print(f"    ! skipping one submission: {e}")
                        continue

            except Exception as e:
                print(f"  ! Error scanning r/{sub}: {e}")
                continue

    return results


# ---------- Hashnode Harvest ----------

def harvest_hashnode_articles(config) -> List[Dict[str, Any]]:
    """Harvest Hashnode articles for tacit knowledge"""
    hashnode_cfg = _cfg(config, "hashnode", {}) or {}
    harvest_cfg = hashnode_cfg.get("harvest", {}) or {}
    
    tags = harvest_cfg.get("tags", [])
    search_keywords = harvest_cfg.get("search_keywords", [])
    
    if not tags:
        print("⚠️  No Hashnode tags configured")
        return []
    
    print(f"🔍 Harvesting from Hashnode...")
    print(f"   Tags: {tags}")
    
    rows = []
    
    for tag in tags:
        try:
            tag_rows = _harvest_hashnode_tag(tag, search_keywords, harvest_cfg)
            rows.extend(tag_rows)
            print(f"   📝 {tag}: {len(tag_rows)} articles")
            
            # Rate limiting between tags
            throttle_sec = harvest_cfg.get("throttle_sec", 3.0)
            print(f"     ⏳ Waiting {throttle_sec} seconds...")
            time.sleep(throttle_sec)
            
        except Exception as e:
            print(f"   ❌ Error harvesting {tag}: {e}")
    
    return rows

def _harvest_hashnode_tag(tag: str, search_keywords: List[str], harvest_cfg: Dict) -> List[Dict[str, Any]]:
    """Harvest articles from a specific Hashnode tag using web scraping"""
    rows = []
    
    max_retries = harvest_cfg.get("max_retries", 3)
    retry_delay = harvest_cfg.get("retry_delay", 8.0)
    max_articles = harvest_cfg.get("max_articles_per_tag", 20)
    min_reactions = harvest_cfg.get("min_reactions", 5)
    
    # Hashnode tag URL
    tag_url = f"https://hashnode.com/t/{tag}"
    
    # Try with retries
    for attempt in range(max_retries):
        try:
            print(f"     🔍 Scraping articles for tag '{tag}' (attempt {attempt + 1}/{max_retries})...")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            response = requests.get(tag_url, headers=headers, timeout=15)
            
            # Check for rate limiting
            if response.status_code == 429:
                print(f"       ⚠️  Rate limited (429). Waiting {retry_delay} seconds...")
                time.sleep(retry_delay)
                continue
            
            response.raise_for_status()
            
            # Extract article information from HTML
            # This is a simplified approach - in production you might want to use a proper HTML parser
            article_pattern = r'<h1[^>]*>([^<]+)</h1>.*?<p[^>]*>([^<]+)</p>'
            matches = re.findall(article_pattern, response.text, re.DOTALL)
            
            count = 0
            for title, description in matches[:max_articles]:
                if count >= max_articles:
                    break
                
                # Check if content contains tacit knowledge
                content = f"{title} {description}".lower()
                
                if _contains_tacit_knowledge(content, search_keywords):
                    row = {
                        "description": title,
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
                        "source_(interview_#/_name)": f"hashnode/{tag}",
                        "link": tag_url,
                        "notes": f"Tag: {tag}, Description: {description[:200]}"
                    }
                    rows.append(row)
                    count += 1
                    print(f"       ✅ Found article: {title[:50]}...")
            
            # Success, break out of retry loop
            break
            
        except requests.exceptions.RequestException as e:
            print(f"       ❌ Request error with tag '{tag}' (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                print(f"         ⏳ Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
            continue
        except Exception as e:
            print(f"       ❌ Error scraping articles for tag '{tag}' (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                print(f"         ⏳ Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
            continue
    
    return rows

def _parse_hashnode_date(date_str: str) -> str:
    """Parse Hashnode date format to YYYY-MM-DD"""
    try:
        if date_str:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d")
    except:
        pass
    return datetime.now().strftime("%Y-%m-%d")


# ---------- AngelList Harvest ----------

def harvest_angellist_data(config) -> List[Dict[str, Any]]:
    """Harvest AngelList data for tacit knowledge"""
    angellist_cfg = _cfg(config, "angellist", {}) or {}
    harvest_cfg = angellist_cfg.get("harvest", {}) or {}
    
    categories = harvest_cfg.get("categories", [])
    search_keywords = harvest_cfg.get("search_keywords", [])
    
    if not categories:
        print("⚠️  No AngelList categories configured")
        return []
    
    print(f"🔍 Harvesting from AngelList...")
    print(f"   Categories: {categories}")
    
    rows = []
    
    for category in categories:
        try:
            category_rows = _harvest_angellist_category(category, search_keywords, harvest_cfg)
            rows.extend(category_rows)
            print(f"   🏢 {category}: {len(category_rows)} items")
            
            # Rate limiting between categories
            throttle_sec = harvest_cfg.get("throttle_sec", 4.0)
            print(f"     ⏳ Waiting {throttle_sec} seconds...")
            time.sleep(throttle_sec)
            
        except Exception as e:
            print(f"   ❌ Error harvesting {category}: {e}")
    
    return rows

def _harvest_angellist_category(category: str, search_keywords: List[str], harvest_cfg: Dict) -> List[Dict[str, Any]]:
    """Harvest data from a specific AngelList category using web scraping"""
    rows = []
    
    max_retries = harvest_cfg.get("max_retries", 3)
    retry_delay = harvest_cfg.get("retry_delay", 10.0)
    max_items = harvest_cfg.get("max_items_per_category", 30)
    min_followers = harvest_cfg.get("min_followers", 100)
    
    # AngelList category URLs (using web scraping)
    if category == "startups":
        category_url = "https://angel.co/companies"
    elif category == "companies":
        category_url = "https://angel.co/companies"
    elif category == "jobs":
        category_url = "https://angel.co/jobs"
    elif category == "investors":
        category_url = "https://angel.co/investors"
    else:
        print(f"     ⚠️  Unknown category: {category}")
        return rows
    
    # Try with retries
    for attempt in range(max_retries):
        try:
            print(f"     🔍 Scraping {category} data (attempt {attempt + 1}/{max_retries})...")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            response = requests.get(category_url, headers=headers, timeout=15)
            
            # Check for rate limiting
            if response.status_code == 429:
                print(f"       ⚠️  Rate limited (429). Waiting {retry_delay} seconds...")
                time.sleep(retry_delay)
                continue
            
            response.raise_for_status()
            
            # Extract company/startup information from HTML
            # This is a simplified approach - in production you might want to use a proper HTML parser
            if category in ["startups", "companies"]:
                company_pattern = r'<h2[^>]*>([^<]+)</h2>.*?<p[^>]*>([^<]+)</p>'
                matches = re.findall(company_pattern, response.text, re.DOTALL)
            elif category == "jobs":
                job_pattern = r'<h3[^>]*>([^<]+)</h3>.*?<p[^>]*>([^<]+)</p>'
                matches = re.findall(job_pattern, response.text, re.DOTALL)
            elif category == "investors":
                investor_pattern = r'<h2[^>]*>([^<]+)</h2>.*?<p[^>]*>([^<]+)</p>'
                matches = re.findall(investor_pattern, response.text, re.DOTALL)
            else:
                matches = []
            
            count = 0
            for name, description in matches[:max_items]:
                if count >= max_items:
                    break
                
                # Check if content contains tacit knowledge
                content = f"{name} {description}".lower()
                
                if _contains_tacit_knowledge(content, search_keywords):
                    row = {
                        "description": name,
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
                        "source_(interview_#/_name)": f"angellist/{category}",
                        "link": category_url,
                        "notes": f"Category: {category}, Description: {description[:200]}"
                    }
                    rows.append(row)
                    count += 1
                    print(f"       ✅ Found {category} item: {name[:50]}...")
            
            # Success, break out of retry loop
            break
            
        except requests.exceptions.RequestException as e:
            print(f"       ❌ Request error with {category} (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                print(f"         ⏳ Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
            continue
        except Exception as e:
            print(f"       ❌ Error scraping {category} data (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                print(f"         ⏳ Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
            continue
    
    return rows


# ---------- Usenet Harvest ----------

def harvest_usenet_groups(config) -> List[Dict[str, Any]]:
    """Harvest from Usenet groups via Google Groups"""
    usenet_cfg = _cfg(config, "usenet", {}) or {}
    harvest_cfg = usenet_cfg.get("harvest", {}) or {}
    
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

# ---------- Podcast Harvest ----------

def harvest_podcast_transcripts(config) -> List[Dict[str, Any]]:
    """Harvest from podcast transcripts"""
    podcast_cfg = _cfg(config, "podcasts", {}) or {}
    harvest_cfg = podcast_cfg.get("harvest", {}) or {}
    
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
            import feedparser
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

# ---------- YouTube Harvest ----------

def harvest_youtube_business_podcasts(config) -> List[Dict[str, Any]]:
    """Harvest from YouTube business podcasts using YouTube Data API"""
    import os
    from googleapiclient.discovery import build
    
    youtube_cfg = _cfg(config, "youtube", {}) or {}
    harvest_cfg = youtube_cfg.get("harvest", {}) or {}
    
    # Check for API key
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        print("⚠️  No YouTube API key found. Set YOUTUBE_API_KEY environment variable.")
        print("   Get your API key from: https://console.cloud.google.com/apis/credentials")
        return []
    
    search_terms = harvest_cfg.get("search_terms", [])
    search_keywords = harvest_cfg.get("search_keywords", [])
    max_results_per_search = harvest_cfg.get("max_results_per_search", 20)
    max_videos_total = harvest_cfg.get("max_videos_total", 100)
    
    if not search_terms:
        print("⚠️  No YouTube search terms configured")
        return []
    
    print(f"🔍 Harvesting from YouTube business podcasts...")
    print(f"   Search terms: {len(search_terms)}")
    
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        all_videos = []
        all_insights = []
        
        for search_term in search_terms:
            try:
                print(f"     🔍 Searching: {search_term}")
                
                # Search for videos
                search_response = youtube.search().list(
                    q=search_term,
                    part='id,snippet',
                    maxResults=min(max_results_per_search, 50),
                    type='video',
                    videoDuration='medium',  # 4-20 minutes
                    publishedAfter='2020-01-01T00:00:00Z',
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
                print(f"       ✅ Found {len(videos)} videos")
                
                time.sleep(harvest_cfg.get("throttle_sec", 2.0))
                
            except HttpError as e:
                print(f"       ❌ Error searching for '{search_term}': {e}")
        
        print(f"📺 Processing {len(all_videos)} videos for insights...")
        
        # Limit total videos to process
        videos_to_process = all_videos[:max_videos_total]
        
        for video in videos_to_process:
            try:
                print(f"       🔍 Processing: {video['title'][:50]}...")
                
                # Get captions
                captions = _get_youtube_captions(youtube, video['video_id'])
                
                if captions:
                    # Extract insights
                    insights = _extract_insights_from_youtube_captions(captions, video, search_keywords)
                    all_insights.extend(insights)
                    
                    print(f"         ✅ Found {len(insights)} insights")
                else:
                    print(f"         ⚠️  No captions available")
                
                time.sleep(harvest_cfg.get("video_throttle_sec", 1.0))
                
            except Exception as e:
                print(f"         ❌ Error processing video: {e}")
        
        print(f"✅ YouTube processing complete! Found {len(all_insights)} insights")
        return all_insights
        
    except Exception as e:
        print(f"❌ YouTube API error: {e}")
        return []

def _get_youtube_captions(youtube, video_id: str) -> Optional[str]:
    """Get video captions/transcript"""
    try:
        # Check if captions are available
        captions_response = youtube.captions().list(
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
            caption_response = youtube.captions().download(
                id=target_caption['id'],
                tfmt='srt'  # SubRip format
            ).execute()
            
            # Parse SRT format to extract text
            caption_text = _parse_srt_captions(caption_response)
            return caption_text
        
        return None
        
    except HttpError as e:
        print(f"         ⚠️  Error getting captions for {video_id}: {e}")
        return None

def _parse_srt_captions(srt_content: bytes) -> str:
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
        print(f"         ⚠️  Error parsing captions: {e}")
        return ""

def _extract_insights_from_youtube_captions(captions: str, video_info: Dict[str, Any], 
                                          search_keywords: List[str]) -> List[Dict[str, Any]]:
    """Extract tacit knowledge insights from YouTube captions"""
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
                "source_(interview_#/_name)": f"youtube/{video_info['channel_title']}",
                "link": f"https://www.youtube.com/watch?v={video_info['video_id']}",
                "notes": f"Video: {video_info['title']}, Channel: {video_info['channel_title']}, Content: {sentence[:200]}"
            }
            insights.append(insight)
    
    return insights

# ---------- CSV Writer ----------

def write_csv(rows: List[Dict[str, Any]], out_path: str):
    # Ensure all rows have every column
    cleaned = []
    for r in rows:
        row = {k: r.get(k, "") for k in SCHEMA}
        cleaned.append(row)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SCHEMA)
        writer.writeheader()
        writer.writerows(cleaned)

    print(f"\n✅ Wrote {len(cleaned)} rows to {out_path}")


# ---------- Main ----------

def main():
    parser = argparse.ArgumentParser(description="Multi-platform harvester for Wisdom Index CSV.")
    parser.add_argument("--config", required=True, help="Path to YAML config (e.g., wi_config_unified.yaml)")
    parser.add_argument("--out", default="wisdom_index.csv", help="Output CSV path (default: wisdom_index.csv)")
    parser.add_argument("--check-duplicates", action="store_true", help="Check for duplicate searches before running")
    args = parser.parse_args()
    
    # Ensure data directory exists
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Update output path to use data directory
    if not args.out.startswith("data/"):
        args.out = str(data_dir / args.out)

    # Load YAML
    with open(args.config, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    # Check for duplicate searches
    if args.check_duplicates:
        search_log = load_search_log()
        current_config = {
            "platforms": _cfg(config, "sources", {}),
            "keywords": _cfg(config, "keywords", []),
        }
        
        for search in search_log["searches"]:
            if (search.get("platforms") == current_config["platforms"] and 
                search["keywords"] == current_config["keywords"]):
                print(f"⚠️  Similar search found from {search['timestamp']}")
                print(f"   Results: {search['results_count']} entries")
                response = input("Continue anyway? (y/N): ")
                if response.lower() != 'y':
                    print("Search cancelled.")
                    return

    # Harvest from all enabled platforms
    all_rows = []
    
    # Debug: Print what platforms are enabled
    print(f"🔧 Debug - Sources config: {_cfg(config, 'sources', {})}")
    print(f"🔧 Debug - Reddit enabled: {_cfg(config, 'sources.reddit', False)}")
    print(f"🔧 Debug - GitHub enabled: {_cfg(config, 'sources.github', False)}")
    
    # Reddit
    if _cfg(config, "sources.reddit", False):
        print("🔍 Harvesting from Reddit...")
        reddit_rows = harvest_submissions(config)
        all_rows.extend(reddit_rows)
        print(f"✅ Reddit: {len(reddit_rows)} items")
    
    # GitHub
    if _cfg(config, "sources.github", False):
        print("🔍 Harvesting from GitHub...")
        github_rows = harvest_github_issues(config)
        all_rows.extend(github_rows)
        print(f"✅ GitHub: {len(github_rows)} items")
    
    # Medium
    if _cfg(config, "sources.medium", False):
        print("🔍 Harvesting from Medium...")
        medium_rows = harvest_medium_articles(config)
        all_rows.extend(medium_rows)
        print(f"✅ Medium: {len(medium_rows)} items")
    
    # StackExchange
    if _cfg(config, "sources.stackexchange", False):
        print("🔍 Harvesting from StackExchange...")
        stackexchange_rows = harvest_stackexchange_questions(config)
        all_rows.extend(stackexchange_rows)
        print(f"✅ StackExchange: {len(stackexchange_rows)} items")
    
    # Hacker News
    if _cfg(config, "sources.hackernews", False):
        print("🔍 Harvesting from Hacker News...")
        hackernews_rows = harvest_hackernews_posts(config)
        all_rows.extend(hackernews_rows)
        print(f"✅ Hacker News: {len(hackernews_rows)} items")
    
    # Substack
    if _cfg(config, "sources.substack", False):
        print("🔍 Harvesting from Substack...")
        substack_rows = harvest_substack_newsletters(config)
        all_rows.extend(substack_rows)
        print(f"✅ Substack: {len(substack_rows)} items")
    
    # Quora
    if _cfg(config, "sources.quora", False):
        print("🔍 Harvesting from Quora...")
        quora_rows = harvest_quora_questions(config)
        all_rows.extend(quora_rows)
        print(f"✅ Quora: {len(quora_rows)} items")
    
    # IndieHackers
    if _cfg(config, "sources.indiehackers", False):
        print("🔍 Harvesting from IndieHackers...")
        indiehackers_rows = harvest_indiehackers_posts(config)
        all_rows.extend(indiehackers_rows)
        print(f"✅ IndieHackers: {len(indiehackers_rows)} items")
    
    # Twitter
    if _cfg(config, "sources.twitter", False):
        print("🔍 Harvesting from Twitter...")
        twitter_rows = harvest_twitter_posts(config)
        all_rows.extend(twitter_rows)
        print(f"✅ Twitter: {len(twitter_rows)} items")
    
    # LinkedIn
    if _cfg(config, "sources.linkedin", False):
        print("🔍 Harvesting from LinkedIn...")
        linkedin_rows = harvest_linkedin_posts(config)
        all_rows.extend(linkedin_rows)
        print(f"✅ LinkedIn: {len(linkedin_rows)} items")
    
    # Internet Archive
    if _cfg(config, "sources.internetarchive", False):
        print("🔍 Harvesting from Internet Archive...")
        internetarchive_rows = harvest_internet_archive(config)
        all_rows.extend(internetarchive_rows)
        print(f"✅ Internet Archive: {len(internetarchive_rows)} items")
    
    # Dev.to
    if _cfg(config, "sources.devto", False):
        print("🔍 Harvesting from Dev.to...")
        devto_rows = harvest_devto_articles(config)
        all_rows.extend(devto_rows)
        print(f"✅ Dev.to: {len(devto_rows)} items")
    
    # Product Hunt
    if _cfg(config, "sources.producthunt", False):
        print("🔍 Harvesting from Product Hunt...")
        producthunt_rows = harvest_producthunt_products(config)
        all_rows.extend(producthunt_rows)
        print(f"✅ Product Hunt: {len(producthunt_rows)} items")
    
    # Hashnode
    if _cfg(config, "sources.hashnode", False):
        print("🔍 Harvesting from Hashnode...")
        hashnode_rows = harvest_hashnode_articles(config)
        all_rows.extend(hashnode_rows)
        print(f"✅ Hashnode: {len(hashnode_rows)} items")
    
    # AngelList
    if _cfg(config, "sources.angellist", False):
        print("🔍 Harvesting from AngelList...")
        angellist_rows = harvest_angellist_data(config)
        all_rows.extend(angellist_rows)
        print(f"✅ AngelList: {len(angellist_rows)} items")
    
    # Usenet
    if _cfg(config, "sources.usenet", False):
        print("🔍 Harvesting from Usenet...")
        usenet_rows = harvest_usenet_groups(config)
        all_rows.extend(usenet_rows)
        print(f"✅ Usenet: {len(usenet_rows)} items")
    
    # Podcasts
    if _cfg(config, "sources.podcasts", False):
        print("🔍 Harvesting from Podcasts...")
        podcast_rows = harvest_podcast_transcripts(config)
        all_rows.extend(podcast_rows)
        print(f"✅ Podcasts: {len(podcast_rows)} items")
    
    # YouTube
    if _cfg(config, "sources.youtube", False):
        print("🔍 Harvesting from YouTube...")
        youtube_rows = harvest_youtube_business_podcasts(config)
        all_rows.extend(youtube_rows)
        print(f"✅ YouTube: {len(youtube_rows)} items")
    
    # Medium (placeholder for future implementation)
    if _cfg(config, "sources.medium", False):
        print("⚠️  Medium harvesting not yet implemented")
    
    write_csv(all_rows, args.out)
    
    # Log this search
    search_config = {
        "platforms": _cfg(config, "sources", {}),
        "keywords": _cfg(config, "keywords", []),
    }
    save_search_log(search_config, len(all_rows), _cfg(config, 'sources', {}))


if __name__ == "__main__":
    main()
