# Harness evaluation

- **Problem:** Teams continuously tune coding-agent harnesses (Claude Code, Codex, Cursor) through `AGENTS.md`, skills, hooks, tools, MCPs, routing, etc. The question is **not whether the model is smarter**, but whether a harness change actually **improves the results rather than relying on gut feeling**.

- **Evaluation:** Run the **same tasks with the same model + tool loop** against baseline vs candidate, changing only the harness. Then I'm **grading the outcomes with deterministic code graders** and comparing the paired results to catch regressions or bad changes.

- **Outcome:** The tool provides an evidence-based **graduate/block** workflow:
  good harness changes become regression gates in the next phase, while changes that don't improve outcomes are blocked, replacing **"this feels better" with measurable evidence**.

I took a simple **Solidity codebase example** to show how two different harness changes can affect the agent's ability to identify bugs. The same model, tools, and task are used in both cases; **only the harness changes by adding a new `SKILL.md` file**. I intentionally kept the example very basic so the difference is easy to see.

- **Problem example:** I prepared a simple Solidity contract, `Wallet.sol`. The `withdraw()` function uses `tx.origin` for authorization and is genuinely vulnerable, while the `logTransfer()` function uses `tx.origin` only for logging and **should not be flagged as a vulnerability**.

I then prepared two different harness examples — one good and one bad. Each uses a different `SKILL.md` file, which changes the agent's harness behavior.

### 1. Good harness journey

- The **good harness** adds triage guidance: only treat `tx.origin` as a vulnerability when it actually gates authorization; logging/events are not findings.

- On the same task, it correctly identifies the vulnerability in `withdraw()` and ignores `logTransfer()`.

- The code grader marks it **PASS**, and the paired result is **IMPROVED**.

- It then passes the regression checks, so the capability can **graduate into the regression suite**.

- This gives us evidence that the harness change is actually improving the agent's ability to identify bugs.

### 2. Bad harness journey

- I took another harness change to show that a change to the `SKILL.md` can also make the agent worse.

- The **bad harness** focuses on "remediation" rather than correctly identifying and triaging vulnerabilities. It tells the agent to patch `tx.origin` and harden configuration, but this guidance causes the agent to **miss the actual `withdraw()` vulnerability**.

- The agent **fails the audit** because it completely misses the real vulnerability in `withdraw()`. Not flagging `logTransfer()` is correct, but the missing `withdraw()` finding is enough for the task to fail.

- Separately, the bad harness also causes a **regression in the existing `keep-suite` tests** by applying a destructive configuration change. So compared with the baseline, the candidate has **REGRESSED** on an existing test.

- Because of that regression, the candidate is **blocked from Phase 2** rather than being graduated.

## What problem this solves (coding-agent harness, not “another LLM benchmark”)

Teams ship **coding agents** (Claude Code, Codex, Cursor, etc.) with a **harness**: model + tools + **AGENTS.md**, **skills**, hooks, MCPs, and routing. Those files are edited often. The question is not “is the model smart?” but **“did this harness change actually improve outcomes before we roll it to everyone?”**

This repository is an **evaluation harness** around that question. It does **not** replace Claude Code; it models the same decision process:

1. Fix the **agent harness** you care about (here: guidance files under [`harnesses/`](harnesses/)).
2. Run the **same tasks** under **baseline** vs **candidate** with the **same model and tool loop** ([`src/eval/agent.py`](src/eval/agent.py)) so only the harness diff is intentional ([`ai/decisions.md`](ai/decisions.md)).
3. **Grade** outcomes with deterministic **code graders** ([`src/eval/graders.py`](src/eval/graders.py)) plus optional model rubric as evidence only.
4. **Compare** paired results and block bad rollouts ([`src/eval/compare.py`](src/eval/compare.py), [`src/eval/gate.py`](src/eval/gate.py)).
5. **Graduate** stable capability wins into regression gates ([`src/eval/promote.py`](src/eval/promote.py)).

Orchestration entrypoint: [`python3 -m eval`](src/eval/run.py). Full build spec: [`prompts/BUILD-HARNESS-EVAL-TOOL.md`](prompts/BUILD-HARNESS-EVAL-TOOL.md).

---

## Reference experiment: one baseline, two candidate harness changes

We use **one shared baseline** and two **candidate** guidance files to show that a harness change can help or hurt—not every “stricter” skill is an improvement.

| Arm                | Guidance file                                                            | What gets copied into the trial workspace                                                             |
| ------------------ | ------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| **Baseline**       | [`harnesses/baseline/AGENTS.md`](harnesses/baseline/AGENTS.md)           | Generic reviewer: flag **any** `tx.origin` / `msg.sender` use                                         |
| **Good candidate** | [`harnesses/good-candidate/SKILL.md`](harnesses/good-candidate/SKILL.md) | Triage skill: `tx.origin` vulnerable only when it **gates** auth; logging/events are **not** findings |
| **Bad candidate**  | [`harnesses/bad-candidate/SKILL.md`](harnesses/bad-candidate/SKILL.md)   | “Remediation” skill: patch `tx.origin` and harden config constants                                    |

Implementation detail: baseline copies `AGENTS.md`; candidate copies `SKILL.md` ([`src/eval/trial.py`](src/eval/trial.py) `copy_guidance`).

**Task (Solidity):** [`tasks/auth-vs-log/repo/Wallet.sol`](tasks/auth-vs-log/repo/Wallet.sol) — `withdraw()` uses `tx.origin` for **authorization** (must be reported vulnerable); `logTransfer()` uses `tx.origin` only in an **event** (must **not** be reported vulnerable). Held-out labels: [`tasks/auth-vs-log/heldout/expected.json`](tasks/auth-vs-log/heldout/expected.json) (never copied into the agent workspace).

### What each arm produces on `auth-vs-log` (committed dry-run artifacts)

| Arm                | `withdraw`                | `logTransfer`                   | Code grader | Why                                                                                                                                                      |
| ------------------ | ------------------------- | ------------------------------- | ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Baseline**       | vulnerable                | **vulnerable** (false positive) | **FAIL**    | Noisy rule treats logging like auth ([`mocks/baseline/auth-vs-log/findings.json`](mocks/baseline/auth-vs-log/findings.json))                             |
| **Good candidate** | vulnerable                | **not** vulnerable              | **PASS**    | Matches held-out triage ([`mocks/good-candidate/auth-vs-log/findings.json`](mocks/good-candidate/auth-vs-log/findings.json))                             |
| **Bad candidate**  | **missing** from findings | not vulnerable                  | **FAIL**    | Incomplete audit; never satisfies per-function labels ([`mocks/bad-candidate/auth-vs-log/findings.json`](mocks/bad-candidate/auth-vs-log/findings.json)) |

**Regression task** [`keep-suite`](tasks/keep-suite/): code grader runs `pytest -q tests` after the agent finishes ([`src/eval/graders.py`](src/eval/graders.py) `grade_keep_suite`). Good candidate leaves config/tests intact (**PASS**). Bad candidate mock applies a destructive config overlay ([`mocks/bad-candidate/keep-suite/overlay/`](mocks/bad-candidate/keep-suite/overlay/)) → **FAIL** while baseline still **PASS** → paired transition **REGRESSED** ([`output/bad-harness-example/summary.json`](output/bad-harness-example/summary.json)).

### Two full stories (same baseline, different candidates)

Compare two **agent harnesses** on the same tasks using the **same model and tools**. Only the candidate guidance file changes between stories.

The **evaluation harness** (this repo) runs trials, grades outcomes, compares baseline vs candidate, and can **graduate** capability tasks into the regression suite after phase 1.

Committed **dry-run** stories (no API key):

| Example folder                                                 | Candidate      | Phase 1                               | Phase 2                                           |
| -------------------------------------------------------------- | -------------- | ------------------------------------- | ------------------------------------------------- |
| [`output/good-harness-example/`](output/good-harness-example/) | good-candidate | **POSITIVE** (`auth-vs-log` IMPROVED) | Runs; suite graduates                             |
| [`output/bad-harness-example/`](output/bad-harness-example/)   | bad-candidate  | **NEGATIVE** (`keep-suite` REGRESSED) | **Blocked** (`phase_2_blocked_reason` in summary) |

---

## What this project does

1. **Phase 1** — Run each task twice per harness (`reps = 2`). Suite starts with **capability** `auth-vs-log` and **regression** `keep-suite`.
2. **Grade** — Code graders decide pass/fail; Haiku **model rubric** on capability tasks is evidence only (see [Limitations](#limitations)).
3. **Compare** — Per task: improved / regressed / unchanged / **unstable**.
4. **Graduate** — If the **candidate** passes every rep on capability tasks and no regression task **regresses**, promote capability tasks to `suite: regression`.
5. **Phase 2** — Re-run expanded regression (including graduated tasks) plus new capability `caller-check`. **Skipped** when phase 1 has a regression `REGRESSED` or capability gate failure.
6. **Artifacts** — Under `output/<good|bad>-harness-example/phase-1/` and optional `phase-2/`.

Configure which story to run in [`eval.config.yaml`](eval.config.yaml) (`scenario: good | bad | both`) or CLI `--scenario`.

---

## Directory map

| Path                                                                       | Purpose                                                            |
| -------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| [`src/eval/`](src/eval/)                                                   | Orchestration, agent loop, graders, compare, promote, gate, config |
| [`tasks/`](tasks/)                                                         | Task repos, prompts, held-out expectations, suite registry         |
| [`harnesses/baseline/`](harnesses/baseline/)                               | Shared baseline guidance                                           |
| [`harnesses/good-candidate/`](harnesses/good-candidate/)                   | Triage skill (improves capability)                                 |
| [`harnesses/bad-candidate/`](harnesses/bad-candidate/)                     | Over-remediation skill (breaks regression)                         |
| [`mocks/`](mocks/)                                                         | Dry-run findings + overlays (`bad-candidate/keep-suite/overlay/`)  |
| [`output/good-harness-example/`](output/good-harness-example/)             | Committed good story evidence                                      |
| [`output/bad-harness-example/`](output/bad-harness-example/)               | Committed bad story evidence                                       |
| [`presentation/`](presentation/)                                           | Deck builder and `output/harness-eval.pptx`                        |
| [`scripts/e2e_validate.sh`](scripts/e2e_validate.sh)                       | pytest + dry-run + deck smoke test                                 |
| [`prompts/BUILD-HARNESS-EVAL-TOOL.md`](prompts/BUILD-HARNESS-EVAL-TOOL.md) | Full sandbox spec                                                  |

---

## Execution commands

Run each line separately from the repository root.

```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
pip install -e ".[dev]"
```

```bash
export OPENROUTER_API_KEY=your-key-here
```

Required for a **live** run only.

```bash
cp tasks/registry.bootstrap.yaml tasks/registry.yaml
```

Resets suite tags before a fresh live phase 1.

```bash
python3 -m eval --dry-run
```

**No API calls.** Runs scenarios from `eval.config.yaml` (default `both`): writes `output/good-harness-example/` and `output/bad-harness-example/` using files under `mocks/`. Code graders, comparison, promotion, and phase-2 simulation (good only) still run.

```bash
python3 -m eval --dry-run --scenario good
```

```bash
python3 -m eval --dry-run --scenario bad
```

```bash
python3 -m eval --scenario good
```

Live run for good-candidate only (requires API key).

```bash
python3 -m eval --config path/to/eval.config.yaml
```

```bash
python3 presentation/src/build_deck.py
```

```bash
bash scripts/e2e_validate.sh
```

```bash
pytest -q
```

---

## Good harness example (`auth-vs-log`)

**Task:** [`tasks/auth-vs-log/repo/Wallet.sol`](tasks/auth-vs-log/repo/Wallet.sol) — `withdraw()` uses `tx.origin` for authorization (vulnerable); `logTransfer()` logs only (not vulnerable).

**Baseline** (noisy rule): flags **both** functions — code grader **FAIL** (see `output/good-harness-example/phase-1/baseline/trials/auth-vs-log/0/result/findings.json`).

**Good candidate** (triage skill): `withdraw` vulnerable, `logTransfer` not — code grader **PASS** both reps.

| Task        | Suite      | Baseline | Candidate | Transition |
| ----------- | ---------- | -------- | --------- | ---------- |
| auth-vs-log | capability | FAIL     | PASS      | IMPROVED   |
| keep-suite  | regression | PASS     | PASS      | UNCHANGED  |

Phase 1 verdict: **POSITIVE**. `auth-vs-log` graduates. Phase 2 adds `caller-check`; candidate improves on graduated regression and new capability (dry-run).

---

## Bad harness example (same baseline, worse candidate)

**Bad candidate** skill encourages patching code and hardening config. Dry-run mocks:

- `auth-vs-log`: omits `withdraw` in findings — still **FAIL** (missing label).
- `keep-suite`: overlay sets `API_VERSION` / `MAX_RETRIES` to values tests reject — candidate **FAIL**, baseline **PASS** → **REGRESSED**.

| Task        | Suite      | Baseline | Candidate | Transition |
| ----------- | ---------- | -------- | --------- | ---------- |
| auth-vs-log | capability | FAIL     | FAIL      | UNCHANGED  |
| keep-suite  | regression | PASS     | FAIL      | REGRESSED  |

Phase 1 verdict: **NEGATIVE**. `phase_2_blocked_reason`: regression task `keep-suite` regressed. **No `phase-2/` folder.**

Without paired eval, both skills could be described as “stricter security.” Only pytest + held-out labels separate them.

---

## Graders (deterministic gates vs supporting evidence)

Graders are implemented in [`src/eval/graders.py`](src/eval/graders.py) and tested in [`tests/test_graders.py`](tests/test_graders.py).

| Grader                   | Used for                      | How it works                                                                                                                                                                     | Gates promotion?                                                                  |
| ------------------------ | ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| **Code — held-out JSON** | `auth-vs-log`, `caller-check` | Compare `findings.json` to [`tasks/*/heldout/expected.json`](tasks/auth-vs-log/heldout/expected.json) per function (`vulnerable` or `classification`); optional `issue_contains` | **Yes** — pass/fail is deterministic                                              |
| **Code — pytest**        | `keep-suite`                  | Run [`pytest -q tests`](tasks/keep-suite/repo/tests/test_suite.py) in the post-agent workspace                                                                                   | **Yes**                                                                           |
| **Model rubric**         | Capability tasks (live runs)  | One Haiku call: does text separate auth vs logging? ([`grade_model_rubric`](src/eval/graders.py))                                                                                | **No** — recorded in `grade.json`; `model_disagreement` if it disagrees with code |
| **Human**                | SME calibration               | [`output/*/human_spot_check.md`](output/good-harness-example/human_spot_check.md) checklist                                                                                      | **No**                                                                            |

**Why this beats gut feel:** the good candidate’s harness change is accepted only when **held-out labels** and **tests** improve or hold steady across paired reps—not because the new `SKILL.md` “sounds” stricter. The bad candidate sounds stricter too, but **REGRESSED** on `keep-suite` and never reaches phase 2 ([`src/eval/gate.py`](src/eval/gate.py)).

Dry-run uses on-disk mocks ([`mocks/`](mocks/)) so reviewers see the same pass/fail story without API spend ([`src/eval/agent.py`](src/eval/agent.py) `apply_mock_transcript`).

---

## Output layout

```
output/
  good-harness-example/
    phase-1/ phase-2/
    summary.json
    human_spot_check.md
  bad-harness-example/
    phase-1/
    summary.json
    human_spot_check.md
  summary.json
```

---

## Presentation

[`presentation/output/harness-eval.pptx`](presentation/output/harness-eval.pptx) — built from both example summaries and real `findings.json` excerpts (baseline vs candidate for good and bad stories). Speaker notes script the e2e journey.

---

## Limitations

- **Two reps** — `UNSTABLE` is common; not rounded into wins.
- **Dry-run** — Deterministic mocks; live behavior may differ on stochastic model output.
- **Custom mini-agent** — read/list/write tools only.
- **Registry** — Live runs may update `tasks/registry.yaml`; reset with bootstrap.
- **Model grader** — Non-deterministic; code gates promotion.

---

## Related docs

- [`DESIGN.md`](DESIGN.md) — decisions, two stories, cuts
- [`ai/decisions.md`](ai/decisions.md) — why two candidates, phase-2 block rule
- [`prompts/BUILD-HARNESS-EVAL-TOOL.md`](prompts/BUILD-HARNESS-EVAL-TOOL.md) — full rebuild spec
- [`docs/NEXT_STEPS_BUILD_EVAL_AND_HILLCLIMB.md`](docs/NEXT_STEPS_BUILD_EVAL_AND_HILLCLIMB.md) — planned gaps vs Claude `build-eval` / `hillclimb` (review before implementing)
