import yaml

from eval.promote import load_registry, promote_capability_tasks, tasks_for_suite


def test_promote_only_when_all_pass(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    (project / "tasks").mkdir(parents=True)
    reg = {
        "tasks": {
            "auth-vs-log": {"suite": "capability"},
            "keep-suite": {"suite": "regression"},
        }
    }
    (project / "tasks" / "registry.yaml").write_text(
        yaml.safe_dump(reg), encoding="utf-8"
    )

    monkeypatch.chdir(project)
    promoted = promote_capability_tasks(
        project,
        "run-1",
        {"auth-vs-log": [True, False]},
        min_reps=2,
        dry_run=False,
    )
    assert promoted == []
    reg2 = load_registry(project)
    assert reg2["tasks"]["auth-vs-log"]["suite"] == "capability"

    promoted = promote_capability_tasks(
        project,
        "run-1",
        {"auth-vs-log": [True, True]},
        min_reps=2,
        dry_run=False,
    )
    assert promoted == ["auth-vs-log"]
    reg3 = load_registry(project)
    assert reg3["tasks"]["auth-vs-log"]["suite"] == "regression"
    assert "auth-vs-log" in tasks_for_suite(reg3, "regression")
