---
name: assignment-creation
description: Build assignment solutions (take-home challenges, coding tests, technical interview exercises, hiring assessments, benchmarks, comparisons of tools/models/harnesses) so they are simple, easy to review, easy to run, and clearly organized, with source code, generated output, presentation, and AI-workflow documentation kept separate. Use this skill whenever the user mentions an assignment, take-home, challenge, coding test, assessment, submission, reviewer, "compare A vs B", execution output, cost/token tracking, a PPT/presentation for the assignment, or CLAUDE.md/AGENTS.md/skills for such a project, even if they never say "assignment creation". Covers requirement extraction, minimal code, repository layout, one real execution, per-run READMEs, evidence capture, presentation build, agentic AI documentation, and a final review checklist.
---

# Assignment Creation

Use this skill to build the solution to an assignment so that a reviewer can understand it in minutes.

The reviewer is busy and will skim. They judge whether the requested problem was solved clearly. They do not reward how much architecture was built around it. Every rule below serves that reader. When two rules seem to conflict, choose the option that is simpler for the reviewer to read and run.

Read this whole file before you start. The ordered workflow is in section 2. The sections after it are the detailed rules that the workflow refers to.

## Words used in this skill

| Word | Meaning |
|---|---|
| Assignment | The task description you were given. |
| Requirement | One thing the assignment explicitly asks for. |
| Implementation | One approach being built or compared: a tool, model, harness, agent, algorithm. Use the assignment's own word for it (for example "harness"). |
| Execution / run | Running the code once against the input. |
| Output / evidence | Files produced by running the code. Never written by hand. |
| Reviewer | The person who will read the repository. |
| Slop | Generated-looking material that reviewers delete: needless abstraction, generic utility files, obvious comments, bloated docs, fake configurability. |

---

## 1. Goal and core principle

The repository must make it immediately obvious:

1. What the assignment asks for
2. Where the source code is
3. How to run it
4. Where the execution output is
5. What happened during the execution
6. How the final presentation was generated

The solution must be:

* Simple to understand
* Easy to review
* Easy to run
* Clearly organized
* Minimal without being cryptic
* Focused strictly on the requirements
* Written like practical developer code, not AI-generated demo code

**Core principle: make the reviewer understand the solution before they have to understand the implementation.** Use the simplest structure that makes the work obvious. If a simpler implementation satisfies the assignment, choose it. Write code that another developer would be comfortable editing tomorrow.

---

## 2. Workflow: follow these steps in order

Do not skip steps. Do not start coding before step 1 and step 2 are done.

1. **Read the whole assignment and write a requirements checklist.** One line per requirement, in the assignment's own words. Include the deliverables (code, output, presentation, README, and so on), the constraints (language, tools, slide count, time limits), and the evaluation criteria if the assignment states them. You will use this list again in the final review. See section 3.1.
2. **Decide the shape of the repository.** Answer these questions:
   * Is there one implementation, or are two or more being compared?
   * Does the assignment provide input files, or does it need one? If yes, plan an `input/` folder.
   * Is a presentation required? If yes, plan `presentation/`.
   * Is a coding agent being used, or does the assignment mention agentic AI? If yes, plan the agent files in section 9.
3. **Create only the folders that will hold real files.** No empty placeholder folders. See section 5.
4. **Write shared code first (if any), then each implementation, then the entry point** (`src/index.js`). Keep every file small and focused. See section 4.
5. **Wire one command that runs everything**, usually `npm run assignment`. See section 6.2.
6. **Run it for real.** Read the generated output. Fix problems and run again until the output is correct. If you cannot run it, follow section 6.9. Never fake output.
7. **Write the execution READMEs from the actual results,** after the run, never before. See section 7.2.
8. **If two or more implementations exist, generate the comparison from the actual results.** See section 6.6.
9. **Build the presentation from the actual output files,** if a presentation is required. See section 8.
10. **Write the root README, the agent files, and `ai/decisions.md`** (only the ones section 9 says are needed).
11. **Do the final review.** Go through the checklist in section 11 and remove slop (section 10). If removing something makes the solution easier to understand without losing a requirement, remove it.
12. **Send the final reply to the user** using the format in section 12.

---

## 3. Scope: solve only what was asked

### 3.1 Requirements checklist

Before writing code, list every requirement. Then, for each one, know which file will satisfy it. Do not invent requirements. If a feature is not on the list, do not build it.

Example:

```text
1. Run the same task with two harnesses          -> src/harness-a.js, src/harness-b.js
2. Record token usage and cost for each          -> common/cost.js, output/*/cost/
3. Compare the results                           -> src/compare.js, output/comparison/
4. Deliver a presentation                        -> presentation/
```

### 3.2 Start with the simplest valid solution

Implement the bare minimum required by the assignment. Prefer this shape:

```text
read input
process input
write result
```

over this shape:

```text
InputManager
ExecutionManager
ResultProcessor
ReportFactory
OutputStrategy
ExecutionContext
```

Only use the second shape if the problem genuinely requires those abstractions. It almost never does.

### 3.3 Do not add these unless the assignment asks for them

* Frameworks that are not necessary
* Extra CLI features or flags
* Configuration systems
* Plugin systems
* Generic abstractions
* Dependency injection
* Complex class hierarchies
* Extensive error handling for impossible scenarios
* Multiple execution modes
* Multiple examples
* Extra reports that were not requested

### 3.4 When the assignment is ambiguous

Pick the simplest reasonable interpretation, build it, and write one line in the root README "Notes" section saying what you assumed. Ask the user a question only when the ambiguity blocks the work completely (for example, a required input file is missing).

---

## 4. Code

### 4.1 Prefer obvious code over clever code

Good:

```js
const result = await runHarness(input);
await writeResult(result);
```

Avoid:

```js
const result = await executionOrchestrator
  .withContext(contextFactory.create(input))
  .execute()
  .then(resultTransformer.transform)
  .then(outputCoordinator.persist);
```

The first version is easier to review and easier to debug. Prefer plain functions over classes. Use a class only when object state or lifecycle genuinely helps.

### 4.2 Naming

Names should sound like something a developer would naturally write.

* Use descriptive function names: `runHarness()`, `parseResult()`, `writeReport()`, `calculateCost()`.
* Avoid vague names such as `process()`, `handle()`, `executeThing()`, `doWork()`, `manage()`, unless the scope makes the meaning genuinely obvious.
* Prefer short file names when the responsibility is obvious: `run.js`, `parse.js`, `compare.js`, `report.js`, `cost.js`.
* Prefer `harnessA`, `harnessB`, `result`, `usage`, `errors` over verbose names such as `harnessAExecutionResultProcessor`.
* Use the vocabulary of the assignment. If the assignment says "harness", call it a harness. Do not invent terminology to sound sophisticated.

### 4.3 Functions

Each function has one obvious responsibility.

Good:

```text
runHarness()
parseOutput()
calculateCost()
writeExecutionReport()
```

Bad: a `runEverything()` that starts the process, parses stdout, calculates tokens, calculates cost, writes files, generates markdown, handles errors, and prints presentation data.

Also do not split every two lines into its own function. The goal is reasonable reuse, not maximum abstraction. A function should exist when it makes the code easier to understand, test, or reuse.

### 4.4 Files and shared code

Multiple files are encouraged. Use them when they make responsibilities clearer.

Good:

```text
src/
├── index.js
├── harness.js
├── parser.js
├── cost.js
└── report.js
```

Bad: one `everything.js` with 500 lines of unrelated logic.

Also bad: a file per tiny function, or deep folders like `utils/string/trim.js`, `utils/number/round.js`. Do not create that level of organization unless the assignment needs it.

**Shared code:** if two or more implementations (or `src/` and another part of the project) need the same functionality, put it in `common/` once. Do not copy the same helper into several implementations.

```text
common/
├── config.js
├── file-utils.js
└── cost.js

src/
├── harness-a.js
└── harness-b.js
```

```js
import { writeJson } from "../common/file-utils.js";
```

Name shared files after what they do: `common/file-utils.js`, `common/cost.js`. Never create `utils.js`, `helpers.js`, `common.js`, or `misc.js` that mix unrelated functions. If there is only one implementation and nothing is shared, do not create `common/` at all.

### 4.5 Comments

Comments explain intent, not what the code obviously does.

Bad:

```js
// Increment i by 1
i++;
```

Bad:

```js
// Get the result from the harness
const result = await runHarness();
```

Good (explains a decision the code cannot show):

```js
// Keep the raw response because the parsed result
// is used for the comparison, while the original
// response is useful when reviewing unexpected output.
const raw = await runHarness();
```

Rules:

* Simple function: at most a one-line comment, and only when it helps. Example: `// Writes the execution result to the output folder.`
* Genuinely complex logic: 3 to 4 lines or more explaining the reasoning.
* Never use comments to make up for confusing code. If a five-line function needs a paragraph to explain it, simplify the function first.

### 4.6 Error handling

Handle errors where they can be acted upon. Do not wrap every function in its own `try/catch`. Handle realistic failures, not every theoretical one. Do not write 100 lines of validation for input the assignment controls.

Good:

```js
try {
  await run();
} catch (error) {
  await writeError(error);
  process.exit(1);
}
```

Avoid, because it silently hides a failure:

```js
try {
  ...
} catch {
  return null;
}
```

For an assignment, an explicit failure is better than pretending the run succeeded.

### 4.7 Dependencies

Use the smallest reasonable set. Before adding a package, ask: "Can this be done clearly with the standard library?" If yes, use the standard library. Add a dependency only when it materially simplifies the work or the assignment requires it. Do not add libraries because they are popular. Remove any dependency that ends up unused.

### 4.8 Other languages

The examples in this skill use JavaScript and Node.js. If the assignment requires another language (Python, Go, Java, and so on), keep the same ideas: an implementation folder, a shared-code folder only when needed, one entry file, one run command (for example `python -m src.index` or a `Makefile` target), and the same `output/` layout. Use the language the assignment requires. If it does not say, use the language the user's project already uses.

---

## 5. Repository structure

### 5.1 The canonical structure

Use this as the starting point and adapt it to the actual assignment. Do not blindly create every folder. The structure must reflect the problem.

```text
assignment/
├── src/                        implementation code only
│   ├── index.js                entry point that runs everything
│   └── ...
│
├── common/                     code shared by more than one implementation
│   └── ...
│
├── input/                      only if the assignment provides or needs input files
│   └── ...
│
├── output/                     everything produced by running the code
│   ├── <implementation-a>/
│   │   ├── raw/
│   │   ├── result/
│   │   ├── cost/
│   │   ├── errors/
│   │   └── README.md
│   │
│   ├── <implementation-b>/     same shape as implementation-a
│   │   └── ...
│   │
│   └── comparison/
│       ├── result.json
│       └── README.md
│
├── presentation/
│   ├── src/                    how the presentation is built
│   │   ├── build.js
│   │   └── slides.js
│   └── output/                 the presentation to open
│       └── assignment.pptx
│
├── ai/                         only if it adds evidence, see section 9
├── CLAUDE.md                   only if a coding agent is used, see section 9
├── .claude/                    only if there is a real reusable workflow
├── .gitignore
├── package.json
└── README.md
```

Variations:

* **One implementation only:** drop the second implementation folder and drop `comparison/`. The layout becomes `output/raw/`, `output/result/`, `output/cost/`, `output/errors/`, and `output/README.md`.
* **No presentation required:** drop `presentation/`.
* **Name the pptx after the assignment** if there is an obvious name. `assignment.pptx` is the fallback.

### 5.2 Rules for the structure

* **Source and output are never mixed.** `src/` contains code. `output/` contains what running that code produced. This is how the reviewer tells implementation from evidence at a glance.

  Do not do this:

  ```text
  src/
  ├── index.js
  ├── result.json
  ├── execution.log
  ├── tokens.json
  └── final-report.md
  ```

  Do this:

  ```text
  src/
  └── index.js

  output/
  └── ...
  ```

* **Only create folders that will hold real evidence.** The subfolders `raw/`, `parsed/`, `result/`, `cost/`, `tokens/`, `errors/`, `logs/`, `metrics/`, and `screenshots/` are options. Create one only when the run actually fills it. Do not create empty folders because the structure "looks professional".
* **Keep the structure symmetrical.** If implementation A has `result/`, `cost/`, and `errors/`, implementation B has the same. The reviewer can then compare `harness-a/result` against `harness-b/result` and `harness-a/cost` against `harness-b/cost` without searching.
* **Keep different implementations in different output folders.** Do not put two executions into one `output/results.json` when the assignment compares them. A reviewer should understand the experiment by looking at the directory tree.
* **`input/`** holds the input the assignment provides or that you prepared for the one execution. The execution README says which file was used.
* **`.gitignore`** must ignore `node_modules/` and `.env`. It must NOT ignore `output/` or `presentation/output/`. Those are the evidence and the deliverable.

---

## 6. Execution and output

### 6.1 One complete, real example

The repository contains exactly one complete execution example that demonstrates everything the assignment asks for. One good execution is more useful than four shallow ones.

Do not create `examples/example-1/`, `example-2/`, and so on unless the assignment explicitly asks for multiple cases.

The output in the repository must come from the actual implementation. Do not hand-write output to show the expected format. The repository must be internally consistent: if the README says a command generates `output/harness-a/result/output.json`, that file must exist and must have been produced by that command.

### 6.2 Reproducible commands

A reviewer should be able to clone the repository and understand the execution path quickly. Prefer one command:

```bash
npm run assignment
```

Add a second command only if it is genuinely necessary, normally for the presentation:

```bash
npm run presentation
```

Do not create a chain of stage scripts such as `prepare`, `preprocess`, `execute`, `transform`, `analyze`, `generate`, `finalize` unless the assignment genuinely has those stages.

Minimal `package.json` scripts:

```json
{
  "type": "module",
  "scripts": {
    "assignment": "node src/index.js",
    "presentation": "node presentation/src/build.js"
  }
}
```

`"type": "module"` is needed when the code uses `import`.

### 6.3 What the entry point looks like

The entry point reads like the story of the run. Keep it short.

```js
// Runs each harness on the same input and writes the evidence under output/.
import { runHarnessA } from "./harness-a.js";
import { runHarnessB } from "./harness-b.js";
import { compareResults } from "./compare.js";

try {
  await runHarnessA();
  await runHarnessB();
  await compareResults();
} catch (error) {
  console.error(error);
  process.exit(1);
}
```

### 6.4 Keep evidence traceable and separate from interpretation

Generated files must make it clear how they were produced. This matters most for LLM outputs, token use, cost comparison, multiple harnesses, evaluation, benchmarking, and error analysis. Do not hide everything inside one generated JSON file.

```text
output/
└── harness-a/
    ├── raw/
    │   └── response.json        exactly what the tool returned
    ├── result/
    │   └── output.json          the parsed result
    ├── cost/
    │   └── usage.json           tokens and cost
    ├── errors/
    │   └── execution.log        errors and relevant log lines
    └── README.md
```

Rules:

* **Raw evidence stays untouched.** Never edit, prettify-and-overwrite, or trim files in `raw/`.
* **Derived metrics live separately** (`result/`, `cost/`, `metrics/`).
* **Interpretation lives only in READMEs.** Conclusions such as "A was cheaper" go in `comparison/README.md`, not inside the raw or metric files. This makes the result easy to audit.
* Keep the raw response when it is useful for reviewing unexpected output. The parsed result is what the comparison uses.

### 6.5 Explicit paths, no accidental overwrites

The directory itself must say which execution produced the file.

Avoid, because two implementations would overwrite each other:

```js
writeFile("output/result.json", result);
```

Prefer:

```js
writeFile("output/harness-a/result/output.json", result);
writeFile("output/harness-b/result/output.json", result);
```

Running the command twice must write to the same paths (overwrite), not pile up new timestamped folders. Do not put timestamps in folder names. If the time of the run matters, write it inside the execution README.

### 6.6 Comparing two or more implementations

When the assignment compares harnesses, tools, models, or approaches:

* Keep the output structure symmetrical (section 5.2).
* Generate `output/comparison/result.json` with code that reads the actual `result/` and `cost/` files of each implementation. Never type comparison numbers by hand.
* Put the meaning of the numbers in `output/comparison/README.md` (section 7.3).

### 6.7 Cost and tokens

* Use token counts reported by the API or tool response. If a number had to be estimated, label it as an estimate and write how it was estimated.
* Keep pricing rates in one place (for example `common/cost.js`) with a short comment stating where the rates came from and the date. Do not invent prices. If you do not know the rates, take them from the assignment or the provider's pricing page, or ask the user.
* Save the numbers under `cost/` per implementation so the reviewer can compare them.

### 6.8 Secrets

* Read API keys from environment variables. Never hard-code a key.
* Provide `.env.example` with variable names and no real values. Add `.env` to `.gitignore`.
* Never write a key into `raw/`, `errors/`, or logs. Redact it if a tool prints it.
* Mention the required variables in the root README "Run" section.

### 6.9 When you cannot run it, or the run fails

* **Never create fake output.** If you cannot run the code (missing API key, no network, no permission), say so plainly. Leave `output/` without invented files, write down the exact command the user must run, and note in the final reply that the run was not verified.
* **A failed run is evidence.** Keep the error under `errors/` and describe it honestly in the execution README. Do not hide it, do not swallow the exception, and do not re-run just to get a cleaner-looking result unless the failure was a bug in your code.
* **Never claim something passed or worked unless you ran it and saw it.**
* Expensive runs (paid API calls): do not re-run only to double-check. Verify by comparing the file tree with what the READMEs say.

---

## 7. README files

Write every README as if handing the repository to another developer. Document setup, execution, structure, important assumptions, and the result. Then stop.

Avoid: marketing language ("robust and scalable solution"), long architecture explanations, repeating the assignment text, generic AI-sounding conclusions, and a 1,500-line README for a 200-line assignment.

### 7.1 Root README template

````md
# <Assignment name>

## What this does

Short explanation of the implementation, 2 to 4 sentences.

## Structure

- `src/` - implementation
- `common/` - code shared by the implementations
- `output/` - generated by running the code (one folder per implementation)
- `presentation/src/` - how the presentation is built
- `presentation/output/` - the presentation to open

## Run

```bash
npm install
npm run assignment
```

Environment variables needed: `EXAMPLE_API_KEY` (see `.env.example`).

## Output

Where the generated output is and what each folder contains, one line each.

## Presentation

Where the final PPT is and the command that regenerates it.

## Notes

Only important assumptions or limitations.
````

### 7.2 Execution README (one per implementation under `output/`)

Short. It answers five questions:

````md
# <implementation name>

- **What was executed:** command, tool or model name and version
- **Input:** path of the input file or the prompt used
- **Result:** one to three lines, with a pointer to `result/`
- **Errors:** none, or what happened, with a pointer to `errors/`
- **Notice:** what the reviewer should look at first
````

Add a **Cost** line pointing to `cost/` when cost matters. Do not turn this file into an essay. Write it after the run, using what the output actually shows.

### 7.3 Comparison README (`output/comparison/README.md`)

````md
# Comparison

- **What was compared:** A vs B, on which input
- **Numbers:** small table taken from `result.json`
- **What the numbers mean:** the interpretation, clearly separated from the numbers
- **Caveats:** for example a single run, or non-deterministic model output
````

---

## 8. Presentation

If the assignment requires a presentation, treat it as another small project.

```text
presentation/
├── src/
│   ├── build.js
│   ├── slides.js
│   └── ...
│
└── output/
    └── assignment.pptx
```

* `presentation/src/` is how the presentation is built.
* `presentation/output/` is the presentation that should be opened.
* Never put the PPT beside the source files.
* The PPT must be regenerable with one command (`npm run presentation`).

**Keep it minimal.** Do not build a presentation framework. If five slides are required, write five slides. Prefer:

```text
createTitleSlide()
createResultsSlide()
createComparisonSlide()
createConclusionSlide()
```

over an elaborate slide abstraction system. Add a small helper (`addTable()`, `addMetric()`, `addSectionTitle()`) only when the repetition is real.

**Use real numbers.** The slides must demonstrate the actual implementation. Read numbers from the files under `output/` (preferably in the build script). Do not type results from memory and do not invent claims. The presentation must agree with the code and the READMEs.

**Follow the requested structure.** Use the slide count and sections the assignment asks for. If it gives none, a short deck is enough: the problem, the approach, the results, the comparison (if any), and the conclusion. Keep text short enough to fit on the slide.

If a presentation or pptx skill is available in your environment, use it for the file-format mechanics. This skill decides where the files go and what they contain.

---

## 9. Agentic AI development documentation

Reviewers may also evaluate how effectively the solution used agentic AI during development. When the assignment is built with Claude Code or another coding agent, or the assignment mentions agentic AI, keep the repository structured so the AI workflow is understandable and reproducible.

The quality signal is **how well the AI workflow is organized and controlled**, not how many AI-related files exist. The repository should communicate "AI was used as an engineering tool with deliberate controls", not "many AI configuration files were added because they look impressive".

### 9.1 Possible files

```text
CLAUDE.md                       (or AGENTS.md, follow the convention of the agent in use)

.claude/
├── skills/
│   ├── <task-specific-skill>/
│   │   └── SKILL.md
│   └── <another-skill>/
│       └── SKILL.md
└── agents/
    └── ...

ai/
├── decisions.md
├── prompts/
├── reviews/
└── runs/
```

Create only what genuinely helps. A small assignment might need only:

```text
CLAUDE.md
.claude/
└── skills/
    └── assignment-review/
        └── SKILL.md
```

That can be more professional than a large artificial agent architecture.

### 9.2 CLAUDE.md / AGENTS.md: repository-specific only

Explain what is actually important for working on this repository:

* What the project does
* The important directory structure
* How to run the assignment
* Important implementation constraints
* Where generated output belongs
* How the presentation is generated
* Coding conventions
* Things the agent must not change
* Validation commands
* Important assumptions

Do not fill it with generic advice such as "Write clean code", "Follow best practices", "Use meaningful names", "Be professional". Those add almost nothing.

Prefer repository-specific instructions:

````md
# CLAUDE.md

## Project
One or two sentences: what the assignment asks and what this repo does.

## Layout
- src/ is code only. Do not write execution artifacts into src/.
- output/ is generated by running the code. Never edit it by hand.
- presentation/src/ builds the PPT. The generated PPT belongs in presentation/output/.

## Commands
- npm run assignment  runs everything and writes output/
- npm run presentation  builds presentation/output/assignment.pptx

## Rules
- Keep exactly one runnable example.
- Keep generated output under output/, one folder per implementation.
- Use plain functions. No new abstractions, config files, or dependencies unless the assignment needs them.

## Do not change
- The folder layout under output/
- The requirements list in README.md

## Validate before finishing
- Run npm run assignment and confirm every file named in the READMEs exists.
````

### 9.3 Skills: only for a real reusable workflow

Create a task-specific skill when a workflow is complex enough to deserve its own instructions. For example:

```text
.claude/skills/
├── challenge-runner/        prepare input -> run implementation -> capture output
│   └── SKILL.md               -> capture errors -> save execution metadata
├── output-analysis/
│   └── SKILL.md
└── presentation-builder/
    └── SKILL.md
```

Do not create ten skills for ten simple functions. A skill that only wraps one trivial command is slop.

### 9.4 Agents: separate responsibilities when several are used

If multiple agents are used, give each a clear, different responsibility:

```text
agents/
├── implementation.md
├── reviewer.md
└── presentation.md
```

* A **reviewer** agent checks requirement coverage, simplicity, missing edge cases, unnecessary abstractions, and repository organization.
* A **presentation** agent reads the actual execution results, builds slides from them, and keeps claims consistent with the implementation.

Agents must not duplicate each other's instructions.

### 9.5 Record the AI workflow when it adds evidence

Use `ai/decisions.md` to capture engineering judgment, not raw transcripts:

````md
# Decisions

## <short title>
- **Decision:** what was chosen
- **Why:** one or two lines
- **Not done:** the alternative that was rejected, or what was left out of scope on purpose
````

Good topics: why this implementation was chosen, why a dependency was not added, why this output structure was used, what was intentionally kept out of scope. Do not dump the whole conversation history into the repository. Add `prompts/`, `reviews/`, or `runs/` only if they contain useful evidence.

### 9.6 The intended workflow

```text
requirements
    ↓
agent instructions
    ↓
implementation
    ↓
agent review
    ↓
execution
    ↓
output validation
    ↓
presentation
```

The repository should make this understandable without the reviewer guessing how the AI was used.

### 9.7 Slop check for AI configuration files

Review these files with the same standard as source code. Remove:

* Generic instructions
* Repeated instructions
* Huge system-prompt-style documents
* Instructions unrelated to the repository
* Artificially complex agent hierarchies (for example 12 agents, 25 skills, multiple prompt chains, large agent frameworks)
* Skills that only wrap one trivial command
* Duplicate rules across `CLAUDE.md`, `AGENTS.md`, and skills
* Claims about tools or capabilities that are not actually used

Keep: repository-specific context, clear agent responsibilities, reusable workflows, validation instructions, important constraints, and decisions that help future agents work correctly.

---

## 10. Slop catalog (what to avoid)

Reviewers routinely remove these from generated code. This list adds to section 3.3 (features not to add) and section 4 (code rules). Check for them before finishing.

* **Over-abstraction.** `BaseExecutionStrategy`, `ExecutionStrategyFactory`, `ExecutionContextBuilder`, `ExecutionResultTransformer`, when a few functions would solve the problem.
* **Generic utility dumping.** `utils.js`, `helpers.js`, `common.js`, `misc.js` that hold unrelated functions.
* **Excessive defensive programming.** Long validation of input the assignment controls. Handle realistic failures only.
* **Obvious comments.** Explaining what each line does.
* **Excessive documentation.** Documentation that is longer than the thing it documents.
* **Fake configurability.** Configuration for things that never change, for example a `config/` folder with `environment.js`, `execution.js`, `output.js`, `parser.js`, `constants.js` when the assignment needs one fixed execution.
* **Unnecessary classes.** Prefer functions.
* **Excessive TypeScript types.** Types should improve understanding. Do not build elaborate generic types for simple data.
* **Excessive logging.** Log what helps someone understand the run or a failure. Do not print every internal step.
* **Fake enterprise architecture.** An assignment is not a production platform. Do not rebuild one around a small requirement.
* **Verbose names.** Long invented names instead of the assignment's own vocabulary.
* **Leftovers.** Unused files, unused dependencies, unused functions, duplicate logic.
* **Code that exists only to make the repository look sophisticated.**

---

## 11. Final review checklist

Before calling the assignment complete, check every box. Fix anything that fails.

### Requirements

* [ ] Every item on the requirements checklist is implemented.
* [ ] Nothing unnecessary was added.
* [ ] Assumptions for ambiguous points are written in the root README "Notes".
* [ ] There is exactly one complete execution example.
* [ ] The execution actually works (or the user was told it was not verified, section 6.9).

### Code

* [ ] `src/` contains the implementation.
* [ ] Functions have clear responsibilities.
* [ ] Files have clear responsibilities.
* [ ] No unnecessary classes or abstractions exist.
* [ ] Names are simple, descriptive, and use the assignment's vocabulary.
* [ ] Comments explain intent rather than obvious code.
* [ ] Complex functions have enough explanation.
* [ ] No duplicated shared logic exists, and shared code lives in `common/`.
* [ ] Errors are handled once at the top, not hidden.
* [ ] No secrets are committed, `.env.example` exists, `.gitignore` is correct.

### Output

* [ ] Source and output are separate.
* [ ] Different implementations have separate output folders with a symmetrical structure.
* [ ] Intermediate artifacts are separated where useful, and raw files are untouched.
* [ ] Cost, token, and error information is preserved where relevant.
* [ ] Each important execution has a short README.
* [ ] Generated output matches the actual execution, and every path named in a README exists.
* [ ] The comparison (if any) was generated from actual results.

### Presentation

* [ ] Presentation source is under `presentation/src/`.
* [ ] The final PPT is under `presentation/output/`.
* [ ] The PPT can be generated from the presentation source with one command.
* [ ] The presentation shows real numbers from the actual output.

### Agentic AI documentation

* [ ] `CLAUDE.md` / `AGENTS.md` contains repository-specific instructions only.
* [ ] Skills and agents exist only for real workflows, with no duplicated rules.
* [ ] `ai/decisions.md` exists only if it records real decisions.

### Slop check

* [ ] Walked through the whole of section 10 and section 9.7 and removed what applies.
* [ ] No multiple examples that were not requested.
* [ ] Root README is short and practical.

---

## 12. Final reply to the user

Keep the reply short and factual. Include:

1. What was built, in one or two sentences.
2. The command to run it.
3. Where the output is, and where the presentation is.
4. Assumptions you made.
5. What was **not** verified, if anything (for example "I could not run it because no API key was available").

Do not claim more than you actually did. Do not paste the whole file tree unless asked.

---

## Reminder

**Make the reviewer understand the solution before they have to understand the implementation.** If a simpler implementation satisfies the assignment, choose the simpler implementation.
