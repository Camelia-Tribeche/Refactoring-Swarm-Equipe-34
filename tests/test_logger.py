import json
from pathlib import Path

def test_log_file_exists():
    p = Path("logs/experiment_data.json")
    assert p.exists()

def test_log_is_valid_json():
    p = Path("logs/experiment_data.json")
    data = json.loads(p.read_text(encoding="utf-8"))
    assert isinstance(data, list)
