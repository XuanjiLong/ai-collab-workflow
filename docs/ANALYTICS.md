# Analytics and Trend Tracking

## Purpose

Provide longitudinal visibility for process quality and rubric evolution.

## Required Metrics

1. Coder self-review accuracy trend
- `quality_score_mae`: mean absolute error between coder estimate and reviewer score
- `risk_level_match_rate`: percentage of rounds where risk estimate matches reviewer risk level

2. Iteration efficiency by work type
- `avg_round_count_by_work_type`
- `p95_round_count_by_work_type`

3. Definition mismatch hotspots
- `definition_mismatch_frequency`
- top mismatch tags by trailing 7/30 days

## Event Model

Persist one `metrics_snapshot` per finalized task:

```json
{
  "task_id": "T-...",
  "work_type": "new_feature|refactor|bugfix|other",
  "final_status": "closed|escalated_to_main",
  "round_count": 2,
  "quality_score_mae": 7.0,
  "risk_level_match_rate": 0.5,
  "definition_mismatch_count": 1,
  "top_definition_mismatch_tags": ["edge_case_required"],
  "created_at": "2026-03-04T10:00:00Z"
}
```

## Aggregation Cadence

- Per task finalize: write snapshot
- Daily: refresh rolling dashboards and anomaly checks
- Weekly: review rubric iteration candidates

## Alert Rules

- `quality_score_mae` rises above historical baseline for 3 consecutive days
- `avg_round_count_by_work_type` exceeds agreed threshold
- a mismatch tag appears in top-3 for 2 consecutive weekly windows

## Rubric Iteration Loop

1. Identify high-frequency mismatch tags
2. Update `review_rubric.correctness_definition` or examples
3. Bump `review_rubric.version`
4. Run A/B comparison before full rollout
