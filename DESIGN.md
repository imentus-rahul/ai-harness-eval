# Design (one page)

## Concepts

| Term | Meaning |
|------|---------|
| Task | Prompt + repo + held-out success criteria |
| Trial | One harness run on one task in a clean workspace |
| Transcript | Tools, tokens, latency, findings output |
| Outcome | Grader pass/fail on the workspace |
| Agent harness | Model + tools + guidance files |
| Evaluation harness | This tool: run trials, grade, compare, graduate tasks |
| Suite | Capability (learning) vs regression (must not break) |

## Five hard decisions

1. **One variable** — Same Haiku model and tool loop; baseline `AGENTS.md` vs `good-candidate` or `bad-candidate` `SKILL.md`.
2. **Code grader owns the gate** — Model rubric is evidence; graduation uses code pass^k only.
3. **UNSTABLE not rounded** — Split reps stay out of improved/regressed counts.
4. **Held-out JSON** — Expected labels live outside the workspace until grading.
5. **On-disk mocks** — `mocks/{baseline,good-candidate,bad-candidate}/` drive `--dry-run`; bad candidate uses a `keep-suite` overlay that fails pytest.

## Cut

Claude Code CLI, parallel trials, multi-judge consensus, web UI, inferential stats at n=2, Ollama arm.

## Result I did not fully trust

Model rubric sometimes PASSes vague prose while code FAILs on labels. We show `model_disagreement` and keep the code verdict for promotion.

## Two reference stories

- **Good** (`output/good-harness-example/`): capability improves, regression unchanged → promote → phase 2.
- **Bad** (`output/bad-harness-example/`): regression regresses on `keep-suite` → `phase_2_blocked_reason`, no phase 2.
