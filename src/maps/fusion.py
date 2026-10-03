"""Integración de bloques de variables (imagen, clínica, biología) por sujeto.

Cada bloque es una tabla con una fila por observación. Se evalúa cada bloque
por separado y la fusión de todos con la misma validación cruzada agrupada por
sujeto, para ver qué añade cada fuente sobre las demás.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def _model() -> object:
    return make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        LogisticRegression(C=0.3, max_iter=2000, class_weight="balanced"),
    )


def out_of_fold_scores(x: pd.DataFrame, y: np.ndarray, groups: np.ndarray) -> np.ndarray:
    """Probabilidad predicha para cada fila por un modelo que no vio a su sujeto."""
    scores = np.empty(len(y), dtype=float)
    for train, test in LeaveOneGroupOut().split(x, y, groups):
        model = _model().fit(x.iloc[train], y[train])
        scores[test] = model.predict_proba(x.iloc[test])[:, 1]
    return scores


def bootstrap_auc(
    y: np.ndarray, scores: np.ndarray, groups: np.ndarray, *, n: int = 2000, seed: int = 0
) -> tuple[float, float, float]:
    """AUC con IC 95 % remuestreando sujetos, no filas: los cortes de un sujeto no son independientes."""
    rng = np.random.default_rng(seed)
    rows_by_group = [np.flatnonzero(groups == g) for g in np.unique(groups)]
    aucs = []
    for _ in range(n):
        pick = rng.integers(0, len(rows_by_group), len(rows_by_group))
        rows = np.concatenate([rows_by_group[i] for i in pick])
        if len(np.unique(y[rows])) == 2:
            aucs.append(roc_auc_score(y[rows], scores[rows]))
    lo, hi = np.percentile(aucs, [2.5, 97.5])
    return float(roc_auc_score(y, scores)), float(lo), float(hi)


def compare_blocks(
    blocks: dict[str, pd.DataFrame], y: np.ndarray, groups: np.ndarray
) -> pd.DataFrame:
    """AUC fuera de muestra de cada bloque y de la fusión temprana de todos."""
    candidates = dict(blocks)
    if len(blocks) > 1:
        candidates["+".join(blocks)] = pd.concat(list(blocks.values()), axis=1)
    rows = []
    for name, x in candidates.items():
        auc, lo, hi = bootstrap_auc(y, out_of_fold_scores(x, y, groups), groups)
        rows.append({"bloque": name, "n_variables": x.shape[1], "auc": auc, "ic95_inf": lo, "ic95_sup": hi})
    return pd.DataFrame(rows)
