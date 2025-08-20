import praw
import os
from dotenv import load_dotenv
load_dotenv()

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

def scrape_reddit(keywords, limit=10):
    reddit = praw.Reddit(
        client_id='j57XdE4ULbFoSMIXh9X90A',
        client_secret='w-hTxLx16T_cj0HUsfrUTFDxAE3rfQ',
        user_agent='wisdom_index_agent'
    )

    results = []
    for keyword in keywords:
        for submission in reddit.subreddit("all").search(keyword, limit=limit):
            results.append({
                "site": "reddit",
                "keyword": keyword,
                "title": submission.title,
                "link": submission.url,
                "score": submission.score
            })
    return results
