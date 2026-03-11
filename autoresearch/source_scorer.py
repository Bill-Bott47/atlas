#!/usr/bin/env python3
"""
Atlas Autoresearch - Source Scorer
Tracks intel source quality and stores ratings in SQLite.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from enum import Enum

# Database path
DB_PATH = Path("/Users/bill/.openclaw/workspace/projects/atlas/autoresearch/source_scores.db")


class IntelRating(Enum):
    """1-5 rating scale for intel quality"""
    WORTHLESS = 1      # No value, waste of time
    POOR = 2           # Minimal value, mostly noise
    AVERAGE = 3        # Some useful bits, mixed quality
    GOOD = 4           # Actionable, solid intel
    EXCELLENT = 5      # High signal, immediately useful


@dataclass
class IntelRecord:
    """A single piece of intel from a source"""
    source_id: str
    source_name: str
    source_type: str  # rss, api, twitter, discord, etc.
    intel_summary: str
    rating: int  # 1-5
    timestamp: datetime
    tags: list  # e.g., ["crypto", "funding", "alpha"]
    actionable: bool  # Did this lead to action?
    notes: str = ""


class SourceScorer:
    """Tracks and scores intel sources"""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database with required tables"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS intel_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    intel_summary TEXT,
                    rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                    timestamp TEXT NOT NULL,
                    tags TEXT,  -- JSON array
                    actionable INTEGER,  -- 0 or 1
                    notes TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS source_weights (
                    source_id TEXT PRIMARY KEY,
                    source_name TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    current_weight REAL DEFAULT 1.0,
                    avg_rating REAL DEFAULT 0.0,
                    total_records INTEGER DEFAULT 0,
                    last_updated TEXT,
                    status TEXT DEFAULT 'active'  -- active, deprecated, boosted
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_intel_source ON intel_records(source_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_intel_timestamp ON intel_records(timestamp)
            """)
            
            conn.commit()
    
    def record_intel(self, record: IntelRecord) -> int:
        """
        Record a piece of intel with your rating.
        
        Args:
            record: IntelRecord with your rating (1-5)
            
        Returns:
            The ID of the inserted record
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO intel_records 
                (source_id, source_name, source_type, intel_summary, rating, timestamp, tags, actionable, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.source_id,
                record.source_name,
                record.source_type,
                record.intel_summary,
                record.rating,
                record.timestamp.isoformat(),
                json.dumps(record.tags),
                1 if record.actionable else 0,
                record.notes
            ))
            
            record_id = cursor.lastrowid
            
            # Update source weights table
            self._update_source_stats(conn, record.source_id, record.source_name, record.source_type, record.rating)
            
            conn.commit()
            return record_id
    
    def _update_source_stats(self, conn, source_id: str, source_name: str, source_type: str, new_rating: int):
        """Update source statistics after a new rating"""
        conn.execute("""
            INSERT INTO source_weights (source_id, source_name, source_type, current_weight, avg_rating, total_records, last_updated)
            VALUES (?, ?, ?, 1.0, ?, 1, ?)
            ON CONFLICT(source_id) DO UPDATE SET
                avg_rating = (source_weights.avg_rating * source_weights.total_records + ?) / (source_weights.total_records + 1),
                total_records = source_weights.total_records + 1,
                last_updated = ?
        """, (source_id, source_name, source_type, float(new_rating), datetime.now().isoformat(), 
              new_rating, datetime.now().isoformat()))
    
    def rate_intel(self, record_id: int, rating: int, notes: str = ""):
        """
        Update the rating for an existing intel record.
        
        Args:
            record_id: The ID of the intel record
            rating: New rating (1-5)
            notes: Optional notes about the rating
        """
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")
        
        with sqlite3.connect(self.db_path) as conn:
            # Get old rating for recalculation
            row = conn.execute(
                "SELECT source_id, rating FROM intel_records WHERE id = ?", (record_id,)
            ).fetchone()
            
            if not row:
                raise ValueError(f"Record {record_id} not found")
            
            source_id, old_rating = row
            
            # Update the record
            conn.execute(
                "UPDATE intel_records SET rating = ?, notes = ? WHERE id = ?",
                (rating, notes, record_id)
            )
            
            # Recalculate source average
            conn.execute("""
                UPDATE source_weights 
                SET avg_rating = (SELECT AVG(rating) FROM intel_records WHERE source_id = ?),
                    last_updated = ?
                WHERE source_id = ?
            """, (source_id, datetime.now().isoformat(), source_id))
            
            conn.commit()
    
    def get_source_stats(self, source_id: Optional[str] = None) -> dict:
        """
        Get statistics for one or all sources.
        
        Args:
            source_id: Specific source ID, or None for all sources
            
        Returns:
            Dict with source statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if source_id:
                row = conn.execute(
                    "SELECT * FROM source_weights WHERE source_id = ?", (source_id,)
                ).fetchone()
                return dict(row) if row else {}
            else:
                rows = conn.execute("SELECT * FROM source_weights ORDER BY avg_rating DESC").fetchall()
                return {row['source_id']: dict(row) for row in rows}
    
    def get_intel_history(self, source_id: Optional[str] = None, limit: int = 50) -> list:
        """
        Get intel history, optionally filtered by source.
        
        Args:
            source_id: Filter by source ID
            limit: Maximum records to return
            
        Returns:
            List of intel records
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if source_id:
                rows = conn.execute(
                    """SELECT * FROM intel_records 
                       WHERE source_id = ? 
                       ORDER BY timestamp DESC 
                       LIMIT ?""",
                    (source_id, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM intel_records 
                       ORDER BY timestamp DESC 
                       LIMIT ?""",
                    (limit,)
                ).fetchall()
            
            results = []
            for row in rows:
                d = dict(row)
                d['tags'] = json.loads(d['tags']) if d['tags'] else []
                d['actionable'] = bool(d['actionable'])
                results.append(d)
            
            return results
    
    def get_sources_by_quality(self, min_rating: float = 4.0) -> list:
        """
        Get sources with average rating above threshold.
        
        Args:
            min_rating: Minimum average rating (default 4.0)
            
        Returns:
            List of high-quality source IDs
        """
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """SELECT source_id FROM source_weights 
                   WHERE avg_rating >= ? AND total_records >= 3
                   ORDER BY avg_rating DESC""",
                (min_rating,)
            ).fetchall()
            return [row[0] for row in rows]
    
    def get_deprecate_candidates(self, max_rating: float = 3.0, min_records: int = 5) -> list:
        """
        Get sources that should be deprecated (low rating + enough samples).
        
        Args:
            max_rating: Maximum average rating (default 3.0)
            min_records: Minimum number of ratings before deprecation
            
        Returns:
            List of source IDs to deprecate
        """
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """SELECT source_id FROM source_weights 
                   WHERE avg_rating <= ? AND total_records >= ?
                   ORDER BY avg_rating ASC""",
                (max_rating, min_records)
            ).fetchall()
            return [row[0] for row in rows]
    
    def quick_rate(self, source_id: str, source_name: str, source_type: str, 
                   summary: str, rating: int, tags: list = None, actionable: bool = False):
        """
        Quick method to rate intel in one call.
        
        Example:
            scorer.quick_rate(
                source_id="twitter_whale_alert",
                source_name="Whale Alert Twitter",
                source_type="twitter",
                summary="Large BTC transfer to exchange",
                rating=4,
                tags=["crypto", "whale", "btc"],
                actionable=True
            )
        """
        record = IntelRecord(
            source_id=source_id,
            source_name=source_name,
            source_type=source_type,
            intel_summary=summary,
            rating=rating,
            timestamp=datetime.now(),
            tags=tags or [],
            actionable=actionable
        )
        return self.record_intel(record)
    
    def export_report(self) -> dict:
        """Generate a full report of source quality"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Source stats
            sources = conn.execute("SELECT * FROM source_weights ORDER BY avg_rating DESC").fetchall()
            
            # Rating distribution
            distribution = conn.execute("""
                SELECT rating, COUNT(*) as count 
                FROM intel_records 
                GROUP BY rating 
                ORDER BY rating
            """).fetchall()
            
            # Recent intel
            recent = conn.execute("""
                SELECT * FROM intel_records 
                ORDER BY timestamp DESC 
                LIMIT 20
            """).fetchall()
            
            return {
                "generated_at": datetime.now().isoformat(),
                "total_sources": len(sources),
                "total_intel_records": conn.execute("SELECT COUNT(*) FROM intel_records").fetchone()[0],
                "sources": [dict(s) for s in sources],
                "rating_distribution": {row['rating']: row['count'] for row in distribution},
                "recent_intel": [dict(r) for r in recent]
            }


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Atlas Source Scorer")
    parser.add_argument("--rate", nargs=5, metavar=('SOURCE_ID', 'NAME', 'TYPE', 'SUMMARY', 'RATING'),
                       help="Quick rate: source_id name type summary rating")
    parser.add_argument("--stats", action="store_true", help="Show source statistics")
    parser.add_argument("--report", action="store_true", help="Generate full report")
    parser.add_argument("--tags", default="", help="Comma-separated tags for --rate")
    parser.add_argument("--actionable", action="store_true", help="Mark as actionable")
    
    args = parser.parse_args()
    
    scorer = SourceScorer()
    
    if args.rate:
        source_id, name, source_type, summary, rating = args.rate
        record_id = scorer.quick_rate(
            source_id=source_id,
            source_name=name,
            source_type=source_type,
            summary=summary,
            rating=int(rating),
            tags=args.tags.split(",") if args.tags else [],
            actionable=args.actionable
        )
        print(f"Recorded intel with ID: {record_id}")
    
    elif args.stats:
        stats = scorer.get_source_stats()
        print("\n=== Source Statistics ===")
        for sid, s in stats.items():
            status_emoji = "🟢" if s['status'] == 'active' else "🔴"
            print(f"{status_emoji} {s['source_name']} ({s['source_type']})")
            print(f"   Avg Rating: {s['avg_rating']:.2f} | Records: {s['total_records']} | Weight: {s['current_weight']:.2f}")
    
    elif args.report:
        import json
        report = scorer.export_report()
        print(json.dumps(report, indent=2))
    
    else:
        parser.print_help()
