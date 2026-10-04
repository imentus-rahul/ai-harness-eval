"""Fail-fast debug artifacts when a live trial diverges from expectations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .log_util import error, info


class EvalAbort(RuntimeError):
    """Stop the run immediately; harness or task needs a fix before re-running."""


def write_debug_break(
    project: Path,
    *,
    scenario: str,
    phase_name: str,
    harness: str,
    task_id: str,
    rep: int,
    workspace: Path,
    trial_dir: Path,
    grade: dict[str, Any],
    transcript: dict[str, Any],
    reason: str,
) -> Path:
    findings_path = workspace / "findings.json"
    findings_text = (
        findings_path.read_text(encoding="utf-8")[:4000] if findings_path.is_file() else ""
    )
    payload = {
        "reason": reason,
        "scenario": scenario,
        "phase": phase_name,
        "harness": harness,
        "task_id": task_id,
        "rep": rep,
        "workspace": str(workspace.relative_to(project)),
        "trial_dir": str(trial_dir.relative_to(project)),
        "grade": {
            "pass": grade.get("pass"),
            "code_pass": grade.get("code_pass"),
            "code_reason": grade.get("code_reason"),
            "model_reason": grade.get("model_reason"),
        },
        "agent_errors": transcript.get("errors"),
        "findings_preview": findings_text,
        "hint": (
            "Re-running the same trial without editing harnesses/ or tasks/ will not change "
            "model conclusions. Fix SKILL.md / AGENTS.md / prompt, then re-run."
        ),
    }
    out_dir = project / "output" / "debug-breaks"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = f"{scenario}-{phase_name}-{harness}-{task_id}-rep{rep}".replace("/", "_")
    path = out_dir / f"{stamp}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    error(f"DEBUG BREAK | {reason}")
    info(f"  workspace: {workspace}")
    info(f"  findings.json: {findings_path}")
    info(f"  grader: {grade.get('code_reason') or grade.get('model_reason')}")
    info(f"  debug artifact: {path}")
    return path


def candidate_must_pass(scenario: str, harness: str) -> bool:
    return scenario == "good" and harness == "candidate"
