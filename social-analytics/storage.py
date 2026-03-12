"""SQLite storage for Atlas social analytics MVP."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).resolve().parent / "data" / "twitter_metrics.db"


@dataclass
class MetricRow:
    date: str
    client: str
    followers: int
    tweets: int
    engagement: int


def init_db(db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics (
                date TEXT NOT NULL,
                client TEXT NOT NULL,
                followers INTEGER NOT NULL,
                tweets INTEGER NOT NULL,
                engagement INTEGER NOT NULL,
                PRIMARY KEY (date, client)
            )
            """
        )
        conn.commit()


def insert_metric(row: MetricRow, db_path: Path = DB_PATH) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO metrics (date, client, followers, tweets, engagement)
            VALUES (?, ?, ?, ?, ?)
            """,
            (row.date, row.client, row.followers, row.tweets, row.engagement),
        )
        conn.commit()


def _fetch_row(date: str, client: str, db_path: Path = DB_PATH) -> Optional[MetricRow]:
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            "SELECT date, client, followers, tweets, engagement FROM metrics WHERE date = ? AND client = ?",
            (date, client),
        )
        row = cur.fetchone()
        if not row:
            return None
        return MetricRow(*row)


def fetch_latest(client: str, db_path: Path = DB_PATH) -> Optional[MetricRow]:
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            "SELECT date, client, followers, tweets, engagement FROM metrics WHERE client = ? ORDER BY date DESC LIMIT 1",
            (client,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return MetricRow(*row)


def fetch_week_over_week(client: str, db_path: Path = DB_PATH) -> tuple[Optional[MetricRow], Optional[MetricRow]]:
    latest = fetch_latest(client, db_path)
    if not latest:
        return None, None
    latest_date = datetime.fromisoformat(latest.date)
    prior_date = (latest_date - timedelta(days=7)).date().isoformat()
    prior = _fetch_row(prior_date, client, db_path)
    return latest, prior
