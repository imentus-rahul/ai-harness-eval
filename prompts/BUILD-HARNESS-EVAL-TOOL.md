# Master prompt: build a coding-agent harness evaluation tool

You are building a **take-home-quality** repository from scratch in an empty sandbox.
There is no existing codebase, no external monorepo, and no access to proprietary tools.
Everything required to understand, run, and review the project must live in the repository you create.

Read this entire prompt before writing code. Prefer clarity and a defensible experiment over feature breadth.

## 1. Mission
Your mission is to implement an **evaluation harness** that answers one question for engineering teams:

> When we change our coding-agent harness (instructions, skills, hooks, workflows, MCPs, model routing, etc.),  
> did we **actually improve** outcomes before rolling the change out to everyone?

The tool must:

1. Run the **same tasks** under two harness configurations (**baseline** vs **candidate**).
2. Capture **evidence** per trial (output, tools, tokens, latency, cost, errors).
3. **Grade** outcomes with multiple grader families (code-first; model and human as supporting evidence).
4. Produce a **paired comparison report** (improved, regressed, unstable, inconclusive).
5. Demonstrate a **capability → regression graduation loop** across two phases.
6. Include a **presentation deck** (with speaker notes) that explains the system to experienced AI engineers.
7. Ship a **one-page design note** and minimal process documentation.

Success is not a single confidence score. Success is a reviewer who can trace every claim to artifacts on disk.

## 2. Background problem (why this exists)
Engineering teams iterate on agent harnesses weekly. Someone adds a skill, swaps a model, introduces a guardrail, or changes default tools. Each change is made because someone **believes** it helps.

Today, the question “was that change good?” is usually answered by:

- Reading a handful of outputs
- Anecdotes in Slack
- Gut feel from the harness maintainer

That fails because **quality is multidimensional**:

- Does the code or analysis **work** (correctness)?
- Does it match **business intent** (fidelity)?
- Did we **break** what used to work (regression)?
- Does it follow **team conventions** (format, style, process)?
- What did it **cost** (tokens, latency, dollars)?

Your tool makes harness changes **measurable** and **paired**, so teams can distinguish real improvement from noise.

## 3. Core terminology (use consistently)
Define and use these terms in code, docs, and the deck:

| Term | Definition |
|------|------------|
| **Task** | A problem statement: inputs (repo + prompt), plus success/acceptance criteria enforced by graders. |
| **Trial** | One execution of one agent harness on one task in an isolated workspace (may include multiple LLM turns). |
| **Transcript** | Fingerprint of a trial: final output, tool calls, token usage, timing, errors, intermediate reasoning if captured. |
| **Outcome** | Final state in the environment after the agent stops (files written, tests state), as judged by graders. |
| **Agent harness** | The process that lets a model act as an agent: model, tools, instructions/skills, budgets, command. |
| **Evaluation harness** | Your tool: schedules trials, runs graders, compares arms, manages suite graduation. |
| **Evaluation suite** | Collection of tasks tagged as **capability** or **regression** evals. |
| **Grader** | Logic that scores or pass/fails a trial outcome. |
| **Capability eval** | Probes what the agent **can** do well (learning, expansion). |
| **Regression eval** | Probes what **must keep working** after changes (gates). |

**Capability vs regression lifecycle:**

- Phase 1: you have *x* capability evals and *y* regression evals.
- When capability evals show a **high, stable** pass rate on the candidate harness, **graduate** them into regression evals.
- Phase 2: you add *z* new capability evals; regression suite becomes *x + y* (graduated tasks included).

Automate this graduation in code and show it in the presentation.

## 4. What an eval must do (three jobs)
Every task in your suite should illustrate all three jobs:

1. **Unambiguous specification** — For input X, output Y (or labeled outcome Z).  
   Example: `tx.origin` used for **authorization** is a vulnerability; `tx.origin` used only for **logging** is not.

2. **Regression protection** — Did the last harness change break something that previously worked?

3. **Development feedback** — Is the candidate harness actually better than baseline on capability tasks?

Your example experiment should make these three jobs obvious in the report and deck.

## 5. Controlled experiment (non-negotiable)
The headline comparison must change **one intentional variable** between baseline and candidate.

**Required for the reference implementation:**

- Same hosted model (use a **cheap Haiku-class** model via an OpenAI-compatible API such as OpenRouter).
- Same tool surface and agent loop implementation.
- Same task prompts and repos.
- Only difference: **guidance files** (e.g. generic `AGENTS.md` vs a focused `SKILL.md`).

Do **not** compare local tiny models vs cloud frontier models in the primary demo; that confounds harness quality with model capability.

Document the controlled variable explicitly in README and DESIGN.md.

State what would break attribution if someone changed multiple variables at once.

## 6. Reference task suite (semantic content)
Implement **three tasks** with small on-disk repos (no external git dependencies).

### Task A: `auth-vs-log` (capability)

- Repo contains a minimal Solidity-style contract (`.sol` file is fine) with:
  - `withdraw()` — uses `tx.origin` for **authorization** → **vulnerable**.
  - `logTransfer()` — uses `tx.origin` only in an **event** → **not vulnerable**.
- Agent must write `findings.json` at repo root with per-function classification.
- **Held-out expectations** live outside the agent workspace (e.g. `heldout/expected.json`) and are applied only when grading.

### Task B: `keep-suite` (regression)

- Small Python package with `app/config.py` constants and `tests/test_suite.py`.
- Prompt tells the agent not to break config/tests; may write empty findings.
- **Code grader** runs `pytest -q tests` in the workspace after the agent finishes.

### Task C: `caller-check` (capability; phase 2 only)

- Contract with `withdrawAll()` using `tx.origin` in a `require` where `msg.sender` semantics matter.
- Held-out expectation: flag `withdrawAll` as vulnerable; issue should mention `tx.origin`.

### Suite registry

- YAML registry maps `task_id → suite: capability|regression`.
- Ship a **bootstrap** registry for fresh runs and commit **post-graduation** state in docs or output if helpful.

## 7. Harness arms (shared baseline vs two candidates)
### Baseline harness guidance (`harnesses/baseline/AGENTS.md`)

Generic security reviewer instructions:

- Write `findings.json` with `function`, `vulnerable`, `issue`, `detail`.
- Bias: treat **any** `tx.origin` / `msg.sender` touch as a likely auth bug (intentionally noisy).

### Good candidate (`harnesses/good-candidate/SKILL.md`)

Skill-style triage instructions:

- `tx.origin` is vulnerable **only** when it **gates** privileged actions (withdraw, ownership, spends).
- Logging/events/analytics using `tx.origin` are **not** findings.
- Prefer `msg.sender` for access control; call out `tx.origin` misuse where relevant.

### Bad candidate (`harnesses/bad-candidate/SKILL.md`)

Stricter-sounding remediation instructions:

- Patch or remove `tx.origin`; harden Python config constants when reviewing services.
- Dry-run mocks: incomplete `auth-vs-log` findings; `keep-suite` overlay breaks pytest.

Run **two reference stories** against the **same baseline**:

- `output/good-harness-example/` — candidate improves capability, regression unchanged → phase 2.
- `output/bad-harness-example/` — regression `keep-suite` REGRESSED → phase 2 blocked.

The presentation must show side-by-side **baseline vs candidate findings** for both stories where they differ.

## 8. Agent loop requirements
Implement a **minimal** agent harness (stdlib HTTP to OpenAI-compatible chat completions):

**Tools (suggested minimum):**

- `read_file(path)`
- `list_files(path)`
- `write_file(path, content)`

**Loop:**

- System message includes harness guidance copied into the workspace.
- User message is the task prompt.
- Support tool calls until the model stops with content or you hit `max_turns`.
- Enforce `max_cost_usd` per trial; record budget exceed as an error.

**Model:**

- Default: `anthropic/claude-haiku-4.5` on OpenRouter (or current Haiku slug if renamed).
- Read API key from `OPENROUTER_API_KEY` only; never commit secrets.

**Metrics per trial (write as files, not only aggregated JSON):**

- Latency (wall clock); time-to-first-token when streaming provides it.
- Token in/out/total; `cost_usd` with `cost_source` = `reported` | `computed` | `mock`.
- Ordered tool trace.
- Errors log (write `none` when empty).

**Repetitions:**

- `reps = 2` per task per harness for the demo (enough to show stability vs flake, not enough for p-values).

## 9. Trial isolation
For each trial:

1. Copy task `repo/` into a fresh workspace directory (no shared state between trials).
2. Copy harness guidance into workspace **before** grading (as files the agent can read).
3. Run the agent subprocess/logic.
4. Persist transcript + artifacts under `output/<phase>/<harness>/trials/<task>/<rep>/`.
5. Run graders on the final workspace.

Never let trial N read trial N-1 artifacts. Never let the agent read held-out grader files.

## 10. Grader families
Implement three grader **types** in documentation and at least two in automation.

### Code-based graders (gate promotion)

Methods to support in docs and tests:

- String/structured matching on `findings.json`.
- Binary pass/fail against held-out expected labels per function.
- Outcome verification via `pytest` for regression tasks.
- Optional: tool-call verification if you log tools (not required for minimal scope).

**Rule:** Code grader pass/fail **decides** task pass and graduation.

### Model-based graders (evidence only)

- One cheap Haiku rubric call per capability trial when not in dry-run.
- Prompt: does the explanation separate authorization vs logging for `tx.origin`?
- Output: PASS/FAIL line + reason.
- If model disagrees with code, set `model_disagreement` and **do not** override code.

### Human graders (workflow)

- Export `human_spot_check.md` checklist for SME review of capability transcripts.
- Do not fabricate inter-annotator statistics.

Document strengths/weaknesses of each family in the deck (fast/objective vs nuanced/expensive).

## 11. Comparison logic
For each task, collect pass booleans for baseline and candidate across reps.

**Outcomes:**

- All reps pass → `PASS`
- All reps fail → `FAIL`
- Mixed → `UNSTABLE` (do not round into improved/regressed)

**Transitions (paired):**

- FAIL→PASS → `IMPROVED`
- PASS→FAIL → `REGRESSED`
- PASS→PASS or FAIL→FAIL → `UNCHANGED`
- Any UNSTABLE involved → `UNSTABLE` transition

**Phase verdict:**

- `REGRESSED` > 0 → `NEGATIVE`
- Else `IMPROVED` > 0 and no regressions → `POSITIVE`
- Else → `INCONCLUSIVE`

Write `comparison/result.json` and `comparison/README.md` per phase.

## 12. Graduation gate (pass^k)
After phase 1:

- For each **capability** task, look at **candidate** reps only.
- If all reps pass (pass^k = 1 at k=reps), **promote** task to `suite: regression` in registry with timestamp and run id.
- If gate fails, **skip phase 2** or run phase 2 only in dry-run simulation—document chosen behavior; preferred: skip live phase 2 when gate fails.

Phase 2 task list:

- All regression tasks (including newly graduated).
- One **new** capability task (e.g. `caller-check`).

Show suite growth in deck: before/after task counts.

## 13. Orchestration CLI
Single entrypoint:

```bash
python3 -m eval
```

Configuration: `eval.config.yaml` at repo root:

```yaml
scenario: both   # good | bad | both (both = good+bad on --dry-run)
candidate: good-candidate
```

Flags:

- `--dry-run` — no API calls; load mocks from `mocks/` (see section 14).
- `--scenario good|bad|both` — overrides config scenario.
- `--config path` — alternate YAML config file.
- `--model` — override model id (default Haiku).

Phases (per scenario):

1. Reset registry from bootstrap → run phase 1 under `output/<good|bad>-harness-example/`.
2. Compare → promote capability tasks if candidate pass^k and no regression REGRESSED.
3. Run phase 2 only when eligible; else set `phase_2_blocked_reason` in `summary.json`.
4. Write per-example `summary.json` and `human_spot_check.md`.

Keep dependencies minimal: PyYAML, pytest, python-pptx for deck; stdlib for HTTP.
Avoid Typer/Pydantic/Rich unless you have strong reason.

## 14. Dry-run mode (CI and reviewers without API keys)
`python3 -m eval --dry-run` must:

- Skip OpenRouter calls.
- Load findings from `mocks/<baseline|good-candidate|bad-candidate>/<task>/findings.json`.
- Apply optional `mocks/.../overlay/` into the workspace (bad `keep-suite` breaks pytest).
- Still run real code graders and full comparison/graduation flow per scenario.
- **Good scenario:** phase 2 runs after promotion.
- **Bad scenario:** phase 1 NEGATIVE on `keep-suite` REGRESSED; no `phase-2/` directory.
- Set `cost_usd` to 0 and `cost_source` to `mock`.

Output directories:

- `output/good-harness-example/phase-1`, optional `phase-2`, `summary.json`
- `output/bad-harness-example/phase-1`, `summary.json` with `phase_2_blocked_reason`
- `output/summary.json` — index when both scenarios run

Document dry-run prominently in README.

## 15. Output layout (reviewer-first)
Separate **source** from **generated evidence**.

```
harnesses/baseline/  good-candidate/  bad-candidate/
mocks/baseline/  good-candidate/  bad-candidate/
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
presentation/
  src/build_deck.py
  output/harness-eval.pptx
eval.config.yaml
```

Each harness README: short table of trials (task, rep, pass, cost, latency).

Comparison README: verdict + per-task transitions.

Do not mix generated JSON into `src/`.

## 16. Presentation deck requirements
Build `presentation/output/harness-eval.pptx` from committed `output/` metrics (script in `presentation/src/`).

**Speaker notes on every slide.**

Suggested storyline (~18 slides):

1. Pain: harness changes ship on opinions.
2. False belief: any change is progress.
3. Terminology.
4. Three jobs of evals (mapped to tasks).
5. Controlled experiment (one variable; two candidates).
6. Shared task suite.
7. Graders: what checks what.
8. How to read comparison artifacts.
9. Good candidate: skill intent.
10. Good phase 1: baseline vs candidate `findings.json` excerpts.
11. Good phase 2: graduation + caller-check.
12. Bad candidate: remediation skill intent.
13. Bad phase 1: worse regression outcome; `phase_2_blocked_reason`.
14. Same baseline, two verdicts side by side.
15. Without this tool (perception vs evidence).
16. Limits and policy.
17. How to run (`eval.config.yaml`, `--scenario`, dry-run).

Include real dry-run `findings.json` on slides for **both** good and bad examples. Speaker notes must script the talk, not duplicate bullets.

## 17. DESIGN.md (hard limit: one page)
Include:

- Concepts table (short).
- Five hardest engineering decisions (paired comparison, held-out tests, UNSTABLE handling, cost tracking, graduation).
- What you cut and why.
- One result you did not fully trust (e.g. model rubric vs code grader) and what you did about it.

## 18. README requirements
README must let a reviewer run the tool in minutes:

- What the project does (plain language).
- Directory map.
- **One command per line** for: venv, install, env var, bootstrap registry, eval, dry-run eval, deck build, pytest.
- Explain dry-run mocks source and output paths.
- Walk through the reference example: what baseline found vs candidate, graders used, which harness wins and why.
- Table of multi-rep results per harness.
- Explain phase 2 inconclusive if observed (UNSTABLE transitions).
- Limitations bullet list (honest).

## 19. Testing requirements
`pytest` without network:

- Code grader accepts multiple finding JSON shapes (boolean `vulnerable` vs `classification` strings).
- Comparison transitions (IMPROVED, REGRESSED, UNSTABLE).
- Promotion only when all candidate reps pass.

Run `pytest -q` in CI instructions.

## 20. Cost and safety constraints
- Per-trial budget cap (~$0.05).
- Total demo budget target well under $2 on OpenRouter Haiku.
- No Opus/Sonnet in automated grading or agent loop for the default demo.
- Rotate any API key exposed during development; never print keys in manifests committed to git.

## 21. Take-home implementation style
Follow these engineering norms:

- Smallest valid solution; no enterprise frameworks.
- Multiple small files with clear names (`run.py`, `agent.py`, `graders.py`, `compare.py`, `promote.py`, `report.py`).
- Obvious `output/` tree for two harnesses and comparison.
- One complete execution example committed under `output/` when possible.
- Comments explain intent, not every line.
- No fake configurability or plugin systems.
- Process docs: `AGENTS.md` (repo-specific), `ai/decisions.md` (why one variable, why code grader gates).

Do not dump entire chat transcripts into the repo.

## 22. Sandbox execution assumptions
The builder agent has:

- Python 3.10+
- Network for optional live OpenRouter run
- No pre-existing clone of any reference implementation
- Ability to create files, venv, pip install, run pytest

The repository must be **self-contained**: tasks, harnesses, src, tests, presentation, docs.

A reviewer cloning only this repo can:

1. `pip install -e ".[dev]"`
2. `python -m eval --dry-run`
3. Open `output/` and the pptx

## 23. Anti-patterns (reject during self-review)
- Single composite score hiding per-dimension outcomes.
- Comparing different models in the primary story.
- Letting the agent read held-out tests.
- Treating model rubric PASS as overriding code FAIL.
- Rounding UNSTABLE into improved counts.
- 40-slide architecture tour instead of experiment evidence.
- Empty output folders or fabricated metrics not produced by `python -m eval`.

## 24. Deliverables checklist
- [ ] `src/eval` package with `python -m eval`
- [ ] Three tasks with repos + held-out expectations
- [ ] Baseline vs candidate harness guidance files
- [ ] `output/` from dry-run and/or live run
- [ ] `presentation/output/harness-eval.pptx` with speaker notes
- [ ] `DESIGN.md` (one page)
- [ ] `README.md` (extended, commands one per line)
- [ ] `AGENTS.md`, `ai/decisions.md`
- [ ] `tests/` green
- [ ] `tasks/registry.bootstrap.yaml` for reset

## 25. Expected qualitative outcomes (sanity check)
**Good scenario (dry-run and typical live good-candidate):**

- Baseline flags `logTransfer` vulnerable; good candidate does not; `auth-vs-log` IMPROVED.
- `keep-suite` PASS both arms; phase 1 POSITIVE; phase 2 runs.

**Bad scenario (dry-run bad-candidate):**

- `auth-vs-log` still FAIL on candidate (incomplete findings).
- `keep-suite` REGRESSED (candidate breaks pytest via overlay); phase 1 NEGATIVE; phase 2 blocked.

Live runs may still show **INCONCLUSIVE** phase 2 on stochastic reps—document honestly when `UNSTABLE` appears.

## Appendix A — Example findings.json schema

Agents may emit either:

```json
{"findings": [{"function": "withdraw", "vulnerable": true, "issue": "...", "detail": "..."}]}
```

or a list of objects with `classification`: `VULNERABLE` | `NOT A FINDING`.

Graders must normalize both.

## Appendix B — Example phase 1 comparison row

| task | suite | baseline | candidate | transition |
|------|-------|----------|-----------|--------------|
| auth-vs-log | capability | FAIL | PASS | IMPROVED |
| keep-suite | regression | PASS | PASS | UNCHANGED |

## Appendix C — OpenRouter request shape

POST `/chat/completions` with `stream: true` for TTFT.

Collect `usage` from final stream chunks when present.

Headers: `Authorization: Bearer $OPENROUTER_API_KEY`.

## Appendix D — Human spot-check questions

1. Did the candidate correctly withhold a finding on logging-only `tx.origin`?
2. Is the withdraw finding explained as authorization, not generic tx.origin hate?
3. Would you ship the candidate harness to the team based on this transcript alone?

## Appendix E — Graduation YAML example

```yaml
tasks:
  auth-vs-log:
    suite: regression
    graduated_utc: <iso>
    graduated_from_run: phase-1
  keep-suite:
    suite: regression
  caller-check:
    suite: capability
```

## Appendix F — Why UNSTABLE matters

With 2 reps, a single flake prevents claiming IMPROVED on that task in phase 2.

This is intentional: better INCONCLUSIVE than false confidence.

## Appendix G — File naming conventions

Use kebab-case task ids.

Use `grade.json` beside `transcript.json` per trial.

## Appendix H — Deck data binding

`build_deck.py` should read:

- `output/good-harness-example/summary.json`
- `output/bad-harness-example/summary.json`
- `output/*/phase-1/comparison/result.json`

Findings slides: `output/<example>/phase-1/{baseline,candidate}/trials/auth-vs-log/0/result/findings.json`.

## Appendix I — Security review domain nuance

`tx.origin` phishing class: contract intermediary tricks owner EOA.

Logging `tx.origin` misattributes identity but is not the same severity as fund theft.

Your candidate skill encodes that distinction.

## Appendix J — Regression task philosophy

`keep-suite` ensures harness changes do not encourage destructive edits.

Passing both arms shows the change is not blatantly harmful to unrelated code.

## Appendix K — Limitations to document

- n=2 reps
- No parallel trial execution requirement
- No Claude Code / Codex CLI integration in minimal scope
- No automatic flake retry
- Model grader non-deterministic
- Single human spot-check template (no kappa)
- Agent loop is custom mini-agent, not a production framework

## Appendix L — Command reference (copy to README)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
export OPENROUTER_API_KEY=...
cp tasks/registry.bootstrap.yaml tasks/registry.yaml
python3 -m eval --scenario good
python3 -m eval --dry-run
python3 presentation/src/build_deck.py
bash scripts/e2e_validate.sh
pytest -q
```

## Appendix M — Glossary for slides

**Evaluation harness** — this repository's orchestrator.

**Agent harness** — model + tools + guidance used inside each trial.

**Trial** — one run; may include multiple LLM turns until stop or budget.

**Transcript** — persisted record of that trial.

## Appendix N — Success metrics for the builder agent

1. Reviewer understands experiment in <5 minutes via README + output tree.
2. Dry-run works offline.
3. Live run completes under budget cap.
4. Deck matches numbers in `output/summary.json`.
5. Tests pass without network.

## Appendix O — Optional extensions (explicitly out of scope)

- Pairwise LLM judge across full transcripts
- SWE-bench scale task suites
- Web dashboard
- Statistical tests at n=2 (misleading; do not add)

## Appendix P — Evidence chain

Report number → trial directory → transcript + grade → workspace findings → held-out expected.

Every link must be inspectable.

## Appendix Q — Tone for documentation

Write like a senior engineer handing off to another developer.

No marketing adjectives.

State trade-offs plainly.

## Appendix R — Phase 2 narrative

After graduation, `auth-vs-log` is a **gate**: candidate must keep passing.

Flaky rep on regression task yields UNSTABLE phase verdict.

New capability `caller-check` tests generalization.

## Appendix S — Model ID fallback

If `anthropic/claude-haiku-4.5` 404s on OpenRouter, probe:

- `anthropic/claude-3-haiku`
- current Haiku slug from provider docs

Document chosen default in README.

## Appendix T — Workspace guidance copy

Baseline copies `harnesses/baseline/AGENTS.md`.

Candidate copies `harnesses/good-candidate/SKILL.md` or `harnesses/bad-candidate/SKILL.md` per scenario.

Agent system prompt should reference reading these files or embed their content.

## Appendix U — Error handling policy

If API fails, record error in `errors/execution.log` and fail code grader (missing findings).

Do not silently succeed.

## Appendix V — compare.py purity

Comparison functions should be deterministic given pass lists.

Keep them free of I/O for easy unit tests.

## Appendix W — promote.py purity

Promotion mutates registry YAML on disk only when gate passes and not dry-run (or document dual behavior).

## Appendix X — report.py responsibilities

Render harness README tables and comparison markdown/json.

Keep formatting logic out of `run.py` when possible.

## Appendix Y — ai/decisions.md template

- Why one variable
- Why Haiku only
- Why code grader gates
- Why dry-run mocks exist
- What was cut

## Appendix Z — Final Self-Review Questions

### Final Self-Review Checklist

1. **Attribution:** Can I confidently attribute the Phase 1 improvement to the guidance alone?
2. **Evaluation integrity:** Are all held-out labels completely invisible to the agent during the run?
3. **Artifact traceability:** Does `output/` tell the complete story without requiring someone to inspect `src/`?
4. **Phase 2 reliability:** Would I trust the Phase 2 inconclusive wording when `UNSTABLE` appears?
5. **Presentation clarity:** Are the baseline and candidate findings visibly different in the deck?
6. **Numeric traceability:** Does every numeric claim in the deck map directly to a file under `output/`?

---

### Core Principles

#### 1. Paired Evaluation

**Elaboration:**
Paired evaluation is the only fair way to compare harnesses when tasks are stochastic.

**Implementation:**
Traceability beats clever abstractions. Every result should be traceable back to the run, inputs, configuration, and artifacts that produced it.

**Documentation:**
Show contrasting artifacts, not adjectives. Demonstrate the difference between baseline and candidate outputs rather than describing one as simply "better."

**Testing:**
Graders are the contract. Keep them strict, deterministic where possible, and independently tested.

---

#### 2. Cost Metrics

**Elaboration:**
Cost metrics must always identify their source because providers may omit billing fields or report incomplete usage information.

**Implementation:**
Traceability beats clever abstractions. Preserve the source and calculation path for every reported cost metric.

**Documentation:**
Show contrasting artifacts, not adjectives. Make the source and calculation visible rather than presenting unexplained cost numbers.

**Testing:**
Graders are the contract. Verify that cost reporting behaves correctly when provider billing fields are missing, incomplete, or unavailable.

---

#### 3. Tool Traces

**Elaboration:**
Tool traces help debug harnesses that over-call `write_file` or skip `read_file`.

**Implementation:**
Traceability beats clever abstractions. Preserve enough tool-call information to understand what the harness actually did.

**Documentation:**
Show contrasting artifacts, not adjectives. Use traces or representative artifacts to demonstrate behavioral differences.

**Testing:**
Graders are the contract. Test for undesirable tool-use patterns explicitly rather than relying on subjective review.

---

#### 4. Capability Tasks

**Elaboration:**
Capability tasks should be difficult enough that the baseline fails reliably during live runs. Otherwise, the evaluation cannot demonstrate whether the candidate harness provides a meaningful capability improvement.

**Implementation:**
Traceability beats clever abstractions. Make task outcomes and failure reasons observable.

**Documentation:**
Show contrasting artifacts, not adjectives. Show concrete baseline failures alongside candidate results.

**Testing:**
Graders are the contract. Ensure the grader can reliably distinguish successful capability improvements from incidental variation.

---

#### 5. Regression Tasks

**Elaboration:**
Regression tasks should be easy enough that both arms pass unless the harness is destructive. Their purpose is to detect regressions, not to introduce unnecessary difficulty.

**Implementation:**
Traceability beats clever abstractions. Make it clear when a failure is caused by the harness rather than the underlying task.

**Documentation:**
Show contrasting artifacts, not adjectives. Demonstrate that expected behavior is preserved across both arms.

**Testing:**
Graders are the contract. Regression graders should be strict about destructive or unintended behavior while allowing normal variation.

---

#### 6. Graduation

**Elaboration:**
Graduation is a product metaphor for tests promoted from experimental evaluations to CI gates.

**Implementation:**
Traceability beats clever abstractions. A graduated test should have a clear history, stable inputs, explicit expectations, and reproducible results.

**Documentation:**
Show contrasting artifacts, not adjectives. Document why a test graduated and what behavior it protects.

**Testing:**
Graders are the contract. Only promote tests whose grading logic is reliable enough to act as a CI gate.

---

#### 7. Presentation / Deck

**Elaboration:**
The deck is part of the deliverable and should be optimized for a senior AI engineer audience.

**Implementation:**
Traceability beats clever abstractions. Every important claim should be traceable to an artifact or result.

**Documentation:**
Show contrasting artifacts, not adjectives. Prefer concrete outputs, diffs, traces, and measurements over qualitative descriptions.

**Testing:**
Graders are the contract. Every numeric or factual claim presented in the deck should be verifiable against the underlying artifacts.

**Additional requirement:**
Every numeric claim in the deck must match a corresponding file under `output/`.

---

#### 8. Speaker Notes

**Elaboration:**
Speaker notes should script what to say, not duplicate the slide bullets verbatim.

**Implementation:**
Traceability beats clever abstractions. Notes should provide the reasoning and context behind the artifacts shown on the slide.

**Documentation:**
Show contrasting artifacts, not adjectives. Use notes to explain what the audience should notice in the evidence.

**Testing:**
Graders are the contract. Verify that the deck, notes, and underlying artifacts remain consistent.

---

#### 9. Secrets and Trial Manifests

**Elaboration:**
Do not commit API keys in trial manifests. If environment expansion is captured for debugging, redact all secrets before storing the artifact.

**Implementation:**
Traceability beats clever abstractions. Preserve useful configuration evidence without exposing credentials.

**Documentation:**
Show contrasting artifacts, not adjectives. Demonstrate configuration behavior using sanitized examples.

**Testing:**
Graders are the contract. Add checks that prevent credentials or other sensitive values from appearing in committed artifacts.

---

#### 10. Implementation Simplicity

**Elaboration:**
Use `pathlib` and the standard-library `subprocess` module. Avoid heavy CLI frameworks unless there is a concrete need for them.

**Implementation:**
Traceability beats clever abstractions. Prefer simple, inspectable code that makes execution flow obvious.

**Documentation:**
Show contrasting artifacts, not adjectives. The implementation should be understandable from the repository structure and generated outputs.

**Testing:**
Graders are the contract. Keep the execution path simple enough that tests can exercise the actual behavior rather than framework-specific abstractions.

---

#### 11. JSON Artifacts

**Elaboration:**
Pretty-printed JSON improves human review, especially when inspecting artifacts directly in the GitHub UI.

**Implementation:**
Traceability beats clever abstractions. Store structured results in a format that is easy to inspect and diff.

**Documentation:**
Show contrasting artifacts, not adjectives. JSON artifacts should make the underlying results independently reviewable.

**Testing:**
Graders are the contract. Validate the structure and required fields of generated JSON rather than relying only on visual inspection.