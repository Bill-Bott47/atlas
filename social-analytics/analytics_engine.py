#!/usr/bin/env python3
"""Atlas Twitter Analytics - Engagement Intelligence."""

import os
import json
import sqlite3
import requests
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

DB_PATH = Path(__file__).parent / "twitter_analytics.db"

def init_db():
    """Create tables for engagement tracking."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS tweets (
            id TEXT PRIMARY KEY,
            client TEXT,
            tweet_id TEXT,
            text TEXT,
            created_at TEXT,
            hour_of_day INTEGER,
            day_of_week INTEGER,
            impressions INTEGER,
            engagements INTEGER,
            likes INTEGER,
            retweets INTEGER,
            replies INTEGER,
            quotes INTEGER,
            engagement_rate REAL,
            media_type TEXT,
            has_mention INTEGER,
            has_hashtag INTEGER,
            is_reply INTEGER
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_followers (
            date TEXT,
            client TEXT,
            follower_count INTEGER,
            PRIMARY KEY (date, client)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS mentions (
            id TEXT PRIMARY KEY,
            client TEXT,
            mentioner TEXT,
            tweet_id TEXT,
            text TEXT,
            sentiment TEXT,
            created_at TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def get_user_metrics(username):
    """Get user metrics including follower count."""
    from twitter_api import get_user_metrics as rapidapi_get_user_metrics
    return rapidapi_get_user_metrics(username)

def get_tweets_with_metrics(user_id, max_results=100):
    """Get tweets with full engagement metrics."""
    from twitter_api import get_recent_tweets
    return get_recent_tweets(user_id, max_results)

def analyze_posting_time(tweets):
    """Find optimal posting times."""
    hourly_engagement = defaultdict(lambda: {"total": 0, "count": 0})
    
    for tweet in tweets:
        # Parse Twitter date format: 'Tue Mar 10 23:37:57 +0000 2026'
        try:
            created = datetime.strptime(tweet["created_at"], "%a %b %d %H:%M:%S +0000 %Y")
        except:
            continue
        hour = created.hour
        
        metrics = tweet.get("public_metrics", {})
        engagement = sum([
            metrics.get("like_count", 0),
            metrics.get("retweet_count", 0),
            metrics.get("reply_count", 0),
            metrics.get("quote_count", 0)
        ])
        
        hourly_engagement[hour]["total"] += engagement
        hourly_engagement[hour]["count"] += 1
    
    # Calculate average engagement per hour
    best_times = []
    for hour, data in hourly_engagement.items():
        if data["count"] > 0:
            avg = data["total"] / data["count"]
            best_times.append((hour, avg))
    
    best_times.sort(key=lambda x: x[1], reverse=True)
    return best_times[:3]  # Top 3 hours

def get_best_worst_tweets(tweets, n=3):
    """Get highest and lowest performing tweets."""
    scored_tweets = []
    
    for tweet in tweets:
        metrics = tweet.get("public_metrics", {})
        non_public = tweet.get("non_public_metrics", {})
        
        impressions = non_public.get("impression_count") or 0
        engagements = sum([
            metrics.get("like_count", 0),
            metrics.get("retweet_count", 0),
            metrics.get("reply_count", 0),
            metrics.get("quote_count", 0)
        ])
        
        rate = (engagements / impressions * 100) if impressions > 0 else 0
        
        scored_tweets.append({
            "id": tweet["id"],
            "text": tweet["text"][:100] + "..." if len(tweet["text"]) > 100 else tweet["text"],
            "engagement_rate": rate,
            "impressions": impressions,
            "engagements": engagements,
            "created_at": tweet["created_at"]
        })
    
    scored_tweets.sort(key=lambda x: x["engagement_rate"], reverse=True)
    
    return {
        "best": scored_tweets[:n],
        "worst": scored_tweets[-n:] if len(scored_tweets) >= n else scored_tweets
    }

def analyze_tweet_types(tweets):
    """Analyze which tweet types perform best."""
    type_performance = defaultdict(lambda: {"total_rate": 0, "count": 0})
    
    for tweet in tweets:
        metrics = tweet.get("public_metrics", {})
        non_public = tweet.get("non_public_metrics", {})
        entities = tweet.get("entities", {})
        
        impressions = non_public.get("impression_count") or 0
        engagements = sum([
            metrics.get("like_count", 0),
            metrics.get("retweet_count", 0),
            metrics.get("reply_count", 0),
            metrics.get("quote_count", 0)
        ])
        
        rate = (engagements / impressions * 100) if impressions > 0 else 0
        
        # Categorize tweet type
        has_media = "urls" in entities or "media" in entities
        has_mention = "mentions" in entities
        has_hashtag = "hashtags" in entities
        is_reply = tweet.get("referenced_tweets") and any(
            ref["type"] == "replied_to" for ref in tweet["referenced_tweets"]
        )
        
        if is_reply:
            tweet_type = "Reply"
        elif has_media:
            tweet_type = "Media"
        elif has_hashtag:
            tweet_type = "Hashtag"
        elif has_mention:
            tweet_type = "Mention"
        else:
            tweet_type = "Text"
        
        type_performance[tweet_type]["total_rate"] += rate
        type_performance[tweet_type]["count"] += 1
    
    # Calculate averages
    results = []
    for tweet_type, data in type_performance.items():
        if data["count"] > 0:
            avg_rate = data["total_rate"] / data["count"]
            results.append((tweet_type, avg_rate, data["count"]))
    
    results.sort(key=lambda x: x[1], reverse=True)
    return results

def get_follower_growth(client, user_id, days=14):
    """Calculate follower growth over time."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    try:
        days_int = int(days)
    except (TypeError, ValueError):
        days_int = 14
    days_int = max(days_int, 0)
    
    # Get current followers
    current = get_user_metrics_from_db(client)
    
    # Get historical
    c.execute('''
        SELECT date, follower_count FROM daily_followers
        WHERE client = ? AND date >= date('now', ?)
        ORDER BY date ASC
    ''', (client, f"-{days_int} days"))
    
    history = c.fetchall()
    conn.close()
    
    if len(history) >= 2:
        growth = history[-1][1] - history[0][1]
        growth_pct = (growth / history[0][1] * 100) if history[0][1] > 0 else 0
        return {
            "current": history[-1][1],
            "growth": growth,
            "growth_pct": growth_pct,
            "trend": "up" if growth > 0 else "down" if growth < 0 else "flat"
        }
    
    return {"current": current, "growth": 0, "growth_pct": 0, "trend": "unknown"}

def get_user_metrics_from_db(client):
    """Get latest follower count from DB."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT follower_count FROM daily_followers
        WHERE client = ? ORDER BY date DESC LIMIT 1
    ''', (client,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def generate_actionable_insights(tweets, best_times, tweet_types):
    """Generate actionable recommendations."""
    insights = []
    
    # Best time insight
    if best_times:
        best_hour = best_times[0][0]
        am_pm = "AM" if best_hour < 12 else "PM"
        display_hour = 12 if best_hour % 12 == 0 else best_hour % 12
        insights.append(f"Post at {display_hour} {am_pm} for highest engagement")
    
    # Tweet type insight
    if tweet_types:
        best_type = tweet_types[0][0]
        worst_type = tweet_types[-1][0] if len(tweet_types) > 1 else None
        insights.append(f"Post more {best_type} tweets — they perform {tweet_types[0][1]:.1f}% engagement")
        if worst_type and worst_type != best_type:
            insights.append(f"Post fewer {worst_type} tweets — they only get {tweet_types[-1][1]:.1f}% engagement")
    
    return insights
