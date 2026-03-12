# Atlas Social Analytics + Notion Integration Plan

## Executive Summary

This document outlines a Hootsuite-like social media analytics system for Atlas that tracks client social accounts week-over-week, generates performance charts, and outputs reports to Notion for team sharing.

**Status:** Research Phase  
**Last Updated:** 2026-03-11  
**Clients:** Pharaoh, Benqi, Magic Eden, Bullet, Pro Rata/Gist

---

## 1. Social API Research

### 1.1 Twitter/X API (PRIMARY FOCUS)

**Current State (March 2026):**
- **API v2** is the current version (v1.1 deprecated)
- **Free Tier:** 1,500 tweets/month read limit, 1 app, basic search
- **Basic Tier ($100/mo):** 10,000 tweets/month, 2 apps, full archive search
- **Pro Tier ($5,000/mo):** 1M tweets/month, 3 apps, real-time streaming

**Available Metrics (Free/Basic Tiers):**
- Public metrics: likes, retweets, replies, quote tweets, impressions
- Follower counts
- Tweet volume (posts per time period)
- Account metadata (bio, location, verified status)
- Recent tweets (last 7 days on Free, full archive on Basic+)

**Key API v2 Endpoints:**

| Endpoint | Purpose | Rate Limit (Free) |
|----------|---------|-------------------|
| `GET /2/users/by/username/:username` | Get user ID from handle | 300/15 min |
| `GET /2/users/:id` | User profile + public metrics | 300/15 min |
| `GET /2/users/:id/tweets` | Recent tweets from user | 300/15 min |
| `GET /2/tweets/:id` | Tweet details + metrics | 300/15 min |
| `GET /2/tweets/search/recent` | Search recent tweets | 450/15 min |

**Tweet Fields to Request:**
```
tweet.fields=public_metrics,created_at,author_id,conversation_id
```

**Public Metrics Object:**
```json
{
  "retweet_count": 45,
  "reply_count": 12,
  "like_count": 320,
  "quote_count": 8,
  "bookmark_count": 25,
  "impression_count": 5420
}
```

**User Fields to Request:**
```
user.fields=public_metrics,created_at,description,verified
```

**User Public Metrics:**
```json
{
  "followers_count": 15420,
  "following_count": 450,
  "tweet_count": 892,
  "listed_count": 123
}
```

**Limitations:**
- No engagement rate calculation (must compute: engagements / impressions)
- No historical follower growth data (must track ourselves)
- Rate limits: 300 requests/15 min per user (Free), 450/15 min (Basic)
- No DM access on lower tiers
- No tweet analytics beyond public metrics
- Free tier: only last 7 days of tweets searchable

**Access Level Required:**
- Read-only OAuth 2.0 (App-Auth) sufficient for public data
- User OAuth 2.0 only needed for protected accounts or posting

**Recommendation:** Start with Free tier, upgrade to Basic ($100/mo) if tracking >10 clients or need archive data.

---

### 1.2 LinkedIn API (DEFERRED)

**Status:** Not in scope for initial implementation. Twitter/X only for Phase 1-2.

**Future Consideration:**
- **Marketing Developer Platform** required for organization data
- **Application required:** 2-4 weeks approval process
- **Rate limits:** 500 requests/day per app
- Only needed for Pro Rata/Gist LinkedIn tracking

**Decision:** Focus 100% on Twitter/X analytics. LinkedIn can be added in Phase 3 if needed.

---

### 1.3 Discord API

**Current State:**
- **Bot API** for server/channel data
- **Gateway** for real-time events (not needed for analytics)

**Available Metrics (Bot Permissions):**
- Server member count
- Channel message volume
- Reaction counts on messages
- Voice channel participation
- Role assignments

**Limitations:**
- Must be invited to each server as a bot
- Cannot access message history without `MESSAGE_CONTENT` intent
- `MESSAGE_CONTENT` requires Discord verification for >100 servers
- No native "engagement rate" metric
- No follower/subscriber concept (just member count)

**Access Level Required:**
- Bot token with `Read Messages`, `View Channels`, `Read Message History` permissions
- Must be invited to each client Discord server

**Recommendation:** Create a dedicated Atlas analytics bot. Request `MESSAGE_CONTENT` intent during verification.

---

### 1.4 Instagram API (OUT OF SCOPE)

**Status:** Not in scope. Twitter/X only for all phases.

**Note:** All client tracking via Twitter/X API. Instagram may be considered in future expansion phases if clients request it.

---

### 1.5 YouTube API (OUT OF SCOPE)

**Status:** Not in scope. Twitter/X only for all phases.

---

## 2. Data Architecture

### 2.1 Data to Store

**Account-Level Metrics (Daily Snapshots):**
```json
{
  "account_id": "pharaoh_twitter",
  "platform": "twitter",
  "handle": "pharaoh",
  "date": "2026-03-11",
  "followers": 15420,
  "following": 450,
  "tweets_count": 892,
  "created_at": "2025-01-15T00:00:00Z"
}
```

**Content-Level Metrics (Per Post):**
```json
{
  "post_id": "1234567890",
  "account_id": "pharaoh_twitter",
  "platform": "twitter",
  "content_type": "tweet",
  "posted_at": "2026-03-11T14:30:00Z",
  "text": "Sample tweet content...",
  "metrics": {
    "impressions": 5420,
    "likes": 320,
    "retweets": 45,
    "replies": 12,
    "quotes": 8
  },
  "engagement_rate": 0.071  // calculated: (likes+retweets+replies+quotes)/impressions
}
```





### 2.2 Week-over-Week Comparison Strategy

**Storage Pattern:**
- Daily snapshots for all metrics (enables any comparison window)
- Rolling 90-day retention for granular data
- Aggregated weekly summaries for long-term trends

**Comparison Logic:**
```python
def calculate_wow_change(current, previous):
    """Calculate week-over-week percentage change"""
    if previous == 0:
        return None  # or 100% if current > 0
    return ((current - previous) / previous) * 100

# Example usage:
# Current followers: 15,420
# Previous week followers: 14,890
# WoW change: +3.57%
```

**Key Metrics to Compare:**
1. **Follower Growth:** Absolute change + percentage
2. **Engagement Rate:** Current vs previous week
3. **Content Volume:** Tweets per week
4. **Top Performing Content:** Best tweet by engagement rate

### 2.3 Database Schema (SQLite/PostgreSQL)

```sql
-- Accounts table
CREATE TABLE accounts (
    id TEXT PRIMARY KEY,
    client_name TEXT NOT NULL,
    platform TEXT NOT NULL,
    handle TEXT NOT NULL,
    external_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(client_name, platform, handle)
);

-- Daily snapshots table
CREATE TABLE daily_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    date DATE NOT NULL,
    followers INTEGER,
    following INTEGER,
    posts_count INTEGER,
    impressions INTEGER,
    engagement_rate REAL,
    raw_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    UNIQUE(account_id, date)
);

-- Posts table
CREATE TABLE posts (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    content_type TEXT,
    posted_at TIMESTAMP,
    text TEXT,
    impressions INTEGER,
    likes INTEGER,
    shares INTEGER,
    comments INTEGER,
    engagement_rate REAL,
    raw_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);


```

---

## 3. Notion Integration

### 3.1 Notion API Requirements

**Authentication:**
- **Integration Token:** Create at notion.so/my-integrations
- **Internal Integration:** For single-workspace use
- **OAuth Integration:** If sharing with external users (not needed)

**Required Capabilities:**
- Read content
- Insert content
- Update content
- No user information needed

**Rate Limits:**
- 3 requests per second sustained
- Burst up to ~100 requests
- Retry with exponential backoff on 429 errors

### 3.2 Notion Database Structure

**Weekly Reports Database:**
```
Properties:
- Client (Select): Pharaoh, Benqi, Magic Eden, Bullet, Pro Rata/Gist
- Week Starting (Date): Monday of report week
- Platform (Select): Twitter/X
- Status (Select): Draft, Review, Published
- Report URL (URL): Link to full report page
- Created By (Person): Bill (automation)
```

**Report Page Template:**
```
# [Client] Social Analytics - Week of [Date]

## Executive Summary
- Total Followers: X (+Y% WoW)
- Engagement Rate: X% (+Y% WoW)
- Posts Published: X

## Twitter/X Analytics

### Follower Growth
[Chart: Follower count over time]

### Engagement Trends
[Chart: Engagement rate over time]

### Content Performance
[Table: Top Performing Tweets]
- Tweet text (truncated)
- Posted date
- Impressions
- Likes
- Retweets
- Replies
- Engagement rate

## Week-over-Week Changes
| Metric | This Week | Last Week | Change |
|--------|-----------|-----------|--------|
| Followers | X | Y | +Z% |
| Engagement Rate | X% | Y% | +Z% |
| Tweets Posted | X | Y | +Z |
| Total Impressions | X | Y | +Z% |

## Insights & Recommendations
[Auto-generated insights based on data]
```

### 3.3 Chart/Graph Generation

**Option 1: Notion Native Charts (Limited)**
- Notion doesn't support embedded charts directly
- Can embed images of charts
- Simple but static

**Option 2: Generate Images with Python**
- Use `matplotlib` or `plotly` to generate chart images
- Upload to Notion as image blocks
- Full control over styling

**Option 3: External Dashboard (Future)**
- Generate charts in a web dashboard
- Embed in Notion via iframe (if Notion supports)
- Or link out to dashboard

**Recommendation:** Option 2 (Python chart generation) for MVP. Store images in Notion or external CDN.

### 3.4 Sharing Configuration

**Notion Page Permissions:**
- Create reports in a shared workspace
- Add Hunter, Bryan, Jonathan as viewers/editors
- Use @mentions for specific callouts

**Notification Strategy:**
- Post link to new reports in #phoenix-ops or #atlas Slack/Discord
- Optional: Email digest with report summaries

---

## 4. Implementation Phases

### Phase 1: MVP (Weeks 1-2)

**Scope:**
- Twitter/X API integration (Free tier)
- 2-3 clients (Pharaoh, Benqi, Magic Eden)
- Daily follower tracking
- Weekly report generation
- Basic Notion integration (text + tables)

**Deliverables:**
- Database schema implemented
- Twitter data collector script
- Weekly report generator
- Notion page creator
- First report delivered

**Technical Stack:**
- Python 3.11+
- SQLite for data storage
- `tweepy` for Twitter API
- `notion-client` for Notion API
- `matplotlib` for basic charts

**Cost:** $0 (Free tier APIs)

---

### Phase 2: Enhanced Analytics (Weeks 3-4)

**Scope:**
- Add all 5 clients
- Content-level tracking (individual tweets)
- Engagement rate calculations
- Chart generation (follower growth, engagement trends)
- Tweet performance tracking and top content identification

**Deliverables:**
- Content performance tracking
- Visual charts in Notion reports
- Top performing tweets table
- Engagement trend analysis

**Cost:** $0-100/month (Twitter Basic if needed)

---

### Phase 3: Advanced Features (Weeks 5-8)

**Scope:**
- Competitor benchmarking (track competitor Twitter accounts)
- Automated insights (AI-generated recommendations)
- Historical trend analysis (90-day lookback)
- Custom alert thresholds (follower milestones, engagement drops)
- Dashboard web interface (optional)

**Deliverables:**
- Competitor tracking
- AI insight generator
- Alert system for significant changes
- Optional: Web dashboard

**Cost:** $100-200/month (Twitter Basic + hosting)

---

### Phase 4: Scale & Automation (Ongoing)

**Scope:**
- Additional clients (onboard new clients easily)
- Advanced analytics (sentiment analysis, optimal posting times)
- Client-facing reports (white-label option)

**Cost:** $100-200/month (depending on client count)

---

## 5. API Access Action Items

### Immediate (This Week):
1. **Twitter/X:** Apply for Developer account at developer.twitter.com
   - Create project and app
   - Generate API keys
   - Test with Pharaoh's public data

2. **Notion:** Create integration at notion.so/my-integrations
   - Generate internal integration token
   - Create test database
   - Share with Hunter, Bryan, Jonathan

### Short-term (Next 2 Weeks):
3. **Validate data accuracy** against Twitter UI
4. **Build chart generation** with matplotlib/plotly

---

## 6. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Twitter API rate limits | Medium | Medium | Implement caching, respect limits, upgrade tier if needed |


| API pricing changes | Low | High | Monitor announcements, build abstraction layer |
| Data accuracy issues | Medium | Medium | Validate data, implement error handling, manual spot checks |

---

## 7. Success Metrics

**System Health:**
- 100% of scheduled data collections complete
- <1% API error rate
- Reports generated within 1 hour of scheduled time

**Data Quality:**
- Follower counts match platform UI (±1%)
- All posts from last 7 days captured
- No missing days in historical data

**User Adoption:**
- Reports viewed by all 3 team members
- Zero manual data entry required
- Positive feedback on report usefulness

---

## 8. Next Steps

1. **Review this plan** with Jonathan, Hunter, Bryan
2. **Approve Phase 1 scope** and timeline
3. **Apply for API access** (Twitter, Notion)
4. **Create database** and initial schema
5. **Build Twitter collector** (Phase 1)
6. **Deliver first report** (target: 1 week from start)

---

## Appendix A: Client Account Details

| Client | Twitter Handle | Priority |
|--------|---------------|----------|
| Pharaoh | @pharaoh | P0 |
| Benqi | @benqifinance | P0 |
| Magic Eden | @magiceden | P0 |
| Bullet | @bulletxyz | P1 |
| Pro Rata | @prorata | P1 |
| Gist | @gist | P1 |

---

## Appendix B: API Documentation Links

- **Twitter API v2:** https://developer.twitter.com/en/docs/twitter-api
- **Notion API:** https://developers.notion.com/

---

*Document Version: 1.1*  
*Author: Bill (Atlas Social Analytics Sub-agent)*  
*Date: 2026-03-11*  
*Update: Twitter/X only scope - removed LinkedIn/Discord*
