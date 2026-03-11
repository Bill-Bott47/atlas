#!/usr/bin/env python3
"""
Atlas Source Review - Weekly Cron Job
Runs Sundays at 9pm to review source quality and adjust weights.
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# Add autoresearch directory to path
sys.path.insert(0, str(Path(__file__).parent))

from weight_adjuster import WeightAdjuster
from source_scorer import SourceScorer


def main():
    """Run the weekly source review"""
    print(f"🔄 Atlas Source Review - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)
    
    # Initialize components
    adjuster = WeightAdjuster()
    scorer = SourceScorer()
    
    # Generate and print report
    report = adjuster.generate_weekly_report()
    print(report)
    
    # Export full data for potential downstream use
    full_report = {
        "timestamp": datetime.now().isoformat(),
        "adjustments": [
            {
                "source_id": adj.source_id,
                "source_name": adj.source_name,
                "old_weight": adj.old_weight,
                "new_weight": adj.new_weight,
                "old_status": adj.old_status,
                "new_status": adj.new_status,
                "avg_rating": adj.avg_rating,
                "total_records": adj.total_records,
                "reason": adj.reason
            }
            for adj in adjuster.adjustments
        ],
        "recommendations": adjuster.get_recommendations(),
        "source_stats": scorer.get_source_stats()
    }
    
    # Save report to file
    report_path = Path(__file__).parent / "reports"
    report_path.mkdir(exist_ok=True)
    
    report_file = report_path / f"weekly_review_{datetime.now().strftime('%Y%m%d')}.json"
    with open(report_file, 'w') as f:
        json.dump(full_report, f, indent=2)
    
    print(f"\n📄 Full report saved to: {report_file}")
    
    # Summary stats
    total_sources = len(full_report['source_stats'])
    deprecated = sum(1 for s in full_report['source_stats'].values() if s.get('status') == 'deprecated')
    boosted = sum(1 for s in full_report['source_stats'].values() if s.get('status') == 'boosted')
    
    print(f"\n📈 Summary: {total_sources} sources tracked")
    print(f"   🚀 Boosted: {boosted}")
    print(f"   📉 Deprecated: {deprecated}")
    print(f"   ⚖️  Adjusted this week: {len(adjuster.adjustments)}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
