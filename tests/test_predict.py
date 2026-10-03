import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from maps import persist
from maps.classify import CONTROL, COPD, PRE_COPD
from maps.cohort import fit_region_models, lung_volume, query_columns, region_z_applied
from maps.measures import WHOLE_LUNG
from maps.persist import load_model, save_model

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from predict import main, predict, why_unscored  # noqa: E402

COVARIATES, CATEGORICAL = ["talla", "volumen_pulmon_ml"], ["sexo", "kvp"]
SCORE_MEASURES = ["haa", "via_ramas_por_litro"]
PREDICTION_COLUMNS = ["subject_id", "puntuacion_dano", "dano_tc", "clase_maps", "clase_motivo",
                      "haa_peor_lobulo", "haa_peor_z",
                      "via_ramas_por_litro_peor_lobulo", "via_ramas_por_litro_peor_z"]


def _cohort(n: int, seed: int, *, damaged: int = 0, noise: float = 1.0, prefix: str = "s"):
    """Tablas de una cohorte simulada, como las dejan `collect_cohort.py` y la tabla clínica.

    La alta atenuación de cada lóbulo depende de la talla y del kVp; las ramas de vía
    aérea, del volumen, y solo se miden en el pulmón entero. Los `damaged`
    últimos sujetos tienen daño de 5 dispersiones en las dos medidas y obstrucción.
    """
    rng = np.random.default_rng(seed)
    ids = [f"{prefix}{i:03d}" for i in range(n)]
    talla = rng.normal(170, 9, n)
    sexo = rng.choice(["hombre", "mujer"], n)
    kvp = rng.choice([100, 120], n)
    volume = rng.normal(5500, 700, n)
    hurt = np.arange(n) >= n - damaged
    rows = []
    for region, offset in (("LSD", 1.0), ("LID", 0.0), (WHOLE_LUNG, 0.5)):
        whole = region == WHOLE_LUNG
        laa = 3 + offset + 0.05 * (talla - 170) + 0.8 * (kvp == 100) + noise * rng.normal(0, 0.5, n) + 2.5 * hurt
        ramas = 30 - 0.002 * (volume - 5500) + noise * rng.normal(0, 2, n) - 10 * hurt
        rows.append(pd.DataFrame({"subject_id": ids, "region": region, "volumen_ml": volume * (1.0 if whole else 0.2),
                                  "haa": laa, "via_ramas_por_litro": ramas if whole else np.nan}))
    acquisition = pd.DataFrame({"subject_id": ids, "kvp": kvp})
    clinical = pd.DataFrame({"random_id": ids, "talla": talla, "sexo": sexo, "caso": hurt.astype(int),
                             "fev1_fvc": np.where(hurt, 0.60, 0.80), "fev1pp": np.where(hurt, 65.0, 95.0)})
    return pd.concat(rows, ignore_index=True), acquisition, clinical


def _subjects(features: pd.DataFrame, acquisition: pd.DataFrame, clinical: pd.DataFrame) -> pd.DataFrame:
    """Una fila por sujeto con la clínica, la adquisición y el volumen pulmonar."""
    table = clinical.rename(columns={"random_id": "subject_id"}).set_index("subject_id")
    return table.join(acquisition.set_index("subject_id")).join(lung_volume(features))


def _description(threshold: float = 1.5) -> dict:
    return {"medidas": SCORE_MEASURES, "covariables": COVARIATES, "categoricas": CATEGORICAL,
            "umbral_dano": threshold, "funcional": "fev1pp < 80", "cociente": "fev1_fvc",
            "columnas_funcional": ["fev1pp"]}


@pytest.fixture(scope="module")
def trained():
    """Cohorte de ajuste: 110 sujetos de referencia y 40 con daño, y sus modelos por región."""
    features, acquisition, clinical = _cohort(150, seed=0, damaged=40)
    subjects = _subjects(features, acquisition, clinical)
    reference = subjects["caso"] == 0
    return features, subjects, reference, fit_region_models(features, subjects, reference, COVARIATES, CATEGORICAL)


def _run(script: str, *args) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(ROOT / "src"), os.environ.get("PYTHONPATH", "")])}
    return subprocess.run([sys.executable, str(ROOT / "scripts" / script), *map(str, args)],
                          capture_output=True, text=True, env=env)


@pytest.fixture(scope="module")
def scored_cohort(tmp_path_factory) -> Path:
    """La misma cohorte pasada por `score_cohort.py`, que deja el modelo guardado en su directorio."""
    cohort = tmp_path_factory.mktemp("cohorte")
    features, acquisition, clinical = _cohort(150, seed=0, damaged=40)
    features.to_csv(cohort / "features.csv", index=False)
    acquisition.to_csv(cohort / "adquisicion.csv", index=False)
    clinical.to_csv(cohort / "clinica.csv", index=False)
    (cohort / "cohorte.toml").write_text(f"""
cohorte = "{cohort}"
[clinica]
tabla = "{cohort / 'clinica.csv'}"
id = "random_id"
[normativo]
referencia = "caso == 0"
covariables = ["talla", "volumen_pulmon_ml"]
categoricas = ["sexo", "kvp"]
[puntuacion]
medidas = ["haa", "via_ramas_por_litro"]
[clasificacion]
cociente = "fev1_fvc"
caso = "caso"
funcional = "fev1pp < 80"
""")
    result = _run("score_cohort.py", cohort / "cohorte.toml")
    assert result.returncode == 0, result.stderr
    return cohort


def _write_new_subjects(folder: Path, features: pd.DataFrame, acquisition: pd.DataFrame, clinical: pd.DataFrame) -> list[str]:
    """Escribe los tres ficheros de los sujetos nuevos y devuelve los argumentos que los nombran."""
    features.to_csv(folder / "features.csv", index=False)
    acquisition.to_csv(folder / "adquisicion.csv", index=False)
    clinical.to_csv(folder / "clinica.csv", index=False)
    return ["--features", str(folder / "features.csv"), "--adquisicion", str(folder / "adquisicion.csv"),
            "--clinica", str(folder / "clinica.csv"), "--id", "random_id", "--out", str(folder / "predicciones.csv")]


def test_region_z_applied_gives_one_row_per_subject_and_region_and_no_z_for_an_unseen_kvp():
    features, acquisition, clinical = _cohort(80, seed=3, damaged=20)
    subjects = _subjects(features, acquisition, clinical)
    new_features, new_acquisition, new_clinical = _cohort(6, seed=4, damaged=2, prefix="n")
    new_acquisition.loc[1, "kvp"] = 140  # un kVp que la referencia no tiene
    new_subjects = _subjects(new_features, new_acquisition, new_clinical)

    z = region_z_applied(features, new_features, subjects, new_subjects, subjects["caso"] == 0, COVARIATES, CATEGORICAL)

    assert list(z.columns) == ["subject_id", "region", "volumen_ml", "haa", "via_ramas_por_litro"]
    assert z["subject_id"].tolist() == [f"n{i:03d}" for i in range(6)] * 3
    assert z["region"].tolist() == ["LSD"] * 6 + ["LID"] * 6 + ["pulmon"] * 6
    haa = z["haa"].to_numpy().reshape(3, 6)
    assert np.isnan(haa[:, 1]).all() and np.isfinite(np.delete(haa, 1, axis=1)).all()
    assert (haa[:, 4:] > 3).all()  # los dos sujetos con daño plantado
    assert (np.abs(haa[:, [0, 2, 3]]) < 2.5).all()
    airways = z["via_ramas_por_litro"].to_numpy()
    assert np.isnan(airways[:12]).all()  # solo se mide en el pulmón entero
    assert (airways[16:] < -3).all()


def test_new_subjects_get_the_z_of_the_frozen_model_and_planted_damage_stands_out(trained):
    features, subjects, reference, models = trained
    new_features, new_acquisition, new_clinical = _cohort(60, seed=1, damaged=20, prefix="n")
    new_subjects = _subjects(new_features, new_acquisition, new_clinical)

    predictions, zscores = predict(models, _description(), new_features, new_subjects)

    expected = region_z_applied(features, new_features, subjects, new_subjects, reference, COVARIATES, CATEGORICAL)
    pd.testing.assert_frame_equal(zscores, expected)
    score, hurt = predictions["puntuacion_dano"], new_subjects["caso"] == 1
    assert score[hurt].min() > score[~hurt].max()
    assert score[hurt].mean() > 3.0
    assert abs(score[~hurt].mean()) < 0.5


def test_the_worst_lobe_is_the_one_where_the_damage_is(trained):
    *_, models = trained
    features, acquisition, clinical = _cohort(3, seed=6, noise=0.0, prefix="n")
    features.loc[(features["subject_id"] == "n001") & (features["region"] == "LID"), "haa"] += 2.5

    predictions, _ = predict(models, _description(), features, _subjects(features, acquisition, clinical))

    assert predictions.loc["n001", "haa_peor_lobulo"] == "LID"
    assert predictions.loc["n001", "haa_peor_z"] > 3.0
    # las ramas solo se miden en el pulmón entero: no hay lóbulo que nombrar
    assert predictions.loc["n001", "via_ramas_por_litro_peor_lobulo"] == WHOLE_LUNG


def test_a_saved_model_predicts_exactly_like_the_one_in_memory(trained, tmp_path):
    *_, models = trained
    new_features, new_acquisition, new_clinical = _cohort(20, seed=1, damaged=5, prefix="n")
    new_subjects = _subjects(new_features, new_acquisition, new_clinical)

    save_model(tmp_path, models, _description())
    loaded_models, loaded_description = load_model(tmp_path)

    assert loaded_description == _description()
    in_memory = predict(models, _description(), new_features, new_subjects)
    from_disk = predict(loaded_models, loaded_description, new_features, new_subjects)
    for expected, loaded in zip(in_memory, from_disk):
        pd.testing.assert_frame_equal(loaded, expected, check_exact=True)


def test_a_model_saved_with_another_format_version_is_rejected_with_a_clear_message(trained, tmp_path, monkeypatch):
    *_, models = trained
    with monkeypatch.context() as patch:
        patch.setattr(persist, "FORMAT", persist.FORMAT + 1)
        save_model(tmp_path, models, _description())

    with pytest.raises(ValueError, match=f"formato {persist.FORMAT + 1}.*formato {persist.FORMAT}"):
        load_model(tmp_path)


def test_a_file_that_is_not_a_saved_model_is_rejected_with_a_clear_message(trained, tmp_path):
    *_, models = trained
    with pytest.raises(ValueError, match="no hay modelo guardado"):
        load_model(tmp_path)

    save_model(tmp_path, models, _description())
    (tmp_path / "modelo.pkl").write_bytes(b"esto no lo ha escrito save_model")
    with pytest.raises(ValueError, match="no es un modelo guardado"):
        load_model(tmp_path)


def test_a_subject_the_model_cannot_place_gets_no_score_but_still_a_class(trained):
    *_, models = trained
    new_features, new_acquisition, new_clinical = _cohort(10, seed=2, prefix="n")
    untouched, _ = predict(models, _description(), new_features, _subjects(new_features, new_acquisition, new_clinical))
    new_acquisition.loc[0, "kvp"] = 140  # un kVp que el modelo no vio
    new_clinical.loc[0, "fev1pp"] = 70.0
    new_clinical.loc[1, "talla"] = np.nan
    new_subjects = _subjects(new_features, new_acquisition, new_clinical)

    predictions, zscores = predict(models, _description(), new_features, new_subjects)

    affected = ["n000", "n001"]
    assert zscores.loc[zscores["subject_id"].isin(affected), SCORE_MEASURES].isna().all().all()
    assert predictions.loc[affected, "puntuacion_dano"].isna().all()
    assert predictions.loc[affected, "dano_tc"].isna().all()  # sin puntuación no se afirma que no haya daño
    assert predictions.loc[affected, "clase_maps"].tolist() == [PRE_COPD, CONTROL]
    pd.testing.assert_frame_equal(predictions.drop(index=affected), untouched.drop(index=affected), check_exact=True)
    reasons = why_unscored(models, _description(), new_features, new_subjects, predictions)
    assert list(reasons.index) == affected
    assert "kvp" in reasons["n000"] and "140" not in reasons["n000"]
    assert "talla" in reasons["n001"]


def test_classes_follow_the_three_line_rule(trained):
    *_, models = trained
    features, acquisition, clinical = _cohort(6, seed=5, noise=0.0, prefix="n")
    # obstrucción sin daño, obstrucción con daño, daño solo, FEV1 bajo solo, nada, sin espirometría
    clinical["fev1_fvc"] = [0.60, 0.60, 0.80, 0.80, 0.80, np.nan]
    clinical["fev1pp"] = [95.0, 95.0, 95.0, 70.0, 95.0, 95.0]
    features.loc[features["subject_id"].isin(["n001", "n002"]), "haa"] += 2.5

    predictions, _ = predict(models, _description(threshold=1.5), features, _subjects(features, acquisition, clinical))

    assert (predictions["puntuacion_dano"] >= 1.5).tolist() == [False, True, True, False, False, False]
    assert predictions["dano_tc"].tolist() == ["no", "sí", "sí", "no", "no", "no"]
    assert predictions["clase_maps"].tolist()[:5] == [COPD, COPD, PRE_COPD, PRE_COPD, CONTROL]
    assert pd.isna(predictions["clase_maps"].iloc[5])


def test_the_columns_of_a_rule_are_found_and_quoted_text_is_not_a_column():
    columns = ["sexo", "FEV1pp_GLI_v1", "FEV1 %", "particion", "desarrollo"]

    assert query_columns("FEV1pp_GLI_v1 < 80", columns) == ["FEV1pp_GLI_v1"]
    assert query_columns("`FEV1 %` < 80 and particion == 'desarrollo'", columns) == ["FEV1 %", "particion"]


def test_the_saved_model_reproduces_the_cohort_scores_outside_the_reference(scored_cohort):
    subjects = pd.read_csv(scored_cohort / "subjects.csv", dtype={"subject_id": str}).set_index("subject_id")
    features = pd.read_csv(scored_cohort / "features.csv", dtype={"subject_id": str})
    models, description = load_model(scored_cohort)

    predictions, _ = predict(models, description, features, subjects)

    assert description["cociente"] == "fev1_fvc"
    assert description["columnas_funcional"] == ["fev1pp"]
    reference = subjects["referencia"]
    np.testing.assert_allclose(predictions.loc[~reference, "puntuacion_dano"], subjects.loc[~reference, "puntuacion_dano"])
    assert predictions.loc[~reference, "clase_maps"].tolist() == subjects.loc[~reference, "clase_maps"].tolist()
    # a los de referencia la cohorte les dio el z de un modelo que no los vio; el guardado sí los vio
    assert not np.allclose(predictions.loc[reference, "puntuacion_dano"], subjects.loc[reference, "puntuacion_dano"])


def test_the_command_writes_one_row_per_new_subject_and_prints_only_counts(scored_cohort, tmp_path):
    features, acquisition, clinical = _cohort(15, seed=7, damaged=5, prefix="n")
    acquisition.loc[0, "kvp"] = 140

    result = _run("predict.py", "--modelo", scored_cohort, *_write_new_subjects(tmp_path, features, acquisition, clinical))

    assert result.returncode == 0, result.stderr
    predictions = pd.read_csv(tmp_path / "predicciones.csv", dtype={"subject_id": str})
    assert list(predictions.columns) == PREDICTION_COLUMNS
    assert predictions["subject_id"].tolist() == clinical["random_id"].tolist()
    by_subject = predictions.set_index("subject_id")
    assert by_subject["puntuacion_dano"].isna().tolist() == [True] + [False] * 14
    assert by_subject["clase_maps"].tolist()[-5:] == [COPD] * 5
    assert by_subject.loc["n000", "clase_maps"] == CONTROL
    zscores = pd.read_csv(tmp_path / "predicciones_zscores.csv", dtype={"subject_id": str})
    assert list(zscores.columns) == ["subject_id", "region", "volumen_ml", *SCORE_MEASURES]
    assert len(zscores) == 15 * 3
    assert "14 de 15" in result.stdout
    assert "kvp" in result.stdout  # el motivo, en agregado
    assert "n0" not in result.stdout and "140" not in result.stdout  # ni identificadores ni valores


def test_the_command_stops_with_the_name_of_a_missing_clinical_column(scored_cohort, tmp_path):
    features, acquisition, clinical = _cohort(15, seed=7, damaged=5, prefix="n")

    arguments = _write_new_subjects(tmp_path, features, acquisition, clinical.drop(columns="fev1pp"))
    result = _run("predict.py", "--modelo", scored_cohort, *arguments)

    assert result.returncode != 0
    assert "fev1pp" in result.stderr
    assert "Traceback" not in result.stderr
    assert not (tmp_path / "predicciones.csv").exists()


@pytest.mark.parametrize("table, column", [("clinical", "random_id"), ("clinical", "fev1_fvc"), ("clinical", "talla"),
                                           ("acquisition", "kvp"), ("features", "haa")])
def test_every_column_the_model_needs_is_asked_for_by_name(scored_cohort, tmp_path, table, column):
    tables = dict(zip(("features", "acquisition", "clinical"), _cohort(15, seed=7, damaged=5, prefix="n")))
    tables[table] = tables[table].drop(columns=column)

    with pytest.raises(SystemExit, match=f"'{column}'"):
        main(["--modelo", str(scored_cohort), *_write_new_subjects(tmp_path, **tables)])
