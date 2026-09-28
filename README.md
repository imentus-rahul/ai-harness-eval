# Harness evaluation (simplified)

Compare two **agent harnesses** on the same tasks using the **same model and tools**. Only the guidance file changes: baseline [`harnesses/baseline/AGENTS.md`](harnesses/baseline/AGENTS.md) versus candidate [`harnesses/good-candidate/SKILL.md`](harnesses/good-candidate/SKILL.md) or [`harnesses/bad-candidate/SKILL.md`](harnesses/bad-candidate/SKILL.md).

The **evaluation harness** (this repo) runs trials, grades outcomes, compares baseline vs candidate, and can **graduate** capability tasks into the regression suite after phase 1.

Committed **dry-run** stories (no API key):

| Example folder | Candidate | Phase 1 | Phase 2 |
|----------------|-----------|---------|---------|
| [`output/good-harness-example/`](output/good-harness-example/) | good-candidate | **POSITIVE** (`auth-vs-log` IMPROVED) | Runs; suite graduates |
| [`output/bad-harness-example/`](output/bad-harness-example/) | bad-candidate | **NEGATIVE** (`keep-suite` REGRESSED) | **Blocked** (`phase_2_blocked_reason` in summary) |

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

| Path | Purpose |
|------|---------|
| [`src/eval/`](src/eval/) | Orchestration, agent loop, graders, compare, promote, gate, config |
| [`tasks/`](tasks/) | Task repos, prompts, held-out expectations, suite registry |
| [`harnesses/baseline/`](harnesses/baseline/) | Shared baseline guidance |
| [`harnesses/good-candidate/`](harnesses/good-candidate/) | Triage skill (improves capability) |
| [`harnesses/bad-candidate/`](harnesses/bad-candidate/) | Over-remediation skill (breaks regression) |
| [`mocks/`](mocks/) | Dry-run findings + overlays (`bad-candidate/keep-suite/overlay/`) |
| [`output/good-harness-example/`](output/good-harness-example/) | Committed good story evidence |
| [`output/bad-harness-example/`](output/bad-harness-example/) | Committed bad story evidence |
| [`presentation/`](presentation/) | Deck builder and `output/harness-eval.pptx` |
| [`scripts/e2e_validate.sh`](scripts/e2e_validate.sh) | pytest + dry-run + deck smoke test |
| [`prompts/BUILD-HARNESS-EVAL-TOOL.md`](prompts/BUILD-HARNESS-EVAL-TOOL.md) | Full sandbox spec |

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

| Task | Suite | Baseline | Candidate | Transition |
|------|-------|----------|-----------|------------|
| auth-vs-log | capability | FAIL | PASS | IMPROVED |
| keep-suite | regression | PASS | PASS | UNCHANGED |

Phase 1 verdict: **POSITIVE**. `auth-vs-log` graduates. Phase 2 adds `caller-check`; candidate improves on graduated regression and new capability (dry-run).

---

## Bad harness example (same baseline, worse candidate)

**Bad candidate** skill encourages patching code and hardening config. Dry-run mocks:

- `auth-vs-log`: omits `withdraw` in findings — still **FAIL** (missing label).
- `keep-suite`: overlay sets `API_VERSION` / `MAX_RETRIES` to values tests reject — candidate **FAIL**, baseline **PASS** → **REGRESSED**.

| Task | Suite | Baseline | Candidate | Transition |
|------|-------|----------|-----------|------------|
| auth-vs-log | capability | FAIL | FAIL | UNCHANGED |
| keep-suite | regression | PASS | FAIL | REGRESSED |

Phase 1 verdict: **NEGATIVE**. `phase_2_blocked_reason`: regression task `keep-suite` regressed. **No `phase-2/` folder.**

Without paired eval, both skills could be described as “stricter security.” Only pytest + held-out labels separate them.

---

## Graders (what checks what)

| Task | Code grader | Model rubric (live) |
|------|-------------|---------------------|
| `auth-vs-log` | Held-out [`expected.json`](tasks/auth-vs-log/heldout/expected.json) per function | Explanation quality only |
| `keep-suite` | `pytest -q tests` in workspace | N/A |
| `caller-check` | Held-out labels + `issue_contains: tx.origin` | Explanation quality only |

Code pass/fail gates promotion. Model disagreement is recorded in `grade.json` and does not override code.

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
