#!/usr/bin/env python3
"""
Bootstrap universal: instala uv, clona el repo, crea el venv
y descarga los datos. Funciona incluso sin Python preinstalado
(si se ejecuta desde el instalador de uv).
"""

import os
import platform
import subprocess
import sys
from pathlib import Path
from urllib.request import urlretrieve


REPO_URL = "https://github.com/Acatlan-SI/LimpiezaData"
SHEET_CSV_URL = os.environ.get(
    "SHEET_CSV_URL",
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vQmx6xTqJDv0c-e9SAWH7Jku6ZCiIfIbSrKHHXD1oxrslbA0j3ZqpAP6pP8SXd2CmLB5WDHanazOy12/pub?gid=1639119631&single=true&output=csv"
)


def run(cmd, **kwargs):
    print(f"$ {cmd}")
    subprocess.run(cmd, shell=True, check=True, **kwargs)


def install_uv():
    """Instala uv si no está disponible."""
    try:
        run("uv --version")
        print("✓ uv ya instalado")
        return
    except subprocess.CalledProcessError:
        pass

    system = platform.system()
    print(f"Instalando uv en {system}...")

    if system == "Windows":
        run('powershell -ExecutionPolicy ByPass -c '
            '"irm https://astral.sh/uv/install.ps1 | iex"')
    else:
        run("curl -LsSf https://astral.sh/uv/install.sh | sh")

    print("✓ uv instalado. Reinicia la terminal si es necesario.")


def setup_environment(project_dir: Path):
    """Sincroniza el entorno virtual con uv."""
    os.chdir(project_dir)
    run("uv sync")
    print("✓ Entorno virtual creado y sincronizado")


def download_data():
    """Descarga el CSV público a data/raw/."""
    run("uv run python -m src.downloader")
    print("✓ Datos descargados")


def main():
    print("=" * 60)
    print("  BOOTSTRAP - LimpiezaData Relaciones Acatlán")
    print("=" * 60)

    install_uv()

    project_dir = Path("mi-proyecto")
    if not project_dir.exists():
        run(f"git clone {REPO_URL}")

    setup_environment(project_dir)
    download_data()

    print("\n" + "=" * 60)
    print("  ¡Listo! Próximos pasos:")
    print("  - Notebook:  uv run jupyter notebook")
    print("  - Dashboard: uv run streamlit run src/dashboard/app.py")
    print("=" * 60)


if __name__ == "__main__":
    main()