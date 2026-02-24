from pathlib import Path
import importlib
import pytest


class DummyAuditor:
    def analyze(self, files):
        return {"issues": [{"file": f, "issues": ["dummy_issue"]} for f in files]}


class DummyFixer:
    def fix(self, plan, error_logs=None):
        return {"bugs_fixed": len(plan.get("issues", [])), "files_modified": [f["file"] for f in plan.get("issues", [])]}


class DummyJudge:
    def generate_tests(self, file_path, target_directory):
        # Simule la génération de tests
        test_file = target_directory / "tests" / f"test_{Path(file_path).name}"
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text("def test_dummy(): assert True\n")
        return str(test_file)

    def validate(self, files, target_directory):
        # Simule un test toujours réussi
        return {"passed": True, "tests_passed": 1, "tests_total": 1}


@pytest.fixture
def orch_module():
    return importlib.import_module("src.orchestrator.swarm_orchestrator")


def _make_dummy_py_file(tmp_path: Path, name="a.py"):
    f = tmp_path / name
    f.write_text("x = 1\n", encoding="utf-8")
    return f


def _patch_no_llm(monkeypatch, orch_module):
    # remplacer les agents par nos dummy
    monkeypatch.setattr(orch_module, "AuditorAgent", DummyAuditor)
    monkeypatch.setattr(orch_module, "FixerAgent", DummyFixer)
    monkeypatch.setattr(orch_module, "JudgeAgent", DummyJudge)
    # désactiver les logs
    monkeypatch.setattr(orch_module, "log_experiment", lambda **kwargs: None)


def test_discover_python_files(tmp_path, monkeypatch, orch_module):
    """Vérifie que _discover_files() trouve les fichiers Python"""
    _patch_no_llm(monkeypatch, orch_module)

    _make_dummy_py_file(tmp_path, "hello.py")
    swarm = orch_module.RefactoringSwarm(target_directory=tmp_path, max_iterations=1)
    files = swarm._discover_files()

    assert any(f.endswith("hello.py") for f in files)


def test_run_success_with_dummy_agents(tmp_path, monkeypatch, orch_module):
    """Vérifie que run() réussit avec les agents dummy"""
    _patch_no_llm(monkeypatch, orch_module)

    _make_dummy_py_file(tmp_path, "hello.py")
    swarm = orch_module.RefactoringSwarm(target_directory=tmp_path, max_iterations=2)
    report = swarm.run()

    assert report["success"] is True
    assert report["iterations_used"] == 1
    assert report["files_processed"] == 1
    assert report["bugs_fixed"] >= 1
    assert report["tests_passed"] == report["total_tests"]


def test_run_no_files(tmp_path, monkeypatch, orch_module):
    """Vérifie que run() échoue si aucun fichier Python n'est trouvé"""
    _patch_no_llm(monkeypatch, orch_module)

    swarm = orch_module.RefactoringSwarm(target_directory=tmp_path, max_iterations=2)
    report = swarm.run()

    assert report["success"] is False
    assert "Aucun fichier Python" in report["error"]
    assert report["iterations_used"] == 0


def test_run_multiple_iterations(tmp_path, monkeypatch, orch_module):
    """Vérifie que run() respecte max_iterations même si les tests échouent"""
    _patch_no_llm(monkeypatch, orch_module)

    _make_dummy_py_file(tmp_path, "hello.py")

    class FailingJudge(DummyJudge):
        def validate(self, files, target_directory):
            # simule un échec de test
            return {"passed": False, "tests_failed": 1, "tests_passed": 0, "tests_total": 1, "errors": ["fail"]}

    monkeypatch.setattr(orch_module, "JudgeAgent", FailingJudge)

    swarm = orch_module.RefactoringSwarm(target_directory=tmp_path, max_iterations=2)
    report = swarm.run()

    assert report["success"] is False
    assert report["iterations_used"] == 2
    assert report["tests_passed"] == 0
    assert report["total_tests"] == 1
