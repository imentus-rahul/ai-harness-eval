"""Minimal tool loop: read, list, write files in the trial workspace."""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any

from .openrouter import ChatResult, chat

TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 text file relative to the workspace root.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files under a directory (non-recursive).",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write UTF-8 text to a path relative to the workspace root.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
]

HAIKU_INPUT_PER_M = 0.80
HAIKU_OUTPUT_PER_M = 4.00


def estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1_000_000) * HAIKU_INPUT_PER_M + (
        output_tokens / 1_000_000
    ) * HAIKU_OUTPUT_PER_M


def run_tool(workspace: Path, name: str, args: dict[str, Any]) -> str:
    rel = args.get("path", ".")
    target = (workspace / rel).resolve()
    if not str(target).startswith(str(workspace.resolve())):
        return "error: path escapes workspace"
    if name == "read_file":
        if not target.is_file():
            return f"error: missing file {rel}"
        return target.read_text(encoding="utf-8")
    if name == "list_files":
        if not target.is_dir():
            return f"error: not a directory {rel}"
        names = sorted(p.name for p in target.iterdir())
        return "\n".join(names) if names else "(empty)"
    if name == "write_file":
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(args.get("content", ""), encoding="utf-8")
        return f"wrote {rel} ({len(args.get('content', ''))} bytes)"
    return f"error: unknown tool {name}"


def run_agent(
    workspace: Path,
    prompt: str,
    guidance: str,
    *,
    endpoint: str,
    model: str,
    api_key: str,
    max_turns: int = 8,
    max_cost_usd: float = 0.05,
) -> dict[str, Any]:
    system = guidance + "\n\nYou must use tools to inspect the repo and write findings.json."
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    tool_trace: list[dict[str, Any]] = []
    errors: list[str] = []
    total_in = 0
    total_out = 0
    total_cost = 0.0
    cost_source = "reported"
    ttft_ms: int | None = None
    started = time.monotonic()

    for _ in range(max_turns):
        try:
            result = chat(endpoint, model, messages, TOOL_SPECS, api_key)
        except RuntimeError as exc:
            errors.append(str(exc))
            break

        total_in += result.input_tokens
        total_out += result.output_tokens
        if result.ttft_ms is not None and ttft_ms is None:
            ttft_ms = result.ttft_ms
        if result.cost_usd is not None:
            total_cost += result.cost_usd
        else:
            total_cost += estimate_cost_usd(result.input_tokens, result.output_tokens)
            cost_source = "computed"

        if total_cost > max_cost_usd:
            errors.append(f"budget exceeded {max_cost_usd:.4f} USD")
            break

        if result.tool_calls:
            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": result.content or None,
                "tool_calls": result.tool_calls,
            }
            messages.append(assistant_msg)
            for tc in result.tool_calls:
                fn = tc.get("function") or {}
                tname = fn.get("name", "")
                try:
                    targs = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    targs = {}
                    errors.append(f"bad tool args for {tname}")
                tool_trace.append({"tool": tname, "arguments": targs})
                output = run_tool(workspace, tname, targs)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.get("id", ""),
                        "content": output,
                    }
                )
            continue

        if result.content:
            messages.append({"role": "assistant", "content": result.content})
        break

    findings_path = workspace / "findings.json"
    findings_text = findings_path.read_text(encoding="utf-8") if findings_path.is_file() else ""

    return {
        "messages": messages,
        "tool_trace": tool_trace,
        "errors": errors,
        "findings_text": findings_text,
        "latency_s": round(time.monotonic() - started, 3),
        "ttft_ms": ttft_ms,
        "tokens": {"input": total_in, "output": total_out, "total": total_in + total_out},
        "cost_usd": round(total_cost, 6),
        "cost_source": cost_source,
    }


def mock_harness_id(harness_arm: str, candidate_id: str) -> str:
    if harness_arm == "baseline":
        return "baseline"
    return candidate_id


def apply_mock_transcript(
    project: Path,
    workspace: Path,
    harness_arm: str,
    task_id: str,
    *,
    candidate_id: str,
) -> dict[str, Any]:
    """Deterministic outcomes for --dry-run from mocks/<harness-id>/<task>/."""
    hid = mock_harness_id(harness_arm, candidate_id)
    mock_dir = project / "mocks" / hid / task_id
    findings_path = mock_dir / "findings.json"
    if findings_path.is_file():
        shutil.copy2(findings_path, workspace / "findings.json")
    else:
        (workspace / "findings.json").write_text(
            json.dumps({"findings": []}, indent=2), encoding="utf-8"
        )

    overlay = mock_dir / "overlay"
    if overlay.is_dir():
        for src in overlay.rglob("*"):
            if src.is_file():
                rel = src.relative_to(overlay)
                dest = workspace / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)

    findings_text = (workspace / "findings.json").read_text(encoding="utf-8")
    return {
        "messages": [],
        "tool_trace": [{"tool": "write_file", "arguments": {"path": "findings.json"}}],
        "errors": [],
        "findings_text": findings_text,
        "latency_s": 0.1,
        "ttft_ms": 50,
        "tokens": {"input": 0, "output": 0, "total": 0},
        "cost_usd": 0.0,
        "cost_source": "mock",
    }
