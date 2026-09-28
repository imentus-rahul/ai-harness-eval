# Agent instructions for this repo

- Implementation lives in `src/eval/`. Do not write run artifacts into `src/`.
- Committed example output belongs under `output/` after a real or `--dry-run` execution.
- Keep `DESIGN.md` to one page.
- Presentation source: `presentation/src/`. Generated pptx: `presentation/output/`.
- Do not commit API keys. Read `OPENROUTER_API_KEY` from the environment only.
- When changing the experiment, change **one** harness variable (guidance), not the model.
- Candidate guidance lives under `harnesses/good-candidate/` and `harnesses/bad-candidate/`; dry-run mocks under `mocks/`.
- Example output: `output/good-harness-example/` and `output/bad-harness-example/` (not a single `output/phase-1` tree).
