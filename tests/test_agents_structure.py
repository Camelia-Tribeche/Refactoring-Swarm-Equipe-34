import pytest
import importlib

AGENTS = [
    "src.agents.auditor_agent",
    "src.agents.fixer_agent",
    "src.agents.judge_agent",
]

def test_agents_modules_exist():
    for module_name in AGENTS:
        pytest.importorskip(module_name)

def test_agents_have_classes():
    auditor = importlib.import_module("src.agents.auditor_agent")
    fixer = importlib.import_module("src.agents.fixer_agent")
    judge = importlib.import_module("src.agents.judge_agent")

    assert hasattr(auditor, "AuditorAgent")
    assert hasattr(fixer, "FixerAgent")
    assert hasattr(judge, "JudgeAgent")
