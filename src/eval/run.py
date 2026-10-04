"""Run phase 1, optional promotion, phase 2."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import time
from dataclasses import dataclass, field
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
from .debug_break import EvalAbort, candidate_must_pass, write_debug_break
from .log_util import error, info, warn
from .trial import copy_guidance, copy_task_repo, write_trial_artifacts

from .models import DEFAULT_MODEL

OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1"
REPS = 2
MAX_COST_PER_TRIAL = 0.08
PHASE2_CAPABILITY = "caller-check"
INTER_TRIAL_SLEEP_S = 1.5
PHASE_GAP_SLEEP_S = 20.0


@dataclass
class RunContext:
    credits_depleted: bool = False
    depletion_reason: str | None = None
    openrouter_cost_usd: float = 0.0
    fail_fast: bool = True
    aborted: bool = False
    abort_reason: str | None = None
    scenario: str = ""


def credits_exhausted_message(error_text: str) -> bool:
    m = re.search(r"can only afford\s+(\d+)", error_text, re.I)
    if m and int(m.group(1)) < 200:
        return True
    if "insufficient credits" in error_text.lower():
        return True
    return False


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_env_file(project: Path) -> None:
    path = project / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def trial_total_cost(transcript: dict[str, Any], grade: dict[str, Any]) -> float:
    total = float(transcript.get("cost_usd") or 0)
    rubric = grade.get("model_grade_cost_usd")
    if rubric is not None:
        total += float(rubric)
    return total


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
    ctx: RunContext,
) -> dict[str, Any]:
    task_dir = project / "tasks" / task_id
    prompt = (task_dir / "prompt.txt").read_text(encoding="utf-8")
    trial_dir = phase_dir / harness / "trials" / task_id / str(rep)
    workspace_parent = phase_dir / "_workspaces" / harness / task_id / str(rep)
    if workspace_parent.exists():
        shutil.rmtree(workspace_parent)
    workspace_parent.mkdir(parents=True)
    workspace = workspace_parent / "repo"
    phase_name = phase_dir.name
    info(f"{phase_name} | {harness:8} | {task_id:14} | rep {rep} | start")

    guidance = ""

    if ctx.credits_depleted and not dry_run:
        warn(f"{phase_name} | {harness} | {task_id} rep {rep} | skipped (OpenRouter credits depleted)")
        transcript = {
            "messages": [],
            "tool_trace": [],
            "errors": [ctx.depletion_reason or "OpenRouter credits depleted"],
            "findings_text": "",
            "latency_s": 0.0,
            "ttft_ms": None,
            "tokens": {"input": 0, "output": 0, "total": 0},
            "cost_usd": 0.0,
            "cost_source": "skipped",
        }
    elif dry_run:
        copy_task_repo(task_dir, workspace)
        guidance = copy_guidance(project, harness, workspace, candidate_id=candidate_id)
        transcript = apply_mock_transcript(
            project,
            workspace,
            harness,
            task_id,
            candidate_id=candidate_id,
        )
    else:
        copy_task_repo(task_dir, workspace)
        guidance = copy_guidance(project, harness, workspace, candidate_id=candidate_id)
        transcript = run_agent(
            workspace,
            prompt,
            guidance,
            endpoint=OPENROUTER_ENDPOINT,
            model=model,
            api_key=api_key,
            max_turns=12,
            max_cost_usd=MAX_COST_PER_TRIAL,
            task_dir=task_dir,
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
            dry_run=False,
            use_model_grader=use_model,
        )

    if dry_run or ctx.credits_depleted:
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
    if transcript.get("errors") and not dry_run:
        grade["api_error"] = True
    write_trial_artifacts(trial_dir, transcript, grade)
    cost = trial_total_cost(transcript, grade)
    if not dry_run:
        ctx.openrouter_cost_usd += cost
    tok = (transcript.get("tokens") or {}).get("total", 0)
    info(
        f"{phase_name} | {harness:8} | {task_id:14} | rep {rep} | "
        f"code_pass={grade.get('code_pass')} pass={grade['pass']} | "
        f"cost=${cost:.4f} tokens={tok} latency={transcript.get('latency_s')}s"
    )
    if grade.get("code_reason"):
        info(f"  grader: {grade['code_reason'][:120]}")
    if transcript.get("errors"):
        err_tail = transcript["errors"][-1]
        warn(f"  agent errors: {err_tail[:160]}")
        if not dry_run and credits_exhausted_message(err_tail):
            ctx.credits_depleted = True
            ctx.depletion_reason = err_tail[:300]
            error("OpenRouter credits depleted — remaining trials in this phase will be skipped")
    if (
        not dry_run
        and ctx.fail_fast
        and not ctx.aborted
        and (
            transcript.get("errors")
            or (candidate_must_pass(ctx.scenario, harness) and not grade.get("pass"))
        )
    ):
        reason = (
            f"candidate trial failed ({grade.get('code_reason') or grade.get('model_reason')})"
            if candidate_must_pass(ctx.scenario, harness) and not grade.get("pass")
            else f"agent errors: {transcript.get('errors')}"
        )
        write_debug_break(
            project,
            scenario=ctx.scenario,
            phase_name=phase_name,
            harness=harness,
            task_id=task_id,
            rep=rep,
            workspace=workspace,
            trial_dir=trial_dir,
            grade=grade,
            transcript=transcript,
            reason=reason,
        )
        ctx.aborted = True
        ctx.abort_reason = reason
    return {
        "task_id": task_id,
        "harness": harness,
        "rep": rep,
        "pass": grade["pass"],
        "cost_usd": cost,
        "latency_s": transcript.get("latency_s"),
        "grade": grade,
        "api_error": bool(grade.get("api_error")),
        "trial_dir": str(trial_dir.relative_to(project)),
    }


def _aborted_summary(
    scenario: str,
    example_name: str,
    candidate_id: str,
    model: str,
    dry_run: bool,
    ctx: RunContext,
    phase1: dict[str, Any],
    phase2: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "scenario": scenario,
        "example_dir": example_name,
        "candidate_id": candidate_id,
        "phase_1": phase1,
        "phase_2": phase2,
        "aborted": True,
        "abort_reason": ctx.abort_reason,
        "openrouter_cost_usd": round(ctx.openrouter_cost_usd, 6),
        "dry_run": dry_run,
        "model": model,
    }


def run_scenario_fixed(
    project: Path,
    scenario: str,
    *,
    api_key: str,
    model: str,
    dry_run: bool,
    ctx: RunContext | None = None,
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

    if ctx is None:
        ctx = RunContext()
    ctx.scenario = scenario
    info(f"=== scenario={scenario} example={example_name} candidate={candidate_id} ===")
    info("--- Phase 1 start ---")
    comparisons1, summary1 = run_phase_under(
        project,
        out_root / "phase-1",
        phase1_tasks,
        registry,
        api_key=api_key,
        model=model,
        dry_run=dry_run,
        candidate_id=candidate_id,
        ctx=ctx,
    )
    if ctx.aborted:
        out_summary = _aborted_summary(
            scenario, example_name, candidate_id, model, dry_run, ctx, summary1, None
        )
        (out_root / "summary.json").write_text(json.dumps(out_summary, indent=2), encoding="utf-8")
        raise EvalAbort(ctx.abort_reason or "aborted")

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

    info(
        f"Phase 1 done | verdict={summary1.get('verdict')} cost=${summary1.get('total_cost_usd')} "
        f"promoted={promoted}"
    )
    block_reason = phase2_blocked_reason(comparisons1, promoted)
    phase2_ran = False
    comparisons2: list[dict[str, Any]] = []
    summary2: dict[str, Any] = {}

    if phase2_eligible(comparisons1, promoted) and not ctx.credits_depleted:
        if not dry_run:
            info(f"Waiting {PHASE_GAP_SLEEP_S:.0f}s before Phase 2 (OpenRouter in-flight budget)")
            time.sleep(PHASE_GAP_SLEEP_S)
        info("--- Phase 2 start ---")
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
            ctx=ctx,
        )
        if ctx.aborted:
            out_summary = _aborted_summary(
                scenario,
                example_name,
                candidate_id,
                model,
                dry_run,
                ctx,
                summary1,
                summary2,
            )
            (out_root / "summary.json").write_text(
                json.dumps(out_summary, indent=2), encoding="utf-8"
            )
            raise EvalAbort(ctx.abort_reason or "aborted")
        phase2_ran = True
        info(
            f"Phase 2 done | verdict={summary2.get('verdict')} cost=${summary2.get('total_cost_usd')}"
        )
    elif ctx.credits_depleted:
        warn("Phase 2 skipped: OpenRouter credits depleted during Phase 1")
    elif block_reason:
        warn(f"Phase 2 skipped: {block_reason}")

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
        "openrouter_credits_depleted": ctx.credits_depleted,
        "openrouter_depletion_reason": ctx.depletion_reason,
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
    ctx: RunContext,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if phase_dir.exists():
        shutil.rmtree(phase_dir)
    phase_dir.mkdir(parents=True)

    baseline_trials: list[dict[str, Any]] = []
    candidate_trials: list[dict[str, Any]] = []
    total_cost = 0.0
    api_errors = 0

    trial_count = len(task_ids) * REPS * 2
    info(f"{phase_dir.name}: {len(task_ids)} tasks × {REPS} reps × 2 arms = {trial_count} trials")

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
                    ctx=ctx,
                )
                total_cost += float(row.get("cost_usd") or 0)
                if row.get("api_error"):
                    api_errors += 1
                if harness == "baseline":
                    baseline_trials.append(row)
                else:
                    candidate_trials.append(row)
                if not dry_run:
                    time.sleep(INTER_TRIAL_SLEEP_S)
                if ctx.aborted:
                    warn(f"{phase_dir.name}: stopping early (fail-fast)")
                    break
            if ctx.aborted:
                break
        if ctx.aborted:
            break

    if api_errors:
        warn(f"{phase_dir.name}: {api_errors} trial(s) had API/agent errors (see errors/execution.log)")

    if api_errors == trial_count and not dry_run:
        summary_override = {
            "verdict": "INCOMPLETE",
            "improved": 0,
            "regressed": 0,
            "unstable": 0,
            "task_count": len(task_ids),
            "phase": phase_dir.name,
            "total_cost_usd": round(total_cost, 4),
            "api_error_trials": api_errors,
            "failure_reason": "all_trials_had_api_errors",
        }
        write_harness_readme(phase_dir / "baseline", "baseline", baseline_trials)
        write_harness_readme(phase_dir / "candidate", "candidate", candidate_trials)
        write_comparison_readme(phase_dir, summary_override, [])
        (phase_dir / "summary.json").write_text(json.dumps(summary_override, indent=2), encoding="utf-8")
        return [], summary_override

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

    summary = summarise(comparisons, phase=phase_dir.name)
    summary["phase"] = phase_dir.name
    summary["total_cost_usd"] = round(total_cost, 4)
    summary["api_error_trials"] = api_errors

    info(
        f"{phase_dir.name} compare | verdict={summary['verdict']} "
        f"improved={summary['improved']} regressed={summary['regressed']} "
        f"unstable={summary['unstable']}"
    )
    for c in comparisons:
        info(
            f"  {c['task_id']:14} {c['suite']:11} "
            f"{c['baseline_outcome']} → {c['candidate_outcome']} ({c['transition']})"
        )

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
    parser.add_argument(
        "--no-fail-fast",
        action="store_true",
        help="Live only: keep running after a failed good-candidate trial (default: stop immediately)",
    )
    args = parser.parse_args(argv)

    project = project_root()
    load_env_file(project)
    dry_run = args.dry_run
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not dry_run and not api_key:
        error("Set OPENROUTER_API_KEY or pass --dry-run")
        return 1
    if dry_run:
        info("dry-run: mock transcripts only (no OpenRouter)")
    else:
        info(f"live run | model={args.model}")

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
    session_cost = 0.0
    for idx_scenario, scenario in enumerate(scenarios):
        if not dry_run and idx_scenario > 0:
            info(f"Waiting {PHASE_GAP_SLEEP_S:.0f}s before next scenario")
            time.sleep(PHASE_GAP_SLEEP_S)
        ctx = RunContext(fail_fast=not args.no_fail_fast and not dry_run)
        try:
            summary = run_scenario_fixed(
                project,
                scenario,
                api_key=api_key,
                model=args.model,
                dry_run=dry_run,
                ctx=ctx,
            )
        except EvalAbort as exc:
            error(f"Run aborted: {exc}")
            summary = {
                "scenario": scenario,
                "aborted": True,
                "abort_reason": ctx.abort_reason,
                "openrouter_cost_usd": round(ctx.openrouter_cost_usd, 6),
                "model": args.model,
                "dry_run": dry_run,
            }
            all_summaries[scenario] = summary
            session_cost += ctx.openrouter_cost_usd
            print(json.dumps(summary, indent=2))
            if not dry_run:
                info(
                    f"=== OpenRouter session total (this process): ${session_cost:.6f} USD ==="
                )
            return 2
        session_cost += ctx.openrouter_cost_usd
        all_summaries[scenario] = summary
        print(json.dumps(summary, indent=2))

    if len(all_summaries) == 1:
        only = next(iter(all_summaries.values()))
        (project / "output" / "summary.json").write_text(
            json.dumps(only, indent=2), encoding="utf-8"
        )
    else:
        (project / "output" / "summary.json").write_text(
            json.dumps(
                {
                    "scenarios": all_summaries,
                    "dry_run": dry_run,
                    "openrouter_session_cost_usd": round(session_cost, 6),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    if not dry_run:
        info(
            f"=== OpenRouter session total (this process): ${session_cost:.6f} USD ==="
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
