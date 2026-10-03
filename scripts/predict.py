"""Aplica el modelo guardado de una cohorte a sujetos que no estaban en ella, sin reajustar nada.

Usa lo que `scripts/score_cohort.py` dejó en el directorio de la cohorte: los
modelos normativos por región, el umbral de daño y la regla de tres clases.
`--features` y `--adquisicion` son los que escribe `scripts/collect_cohort.py`
para los sujetos nuevos; `--clinica` es su tabla clínica, con los mismos nombres
de columna que la de la cohorte. Escribe una fila por sujeto en `--out` y, al
lado, la tabla larga de z en `<out>_zscores.csv`. Por pantalla solo da recuentos.

    python scripts/predict.py --modelo outputs/cohorte --features nuevos/features.csv \
        --adquisicion nuevos/adquisicion.csv --clinica nuevos/clinica.csv --id random_id \
        --out nuevos/predicciones.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from pandas.api.types import is_numeric_dtype

from maps.classify import CLASSES, classify, explain
from maps.cohort import apply_region_models, damage_score, lung_volume, read_table, seen_levels, worst_lobe
from maps.normative import NormativeModel
from maps.persist import DESCRIPTION_FILE, load_model

DESCRIPTION_KEYS = ("medidas", "covariables", "categoricas", "umbral_dano", "funcional", "cociente", "columnas_funcional")


def predict(models: dict[str, NormativeModel], description: dict, features: pd.DataFrame,
            subjects: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Predicción por sujeto y tabla larga de z. `subjects` va indexada por `subject_id`.

    Un sujeto al que el modelo no puede puntuar (le falta una covariable, o
    tiene una categoría que el ajuste no vio) se clasifica solo por la función.
    """
    measures, threshold = tuple(description["medidas"]), description["umbral_dano"]
    zscores = apply_region_models(models, features, subjects, description["covariables"], description["categoricas"])
    out = pd.DataFrame(index=subjects.index)
    out["puntuacion_dano"] = score = damage_score(zscores, measures).reindex(subjects.index)
    # sin puntuación no se puede afirmar que no haya daño: queda vacío en vez de "no"
    out["dano_tc"] = (score >= threshold).map({True: "sí", False: "no"}).where(score.notna())
    abnormal = pd.Series(False, index=subjects.index)
    if description["funcional"]:
        abnormal.loc[subjects.query(description["funcional"]).index] = True
    out["clase_maps"] = classify(subjects[description["cociente"]], score, abnormal, threshold)
    out["clase_motivo"] = explain(subjects[description["cociente"]], score, abnormal, threshold,
                                  description.get("funcional_nombre", description["funcional"]))
    return out.join(worst_lobe(zscores, measures)), zscores


def why_unscored(models: dict[str, NormativeModel], description: dict, features: pd.DataFrame,
                 subjects: pd.DataFrame, predictions: pd.DataFrame) -> pd.Series:
    """Por qué cada sujeto sin puntuación se quedó sin ella. Nombra columnas, nunca sus valores."""
    covariates, categorical = description["covariables"], description["categoricas"]
    seen = {name: seen_levels(models, name, description["medidas"]) for name in categorical}
    with_ct = set(features["subject_id"])
    reasons = {}
    for subject in predictions.index[predictions["puntuacion_dano"].isna()]:
        row = subjects.loc[subject]
        missing = [name for name in dict.fromkeys([*covariates, *categorical]) if pd.isna(row[name])]
        unseen = [name for name in categorical if pd.notna(row[name]) and row[name] not in seen[name]]
        if subject not in with_ct:
            reasons[subject] = "no tiene TC"
        elif missing:
            reasons[subject] = "falta " + ", ".join(missing)
        elif unseen:
            reasons[subject] = "valor de " + ", ".join(unseen) + " que el modelo no vio"
        else:
            reasons[subject] = "ninguna medida de la puntuación tiene z"
    return pd.Series(reasons, dtype="object")


def _require(table: pd.DataFrame, columns: list[str], where: object) -> None:
    for name in columns:
        if name not in table.columns:
            raise SystemExit(f"falta la columna '{name}' en {where}")


def read_subjects(args: argparse.Namespace, models: dict[str, NormativeModel],
                  description: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Lee los ficheros de los sujetos nuevos y los deja como los espera `predict`.

    Aquí se rechaza lo que haría fallar más adentro: columnas que faltan,
    identificadores repetidos y números que llegan como texto.
    """
    for path in (args.features, args.adquisicion, args.clinica):
        if not path.is_file():
            raise SystemExit(f"no existe el fichero {path}")
    features = pd.read_csv(args.features, dtype={"subject_id": str})
    fitted = dict.fromkeys(measure for model in models.values() for measure in model.fits)
    _require(features, ["subject_id", "region", "volumen_ml", *fitted], args.features)
    if features.empty:
        raise SystemExit(f"{args.features} no tiene ninguna fila")
    if features.duplicated(["subject_id", "region"]).any():
        raise SystemExit(f"{args.features} repite regiones de un mismo sujeto: hay que dejar una fila por región")
    acquisition = pd.read_csv(args.adquisicion, dtype={"subject_id": str})
    _require(acquisition, ["subject_id"], args.adquisicion)
    try:
        clinical = read_table(args.clinica)
    except ValueError as error:
        raise SystemExit(str(error)) from None
    _require(clinical, [args.id], args.clinica)
    clinical = clinical.rename(columns={args.id: "subject_id"})
    clinical["subject_id"] = clinical["subject_id"].astype(str).str.strip()
    for table, where in ((clinical, args.clinica), (acquisition, args.adquisicion)):
        if table["subject_id"].duplicated().any():
            raise SystemExit(f"{where} tiene identificadores repetidos: hay que dejar una fila por sujeto")
    clinical, acquisition = clinical.set_index("subject_id"), acquisition.set_index("subject_id")
    acquisition = acquisition[[c for c in acquisition.columns if c not in clinical.columns]]

    with_ct = pd.Index(pd.unique(features["subject_id"]), name="subject_id")
    both = clinical.index.intersection(with_ct)
    print(f"{len(clinical)} sujetos en la tabla clínica, {len(with_ct)} con TC, {len(both)} con las dos")
    if both.empty:
        raise SystemExit("ningún identificador coincide entre la tabla clínica y las TC: revisa --id")
    # Entra todo el que esté en la tabla clínica o tenga TC: a nadie se le deja sin fila en silencio.
    everyone = clinical.index.union(with_ct, sort=False)
    subjects = clinical.reindex(everyone).join(acquisition).join(lung_volume(features))

    numeric = [name for name in description["covariables"] if name not in description["categoricas"]]
    needed = [*numeric, *description["categoricas"], description["cociente"], *description["columnas_funcional"]]
    _require(subjects, needed, f"{args.clinica} y en {args.adquisicion}")
    for name in [*numeric, description["cociente"]]:
        if not is_numeric_dtype(subjects[name]):
            raise SystemExit(f"la columna '{name}' tiene que ser numérica y llega como texto")
    return features, subjects


def report(predictions: pd.DataFrame, reasons: pd.Series) -> None:
    """Recuentos de lo que se ha podido puntuar y clasificar. Ni identificadores ni valores clínicos."""
    scored = predictions["puntuacion_dano"].notna()
    print(f"puntuados: {int(scored.sum())} de {len(predictions)} sujetos")
    for reason, count in reasons.value_counts().items():
        print(f"  sin puntuación, {reason}: {count}")
    partial = scored & predictions.filter(like="_peor_z").isna().any(axis=1)
    if partial.any():
        print(f"  puntuados con menos medidas, porque alguna no tiene z: {int(partial.sum())}")
    classes = predictions["clase_maps"].value_counts()
    counts = [f"{name} {int(classes.get(name, 0))}" for name in CLASSES]
    print("clases: " + ", ".join(counts) + f", sin clase por falta de espirometría {int(predictions['clase_maps'].isna().sum())}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--modelo", type=Path, required=True, help="directorio de la cohorte donde score_cohort.py guardó el modelo")
    parser.add_argument("--features", type=Path, required=True, help="features.csv de los sujetos nuevos")
    parser.add_argument("--adquisicion", type=Path, required=True, help="adquisicion.csv de los sujetos nuevos")
    parser.add_argument("--clinica", type=Path, required=True, help="tabla clínica, con las columnas de la de la cohorte")
    parser.add_argument("--id", required=True, help="columna de la tabla clínica que coincide con subject_id")
    parser.add_argument("--out", type=Path, required=True, help="CSV de predicciones, una fila por sujeto")
    args = parser.parse_args(argv)

    try:
        models, description = load_model(args.modelo)
    except ValueError as error:
        raise SystemExit(str(error)) from None
    absent = [key for key in DESCRIPTION_KEYS if key not in description]
    if absent:
        raise SystemExit(f"a {args.modelo / DESCRIPTION_FILE} le falta {absent}: vuelve a ejecutar scripts/score_cohort.py")

    features, subjects = read_subjects(args, models, description)
    predictions, zscores = predict(models, description, features, subjects)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    zscores_path = args.out.with_name(f"{args.out.stem}_zscores.csv")
    predictions.reset_index().to_csv(args.out, index=False)
    zscores.to_csv(zscores_path, index=False)
    report(predictions, why_unscored(models, description, features, subjects, predictions))
    print(f"escritos {args.out} y {zscores_path}")


if __name__ == "__main__":
    main()
