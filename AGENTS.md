# AGENTS.md

This repository is documentation-first. The `Main Agent` runs in your CLI session and follows this protocol.

## Purpose

Coordinate `Coder` and `Reviewer` sub-agents to complete a coding task with a controlled review loop.

## Core Roles

- `Main Agent`
  - Owns task lifecycle and final decisions.
  - Delegates implementation and review work.
  - Enforces retry and escalation policy.
- `Coder`
  - Produces implementation patch and self-check report.
- `Reviewer`
  - Produces structured review decision (`pass` / `pass_with_suggestions` / `block`) and issue lists.

## Execution Protocol

1. Build `TaskContract` from user request.
2. Set `work_type` and attach `review_rubric` with selected weight profile for this round.
3. Send contract to `Coder`.
4. Validate coder output schema, including `self_review`.
5. Send coder output + contract to `Reviewer`.
6. Reviewer scores with the same rubric/weights and returns alignment delta.
7. Route to risk-based decision mode (`auto_approve` / `human_optional` / `human_required`).
8. Record final decision (`auto_approve`, `approve`, or `reject`) with decision source.
9. Stop and escalate when task-specific retry budget is reached.

## Rework Protocol (After Reject)

When a round is rejected, `Main Agent` must build a rework packet and pass it to `Coder` in the next round.

Rework packet minimum content:

- Previous `review_result` (full structured object)
- Previous `decision_record` comment (if any)
- Blocking issue IDs and required fixes
- Previous round artifact references (`coder_output`, `review_result`)

`Coder` must read this packet and explicitly address blocking issues before adding new changes.

## State Machine

`created -> assigned -> in_progress -> submitted -> under_review`

Approve path:

`under_review -> approved -> merged -> closed`

Reject/rework path:

`under_review -> changes_requested -> assigned`

Escalation path:

`changes_requested -> blocked -> escalated_to_main`

## Policy

- `auto_approve` is valid only when reviewer verdict is `pass`.
- `approve` is valid when reviewer verdict is `pass` or `pass_with_suggestions`.
- `reject` always increments `retry_count`.
- Base constraints are immutable across retries.
- Retry rounds add `rework_constraints` on top of base constraints.
- Reviewer and Coder must use the same `review_rubric` version in each round.
- Reviewer and Coder must use the same `active_weight_profile` in each round.
- `approval_policy` defines thresholds and SLA for decision modes.
- `retry_policy` defines task-specific retry budget.
- On budget reached: mark `escalated_to_main` and execute escalation playbook.

## Review Thresholds

- `quality_score` is weighted by `review_rubric.active_weight_profile`.
- `block`: any blocking issue or `quality_score < 60`.
- `pass_with_suggestions`: no blockers and (`60 <= quality_score < 85` or advisory issues exist).
- `pass`: no blockers, `quality_score >= 85`, and no follow-up-required advisory issues.
- `Main Agent` should record advisory follow-ups when verdict is `pass_with_suggestions`.

## Weight Profile Policy

- Weight profile must be explicit and auditable in each task.
- Profile should be selected by `work_type`:
  - `new_feature`: prioritize `goal_coverage`
  - `refactor`: prioritize `regression_risk`
  - `bugfix`: prioritize `correctness`
- If `work_type` is unclear, use `balanced` and record rationale.

## Decision Gate Modes

- `auto_approve`:
  - reviewer verdict is `pass`
  - `risk_level == low`
  - `quality_score >= 90`
  - no `block_issues`
- `human_optional`:
  - reviewer verdict is `pass_with_suggestions`, or
  - reviewer verdict is `pass` with medium-risk or follow-up advisory items
  - can auto-approve after SLA timeout if no human rejection arrives
- `human_required`:
  - reviewer verdict is `block`, or
  - `risk_level == high`, or
  - policy/regulatory rule requires explicit human sign-off

## Retry Budget Policy

- Use adaptive retry budget instead of fixed global `max_rework_rounds`.
- Default mapping:
  - `complexity_level = low` -> `max_rework_rounds = 1`
  - `complexity_level = medium` -> `max_rework_rounds = 2`
  - `complexity_level = high` -> `max_rework_rounds = 3`
  - `complexity_level = critical` -> `max_rework_rounds = 4`
- `Main Agent` may adjust budget by `+/-1` only with explicit `override_reason`.
- Retry budget must be frozen once `retry_count > 0` unless escalation owner approves a change.

## Escalation Operations

When retry budget is exhausted, `Main Agent` must run these actions:

1. Freeze task in `escalated_to_main` and stop auto retries.
2. Build escalation package:
   - unresolved `block_issues`
   - summary of attempted fixes by round
   - latest `review_result`, `decision_record`, and diff references
3. Route package to escalation owner (`tech_lead` or `senior_reviewer`).
4. Escalation owner must choose one action:
   - `split_task`: break into smaller child tasks
   - `adjust_constraints`: clarify or relax conflicting constraints
   - `change_owner`: assign stronger coder/reviewer pair
   - `extend_retry_budget`: grant additional rounds with written rationale
5. Record selected action and rationale before any further task state change.

## Required Artifacts

For each round, persist:

- `task_contract`
- `coder_output`
- `review_result`
- `decision_record`
- `decision_summary`

For each finalized task (`closed` or `escalated_to_main`), persist:

- `metrics_snapshot`

## Document Index

- `docs/TASK_CONTRACT.md`
- `docs/roles/coder.md`
- `docs/roles/reviewer.md`
- `docs/RUNBOOK.md`
- `docs/ANALYTICS.md`
- `docs/MODES.md`
- `docs/ARTIFACT_STORAGE.md`
- `docs/SCHEMA_VALIDATION.md`
- `docs/prompts/main_agent.system.md`
- `docs/prompts/coder.prompt.md`
- `docs/prompts/reviewer.prompt.md`
- `examples/full-run/`
