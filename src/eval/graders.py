"""Code and model graders."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .openrouter import rubric_chat

RUBRIC_SYSTEM = """You grade security audit explanations.
Reply with exactly one line: PASS or FAIL, then a short reason.
PASS only if the agent clearly separates authorization bugs from logging-only uses of tx.origin."""


def _load_findings(workspace: Path) -> list[dict[str, Any]]:
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


def _match_function(findings: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for row in findings:
        if (row.get("function") or row.get("id")) == name:
            return row
    return None


def _is_vulnerable(row: dict[str, Any]) -> bool | None:
    if "vulnerable" in row:
        return bool(row.get("vulnerable"))
    label = str(row.get("classification", "")).upper()
    if "NOT" in label and "FINDING" in label:
        return False
    if label in ("VULNERABLE", "TRUE", "YES"):
        return True
    if label in ("SAFE", "FALSE", "NO"):
        return False
    return None


def grade_auth_expected(workspace: Path, expected_path: Path) -> tuple[bool, str]:
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    findings = _load_findings(workspace)
    for req in expected.get("required", []):
        fn = req["function"]
        row = _match_function(findings, fn)
        if row is None:
            return False, f"missing finding for {fn}"
        got = _is_vulnerable(row)
        if got is None:
            return False, f"{fn}: could not read vulnerable/classification"
        if got != bool(req.get("vulnerable")):
            return (
                False,
                f"{fn}: expected vulnerable={req.get('vulnerable')} got {got}",
            )
        issue_contains = req.get("issue_contains")
        if issue_contains:
            blob = json.dumps(row).lower()
            if issue_contains.lower() not in blob:
                return False, f"{fn}: expected issue mentioning {issue_contains}"
    return True, "held-out labels match"


def grade_keep_suite(workspace: Path, task_dir: Path) -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return True, "visible regression tests pass"
    return False, (proc.stdout + proc.stderr)[-500:]


def grade_code(task_id: str, workspace: Path, task_dir: Path) -> dict[str, Any]:
    if task_id == "keep-suite":
        ok, reason = grade_keep_suite(workspace, task_dir)
    else:
        expected = task_dir / "heldout" / "expected.json"
        ok, reason = grade_auth_expected(workspace, expected)
    return {"code_pass": ok, "code_reason": reason}


def grade_model_rubric(
    findings_text: str,
    *,
    endpoint: str,
    model: str,
    api_key: str,
    dry_run: bool,
) -> dict[str, Any]:
    if not findings_text.strip():
        return {"model_pass": False, "model_reason": "no findings.json", "model_raw": ""}
    if dry_run:
        parsed = json.loads(findings_text)
        rows = parsed.get("findings") or []
        log_ok = any(
            (r.get("function") == "logTransfer" and r.get("vulnerable") is False)
            for r in rows
        )
        if log_ok:
            return {"model_pass": True, "model_reason": "mock rubric PASS", "model_raw": "PASS"}
        return {"model_pass": False, "model_reason": "mock rubric FAIL", "model_raw": "FAIL"}

    raw, cost, tin, tout = rubric_chat(
        endpoint,
        model,
        api_key,
        RUBRIC_SYSTEM,
        f"findings.json contents:\n{findings_text}",
    )
    passed = raw.upper().startswith("PASS")
    return {
        "model_pass": passed,
        "model_reason": raw[:200],
        "model_raw": raw,
        "model_grade_cost_usd": cost,
        "model_grade_tokens": {"input": tin, "output": tout},
    }


def grade_trial(
    task_id: str,
    task_dir: Path,
    workspace: Path,
    transcript: dict[str, Any],
    *,
    endpoint: str,
    model: str,
    api_key: str,
    dry_run: bool,
    use_model_grader: bool,
) -> dict[str, Any]:
    code = grade_code(task_id, workspace, task_dir)
    out = dict(code)
    if use_model_grader and task_id in ("auth-vs-log", "caller-check"):
        model_grade = grade_model_rubric(
            transcript.get("findings_text", ""),
            endpoint=endpoint,
            model=model,
            api_key=api_key,
            dry_run=dry_run,
        )
        out.update(model_grade)
        out["pass"] = code["code_pass"]
        out["model_disagreement"] = model_grade["model_pass"] != code["code_pass"]
    else:
        out["pass"] = code["code_pass"]
        out["model_disagreement"] = False
    return out
