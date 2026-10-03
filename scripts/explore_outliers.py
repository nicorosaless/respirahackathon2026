"""¿Quiénes son los que se salen? Los sujetos cuya TC no cuadra con su espirometría.

Dos grupos de discordantes y una pregunta para cada uno:

- Controles con la TC parecida a la de la EPOC: ¿en qué se diferencian de los
  demás controles? ¿Apunta a tabaco, a un árbol bronquial pequeño de origen o a nada?
- Sujetos con EPOC cuya TC es como la de los controles: ¿en qué se diferencian
  de los demás casos? ¿Asma, obstrucción que luego desaparece?

Compara cada grupo con sus iguales en todas las variables de la tabla y, además,
relaciona la puntuación con cada variable dentro de los controles y dentro de
los casos. Es exploratorio: muchas comparaciones y pocos sujetos; se corrige por
comparaciones múltiples y se informa todo, salga o no. Escribe `discordantes.json`
con agregados; los grupos de menos de 5 sujetos salen sin detalle.

    python scripts/explore_outliers.py mn5/cohorte.final.toml
"""

from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from check_score import MIN_CELL, benjamini_hochberg
from maps.cohort import damage_score

SCORE = "puntuacion_dano"
NUMERIC = {
    "edat_round_v1": "Edad", "altura_v1": "Talla, cm", "imc_v1": "IMC", "paquetes_año_v1": "Paquetes-año",
    "fev1_fvc_post_v1": "FEV1/FVC", "FEV1pp_GLI_v1": "FEV1, % del predicho", "FVCpp_GLI_v1": "FVC, % del predicho",
    "reversibilidad_pct": "Respuesta al broncodilatador, % del FEV1", "DLCO_v1": "DLCO, % del predicho",
    "CAT_v1": "CAT", "mmrc_num_v1": "Disnea (mMRC)", "COPD_PS_v1": "COPD-PS", "FENO_v1": "FENO",
    "volumen_pulmon_ml": "Volumen pulmonar en la TC, mL", "cambio_cociente": "Cambio del FEV1/FVC a 3,6 años",
    "cambio_fev1pp": "Cambio del FEV1 % a 3,6 años", "cambio_peso": "Cambio de peso, kg",
    "z_disanapsia": "Calibre central para su pulmón (z; más es más estrecho)",
    "z_enfisema": "Enfisema (z)", "z_via": "Vía aérea (z; más es menos árbol)",
}
BINARY = {
    "mujer": "Mujeres", "fuma": "Fuman ahora", "asma": "Asma", "enfisema_visual": "Enfisema visual",
    "deja_de_fumar": "Fumaba en la visita 1 y no en la 2", "obstruccion_v2": "Obstrucción en la visita 2",
}


def derive(t: pd.DataFrame, zscores: pd.DataFrame, panel: tuple[str, ...]) -> pd.DataFrame:
    t = t.copy()
    t["reversibilidad_pct"] = 100 * (t["FEV1postBDlitros_v1"] - t["FEV1preBDlitros_v1"]) / t["FEV1preBDlitros_v1"]
    t["cambio_cociente"] = t["fev1_fvc_post_v2"] - t["fev1_fvc_post_v1"]
    t["cambio_peso"] = t["peso_v2"] - t["peso_v1"]
    t["z_disanapsia"] = damage_score(zscores, ("via_disanapsia",)).reindex(t.index)
    t["z_enfisema"] = damage_score(zscores, (panel[0],)).reindex(t.index)
    t["z_via"] = damage_score(zscores, (panel[1],)).reindex(t.index)
    yes = lambda column, value: (t[column] == value).where(t[column].notna())  # noqa: E731
    t["mujer"], t["fuma"] = yes("sexo", "mujer"), yes("fuma", "fuma")
    t["asma"], t["enfisema_visual"] = yes("asma_num_v1", 1), yes("enfisema_visual", "sí")
    t["deja_de_fumar"] = ((t["actual_fuma_num_v1"] == 1) & (t["actual_fuma_num_v2"] == 0)).where(t["actual_fuma_num_v2"].notna())
    t["obstruccion_v2"] = (t["fev1_fvc_post_v2"] < 0.70).where(t["fev1_fvc_post_v2"].notna())
    return t


def compare(t: pd.DataFrame, flagged: pd.Series) -> list[dict]:
    """Cada variable en los discordantes y en sus iguales. Mann-Whitney para las numéricas, Fisher para las de sí o no."""
    rows = []
    for column, label in NUMERIC.items():
        a, b = t.loc[flagged, column].dropna(), t.loc[~flagged, column].dropna()
        if min(len(a), len(b)) < MIN_CELL:
            continue
        rows.append({"variable": label, "discordantes": round(float(a.median()), 3), "n_discordantes": len(a),
                     "iguales": round(float(b.median()), 3), "n_iguales": len(b), "p": float(stats.mannwhitneyu(a, b).pvalue)})
    for column, label in BINARY.items():
        a, b = t.loc[flagged, column].dropna().astype(bool), t.loc[~flagged, column].dropna().astype(bool)
        if min(len(a), len(b)) < MIN_CELL:
            continue
        table = [[int(a.sum()), int((~a).sum())], [int(b.sum()), int((~b).sum())]]
        rows.append({"variable": label, "discordantes": f"{100 * a.mean():.0f} %", "n_discordantes": len(a),
                     "iguales": f"{100 * b.mean():.0f} %", "n_iguales": len(b), "p": float(stats.fisher_exact(table).pvalue)})
    q = benjamini_hochberg(np.array([row["p"] for row in rows]))
    for row, value in zip(rows, q):
        row["q"] = float(value)
    return sorted(rows, key=lambda row: row["p"])


def relate(t: pd.DataFrame, target: str) -> list[dict]:
    """Spearman de `target` con cada variable, dentro del grupo `t`."""
    rows = []
    for column, label in (NUMERIC | BINARY).items():
        if column in ("z_enfisema", "z_via") and target == SCORE:
            continue  # la puntuación es su media
        x, y = pd.to_numeric(t[column], errors="coerce").astype(float), t[target]
        ok = x.notna() & y.notna()
        if ok.sum() < 12 or x[ok].nunique() < 2:
            continue
        result = stats.spearmanr(x[ok], y[ok])
        rows.append({"variable": label, "rho": round(float(result.statistic), 3), "p": float(result.pvalue), "n": int(ok.sum())})
    q = benjamini_hochberg(np.array([row["p"] for row in rows]))
    for row, value in zip(rows, q):
        row["q"] = float(value)
    return sorted(rows, key=lambda row: row["p"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    config = tomllib.loads(args.config.read_text())
    cohort = Path(config["cohorte"])
    panel = tuple(config["puntuacion"]["medidas"])
    threshold = json.loads((cohort / "modelo.json").read_text())["umbral_dano"]
    t = pd.read_csv(cohort / "subjects.csv", dtype={"subject_id": str}).set_index("subject_id")
    t = derive(t, pd.read_csv(cohort / "zscores.csv", dtype={"subject_id": str}), panel)
    case = t["caso_v1"] == 1
    high = t[SCORE] >= threshold
    controls, cases = t[~case], t[case]

    out = {
        "umbral": threshold,
        "controles_con_tc_como_epoc": {"n": int((high & ~case).sum()), "de": int((~case).sum()),
                                       "frente_a_los_demas_controles": compare(controls, high[~case])},
        "epoc_con_tc_como_control": {"n": int((~high & case).sum()), "de": int(case.sum()),
                                     "frente_a_los_demas_casos": compare(cases, ~high[case])},
        "dentro_de_los_controles": {"puntuacion": relate(controls, SCORE), "via_aerea": relate(controls, "z_via")},
        "dentro_de_los_casos": {"puntuacion": relate(cases, SCORE)},
    }
    (cohort / "discordantes.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    pd.set_option("display.width", 220, "display.max_colwidth", 60)
    for title, rows in (("Controles con la TC como la de la EPOC, frente a los demás controles", out["controles_con_tc_como_epoc"]["frente_a_los_demas_controles"]),
                        ("EPOC con la TC como la de los controles, frente a los demás casos", out["epoc_con_tc_como_control"]["frente_a_los_demas_casos"]),
                        ("Dentro de los controles: puntuación frente a cada variable", out["dentro_de_los_controles"]["puntuacion"]),
                        ("Dentro de los controles: vía aérea frente a cada variable", out["dentro_de_los_controles"]["via_aerea"]),
                        ("Dentro de los casos: puntuación frente a cada variable", out["dentro_de_los_casos"]["puntuacion"])):
        print(f"\n== {title} ==")
        print(pd.DataFrame(rows).round(3).to_string(index=False) if rows else "grupo de menos de 5 sujetos: sin detalle")
    print(f"\ncontroles por encima del umbral: {out['controles_con_tc_como_epoc']['n']} de {out['controles_con_tc_como_epoc']['de']}; "
          f"casos por debajo: {out['epoc_con_tc_como_control']['n']} de {out['epoc_con_tc_como_control']['de']}")


if __name__ == "__main__":
    main()
