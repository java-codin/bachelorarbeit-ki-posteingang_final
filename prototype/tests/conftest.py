"""Pytest-Konfiguration für die Regressionstests des Prototyps."""

from pathlib import Path
import sys


PROTOTYPE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = PROTOTYPE_DIR.parent

for import_path in [PROJECT_ROOT, PROTOTYPE_DIR]:
    import_path_value = str(import_path)
    if import_path_value not in sys.path:
        sys.path.insert(0, import_path_value)
