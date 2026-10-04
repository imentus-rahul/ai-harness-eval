"""Validate findings.json shape against task held-out expectations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_required_functions(task_dir: Path) -> list[str]:
    expected = task_dir / "heldout" / "expected.json"
    if not expected.is_file():
        return []
    data = json.loads(expected.read_text(encoding="utf-8"))
    required = data.get("required") or []
    return [str(r["function"]) for r in required if r.get("function")]


def load_findings_rows(workspace: Path) -> list[dict[str, Any]]:
    path = workspace / "findings.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return data
    findings = data.get("findings")
    return findings if isinstance(findings, list) else []


def findings_schema_ok(workspace: Path, required_functions: list[str]) -> tuple[bool, str]:
    if not required_functions:
        return True, "no schema"
    rows = load_findings_rows(workspace)
    by_fn = {
        (r.get("function") or r.get("id")): r for r in rows if (r.get("function") or r.get("id"))
    }
    for fn in required_functions:
        row = by_fn.get(fn)
        if row is None:
            return False, f"findings.json must include an entry for function `{fn}`"
        if "vulnerable" not in row:
            return False, f"`{fn}` must set vulnerable to true or false (boolean)"
    return True, "schema ok"
