#!/usr/bin/env python3
"""
Atlas Autoresearch - Weight Adjuster
Weekly review that adjusts source weights based on your ratings.
Deprecates poor sources, boosts high performers.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass

# Database path (same as source_scorer)
DB_PATH = Path("/Users/bill/.openclaw/workspace/projects/atlas/autoresearch/source_scores.db")

# Weight adjustment constants
DEPRECATE_THRESHOLD = 3.0      # Avg rating below this = deprecated
BOOST_THRESHOLD = 4.0          # Avg rating above this = boosted
MIN_RECORDS_FOR_ACTION = 5     # Need at least this many ratings
WEIGHT_BOOST_FACTOR = 1.5      # Multiply weight by this for boosted sources
WEIGHT_DEPRECATE_FACTOR = 0.3  # Multiply weight by this for deprecated sources
DEFAULT_WEIGHT = 1.0


@dataclass
class WeightAdjustment:
    """Result of a weight adjustment decision"""
    source_id: str
    source_name: str
    old_weight: float
    new_weight: float
    old_status: str
    new_status: str
    avg_rating: float
    total_records: int
    reason: str


class WeightAdjuster:
    """Adjusts source weights based on historical ratings"""
    
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or DB_PATH
        self.adjustments: List[WeightAdjustment] = []
    
    def run_weekly_review(self) -> List[WeightAdjustment]:
        """
        Run the weekly source weight adjustment.
        
        Returns:
            List of adjustments made
        """
        self.adjustments = []
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get all sources with enough data
            sources = conn.execute("""
                SELECT * FROM source_weights 
                WHERE total_records >= ?
                ORDER BY avg_rating ASC
            """, (MIN_RECORDS_FOR_ACTION,)).fetchall()
            
            for source in sources:
                adjustment = self._evaluate_source(conn, dict(source))
                if adjustment:
                    self.adjustments.append(adjustment)
            
            conn.commit()
        
        return self.adjustments
    
    def _evaluate_source(self, conn, source: Dict) -> WeightAdjustment:
        """Evaluate a single source and adjust weight if needed"""
        source_id = source['source_id']
        source_name = source['source_name']
        current_weight = source['current_weight'] or DEFAULT_WEIGHT
        current_status = source['status'] or 'active'
        avg_rating = source['avg_rating'] or 0.0
        total_records = source['total_records'] or 0
        
        new_weight = current_weight
        new_status = current_status
        reason = "No change"
        
        # Decision logic
        if avg_rating < DEPRECATE_THRESHOLD:
            # Deprecate poor performers
            new_weight = current_weight * WEIGHT_DEPRECATE_FACTOR
            new_status = 'deprecated'
            reason = f"Avg rating {avg_rating:.2f} below threshold {DEPRECATE_THRESHOLD}"
            
        elif avg_rating > BOOST_THRESHOLD:
            # Boost high performers
            new_weight = min(current_weight * WEIGHT_BOOST_FACTOR, 3.0)  # Cap at 3x
            new_status = 'boosted'
            reason = f"Avg rating {avg_rating:.2f} above threshold {BOOST_THRESHOLD}"
            
        elif current_status in ['deprecated', 'boosted']:
            # Return to normal if rating stabilizes in middle range
            new_weight = DEFAULT_WEIGHT
            new_status = 'active'
            reason = f"Rating {avg_rating:.2f} normalized, returning to active"
        
        # Apply the change
        if new_weight != current_weight or new_status != current_status:
            conn.execute("""
                UPDATE source_weights 
                SET current_weight = ?, status = ?, last_updated = ?
                WHERE source_id = ?
            """, (new_weight, new_status, datetime.now().isoformat(), source_id))
            
            return WeightAdjustment(
                source_id=source_id,
                source_name=source_name,
                old_weight=current_weight,
                new_weight=new_weight,
                old_status=current_status,
                new_status=new_status,
                avg_rating=avg_rating,
                total_records=total_records,
                reason=reason
            )
        
        return None
    
    def get_recommendations(self) -> Dict:
        """
        Get recommendations for source management.
        
        Returns:
            Dict with sources to boost, deprecate, and monitor
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Sources to deprecate (low rating, enough samples)
            deprecate = conn.execute("""
                SELECT source_id, source_name, avg_rating, total_records
                FROM source_weights
                WHERE avg_rating < ? AND total_records >= ? AND status != 'deprecated'
                ORDER BY avg_rating ASC
            """, (DEPRECATE_THRESHOLD, MIN_RECORDS_FOR_ACTION)).fetchall()
            
            # Sources to boost (high rating, enough samples)
            boost = conn.execute("""
                SELECT source_id, source_name, avg_rating, total_records
                FROM source_weights
                WHERE avg_rating > ? AND total_records >= ? AND status != 'boosted'
                ORDER BY avg_rating DESC
            """, (BOOST_THRESHOLD, MIN_RECORDS_FOR_ACTION)).fetchall()
            
            # Sources needing more data (not enough ratings yet)
            need_data = conn.execute("""
                SELECT source_id, source_name, avg_rating, total_records
                FROM source_weights
                WHERE total_records < ?
                ORDER BY total_records ASC
            """, (MIN_RECORDS_FOR_ACTION,)).fetchall()
            
            # Recently deprecated that might deserve a second chance
            second_chance = conn.execute("""
                SELECT source_id, source_name, avg_rating, total_records
                FROM source_weights
                WHERE status = 'deprecated' AND avg_rating > ?
                ORDER BY avg_rating DESC
            """, (DEPRECATE_THRESHOLD + 0.3,)).fetchall()
            
            return {
                "deprecate": [dict(r) for r in deprecate],
                "boost": [dict(r) for r in boost],
                "need_more_data": [dict(r) for r in need_data],
                "second_chance_candidates": [dict(r) for r in second_chance]
            }
    
    def generate_weekly_report(self) -> str:
        """Generate a human-readable weekly report"""
        lines = []
        lines.append("=" * 60)
        lines.append("ATLAS SOURCE QUALITY REVIEW")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("=" * 60)
        
        # Run the adjustment
        adjustments = self.run_weekly_review()
        
        if adjustments:
            lines.append("\n📊 WEIGHT ADJUSTMENTS MADE:\n")
            for adj in adjustments:
                emoji = "🚀" if adj.new_status == 'boosted' else "📉" if adj.new_status == 'deprecated' else "🔄"
                lines.append(f"{emoji} {adj.source_name}")
                lines.append(f"   Status: {adj.old_status} → {adj.new_status}")
                lines.append(f"   Weight: {adj.old_weight:.2f} → {adj.new_weight:.2f}")
                lines.append(f"   Rating: {adj.avg_rating:.2f} ({adj.total_records} records)")
                lines.append(f"   Reason: {adj.reason}")
                lines.append("")
        else:
            lines.append("\n✅ No weight adjustments needed this week.")
        
        # Recommendations
        recs = self.get_recommendations()
        
        if recs['deprecate']:
            lines.append("\n⚠️  SOURCES TO CONSIDER REMOVING:")
            for s in recs['deprecate']:
                lines.append(f"   • {s['source_name']}: {s['avg_rating']:.2f} avg ({s['total_records']} ratings)")
        
        if recs['boost']:
            lines.append("\n⭐ SOURCES PERFORMING WELL:")
            for s in recs['boost']:
                lines.append(f"   • {s['source_name']}: {s['avg_rating']:.2f} avg ({s['total_records']} ratings)")
        
        if recs['need_more_data']:
            lines.append("\n⏳ SOURCES NEEDING MORE RATINGS:")
            for s in recs['need_more_data'][:5]:  # Top 5
                lines.append(f"   • {s['source_name']}: {s['total_records']} ratings so far")
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)
    
    def reset_source(self, source_id: str) -> bool:
        """
        Reset a source to default weight and active status.
        Use this if you want to give a deprecated source another chance.
        
        Args:
            source_id: The source to reset
            
        Returns:
            True if source was found and reset
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE source_weights 
                SET current_weight = 1.0, status = 'active', last_updated = ?
                WHERE source_id = ?
            """, (datetime.now().isoformat(), source_id))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def manual_adjust_weight(self, source_id: str, new_weight: float, reason: str = "") -> bool:
        """
        Manually adjust a source's weight.
        
        Args:
            source_id: The source to adjust
            new_weight: New weight value
            reason: Optional reason for the adjustment
            
        Returns:
            True if source was found and updated
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE source_weights 
                SET current_weight = ?, last_updated = ?
                WHERE source_id = ?
            """, (new_weight, datetime.now().isoformat(), source_id))
            
            conn.commit()
            return cursor.rowcount > 0


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Atlas Weight Adjuster")
    parser.add_argument("--review", action="store_true", 
                       help="Run weekly review and adjust weights")
    parser.add_argument("--report", action="store_true",
                       help="Generate weekly report (includes review)")
    parser.add_argument("--recommendations", action="store_true",
                       help="Show recommendations without making changes")
    parser.add_argument("--reset", metavar="SOURCE_ID",
                       help="Reset a source to default weight")
    parser.add_argument("--set-weight", nargs=2, metavar=('SOURCE_ID', 'WEIGHT'),
                       help="Manually set a source's weight")
    
    args = parser.parse_args()
    
    adjuster = WeightAdjuster()
    
    if args.review:
        adjustments = adjuster.run_weekly_review()
        print(f"\nMade {len(adjustments)} weight adjustments:")
        for adj in adjustments:
            print(f"  {adj.source_name}: {adj.old_status} → {adj.new_status} (weight: {adj.old_weight:.2f} → {adj.new_weight:.2f})")
    
    elif args.report:
        print(adjuster.generate_weekly_report())
    
    elif args.recommendations:
        recs = adjuster.get_recommendations()
        print("\n=== Recommendations ===")
        print(f"\nTo Deprecate: {len(recs['deprecate'])}")
        for s in recs['deprecate']:
            print(f"  • {s['source_name']}: {s['avg_rating']:.2f}")
        
        print(f"\nTo Boost: {len(recs['boost'])}")
        for s in recs['boost']:
            print(f"  • {s['source_name']}: {s['avg_rating']:.2f}")
        
        print(f"\nNeed More Data: {len(recs['need_more_data'])}")
        for s in recs['need_more_data'][:5]:
            print(f"  • {s['source_name']}: {s['total_records']} ratings")
    
    elif args.reset:
        if adjuster.reset_source(args.reset):
            print(f"Reset {args.reset} to default weight and active status")
        else:
            print(f"Source {args.reset} not found")
    
    elif args.set_weight:
        source_id, weight = args.set_weight
        if adjuster.manual_adjust_weight(source_id, float(weight)):
            print(f"Set {source_id} weight to {weight}")
        else:
            print(f"Source {source_id} not found")
    
    else:
        parser.print_help()
