"""Load eval.config.yaml for scenario and candidate selection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

SCENARIO_GOOD = "good"
SCENARIO_BAD = "bad"
SCENARIO_BOTH = "both"

CANDIDATE_GOOD = "good-candidate"
CANDIDATE_BAD = "bad-candidate"

SCENARIO_OUTPUT = {
    SCENARIO_GOOD: "good-harness-example",
    SCENARIO_BAD: "bad-harness-example",
}

SCENARIO_CANDIDATE = {
    SCENARIO_GOOD: CANDIDATE_GOOD,
    SCENARIO_BAD: CANDIDATE_BAD,
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_eval_config(project: Path | None = None) -> dict[str, Any]:
    root = project or project_root()
    path = root / "eval.config.yaml"
    if not path.is_file():
        return {"scenario": SCENARIO_BOTH, "candidate": CANDIDATE_GOOD}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {"scenario": SCENARIO_BOTH, "candidate": CANDIDATE_GOOD}
    return data


def resolve_scenarios(
    cli_scenario: str | None,
    dry_run: bool,
    config: dict[str, Any],
) -> list[str]:
    raw = (cli_scenario or config.get("scenario") or SCENARIO_BOTH).strip().lower()
    if raw == SCENARIO_BOTH:
        if dry_run:
            return [SCENARIO_GOOD, SCENARIO_BAD]
        return [SCENARIO_GOOD]
    if raw in (SCENARIO_GOOD, SCENARIO_BAD):
        return [raw]
    return [SCENARIO_GOOD]


def candidate_id_for_scenario(scenario: str, config: dict[str, Any]) -> str:
    if scenario in SCENARIO_CANDIDATE:
        return SCENARIO_CANDIDATE[scenario]
    cand = config.get("candidate") or CANDIDATE_GOOD
    if cand in (CANDIDATE_GOOD, CANDIDATE_BAD):
        return cand
    return CANDIDATE_GOOD
