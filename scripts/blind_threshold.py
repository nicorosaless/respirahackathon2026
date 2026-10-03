"""¿Encuentra la TC, sin ver la espirometría, dónde está la frontera de la obstrucción?

Construye una puntuación ciega: lo esperado se ajusta con todos los sujetos, sin
saber quién es caso y quién control, dejando fuera a cada uno al puntuarlo. La
espirometría no entra en ningún paso. Después se levanta la tapa y se pregunta:

- ¿Sigue esa puntuación al FEV1/FVC?
- Si se parten los sujetos en dos grupos solo por su TC, ¿dónde cae la frontera
  y a qué valor de FEV1/FVC corresponde?
- ¿A partir de qué FEV1/FVC empieza a subir la puntuación?

Escribe `umbral_natural.json` en el directorio de la cohorte, con agregados.

    python scripts/blind_threshold.py mn5/cohorte.final.toml
"""

from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.mixture import GaussianMixture

from evaluate import auc
from maps.cohort import KEYS, damage_score, region_z

N_BOOTSTRAP = 2000
CUTS = np.round(np.arange(0.60, 0.851, 0.01), 2)
MIN_SIDE = 10  # sujetos a cada lado de un corte para poder evaluarlo


def mixture_threshold(score: np.ndarray) -> float:
    """El punto que separa dos grupos en la puntuación, sin ninguna etiqueta: mezcla de dos gaussianas."""
    model = GaussianMixture(2, random_state=0, n_init=5).fit(score.reshape(-1, 1))
    low, high = np.sort(model.means_.ravel())
    grid = np.linspace(low, high, 2001)
    top = int(np.argmax(model.means_.ravel()))
    return float(grid[np.argmin(np.abs(model.predict_proba(grid.reshape(-1, 1))[:, top] - 0.5))])


def breakpoint(score: np.ndarray, ratio: np.ndarray) -> float:
    """El FEV1/FVC por debajo del cual la puntuación empieza a subir: plana por encima, recta por debajo."""
    best = (np.inf, np.nan)
    for b in CUTS:
        x = np.column_stack([np.ones_like(ratio), np.minimum(ratio - b, 0.0)])
        residual = score - x @ np.linalg.lstsq(x, score, rcond=None)[0]
        best = min(best, (float(residual @ residual), float(b)))
    return best[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    config = tomllib.loads(args.config.read_text())
    cohort = Path(config["cohorte"])
    normative = config["normativo"]
    panel = tuple(config["puntuacion"]["medidas"])
    subjects = pd.read_csv(cohort / "subjects.csv", dtype={"subject_id": str}).set_index("subject_id")
    features = pd.read_csv(cohort / "features.csv", dtype={"subject_id": str})[[*KEYS, *panel]]

    # Lo esperado, ajustado con todos y sin etiquetas: cada sujeto se compara con un modelo de los demás.
    everyone = pd.Series(True, index=subjects.index)
    z = region_z(features, subjects, everyone, normative["covariables"], normative.get("categoricas", []))
    blind = damage_score(z, panel).reindex(subjects.index)
    ok = blind.notna()
    score, ratio = blind[ok].to_numpy(), subjects.loc[ok, "fev1_fvc_post_v1"].to_numpy(dtype=float)
    obstructed = ratio < 0.70
    rng = np.random.default_rng(0)
    draws = rng.integers(0, len(score), (N_BOOTSTRAP, len(score)))

    association = stats.spearmanr(score, ratio)
    inside = stats.spearmanr(score[~obstructed], ratio[~obstructed])
    out = {
        "sujetos": int(ok.sum()),
        "con_la_puntuacion_del_modelo": round(float(stats.spearmanr(score, subjects.loc[ok, "puntuacion_dano"]).statistic), 3),
        "fev1_fvc": {"rho": round(float(association.statistic), 3), "p": float(association.pvalue)},
        "fev1_fvc_sin_obstruccion": {"rho": round(float(inside.statistic), 3), "p": float(inside.pvalue), "n": int((~obstructed).sum())},
        "separa_0_70": round(auc(obstructed.astype(float), score), 3),
    }

    # 1. Dos grupos solo por la TC. ¿A qué FEV1/FVC corresponde la frontera?
    cut = mixture_threshold(score)
    above = score >= cut
    out["dos_grupos_por_la_tc"] = {
        "umbral_de_puntuacion": round(cut, 3), "por_encima": int(above.sum()), "por_debajo": int((~above).sum()),
        "fev1_fvc_mediana_por_encima": round(float(np.median(ratio[above])), 3),
        "fev1_fvc_mediana_por_debajo": round(float(np.median(ratio[~above])), 3),
        "con_obstruccion_por_encima": f"{int((above & obstructed).sum())} de {int(obstructed.sum())}",
        "sin_obstruccion_por_debajo": f"{int((~above & ~obstructed).sum())} de {int((~obstructed).sum())}",
    }

    # 2. ¿Qué corte del FEV1/FVC separa mejor la TC? Si la TC "ve" el 0,70, el máximo estará ahí.
    rows = []
    for c in CUTS:
        below = ratio < c
        if min(below.sum(), (~below).sum()) >= MIN_SIDE:
            rows.append({"corte": float(c), "auc": round(auc(below.astype(float), score), 3), "por_debajo": int(below.sum())})
    out["por_corte_del_cociente"] = rows
    out["corte_que_mejor_separa"] = max(rows, key=lambda row: row["auc"])["corte"]

    # 3. ¿A partir de qué FEV1/FVC empieza a subir la puntuación?
    point = breakpoint(score, ratio)
    resampled = [breakpoint(score[d], ratio[d]) for d in draws[:500]]
    out["empieza_a_subir_en"] = {"fev1_fvc": point, "ic95": [float(v) for v in np.percentile(resampled, [2.5, 97.5])]}

    out["coinciden_con_la_obstruccion"] = f"{int((above == obstructed).sum())} de {len(score)}"
    (cohort / "umbral_natural.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    # La puntuación ciega de cada sujeto y su grupo: son datos de sujetos, se quedan con la cohorte.
    pd.DataFrame({"subject_id": blind[ok].index, "puntuacion_ciega": score, "grupo_por_la_tc": np.where(above, "alto", "bajo")}).to_csv(
        cohort / "ciego.csv", index=False)
    print(json.dumps({k: v for k, v in out.items() if k != "por_corte_del_cociente"}, indent=1, ensure_ascii=False))
    print(pd.DataFrame(rows).T.to_string(header=False))


if __name__ == "__main__":
    main()
