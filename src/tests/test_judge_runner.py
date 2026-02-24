from pathlib import Path
import importlib
import pytest


class DummyModel:
    def generate_content(self, prompt: str):
        class Resp:
            text = "DUMMY"
        return Resp()


def test_judge_validate_without_real_llm(tmp_path, monkeypatch):
    judge_mod = importlib.import_module("src.agents.judge_agent")

    # créer un fichier python valide
    ok_file = tmp_path / "ok.py"
    ok_file.write_text("x = 1\n", encoding="utf-8")

    # éviter vraie clé API
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy")

    # mock genai
    monkeypatch.setattr(
        judge_mod.genai,
        "configure",
        lambda api_key=None: None
    )

    monkeypatch.setattr(
        judge_mod.genai,
        "GenerativeModel",
        lambda *args, **kwargs: DummyModel()
    )

    # mock pytest runner
    monkeypatch.setattr(
        judge_mod,
        "run_pytest_on_directory",
        lambda directory: {
            "passed_count": 1,
            "failed_count": 0,
            "total_count": 1,
            "error_logs": []
        }
    )

    # mock logs
    monkeypatch.setattr(
        judge_mod,
        "log_experiment",
        lambda **kwargs: None
    )

    judge = judge_mod.JudgeAgent()

    result = judge.validate(
        files=[str(ok_file)],
        target_directory=tmp_path
    )

    assert result["passed"] is True
    assert result["tests_passed"] == 1
    assert result["tests_total"] == 1


