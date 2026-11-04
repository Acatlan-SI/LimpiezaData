"""Tests para la configuración."""

from pathlib import Path
from src.config import (
    PROJECT_ROOT, DATA_DIR, RAW_DIR, PROCESSED_DIR,
    RAW_CSV, PROCESSED_CSV
)


def test_project_root_existe():
    """El directorio raíz debe existir."""
    assert PROJECT_ROOT.exists()
    assert PROJECT_ROOT.is_dir()


def test_estructura_de_directorios():
    """Las rutas deben seguir la estructura esperada."""
    assert DATA_DIR == PROJECT_ROOT / "data"
    assert RAW_DIR == DATA_DIR / "raw"
    assert PROCESSED_DIR == DATA_DIR / "processed"


def test_rutas_de_archivos():
    """Los archivos deben estar en los directorios correctos."""
    assert RAW_CSV.parent == RAW_DIR
    assert PROCESSED_CSV.parent == PROCESSED_DIR
    assert RAW_CSV.suffix == ".csv"
    assert PROCESSED_CSV.suffix == ".csv"