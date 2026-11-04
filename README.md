# 📊 Limpieza de Datos

Pipeline de datos que descarga información desde Google Sheets, la limpia en un notebook interactivo y la expone en un dashboard en la nube.

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
├── .env.example            # Plantilla de variables de entorno
├── .gitignore
│
├── src/
│   ├── __init__.py
│   ├── config.py           # Rutas y configuración
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

### Instalación en un solo comando

#### 🐧 Linux / 🍎 macOS

```bash
# 1. Instalar uv (si no lo tienes)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Recargar la shell (solo la primera vez)
source ~/.bashrc   # o ~/.zshrc

# 3. Clonar el repositorio
git clone https://github.com/TU_USUARIO/mi-proyecto.git
cd mi-proyecto

# 4. Sincronizar dependencias (crea .venv automáticamente)
uv sync

# 5. Configurar la URL de tu Google Sheet
cp .env.example .env
# Edita .env y pon tu URL real
```

#### 🪟 Windows (PowerShell como administrador)

```powershell
# 1. Instalar uv
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2. Reiniciar PowerShell

# 3. Clonar el repositorio
git clone https://github.com/Acatlan-SI/LimpiezaData.git
cd mi-proyecto

# 4. Sincronizar dependencias
uv sync

# 5. Configurar la URL
copy .env.example .env
# Edita .env con tu URL real
```

### Instalación alternativa con bootstrap (sin git)

Si no tienes git instalado, usa el bootstrap:

```bash
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
uv run --from python python bootstrap.py

# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv run --from python python bootstrap.py
```

## 🔧 Configuración

### Variable de entorno

Crea un archivo `.env` en la raíz (ya tienes `.env.example`):

```bash
SHEET_CSV_URL=https://docs.google.com/spreadsheets/d/e/2PACX-TU_ID/pub?output=csv
```

### Obtener la URL pública de Google Sheets

1. Abre tu Google Sheet
2. Menú: **Archivo → Compartir → Publicar en la web**
3. Selecciona la pestaña deseada y formato **CSV**
4. Copia la URL generada y pégala en `.env`

## 📋 Comandos principales

### Descargar datos desde Google Sheets

```bash
# Linux / macOS / Windows
uv run python -m src.downloader
```

Esto descarga el CSV a `data/raw/datos_raw.csv`.

### Abrir el notebook de limpieza

```bash
# Todos los sistemas
uv run jupyter notebook notebooks/
```

Se abrirá el navegador en `http://localhost:8888`. Sigue las celdas paso a paso:
1. Cargar datos crudos
2. Explorar y visualizar
3. Aplicar transformaciones
4. Exportar a `data/processed/datos_limpios.csv`

### Ejecutar tests

```bash
# Todos los sistemas
uv run pytest tests/ -v
```

### Limpiar datos de la sesión

```bash
# Todos los sistemas
uv run python -c "from src.downloader import clean_session; clean_session()"
```

Esto elimina todos los CSV de `data/raw/` y `data/processed/`.

### Actualizar dependencias

```bash
# Todos los sistemas
uv lock --upgrade
uv sync
```

## 🔄 Flujo de trabajo típico

```bash
# 1. Descargar datos frescos
uv run python -m src.downloader

# 2. Abrir notebook y limpiar
uv run jupyter notebook notebooks/
# (ejecuta todas las celdas, exporta CSV limpio)

# 3. Verificar que se generó el CSV limpio
ls data/processed/

# 4. (Opcional) Ejecutar tests
uv run pytest tests/ -v

# 5. (Futuro) Lanzar dashboard
uv run streamlit run src/dashboard/app.py
```

## ☁️ Despliegue del dashboard en la nube

Por llenar

## 🧪 Tests

Los tests están en `tests/` y usan `pytest`:

```bash
# Ejecutar todos los tests
uv run pytest tests/ -v

# Ejecutar con cobertura
uv run pytest tests/ --cov=src --cov-report=term-missing

# Ejecutar solo un archivo
uv run pytest tests/test_downloader.py -v
```

## 🛠️ Solución de problemas

### "uv: command not found"

**Linux/macOS:**
```bash
source ~/.bashrc   # o ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"
```

**Windows:**
Reinicia PowerShell o añade `%USERPROFILE%\.local\bin` al PATH.

### "ModuleNotFoundError: src"

Asegúrate de ejecutar los comandos desde la raíz del proyecto:
```bash
cd mi-proyecto
uv run python -m src.downloader
```

### "Error HTTP 404 al descargar"

Verifica que:
1. La URL en `.env` es correcta
2. La hoja está publicada como CSV (no solo compartida)
3. La URL termina en `?output=csv`

### "El notebook no encuentra los datos"

Primero ejecuta la descarga:
```bash
uv run python -m src.downloader
```

Luego abre el notebook.

### "Permission denied" al ejecutar bootstrap

```bash
chmod +x bootstrap.py
```

## 📚 Recursos

- [Documentación de uv](https://docs.astral.sh/uv/)
- [Documentación de pandas](https://pandas.pydata.org/docs/)
- [Documentación de Streamlit](https://docs.streamlit.io/)
- [Publicar Google Sheets como CSV](https://support.google.com/docs/answer/183965)