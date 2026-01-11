import importlib
import pytest


def test_agents_have_classes():
    # Auditor
    auditor = importlib.import_module("src.agents.auditor_agent")
    assert hasattr(auditor, "AuditorAgent"), "AuditorAgent manque dans auditor_agent.py"

    # Fixer (peut être vide au début)
    fixer = importlib.import_module("src.agents.fixer_agent")
    if not hasattr(fixer, "FixerAgent"):
        pytest.skip("FixerAgent pas encore implémenté (fixer_agent.py est vide).")

    # Judge (si présent)
    judge = importlib.import_module("src.agents.judge_agent")
    if not hasattr(judge, "JudgeAgent"):
        pytest.skip("JudgeAgent pas encore implémenté.")
