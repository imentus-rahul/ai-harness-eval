"""Paired harness comparison per task."""

from __future__ import annotations

from typing import Any


def outcome_from_reps(passes: list[bool]) -> str:
    if not passes:
        return "UNMEASURED"
    if all(passes):
        return "PASS"
    if not any(passes):
        return "FAIL"
    return "UNSTABLE"


def transition(baseline: str, candidate: str) -> str:
    if baseline == "UNSTABLE" or candidate == "UNSTABLE":
        return "UNSTABLE"
    if baseline == "FAIL" and candidate == "PASS":
        return "IMPROVED"
    if baseline == "PASS" and candidate == "FAIL":
        return "REGRESSED"
    if baseline == candidate:
        return "UNCHANGED"
    return "MIXED"


def compare_task(
    task_id: str,
    baseline_passes: list[bool],
    candidate_passes: list[bool],
    suite: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    b_out = outcome_from_reps(baseline_passes)
    c_out = outcome_from_reps(candidate_passes)
    return {
        "task_id": task_id,
        "suite": suite,
        "baseline_outcome": b_out,
        "candidate_outcome": c_out,
        "transition": transition(b_out, c_out),
        "baseline_passes": baseline_passes,
        "candidate_passes": candidate_passes,
        **(extra or {}),
    }


def summarise(comparisons: list[dict[str, Any]]) -> dict[str, Any]:
    improved = sum(1 for c in comparisons if c["transition"] == "IMPROVED")
    regressed = sum(1 for c in comparisons if c["transition"] == "REGRESSED")
    unstable = sum(1 for c in comparisons if c["transition"] == "UNSTABLE")
    if regressed > 0:
        verdict = "NEGATIVE"
    elif improved > 0 and regressed == 0:
        verdict = "POSITIVE"
    else:
        verdict = "INCONCLUSIVE"
    return {
        "verdict": verdict,
        "improved": improved,
        "regressed": regressed,
        "unstable": unstable,
        "task_count": len(comparisons),
    }


def pass_hat_k(n: int, successes: int, k: int) -> float:
    if n < k or successes < k:
        return 0.0
    return 1.0
