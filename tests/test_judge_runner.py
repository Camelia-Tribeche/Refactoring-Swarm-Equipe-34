from pathlib import Path
import json
import importlib
import pytest


class DummyModel:
    def generate_content(self, prompt: str):
        # Le Judge attend un JSON dans response.text
        class Resp:
            text = json.dumps({
                "validation_result": "SUCCESS",
                "next_action": "STOP",
                "explanation": "All good"
            })
        return Resp()


def test_judge_syntax_check_passes(tmp_path, monkeypatch):
    judge_mod = importlib.import_module("src.agents.judge_agent")

    # Créer un fichier .py valide
    (tmp_path / "ok.py").write_text("x = 1\n", encoding="utf-8")

    # Créer un JudgeAgent SANS appeler __init__ (pour éviter GOOGLE_API_KEY)
    judge = judge_mod.JudgeAgent.__new__(judge_mod.JudgeAgent)

    result = judge_mod.JudgeAgent._run_syntax_check(judge, tmp_path)
    assert result["passed"] is True
    assert result["errors"] == []


def test_judge_validate_without_real_llm(tmp_path, monkeypatch):
    judge_mod = importlib.import_module("src.agents.judge_agent")

    # Créer un fichier .py valide
    (tmp_path / "ok.py").write_text("x = 1\n", encoding="utf-8")

    # Mock: pas besoin de vraie clé
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy")

    # Mock genai: configure + GenerativeModel
    monkeypatch.setattr(judge_mod.genai, "configure", lambda api_key: None)
    monkeypatch.setattr(judge_mod.genai, "GenerativeModel", lambda *_: DummyModel())

    # Mock prompt loader (évite FileNotFoundError si prompt absent)
    monkeypatch.setattr(judge_mod.JudgeAgent, "_load_tester_prompt", lambda self: "PROMPT")

    # Mock run_pytest_on_directory (évite lancer de vrais tests)
    monkeypatch.setattr(
        judge_mod,
        "run_pytest_on_directory",
        lambda directory: {"passed_count": 1, "failed_count": 0, "total_count": 1, "error_logs": []},
    )

    # Mock log_experiment (évite écrire logs)
    monkeypatch.setattr(judge_mod, "log_experiment", lambda **kwargs: None)

    judge = judge_mod.JudgeAgent()

    out = judge.validate(
        target_directory=tmp_path,
        audit_plan={"issues": []},
        iteration_count=1
    )

    assert out["status"] == "completed"
    assert out["validation_result"] == "SUCCESS"
    assert out["next_action"] == "STOP"
def test_judge_syntax_check_fails_on_bad_file(tmp_path, monkeypatch):
    import importlib
    judge_mod = importlib.import_module("src.agents.judge_agent")

    # fichier Python cassé
    (tmp_path / "bad.py").write_text("def x(:\n    pass\n", encoding="utf-8")

    judge = judge_mod.JudgeAgent.__new__(judge_mod.JudgeAgent)
    result = judge_mod.JudgeAgent._run_syntax_check(judge, tmp_path)

    assert result["passed"] is False
    assert len(result["errors"]) >= 1
