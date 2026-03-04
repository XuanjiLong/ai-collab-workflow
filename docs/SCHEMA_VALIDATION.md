# Schema Validation

## Goal

Validate artifact JSON files before state transitions.

## Prerequisite

```bash
pip install -r requirements.txt
# or: pip install jsonschema
```

## Validate One File

```bash
python scripts/validate_artifact.py \
  --schema schemas/review_result.schema.json \
  --input examples/full-run/T-202603040001/round-1/review_result.json
```

## Validate All Example Artifacts

```bash
python scripts/validate_artifact.py --examples
# with semantic checks (math + cross-file consistency)
python scripts/validate_artifact.py --examples --strict
# or
./scripts/validate_examples.sh
```

## Strict Mode (Semantic Validation)

Strict mode adds semantic checks on top of JSON Schema (for example, score math consistency and alignment deltas).

Validate one `review_result` with full context:

```bash
python scripts/validate_artifact.py \
  --schema schemas/review_result.schema.json \
  --input examples/full-run/T-202603040001/round-2/review_result.json \
  --task-contract examples/full-run/T-202603040001/round-2/task_contract.json \
  --coder-output examples/full-run/T-202603040001/round-2/coder_output.json \
  --strict
```

## Schema Files

- `schemas/task_contract.schema.json`
- `schemas/coder_output.schema.json`
- `schemas/review_result.schema.json`
- `schemas/decision_record.schema.json`
- `schemas/metrics_snapshot.schema.json`
