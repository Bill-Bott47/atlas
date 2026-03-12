"""Sentiment analysis for Twitter mentions and replies."""

import re
from collections import Counter

# Simple sentiment lexicon (can be expanded or use external API)
POSITIVE_WORDS = {
    'good', 'great', 'excellent', 'amazing', 'awesome', 'love', 'best', 'fantastic',
    'wonderful', 'perfect', 'brilliant', 'outstanding', 'superb', 'incredible',
    'thank', 'thanks', 'appreciate', 'helpful', 'useful', 'impressive', 'solid',
    'bullish', 'moon', 'pump', 'gain', 'profit', 'win', 'winner', 'success',
    'congrats', 'congratulations', 'celebrate', 'excited', 'happy', 'pleased'
}

NEGATIVE_WORDS = {
    'bad', 'terrible', 'awful', 'hate', 'worst', 'horrible', 'disappointing',
    'poor', 'useless', 'broken', 'bug', 'scam', 'rug', 'dump', 'crash',
    'lose', 'loss', 'fail', 'failure', 'sad', 'angry', 'frustrated', 'annoyed',
    'unhappy', 'disappointed', 'concerned', 'worried', 'problem', 'issue'
}

def analyze_sentiment(text):
    """Analyze sentiment of a tweet/reply."""
    text_lower = text.lower()
    
    # Remove URLs, mentions, hashtags for cleaner analysis
    clean_text = re.sub(r'http\S+|@\w+|#\w+', '', text_lower)
    words = set(clean_text.split())
    
    positive_count = len(words & POSITIVE_WORDS)
    negative_count = len(words & NEGATIVE_WORDS)
    
    if positive_count > negative_count:
        return "positive", positive_count - negative_count
    elif negative_count > positive_count:
        return "negative", negative_count - positive_count
    else:
        return "neutral", 0

def analyze_mentions(mentions, client_username):
    """Analyze sentiment of mentions and identify key engagers."""
    sentiment_counts = Counter()
    engagers = Counter()
    positive_mentions = []
    negative_mentions = []
    
    for mention in mentions:
        text = mention.get("text", "")
        author = mention.get("author_username", "unknown")
        
        sentiment, score = analyze_sentiment(text)
        sentiment_counts[sentiment] += 1
        
        # Track engagers
        engagers[author] += 1
        
        # Store notable mentions
        if sentiment == "positive" and score >= 2:
            positive_mentions.append({
                "author": author,
                "text": text[:100] + "..." if len(text) > 100 else text,
                "score": score
            })
        elif sentiment == "negative" and score >= 2:
            negative_mentions.append({
                "author": author,
                "text": text[:100] + "..." if len(text) > 100 else text,
                "score": score
            })
    
    # Get top engagers
    top_engagers = engagers.most_common(10)
    
    return {
        "sentiment_breakdown": dict(sentiment_counts),
        "top_engagers": top_engagers,
        "positive_highlights": positive_mentions[:5],
        "negative_alerts": negative_mentions[:5],
        "overall_sentiment": "positive" if sentiment_counts["positive"] > sentiment_counts["negative"] else "negative" if sentiment_counts["negative"] > sentiment_counts["positive"] else "neutral"
    }

def generate_sentiment_insights(analysis):
    """Generate actionable insights from sentiment analysis."""
    insights = []
    
    sb = analysis["sentiment_breakdown"]
    total = sum(sb.values())
    
    if total > 0:
        pos_pct = (sb.get("positive", 0) / total) * 100
        neg_pct = (sb.get("negative", 0) / total) * 100
        
        if pos_pct > 60:
            insights.append(f"Strong positive sentiment ({pos_pct:.0f}%) — community is bullish")
        elif neg_pct > 30:
            insights.append(f"⚠️ Elevated negative sentiment ({neg_pct:.0f}%) — monitor closely")
        
        # Top engager insight
        if analysis["top_engagers"]:
            top = analysis["top_engagers"][0]
            insights.append(f"@{top[0]} engages with you most ({top[1]} mentions) — consider following back")
    
    # Positive highlights
    if analysis["positive_highlights"]:
        insights.append(f"{len(analysis['positive_highlights'])} highly positive mentions — good engagement opportunities")
    
    # Negative alerts
    if analysis["negative_alerts"]:
        insights.append(f"{len(analysis['negative_alerts'])} negative mentions need attention")
    
    return insights
