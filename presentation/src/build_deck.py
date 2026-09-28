#!/usr/bin/env python3
"""Build harness-eval.pptx from committed output/ example runs."""

from __future__ import annotations

import json
from pathlib import Path

from pptx import Presentation
from pptx.util import Pt

GOOD_DIR = "good-harness-example"
BAD_DIR = "bad-harness-example"


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def findings_snippet(project: Path, example: str, harness: str, task: str = "auth-vs-log") -> str:
    path = (
        project
        / "output"
        / example
        / "phase-1"
        / harness
        / "trials"
        / task
        / "0"
        / "result"
        / "findings.json"
    )
    if not path.is_file():
        return "(run python3 -m eval --dry-run first)"
    text = path.read_text(encoding="utf-8")
    return text[:900] + ("..." if len(text) > 900 else "")


def add_slide(prs: Presentation, title: str, bullets: list[str], notes: str) -> None:
    layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(layout)
    slide.shapes.title.text = title
    body = slide.placeholders[1].text_frame
    body.clear()
    for i, line in enumerate(bullets):
        p = body.paragraphs[0] if i == 0 else body.add_paragraph()
        p.text = line
        p.level = 0
        p.font.size = Pt(16 if len(line) > 120 else 18)
    slide.notes_slide.notes_text_frame.text = notes


def comparison_rows(project: Path, example: str, phase: str) -> list[str]:
    data = load_json(project / "output" / example / phase / "comparison" / "result.json")
    rows: list[str] = []
    for c in data.get("comparisons") or []:
        rows.append(
            f"{c['task_id']}: {c['baseline_outcome']} → {c['candidate_outcome']} ({c['transition']})"
        )
    return rows or ["(no comparison data)"]


def main() -> None:
    project = root()
    good = load_json(project / "output" / GOOD_DIR / "summary.json")
    bad = load_json(project / "output" / BAD_DIR / "summary.json")
    g1 = good.get("phase_1") or {}
    g2 = good.get("phase_2") or {}
    b1 = bad.get("phase_1") or {}

    prs = Presentation()
    title = prs.slides.add_slide(prs.slide_layouts[0])
    title.shapes.title.text = "Harness evaluation loop"
    title.placeholders[1].text = (
        "Paired trials, code graders, and capability graduation — good vs bad harness changes"
    )
    title.notes_slide.notes_text_frame.text = (
        "Frame the talk around a question every agent platform team faces: "
        "we changed the harness — did we actually improve outcomes? "
        "This repository runs the same tasks under the same model and tools, "
        "changing only guidance files. You will see two real outcomes from one shared baseline: "
        "a skill that graduates into phase 2, and a skill that fails a regression gate before phase 2 runs."
    )

    add_slide(
        prs,
        "The problem: harness changes ship on anecdotes",
        [
            "Teams edit AGENTS.md, skills, hooks, and tool defaults every week.",
            "Review is often a few transcripts in Slack and maintainer gut feel.",
            "Quality is multidimensional: correctness, fidelity, regression risk, cost, latency.",
            "Without paired evidence, a louder narrative wins — not necessarily a better harness.",
        ],
        "Pause here and ask who has shipped a harness tweak without a before/after suite. "
        "The pain is not missing metrics in general — it is missing metrics tied to the same task "
        "and the same model so the delta is attributable.",
    )

    add_slide(
        prs,
        "The false belief: any harness change is progress",
        [
            "A new skill file sounds stricter, so reviewers assume safety improved.",
            "Sometimes guidance helps triage (fewer false positives).",
            "Sometimes guidance encourages destructive edits (tests fail).",
            "Our tool makes both outcomes visible before rollout — same baseline, different candidates.",
        ],
        "This slide sets up the two stories. Point at the repo folders good-harness-example and "
        "bad-harness-example under output/. Same baseline AGENTS.md both times; only the candidate "
        "SKILL.md differs. One candidate beats baseline on capability without breaking regression; "
        "the other regresses keep-suite in phase 1 and never reaches phase 2.",
    )

    add_slide(
        prs,
        "Terminology (use consistently)",
        [
            "Task: repo + prompt + held-out acceptance criteria",
            "Trial: one harness run in a clean workspace (reps=2 for stability signal)",
            "Transcript: tools, tokens, latency, findings, errors — on disk per trial",
            "Agent harness: model + tools + guidance | Evaluation harness: this orchestrator",
            "Capability eval: learn what works | Regression eval: must keep passing",
        ],
        "Walk the table quickly. Emphasize evaluation harness vs agent harness — reviewers confuse them. "
        "Capability tasks can graduate into regression after pass^k on the candidate arm.",
    )

    add_slide(
        prs,
        "Three jobs every eval must do (our tasks)",
        [
            "Unambiguous spec — auth-vs-log: withdraw vulnerable, logTransfer not (tx.origin triage)",
            "Regression protection — keep-suite: pytest on app/config.py must still pass",
            "Development feedback — caller-check (phase 2): new capability after graduation",
            "Each job maps to a grader family; code graders gate promotion",
        ],
        "Tie jobs to Wallet.sol. withdraw uses tx.origin for authorization; logTransfer only logs it. "
        "keep-suite is intentionally easy for both arms unless the agent breaks constants. "
        "caller-check generalizes the triage skill to withdrawAll.",
    )

    add_slide(
        prs,
        "Controlled experiment: one intentional variable",
        [
            "Same OpenRouter Haiku model, endpoint, tool loop (read/list/write)",
            "Same task repos and prompts; held-out labels never enter the workspace",
            "Baseline: harnesses/baseline/AGENTS.md (noisy tx.origin rule)",
            "Candidate: good-candidate or bad-candidate SKILL.md — only guidance changes",
            "Attribution breaks if you also swap model, tools, or task prompts",
        ],
        "Stress one variable. If someone compared Haiku to Opus in the same slide, you could not "
        "claim the skill helped. Our dry-run uses mocks/ for deterministic findings; live runs use the same graders.",
    )

    add_slide(
        prs,
        "Shared task suite (phase 1)",
        [
            "auth-vs-log (capability): audit Wallet.sol → write findings.json",
            "keep-suite (regression): scan repo; do not break config or tests",
            "Phase 2 adds caller-check (capability) + graduated auth-vs-log as regression gate",
            "Registry: tasks/registry.yaml — bootstrap resets suite tags",
        ],
        "Read prompt.txt paths if asked. Held-out expected.json lives under tasks/*/heldout/ and is "
        "applied only at grade time.",
    )

    add_slide(
        prs,
        "Graders: what checks what",
        [
            "Code (auth tasks): match findings to held-out per-function vulnerable flags; caller-check requires tx.origin in issue text",
            "Code (keep-suite): subprocess pytest -q tests in workspace after agent stops",
            "Model rubric (capability, live only): Haiku PASS/FAIL on explanation quality — evidence only",
            "Human: human_spot_check.md checklist per example run — does not override code",
            "Promotion and phase verdicts use code pass/fail only; model_disagreement is surfaced",
        ],
        "If code FAILs and model PASSes, we record disagreement and keep FAIL. "
        "This avoids rubric optimism on vague prose.",
    )

    add_slide(
        prs,
        "How to read a result (reviewer path)",
        [
            "Per task: baseline_outcome, candidate_outcome, transition (IMPROVED/REGRESSED/UNCHANGED/UNSTABLE)",
            "Phase verdict: NEGATIVE if any regression; POSITIVE if improved with no regressions; else INCONCLUSIVE",
            "Open output/<example>/phase-1/comparison/result.json then trials/*/grade.json",
            "phase_2_blocked_reason explains why graduation did not run (bad example)",
        ],
        "Teach the artifact chain: comparison row → trial directory → findings.json vs held-out. "
        "Numbers on later slides come from summary.json under each example folder.",
    )

    add_slide(
        prs,
        "Good harness change: triage skill (good-candidate)",
        [
            "Candidate SKILL: tx.origin vulnerable only when it gates privileged actions",
            "Logging/events using tx.origin are explicitly not findings",
            "Intent: reduce false positives while keeping withdraw flagged",
            "Harness diff: harnesses/good-candidate/SKILL.md vs baseline AGENTS.md",
        ],
        "This is the change a security-minded team would propose after too many logTransfer noise tickets. "
        "The eval asks: does it actually pass held-out labels and keep tests green?",
    )

    good_b = findings_snippet(project, GOOD_DIR, "baseline")
    good_c = findings_snippet(project, GOOD_DIR, "candidate")
    add_slide(
        prs,
        "Good example — phase 1 findings (baseline vs candidate)",
        [
            "Baseline (over-flags logging):",
            good_b[:420],
            "Candidate (correct triage):",
            good_c[:420],
            f"Verdict: {g1.get('verdict')} | Promoted: {good.get('promoted_tasks')}",
        ],
        "Walk line by line. Baseline marks logTransfer vulnerable — code grader FAIL. "
        "Candidate marks withdraw vulnerable and logTransfer not — PASS both reps. "
        "keep-suite stays PASS/UNCHANGED. Phase 1 POSITIVE; auth-vs-log graduates to regression.",
    )

    g1_rows = comparison_rows(project, GOOD_DIR, "phase-1")
    g2_rows = comparison_rows(project, GOOD_DIR, "phase-2")
    add_slide(
        prs,
        "Good example — phase 2 after graduation",
        [
            f"Phase 2 ran: {good.get('phase_2_ran')}",
            f"Phase 2 verdict: {g2.get('verdict', 'n/a')}",
            "Phase 1 transitions:",
            *g1_rows[:3],
            "Phase 2 transitions:",
            *g2_rows[:4],
        ],
        "Suite grew: auth-vs-log is now a regression gate; caller-check probes generalization. "
        "Candidate improves on graduated auth-vs-log and new caller-check while keep-suite stays stable. "
        "This is the product loop: capability → stable pass → regression CI gate.",
    )

    add_slide(
        prs,
        "Bad harness change: strict remediation (bad-candidate)",
        [
            "Candidate SKILL: remove tx.origin and harden config values aggressively",
            "Sounds safer in a design review — patch code, bump versions, tighten retries",
            "Mock outcome: incomplete findings on auth-vs-log (missing withdraw)",
            "keep-suite: overlay changes API_VERSION and MAX_RETRIES → pytest FAIL",
        ],
        "Contrast with good skill. Both could be described as more thorough in Slack. "
        "Only paired graders show keep-suite regression.",
    )

    bad_b = findings_snippet(project, BAD_DIR, "baseline")
    bad_c = findings_snippet(project, BAD_DIR, "candidate")
    b1_rows = comparison_rows(project, BAD_DIR, "phase-1")
    add_slide(
        prs,
        "Bad example — phase 1 (worse than baseline on regression)",
        [
            "Baseline findings (auth-vs-log):",
            bad_b[:380],
            "Bad candidate findings:",
            bad_c[:380],
            *b1_rows,
            f"Verdict: {b1.get('verdict')} | Phase 2 blocked: {bad.get('phase_2_blocked_reason')}",
        ],
        "Capability still FAIL — missing withdraw label. Regression REGRESSED: baseline PASS, candidate FAIL on keep-suite. "
        "Phase 2 never runs; phase_2_blocked_reason is in bad-harness-example/summary.json. "
        "This is the failure mode teams miss without pytest gates.",
    )

    add_slide(
        prs,
        "Same baseline, two candidates — side by side",
        [
            f"Good phase 1: {g1.get('verdict')} | improved {g1.get('improved')} regressed {g1.get('regressed')}",
            f"Bad phase 1: {b1.get('verdict')} | improved {b1.get('improved')} regressed {b1.get('regressed')}",
            "Good: phase 2 runs, suite graduates auth-vs-log",
            "Bad: no promotion, no phase 2 — regression gate failed first",
        ],
        "The baseline arm is identical in both experiments. The only fork is which SKILL.md the candidate arm loads. "
        "Use this slide to answer why we do not trust a single demo run.",
    )

    add_slide(
        prs,
        "Without this tool",
        [
            "Both skills read as security improvements in a design doc",
            "Baseline noise on logging might be dismissed as model randomness",
            "Destructive config edits might be caught only in production CI days later",
            "Paired trials + code graders produce a verdict before rollout",
        ],
        "Invite discussion: what would your team have shipped? "
        "The evaluation harness does not replace human review — it forces contrasting artifacts early.",
    )

    add_slide(
        prs,
        "Limits and policy",
        [
            "n=2 reps: UNSTABLE transitions are not rounded into wins",
            "No p-values at this scale — INCONCLUSIVE is honest",
            "Model rubric non-deterministic; code gates promotion",
            "Dry-run: mocks/ + overlay files; cost_usd=0, cost_source=mock",
            "Live runs need OPENROUTER_API_KEY; reset registry from bootstrap between fresh phase-1 runs",
        ],
        "Acknowledge scope. Custom mini-agent, sequential trials, single spot-check template.",
    )

    add_slide(
        prs,
        "Run it (commands)",
        [
            "pip install -e '.[dev]'",
            "python3 -m eval --dry-run  # both scenarios per eval.config.yaml",
            "python3 -m eval --dry-run --scenario good",
            "python3 -m eval --dry-run --scenario bad",
            "python3 presentation/src/build_deck.py",
            "pytest -q",
        ],
        "Point reviewers to output/good-harness-example and output/bad-harness-example. "
        "Configure scenario in eval.config.yaml. Deck numbers must match summary.json on disk.",
    )

    out_dir = project / "presentation" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "harness-eval.pptx"
    prs.save(str(out_path))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
