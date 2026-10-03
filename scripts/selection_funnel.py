"""Por qué se quedan dos medidas: el embudo de selección, medida a medida.

Cada medida de TC tiene que pasar tres filtros, por orden:

1. Estable: acuerdo de 0,90 o más entre las dos reconstrucciones de la misma TC.
2. Asociada: relación con el FEV1/FVC con q < 0,05 (p corregida por todas las medidas).
3. Aporta algo nuevo: relación con el FEV1/FVC que se mantiene (p < 0,05) cuando se descuenta lo
   que ya dicen las medidas elegidas. Si no, es redundante: dice lo mismo que otra.

Las medidas se recorren de más a menos asociadas, y la que aporta se suma a las elegidas. Escribe
`embudo.json` en el directorio de la cohorte, con agregados.

    python scripts/selection_funnel.py mn5/cohorte.final.toml
"""

from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from maps.cohort import damage_score
from maps.measures import MEASURES

MIN_ICC = 0.90
ALPHA = 0.05


def partial_spearman(x: pd.Series, y: pd.Series, controls: pd.DataFrame) -> tuple[float, float]:
    """Spearman de x con y descontando `controls`: correlación de los residuos de los rangos."""
    data = pd.concat([x, y, controls], axis=1).dropna()
    ranks = data.rank().to_numpy()
    design = np.column_stack([np.ones(len(ranks)), ranks[:, 2:]])
    residual = [r - design @ np.linalg.lstsq(design, r, rcond=None)[0] for r in (ranks[:, 0], ranks[:, 1])]
    result = stats.pearsonr(*residual)
    return float(result.statistic), float(result.pvalue)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    cohort = Path(tomllib.loads(args.config.read_text())["cohorte"])
    subjects = pd.read_csv(cohort / "subjects.csv", dtype={"subject_id": str}).set_index("subject_id")
    zscores = pd.read_csv(cohort / "zscores.csv", dtype={"subject_id": str})
    checks = json.loads((cohort / "comprobaciones.json").read_text())
    by_measure = {row["medida"]: row for row in checks["por_medida"]}
    ratio = subjects["fev1_fvc_post_v1"]

    rows = []
    for measure, row in by_measure.items():
        association = row["fev1_fvc_post_v1"]
        rows.append({"medida": measure, "nombre": MEASURES[measure][0], "icc": row.get("icc_kernel"),
                     "rho": association.get("rho"), "p": association.get("p"), "q": association.get("q")})
    table = pd.DataFrame(rows).sort_values("p")
    z = pd.DataFrame({m: damage_score(zscores, (m,)).reindex(subjects.index) for m in table["medida"]})

    chosen, steps = [], []
    for _, row in table.iterrows():
        entry = row.to_dict()
        if row["icc"] is None or not row["icc"] >= MIN_ICC:
            entry["resultado"] = "fuera: inestable entre reconstrucciones"
        elif not row["q"] < ALPHA:
            entry["resultado"] = "fuera: no se asocia con el FEV1/FVC"
        else:
            if chosen:
                rho_partial, p_partial = partial_spearman(z[row["medida"]], ratio, z[chosen])
                entry |= {"rho_descontando": round(rho_partial, 3), "p_descontando": p_partial,
                          "parecido_a_las_elegidas": round(float(max(abs(stats.spearmanr(z[row["medida"]], z[c], nan_policy="omit").statistic)
                                                                     for c in chosen)), 3)}
                if p_partial >= ALPHA:
                    entry["resultado"] = "fuera: redundante, dice lo mismo que las elegidas"
                    steps.append(entry)
                    continue
            entry["resultado"] = "dentro"
            chosen.append(row["medida"])
        steps.append(entry)

    out = {"criterios": {"acuerdo_minimo": MIN_ICC, "q_maximo": ALPHA, "p_descontando_maximo": ALPHA},
           "medidas": len(steps), "estables": int(sum(s["icc"] is not None and s["icc"] >= MIN_ICC for s in steps)),
           "estables_y_asociadas": int(sum(s["resultado"] in ("dentro", "fuera: redundante, dice lo mismo que las elegidas") for s in steps)),
           "elegidas": chosen, "pasos": steps}
    (cohort / "embudo.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float))
    pd.set_option("display.width", 220)
    print(pd.DataFrame(steps)[[c for c in ("medida", "icc", "rho", "q", "rho_descontando", "p_descontando", "parecido_a_las_elegidas", "resultado")
                               if c in pd.DataFrame(steps)]].round(3).to_string(index=False))
    print({k: v for k, v in out.items() if k not in ("pasos",)})


if __name__ == "__main__":
    main()
