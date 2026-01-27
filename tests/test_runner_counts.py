import importlib

def test_run_pytest_on_directory_returns_counts(monkeypatch, tmp_path):
    tr = importlib.import_module("src.tools.test_runner")

    # On mock subprocess pour ne pas lancer pytest réellement
    class DummyResult:
        returncode = 0
        stdout = "=== 3 passed in 0.01s ==="
        stderr = ""

    monkeypatch.setattr(tr.subprocess, "run", lambda *args, **kwargs: DummyResult())

    out = tr.run_pytest_on_directory(str(tmp_path))

    assert "passed_count" in out
    assert "failed_count" in out
    assert "total_count" in out
    assert out["failed_count"] == 0
