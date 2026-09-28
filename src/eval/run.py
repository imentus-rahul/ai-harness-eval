"""Run phase 1, optional promotion, phase 2."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Any

from .agent import apply_mock_transcript, run_agent
from .compare import compare_task, summarise
from .config import (
    SCENARIO_OUTPUT,
    candidate_id_for_scenario,
    load_eval_config,
    resolve_scenarios,
)
from .gate import phase2_blocked_reason, phase2_eligible
from .graders import grade_trial
from .promote import load_registry, promote_capability_tasks, save_registry, tasks_for_suite
from .report import write_comparison_readme, write_harness_readme, write_human_spot_check
from .trial import copy_guidance, copy_task_repo, write_trial_artifacts

OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "anthropic/claude-haiku-4.5"
REPS = 2
MAX_COST_PER_TRIAL = 0.05
PHASE2_CAPABILITY = "caller-check"


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def reset_registry(project: Path) -> None:
    bootstrap = project / "tasks" / "registry.bootstrap.yaml"
    target = project / "tasks" / "registry.yaml"
    shutil.copy2(bootstrap, target)


def run_one_trial(
    project: Path,
    phase_dir: Path,
    task_id: str,
    harness: str,
    rep: int,
    *,
    api_key: str,
    model: str,
    dry_run: bool,
    candidate_id: str,
) -> dict[str, Any]:
    task_dir = project / "tasks" / task_id
    prompt = (task_dir / "prompt.txt").read_text(encoding="utf-8")
    trial_dir = phase_dir / harness / "trials" / task_id / str(rep)
    workspace_parent = phase_dir / "_workspaces" / harness / task_id / str(rep)
    if workspace_parent.exists():
        shutil.rmtree(workspace_parent)
    workspace_parent.mkdir(parents=True)
    workspace = workspace_parent / "repo"
    copy_task_repo(task_dir, workspace)
    guidance = copy_guidance(project, harness, workspace, candidate_id=candidate_id)

    if dry_run:
        transcript = apply_mock_transcript(
            project,
            workspace,
            harness,
            task_id,
            candidate_id=candidate_id,
        )
    else:
        transcript = run_agent(
            workspace,
            prompt,
            guidance,
            endpoint=OPENROUTER_ENDPOINT,
            model=model,
            api_key=api_key,
            max_turns=8,
            max_cost_usd=MAX_COST_PER_TRIAL,
        )

    use_model = task_id in ("auth-vs-log", "caller-check")
    grade = grade_trial(
        task_id,
        task_dir,
        workspace,
        transcript,
        endpoint=OPENROUTER_ENDPOINT,
        model=model,
        api_key=api_key,
        dry_run=dry_run,
        use_model_grader=use_model,
    )
    write_trial_artifacts(trial_dir, transcript, grade)
    return {
        "task_id": task_id,
        "harness": harness,
        "rep": rep,
        "pass": grade["pass"],
        "cost_usd": transcript.get("cost_usd"),
        "latency_s": transcript.get("latency_s"),
        "grade": grade,
        "trial_dir": str(trial_dir.relative_to(project)),
    }


def run_scenario_fixed(
    project: Path,
    scenario: str,
    *,
    api_key: str,
    model: str,
    dry_run: bool,
) -> dict[str, Any]:
    reset_registry(project)
    config = load_eval_config(project)
    candidate_id = candidate_id_for_scenario(scenario, config)
    example_name = SCENARIO_OUTPUT[scenario]
    out_root = project / "output" / example_name
    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True)

    registry = load_registry(project)
    phase1_tasks = tasks_for_suite(registry, "capability") + tasks_for_suite(
        registry, "regression"
    )
    if not phase1_tasks:
        phase1_tasks = ["auth-vs-log", "keep-suite"]

    comparisons1, summary1 = run_phase_under(
        project,
        out_root / "phase-1",
        phase1_tasks,
        registry,
        api_key=api_key,
        model=model,
        dry_run=dry_run,
        candidate_id=candidate_id,
    )

    capability_results: dict[str, list[bool]] = {}
    for c in comparisons1:
        if c["suite"] != "capability":
            continue
        capability_results[c["task_id"]] = c["candidate_passes"]

    promoted = promote_capability_tasks(
        project,
        f"{example_name}-phase-1",
        capability_results,
        min_reps=REPS,
        dry_run=dry_run,
    )

    block_reason = phase2_blocked_reason(comparisons1, promoted)
    phase2_ran = False
    comparisons2: list[dict[str, Any]] = []
    summary2: dict[str, Any] = {}

    if phase2_eligible(comparisons1, promoted):
        registry_phase2 = load_registry(project)
        tasks_map = dict(registry_phase2.get("tasks") or {})
        for tid in promoted:
            tasks_map.setdefault(tid, {})["suite"] = "regression"
        tasks_map.setdefault(PHASE2_CAPABILITY, {})["suite"] = "capability"
        registry_phase2["tasks"] = tasks_map
        phase2_tasks = sorted(
            set(tasks_for_suite(registry_phase2, "regression")) | {PHASE2_CAPABILITY}
        )
        if not dry_run:
            save_registry(project, registry_phase2)
        comparisons2, summary2 = run_phase_under(
            project,
            out_root / "phase-2",
            phase2_tasks,
            registry_phase2,
            api_key=api_key,
            model=model,
            dry_run=dry_run,
            candidate_id=candidate_id,
        )
        phase2_ran = True

    write_human_spot_check(project, out_root / "phase-1", example_name)

    out_summary = {
        "scenario": scenario,
        "example_dir": example_name,
        "candidate_id": candidate_id,
        "phase_1": summary1,
        "promoted_tasks": promoted,
        "phase_2_ran": phase2_ran,
        "phase_2_blocked_reason": block_reason if not phase2_ran else None,
        "phase_2": summary2 if phase2_ran else None,
        "dry_run": dry_run,
        "model": model,
    }
    (out_root / "summary.json").write_text(json.dumps(out_summary, indent=2), encoding="utf-8")
    return out_summary


def run_phase_under(
    project: Path,
    phase_dir: Path,
    task_ids: list[str],
    registry: dict[str, Any],
    *,
    api_key: str,
    model: str,
    dry_run: bool,
    candidate_id: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if phase_dir.exists():
        shutil.rmtree(phase_dir)
    phase_dir.mkdir(parents=True)

    baseline_trials: list[dict[str, Any]] = []
    candidate_trials: list[dict[str, Any]] = []
    total_cost = 0.0

    for task_id in task_ids:
        for rep in range(REPS):
            for harness in ("baseline", "candidate"):
                row = run_one_trial(
                    project,
                    phase_dir,
                    task_id,
                    harness,
                    rep,
                    api_key=api_key,
                    model=model,
                    dry_run=dry_run,
                    candidate_id=candidate_id,
                )
                total_cost += float(row.get("cost_usd") or 0)
                if harness == "baseline":
                    baseline_trials.append(row)
                else:
                    candidate_trials.append(row)

    comparisons: list[dict[str, Any]] = []
    for task_id in task_ids:
        suite = (registry.get("tasks", {}).get(task_id) or {}).get("suite", "capability")
        b_passes = [t["pass"] for t in baseline_trials if t["task_id"] == task_id]
        c_passes = [t["pass"] for t in candidate_trials if t["task_id"] == task_id]
        disagreements = [
            t["grade"].get("model_disagreement")
            for t in candidate_trials
            if t["task_id"] == task_id and t["grade"].get("model_disagreement")
        ]
        comparisons.append(
            compare_task(
                task_id,
                b_passes,
                c_passes,
                suite,
                extra={"model_disagreements": len(disagreements)},
            )
        )

    summary = summarise(comparisons)
    summary["phase"] = phase_dir.name
    summary["total_cost_usd"] = round(total_cost, 4)

    write_harness_readme(phase_dir / "baseline", "baseline", baseline_trials)
    write_harness_readme(phase_dir / "candidate", "candidate", candidate_trials)
    write_comparison_readme(phase_dir, summary, comparisons)
    (phase_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return comparisons, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run harness evaluation")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mock transcripts (no API calls)",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL),
    )
    parser.add_argument(
        "--scenario",
        choices=["good", "bad", "both"],
        default=None,
        help="Which harness story (default from eval.config.yaml; both runs good+bad on --dry-run)",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to eval.config.yaml (default: repo root eval.config.yaml)",
    )
    args = parser.parse_args(argv)

    project = project_root()
    dry_run = args.dry_run
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not dry_run and not api_key:
        print("Set OPENROUTER_API_KEY or pass --dry-run")
        return 1

    config = load_eval_config(project)
    if args.config:
        import yaml

        config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8")) or config

    scenarios = resolve_scenarios(args.scenario, dry_run, config)

    legacy_phase1 = project / "output" / "phase-1"
    legacy_phase2 = project / "output" / "phase-2"
    if dry_run and scenarios == resolve_scenarios("both", True, config):
        if legacy_phase1.exists():
            shutil.rmtree(legacy_phase1)
        if legacy_phase2.exists():
            shutil.rmtree(legacy_phase2)
        legacy_summary = project / "output" / "summary.json"
        if legacy_summary.is_file():
            legacy_summary.unlink()

    all_summaries: dict[str, Any] = {}
    for scenario in scenarios:
        summary = run_scenario_fixed(
            project,
            scenario,
            api_key=api_key,
            model=args.model,
            dry_run=dry_run,
        )
        all_summaries[scenario] = summary
        print(json.dumps(summary, indent=2))

    if len(all_summaries) == 1:
        only = next(iter(all_summaries.values()))
        (project / "output" / "summary.json").write_text(
            json.dumps(only, indent=2), encoding="utf-8"
        )
    else:
        (project / "output" / "summary.json").write_text(
            json.dumps({"scenarios": all_summaries, "dry_run": dry_run}, indent=2),
            encoding="utf-8",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
