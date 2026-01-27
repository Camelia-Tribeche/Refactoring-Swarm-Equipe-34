import importlib
from pathlib import Path
import pytest


def test_sandbox_folder_exists():
    """
    Vérifie que le dossier sandbox peut exister / être créé.
    """
    sandbox = Path("sandbox")
    sandbox.mkdir(exist_ok=True)
    assert sandbox.exists()
    assert sandbox.is_dir()


def test_write_file_safe_writes_inside_tmp(tmp_path):
    """
    Cas NORMAL : écrire dans un dossier autorisé doit fonctionner.
    """
    fm = importlib.import_module("src.tools.file_manager")

    target = tmp_path / "sandbox" / "ok.txt"
    result = fm.write_file_safe(str(target), "hello")

    assert result is True
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "hello"


@pytest.mark.xfail(reason="Sécurité sandbox non implémentée")
def test_write_file_safe_should_block_outside_sandbox(tmp_path):
    import importlib
    fm = importlib.import_module("src.tools.file_manager")

    outside = tmp_path.parent / "outside.txt"

    with pytest.raises(Exception):
        fm.write_file_safe(str(outside), "NO")

