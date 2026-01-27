import json
import importlib
import builtins
from pathlib import Path


def _redirect_logger_to_tmp(monkeypatch, logger_module, tmp_log_path: Path):
    """
    Redirige l'écriture du logger vers un fichier temporaire
    pour ne pas toucher logs/experiment_data.json du projet.
    """
    candidates = [
        "LOG_FILE",
        "LOG_PATH",
        "LOG_FILE_PATH",
        "LOG_FILENAME",
        "LOGS_PATH",
        "EXPERIMENT_LOG_PATH",
    ]
    for name in candidates:
        if hasattr(logger_module, name):
            monkeypatch.setattr(logger_module, name, str(tmp_log_path))
            return "attr"

    real_open = builtins.open

    def fake_open(file, mode="r", *args, **kwargs):
        file_str = str(file)
        # Rediriger seulement quand on écrit le fichier experiment_data.json
        if ("experiment_data.json" in file_str) and ("w" in mode or "a" in mode):
            tmp_log_path.parent.mkdir(parents=True, exist_ok=True)
            return real_open(tmp_log_path, mode, *args, **kwargs)
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)
    return "open"


def test_logger_writes_valid_json_file(tmp_path, monkeypatch):
    logger = importlib.import_module("src.utils.logger")

    tmp_log = tmp_path / "experiment_data.json"
    _redirect_logger_to_tmp(monkeypatch, logger, tmp_log)

    logger.log_experiment(
        agent_name="QA",
        model_used="N/A",
        action=logger.ActionType.ANALYSIS,
        details={"input_prompt": "a", "output_response": "b"},
        status="SUCCESS",
    )

    assert tmp_log.exists(), "Le fichier log n'a pas été créé"
    content = tmp_log.read_text(encoding="utf-8").strip()
    assert content != "", "Le fichier log est vide"

    data = json.loads(content)
    assert isinstance(data, (list, dict)), "Le JSON log doit être une liste ou un objet"


def test_each_log_entry_has_required_fields(tmp_path, monkeypatch):
    logger = importlib.import_module("src.utils.logger")

    tmp_log = tmp_path / "experiment_data.json"
    _redirect_logger_to_tmp(monkeypatch, logger, tmp_log)

    logger.log_experiment(
        agent_name="Judge_Agent",
        model_used="gemini-2.5-flash",
        action=logger.ActionType.DEBUG,
        details={"input_prompt": "x", "output_response": "y"},
        status="SUCCESS",
    )

    data = json.loads(tmp_log.read_text(encoding="utf-8"))

    # Le logger peut écrire un dict (1 événement) ou une liste (plusieurs événements)
    entries = [data] if isinstance(data, dict) else data

    assert isinstance(entries, list)
    assert len(entries) >= 1, "Aucune entrée trouvée dans le log"

    last = entries[-1]
    assert isinstance(last, dict), "Chaque entrée de log doit être un dict"

    # Champs attendus (selon ton format actuel)
    required_top = ["timestamp", "action", "details", "status"]
    for k in required_top:
        assert k in last, f"Champ manquant dans l'entrée de log: {k}"
    assert ("model_used" in last) or ("model" in last), "Champ model manquant (model_used ou model)"
    model_value = last.get("model_used") or last.get("model")
    assert str(model_value).strip() != ""
    # Champ agent : accepter "agent_name" OU "agent"
    assert ("agent_name" in last) or ("agent" in last), "Champ agent manquant (agent_name ou agent)"
    agent_value = last.get("agent_name") or last.get("agent")
    assert str(agent_value).strip() != ""

    # details obligatoires Data Officer
    assert isinstance(last["details"], dict)
    assert "input_prompt" in last["details"], "details.input_prompt manquant"
    assert "output_response" in last["details"], "details.output_response manquant"
