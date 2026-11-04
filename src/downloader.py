"""Descarga el CSV público de Google Sheets."""

import sys
import argparse
from datetime import datetime

import requests

from src.config import RAW_CSV, SHEET_CSV_URL


def download(url: str = SHEET_CSV_URL, dest=RAW_CSV) -> None:
    """Descarga el CSV y lo guarda en data/raw/."""
    print(f"[{datetime.now():%H:%M:%S}] Descargando desde: {url}")
    
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(response.content)
    print(f"✓ Guardado en: {dest} ({dest.stat().st_size} bytes)")


def clean_session() -> None:
    """Elimina los datos de la sesión actual."""
    from src.config import RAW_DIR, PROCESSED_DIR
    
    for d in (RAW_DIR, PROCESSED_DIR):
        for f in d.glob("*.csv"):
            f.unlink()
            print(f"✗ Eliminado: {f}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Descarga CSV desde Google Sheets"
    )
    parser.add_argument(
        "url",
        nargs="?",
        default=SHEET_CSV_URL,
        help="URL del CSV público (opcional, usa DEFAULT_SHEET_URL si no se pasa)"
    )
    args = parser.parse_args()
    
    try:
        download(url=args.url)
        return 0
    except requests.HTTPError as e:
        print(f"✗ Error HTTP: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())