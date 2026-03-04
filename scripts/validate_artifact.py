#!/usr/bin/env python3
"""Validate workflow artifacts against JSON Schema files.

Examples:
  python scripts/validate_artifact.py \
    --schema schemas/review_result.schema.json \
    --input examples/full-run/T-202603040001/round-1/review_result.json

  python scripts/validate_artifact.py --examples
  python scripts/validate_artifact.py --examples --strict
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Optional


DEFAULT_EXAMPLE_PAIRS: list[tuple[str, str]] = [
    ("schemas/task_contract.schema.json", "examples/full-run/T-202603040001/task_contract.initial.json"),
    ("schemas/coder_output.schema.json", "examples/full-run/T-202603040001/round-1/coder_output.json"),
    ("schemas/review_result.schema.json", "examples/full-run/T-202603040001/round-1/review_result.json"),
    ("schemas/decision_record.schema.json", "examples/full-run/T-202603040001/round-1/decision_record.json"),
    ("schemas/task_contract.schema.json", "examples/full-run/T-202603040001/round-2/task_contract.json"),
    ("schemas/coder_output.schema.json", "examples/full-run/T-202603040001/round-2/coder_output.json"),
    ("schemas/review_result.schema.json", "examples/full-run/T-202603040001/round-2/review_result.json"),
    ("schemas/decision_record.schema.json", "examples/full-run/T-202603040001/round-2/decision_record.json"),
    ("schemas/metrics_snapshot.schema.json", "examples/full-run/T-202603040001/metrics_snapshot.json"),
]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _isclose(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) <= tol


def _sum_breakdown(breakdown: dict[str, Any]) -> float:
    return float(
        breakdown["goal_coverage"]
        + breakdown["constraint_compliance"]
        + breakdown["correctness"]
        + breakdown["regression_risk"]
        + breakdown["test_confidence"]
    )


def _strict_validate_task_contract(task_contract: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    rubric = task_contract.get("review_rubric", {})
    profiles = rubric.get("weight_profiles", {})
    mapping = rubric.get("weight_profile_by_work_type", {})
    active = rubric.get("active_weight_profile")

    if not isinstance(profiles, dict) or not profiles:
        return ["task_contract.review_rubric.weight_profiles missing/empty"]

    if not isinstance(active, str) or active not in profiles:
        errs.append(f"task_contract.review_rubric.active_weight_profile not found in weight_profiles: {active!r}")

    if isinstance(mapping, dict):
        for k, v in mapping.items():
            if isinstance(v, str) and v not in profiles:
                errs.append(f"task_contract.review_rubric.weight_profile_by_work_type.{k} references missing profile: {v!r}")

    for name, weights in profiles.items():
        if not isinstance(weights, dict):
            errs.append(f"task_contract.review_rubric.weight_profiles.{name} must be an object")
            continue
        total = 0.0
        for dim in ("goal_coverage", "constraint_compliance", "correctness", "regression_risk", "test_confidence"):
            w = weights.get(dim)
            if not isinstance(w, (int, float)):
                errs.append(f"task_contract.review_rubric.weight_profiles.{name}.{dim} missing/not number")
                continue
            total += float(w)
        if not _isclose(total, 1.0, tol=1e-6):
            errs.append(f"task_contract.review_rubric.weight_profiles.{name} weights must sum to 1.0, got {total}")

    return errs


def _strict_validate_review_result(
    *,
    task_contract: Optional[dict[str, Any]],
    coder_output: Optional[dict[str, Any]],
    review_result: dict[str, Any],
) -> list[str]:
    errs: list[str] = []

    # Always check internal math consistency that does not require a contract.
    breakdown = review_result.get("weighted_score_breakdown")
    if not isinstance(breakdown, dict):
        return ["review_result.weighted_score_breakdown missing/not object"]

    try:
        breakdown_sum = _sum_breakdown(breakdown)
    except Exception:
        return ["review_result.weighted_score_breakdown missing required dimensions"]

    quality_score = review_result.get("quality_score")
    if not isinstance(quality_score, int):
        errs.append("review_result.quality_score must be an integer")
    else:
        expected = int(round(breakdown_sum))
        if quality_score != expected:
            errs.append(f"review_result.quality_score must equal round(sum(weighted_score_breakdown)) ({expected}), got {quality_score}")

    # The remaining checks depend on task_contract.
    if task_contract is None:
        return errs

    rubric = task_contract.get("review_rubric", {})
    profiles = rubric.get("weight_profiles", {})
    active = rubric.get("active_weight_profile")
    block_threshold = rubric.get("block_threshold")
    pass_threshold = rubric.get("pass_threshold")

    if not isinstance(active, str) or not isinstance(profiles, dict) or active not in profiles:
        errs.append("task_contract.review_rubric.active_weight_profile missing or not present in weight_profiles")
        return errs

    if review_result.get("weight_profile_used") != active:
        errs.append(
            "review_result.weight_profile_used must equal task_contract.review_rubric.active_weight_profile "
            f"({active!r}), got {review_result.get('weight_profile_used')!r}"
        )

    weights = profiles[active]
    scorecard = review_result.get("scorecard")
    if not isinstance(scorecard, dict):
        errs.append("review_result.scorecard missing/not object")
        return errs

    for dim in ("goal_coverage", "constraint_compliance", "correctness", "regression_risk", "test_confidence"):
        s = scorecard.get(dim)
        w = weights.get(dim) if isinstance(weights, dict) else None
        if not isinstance(s, int) or s < 0 or s > 2:
            errs.append(f"review_result.scorecard.{dim} must be int in 0..2, got {s!r}")
            continue
        if not isinstance(w, (int, float)):
            errs.append(f"task_contract.review_rubric.weight_profiles.{active}.{dim} missing/not number")
            continue

        expected_points = 100.0 * float(w) * (float(s) / 2.0)
        actual_points = breakdown.get(dim)
        if not isinstance(actual_points, (int, float)):
            errs.append(f"review_result.weighted_score_breakdown.{dim} missing/not number")
            continue
        if not _isclose(float(actual_points), expected_points, tol=1e-6):
            errs.append(
                f"review_result.weighted_score_breakdown.{dim} must equal 100*weight*score/2 ({expected_points}), got {actual_points}"
            )

    # Verdict sanity checks.
    verdict = review_result.get("verdict")
    block_issues = review_result.get("block_issues")
    if isinstance(block_issues, list) and block_issues and verdict != "block":
        errs.append("review_result.verdict must be 'block' when block_issues is non-empty")
    if verdict != "block":
        if scorecard.get("constraint_compliance") == 0:
            errs.append("review_result.verdict must be 'block' when scorecard.constraint_compliance == 0")
        if scorecard.get("correctness") == 0:
            errs.append("review_result.verdict must be 'block' when scorecard.correctness == 0")
    if isinstance(quality_score, int):
        if isinstance(block_threshold, int) and quality_score < block_threshold and verdict != "block":
            errs.append("review_result.verdict must be 'block' when quality_score < block_threshold")
        if verdict == "pass" and isinstance(pass_threshold, int) and quality_score < pass_threshold:
            errs.append("review_result.verdict cannot be 'pass' when quality_score < pass_threshold")

    # Alignment checks require coder_output.
    if coder_output is None:
        return errs

    coder_self = coder_output.get("self_review", {})
    coder_est = coder_self.get("quality_score_estimate")
    coder_scorecard = coder_self.get("scorecard_estimate", {})
    alignment = review_result.get("alignment", {}).get("coder_self_review_delta", {})
    if isinstance(quality_score, int) and isinstance(coder_est, int):
        expected_diff = quality_score - coder_est
        if alignment.get("quality_score_diff") != expected_diff:
            errs.append(
                f"alignment.coder_self_review_delta.quality_score_diff must be {expected_diff}, got {alignment.get('quality_score_diff')!r}"
            )
    if isinstance(scorecard, dict) and isinstance(coder_scorecard, dict):
        rc = scorecard.get("correctness")
        cc = coder_scorecard.get("correctness")
        if isinstance(rc, int) and isinstance(cc, int):
            expected_cd = rc - cc
            if alignment.get("correctness_diff") != expected_cd:
                errs.append(
                    f"alignment.coder_self_review_delta.correctness_diff must be {expected_cd}, got {alignment.get('correctness_diff')!r}"
                )

    return errs


def _strict_validate_decision_record(
    *,
    review_result: Optional[dict[str, Any]],
    decision_record: dict[str, Any],
) -> list[str]:
    if review_result is None:
        return []

    verdict = review_result.get("verdict")
    action = decision_record.get("action")
    errs: list[str] = []

    if verdict == "block" and action == "approve":
        errs.append("decision_record.action cannot be 'approve' when review_result.verdict is 'block'")
    if verdict in ("pass", "pass_with_suggestions") and action == "reject":
        errs.append("decision_record.action cannot be 'reject' when review_result.verdict is pass-like")

    return errs


def _strict_validate_metrics_snapshot(
    *,
    task_contract: dict[str, Any],
    rounds: list[tuple[dict[str, Any], dict[str, Any]]],  # (coder_output, review_result)
    metrics_snapshot: dict[str, Any],
) -> list[str]:
    errs: list[str] = []

    task_id = task_contract.get("task_id")
    if metrics_snapshot.get("task_id") != task_id:
        errs.append(f"metrics_snapshot.task_id must match task_contract.task_id ({task_id!r})")

    if metrics_snapshot.get("round_count") != len(rounds):
        errs.append(f"metrics_snapshot.round_count must be {len(rounds)}, got {metrics_snapshot.get('round_count')!r}")

    diffs: list[float] = []
    risk_matches = 0
    mismatch_count = 0
    for coder_output, review_result in rounds:
        coder_self = coder_output.get("self_review", {})
        coder_est = coder_self.get("quality_score_estimate")
        review_score = review_result.get("quality_score")
        if isinstance(coder_est, int) and isinstance(review_score, int):
            diffs.append(abs(float(review_score - coder_est)))
        if coder_self.get("risk_level_estimate") == review_result.get("risk_level"):
            risk_matches += 1
        mismatch = review_result.get("alignment", {}).get("definition_mismatch", [])
        if isinstance(mismatch, list):
            mismatch_count += len(mismatch)

    if diffs:
        expected_mae = sum(diffs) / float(len(diffs))
        actual_mae = metrics_snapshot.get("quality_score_mae")
        if not isinstance(actual_mae, (int, float)) or not _isclose(float(actual_mae), expected_mae, tol=1e-6):
            errs.append(f"metrics_snapshot.quality_score_mae must be {expected_mae}, got {actual_mae!r}")

    if rounds:
        expected_rate = float(risk_matches) / float(len(rounds))
        actual_rate = metrics_snapshot.get("risk_level_match_rate")
        if not isinstance(actual_rate, (int, float)) or not _isclose(float(actual_rate), expected_rate, tol=1e-6):
            errs.append(f"metrics_snapshot.risk_level_match_rate must be {expected_rate}, got {actual_rate!r}")

    if metrics_snapshot.get("definition_mismatch_count") != mismatch_count:
        errs.append(
            f"metrics_snapshot.definition_mismatch_count must be {mismatch_count}, got {metrics_snapshot.get('definition_mismatch_count')!r}"
        )

    return errs


def _validate(schema_path: Path, input_path: Path) -> tuple[bool, str]:
    try:
        from jsonschema import Draft202012Validator  # type: ignore
    except Exception:
        return (
            False,
            "Missing dependency `jsonschema`. Install with: pip install jsonschema",
        )

    schema = _load_json(schema_path)
    payload = _load_json(input_path)

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
    if not errors:
        return True, "ok"

    first = errors[0]
    path = ".".join(str(p) for p in first.path) or "<root>"
    return False, f"{path}: {first.message}"


def _run_pair(schema: str, input_file: str) -> int:
    schema_path = Path(schema)
    input_path = Path(input_file)
    if not schema_path.exists():
        print(f"FAIL {input_file}: schema not found: {schema_path}")
        return 1
    if not input_path.exists():
        print(f"FAIL {input_file}: input not found: {input_path}")
        return 1

    ok, msg = _validate(schema_path, input_path)
    status = "PASS" if ok else "FAIL"
    print(f"{status} {input_path} <- {schema_path} :: {msg}")
    return 0 if ok else 1


def _run_examples_strict() -> int:
    """Semantic validation for example runs (cross-file checks)."""
    base = Path("examples/full-run")
    if not base.exists():
        print("STRICT FAIL examples: examples/full-run not found")
        return 1

    code = 0
    for task_dir in sorted(p for p in base.iterdir() if p.is_dir() and p.name.startswith("T-")):
        initial_contract_path = task_dir / "task_contract.initial.json"
        if not initial_contract_path.exists():
            print(f"STRICT FAIL {task_dir}: missing task_contract.initial.json")
            code |= 1
            continue

        initial_contract = _load_json(initial_contract_path)
        tc_errs = _strict_validate_task_contract(initial_contract)
        if tc_errs:
            code |= 1
            print(f"STRICT FAIL {initial_contract_path}: " + "; ".join(tc_errs))
        else:
            print(f"STRICT PASS {initial_contract_path}: ok")

        rounds: list[tuple[int, Path]] = []
        for p in task_dir.iterdir():
            if p.is_dir() and p.name.startswith("round-"):
                try:
                    n = int(p.name.split("-", 1)[1])
                except Exception:
                    continue
                rounds.append((n, p))
        rounds.sort()

        round_pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
        last_contract = initial_contract
        for n, round_dir in rounds:
            contract_path = round_dir / "task_contract.json"
            if contract_path.exists():
                last_contract = _load_json(contract_path)
                tc_errs = _strict_validate_task_contract(last_contract)
                if tc_errs:
                    code |= 1
                    print(f"STRICT FAIL {contract_path}: " + "; ".join(tc_errs))
                else:
                    print(f"STRICT PASS {contract_path}: ok")

            coder_path = round_dir / "coder_output.json"
            review_path = round_dir / "review_result.json"
            decision_path = round_dir / "decision_record.json"
            if not coder_path.exists() or not review_path.exists() or not decision_path.exists():
                code |= 1
                print(f"STRICT FAIL {round_dir}: missing one of coder_output.json/review_result.json/decision_record.json")
                continue

            coder = _load_json(coder_path)
            review = _load_json(review_path)
            decision = _load_json(decision_path)
            rr_errs = _strict_validate_review_result(task_contract=last_contract, coder_output=coder, review_result=review)
            if rr_errs:
                code |= 1
                print(f"STRICT FAIL {review_path}: " + "; ".join(rr_errs))
            else:
                print(f"STRICT PASS {review_path}: ok")

            dr_errs = _strict_validate_decision_record(review_result=review, decision_record=decision)
            if dr_errs:
                code |= 1
                print(f"STRICT FAIL {decision_path}: " + "; ".join(dr_errs))
            else:
                print(f"STRICT PASS {decision_path}: ok")

            round_pairs.append((coder, review))

        metrics_path = task_dir / "metrics_snapshot.json"
        if metrics_path.exists():
            metrics = _load_json(metrics_path)
            ms_errs = _strict_validate_metrics_snapshot(
                task_contract=initial_contract,
                rounds=round_pairs,
                metrics_snapshot=metrics,
            )
            if ms_errs:
                code |= 1
                print(f"STRICT FAIL {metrics_path}: " + "; ".join(ms_errs))
            else:
                print(f"STRICT PASS {metrics_path}: ok")

    return code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", help="Path to schema file")
    parser.add_argument("--input", help="Path to input JSON")
    parser.add_argument(
        "--examples",
        action="store_true",
        help="Validate all built-in example artifacts",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable semantic validation (cross-field / cross-file checks)",
    )
    parser.add_argument(
        "--task-contract",
        help="Optional TaskContract JSON path (enables deeper semantic checks for single-file validation)",
    )
    parser.add_argument(
        "--coder-output",
        help="Optional Coder output JSON path (enables alignment checks for review_result validation)",
    )
    args = parser.parse_args()

    if args.examples:
        code = 0
        for schema, input_file in DEFAULT_EXAMPLE_PAIRS:
            code |= _run_pair(schema, input_file)
        if args.strict:
            code |= _run_examples_strict()
        return code

    if not args.schema or not args.input:
        parser.error("Either use --examples or provide both --schema and --input")

    code = _run_pair(args.schema, args.input)
    if not args.strict:
        return code

    schema_name = Path(args.schema).name
    input_payload = _load_json(Path(args.input))
    task_contract = _load_json(Path(args.task_contract)) if args.task_contract else None
    coder_output = _load_json(Path(args.coder_output)) if args.coder_output else None

    strict_errs: list[str] = []
    if schema_name == "task_contract.schema.json":
        strict_errs = _strict_validate_task_contract(input_payload)
    elif schema_name == "review_result.schema.json":
        strict_errs = _strict_validate_review_result(
            task_contract=task_contract,
            coder_output=coder_output,
            review_result=input_payload,
        )

    if strict_errs:
        print(f"STRICT FAIL {args.input}: " + "; ".join(strict_errs))
        return code | 1
    if schema_name in ("task_contract.schema.json", "review_result.schema.json"):
        print(f"STRICT PASS {args.input}: ok")
    return code


if __name__ == "__main__":
    sys.exit(main())
