# Main Agent Runbook

See `docs/DISPATCH.md` for how to implement “Invoke Coder/Reviewer” (prompt assembly, context isolation, and I/O contracts).

## 0) Inputs

- User goal
- Constraints
- Optional file hints/context

## 1) Create Task

- Build a `TaskContract`
- Set `work_type` (`new_feature|refactor|bugfix|other`)
- Define and attach `review_rubric` (shared by Coder and Reviewer)
- Select `review_rubric.active_weight_profile` from `work_type`
- Define and attach `approval_policy` (risk-based decision mode + SLA)
- Assess task complexity and set `retry_policy.max_rework_rounds`:
  - `low -> 1`, `medium -> 2`, `high -> 3`, `critical -> 4`
- If override is needed, set `retry_policy.override_reason`
- Initialize status: `created -> assigned`

## 2) Coding Round

- Move status: `assigned -> in_progress`
- If `retry_count > 0`, attach a rework packet to the new task input.
- Invoke `Coder`
- Validate coder output schema (must include `self_review`)
- Save artifact: `coder_output`
- Move status: `in_progress -> submitted -> under_review`

## 3) Review Round

- Invoke `Reviewer`
- Validate review output schema
- Validate `weight_profile_used == review_rubric.active_weight_profile`
- Validate weighted score formula and `weighted_score_breakdown`
- Validate `alignment` section against coder self-review
- Save artifact: `review_result`

## 4) Risk-Based Decision Gate

- Determine decision mode from `review_result` + `approval_policy`:
  - `auto_approve`
  - `human_optional`
  - `human_required`
- Record decision source:
  - `system` for auto decisions
  - `human` for manual decisions
- Save artifact: `decision_record`

## 5) State Transition by Decision

### auto_approve

- Precondition: reviewer verdict must be `pass`
- Transition: `under_review -> approved -> merged -> closed`

### approve

- Precondition: reviewer verdict must be `pass` or `pass_with_suggestions`
- Transition: `under_review -> approved -> merged -> closed`

### reject

- Increment `retry_count`
- Build rework packet for next round:
  - Include previous `review_result` and `decision_record`
  - Extract all `block_issues` into mandatory fix targets
  - Add retry-only `rework_constraints`
- Transition: `under_review -> changes_requested -> assigned`
- If `retry_count >= retry_policy.max_rework_rounds`:
  - `changes_requested -> blocked -> escalated_to_main`

## 6) Human Optional SLA

- If mode is `human_optional`, open a decision window (for example, 15 minutes).
- If no human `reject` arrives before timeout, execute `auto_approve`.
- If human `reject` arrives in time, execute `reject`.

## 7) Escalation Playbook

When state reaches `escalated_to_main`, execute all steps:

1. Freeze automatic retries and mark escalation timestamp.
2. Build escalation package:
   - unresolved `block_issues`
   - per-round attempt summary
   - latest `review_result` and `decision_record`
3. Route package to `retry_policy.escalation_owner`.
4. Escalation owner selects one action:
   - `split_task`
   - `adjust_constraints`
   - `change_owner`
   - `extend_retry_budget`
5. Record selected action + rationale before resuming workflow.

## 8) Trend Metrics Update

After task is `closed` or `escalated_to_main`:

1. Compute and persist metrics snapshot:
   - coder self-review accuracy (`quality_score_mae`, `risk_level_match_rate`)
   - `round_count`
   - `work_type`
   - `definition_mismatch_count` and top mismatch tags
2. Append snapshot to analytics store.
3. Update rolling dashboards:
   - average rounds by `work_type`
   - recent mismatch hotspots
4. If mismatch hotspots exceed threshold, schedule rubric update.

## 9) Stop Conditions

- Closed successfully
- Escalated after retry limit
- Manual stop by user

## 10) Failure Handling

- If coder/reviewer output schema is invalid: mark round failed and request regeneration.
- If required artifact missing: do not progress state.
- If conflict between artifacts and state: state machine rules take precedence.
- If retry round has no rework packet: stop and regenerate task input before calling `Coder`.
- If `review_rubric` is missing or mismatched between Coder and Reviewer: stop the round and re-run with aligned rubric version.
- If weight profile is missing, mismatched, or does not sum to `1.0`: stop the round and regenerate review input.
- If mode is `human_required` and human response exceeds SLA, escalate to `escalated_to_main`.
- If retry budget extension is requested, require explicit escalation-owner rationale.
