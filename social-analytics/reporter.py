"""Run Atlas Twitter analytics MVP and push report to Notion."""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Dict, List

import requests

from twitter_client import TwitterClient
from storage import MetricRow, fetch_week_over_week, init_db, insert_metric


def _load_dotenv() -> None:
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

CLIENTS = {
    "Pharaoh": "PharaohDEX",
    "Benqi": "BenqiFinance",
    "Magic Eden": "MagicEden",
}


def _fmt_delta(current: int, previous: int | None) -> str:
    if previous is None:
        return "—"
    delta = current - previous
    return f"{delta:+}"


def build_rows(results: Dict[str, Dict]) -> List[List[str]]:
    rows = [
        [
            "Client",
            "Followers",
            "WoW Δ",
            "Tweets (7d)",
            "WoW Δ",
            "Engagement (7d)",
            "WoW Δ",
        ]
    ]
    for client, data in results.items():
        rows.append(
            [
                client,
                str(data["followers"]),
                data["followers_delta"],
                str(data["tweets"]),
                data["tweets_delta"],
                str(data["engagement"]),
                data["engagement_delta"],
            ]
        )
    return rows


def create_notion_report(rows: List[List[str]]) -> str | None:
    _load_dotenv()
    token = os.getenv("NOTION_TOKEN") or os.getenv("NOTION_API_KEY")
    parent_id = os.getenv("NOTION_PARENT_PAGE_ID") or os.getenv("NOTION_PAGE_ID")
    if not token or not parent_id:
        print("Missing NOTION_TOKEN/NOTION_API_KEY or NOTION_PARENT_PAGE_ID/NOTION_PAGE_ID. Skipping Notion push.")
        return None

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    title = f"Atlas Twitter Analytics — {date.today().isoformat()}"
    page_payload = {
        "parent": {"page_id": parent_id},
        "properties": {
            "title": [
                {"type": "text", "text": {"content": title}}
            ]
        },
    }
    page_resp = requests.post("https://api.notion.com/v1/pages", headers=headers, json=page_payload, timeout=30)
    page_resp.raise_for_status()
    page = page_resp.json()

    table_block = {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": len(rows[0]),
            "has_column_header": True,
            "has_row_header": False,
            "children": [
                {
                    "object": "block",
                    "type": "table_row",
                    "table_row": {
                        "cells": [
                            [{"type": "text", "text": {"content": cell}}] for cell in row
                        ]
                    },
                }
                for row in rows
            ],
        },
    }

    children_resp = requests.patch(
        f"https://api.notion.com/v1/blocks/{page['id']}/children",
        headers=headers,
        json={"children": [table_block]},
        timeout=30,
    )
    children_resp.raise_for_status()
    return page.get("url")


def run() -> None:
    _load_dotenv()
    init_db()
    twitter = TwitterClient()
    today = date.today().isoformat()

    results: Dict[str, Dict] = {}

    for client_name, handle in CLIENTS.items():
        metrics = twitter.fetch_metrics(handle, days=7)
        insert_metric(
            MetricRow(
                date=today,
                client=client_name,
                followers=metrics.followers,
                tweets=metrics.tweets,
                engagement=metrics.engagement,
            )
        )

        latest, prior = fetch_week_over_week(client_name)
        results[client_name] = {
            "followers": metrics.followers,
            "tweets": metrics.tweets,
            "engagement": metrics.engagement,
            "followers_delta": _fmt_delta(metrics.followers, prior.followers if prior else None),
            "tweets_delta": _fmt_delta(metrics.tweets, prior.tweets if prior else None),
            "engagement_delta": _fmt_delta(metrics.engagement, prior.engagement if prior else None),
        }

    rows = build_rows(results)
    notion_url = create_notion_report(rows)
    if notion_url:
        print(f"Notion report created: {notion_url}")


if __name__ == "__main__":
    run()
