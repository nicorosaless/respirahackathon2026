"""Resultados de la cohorte en agregados: qué separa la puntuación y qué deja la regla de clases.

Fija el umbral de daño con los sujetos de desarrollo y describe cada clase.
Imprime solo recuentos y medianas; los grupos de menos de 5 sujetos salen sin detalle.

    python scripts/report_cohort.py mn5/cohorte.early.toml
"""

from __future__ import annotations

import argparse
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score, roc_auc_score

from maps.classify import CLASSES, classify, damage_threshold

MIN_CELL = 5
DESCRIBE = ["puntuacion_dano", "fev1_fvc_post_v1", "FEV1pp_GLI_v1", "DLCO_v1", "CAT_v1", "mmrc_num_v1",
            "paquetes_año_v1", "cambio_fev1pp", "caida_fev1_ml_ano", "CAT_v2"]


def describe(table: pd.DataFrame, by: pd.Series) -> pd.DataFrame:
    rows = {}
    for level, part in table.groupby(by, observed=True):
        if len(part) < MIN_CELL:
            rows[level] = {"n": f"<{MIN_CELL}"}
            continue
        row = {"n": len(part), "% fuma": round(100 * (part["fuma"] == "fuma").mean()),
               "% enfisema visual": round(100 * (part["enfisema_visual"] == "sí").mean())}
        for column in DESCRIBE:
            values = part[column].dropna()
            row[column] = f"{values.median():.2f} (n={len(values)})" if len(values) >= MIN_CELL else f"n<{MIN_CELL}"
        rows[level] = row
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    config = tomllib.loads(args.config.read_text())
    cohort = Path(config["cohorte"])
    pd.set_option("display.width", 220, "display.max_columns", 20)

    t = pd.read_csv(cohort / "subjects.csv", dtype={"subject_id": str}).set_index("subject_id")
    dev = t.query(config.get("analisis", {}).get("filtro", "particion == 'desarrollo'"))
    case = dev["caso_v1"] == 1
    threshold = damage_threshold(dev["puntuacion_dano"], case)
    high = dev["puntuacion_dano"] >= threshold
    print(f"desarrollo: {len(dev)} sujetos, {int(case.sum())} con EPOC")
    print(f"AUC de la puntuación para EPOC: {roc_auc_score(case, dev['puntuacion_dano']):.2f}")
    print(f"umbral de daño (Youden): {threshold:.2f} | sensibilidad {high[case].mean():.2f} | especificidad {(~high[~case]).mean():.2f}")
    print(f"controles por encima del umbral: {int(high[~case].sum())} de {int((~case).sum())}")

    known = dev["enfisema_visual"].notna()
    print(f"\nacuerdo con el enfisema visual (kappa): {cohen_kappa_score(dev.loc[known, 'enfisema_visual'] == 'sí', high[known]):.2f}")
    print(pd.crosstab(dev.loc[known, "enfisema_visual"].rename("enfisema visual"), high[known].rename("daño por TC")).to_string())

    controls = dev[~case]
    print("\n== Controles de desarrollo, por daño objetivo en la TC ==")
    print(describe(controls, np.where(controls["puntuacion_dano"] >= threshold, "con daño", "sin daño")).to_string())

    print("\n== Clases en desarrollo ==")
    print(describe(dev, pd.Categorical(dev["clase_maps"], categories=CLASSES, ordered=True)).to_string())
    print("\nclase frente al grupo descriptivo (desarrollo):")
    print(pd.crosstab(dev["grupo"], dev["clase_maps"]).to_string())


if __name__ == "__main__":
    main()
