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


