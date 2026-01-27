import json
from pathlib import Path
import pytest

from src.utils.logger import log_experiment, ActionType


def test_logger_imports():
    # Si ce test passe, le module logger est OK
    assert log_experiment is not None
    assert ActionType is not None


def test_logger_writes_valid_json():
    # Appeler le logger avec les bons paramètres
    log_experiment(
        agent_name="DataOfficer_Test",
        model_used="TEST",
        action=ActionType.ANALYSIS,
        details={"input_prompt": "hello", "output_response": "world"},
        status="SUCCESS",
    )

    # Vérifier que le fichier de log existe
    log_path = Path("logs/experiment_data.json")
    assert log_path.exists(), "logs/experiment_data.json n'a pas été créé."

    # Vérifier que c'est un JSON valide et non vide
    data = json.loads(log_path.read_text(encoding="utf-8"))
    assert data, "Le fichier de log est vide."


def test_logger_requires_status():
    # Si on oublie status, Python doit lever TypeError
    with pytest.raises(TypeError):
        log_experiment(
            agent_name="DataOfficer_Test",
            model_used="TEST",
            action=ActionType.ANALYSIS,
            details={"input_prompt": "x", "output_response": "y"},
            # status manquant volontairement
        )


def test_logger_requires_prompt_fields():
    # Si details ne contient pas input_prompt/output_response,
    # votre logger doit refuser (le guide dit que c'est obligatoire)
    with pytest.raises(Exception):
        log_experiment(
            agent_name="DataOfficer_Test",
            model_used="TEST",
            action=ActionType.ANALYSIS,
            details={},  # volontairement vide
            status="FAILURE",
        )
