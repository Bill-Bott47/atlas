#!/usr/bin/env python3
"""Atlas Twitter Analytics - Engagement per tweet tracker."""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Phoenix clients to track
CLIENTS = {
    "Pharaoh": "PharaohDEX",
    "Benqi": "BenqiFinance", 
    "MagicEden": "MagicEden"
}

DB_PATH = Path(__file__).parent / "twitter_analytics.db"

def init_db():
    """Create SQLite tables for tweet engagement tracking."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS tweets (
            id TEXT PRIMARY KEY,
            client TEXT,
            tweet_id TEXT,
            text TEXT,
            created_at TEXT,
            collected_at TEXT,
            impressions INTEGER,
            engagements INTEGER,
            likes INTEGER,
            retweets INTEGER,
            replies INTEGER,
            quotes INTEGER
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_stats (
            date TEXT,
            client TEXT,
            tweet_count INTEGER,
            total_impressions INTEGER,
            total_engagements INTEGER,
            avg_engagement_rate REAL,
            PRIMARY KEY (date, client)
        )
    ''')
    
    conn.commit()
    conn.close()

def collect_tweets(client_name, username):
    """Collect recent tweets with engagement metrics."""
    # TODO: Implement Twitter API v2 call
    # For now, return placeholder structure
    return []

def calculate_engagement_rate(impressions, engagements):
    """Calculate engagement rate as percentage."""
    if impressions == 0:
        return 0.0
    return (engagements / impressions) * 100

def get_week_over_week(client, metric="avg_engagement_rate"):
    """Compare this week vs last week."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    two_weeks_ago = today - timedelta(days=14)
    
    # This week
    c.execute('''
        SELECT AVG({}) FROM daily_stats 
        WHERE client = ? AND date >= ? AND date <= ?
    '''.format(metric), (client, week_ago, today))
    this_week = c.fetchone()[0] or 0
    
    # Last week
    c.execute('''
        SELECT AVG({}) FROM daily_stats 
        WHERE client = ? AND date >= ? AND date <= ?
    '''.format(metric), (client, two_weeks_ago, week_ago))
    last_week = c.fetchone()[0] or 0
    
    conn.close()
    
    if last_week == 0:
        return 0.0
    return ((this_week - last_week) / last_week) * 100

if __name__ == "__main__":
    init_db()
    print("Atlas Twitter Analytics initialized")
    print(f"Database: {DB_PATH}")
    print(f"Tracking {len(CLIENTS)} clients")
