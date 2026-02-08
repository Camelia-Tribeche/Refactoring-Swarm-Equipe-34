import pytest
import importlib


def test_orchestrator_imports():
    importlib.import_module("src.orchestrator.swarm_orchestrator")


def test_orchestrator_has_main_class():
    orch = importlib.import_module("src.orchestrator.swarm_orchestrator")
    assert hasattr(orch, "RefactoringSwarm"), "La classe RefactoringSwarm doit exister"
