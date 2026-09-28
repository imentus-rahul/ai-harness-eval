"""Prepare workspace and persist trial artifacts."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .config import CANDIDATE_GOOD


def copy_task_repo(task_dir: Path, dest: Path) -> None:
    repo = task_dir / "repo"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(repo, dest)


def copy_guidance(
    project_root: Path,
    harness: str,
    workspace: Path,
    *,
    candidate_id: str = CANDIDATE_GOOD,
) -> str:
    if harness == "baseline":
        path = project_root / "harnesses" / "baseline" / "AGENTS.md"
        text = path.read_text(encoding="utf-8")
        (workspace / "AGENTS.md").write_text(text, encoding="utf-8")
        return text
    path = project_root / "harnesses" / candidate_id / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    (workspace / "SKILL.md").write_text(text, encoding="utf-8")
    return text


def write_trial_artifacts(trial_dir: Path, transcript: dict[str, Any], grade: dict[str, Any]) -> None:
    trial_dir.mkdir(parents=True, exist_ok=True)
    (trial_dir / "transcript.json").write_text(
        json.dumps(transcript, indent=2), encoding="utf-8"
    )
    (trial_dir / "grade.json").write_text(json.dumps(grade, indent=2), encoding="utf-8")

    cost_dir = trial_dir / "cost"
    cost_dir.mkdir(exist_ok=True)
    (cost_dir / "usage.json").write_text(
        json.dumps(
            {
                "tokens": transcript.get("tokens"),
                "cost_usd": transcript.get("cost_usd"),
                "cost_source": transcript.get("cost_source"),
                "latency_s": transcript.get("latency_s"),
                "ttft_ms": transcript.get("ttft_ms"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    tools_dir = trial_dir / "tools"
    tools_dir.mkdir(exist_ok=True)
    (tools_dir / "trace.json").write_text(
        json.dumps(transcript.get("tool_trace", []), indent=2), encoding="utf-8"
    )

    errors_dir = trial_dir / "errors"
    errors_dir.mkdir(exist_ok=True)
    errs = transcript.get("errors") or []
    if errs:
        (errors_dir / "execution.log").write_text("\n".join(errs), encoding="utf-8")
    else:
        (errors_dir / "execution.log").write_text("none\n", encoding="utf-8")

    result_dir = trial_dir / "result"
    result_dir.mkdir(exist_ok=True)
    findings = transcript.get("findings_text", "")
    if findings:
        (result_dir / "findings.json").write_text(findings, encoding="utf-8")
