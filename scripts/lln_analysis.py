"""Obstrucción por el límite inferior de normalidad (LLN) en vez de por el 0,70 fijo.

El LLN del FEV1/FVC sale de las ecuaciones GLI-2012 (población caucásica), con
la edad, el sexo y la talla de cada persona. Es el criterio que usa la
definición de EPOC precoz (Martinez 2018). Las ecuaciones vienen del paquete
público `pyspiro`, que en MareNostrum se instala a mano porque no hay internet.

Responde a tres preguntas:

- ¿Cuántos de los controles de la cohorte (FEV1/FVC de 0,70 o más) están por
  debajo de su LLN, y cuántos de los 14 posibles pre-EPOC?
- ¿Cuántos casos tienen el cociente por debajo de 0,70 pero por encima de su LLN?
- Entre quienes no tienen obstrucción por el 0,70, ¿sigue la puntuación al z del
  cociente, que ya descuenta la edad, el sexo y la talla?

Además, la relación de la puntuación con los paquetes-año dentro de la EPOC,
descontando la edad y el tabaquismo activo. Escribe `lln.json`, con agregados.

    PYTHONPATH=src:vendor python scripts/lln_analysis.py mn5/cohorte.final.toml
"""

from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def lln_table(t: pd.DataFrame) -> pd.DataFrame:
    from pyspiro import GLI_2012

    equation = GLI_2012()
    equation.set_strategy("closest")
    data = pd.DataFrame({"sex": (t["sexo"] == "hombre").astype(int), "age": t["edat_round_v1"].astype(float),
                         "height": t["altura_v1"].astype(float), "ethnicity": 1,
                         "ratio": t["fev1_fvc_post_v1"].astype(float), "fev1": t["FEV1postBDlitros_v1"].astype(float)}, index=t.index)
    ratio = equation.compute(data, equation.Parameters.FEV1FVC, value_col="ratio", ethnicity_col="ethnicity", metrics=("lln", "zscore"))
    fev1 = equation.compute(data, equation.Parameters.FEV1, value_col="fev1", ethnicity_col="ethnicity", metrics=("percent",))
    return pd.DataFrame({"lln": ratio["lln"], "z_cociente": ratio["zscore"], "fev1_pct_gli": fev1["percent"]}, index=t.index)


def partial(x: pd.Series, y: pd.Series, controls: pd.DataFrame) -> dict:
    data = pd.concat([x, y, controls], axis=1).dropna()
    ranks = data.rank().to_numpy()
    design = np.column_stack([np.ones(len(ranks)), ranks[:, 2:]])
    residual = [r - design @ np.linalg.lstsq(design, r, rcond=None)[0] for r in (ranks[:, 0], ranks[:, 1])]
    result = stats.pearsonr(*residual)
    return {"rho": round(float(result.statistic), 3), "p": float(result.pvalue), "n": len(data)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    cohort = Path(tomllib.loads(args.config.read_text())["cohorte"])
    t = pd.read_csv(cohort / "subjects.csv", dtype={"subject_id": str}).set_index("subject_id")
    t = t.join(lln_table(t))
    below = t["fev1_fvc_post_v1"] < t["lln"]
    fixed = t["fev1_fvc_post_v1"] < 0.70
    flagged = (t["clase_maps"] == "pre-EPOC")
    controls = ~fixed

    # Comprobación: el FEV1 en % del predicho de la tabla es GLI; el nuestro tiene que coincidir.
    check = (t["fev1_pct_gli"] - t["FEV1pp_GLI_v1"]).abs()
    out = {
        "comprobacion_fev1_pct": {"diferencia_mediana": round(float(check.median()), 2), "diferencia_maxima": round(float(check.max()), 2)},
        "lln_del_cociente": {"mediana": round(float(t["lln"].median()), 3), "minimo": round(float(t["lln"].min()), 3),
                             "maximo": round(float(t["lln"].max()), 3)},
        "controles_por_debajo_del_lln": {"n": int((controls & below).sum()), "de": int(controls.sum())},
        "posibles_pre_epoc_por_debajo_del_lln": {"n": int((flagged & below).sum()), "de": int(flagged.sum())},
        "otros_controles_por_debajo_del_lln": {"n": int((controls & ~flagged & below).sum()), "de": int((controls & ~flagged).sum())},
        "epoc_por_0_70_pero_no_por_lln": {"n": int((fixed & ~below).sum()), "de": int(fixed.sum())},
    }
    table = [[int((flagged & below).sum()), int((flagged & ~below).sum())],
             [int((controls & ~flagged & below).sum()), int((controls & ~flagged & ~below).sum())]]
    out["fisher_p"] = float(stats.fisher_exact(table).pvalue)
    # El z del cociente ya descuenta edad, sexo y talla: ¿sigue la puntuación al cociente con esa escala?
    score = t["puntuacion_dano"]
    out["z_cociente_vs_puntuacion_sin_obstruccion"] = {"rho": round(float(stats.spearmanr(score[controls], t.loc[controls, "z_cociente"]).statistic), 3),
                                                       "p": float(stats.spearmanr(score[controls], t.loc[controls, "z_cociente"]).pvalue)}
    # Paquetes-año dentro de la EPOC, descontando edad y tabaquismo activo.
    cases = t[fixed]
    out["epoc_paquetes_ano"] = {
        "crudo": {"rho": round(float(stats.spearmanr(cases["puntuacion_dano"], cases["paquetes_año_v1"], nan_policy="omit").statistic), 3)},
        "descontando_edad_y_fumar_ahora": partial(cases["puntuacion_dano"], cases["paquetes_año_v1"],
                                                  pd.DataFrame({"edad": cases["edat_round_v1"], "fuma": (cases["fuma"] == "fuma").astype(float)})),
    }
    (cohort / "lln.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
