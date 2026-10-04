# Next steps: align with `build-eval` / `hillclimb` (conceptual parity)

**Status:** Plan only — no implementation until reviewed and approved.  
**Goal:** Keep the repo **demo-ready for interviewers** while closing the largest gaps vs Anthropic’s guided workflows ([Automating eval design and hillclimbing](https://claude.dev/blog/automating-eval-design-and-hillclimbing/)).

**Reference commands in the blog:** `/claude-api build-eval`, `/claude-api hillclimb` (Claude Code + `claude-api` skill).

---

## What we already provide (mapped to the blog)

| Blog concept | Our implementation today | Where to point in the repo |
|--------------|-------------------------|----------------------------|
| Eval tasks tied to a real harness surface | Solidity audit + Python regression tasks | [`tasks/`](tasks/), [`harnesses/`](harnesses/) |
| Programmatic grader (preferred when output is structured) | Held-out JSON + pytest | [`src/eval/graders.py`](src/eval/graders.py) |
| Baseline vs candidate comparison | Paired arms, per-task transitions | [`src/eval/compare.py`](src/eval/compare.py), `output/*/phase-1/comparison/` |
| Regression protection | `keep-suite` + phase-2 block on REGRESSED | [`src/eval/gate.py`](src/eval/gate.py) |
| Capability → regression graduation | `promote_capability_tasks` after pass^k | [`src/eval/promote.py`](src/eval/promote.py) |
| Held-out answers not in agent workspace | `heldout/expected.json` only at grade time | [`src/eval/trial.py`](src/eval/trial.py) |
| One controlled harness variable | Same model/tools; guidance-only diff | [`ai/decisions.md`](ai/decisions.md) |
| Evidence on disk | Trials, transcripts, grades, cost | `output/good-harness-example/`, `output/bad-harness-example/` |
| Good vs bad harness narrative | Two scenarios, shared baseline | [`README.md`](../README.md), [`eval.config.yaml`](../eval.config.yaml) |

This already answers the core interview story: **measure harness changes before rollout**, with deterministic graders—not vibes.

---

## Gaps vs `/claude-api build-eval`

### Gap 1 — No guided “design the eval” workflow

**Blog:** Interactive flow to sample tasks from production/bugs/hand-written cases, review inputs on a page, approve before running.

**Us today:** Tasks and graders are **fixed in repo** ([`prompts/BUILD-HARNESS-EVAL-TOOL.md`](../prompts/BUILD-HARNESS-EVAL-TOOL.md)). A new team must edit YAML/Python by hand.

**Steps to fill (demo scope, ~1–2 days):**

1. Add `docs/eval-design-checklist.md` (or a single CLI subcommand `python3 -m eval.design`) that walks: production-like task → acceptance criteria → grader choice (code vs rubric).
2. Add `tasks/registry.schema.yaml` + validator so suite tags stay consistent.
3. Optional: static HTML generator `python3 -m eval.report_inputs` listing each task’s prompt path, repo path, and held-out path for reviewer sign-off (mirrors blog “review every input” without a full UI).

**Benefit for demo:** You can say “we don’t only run evals—we document how to **add** one without fooling ourselves,” even if automation is lighter than Claude’s skill.

### Gap 2 — No grader validation ritual

**Blog:** Grade a handful of cases; ask “would you score differently?”; run grader **twice on identical output** to detect flakiness.

**Us today:** Unit tests on graders ([`tests/test_graders.py`](../tests/test_graders.py)); no `grader --self-check` on real trial outputs.

**Steps:**

1. Add `python3 -m eval.validate-grader --task auth-vs-log` that loads N mock/workspace fixtures and asserts stable pass/fail.
2. Add optional step in [`scripts/e2e_validate.sh`](../scripts/e2e_validate.sh) to run grader twice on the same `findings.json` and fail if verdict flips.
3. Document in README: “validate grader before trusting phase verdict.”

**Benefit:** Directly addresses interviewer concern that **bad graders** fake improvements.

### Gap 3 — No baseline score + headroom / noise diagnostics

**Blog:** Baseline run with confidence interval; warn if ~95%+ (no headroom); check infra noise vs model variance.

**Us today:** `summary.json` verdict counts; **n=2**, no CIs, no headroom warning ([`README.md`](../README.md) limitations).

**Steps (keep demo honest, not fake stats):**

1. Add `diagnostics` block in phase summary: fraction pass per arm, count UNSTABLE, explicit **“low n — not for production CI”** banner in comparison README.
2. If baseline candidate pass rate on capability tasks is already 100% on both reps, emit `headroom_warning` in JSON (blog-style tell).
3. Deck slide: “we report noise explicitly; we do not claim p-values at n=2.”

**Benefit:** Shows maturity: we know when an eval **cannot** support hillclimbing.

### Gap 4 — No local results browser

**Blog:** Plain HTML page per case with score + link to transcript.

**Us today:** Markdown READMEs + JSON ([`src/eval/report.py`](../src/eval/report.py)); deck from [`presentation/src/build_deck.py`](../presentation/src/build_deck.py).

**Steps:**

1. Add `python3 -m eval.report_html` → `output/<example>/index.html` linking each trial’s `findings.json`, `grade.json`, `comparison/result.json`.
2. Mention in README next to pptx for reviewers who want click-through evidence.

**Benefit:** Faster live demo than opening pptx + digging folders.

---

## Gaps vs `/claude-api hillclimb`

### Gap 5 — No automated harness iteration loop

**Blog:** Split train/test; one patch per round; revert if train↑ test flat or regression; stop when stalled; output best-on-test vs baseline with CIs.

**Us today:** Human edits `SKILL.md` / `AGENTS.md`; tool **compares** baseline vs one candidate; does not propose or apply patches.

**Steps (conceptual parity, minimal scope):**

1. **Do not** auto-edit harness in v1 demo—interviewers may worry about overfitting automation. Instead:
   - Add `hillclimb/` doc describing how a human would loop: edit guidance → `python3 -m eval --scenario good` → read comparison → repeat.
2. Optional v2: `python3 -m eval.hillclimb --max-rounds 3` that only allows edits under `harnesses/candidate-patches/` with **manual approve** per patch (stdin y/n), still using our graders.
3. Implement **train/test task split** in registry: `suite: capability-train` vs `capability-holdout` (e.g. 2 tasks train, 1 holdout). Promotion uses train only; holdout reported separately in summary (blog overfitting check).

**Benefit:** You can say “we support the **same loop** as hillclimb; we scoped automation out to keep the take-home auditable,” and show holdout if implemented.

### Gap 6 — No cost/latency optimization objective

**Blog:** Hillclimb for cost while holding accuracy; model/effort sweep.

**Us today:** `cost_usd` per trial in artifacts; no “optimize cost given pass rate ≥ baseline” loop.

**Steps:**

1. Add comparison field: `total_cost_usd` delta baseline vs candidate per phase (already partially in phase summary).
2. In deck/README: one row “same pass, lower cost” as future objective—even if current demo fixes model.

**Benefit:** Aligns with blog’s second hillclimb story without requiring Opus/Sonnet sweeps in demo.

### Gap 7 — No failure bucketing when score stalls

**Blog:** When stalled, cluster remaining failures by root cause (ambiguous task vs grader bug vs harness).

**Us today:** Human reads `comparison/README.md` and trials.

**Steps:**

1. Add `python3 -m eval.triage-failures --example good-harness-example` that groups failed trials by `grade.json` `code_reason` prefix.
2. Output markdown table for slide/deck appendix.

**Benefit:** Shows you understand **eval debugging**, not only happy-path good/bad stories.

---

## Suggested priority for interview demo (ordered)

| Priority | Item | Effort | Interview payoff |
|----------|------|--------|------------------|
| P0 | README purpose + two harness stories (done) | — | Clarifies “coding agent harness” goal |
| P1 | Static HTML results index (`report_html`) | Small | Click-through evidence in live demo |
| P1 | Grader self-check command + e2e hook | Small | “Deterministic gates” credibility |
| P2 | Holdout task split in registry (train vs holdout) | Medium | Hillclimb overfitting story without full automation |
| P2 | `diagnostics` + headroom warning in summary | Small | Honest about n=2 |
| P3 | Documented human hillclimb loop in `docs/HILLCLIMB_LOOP.md` | Small | Conceptual parity with `/claude-api hillclimb` |
| P3 | Optional approved-patch hillclimb CLI | Large | Only if interviewer pushes on automation |

---

## Out of scope (keep take-home bounded)

- Full Claude Code / Codex CLI integration as the agent under test (we use a minimal loop on purpose).
- LLM-as-judge as the **gate** (blog allows it; we deliberately keep code-first — [`DESIGN.md`](../DESIGN.md)).
- Automatic paste of failure transcripts into prompts (blog warns against this; we should not add it).
- Statistical tests at n=2 presented as significant.

---

## Video note

The [referenced X video](https://x.com/cammy_wammy/status/2104913198155530672/video/1) was not parsed in this plan (no transcript in tooling). If it shows a UI walkthrough of `build-eval` / `hillclimb`, treat **P1 HTML index + comparison table** as the closest demo equivalent; re-watch once and add any UI-specific bullet under Gap 4.

---

## Approval checklist (for you)

- [ ] Is P1 (HTML + grader self-check) enough for the next demo iteration?
- [ ] Should we implement holdout split (P2) before claiming “hillclimb conceptually”?
- [ ] Any interviewer requirement to run against **real** Claude Code harness instead of our mini-agent?

Once approved, implement in the order above without expanding scope beyond demonstration needs.
