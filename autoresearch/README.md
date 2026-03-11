# Atlas Autoresearch - Source Quality System

Simplified source scoring and weight adjustment for Atlas intel pipeline.

## Components

### source_scorer.py
Tracks intel source quality and stores ratings in SQLite.

**Key Features:**
- Rate intel from any source (1-5 scale)
- Track which sources produce actionable intel
- Store ratings with tags, timestamps, and notes
- Query source statistics and history

**Usage:**
```bash
# Quick rate a piece of intel
python3 source_scorer.py --rate "source_id" "Source Name" "type" "summary" 4 --tags "crypto,alpha" --actionable

# View source statistics
python3 source_scorer.py --stats

# Generate full report
python3 source_scorer.py --report
```

**Python API:**
```python
from source_scorer import SourceScorer, IntelRecord

scorer = SourceScorer()

# Quick rate
scorer.quick_rate(
    source_id="twitter_whale_alert",
    source_name="Whale Alert",
    source_type="twitter",
    summary="Large BTC transfer to exchange",
    rating=4,
    tags=["crypto", "whale", "btc"],
    actionable=True
)

# Get high-quality sources
high_quality = scorer.get_sources_by_quality(min_rating=4.0)
```

### weight_adjuster.py
Weekly review that adjusts source weights based on ratings.

**Logic:**
- **Deprecate:** Sources with avg rating < 3.0 (weight × 0.3)
- **Boost:** Sources with avg rating > 4.0 (weight × 1.5, capped at 3.0)
- **Minimum samples:** 5 ratings before action

**Usage:**
```bash
# Run weekly review
python3 weight_adjuster.py --review

# Generate full report
python3 weight_adjuster.py --report

# See recommendations without changing
python3 weight_adjuster.py --recommendations

# Reset a deprecated source
python3 weight_adjuster.py --reset "source_id"
```

### atlas_source_review.py
Weekly cron job that runs the full review.

**Schedule:** Sundays at 9:00 PM

**What it does:**
1. Runs weight adjustments
2. Generates human-readable report
3. Saves JSON report to `reports/weekly_review_YYYYMMDD.json`
4. Prints summary statistics

## Rating Scale

| Rating | Meaning | Action |
|--------|---------|--------|
| 1 | Worthless | Deprecate if pattern continues |
| 2 | Poor | Monitor closely |
| 3 | Average | Keep active |
| 4 | Good | Consider boosting |
| 5 | Excellent | Boost priority |

## Database

SQLite database at `source_scores.db` with two tables:
- `intel_records`: Individual intel pieces with ratings
- `source_weights`: Aggregated stats and current weights

## Integration

Use source weights to prioritize intel collection:
```python
from source_scorer import SourceScorer

scorer = SourceScorer()
stats = scorer.get_source_stats()

# Fetch more frequently from high-weight sources
for source_id, stat in stats.items():
    if stat['status'] == 'boosted':
        fetch_interval = 60  # 1 minute
    elif stat['status'] == 'deprecated':
        fetch_interval = 3600  # 1 hour (or skip)
    else:
        fetch_interval = 300  # 5 minutes
```

## Files

- `source_scorer.py` - Core scoring module
- `weight_adjuster.py` - Weight adjustment logic
- `atlas_source_review.py` - Weekly cron script
- `source_scores.db` - SQLite database
- `reports/` - Weekly review JSON outputs
