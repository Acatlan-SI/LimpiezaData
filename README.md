# 📊 Mi Proyecto

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![uv](https://img.shields.io/badge/managed%20with-uv-deeppink?logo=uv&logoColor=white)](https://docs.astral.sh/uv/)
[![pandas](https://img.shields.io/badge/pandas-2.2%2B-150458?logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Pipeline de datos**: descarga desde Google Sheets → limpieza en notebook → dashboard en la nube.

## 🏷️ Etiquetas

`#python` `#data-engineering` `#data-cleaning` `#pandas` `#uv` `#jupyter` `#streamlit` `#google-sheets` `#etl` `#data-pipeline`

## 🎯 Características

- ✅ **Cero instalaciones previas**: funciona en máquinas sin Python
- ✅ **Datos efímeros**: el CSV nunca toca el repositorio
- ✅ **Notebook interactivo**: limpieza paso a paso con visualización
- ✅ **Reproducible**: lockfile de `uv` garantiza mismas dependencias
- ✅ **Dashboard en la nube**: desplegable en Streamlit Cloud

## 📁 Estructura del proyecto

```
mi-proyecto/
├── pyproject.toml          # Dependencias del proyecto
├── uv.lock                 # Lockfile reproducible
├── bootstrap.py            # Instalador universal
├── README.md
├── .env.example            # Plantilla opcional de variables
├── .gitignore
│
├── src/
│   ├── __init__.py
│   ├── config.py           # Rutas y URL por defecto
│   └── downloader.py       # Descarga del CSV público
│
├── notebooks/
│   └── 01_limpieza_datos.ipynb
│
├── data/                   # ⚠️ EFÍMERO (gitignored)
│   ├── raw/                # CSV descargado de Google Sheets
│   └── processed/          # CSV limpio exportado del notebook
│
└── tests/
    ├── test_config.py
    └── test_downloader.py
```

## 🚀 Instalación

### Requisitos

**Ninguno.** `uv` descarga Python automáticamente si no está instalado.

### Instalación rápida

#### 🐧 Linux / 🍎 macOS

```bash
# 1. Instalar uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc   # o ~/.zshrc

# 2. Clonar el repositorio
git clone https://github.com/TU_USUARIO/mi-proyecto.git
cd mi-proyecto

# 3. Sincronizar dependencias (crea .venv automáticamente)
uv sync

# 4. Editar la URL de tu Google Sheet en src/config.py
#    Cambia DEFAULT_SHEET_URL por tu URL real
```

#### 🪟 Windows (PowerShell)

```powershell
# 1. Instalar uv
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# Reiniciar PowerShell

# 2. Clonar el repositorio
git clone https://github.com/Acatlan-SI/LimpiezaData.git
cd mi-proyecto

# 3. Sincronizar dependencias
uv sync

# 4. Editar la URL en src/config.py
```

### Instalación alternativa con bootstrap (sin git)

```bash
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
uv run --from python python bootstrap.py

# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv run --from python python bootstrap.py
```

## 🔧 Configuración

### URL del Google Sheet (obligatoria, una sola vez)

Edita `src/config.py` y reemplaza `DEFAULT_SHEET_URL` con tu URL:

```python
DEFAULT_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-TU_ID_REAL/pub?output=csv"
)
```

### Obtener la URL pública de Google Sheets

1. Abre tu Google Sheet
2. Menú: **Archivo → Compartir → Publicar en la web**
3. Selecciona la pestaña y formato **CSV**
4. Copia la URL generada

### (Opcional) Usar `.env` para sobrescribir la URL

Si prefieres no tocar el código:

```bash
cp .env.example .env
# Edita .env con: SHEET_CSV_URL=https://...
```

## 📋 Comandos principales

### Descargar datos desde Google Sheets

```bash
# Usa la URL por defecto de src/config.py
uv run python -m src.downloader

# O pasa una URL diferente como argumento
uv run python -m src.downloader "https://docs.google.com/.../pub?output=csv"
```

### Abrir el notebook de limpieza

```bash
uv run jupyter notebook notebooks/
```

Sigue las celdas paso a paso:
1. Cargar datos crudos
2. Explorar y visualizar
3. Aplicar transformaciones
4. Exportar a `data/processed/datos_limpios.csv`

### Ejecutar tests

```bash
uv run pytest tests/ -v
```

### Limpiar datos de la sesión

```bash
uv run python -c "from src.downloader import clean_session; clean_session()"
```

### Actualizar dependencias

```bash
uv lock --upgrade
uv sync
```

## 🔄 Flujo de trabajo típico

```bash
# 1. Descargar datos frescos
uv run python -m src.downloader

# 2. Abrir notebook y limpiar
uv run jupyter notebook notebooks/
# (ejecuta celdas, exporta CSV limpio)

# 3. (Opcional) Ejecutar tests
uv run pytest tests/ -v

# 4. (Futuro) Lanzar dashboard
uv run streamlit run src/dashboard/app.py
```

## ☁️ Despliegue del dashboard en la nube

PENDIENTE

## 🧪 Tests

```bash
# Ejecutar todos los tests
uv run pytest tests/ -v

# Con cobertura
uv run pytest tests/ --cov=src --cov-report=term-missing

# Solo un archivo
uv run pytest tests/test_downloader.py -v
```

## 🛠️ Solución de problemas

### "uv: command not found"

**Linux/macOS:**
```bash
source ~/.bashrc   # o ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"
```

**Windows:** Reinicia PowerShell o añade `%USERPROFILE%\.local\bin` al PATH.

### "ModuleNotFoundError: src"

Ejecuta los comandos desde la raíz del proyecto:
```bash
cd mi-proyecto
uv run python -m src.downloader
```

### "Error HTTP 404 al descargar"

Verifica que:
1. La URL en `src/config.py` es correcta
2. La hoja está **publicada** como CSV (no solo compartida)
3. La URL termina en `?output=csv`

### "El notebook no encuentra los datos"

Primero ejecuta la descarga:
```bash
uv run python -m src.downloader
```

## 📚 Recursos

- [Documentación de uv](https://docs.astral.sh/uv/)
- [Documentación de pandas](https://pandas.pydata.org/docs/)
- [Documentación de Streamlit](https://docs.streamlit.io/)
- [Publicar Google Sheets como CSV](https://support.google.com/docs/answer/183965)

## 👤 Autores
[@Asonxc](https://github.com/Asonxc)
[@decigamelanie-web](https://github.com/decigamelanie-web)
[@EstefaniDL](https://github.com/EstefaniDL)
[@MysticMichelle](https://github.com/MysticMichelle)
[@Sin_R0str0](https://github.com/SinR0str0)
[@songohan654](https://github.com/songohan654)
