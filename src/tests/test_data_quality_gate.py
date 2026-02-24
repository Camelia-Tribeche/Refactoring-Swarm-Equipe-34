import json
import importlib
import pytest

def test_log_experiment_requires_required_fields():
    logger = importlib.import_module("src.utils.logger")

    # Mauvais: manque input_prompt/output_response
    with pytest.raises(Exception):
        logger.log_experiment(
            agent_name="X",
            model_used="N/A",
            action=logger.ActionType.ANALYSIS,
            details={"hello": "world"},
            status="SUCCESS",
        )

def test_log_experiment_accepts_valid_payload(tmp_path, monkeypatch):
    logger = importlib.import_module("src.utils.logger")

    # si ton logger écrit dans un fichier, on peut mocker la destination
    # sinon, ce test vérifie surtout que ça ne plante pas avec un payload valide
    logger.log_experiment(
        agent_name="X",
        model_used="N/A",
        action=logger.ActionType.ANALYSIS,
        details={"input_prompt": "a", "output_response": "b"},
        status="SUCCESS",
    )
