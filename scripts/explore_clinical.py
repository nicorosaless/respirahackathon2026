"""Radiografía de la tabla clínica del reto: solo agregados, nunca filas de un sujeto.

Dice qué variables hay en cada visita, cuántas faltan, cómo se reparten y cómo
se relacionan, y deriva las que no vienen calculadas (cociente FEV1/FVC, caída
del FEV1 entre visitas).

    python scripts/explore_clinical.py /gpfs/.../EARLY_Hackathon_anonymous_definitive.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from maps.early import derive
from maps.tables import read_table


def by_group(t: pd.DataFrame, group: str, columns: list[str]) -> pd.DataFrame:
    rows = {}
    for column in columns:
        values = t[column].astype(float)
        rows[column] = {f"{group}={g}": f"{v.median():.2f} [{v.quantile(.25):.2f}, {v.quantile(.75):.2f}] n={v.notna().sum()}"
                        for g, v in values.groupby(t[group])}
    return pd.DataFrame(rows).T


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("table", type=Path)
    args = parser.parse_args()
    pd.set_option("display.width", 230, "display.max_rows", 200, "display.max_columns", 30)

    raw = read_table(args.table)
    t = derive(raw)
    print(f"{len(t)} sujetos, {raw.shape[1]} columnas; con visita 2: {int(t['edat_v2'].notna().sum())}")

    print("\n== Columnas: presentes, faltan, rango ==")
    summary = pd.DataFrame({"n": raw.notna().sum(), "faltan": raw.isna().sum(), "distintos": raw.nunique()})
    print(summary.join(raw.describe().T[["min", "25%", "50%", "75%", "max"]].round(2)).to_string())

    print("\n== Variables de pocos niveles ==")
    for column in raw.columns:
        if raw[column].nunique() <= 5:
            print(f"{column}: {dict(raw[column].value_counts(dropna=False).sort_index())}")
    print("talla media por sexo_num_v1 (para saber qué código es cada sexo):",
          dict(t.groupby("sexo_num_v1")["altura_v1"].mean().round(1)))

    print("\n== Derivadas ==")
    derived = ["fev1_fvc_post_v1", "fev1_fvc_post_v2", "anos_seguimiento", "caida_fev1_ml_ano", "cambio_fev1pp"]
    print(t[derived].describe().T[["count", "min", "25%", "50%", "75%", "max"]].round(3).to_string())
    for column in ("obstruccion_v1", "obstruccion_v2", "prism_v1", "prism_v2"):
        print(f"{column}: {dict(t[column].value_counts(dropna=False))}")

    print("\n== caso_v1 frente a obstrucción y enfisema ==")
    print(pd.crosstab(t["caso_v1"], t["obstruccion_v1"], dropna=False, margins=True))
    print(pd.crosstab(t["caso_v1"], t["enfisema_SI_v1"], dropna=False, margins=True))
    print(pd.crosstab(t["caso_v1"], t["edat_v2"].notna().rename("tiene_v2"), margins=True))
    both = t.dropna(subset=["obstruccion_v1", "obstruccion_v2"])
    print("obstrucción v1 -> v2:\n", pd.crosstab(both["obstruccion_v1"], both["obstruccion_v2"], margins=True))

    print("\n== Mediana [P25, P75] por caso_v1 ==")
    numeric = ["edat_round_v1", "imc_v1", "altura_v1", "paquetes_año_v1", "FEV1pp_GLI_v1", "FVCpp_GLI_v1",
               "fev1_fvc_post_v1", "DLCO_v1", "CAT_v1", "mmrc_num_v1", "COPD_PS_v1", "FENO_v1",
               "FEV1pp_GLI_v2", "fev1_fvc_post_v2", "DLCO_v2", "CAT_v2", "caida_fev1_ml_ano", "cambio_fev1pp"]
    print(by_group(t, "caso_v1", numeric).to_string())
    print("\n== Mediana [P25, P75] por enfisema_SI_v1, solo controles ==")
    controls = t[t["caso_v1"] == 0]
    print(by_group(controls, "enfisema_SI_v1", ["DLCO_v1", "CAT_v1", "mmrc_num_v1", "paquetes_año_v1",
                                                "FEV1pp_GLI_v1", "fev1_fvc_post_v1", "caida_fev1_ml_ano"]).to_string())

    print("\n== Candidatos a pre-EPOC entre los controles (caso_v1 = 0) ==")
    flags = pd.DataFrame({
        "enfisema": controls["enfisema_SI_v1"] == 1,
        "DLCO<80": controls["DLCO_v1"] < 80,
        "CAT>=10": controls["CAT_v1"] >= 10,
        "mMRC>=2": controls["mmrc_num_v1"] >= 2,
    })
    print(f"controles: {len(controls)}")
    print(flags.sum().to_string())
    print("número de criterios por control:", dict(flags.sum(axis=1).value_counts().sort_index()))
    print("enfisema y DLCO<80 a la vez:", int((flags["enfisema"] & flags["DLCO<80"]).sum()))

    print("\n== Correlación de Spearman entre variables clave (visita 1 y cambio) ==")
    key = ["FEV1pp_GLI_v1", "fev1_fvc_post_v1", "DLCO_v1", "CAT_v1", "mmrc_num_v1", "paquetes_año_v1", "FENO_v1",
           "enfisema_SI_v1", "actual_fuma_num_v1", "edat_round_v1", "caida_fev1_ml_ano"]
    print(t[key].corr(method="spearman").round(2).to_string())

    print("\n== Coherencia entre visitas (mismas unidades?) ==")
    for a, b in (("DLCO_v1", "DLCO_v2"), ("mmrc_num_v1", "mmrc_num_v2"), ("COPD_PS_v1", "COPD_PS_v2"),
                 ("CAT_v1", "CAT_v2"), ("FENO_v1", "FENO_v2"), ("altura_v1", "altura_v2")):
        pair = t[[a, b]].dropna()
        print(f"{a} mediana {pair[a].median():.1f} rango {pair[a].min():.1f}-{pair[a].max():.1f} | "
              f"{b} mediana {pair[b].median():.1f} rango {pair[b].min():.1f}-{pair[b].max():.1f} | "
              f"Spearman {pair[a].corr(pair[b], method='spearman'):.2f} n={len(pair)}")


if __name__ == "__main__":
    main()
