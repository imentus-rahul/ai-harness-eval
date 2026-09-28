import json
import shutil
from pathlib import Path

from eval.agent import apply_mock_transcript
from eval.graders import grade_auth_expected, grade_keep_suite


def test_good_auth_mock_passes_heldout():
    project = Path(__file__).resolve().parents[1]
    workspace = project / "tests" / "_tmp_good_auth"
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    apply_mock_transcript(
        project,
        workspace,
        "candidate",
        "auth-vs-log",
        candidate_id="good-candidate",
    )
    expected = project / "tasks" / "auth-vs-log" / "heldout" / "expected.json"
    ok, _ = grade_auth_expected(workspace, expected)
    assert ok
    shutil.rmtree(workspace)


def test_bad_keep_suite_overlay_fails_pytest():
    project = Path(__file__).resolve().parents[1]
    task_dir = project / "tasks" / "keep-suite"
    workspace = project / "tests" / "_tmp_bad_keep"
    if workspace.exists():
        shutil.rmtree(workspace)
    shutil.copytree(task_dir / "repo", workspace)
    apply_mock_transcript(
        project,
        workspace,
        "candidate",
        "keep-suite",
        candidate_id="bad-candidate",
    )
    ok, _ = grade_keep_suite(workspace, task_dir)
    assert not ok
    shutil.rmtree(workspace)
