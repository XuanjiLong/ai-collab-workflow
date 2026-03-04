# Artifact Storage Convention

## Recommended File Layout

```text
.workflow/
  tasks/
    T-202603040001/
      task_contract.initial.json
      round-1/
        coder_output.json
        review_result.json
        decision_record.json
      round-2/
        task_contract.json
        coder_output.json
        review_result.json
        decision_record.json
      metrics_snapshot.json
```

## Naming Rules

- Round directories: `round-<n>` where `<n>` starts at `1`
- One artifact file per type per round
- Use lowercase snake_case filenames

## Minimum Artifacts

Per round:
- `coder_output.json`
- `review_result.json`
- `decision_record.json`

Per task:
- `task_contract.initial.json`
- `metrics_snapshot.json` on final state

## Optional Artifacts

Per round:
- `task_contract.json` when the contract changes (for example to attach a retry `rework` packet)
- `decision_summary.md` for human-readable notes and follow-ups

## Optional Index File

You may add `.workflow/tasks/<task_id>/index.json` to track:
- current state
- latest round
- artifact checksums
- timestamps
