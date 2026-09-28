import json
from pathlib import Path

from eval.graders import grade_auth_expected, grade_code


def test_auth_expected_pass(tmp_path: Path):
    expected = tmp_path / "expected.json"
    expected.write_text(
        json.dumps(
            {
                "required": [
                    {"function": "withdraw", "vulnerable": True},
                    {"function": "logTransfer", "vulnerable": False},
                ]
            }
        ),
        encoding="utf-8",
    )
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "findings.json").write_text(
        json.dumps(
            {
                "findings": [
                    {"function": "withdraw", "vulnerable": True},
                    {"function": "logTransfer", "vulnerable": False},
                ]
            }
        ),
        encoding="utf-8",
    )
    ok, _ = grade_auth_expected(workspace, expected)
    assert ok


def test_auth_expected_fail_logging_flagged(tmp_path: Path):
    expected = tmp_path / "expected.json"
    expected.write_text(
        json.dumps(
            {
                "required": [
                    {"function": "withdraw", "vulnerable": True},
                    {"function": "logTransfer", "vulnerable": False},
                ]
            }
        ),
        encoding="utf-8",
    )
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "findings.json").write_text(
        json.dumps(
            {
                "findings": [
                    {"function": "withdraw", "vulnerable": True},
                    {"function": "logTransfer", "vulnerable": True},
                ]
            }
        ),
        encoding="utf-8",
    )
    ok, reason = grade_auth_expected(workspace, expected)
    assert not ok
    assert "logTransfer" in reason


def test_classification_format(tmp_path: Path):
    expected = tmp_path / "expected.json"
    expected.write_text(
        json.dumps({"required": [{"function": "logTransfer", "vulnerable": False}]}),
        encoding="utf-8",
    )
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "findings.json").write_text(
        json.dumps(
            [
                {
                    "function": "logTransfer",
                    "classification": "NOT A FINDING",
                }
            ]
        ),
        encoding="utf-8",
    )
    ok, _ = grade_auth_expected(workspace, expected)
    assert ok
