"""Move capability tasks into the regression suite."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .compare import pass_hat_k


def load_registry(project_root: Path) -> dict[str, Any]:
    path = project_root / "tasks" / "registry.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {"tasks": {}}


def save_registry(project_root: Path, data: dict[str, Any]) -> None:
    path = project_root / "tasks" / "registry.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def tasks_for_suite(registry: dict[str, Any], suite: str) -> list[str]:
    out: list[str] = []
    for task_id, meta in (registry.get("tasks") or {}).items():
        if (meta or {}).get("suite", "capability") == suite:
            out.append(task_id)
    return sorted(out)


def promote_capability_tasks(
    project_root: Path,
    run_id: str,
    capability_results: dict[str, list[bool]],
    min_reps: int,
    dry_run: bool = False,
) -> list[str]:
    promoted: list[str] = []
    reg = load_registry(project_root)
    tasks = reg.setdefault("tasks", {})
    for task_id, passes in capability_results.items():
        if len(passes) < min_reps:
            continue
        k = min(min_reps, len(passes))
        successes = sum(1 for p in passes if p)
        if pass_hat_k(len(passes), successes, k) < 1.0:
            continue
        entry = tasks.get(task_id, {})
        if entry.get("suite") == "regression":
            continue
        promoted.append(task_id)
        if dry_run:
            continue
        entry.update(
            {
                "suite": "regression",
                "graduated_utc": datetime.now(timezone.utc).isoformat(),
                "graduated_from_run": run_id,
            }
        )
        tasks[task_id] = entry
    if promoted and not dry_run:
        save_registry(project_root, reg)
    return promoted
