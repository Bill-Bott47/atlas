#!/usr/bin/env python3
"""Atlas Twitter Analytics - Main runner."""

import os
import sys
from datetime import datetime
from twitter_tracker import init_db, CLIENTS
from twitter_api import get_user_id, get_recent_tweets, parse_metrics
from notion_output import create_report_page
import sqlite3
from pathlib import Path

def collect_all_clients():
    """Collect tweet data for all clients."""
    DB_PATH = Path(__file__).parent / "twitter_analytics.db"
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    collected = 0
    
    for client_name, username in CLIENTS.items():
        print(f"Collecting: {client_name} (@{username})")
        
        user_id = get_user_id(username)
        if not user_id:
            print(f"  Failed to get user ID for {username}")
            continue
        
        tweets = get_recent_tweets(user_id)
        
        for tweet in tweets:
            metrics = parse_metrics(tweet)
            
            try:
                c.execute('''
                    INSERT OR REPLACE INTO tweets 
                    (id, client, tweet_id, text, created_at, collected_at,
                     impressions, engagements, likes, retweets, replies, quotes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    f"{client_name}_{tweet['id']}",
                    client_name,
                    tweet['id'],
                    metrics['text'],
                    metrics['created_at'],
                    datetime.now().isoformat(),
                    metrics['impressions'],
                    metrics['engagements'],
                    metrics['likes'],
                    metrics['retweets'],
                    metrics['replies'],
                    metrics['quotes']
                ))
                collected += 1
            except Exception as e:
                print(f"  Error storing tweet: {e}")
        
        print(f"  Collected {len(tweets)} tweets")
    
    conn.commit()
    conn.close()
    
    return collected

def generate_daily_stats():
    """Aggregate daily statistics."""
    DB_PATH = Path(__file__).parent / "twitter_analytics.db"
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    today = datetime.now().date().isoformat()
    
    for client in CLIENTS.keys():
        c.execute('''
            SELECT 
                COUNT(*),
                SUM(impressions),
                SUM(engagements),
                AVG(CASE WHEN impressions > 0 THEN (engagements * 100.0 / impressions) ELSE 0 END)
            FROM tweets
            WHERE client = ? AND date(created_at) = ?
        ''', (client, today))
        
        result = c.fetchone()
        
        c.execute('''
            INSERT OR REPLACE INTO daily_stats
            (date, client, tweet_count, total_impressions, total_engagements, avg_engagement_rate)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (today, client, result[0] or 0, result[1] or 0, result[2] or 0, result[3] or 0))
    
    conn.commit()
    conn.close()

def get_weekly_summary():
    """Get week-over-week summary for all clients."""
    from twitter_tracker import get_week_over_week
    
    summary = {}
    for client in CLIENTS.keys():
        change = get_week_over_week(client)
        summary[client] = {
            "change": change
        }
    
    return summary

def main():
    """Run full analytics pipeline."""
    print("=" * 50)
    print("Atlas Twitter Analytics")
    print("=" * 50)
    
    # Check for required env vars
    if not os.getenv("TWITTER_BEARER_TOKEN"):
        print("ERROR: TWITTER_BEARER_TOKEN not set")
        sys.exit(1)
    
    # Initialize
    init_db()
    
    # Collect data
    print("\n[1/3] Collecting tweet data...")
    collected = collect_all_clients()
    print(f"Total tweets collected: {collected}")
    
    # Generate stats
    print("\n[2/3] Generating daily stats...")
    generate_daily_stats()
    
    # Summary
    print("\n[3/3] Week-over-week summary:")
    summary = get_weekly_summary()
    for client, stats in summary.items():
        print(f"  {client}: {stats['change']:+.1f}% engagement rate change")
    
    print("\nDone.")

if __name__ == "__main__":
    main()
