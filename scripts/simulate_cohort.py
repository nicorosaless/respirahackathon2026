"""Cohorte SIMULADA para ensayar el análisis y la app antes de tener los datos reales.

Parte de las medidas reales de las TC públicas ya procesadas, las remuestrea y
les añade efectos conocidos: la talla y el kernel cambian la densidad, y un
daño latente baja la densidad, los vasos pequeños, las ramas de vía aérea y la
DLCO. Sirve para comprobar que el análisis recupera lo que se ha puesto, nunca
como resultado.

    python scripts/simulate_cohort.py outputs/cohorte --out outputs/simulada
    python scripts/score_cohort.py mn5/cohorte.simulada.toml
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from maps.measures import WHOLE_LUNG, measures_dictionary

# Cambio de cada medida por unidad de daño latente, en desviaciones de su ruido.
DAMAGE_EFFECT = {"perc15": -1.0, "mld": -0.8, "laa910": 1.0, "laa950": 0.8, "agrupamiento": 0.7,
                 "vasos_bv5_tbv": -0.8, "arterias_bv5_tbv": -0.8, "via_ramas": -0.7,
                 "via_ramas_por_litro": -0.7, "via_longitud_mm": -0.6, "via_disanapsia": -0.5}
NOISE = 0.06  # dispersión relativa entre sujetos sanos


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="cohorte real ya procesada, de la que se toman medidas y vistas previas")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--n", type=int, default=160)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)

    real = pd.read_csv(args.source / "features.csv", dtype={"subject_id": str})
    donors = real["subject_id"].unique()
    measures = [c for c in real.columns if c not in ("subject_id", "region")]
    scale = real.groupby("region")[measures].mean().abs() * NOISE
    scale[["perc15", "mld"]] = 10.0  # en HU, no relativo: -850 HU no es "850 de algo"

    group = rng.choice(["control", "pre-EPOC", "EPOC"], args.n, p=[0.6, 0.25, 0.15])
    # Un tercio de los controles tiene daño que la espirometría no ve: es a quien busca el reto.
    hidden = (group == "control") & (rng.random(args.n) < 0.33)
    damage = np.select([group == "EPOC", group == "pre-EPOC", hidden], [3.0, 1.8, 1.5], 0.0) + rng.normal(0, 0.3, args.n)
    damage = np.clip(damage, 0, None)
    sex = rng.choice(["H", "M"], args.n)
    height = np.where(sex == "H", 175, 162) + rng.normal(0, 6, args.n)
    kernel = rng.choice(["STANDARD", "BONE"], args.n, p=[0.7, 0.3])
    ids = [f"SIM-{i:03d}" for i in range(args.n)]

    rows, previews = [], args.out / "previews"
    previews.mkdir(parents=True, exist_ok=True)
    for i, subject in enumerate(ids):
        donor = rng.choice(donors)
        table = real[real["subject_id"] == donor].set_index("region")[measures].copy()
        for measure in measures:
            noise = scale[measure].reindex(table.index)
            effect = DAMAGE_EFFECT.get(measure, 0.0) * damage[i] * (1.5 if measure in DAMAGE_EFFECT else 0.0)
            table[measure] = table[measure] + noise * (rng.normal(0, 1, len(table)) + effect)
        # Confusores: un pulmón más alto es más grande y menos denso; el kernel duro baja Perc15.
        table["volumen_ml"] *= 1 + 0.012 * (height[i] - 168)
        table["perc15"] += -0.9 * (height[i] - 168) - 12 * (kernel[i] == "BONE")
        table["mld"] += -0.7 * (height[i] - 168) - 8 * (kernel[i] == "BONE")
        table.insert(0, "subject_id", subject)
        rows.append(table.reset_index())
        source_preview = args.source / "previews" / f"{donor}.npz"
        if source_preview.exists():
            shutil.copy(source_preview, previews / f"{subject}.npz")
    features = pd.concat(rows, ignore_index=True)[["subject_id", "region", *measures]]
    features.to_csv(args.out / "features.csv", index=False)

    age = rng.integers(35, 51, args.n)
    clinical = pd.DataFrame({
        "ID": ids, "grupo": group, "edad": age, "sexo": sex, "talla": height.round(1),
        "paquetes_ano": np.clip(rng.normal(22, 8, args.n) + 4 * damage, 10, None).round(1),
        "fev1_fvc": np.where(group == "EPOC", rng.normal(0.62, 0.04, args.n), rng.normal(0.78, 0.04, args.n)).round(3),
        "dlco_pct": (95 - 7 * damage + rng.normal(0, 8, args.n)).round(1),
        "cat": np.clip(6 + 2.5 * damage + rng.normal(0, 3, args.n), 0, 40).round(0),
        "eosinofilos": np.clip(rng.normal(200, 90, args.n), 20, None).round(0),
        "pcr": np.clip(rng.lognormal(0.5, 0.6, args.n) + 0.4 * damage, 0.1, None).round(2),
    })
    clinical.to_csv(args.out / "clinica.csv", index=False)
    pd.DataFrame({"subject_id": ids, "kernel": kernel, "fabricante": rng.choice(["GE", "SIEMENS"], args.n),
                  "grosor_mm": 1.25}).to_csv(args.out / "adquisicion.csv", index=False)
    (args.out / "measures.json").write_text(json.dumps(measures_dictionary(), indent=2, ensure_ascii=False))
    (args.out / "SINTETICO").write_text("Cohorte simulada a partir de TC públicas de LIDC-IDRI. No son pacientes.\n")
    whole = features[features["region"] == WHOLE_LUNG]
    print(f"{args.n} sujetos simulados en {args.out}: {dict(pd.Series(group).value_counts())}, "
          f"{int(hidden.sum())} controles con daño oculto; Perc15 medio {whole['perc15'].mean():.0f} HU")


if __name__ == "__main__":
    main()
