"""De las medidas de TC y la tabla clínica a las puntuaciones y la evidencia que enseña la app.

Lee un fichero de configuración (ver `mn5/cohorte.ejemplo.toml`) y escribe en el
directorio de la cohorte `subjects.csv`, `zscores.csv` y `evidence.json`. Si hay
regla de clasificación, guarda también el modelo (`modelo.json` y `modelo.pkl`)
con el que `scripts/predict.py` puntúa a sujetos nuevos.

    python scripts/score_cohort.py mn5/cohorte.toml
"""

from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

import pandas as pd

from maps.classify import classify, damage_threshold, explain
from maps.cohort import (DEFAULT_SCORE_MEASURES, damage_score, encode_block, fit_region_models, lung_volume,
                         query_columns, read_table, region_z, wide_block)
from maps.measures import measures_dictionary
from maps.persist import save_model
from maps.validation import evidence_ladder, nuisance_association

TC_PREFIX = "tc:"


def build_blocks(spec: dict, subjects: pd.DataFrame, zscores: pd.DataFrame) -> dict[str, pd.DataFrame]:
    blocks = {}
    for name, columns in spec.items():
        if isinstance(columns, str) and columns.startswith(TC_PREFIX):
            block = wide_block(zscores, [c.strip() for c in columns[len(TC_PREFIX):].split(",")])
        else:
            missing = [c for c in columns if c not in subjects]
            if missing:
                raise SystemExit(f"bloque '{name}': columnas que no están en la tabla de sujetos: {missing}")
            block = encode_block(subjects[columns])
        blocks[name] = block.reindex(subjects.index)
    return blocks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    config = tomllib.loads(args.config.read_text())
    cohort = Path(config["cohorte"])

    features = pd.read_csv(cohort / "features.csv", dtype={"subject_id": str})
    acquisition = pd.read_csv(cohort / "adquisicion.csv", dtype={"subject_id": str}).set_index("subject_id")
    clinical = read_table(config["clinica"]["tabla"]).rename(columns={config["clinica"]["id"]: "subject_id"})
    clinical["subject_id"] = clinical["subject_id"].astype(str).str.strip()
    if clinical["subject_id"].duplicated().any():
        raise SystemExit("la tabla clínica tiene identificadores repetidos: hay que dejar una fila por sujeto")
    clinical = clinical.set_index("subject_id")

    with_ct = lung_volume(features)
    acquisition = acquisition[[c for c in acquisition.columns if c not in clinical.columns]]
    subjects = clinical.join(acquisition, how="inner").join(with_ct, how="inner")
    print(f"{len(clinical)} sujetos en la tabla clínica, {len(with_ct)} con TC, {len(subjects)} con las dos")
    if subjects.empty:
        raise SystemExit("ningún identificador coincide entre la tabla clínica y las TC: revisa [clinica].id")

    normative = config["normativo"]
    reference = pd.Series(False, index=subjects.index)
    reference.loc[subjects.query(normative["referencia"]).index] = True
    print(f"referencia: {int(reference.sum())} sujetos ({normative['referencia']})")
    zscores = region_z(features[features["subject_id"].isin(subjects.index)], subjects, reference,
                       normative["covariables"], normative.get("categoricas", []))
    zscores.to_csv(cohort / "zscores.csv", index=False)

    score_measures = tuple(config.get("puntuacion", {}).get("medidas", DEFAULT_SCORE_MEASURES))
    subjects["puntuacion_dano"] = damage_score(zscores, score_measures)
    subjects["referencia"] = reference
    rule = config.get("clasificacion")
    if rule:
        # El umbral de daño se fija solo con los sujetos de `ajuste`; a los demás se les aplica tal cual.
        fit = subjects.query(rule["ajuste"]) if "ajuste" in rule else subjects
        threshold = damage_threshold(fit["puntuacion_dano"], fit[rule["caso"]] == 1)
        subjects["dano_tc"] = (subjects["puntuacion_dano"] >= threshold).map({True: "sí", False: "no"})
        abnormal = pd.Series(False, index=subjects.index)
        # El criterio funcional es opcional: sin él, la clase intermedia la decide solo la TC.
        if rule.get("funcional"):
            abnormal.loc[subjects.query(rule["funcional"]).index] = True
        subjects["clase_maps"] = classify(subjects[rule["cociente"]], subjects["puntuacion_dano"], abnormal, threshold)
        function_rule = rule.get("funcional_nombre", rule.get("funcional"))
        subjects["clase_motivo"] = explain(subjects[rule["cociente"]], subjects["puntuacion_dano"], abnormal, threshold, function_rule)
        # Lo que `predict.py` necesita para puntuar a sujetos nuevos sin reajustar nada. Estos modelos
        # se ajustan con toda la referencia; el z cruzado de arriba es solo para los sujetos de la cohorte.
        models = fit_region_models(features[features["subject_id"].isin(subjects.index)], subjects, reference,
                                   normative["covariables"], normative.get("categoricas", []))
        save_model(cohort, models,
                   {"medidas": list(score_measures), "covariables": normative["covariables"],
                    "categoricas": normative.get("categoricas", []), "umbral_dano": threshold,
                    "funcional": rule.get("funcional"), "funcional_nombre": function_rule, "cociente": rule["cociente"],
                    "columnas_funcional": query_columns(rule["funcional"], subjects.columns) if rule.get("funcional") else [],
                    "sujetos_de_ajuste": len(fit)})
        print(f"umbral de daño {threshold:.2f} fijado con {len(fit)} sujetos")
    # La app enseña las medidas que forman la puntuación: una por familia cabe en pantalla.
    dictionary = measures_dictionary()
    for measure in zscores.columns.drop(["subject_id", "region"]):
        dictionary.setdefault(measure, {"nombre": measure})["mostrar"] = measure in score_measures
    (cohort / "measures.json").write_text(json.dumps(dictionary, indent=2, ensure_ascii=False))
    subjects.reset_index().to_csv(cohort / "subjects.csv", index=False)

    evidence = config.get("evidencia")
    if evidence:
        task = evidence["tarea"]
        # `filtro` deja fuera de la evidencia a los sujetos de reserva, que solo se miran al final.
        used = subjects.query(evidence["filtro"]) if "filtro" in evidence else subjects
        blocks = {name: block.loc[used.index] for name, block in build_blocks(evidence["bloques"], subjects, zscores).items()}
        ladder = evidence_ladder(blocks, used[evidence["objetivo"]], task=task,
                                 n_permutations=evidence.get("permutaciones", 200))
        print(ladder.round(3).to_string(index=False))
        controls = []
        for variable in evidence.get("controles_negativos", []):
            controls.append({"variable": variable} | nuisance_association(used["puntuacion_dano"], used[variable]))
        # La app enseña cada escalón como lo que se añade al anterior.
        names = [name.replace("_", " ") for name in evidence["bloques"]]
        ladder["escalon"] = [names[0].capitalize() + " sola" if i == 0 else f"+ {name}" for i, name in enumerate(names)]
        out = {"objetivo": evidence.get("objetivo_nombre", evidence["objetivo"]),
               "metrica_nombre": "AUC" if task == "classification" else "Spearman",
               "escalera": json.loads(ladder.to_json(orient="records")),
               "controles_negativos": controls}
        (cohort / "evidence.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
        for control in controls:
            print(control)


if __name__ == "__main__":
    main()
