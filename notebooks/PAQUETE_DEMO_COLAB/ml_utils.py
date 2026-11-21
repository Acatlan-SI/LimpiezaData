"""Utilidades compartidas del proyecto: rutas, definicion de variables,
transformadores sin fuga de informacion, modelos, validacion y metricas.

Todo lo que se "aprende" de los datos (vocabularios, imputaciones, escalas,
seleccion de variables, hiperparametros) se ajusta DENTRO de cada particion
de entrenamiento mediante Pipelines de scikit-learn.
"""
from __future__ import annotations

import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin, clone
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectKBest, VarianceThreshold, f_classif
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, brier_score_loss, f1_score,
    precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, RepeatedStratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]                 # ENTREGA_FINAL_MODELOS
ORIGINALES_DIR = Path(os.environ.get("FORMULARIOS_DIR", BASE_DIR.parent))
DATOS_DIR = BASE_DIR / "datos_derivados"
METRICAS_DIR = BASE_DIR / "resultados" / "metricas"
GRAFICAS_DIR = BASE_DIR / "resultados" / "graficas"
MODELOS_DIR = BASE_DIR / "modelos"
DOCS_DIR = BASE_DIR / "docs"

ARCHIVO_RELACIONES = "datos_limpios_relacionesamorosas.csv"
ARCHIVO_MUSICA = "datos_limpios_musica.csv"
ARCHIVO_PERSONALIDAD = "dtos_limpios._personalidad.csv"   # en realidad es un .xlsx

SEMILLA = 42
TARGET = "tiene_pareja"          # 1 = si tiene pareja (clase positiva), 0 = no

# ---------------------------------------------------------------------------
# Definicion de variables por formulario
#   num   -> numericas (imputacion mediana + escalado)
#   bin   -> binarias 0/1 (imputacion moda)
#   cat   -> categoricas de una sola etiqueta (one-hot, categorias raras agrupadas)
#   multi -> categoricas multi-etiqueta separadas por coma (indicadores 0/1)
# Se excluye texto libre (respuestas unicas por persona) e indicadores de
# calidad/auditoria (posible_copia, n_respuestas_copiadas).
# ---------------------------------------------------------------------------
VARS_RELACIONES = {
    "num": ["edad_primera_relacion_val", "diferencia_edad_max_val"],
    "bin": ["nunca_tuvo_relacion", "diferencia_edad_indefinida"],
    "cat": ["diferencia_edad_dir"],
    "multi": [
        "base_confianza", "definicion_respeto", "cualidad_valorada", "no_negociables",
        "demostracion_carino", "gesto_significativo", "resolucion_desacuerdos",
        "pareja_ideal_fisico_cat", "cita_ideal_cat",
    ],
}
VARS_MUSICA = {
    "num": ["mus_horas_dia", "mus_n_plataformas"],
    "bin": ["mus_escucha_musica", "mus_tuvo_experiencia", "mus_usa_spotify", "mus_usa_youtube",
            "mus_usa_youtube_music", "mus_usa_apple_music"],
    "cat": ["mus_cambio_animo", "mus_influencia_energia", "mus_efecto_concentracion",
            "mus_efecto_sueno", "mus_prefiere", "mus_ayuda_emociones", "mus_importancia_nivel"],
    "multi": ["mus_generos_frecuentes", "mus_razon_genero", "mus_generos_emocion",
              "mus_generos_animo_negativo", "mus_estrategia_animo_negativo", "mus_actividades",
              "mus_experiencia_conceptos", "mus_caracteristicas", "mus_mecanismos_ayuda"],
}


def combinar_vars(*specs):
    out = {"num": [], "bin": [], "cat": [], "multi": []}
    for s in specs:
        for k in out:
            out[k] += s[k]
    return out


def columnas(spec):
    return spec["num"] + spec["bin"] + spec["cat"] + spec["multi"]


# Escenarios solicitados. "ejecutable" se decide en 01_preparar_datos.py segun
# la verificacion de vinculacion; personalidad no tiene clave verificable.
ESCENARIOS = {
    "relaciones": {"spec": VARS_RELACIONES, "formularios": "Relaciones", "tipo": "principal"},
    "relaciones_musica": {"spec": combinar_vars(VARS_RELACIONES, VARS_MUSICA),
                          "formularios": "Relaciones + Musica", "tipo": "principal"},
    "musica_sola": {"spec": VARS_MUSICA, "formularios": "Musica (referencia)",
                    "tipo": "complementario"},
}
ESCENARIOS_NO_EJECUTABLES = {
    "relaciones_personalidad": "Relaciones + Personalidad",
    "relaciones_musica_personalidad": "Relaciones + Musica + Personalidad",
}


# ---------------------------------------------------------------------------
# Transformador multi-etiqueta (vocabulario aprendido solo en entrenamiento)
# ---------------------------------------------------------------------------
class MultiEtiquetaBinarizer(BaseEstimator, TransformerMixin):
    """Convierte columnas de texto 'a, b, c' en indicadores 0/1.

    El vocabulario se aprende en fit() y solo conserva etiquetas que aparecen
    al menos `min_freq` veces en los datos de entrenamiento.
    """

    def __init__(self, min_freq: int = 2, sep: str = ","):
        self.min_freq = min_freq
        self.sep = sep

    @staticmethod
    def _tokens(valor, sep):
        if valor is None or (isinstance(valor, float) and np.isnan(valor)) or pd.isna(valor):
            return set()
        return {t.strip().lower() for t in str(valor).split(sep) if t.strip()}

    def fit(self, X, y=None):
        X = pd.DataFrame(X)
        self.columnas_ = list(X.columns)
        self.vocabulario_ = {}
        for c in self.columnas_:
            conteo = {}
            for v in X[c]:
                for t in self._tokens(v, self.sep):
                    conteo[t] = conteo.get(t, 0) + 1
            self.vocabulario_[c] = sorted(t for t, n in conteo.items() if n >= self.min_freq)
        return self

    def transform(self, X):
        X = pd.DataFrame(X, columns=self.columnas_)
        bloques = []
        for c in self.columnas_:
            vocab = self.vocabulario_[c]
            m = np.zeros((len(X), len(vocab)), dtype=float)
            for i, v in enumerate(X[c]):
                toks = self._tokens(v, self.sep)
                for j, t in enumerate(vocab):
                    m[i, j] = float(t in toks)
            bloques.append(m)
        return np.hstack(bloques) if bloques else np.zeros((len(X), 0))

    def get_feature_names_out(self, input_features=None):
        return np.array([f"{c}={t}" for c in self.columnas_ for t in self.vocabulario_[c]], dtype=object)


# ---------------------------------------------------------------------------
# Pipelines
# ---------------------------------------------------------------------------
def preprocesador(spec) -> ColumnTransformer:
    partes = []
    if spec["num"]:
        partes.append(("num", Pipeline([("imp", SimpleImputer(strategy="median"))]), spec["num"]))
    if spec["bin"]:
        partes.append(("bin", SimpleImputer(strategy="most_frequent"), spec["bin"]))
    if spec["cat"]:
        partes.append(("cat", Pipeline([
            ("imp", SimpleImputer(strategy="constant", fill_value="faltante")),
            ("ohe", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=2,
                                  sparse_output=False)),
        ]), spec["cat"]))
    if spec["multi"]:
        partes.append(("multi", MultiEtiquetaBinarizer(min_freq=2), spec["multi"]))
    return ColumnTransformer(partes, remainder="drop", verbose_feature_names_out=True)


def pipeline_base(spec, modelo, seleccion=True) -> Pipeline:
    pasos = [
        ("prep", preprocesador(spec)),
        ("varianza", VarianceThreshold(0.0)),
        ("escalar", StandardScaler()),
    ]
    if seleccion:
        pasos.append(("seleccion", SelectKBest(f_classif, k="all")))
    pasos.append(("modelo", modelo))
    return Pipeline(pasos)


def definir_modelos(spec):
    """Devuelve {nombre: (pipeline, rejilla_hiperparametros)}."""
    return {
        "Dummy (prior)": (
            pipeline_base(spec, DummyClassifier(strategy="prior"), seleccion=False), None),
        "Logistic Regression": (
            pipeline_base(spec, LogisticRegression(class_weight="balanced", max_iter=5000,
                                                   solver="liblinear", random_state=SEMILLA)),
            {"seleccion__k": [3, 5, 10, "all"], "modelo__C": [0.01, 0.1, 1.0, 10.0]}),
        "Decision Tree": (
            pipeline_base(spec, DecisionTreeClassifier(class_weight="balanced", random_state=SEMILLA)),
            {"seleccion__k": [5, "all"], "modelo__max_depth": [1, 2, 3],
             "modelo__min_samples_leaf": [2, 4]}),
        "Random Forest": (
            pipeline_base(spec, RandomForestClassifier(n_estimators=100, class_weight="balanced",
                                                       min_samples_leaf=2, random_state=SEMILLA,
                                                       n_jobs=1)),
            {"seleccion__k": [10, "all"], "modelo__max_depth": [2, 3],
             "modelo__max_features": ["sqrt", 0.5]}),
    }


def cv_interna(semilla=SEMILLA):
    # 16 personas de entrenamiento por particion externa -> 4 particiones de ~4 personas.
    return RepeatedStratifiedKFold(n_splits=4, n_repeats=2, random_state=semilla)


def estimador_optimizable(pipe, rejilla, semilla=SEMILLA):
    if rejilla is None:
        return clone(pipe)
    return GridSearchCV(clone(pipe), rejilla, scoring="neg_brier_score", cv=cv_interna(semilla),
                        refit=True, n_jobs=1, error_score="raise")


# ---------------------------------------------------------------------------
# Metricas
# ---------------------------------------------------------------------------
def calcular_metricas(y, proba, umbral=0.5) -> dict:
    y = np.asarray(y).astype(int)
    proba = np.asarray(proba, dtype=float)
    pred = (proba > umbral).astype(int)   # empate 0.5 -> clase 0, igual que predict()
    auc = roc_auc_score(y, proba) if len(np.unique(y)) == 2 else np.nan
    return {
        "accuracy": accuracy_score(y, pred),
        "precision": precision_score(y, pred, zero_division=0),
        "recall": recall_score(y, pred, zero_division=0),
        "f1_macro": f1_score(y, pred, average="macro", zero_division=0),
        "balanced_accuracy": balanced_accuracy_score(y, pred),
        "roc_auc": auc,
        "brier": brier_score_loss(y, proba),
    }


METRICAS = ["accuracy", "precision", "recall", "f1_macro", "balanced_accuracy", "roc_auc", "brier"]


def silenciar_avisos():
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)
    os.environ["PYTHONWARNINGS"] = "ignore"   # se hereda a los procesos de joblib


def cargar_integrado() -> pd.DataFrame:
    return pd.read_csv(DATOS_DIR / "dataset_relaciones_musica.csv")
