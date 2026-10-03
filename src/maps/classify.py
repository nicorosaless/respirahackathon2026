"""Clasificación en control, pre-EPOC y EPOC con una regla de tres líneas.

1. EPOC: FEV1/FVC posbroncodilatador menor de 0,70. Es la definición vigente.
2. Posible pre-EPOC: sin obstrucción, pero con la TC parecida a la de la EPOC
   (puntuación de daño por encima del umbral) o con la función ya alterada.
3. Control: lo demás.

El umbral de daño no se pone a ojo: es el punto de la puntuación que mejor
separa a los sujetos con EPOC de los que no la tienen. Un control por encima de
ese punto tiene un pulmón que, en la TC, se parece más al de la EPOC que al de
los demás controles.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

CONTROL, PRE_COPD, COPD = "control", "pre-EPOC", "EPOC"
CLASSES = (CONTROL, PRE_COPD, COPD)
OBSTRUCTION_RATIO = 0.70


def damage_threshold(score: pd.Series, case: pd.Series) -> float:
    """Umbral de la puntuación que maximiza sensibilidad + especificidad para EPOC (índice de Youden).

    `case` es verdadero en los sujetos con EPOC. Se ignoran los sujetos sin puntuación.
    """
    known = score.notna() & case.notna()
    values, labels = score[known].to_numpy(dtype=float), case[known].to_numpy(dtype=bool)
    if labels.all() or not labels.any():
        raise ValueError("hacen falta sujetos con EPOC y sin EPOC para fijar el umbral")
    order = np.argsort(values)
    values, labels = values[order], labels[order]
    # Candidatos: el punto medio entre cada par de puntuaciones vecinas distintas.
    cuts = (values[:-1] + values[1:]) / 2
    cuts = cuts[values[:-1] < values[1:]]
    sensitivity = np.array([(labels & (values >= c)).sum() for c in cuts]) / labels.sum()
    specificity = np.array([(~labels & (values < c)).sum() for c in cuts]) / (~labels).sum()
    return float(cuts[np.argmax(sensitivity + specificity)])


def classify(ratio: pd.Series, score: pd.Series, function_abnormal: pd.Series, threshold: float) -> pd.Series:
    """Clase de cada sujeto. Sin espirometría no hay clase; sin TC decide solo la función."""
    structural = (score >= threshold).fillna(False)
    functional = function_abnormal.fillna(False).astype(bool)
    out = pd.Series(CONTROL, index=ratio.index, dtype="object")
    out[structural | functional] = PRE_COPD
    out[ratio < OBSTRUCTION_RATIO] = COPD
    out[ratio.isna()] = pd.NA
    return out


def _number(value: float, decimals: int) -> str:
    return f"{value:.{decimals}f}".replace(".", ",").replace("-", "−")


def explain(ratio: pd.Series, score: pd.Series, function_abnormal: pd.Series, threshold: float,
            function_rule: str | None) -> pd.Series:
    """La frase que acompaña a la clase de cada sujeto: los números que la decidieron.

    Es una plantilla fija. `function_rule` dice con palabras qué se considera
    función alterada, por ejemplo "FEV1 por debajo del 80 % del predicho". Con
    `None` la regla no tiene criterio funcional y la frase no lo nombra.
    """
    functional = function_abnormal.fillna(False).astype(bool)
    out = pd.Series(pd.NA, index=ratio.index, dtype="object")
    for subject in ratio.index[ratio.notna()]:
        r, s = float(ratio[subject]), score[subject]
        if r < OBSTRUCTION_RATIO:
            out[subject] = f"FEV1/FVC de {_number(r, 2)}, por debajo de {_number(OBSTRUCTION_RATIO, 2)}: hay obstrucción."
            continue
        start = f"Sin obstrucción (FEV1/FVC de {_number(r, 2)})"
        measured = f"puntuación de {_number(float(s), 2)} con el umbral en {_number(threshold, 2)}" if pd.notna(s) else ""
        if pd.notna(s) and s >= threshold:
            tail = f" y con la función alterada: {function_rule}." if function_rule is not None and functional[subject] else "."
            out[subject] = f"{start}, con la TC parecida a la de la EPOC: {measured}{tail}"
            continue
        ct = f"con la TC por debajo del umbral ({measured})" if measured else "sin TC que medir"
        if function_rule is None:
            out[subject] = f"{start}, {ct}."
        elif functional[subject]:
            out[subject] = f"{start}, {ct}, con la función alterada: {function_rule}."
        else:
            out[subject] = f"{start}, {ct} y con la función conservada."
    return out
