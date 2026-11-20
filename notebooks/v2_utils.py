"""Utilidades de la fase OPTIMIZACION_V2.

Reutiliza el modulo de la entrega V1 (`ENTREGA_FINAL_MODELOS/src/ml_utils.py`) mediante importacion:
transformador multi-etiqueta, metricas, CV interna y GridSearchCV. Anade:
  * representacion V2 (ordinal fija con significado, categorias raras agrupadas con frecuencia >= 3,
    filtro de redundancia aprendido en entrenamiento, exclusion de `nunca_tuvo_relacion`);
  * candidatos nuevos con rejillas pequenas y un meta-procedimiento que elige la familia dentro de la CV interna;
  * CV anidada que conserva variables seleccionadas por particion (estabilidad) y AUC por particion.

Todo lo que se aprende de los datos se ajusta dentro de cada particion de entrenamiento (Pipelines).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.base import BaseEstimator, TransformerMixin, clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.feature_selection import SelectKBest, VarianceThreshold, f_classif
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GridSearchCV, RepeatedStratifiedKFold
from sklearn.naive_bayes import BernoulliNB, GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

# --------------------------------------------------------------------------- reutilizacion de la V1
V2_DIR = Path(__file__).resolve().parents[1]                  # OPTIMIZACION_V2
V1_DIR = V2_DIR.parent                                         # ENTREGA_FINAL_MODELOS
sys.path.insert(0, str(V1_DIR / "src"))
import ml_utils as v1  # noqa: E402
from ml_utils import (  # noqa: E402,F401
    METRICAS, SEMILLA, TARGET, MultiEtiquetaBinarizer, calcular_metricas, cargar_integrado,
    estimador_optimizable, silenciar_avisos,
)

METRICAS_V1_DIR = v1.METRICAS_DIR
MET_DIR = V2_DIR / "resultados" / "metricas"
GRAF_DIR = V2_DIR / "resultados" / "graficas"
CACHE_DIR = V2_DIR / "resultados" / "cache"
MOD_DIR = V2_DIR / "modelos"
N_PARTICIONES = 5
METRICAS_V2 = METRICAS + ["roc_auc_por_particion"]

# --------------------------------------------------------------------------- variables V2
# Codificacion ordinal FIJA (definida por el significado de la respuesta, no aprendida de los datos).
# "indeterminado" -> faltante (se imputa con la mediana de entrenamiento).
MAPAS_ORDINALES = {
    "mus_importancia_nivel": {"baja": 0, "media": 1, "alta": 2},
    "mus_influencia_energia": {"baja/nula": 0, "media": 1, "alta": 2},
    "mus_cambio_animo": {"sin cambio": 0, "mejora": 1},
    "mus_ayuda_emociones": {"no": 0, "condicional": 0.5, "si": 1},
    "mus_efecto_concentracion": {"distrae": -1, "sin efecto": 0, "depende/regular": 0, "ayuda": 1},
    "mus_efecto_sueno": {"perjudica": -1, "sin efecto": 0, "no la usa para dormir": 0,
                         "depende/regular": 0, "favorece": 1},
    "mus_prefiere": {"prefiere silencio": -1, "sin diferencia": 0, "depende/mixto": 0, "prefiere musica": 1},
}

VARS_REL_V2 = {
    "num": ["edad_primera_relacion_val", "diferencia_edad_max_val"],
    "bin": ["diferencia_edad_indefinida"],               # se excluye nunca_tuvo_relacion (revela el objetivo)
    "ord": [],
    "cat": ["diferencia_edad_dir"],
    "multi": list(v1.VARS_RELACIONES["multi"]),
}
VARS_MUS_V2 = {
    "num": list(v1.VARS_MUSICA["num"]),
    "bin": list(v1.VARS_MUSICA["bin"]),
    "ord": list(MAPAS_ORDINALES),
    "cat": [],
    "multi": list(v1.VARS_MUSICA["multi"]),
}
assert set(VARS_MUS_V2["ord"]) == set(v1.VARS_MUSICA["cat"])
EXCLUIDAS = {"nunca_tuvo_relacion": "implica logicamente tiene_pareja = 0 (revela el objetivo)"}


def combinar(*specs):
    out = {k: [] for k in ("num", "bin", "ord", "cat", "multi")}
    for s in specs:
        for k in out:
            out[k] += s[k]
    return out


def columnas(spec):
    return spec["num"] + spec["bin"] + spec["ord"] + spec["cat"] + spec["multi"]


ESCENARIOS_V2 = {
    "relaciones": VARS_REL_V2,
    "musica_sola": VARS_MUS_V2,
    "relaciones_musica": combinar(VARS_REL_V2, VARS_MUS_V2),
}
NOMBRE_ESCENARIO = {"relaciones": "Relaciones", "musica_sola": "Música", "relaciones_musica": "Relaciones + Música"}


# --------------------------------------------------------------------------- transformadores
class MapeoOrdinal(BaseEstimator, TransformerMixin):
    """Aplica MAPAS_ORDINALES (fijos). Valores no previstos -> NaN. No aprende nada de los datos."""

    def fit(self, X, y=None):
        self.columnas_ = list(pd.DataFrame(X).columns)
        return self

    def transform(self, X):
        X = pd.DataFrame(X, columns=self.columnas_)
        return np.column_stack([X[c].map(MAPAS_ORDINALES[c]).astype(float).to_numpy() for c in self.columnas_])

    def get_feature_names_out(self, input_features=None):
        return np.array(self.columnas_, dtype=object)


class FiltroCorrelacion(BaseEstimator, TransformerMixin):
    """Elimina variables redundantes: de cada par con |r| > umbral conserva la primera (aprendido en fit)."""

    def __init__(self, umbral: float = 0.9):
        self.umbral = umbral

    def fit(self, X, y=None):
        X = np.asarray(X, dtype=float)
        self.n_features_in_ = X.shape[1]
        sd = X.std(axis=0)
        keep = np.ones(X.shape[1], dtype=bool)
        if X.shape[1] > 1:
            with np.errstate(invalid="ignore", divide="ignore"):
                r = np.abs(np.corrcoef(X, rowvar=False))
            r = np.nan_to_num(r, nan=0.0)
            for j in range(X.shape[1]):
                if sd[j] == 0:
                    continue
                if keep[j]:
                    redundantes = (r[j] > self.umbral) & (np.arange(X.shape[1]) > j)
                    keep[redundantes] = False
        self.support_ = keep
        return self

    def transform(self, X):
        return np.asarray(X, dtype=float)[:, self.support_]

    def get_support(self):
        return self.support_

    def get_feature_names_out(self, input_features=None):
        if input_features is None:
            input_features = np.array([f"x{i}" for i in range(self.n_features_in_)], dtype=object)
        return np.asarray(input_features, dtype=object)[self.support_]


class SelectKBestSeguro(SelectKBest):
    """SelectKBest que recorta k al numero de variables disponibles (evita errores cuando el filtro elimina muchas)."""

    def _check_params(self, X, y):
        pass

    def _get_support_mask(self):
        k = self.k
        n = len(self.scores_)
        if k == "all" or k >= n:
            return np.ones(n, dtype=bool)
        return super()._get_support_mask() if k >= 0 else np.ones(n, dtype=bool)


def preprocesador_v2(spec, min_freq: int = 3) -> ColumnTransformer:
    partes = []
    if spec["num"]:
        partes.append(("num", SimpleImputer(strategy="median"), spec["num"]))
    if spec["bin"]:
        partes.append(("bin", SimpleImputer(strategy="most_frequent"), spec["bin"]))
    if spec["ord"]:
        partes.append(("ord", Pipeline([("map", MapeoOrdinal()), ("imp", SimpleImputer(strategy="median"))]),
                       spec["ord"]))
    if spec["cat"]:
        partes.append(("cat", Pipeline([
            ("imp", SimpleImputer(strategy="constant", fill_value="faltante")),
            ("ohe", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=min_freq,
                                  sparse_output=False)),
        ]), spec["cat"]))
    if spec["multi"]:
        partes.append(("multi", MultiEtiquetaBinarizer(min_freq=min_freq), spec["multi"]))
    return ColumnTransformer(partes, remainder="drop", verbose_feature_names_out=True)


def pipe_v2(spec, modelo, reductor="kbest") -> Pipeline:
    """prep -> varianza 0 -> filtro |r|>0.9 -> escalado -> [SelectKBest | PCA | nada] -> modelo."""
    pasos = [("prep", preprocesador_v2(spec)), ("varianza", VarianceThreshold(0.0)),
             ("redundancia", FiltroCorrelacion(0.9)), ("escalar", StandardScaler())]
    if reductor == "kbest":
        pasos.append(("seleccion", SelectKBestSeguro(f_classif, k="all")))
    elif reductor == "pca":
        pasos.append(("pca", PCA(n_components=2, random_state=SEMILLA)))
    pasos.append(("modelo", modelo))
    return Pipeline(pasos)


def _svm(kernel):
    return CalibratedClassifierCV(SVC(kernel=kernel, class_weight="balanced", random_state=SEMILLA),
                                  method="sigmoid", cv=3, ensemble=False)


def candidatos_v2(spec):
    """{nombre: (pipeline, rejilla)}; rejillas pequenas fijadas en docs/PREREGISTRO.md."""
    lr = dict(class_weight="balanced", max_iter=20000, random_state=SEMILLA)
    c = {
        "LogReg Elastic Net": (
            pipe_v2(spec, LogisticRegression(solver="saga", **lr), reductor=None),
            {"modelo__C": [0.05, 0.2, 1.0], "modelo__l1_ratio": [0.0, 0.5, 1.0]}),
        "LogReg pocas variables": (
            pipe_v2(spec, LogisticRegression(solver="lbfgs", **lr)),
            {"seleccion__k": [1, 2, 3], "modelo__C": [0.1, 1.0]}),
        "SVM lineal": (
            pipe_v2(spec, _svm("linear")),
            {"seleccion__k": [5, "all"], "modelo__estimator__C": [0.01, 0.1, 1.0]}),
        "SVM RBF": (
            pipe_v2(spec, _svm("rbf"), reductor=None),
            {"modelo__estimator__C": [0.1, 1.0, 10.0], "modelo__estimator__gamma": ["scale", 0.01]}),
        "LDA contraccion": (
            pipe_v2(spec, LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto", priors=[0.5, 0.5])),
            {"seleccion__k": [5, 10, "all"]}),
        "PCA + LogReg": (
            pipe_v2(spec, LogisticRegression(solver="lbfgs", **lr), reductor="pca"),
            {"pca__n_components": [2, 3, 5], "modelo__C": [0.1, 1.0]}),
        "Bernoulli NB": (
            pipe_v2(spec, BernoulliNB(binarize=0.0, fit_prior=False)),
            {"modelo__alpha": [0.5, 1.0, 2.0], "seleccion__k": [5, 10, "all"]}),
        "Gaussian NB": (
            pipe_v2(spec, GaussianNB(priors=[0.5, 0.5])),
            {"seleccion__k": [3, 5, 10]}),
        "KNN": (
            pipe_v2(spec, KNeighborsClassifier()),
            {"modelo__n_neighbors": [3, 5, 7], "seleccion__k": [5, 10]}),
        "Arbol podado": (
            pipe_v2(spec, DecisionTreeClassifier(class_weight="balanced", min_samples_leaf=3,
                                                 random_state=SEMILLA), reductor=None),
            {"modelo__max_depth": [1, 2, 3], "modelo__ccp_alpha": [0.0, 0.02]}),
        "Random Forest regularizado": (
            pipe_v2(spec, RandomForestClassifier(n_estimators=300, min_samples_leaf=3, max_features="sqrt",
                                                 class_weight="balanced", random_state=SEMILLA, n_jobs=1),
                    reductor=None),
            {"modelo__max_depth": [2, 3]}),
        "Extra Trees regularizado": (
            pipe_v2(spec, ExtraTreesClassifier(n_estimators=300, min_samples_leaf=3, max_features="sqrt",
                                               class_weight="balanced", random_state=SEMILLA, n_jobs=1),
                    reductor=None),
            {"modelo__max_depth": [2, 3]}),
    }
    return c


def ablacion_v1_en_v2(spec):
    """Modelos y rejillas EXACTOS de la V1 sobre la representacion V2 (aisla el efecto de las variables)."""
    out = {}
    for nombre, (pipe_v1, rej) in v1.definir_modelos({k: [] for k in ("num", "bin", "cat", "multi")}).items():
        if rej is None:
            continue
        out[f"{nombre} (rejilla V1)"] = (pipe_v2(spec, clone(pipe_v1.named_steps["modelo"])), rej)
    return out


def meta_seleccion(spec):
    """Una sola 'caja' que elige la familia de modelo + hiperparametros dentro de la CV interna.
    Su estimacion externa incluye el coste de elegir entre familias (correccion del sesgo de seleccion)."""
    rejilla = []
    for nombre, (pipe, rej) in candidatos_v2(spec).items():
        rejilla.append({"clf": [pipe], **{f"clf__{k}": v for k, v in rej.items()}})
    return Pipeline([("clf", candidatos_v2(spec)["LogReg Elastic Net"][0])]), rejilla


def dummy(spec):
    return pipe_v2(spec, DummyClassifier(strategy="prior"), reductor=None), None


# --------------------------------------------------------------------------- CV anidada con detalle
def _familia(est):
    """Nombre de la familia de un pipeline final (para la meta-seleccion)."""
    pipe = est.named_steps["clf"] if "clf" in est.named_steps else est
    m = pipe.named_steps["modelo"]
    if isinstance(m, CalibratedClassifierCV):
        m = m.estimator
    nombre = type(m).__name__
    if nombre == "SVC":
        nombre += f"-{m.kernel}"
    if "pca" in pipe.named_steps:
        nombre = "PCA+" + nombre
    if nombre == "LogisticRegression" and "seleccion" in pipe.named_steps:
        nombre += "+SelectKBest"
    return nombre


def variables_usadas(est):
    """Nombres de variables realmente usadas por el pipeline final (tras filtro/seleccion/coeficientes)."""
    pipe = est.named_steps["clf"] if "clf" in est.named_steps else est
    if "pca" in pipe.named_steps:
        return ["(componentes PCA)"]
    nombres = pipe[:-1].get_feature_names_out()
    m = pipe.named_steps["modelo"]
    if hasattr(m, "coef_") and isinstance(m, LogisticRegression):
        return list(nombres[np.abs(m.coef_[0]) > 1e-10])
    if hasattr(m, "feature_importances_"):
        return list(nombres[m.feature_importances_ > 0])
    return list(nombres)


def _ajustar(pipe, rejilla, X, y, tr, te, rep, semilla):
    silenciar_avisos()
    est = estimador_optimizable(pipe, rejilla, semilla + rep)     # reutiliza V1: GridSearchCV(neg_brier, 4x2)
    est.fit(X.iloc[tr], y.iloc[tr])
    proba = est.predict_proba(X.iloc[te])[:, 1]
    best = getattr(est, "best_estimator_", est)
    params = {k: (v if not hasattr(v, "fit") else "pipeline") for k, v in getattr(est, "best_params_", {}).items()}
    try:
        usadas = variables_usadas(best)
    except Exception:  # pragma: no cover - solo informativo
        usadas = []
    return rep, te, proba, params, _familia(best), usadas


def particiones(y, repeticiones, semilla=SEMILLA):
    """Mismas particiones externas que la V1 (RepeatedStratifiedKFold 5 x R, semilla 42)."""
    cv = RepeatedStratifiedKFold(n_splits=N_PARTICIONES, n_repeats=repeticiones, random_state=semilla)
    return [(i // N_PARTICIONES, i % N_PARTICIONES, tr, te) for i, (tr, te) in enumerate(cv.split(np.zeros(len(y)), y))]


def evaluar(pipe, rejilla, X, y, repeticiones, n_jobs=-1, semilla=SEMILLA):
    tareas = particiones(y, repeticiones, semilla)
    salida = Parallel(n_jobs=n_jobs)(delayed(_ajustar)(pipe, rejilla, X, y, tr, te, rep, semilla)
                                     for rep, _, tr, te in tareas)
    probas = np.full((repeticiones, len(y)), np.nan)
    pliegue = np.full((repeticiones, len(y)), -1)
    detalle = []
    for (rep, f, _, te), (_, _, p, prm, fam, usadas) in zip(tareas, salida):
        probas[rep, te] = p
        pliegue[rep, te] = f
        detalle.append({"repeticion": rep, "particion": f, "familia": fam, "variables": "|".join(usadas),
                        "n_variables": len(usadas), **{k: str(v) for k, v in prm.items()}})
    assert not np.isnan(probas).any()
    return probas, pliegue, pd.DataFrame(detalle)


def metricas_rep(y, probas, pliegue):
    y = np.asarray(y).astype(int)
    filas = []
    for r in range(len(probas)):
        m = calcular_metricas(y, probas[r])
        aucs = [roc_auc_score(y[pliegue[r] == f], probas[r][pliegue[r] == f])
                for f in range(N_PARTICIONES) if len(np.unique(y[pliegue[r] == f])) == 2]
        m["roc_auc_por_particion"] = float(np.mean(aucs)) if aucs else np.nan
        filas.append({"repeticion": r, **m})
    return pd.DataFrame(filas)


def clave_cache(escenario, nombre, pipe, rejilla, repeticiones, X, y):
    """Huella del experimento: configuracion completa (joblib.hash, sin truncar), datos y codigo V1/V2."""
    import joblib
    codigo = (Path(__file__).read_bytes() + (V1_DIR / "src" / "ml_utils.py").read_bytes())
    partes = [escenario, nombre, joblib.hash(pipe), joblib.hash(rejilla), repeticiones, SEMILLA,
              joblib.hash(X), joblib.hash(y), hashlib.sha256(codigo).hexdigest()]
    return hashlib.sha256(json.dumps(partes, default=str).encode()).hexdigest()[:12]
