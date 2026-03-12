"""Twitter API client via RapidAPI for Atlas."""

import os
import requests
from datetime import datetime

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = "twitter-api45.p.rapidapi.com"
BASE_URL = f"https://{RAPIDAPI_HOST}"


def get_headers():
    """Build request headers with a validated RapidAPI key."""
    key = os.getenv("RAPIDAPI_KEY")
    if not key:
        raise ValueError("RAPIDAPI_KEY not set")
    return {
        "X-RapidAPI-Key": key,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }

def get_user_id(username):
    """Get Twitter user ID from username."""
    url = f"{BASE_URL}/screenname.php"
    params = {"screenname": username}
    
    response = requests.get(url, headers=get_headers(), params=params)
    if response.status_code == 200:
        data = response.json()
        if "rest_id" in data:
            return data["rest_id"]
    return None

def get_user_metrics(username):
    """Get user metrics including follower count."""
    url = f"{BASE_URL}/screenname.php"
    params = {"screenname": username}
    
    response = requests.get(url, headers=get_headers(), params=params)
    if response.status_code == 200:
        data = response.json()
        # RapidAPI returns different format
        followers = data.get("sub_count", 0) or data.get("legacy", {}).get("followers_count", 0)
        following = data.get("friends", 0) or data.get("legacy", {}).get("friends_count", 0)
        tweets = data.get("statuses_count", 0) or data.get("legacy", {}).get("statuses_count", 0)
        return {
            "id": data.get("rest_id"),
            "followers": followers,
            "following": following,
            "tweets": tweets
        }
    return None

def get_recent_tweets(screenname, max_results=100):
    """Get recent tweets with engagement metrics."""
    url = f"{BASE_URL}/timeline.php"
    params = {
        "screenname": screenname,
        "count": min(max_results, 100)
    }
    
    response = requests.get(url, headers=get_headers(), params=params)
    if response.status_code == 200:
        data = response.json()
        tweets = []
        
        # Parse timeline tweets
        for tweet in data.get("timeline", []):
            try:
                # Parse views (can be int or string)
                views = tweet.get("views", 0)
                if isinstance(views, str):
                    views = int(views.replace(",", ""))
                
                parsed = {
                    "id": str(tweet.get("tweet_id")),
                    "text": tweet.get("text", ""),
                    "created_at": tweet.get("created_at"),
                    "public_metrics": {
                        "like_count": tweet.get("favorites", 0),
                        "retweet_count": tweet.get("retweets", 0),
                        "reply_count": tweet.get("replies", 0),
                        "quote_count": tweet.get("quotes", 0)
                    },
                    "non_public_metrics": {
                        "impression_count": views
                    }
                }
                tweets.append(parsed)
            except Exception as e:
                tweet_id = tweet.get("tweet_id", "unknown")
                print(f"⚠️ Failed to parse tweet {tweet_id}: {e}")
                continue
        return tweets
    return []

def parse_metrics(tweet):
    """Extract metrics from tweet data."""
    metrics = tweet.get("public_metrics", {})
    non_public = tweet.get("non_public_metrics", {})
    
    return {
        "tweet_id": tweet["id"],
        "text": tweet["text"][:280],
        "created_at": tweet["created_at"],
        "impressions": non_public.get("impression_count", 0),
        "likes": metrics.get("like_count", 0),
        "retweets": metrics.get("retweet_count", 0),
        "replies": metrics.get("reply_count", 0),
        "quotes": metrics.get("quote_count", 0),
        "engagements": (
            metrics.get("like_count", 0) +
            metrics.get("retweet_count", 0) +
            metrics.get("reply_count", 0) +
            metrics.get("quote_count", 0)
        )
    }
