# Engineering decisions

1. **One controlled variable** — Same OpenRouter model, endpoint, tool set, and agent loop; only baseline vs candidate guidance differs so a delta is attributable.
2. **Two candidate harnesses** — `good-candidate` (triage skill) and `bad-candidate` (over-remediation) share one baseline for teaching and dry-run evidence.
3. **Code grader gates graduation** — Model rubric can disagree; we document disagreement instead of overriding pytest/JSON checks.
4. **Phase 2 block on regression** — Any `REGRESSED` transition or candidate FAIL on a regression task in phase 1 skips phase 2; reason stored in `summary.json`.
5. **Dry-run mocks on disk** — `mocks/` plus `eval.config.yaml` (`scenario: good|bad|both`); no OpenRouter spend for committed output.
6. **Small dependency set** — stdlib HTTP, PyYAML, pytest, python-pptx for the deck only.
