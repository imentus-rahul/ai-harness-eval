"""Phase 2 eligibility after phase 1 comparison."""

from __future__ import annotations

from typing import Any


def phase2_blocked_reason(
    comparisons: list[dict[str, Any]],
    promoted: list[str],
) -> str | None:
    for row in comparisons:
        if row.get("transition") == "REGRESSED":
            return f"regression task {row['task_id']} regressed (PASS→FAIL)"
        suite = row.get("suite", "")
        if suite == "regression" and row.get("candidate_outcome") == "FAIL":
            return f"regression task {row['task_id']} candidate failed"
    if not promoted:
        return "capability graduation gate not met (candidate did not pass all capability reps)"
    return None


def phase2_eligible(
    comparisons: list[dict[str, Any]],
    promoted: list[str],
) -> bool:
    return phase2_blocked_reason(comparisons, promoted) is None
