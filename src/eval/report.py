"""Write comparison READMEs and phase summaries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_harness_readme(
    harness_dir: Path,
    harness: str,
    trials: list[dict[str, Any]],
) -> None:
    lines = [
        f"# {harness} execution",
        "",
        "What ran: paired trials for each task in this phase.",
        "",
        "| task | rep | pass | cost_usd | latency_s |",
        "|------|-----|------|----------|-----------|",
    ]
    for t in trials:
        lines.append(
            f"| {t['task_id']} | {t['rep']} | {t['pass']} | {t.get('cost_usd', 'n/a')} | {t.get('latency_s', 'n/a')} |"
        )
    lines.append("")
    lines.append("Artifacts: each trial has result/, cost/, tools/, errors/, transcript.json.")
    harness_dir.mkdir(parents=True, exist_ok=True)
    (harness_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def write_comparison_readme(phase_dir: Path, summary: dict[str, Any], comparisons: list[dict[str, Any]]) -> None:
    comp_dir = phase_dir / "comparison"
    comp_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Comparison",
        "",
        f"Verdict: **{summary.get('verdict')}**",
        "",
        f"Improved: {summary.get('improved')}, regressed: {summary.get('regressed')}, unstable: {summary.get('unstable')}",
        "",
        "| task | suite | baseline | candidate | transition |",
        "|------|-------|----------|-----------|------------|",
    ]
    for c in comparisons:
        lines.append(
            f"| {c['task_id']} | {c['suite']} | {c['baseline_outcome']} | {c['candidate_outcome']} | {c['transition']} |"
        )
    lines.append("")
    (comp_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    (comp_dir / "result.json").write_text(
        json.dumps({"summary": summary, "comparisons": comparisons}, indent=2),
        encoding="utf-8",
    )


def write_human_spot_check(
    project_root: Path,
    phase_dir: Path,
    example_name: str,
) -> None:
    rel = phase_dir.relative_to(project_root)
    text = f"""# Human spot-check (capability transcripts)

Review `{rel}/candidate/trials/auth-vs-log/*/result/findings.json` ({example_name}).

| question | Y/N | notes |
|----------|-----|-------|
| withdraw flagged as auth bug? | | |
| logTransfer not flagged as vuln? | | |
| explanation mentions logging vs auth? | | |

Fill this after reading transcripts; human grades calibrate model rubrics.
"""
    spot = project_root / "output" / example_name / "human_spot_check.md"
    spot.parent.mkdir(parents=True, exist_ok=True)
    spot.write_text(text, encoding="utf-8")
