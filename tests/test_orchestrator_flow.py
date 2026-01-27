from pathlib import Path
import importlib
import pytest


class DummyAuditor:
    def analyze(self, files):
        return {"issues": ["dummy_issue"]}

class DummyFixer:
    def fix(self, plan, error_logs):
        return {"bugs_fixed": 1, "files_modified": ["dummy.py"]}

class DummyJudge:
    pass


@pytest.fixture
def orch_module():
    return importlib.import_module("src.orchestrator.swarm_orchestrator")


def _make_dummy_py_file(tmp_path: Path, name="a.py"):
    f = tmp_path / name
    f.write_text("x = 1\n", encoding="utf-8")
    return f


def _patch_no_llm(monkeypatch, orch_module):
    # enlever les pauses
    monkeypatch.setattr(orch_module.time, "sleep", lambda *_: None)
    # enlever les logs
    monkeypatch.setattr(orch_module, "log_experiment", lambda **kwargs: None)
    # remplacer les agents LLM par des dummy
    monkeypatch.setattr(orch_module, "AuditorAgent", DummyAuditor)
    monkeypatch.setattr(orch_module, "FixerAgent", DummyFixer)
    monkeypatch.setattr(orch_module, "JudgeAgent", DummyJudge)


def test_discover_python_files_finds_py(tmp_path, monkeypatch, orch_module):
    _patch_no_llm(monkeypatch, orch_module)

    _make_dummy_py_file(tmp_path, "hello.py")

    swarm = orch_module.RefactoringSwarm(target_directory=tmp_path, max_iterations=1)
    swarm._discover_python_files()

    assert any(p.endswith("hello.py") for p in swarm.state.files_to_process)


def test_run_returns_error_when_no_py_files(tmp_path, monkeypatch, orch_module):
    _patch_no_llm(monkeypatch, orch_module)

    swarm = orch_module.RefactoringSwarm(target_directory=tmp_path, max_iterations=2)
    report = swarm.run()

    assert report["success"] is False
    assert "Aucun fichier Python" in report["error"]
    assert report["iterations_used"] == 0


def test_run_stops_early_when_tests_pass(tmp_path, monkeypatch, orch_module):
    _patch_no_llm(monkeypatch, orch_module)

    _make_dummy_py_file(tmp_path, "hello.py")

    # ne pas générer de vrais tests
    monkeypatch.setattr(
        orch_module.RefactoringSwarm,
        "_generate_test_file",
        lambda self, fp: str(tmp_path / "tests" / "test_dummy.py"),
    )

    # pytest => SUCCESS
    monkeypatch.setattr(
        orch_module,
        "run_pytest_on_directory",
        lambda directory: {"passed_count": 5, "failed_count": 0, "total_count": 5, "error_logs": []},
    )

    swarm = orch_module.RefactoringSwarm(target_directory=tmp_path, max_iterations=4)
    report = swarm.run()

    assert report["success"] is True
    assert report["iterations_used"] == 1


def test_run_respects_max_iterations(tmp_path, monkeypatch, orch_module):
    _patch_no_llm(monkeypatch, orch_module)

    _make_dummy_py_file(tmp_path, "hello.py")

    monkeypatch.setattr(
        orch_module.RefactoringSwarm,
        "_generate_test_file",
        lambda self, fp: str(tmp_path / "tests" / "test_dummy.py"),
    )

    # pytest échoue toujours
    monkeypatch.setattr(
        orch_module,
        "run_pytest_on_directory",
        lambda directory: {"passed_count": 0, "failed_count": 1, "total_count": 1, "error_logs": ["fail"]},
    )

    swarm = orch_module.RefactoringSwarm(target_directory=tmp_path, max_iterations=2)
    report = swarm.run()

    assert report["success"] is False
    assert report["iterations_used"] == 2
    assert report["max_iterations"] == 2

