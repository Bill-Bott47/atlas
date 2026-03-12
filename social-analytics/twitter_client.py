"""Minimal Twitter/X API client for Atlas social analytics MVP."""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

import requests

TWITTER_API_BASE = "https://api.twitter.com/2"


def _load_dotenv() -> None:
    """Load workspace .env if present (lightweight, no external deps)."""
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass
class TwitterMetrics:
    followers: int
    tweets: int
    engagement: int  # total engagement across tweets in window


class TwitterClient:
    def __init__(self, bearer_token: str | None = None):
        if not bearer_token:
            _load_dotenv()
        self.bearer_token = bearer_token or os.getenv("X_BEARER_TOKEN") or os.getenv("TWITTER_BEARER_TOKEN")
        if not self.bearer_token:
            raise ValueError("Missing X_BEARER_TOKEN or TWITTER_BEARER_TOKEN in environment")

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.bearer_token}"}

    def get_user(self, username: str) -> Dict:
        url = f"{TWITTER_API_BASE}/users/by/username/{username}"
        params = {"user.fields": "public_metrics"}
        resp = requests.get(url, headers=self._headers(), params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()["data"]

    def get_recent_tweets(self, user_id: str, days: int = 7) -> List[Dict]:
        url = f"{TWITTER_API_BASE}/users/{user_id}/tweets"
        start_time = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        params = {
            "max_results": 100,
            "tweet.fields": "public_metrics,created_at",
            "start_time": start_time,
        }
        resp = requests.get(url, headers=self._headers(), params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])

    def fetch_metrics(self, username: str, days: int = 7) -> TwitterMetrics:
        user = self.get_user(username)
        followers = int(user["public_metrics"]["followers_count"])
        tweets = self.get_recent_tweets(user["id"], days=days)
        engagement_total = 0
        for tweet in tweets:
            metrics = tweet.get("public_metrics", {})
            engagement_total += (
                metrics.get("like_count", 0)
                + metrics.get("retweet_count", 0)
                + metrics.get("reply_count", 0)
                + metrics.get("quote_count", 0)
            )
        return TwitterMetrics(
            followers=followers,
            tweets=len(tweets),
            engagement=engagement_total,
        )
