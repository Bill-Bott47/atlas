#!/usr/bin/env python3
"""Atlas Twitter Analytics - Main Runner."""

import os
import sys
from datetime import datetime
from analytics_engine import (
    init_db, get_user_metrics, get_tweets_with_metrics,
    analyze_posting_time, get_best_worst_tweets, analyze_tweet_types,
    get_follower_growth, generate_actionable_insights
)
from sentiment import analyze_mentions, generate_sentiment_insights
from notion_client import create_client_report, create_weekly_summary

# Phoenix clients
CLIENTS = {
    "Pharaoh": "PharaohDEX",
    "Benqi": "BenqiFinance",
    "MagicEden": "MagicEden"
}

def collect_client_data(client_name, username):
    """Collect all data for a client."""
    print(f"\n📊 Analyzing {client_name} (@{username})...")
    
    # Get user metrics
    user = get_user_metrics(username)
    if not user:
        print(f"  ❌ Failed to get user data")
        return None
    
    print(f"  Followers: {user['followers']:,}")
    
    # Get tweets
    tweets = get_tweets_with_metrics(user["id"], max_results=100)
    print(f"  Tweets analyzed: {len(tweets)}")
    
    if not tweets:
        return None
    
    # Analyze
    best_times = analyze_posting_time(tweets)
    best_worst = get_best_worst_tweets(tweets, n=3)
    tweet_types = analyze_tweet_types(tweets)
    follower_growth = get_follower_growth(client_name, user["id"])
    insights = generate_actionable_insights(tweets, best_times, tweet_types)
    
    return {
        "client": client_name,
        "username": username,
        "followers": user["followers"],
        "follower_growth": follower_growth,
        "tweet_count": len(tweets),
        "best_times": best_times,
        "best_tweets": best_worst["best"],
        "worst_tweets": best_worst["worst"],
        "tweet_types": tweet_types,
        "insights": insights
    }

def print_report(data):
    """Print formatted report to console."""
    print(f"\n{'='*60}")
    print(f"📈 {data['client']} (@{data['username']})")
    print(f"{'='*60}")
    
    # Followers
    fg = data["follower_growth"]
    trend_emoji = "📈" if fg["trend"] == "up" else "📉" if fg["trend"] == "down" else "➡️"
    print(f"\n{trend_emoji} Followers: {fg['current']:,} ({fg['growth']:+d}, {fg['growth_pct']:+.1f}%)")
    
    # Best posting times
    print(f"\n🕐 Best Posting Times:")
    for hour, avg_engagement in data["best_times"][:3]:
        am_pm = "AM" if hour < 12 else "PM"
        display = hour if hour <= 12 else hour - 12
        if display == 0:
            display = 12
        print(f"   {display} {am_pm}: {avg_engagement:.1f} avg engagement")
    
    # Tweet types
    print(f"\n📝 Tweet Type Performance:")
    for tweet_type, rate, count in data["tweet_types"][:5]:
        print(f"   {tweet_type}: {rate:.2f}% engagement ({count} tweets)")
    
    # Best tweets
    print(f"\n🔥 Top Performing Tweets:")
    for i, tweet in enumerate(data["best_tweets"][:3], 1):
        print(f"   {i}. {tweet['engagement_rate']:.2f}% | {tweet['text'][:60]}...")
    
    # Sentiment Analysis
    if "sentiment" in data:
        print(f"\n😊 Sentiment Analysis:")
        sb = data["sentiment"]["sentiment_breakdown"]
        total = sum(sb.values())
        if total > 0:
            print(f"   Positive: {sb.get('positive', 0)} ({sb.get('positive', 0)/total*100:.0f}%)")
            print(f"   Neutral: {sb.get('neutral', 0)} ({sb.get('neutral', 0)/total*100:.0f}%)")
            print(f"   Negative: {sb.get('negative', 0)} ({sb.get('negative', 0)/total*100:.0f}%)")
        
        if data["sentiment"]["top_engagers"]:
            print(f"\n👥 Top Engagers:")
            for user, count in data["sentiment"]["top_engagers"][:5]:
                print(f"   @{user}: {count} mentions")
    
    # Insights
    print(f"\n💡 Actionable Insights:")
    for insight in data["insights"]:
        print(f"   • {insight}")
    if "sentiment_insights" in data:
        for insight in data["sentiment_insights"]:
            print(f"   • {insight}")

def main():
    """Run full analytics for all clients."""
    print("="*60)
    print("🚀 Atlas Twitter Analytics")
    print("="*60)
    
    # Check env
    if not os.getenv("RAPIDAPI_KEY"):
        print("❌ ERROR: RAPIDAPI_KEY not set")
        sys.exit(1)
    
    init_db()
    
    all_data = []
    
    for client_name, username in CLIENTS.items():
        data = collect_client_data(client_name, username)
        if data:
            print_report(data)
            all_data.append(data)
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 SUMMARY")
    print(f"{'='*60}")
    
    for data in all_data:
        fg = data["follower_growth"]
        print(f"{data['client']}: {fg['current']:,} followers ({fg['growth_pct']:+.1f}%)")
    
    print(f"\n✅ Analysis complete. {len(all_data)} clients analyzed.")
    
    # Notion export (if configured)
    if os.getenv("NOTION_PARENT_PAGE_ID") and os.getenv("NOTION_API_KEY"):
        print("\n📝 Exporting to Notion...")
        try:
            for data in all_data:
                result = create_client_report(
                    client_name=data["client"],
                    twitter_data=data,
                    research_data=None  # TODO: Add Atlas research integration
                )
                if result.get("id"):
                    print(f"   ✅ {data['client']} report created")
                else:
                    print(f"   ❌ {data['client']} failed: {result.get('message', 'Unknown error')}")
            
            # Create weekly summary
            summary = create_weekly_summary(all_data)
            if summary.get("id"):
                print("   ✅ Weekly summary created")
            
        except Exception as e:
            print(f"   ❌ Notion export failed: {e}")
    else:
        print("\n⚠️  Notion not configured (set NOTION_PARENT_PAGE_ID and NOTION_API_KEY)")

if __name__ == "__main__":
    main()
