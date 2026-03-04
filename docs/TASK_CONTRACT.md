# Task Contract

## JSON Schema (Practical)

```json
{
  "task_id": "T-202603040001",
  "type": "code_change",
  "work_type": "new_feature",
  "goal": "Add idempotency checks to order API",
  "context": {
    "repo": "...",
    "files_hint": ["src/api/order.ts", "src/service/order_service.ts"]
  },
  "constraints": [
    "Do not change DB schema",
    "Keep backward-compatible response"
  ],
  "review_rubric": {
    "version": "v1",
    "dimensions": [
      "goal_coverage",
      "constraint_compliance",
      "correctness",
      "regression_risk",
      "test_confidence"
    ],
    "weight_profiles": {
      "new_feature": {
        "goal_coverage": 0.30,
        "constraint_compliance": 0.20,
        "correctness": 0.25,
        "regression_risk": 0.15,
        "test_confidence": 0.10
      },
      "refactor": {
        "goal_coverage": 0.15,
        "constraint_compliance": 0.20,
        "correctness": 0.25,
        "regression_risk": 0.30,
        "test_confidence": 0.10
      },
      "bugfix": {
        "goal_coverage": 0.20,
        "constraint_compliance": 0.20,
        "correctness": 0.35,
        "regression_risk": 0.15,
        "test_confidence": 0.10
      },
      "balanced": {
        "goal_coverage": 0.20,
        "constraint_compliance": 0.20,
        "correctness": 0.25,
        "regression_risk": 0.25,
        "test_confidence": 0.10
      }
    },
    "weight_profile_by_work_type": {
      "new_feature": "new_feature",
      "refactor": "refactor",
      "bugfix": "bugfix",
      "other": "balanced"
    },
    "active_weight_profile": "new_feature",
    "scoring_scale": "0..2",
    "block_threshold": 60,
    "pass_threshold": 85,
    "correctness_definition": [
      "Behavior matches goal and acceptance criteria",
      "No required constraint is violated",
      "Error handling/status code semantics are preserved"
    ]
  },
  "approval_policy": {
    "mode": "risk_based",
    "auto_approve_min_quality_score": 90,
    "human_optional_sla_seconds": 900,
    "human_required_max_wait_seconds": 1800
  },
  "retry_policy": {
    "strategy": "adaptive_by_complexity",
    "complexity_level": "medium",
    "complexity_score": 3,
    "max_rework_rounds": 2,
    "override_reason": null,
    "escalation_owner": "tech_lead",
    "allowed_escalation_actions": [
      "split_task",
      "adjust_constraints",
      "change_owner",
      "extend_retry_budget"
    ]
  },
  "output_schema": {
    "required": ["patch", "change_summary", "self_test", "self_review"]
  },
  "done_criteria": [
    "unit_test_passed",
    "block_issue_count == 0",
    "required_artifacts_present"
  ],
  "owner_agent": "coder",
  "status": "assigned",
  "deadline": null,
  "retry_count": 0,
  "rework": null
}
```

## Rules

- `goal` must be concrete and testable.
- `constraints` should be explicit and small.
- `context.files_hint` should list the most relevant files only.
- `work_type` should be one of: `new_feature|refactor|bugfix|other`.
- `retry_count` is controlled by `Main Agent` only.
- `constraints` are base constraints and must remain stable across retries.
- Retry-specific requirements must be added under `rework.rework_constraints`.
- `review_rubric` must be passed to `Coder` before every coding round.
- `review_rubric.version` should change only when criteria meaning changes.
- `review_rubric.active_weight_profile` should be selected from `weight_profile_by_work_type`.
- Each weight profile must sum to `1.0`.
- `approval_policy` controls when human approval is required.
- `retry_policy.max_rework_rounds` is task-specific and should be set at task creation.
- `retry_policy.max_rework_rounds` should follow complexity mapping unless override is justified.

## Adaptive Retry Mapping

Default mapping for `retry_policy.max_rework_rounds`:

- `complexity_level = low` -> `1`
- `complexity_level = medium` -> `2`
- `complexity_level = high` -> `3`
- `complexity_level = critical` -> `4`

Override rule:

- `Main Agent` may adjust by `+/-1` only with `retry_policy.override_reason`.

## Rework Extension (retry_count > 0)

When `retry_count > 0`, `TaskContract` should include a `rework` object:

```json
{
  "rework": {
    "from_round": 1,
    "previous_review_result": {
      "review_id": "R-T-...",
      "verdict": "block",
      "block_issues": [
        {
          "id": "B1",
          "title": "Idempotency conflict response code is missing",
          "severity": "high",
          "file": "src/service.py",
          "line": 1,
          "expected": "Return 409 with unified error payload for conflict"
        }
      ]
    },
    "previous_decision_record": {
      "action": "reject",
      "decision_mode": "human_required",
      "decision_source": "human",
      "comment": "Need fixes before merge"
    },
    "rework_constraints": [
      "Must resolve all block_issues from previous_review_result",
      "Do not introduce regressions to already-correct behavior"
    ],
    "artifact_refs": {
      "coder_output": "artifact://coder_output/12",
      "review_result": "artifact://review_result/13"
    }
  }
}
```

### Rework Semantics

- `previous_review_result` must be forwarded to `Coder` unchanged.
- `Coder` should treat all `block_issues` as mandatory fixes.
- `previous_decision_record.comment` is advisory, but should be addressed when actionable.
- Rework attempts must stop once `retry_count >= retry_policy.max_rework_rounds`.

## Escalation Package Schema (On Retry Budget Exhausted)

```json
{
  "task_id": "T-...",
  "retry_count": 3,
  "retry_budget": 3,
  "escalation_owner": "tech_lead",
  "unresolved_block_issues": ["B3", "B8"],
  "attempt_history": [
    {"round": 1, "decision": "reject", "summary": "..."},
    {"round": 2, "decision": "reject", "summary": "..."},
    {"round": 3, "decision": "reject", "summary": "..."}
  ],
  "recommended_actions": ["split_task", "change_owner"]
}
```

## Coder Output Schema

```json
{
  "patch": "unified diff text",
  "change_summary": "what changed and why",
  "self_test": {
    "unit_test_passed": true,
    "notes": "test scope and limitations"
  },
  "self_review": {
    "quality_score_estimate": 88,
    "weight_profile_used": "new_feature",
    "risk_level_estimate": "low|medium|high",
    "scorecard_estimate": {
      "goal_coverage": 2,
      "constraint_compliance": 2,
      "correctness": 2,
      "regression_risk": 2,
      "test_confidence": 1
    },
    "addressed_block_issue_ids": ["B1"],
    "known_gaps": ["non-blocking perf optimization remains"]
  }
}
```

## Reviewer Output Schema

```json
{
  "task_id": "T-...",
  "review_id": "R-T-...",
  "verdict": "pass|pass_with_suggestions|block",
  "summary": "review summary",
  "quality_score": 90,
  "weight_profile_used": "new_feature",
  "weighted_score_breakdown": {
    "goal_coverage": 30.0,
    "constraint_compliance": 20.0,
    "correctness": 25.0,
    "regression_risk": 7.5,
    "test_confidence": 5.0
  },
  "risk_level": "low|medium|high",
  "scorecard": {
    "goal_coverage": 2,
    "constraint_compliance": 2,
    "correctness": 2,
    "regression_risk": 2,
    "test_confidence": 1
  },
  "block_issues": [
    {
      "id": "B1",
      "title": "...",
      "severity": "high",
      "file": "src/...",
      "line": 42,
      "expected": "..."
    }
  ],
  "advisory_issues": [
    {
      "id": "A1",
      "title": "...",
      "severity": "low",
      "file": "src/...",
      "line": 10,
      "expected": "..."
    }
  ],
  "suggestions": ["..."],
  "recommended_decision_mode": "auto_approve|human_optional|human_required",
  "alignment": {
    "coder_self_review_delta": {
      "quality_score_diff": -8,
      "correctness_diff": 0
    },
    "definition_mismatch": [
      "Coder treated edge case as optional, rubric marks it required"
    ]
  }
}
```

### Verdict Semantics

- `pass`: merge-ready, no required follow-up, usually `quality_score >= task_contract.review_rubric.pass_threshold`.
- `pass_with_suggestions`: merge-ready with non-blocking improvements tracked, usually `task_contract.review_rubric.block_threshold <= quality_score < task_contract.review_rubric.pass_threshold`.
- `block`: not merge-ready, must rework before approval, or `quality_score < task_contract.review_rubric.block_threshold`.

### Weighted Score Formula

- Let each dimension score be `0..2`.
- Normalize each dimension as `normalized_i = score_i / 2`.
- `quality_score = round(100 * sum(weight_i * normalized_i))`.
- `weight_profile_used` must be explicit in reviewer output.
- `weighted_score_breakdown` should show per-dimension contribution in score points.

### Decision Mode Semantics

- `auto_approve`: safe for direct approval by policy.
- `human_optional`: allow human review window; auto-approve on SLA timeout if no reject.
- `human_required`: must wait for explicit human decision.

### Single Source of Truth

- `review_result` should not contain a `decision` object.
- `Main Agent` derives transition from:
  - `verdict`
  - `recommended_decision_mode`
  - `approval_policy`
- Keep decision logic centralized in `Main Agent` only.

### Advisory vs Suggestions Boundary

- `advisory_issues`: file-level, locatable, actionable findings (path + line + expected).
- `suggestions`: architecture/process-level recommendations without strict file-line requirement.

### Feedback Loop Requirement

- `Main Agent` must include `review_rubric` in coder input for every round.
- `Coder` must produce `self_review` using the same rubric dimensions.
- `Coder` must use `review_rubric.active_weight_profile` and expose it in `self_review.weight_profile_used`.
- `Reviewer` should compare review scorecard with coder self-review and report major mismatches in `alignment.definition_mismatch`.
- `Reviewer` should propose `recommended_decision_mode` using `approval_policy` and review risk signals.
- `Reviewer` must apply `review_rubric.active_weight_profile` when computing `quality_score`.

## Trend Metrics Snapshot Schema (Per Task Completion)

```json
{
  "task_id": "T-...",
  "work_type": "new_feature",
  "final_status": "closed|escalated_to_main",
  "round_count": 2,
  "quality_score_mae": 7.0,
  "risk_level_match_rate": 0.5,
  "definition_mismatch_count": 1,
  "top_definition_mismatch_tags": ["edge_case_required"],
  "created_at": "2026-03-04T10:00:00Z"
}
```

## Trend Aggregation Targets

- Coder self-review accuracy trend (MAE and risk-level match rate).
- Average rounds by `work_type`.
- High-frequency `definition_mismatch` tags (for rubric iteration).
