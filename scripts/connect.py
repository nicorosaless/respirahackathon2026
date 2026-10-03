"""El paso "Connect": asocia la TC y la clínica con determinaciones moleculares.

Para cada exposición (la puntuación de daño, el z de una medida de TC o una
variable clínica) ajusta un modelo lineal por rasgo molecular, con covariables,
y controla la multiplicidad. Sirve igual para un biomarcador que para una matriz
de metilación con cientos de miles de CpG: la tabla molecular lleva un sujeto
por fila y un rasgo por columna.

Es el motor de asociaciones, no un flujo de metilación completo. La matriz tiene
que llegar ya depurada (control de calidad de sondas y muestras, M-values) y las
covariables propias del ensayo, como la composición celular y el lote, se pasan
en `covariables`. La corrección por comparaciones múltiples es por exposición.

Lee la sección `[molecular]` de la configuración de la cohorte y escribe en su
directorio `conexion.csv` (una fila por exposición y rasgo) y `conexion.json`
(el resumen por exposición). Por pantalla solo da agregados.

    python scripts/connect.py mn5/cohorte.early.toml
"""

from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

from maps.cohort import damage_score, read_table
from maps.molecular import associate, genomic_inflation, max_t_permutation

TC_PREFIX = "tc:"
MIN_FEATURES_LAMBDA = 100  # con menos rasgos, la mediana de los ji-cuadrado no dice nada
TOP = 10


def exposure_values(name: str, subjects: pd.DataFrame, zscores: pd.DataFrame) -> pd.Series:
    """Una exposición por sujeto. `tc:<medida>` es el z de esa medida, orientado para que más sea peor."""
    if name.startswith(TC_PREFIX):
        return damage_score(zscores, (name[len(TC_PREFIX):],)).reindex(subjects.index)
    if name not in subjects:
        raise SystemExit(f"la exposición '{name}' no está en subjects.csv")
    return subjects[name].astype("float64")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    config = tomllib.loads(args.config.read_text())
    cohort = Path(config["cohorte"])
    spec = config.get("molecular")
    if not spec:
        raise SystemExit(f"{args.config} no tiene sección [molecular]")

    subjects = pd.read_csv(cohort / "subjects.csv", dtype={"subject_id": str}).set_index("subject_id")
    zscores = pd.read_csv(cohort / "zscores.csv", dtype={"subject_id": str})
    if "filtro" in spec:
        subjects = subjects.query(spec["filtro"])

    molecular = read_table(spec["tabla"]).rename(columns={spec["id"]: "subject_id"})
    molecular["subject_id"] = molecular["subject_id"].astype(str).str.strip()
    molecular = molecular.set_index("subject_id")
    traits = spec.get("rasgos") or [c for c in molecular.columns if pd.api.types.is_numeric_dtype(molecular[c])]
    missing = [c for c in traits if c not in molecular]
    if missing:
        raise SystemExit(f"rasgos que no están en {spec['tabla']}: {missing}")
    molecular = molecular.loc[molecular.index.intersection(subjects.index), traits].astype("float64")
    if spec.get("logaritmo", False):
        # Para un biomarcador de concentración, como el FENO. No para metilación: los M-values son negativos.
        if (molecular <= 0).any().any():
            raise SystemExit("`logaritmo = true` pide rasgos positivos y la tabla tiene ceros o negativos: quítalo de [molecular]")
        molecular = np.log(molecular)
    # En desviaciones típicas de cada rasgo, para que los coeficientes se puedan comparar entre rasgos.
    molecular = (molecular - molecular.mean()) / molecular.std()
    subjects = subjects.loc[molecular.index]
    covariates = subjects[spec["covariables"]] if spec.get("covariables") else None
    print(f"{len(subjects)} sujetos, {len(traits)} rasgos moleculares, {len(spec['exposiciones'])} exposiciones")

    tables, summary = [], {}
    for name in spec["exposiciones"]:
        exposure = exposure_values(name, subjects, zscores)
        result = associate(molecular, exposure, covariates)
        result.insert(0, "exposicion", name)
        tables.append(result.rename_axis("rasgo").reset_index())
        tested = result["p"].notna()
        entry = {"rasgos_contrastados": int(tested.sum()), "rasgos_fdr_5": int((result["fdr"] < 0.05).sum()),
                 "p_minimo": float(result["p"].min())}
        if tested.sum() >= 2:
            entry["permutacion_p"] = max_t_permutation(molecular, exposure, covariates,
                                                       n_permutations=spec.get("permutaciones", 1000))["p"]
        if tested.sum() >= MIN_FEATURES_LAMBDA:
            entry["lambda"] = round(genomic_inflation(result["p"]), 3)
        summary[name] = entry
        print(f"\n== {name} ==")
        print(json.dumps(entry, ensure_ascii=False))
        print(result.drop(columns="exposicion").head(TOP).round(4).to_string())

    pd.concat(tables, ignore_index=True).to_csv(cohort / "conexion.csv", index=False)
    (cohort / "conexion.json").write_text(json.dumps(
        {"sujetos": len(subjects), "rasgos": len(traits), "covariables": spec.get("covariables", []),
         "exposiciones": summary}, indent=1, ensure_ascii=False))
    print(f"\nescritos {cohort / 'conexion.csv'} y {cohort / 'conexion.json'}")


if __name__ == "__main__":
    main()
