# Workflow Modes

## Full Mode (Default)

Use when task risk/impact is medium to high.

Features:
- Weighted scorecard
- Risk-based decision gate
- Adaptive retry budget
- Rework packet and escalation playbook
- Trend metrics snapshot

## Lite Mode

Use when task is simple and low-risk (for example, tiny bugfix or naming cleanup).

Simplifications:
- Verdict reduced to `pass|block`
- No weighted profile selection (use fixed `balanced` rubric)
- Decision gate reduced to `auto_approve|human_required`
- Retry budget fixed to `1`

Schema compatibility note:
- Lite Mode is a behavioral simplification. Artifacts should still conform to the same JSON Schemas.
- Fields that become less meaningful in Lite Mode (for example `alignment`) should remain present but can be minimal (zero deltas, empty arrays).

## Selection Guide

Choose Full Mode when any condition holds:
- `work_type` is `refactor`
- multiple files/subsystems are touched
- API behavior or error handling changes
- compliance/safety concerns exist

Choose Lite Mode when all conditions hold:
- single-file, low-risk change
- no API contract impact
- no schema/storage/security changes

## Upgrade Rule

If Lite Mode hits a block once, upgrade task to Full Mode for the next round.
