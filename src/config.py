"""Configuración centralizada del proyecto."""

from pathlib import Path
import os

DEFAULT_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vQmx6xTqJDv0c-e9SAWH7Jku6ZCiIfIbSrKHHXD1oxrslbA0j3ZqpAP6pP8SXd2CmLB5WDHanazOy12/pub?gid=1639119631&single=true&output=csv"
)

SHEET_CSV_URL = DEFAULT_SHEET_URL

# ============================================================
# Rutas
# ============================================================
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

RAW_CSV = RAW_DIR / "datos_raw.csv"
PROCESSED_CSV = PROCESSED_DIR / "datos_limpios.csv"

# Crear directorios
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)