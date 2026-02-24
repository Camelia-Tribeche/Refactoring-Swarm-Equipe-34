import importlib


def test_tools_modules_import():
    # Ces imports doivent marcher si les fichiers existent
    importlib.import_module("src.tools.file_manager")
    importlib.import_module("src.tools.static_analyzer")
    importlib.import_module("src.tools.test_runner")
