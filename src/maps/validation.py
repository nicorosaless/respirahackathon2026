"""Evidencia honesta con pocos sujetos: qué añade cada bloque y qué no debería pesar.

La escalera evalúa bloques acumulados (clínica, más densitometría, más medidas
nuevas, más ómicas) con la misma validación cruzada anidada y reporta el
incremento de cada peldaño con su intervalo. `nuisance_association` comprueba
que la puntuación de daño no separa lo que no debe: escáner, sexo, centro.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from scipy import stats
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegressionCV, RidgeCV
from sklearn.model_selection import RepeatedKFold, RepeatedStratifiedKFold, StratifiedKFold
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler

Task = Literal["classification", "regression"]

# Rejillas sobre variables estandarizadas. Llegan a una regularización lo
# bastante fuerte para que un bloque de ómicas sin señal quede casi anulado.
# La logística va por décadas: su validación interna es lo que más tarda.
INVERSE_PENALTIES = np.logspace(-4, 1, 6)
RIDGE_PENALTIES = np.logspace(-2, 5, 15)


def _model(task: Task, n_splits: int, seed: int) -> Pipeline:
    """Imputación, escalado y modelo lineal que elige su regularización dentro del entrenamiento."""
    if task == "classification":
        estimator = LogisticRegressionCV(
            Cs=INVERSE_PENALTIES,
            l1_ratios=(0.0,),  # solo L2
            cv=StratifiedKFold(n_splits, shuffle=True, random_state=seed),
            class_weight="balanced",
            scoring="roc_auc",
            max_iter=2000,
            use_legacy_attributes=False,
        )
    else:
        estimator = RidgeCV(alphas=RIDGE_PENALTIES)  # validación interna dejando uno fuera, en forma cerrada
    # keep_empty_features: una columna vacía en un fold no debe cambiar el ancho de la matriz
    return make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True), StandardScaler(), estimator)


def _out_of_fold(x: np.ndarray, y: np.ndarray, task: Task, n_splits: int, n_repeats: int, seed: int) -> np.ndarray:
    """Predicción de cada sujeto por modelos que no lo vieron: una fila por repetición."""
    repeated = RepeatedStratifiedKFold if task == "classification" else RepeatedKFold
    splits = repeated(n_splits=n_splits, n_repeats=n_repeats, random_state=seed).split(x, y)
    predictions = np.empty((n_repeats, len(y)))
    for i, (train, test) in enumerate(splits):
        model = _model(task, n_splits, seed).fit(x[train], y[train])
        if task == "classification":
            predictions[i // n_splits, test] = model.predict_proba(x[test])[:, 1]
        else:
            # El término independiente es la media del entrenamiento, que baja
            # cuando el fold de prueba tiene valores altos. Al juntar folds eso
            # da una correlación negativa a un modelo que no ha aprendido nada.
            predictions[i // n_splits, test] = model.predict(x[test]) - y[train].mean()
    return predictions


def _metric(y: np.ndarray, prediction: np.ndarray, task: Task) -> np.ndarray:
    """AUC o Spearman a lo largo del último eje. NaN si no está definida (una sola clase, predicción constante)."""
    ranks = stats.rankdata(prediction, axis=-1)
    with np.errstate(invalid="ignore", divide="ignore"):
        if task == "classification":
            positives = y.sum(axis=-1)
            negatives = y.shape[-1] - positives
            # estadístico U de Mann-Whitney: fracción de pares positivo-negativo bien ordenados
            return ((ranks * y).sum(axis=-1) - positives * (positives + 1) / 2) / (positives * negatives)
        target = stats.rankdata(y, axis=-1)
        ranks = ranks - ranks.mean(axis=-1, keepdims=True)
        target = target - target.mean(axis=-1, keepdims=True)
        return (ranks * target).sum(axis=-1) / np.sqrt((ranks**2).sum(axis=-1) * (target**2).sum(axis=-1))


def _interval(samples: np.ndarray) -> tuple[float, float]:
    lo, hi = np.nanpercentile(samples, [2.5, 97.5])
    return float(lo), float(hi)


def _target(y: pd.Series, task: Task, n_splits: int) -> np.ndarray:
    if task == "regression":
        return y.to_numpy(dtype=float)
    if task != "classification":
        raise ValueError(f"task debe ser 'classification' o 'regression', no '{task}'")
    classes, codes = np.unique(y.to_numpy(), return_inverse=True)
    if len(classes) != 2:
        raise ValueError(f"la clasificación necesita dos clases en y y hay {len(classes)}")
    minority = int(np.bincount(codes).min())
    if minority < 2 * n_splits:
        raise ValueError(
            f"la clase minoritaria tiene {minority} sujetos y hacen falta al menos {2 * n_splits} "
            f"para que cada fold interno de la validación anidada tenga las dos clases"
        )
    return codes.astype(float)


def evidence_ladder(
    blocks: dict[str, pd.DataFrame],
    y: pd.Series,
    *,
    task: Task,
    n_splits: int = 5,
    n_repeats: int = 5,
    n_bootstrap: int = 2000,
    n_permutations: int = 200,
    seed: int = 0,
) -> pd.DataFrame:
    """Qué añade cada bloque de variables sobre los anteriores, fuera de muestra.

    `blocks` va en orden y cada bloque comparte el índice de `y`, con un sujeto
    por fila. El peldaño k usa las columnas de los bloques 1..k. Los sujetos sin
    `y` se descartan; los huecos en las variables se imputan con la mediana del
    fold de entrenamiento. En clasificación la clase positiva es la mayor de las
    dos al ordenarlas (True, 1).

    Cada peldaño se evalúa con K-fold repetido (estratificado en clasificación).
    Dentro de cada fold de entrenamiento se ajustan la imputación y el escalado,
    y el modelo elige su regularización con una validación cruzada interna:
    regresión logística L2 con clases equilibradas o ridge. Nada del fold de
    prueba interviene. Las predicciones se promedian entre repeticiones.

    Devuelve una fila por peldaño:

    - `escalon`, `n_variables`: bloques acumulados y cuántas columnas suman.
    - `metrica`, `ic95_inf`, `ic95_sup`: AUC en clasificación o correlación de
      Spearman entre predicción y objetivo en regresión, con IC 95 % por
      bootstrap de sujetos sobre las predicciones fuera de muestra.
    - `incremento`, `incremento_ic95_inf`, `incremento_ic95_sup`: este peldaño
      menos el anterior, con los mismos sujetos remuestreados en ambos. NaN en
      el primero.
    - `p_permutacion`: fracción de permutaciones de `y` cuya métrica iguala o
      supera a la observada (con la corrección +1). Con `n_permutations=0` no
      se calcula y queda NaN.

    Cada permutación repite la validación cruzada entera, así que para abaratar
    usa una sola repetición. Para comparar igual con igual, el valor observado
    que entra en la prueba es la métrica de la primera repetición, no la
    promediada que se reporta en `metrica`.

    El intervalo refleja qué sujetos cayeron en la muestra, no la variación de
    reajustar el modelo. En regresión las predicciones son desviaciones respecto
    a la media de entrenamiento de cada fold; sirven para ordenar sujetos.
    """
    if not blocks:
        raise ValueError("hace falta al menos un bloque")
    for name, block in blocks.items():
        if not block.index.equals(y.index):
            raise ValueError(f"el bloque '{name}' no comparte el índice de y")
        for column in block.columns:
            if not is_numeric_dtype(block[column]):
                raise ValueError(f"la columna '{column}' del bloque '{name}' no es numérica; codifícala antes")
    known = y.notna().to_numpy()
    target = _target(y[known], task, n_splits)
    n = len(target)
    rng = np.random.default_rng(seed)
    # los mismos remuestreos y permutaciones para todos los peldaños: comparación emparejada
    resamples = rng.integers(0, n, (n_bootstrap, n))
    permutations = [rng.permutation(n) for _ in range(n_permutations)]

    rows = []
    names: list[str] = []
    x = np.empty((n, 0))
    previous = previous_bootstrap = None
    for name, block in blocks.items():
        names.append(name)
        x = np.hstack([x, block.to_numpy(dtype=float, na_value=np.nan)[known]])
        repeats = _out_of_fold(x, target, task, n_splits, n_repeats, seed)
        prediction = repeats.mean(axis=0)
        metric = float(_metric(target, prediction, task))
        bootstrap = _metric(target[resamples], prediction[resamples], task)
        lo, hi = _interval(bootstrap)
        if previous is None:
            increment, increment_lo, increment_hi = np.nan, np.nan, np.nan
        else:
            increment = metric - previous
            increment_lo, increment_hi = _interval(bootstrap - previous_bootstrap)
        p_value = np.nan
        if permutations:
            observed = _metric(target, repeats[0], task)
            null = [
                _metric(target[p], _out_of_fold(x, target[p], task, n_splits, 1, seed)[0], task)
                for p in permutations
            ]
            p_value = float(1 + np.sum(np.asarray(null) >= observed)) / (1 + n_permutations)
        rows.append(
            {
                "escalon": "+".join(names),
                "n_variables": x.shape[1],
                "metrica": metric,
                "ic95_inf": lo,
                "ic95_sup": hi,
                "incremento": increment,
                "incremento_ic95_inf": increment_lo,
                "incremento_ic95_sup": increment_hi,
                "p_permutacion": p_value,
            }
        )
        previous, previous_bootstrap = metric, bootstrap
    return pd.DataFrame(rows)


def nuisance_association(
    score: pd.Series, nuisance: pd.Series, *, n_bootstrap: int = 2000, seed: int = 0
) -> dict:
    """Cuánto separa una puntuación los niveles de una variable que no debería importar.

    `score` y `nuisance` (escáner, sexo, centro) se alinean por índice y se
    descartan los sujetos a los que falta alguno de los dos. Siempre devuelve
    `n` (sujetos usados) y `niveles`. Además:

    - Con dos niveles: `auc`, `ic95_inf`, `ic95_sup`. El AUC va plegado: 0,5 es
      ninguna asociación y nunca baja de ahí, sea cual sea el nivel con
      puntuaciones más altas. El IC 95 % por bootstrap de sujetos mantiene la
      orientación de la estimación, así que sí puede bajar de 0,5: si lo
      incluye, la separación no se distingue del azar.
    - Con más niveles: `p_kruskal` (prueba de Kruskal-Wallis) y `eta2`, la
      fracción de la variación de los rangos que explican los niveles,
      (H - k + 1) / (n - k), recortada a 0.
    """
    paired = pd.DataFrame({"score": score, "nuisance": nuisance}).dropna()
    levels, codes = np.unique(paired["nuisance"].to_numpy(), return_inverse=True)
    if len(levels) < 2:
        raise ValueError(f"hacen falta al menos dos niveles de la variable y hay {len(levels)}")
    values = paired["score"].to_numpy(dtype=float)
    n = len(values)
    out = {"n": n, "niveles": levels.tolist()}
    if len(levels) == 2:
        group = codes.astype(float)
        auc = float(_metric(group, values, "classification"))
        if auc < 0.5:  # se toma como positivo el nivel con puntuaciones más altas
            group, auc = 1.0 - group, 1.0 - auc
        resamples = np.random.default_rng(seed).integers(0, n, (n_bootstrap, n))
        lo, hi = _interval(_metric(group[resamples], values[resamples], "classification"))
        return out | {"auc": auc, "ic95_inf": lo, "ic95_sup": hi}
    h, p_value = stats.kruskal(*(values[codes == level] for level in range(len(levels))))
    eta2 = max(0.0, (h - len(levels) + 1) / (n - len(levels)))
    return out | {"p_kruskal": float(p_value), "eta2": float(eta2)}
