"""Lógica de la app MAPS: orientación de las z, puntuación de daño, carga y frase de lectura."""

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from maps_core import (  # noqa: E402
    LOBULOS,
    CohorteInvalida,
    Medida,
    cargar_cohorte,
    columnas_de_grupo,
    columnas_por_tipo,
    desviacion_por_lobulo,
    etiqueta_columna,
    fmt,
    frase_lectura,
    leer_medidas,
    orientar_z,
    percentil,
    puntuacion_dano,
    puntuaciones_cohorte,
    resumen_por_grupo,
    tabla_sujeto,
)

MEDIDAS = {
    "perc15": Medida("perc15", "Perc15", "HU", peor="menor"),
    "laa950": Medida("laa950", "%LAA-950", "%", peor="mayor"),
}


def _z_lobulos(valores: dict[str, tuple[float, float]]) -> pd.DataFrame:
    """z por lóbulo: {lóbulo: (perc15, laa950)}; los lóbulos no citados quedan en 0."""
    tabla = pd.DataFrame(0.0, index=pd.Index(LOBULOS, name="region"), columns=["perc15", "laa950"])
    for lobulo, fila in valores.items():
        tabla.loc[lobulo] = fila
    return tabla


def _escribir_cohorte(directorio: Path, *, sujetos: pd.DataFrame, z: pd.DataFrame | None = None,
                      medidas: dict | None = None) -> Path:
    directorio.mkdir(parents=True, exist_ok=True)
    sujetos.to_csv(directorio / "subjects.csv", index=False)
    if z is not None:
        z.to_csv(directorio / "zscores.csv", index=False)
    if medidas is not None:
        (directorio / "measures.json").write_text(json.dumps(medidas), encoding="utf-8")
    return directorio


# --- orientación y puntuación ------------------------------------------------


def test_a_lower_perc15_and_a_higher_laa_both_count_as_damage():
    z = _z_lobulos({"LSD": (-3.0, 2.0)})

    orientada = orientar_z(z, MEDIDAS)

    assert orientada.loc["LSD", "perc15"] == 3.0
    assert orientada.loc["LSD", "laa950"] == 2.0


def test_a_measure_without_a_damage_direction_is_left_out_of_the_orientation():
    z = _z_lobulos({"LSD": (-3.0, 2.0)}).assign(mld=9.0)
    medidas = leer_medidas(list(z.columns), {"perc15": {"peor": "menor"}, "laa950": {"peor": "mayor"}})

    orientada = orientar_z(z, medidas)

    assert list(orientada.columns) == ["perc15", "laa950"]


def test_damage_score_is_the_mean_oriented_z_over_lobes_and_measures():
    z = _z_lobulos({"LSD": (-4.0, 2.0), "LSI": (-2.0, 2.0)})  # 10 celdas, suma orientada 10

    assert puntuacion_dano(orientar_z(z, MEDIDAS)) == pytest.approx(1.0)


def test_opposite_deviations_cancel_in_the_score():
    """Un Perc15 más alto de lo esperado no es daño: compensa, no suma."""
    z = _z_lobulos({"LSD": (-2.0, 0.0), "LII": (2.0, 0.0)})

    assert puntuacion_dano(orientar_z(z, MEDIDAS)) == pytest.approx(0.0)


def test_missing_cells_do_not_dilute_the_score():
    z = _z_lobulos({lobulo: (-2.0, 2.0) for lobulo in LOBULOS})
    z.loc["LM"] = np.nan

    assert puntuacion_dano(orientar_z(z, MEDIDAS)) == pytest.approx(2.0)


def test_score_is_nan_without_any_z():
    vacio = pd.DataFrame(np.nan, index=list(LOBULOS), columns=["perc15"])

    assert math.isnan(puntuacion_dano(vacio))
    assert math.isnan(puntuacion_dano(vacio[[]]))


def test_lobe_tint_is_its_most_deviated_measure_or_the_chosen_one():
    orientada = orientar_z(_z_lobulos({"LSD": (-3.5, 1.0), "LII": (-0.5, 2.5)}), MEDIDAS)

    assert desviacion_por_lobulo(orientada)["LSD"] == 3.5
    assert desviacion_por_lobulo(orientada)["LII"] == 2.5
    assert desviacion_por_lobulo(orientada, "laa950")["LSD"] == 1.0


# --- carga --------------------------------------------------------------------


def test_cohort_scores_ignore_the_whole_lung_row_and_keep_subjects_without_ct(tmp_path):
    sujetos = pd.DataFrame({"subject_id": ["001", "002", "003"], "grupo": ["a", "b", "a"]})
    filas = [{"subject_id": "001", "region": lobulo, "perc15": -2.0} for lobulo in LOBULOS]
    filas.append({"subject_id": "001", "region": "pulmon", "perc15": -50.0})
    filas += [{"subject_id": "002", "region": lobulo, "perc15": 1.0} for lobulo in LOBULOS]
    cohorte = cargar_cohorte(_escribir_cohorte(
        tmp_path, sujetos=sujetos, z=pd.DataFrame(filas), medidas={"perc15": {"nombre": "Perc15", "peor": "menor"}}))

    puntuaciones = puntuaciones_cohorte(cohorte)

    assert list(puntuaciones.index) == ["001", "002", "003"]  # los ceros iniciales del identificador se conservan
    assert puntuaciones["001"] == pytest.approx(2.0)
    assert puntuaciones["002"] == pytest.approx(-1.0)
    assert math.isnan(puntuaciones["003"])


def test_only_subjects_csv_is_enough_to_open_the_cohort(tmp_path):
    sujetos = pd.DataFrame({"subject_id": ["a", "b"], "il6": [1.2, np.nan], "centro": ["X", "Y"]})

    cohorte = cargar_cohorte(_escribir_cohorte(tmp_path, sujetos=sujetos))

    assert cohorte.evidencia is None
    assert not cohorte.sintetica
    assert cohorte.medidas == {}
    assert puntuaciones_cohorte(cohorte).isna().all()
    assert tabla_sujeto(cohorte.z, "a").index.tolist() == list(LOBULOS)
    assert any("features.csv" in aviso for aviso in cohorte.avisos)
    assert any("zscores.csv" in aviso for aviso in cohorte.avisos)


def test_synthetic_marker_file_flags_the_cohort_and_carries_its_note(tmp_path):
    _escribir_cohorte(tmp_path, sujetos=pd.DataFrame({"subject_id": ["a"]}))
    assert not cargar_cohorte(tmp_path).sintetica

    (tmp_path / "SINTETICO").write_text("Ningún valor corresponde a un paciente.\nSegunda línea.\n", encoding="utf-8")
    cohorte = cargar_cohorte(tmp_path)
    assert cohorte.sintetica
    assert cohorte.nota_sintetica == "Ningún valor corresponde a un paciente."

    (tmp_path / "SINTETICO").write_text("", encoding="utf-8")
    assert cargar_cohorte(tmp_path).sintetica  # un fichero vacío también marca la cohorte


def test_measure_missing_from_measures_json_shows_with_its_column_name_and_stays_out_of_the_score(tmp_path):
    sujetos = pd.DataFrame({"subject_id": ["a"]})
    z = pd.DataFrame([{"subject_id": "a", "region": lobulo, "perc15": -1.0, "nueva": 8.0} for lobulo in LOBULOS])

    cohorte = cargar_cohorte(_escribir_cohorte(tmp_path, sujetos=sujetos, z=z, medidas={"perc15": {"peor": "menor"}}))

    assert cohorte.medidas["nueva"].nombre == "nueva"
    assert cohorte.medidas["nueva"].signo is None
    assert cohorte.medidas["perc15"].nombre == "perc15"  # sin `nombre` en el JSON, el de la columna
    assert puntuaciones_cohorte(cohorte)["a"] == pytest.approx(1.0)
    assert any("nueva" in aviso for aviso in cohorte.avisos)


def test_unknown_regions_and_non_numeric_cells_do_not_break_the_load(tmp_path):
    sujetos = pd.DataFrame({"subject_id": ["a"]})
    z = pd.DataFrame([
        {"subject_id": "a", "region": "lsd", "perc15": "-2.0"},
        {"subject_id": "a", "region": "Pulmón", "perc15": "-1.0"},
        {"subject_id": "a", "region": "LII", "perc15": "n/d"},
        {"subject_id": "a", "region": "bronquio", "perc15": "5"},
    ])

    cohorte = cargar_cohorte(_escribir_cohorte(tmp_path, sujetos=sujetos, z=z, medidas={"perc15": {"peor": "menor"}}))
    tabla = tabla_sujeto(cohorte.z, "a")

    assert tabla.loc["LSD", "perc15"] == -2.0
    assert tabla.loc["pulmon", "perc15"] == -1.0
    assert math.isnan(tabla.loc["LII", "perc15"])
    assert puntuaciones_cohorte(cohorte)["a"] == pytest.approx(2.0)
    assert any("región desconocida" in aviso for aviso in cohorte.avisos)


def test_a_directory_without_subjects_csv_is_rejected_with_the_file_name(tmp_path):
    with pytest.raises(CohorteInvalida, match="subjects.csv"):
        cargar_cohorte(tmp_path)
    with pytest.raises(CohorteInvalida, match="No existe"):
        cargar_cohorte(tmp_path / "no_esta")


def test_evidence_entries_without_their_numbers_are_dropped_not_fatal(tmp_path):
    _escribir_cohorte(tmp_path, sujetos=pd.DataFrame({"subject_id": ["a"]}))
    (tmp_path / "evidence.json").write_text(json.dumps({
        "objetivo": "DLCO baja", "metrica_nombre": "Spearman",
        "escalera": [
            {"escalon": "Clínica", "metrica": 0.2, "ic95_inf": 0.0, "ic95_sup": 0.4, "incremento": None, "p_permutacion": 0.04},
            {"escalon": "Roto", "metrica": "no", "ic95_inf": 0.0, "ic95_sup": 0.4},
        ],
        "controles_negativos": [
            {"variable": "Escáner", "auc": 0.52, "ic95_inf": 0.41, "ic95_sup": 0.63},
            {"variable": "Centro", "auc": 0.70, "ic95_inf": 0.58, "ic95_sup": 0.81},
            {"variable": "Sexo", "auc": 0.30, "ic95_inf": 0.21, "ic95_sup": 0.42},
        ],
    }), encoding="utf-8")

    evidencia = cargar_cohorte(tmp_path).evidencia

    assert [e.escalon for e in evidencia.escalera] == ["Clínica"]
    assert evidencia.escalera[0].incremento is None
    assert evidencia.azar == 0.0  # una correlación sin señal vale 0, un AUC vale 0,5
    assert [c.distingue for c in evidencia.controles_negativos] == [False, True, True]


def test_unreadable_evidence_json_leaves_a_notice_instead_of_failing(tmp_path):
    _escribir_cohorte(tmp_path, sujetos=pd.DataFrame({"subject_id": ["a"]}))
    (tmp_path / "evidence.json").write_text("{esto no es json", encoding="utf-8")

    cohorte = cargar_cohorte(tmp_path)

    assert cohorte.evidencia is None
    assert any("evidence.json" in aviso for aviso in cohorte.avisos)


# --- columnas clínicas de nombre desconocido -----------------------------------


def test_clinical_columns_are_typed_by_their_content_not_their_name():
    sujetos = pd.DataFrame({
        "il6": [1.2, 3.4, np.nan, 2.2],
        "centro": ["A", "B", "A", None],
        "exacerbador": [0, 1, 0, 1],  # dos valores: una categoría, no una magnitud
        "edad_texto": ["40", "45", "50", "38"],
        "id_muestra": ["m1", "m2", "m3", "m4"],
    })

    numericas, categoricas = columnas_por_tipo(sujetos)

    assert numericas == ["il6", "edad_texto"]
    assert categoricas == ["centro", "exacerbador", "id_muestra"]
    assert columnas_de_grupo(sujetos) == ["centro", "exacerbador", "id_muestra"]
    assert columnas_de_grupo(sujetos, max_niveles=3) == ["centro", "exacerbador"]


def test_the_grupo_column_is_offered_first():
    sujetos = pd.DataFrame({"sexo": ["h", "m", "h"], "Grupo": ["ref", "epoc", "ref"]})

    assert columnas_de_grupo(sujetos)[0] == "Grupo"


def test_an_unknown_clinical_column_keeps_its_own_name():
    assert etiqueta_columna("IL6_pg_mL") == ("IL6_pg_mL", "")
    assert etiqueta_columna("dlco_pct_pred") == ("DLCO", "% pred.")


def test_percentile_uses_only_present_values_and_mid_rank_for_ties():
    cohorte = pd.Series([1.0, 2.0, 2.0, 3.0, np.nan])

    assert percentil(2.0, cohorte) == pytest.approx(50.0)
    assert percentil(0.0, cohorte) == pytest.approx(0.0)
    assert percentil(float("nan"), cohorte) is None


def test_group_summary_orders_clinical_groups_and_gives_a_95_interval():
    puntuaciones = pd.Series({"a": 0.0, "b": 0.2, "c": 2.0, "d": 2.4, "e": 1.0, "f": np.nan})
    grupos = pd.Series({"a": "referencia", "b": "referencia", "c": "EPOC", "d": "EPOC", "e": "pre-COPD", "f": "EPOC"})

    resumen = resumen_por_grupo(puntuaciones, grupos).set_index("grupo")

    assert list(resumen.index) == ["referencia", "pre-COPD", "EPOC"]
    assert resumen.loc["EPOC", "n"] == 2  # el sujeto sin puntuación no cuenta
    assert resumen.loc["EPOC", "media"] == pytest.approx(2.2)
    # n = 2: media ± t(0,975; 1) · s / √2 = 2,2 ± 12,706 · 0,2
    assert resumen.loc["EPOC", "ic95_sup"] - resumen.loc["EPOC", "media"] == pytest.approx(12.706 * 0.2, rel=1e-3)
    assert math.isnan(resumen.loc["pre-COPD", "ic95_inf"])  # con un sujeto no hay intervalo


# --- texto --------------------------------------------------------------------


def test_reading_names_the_most_deviated_lobe_measure_and_side():
    z = _z_lobulos({"LSD": (-3.14, 1.0), "LSI": (-1.0, 2.2), "LII": (2.9, 0.0)})

    frase = frase_lectura(orientar_z(z, MEDIDAS), z, MEDIDAS)

    assert frase.startswith("El lóbulo superior derecho es el que más se desvía: Perc15 está 3,1 desviaciones estándar por debajo")


def test_reading_says_within_expected_when_no_lobe_reaches_two_sd_towards_damage():
    z = _z_lobulos({"LSD": (-1.9, 1.9), "LII": (4.0, -4.0)})  # LII se desvía mucho, pero en sentido contrario al daño

    frase = frase_lectura(orientar_z(z, MEDIDAS), z, MEDIDAS)

    assert frase.startswith("Ningún lóbulo se desvía hacia el daño")


def test_reading_reports_lobes_without_measures_and_the_absence_of_any():
    z = _z_lobulos({"LSD": (-2.5, 0.0)})
    z.loc["LM"] = np.nan
    vacio = z * np.nan

    assert frase_lectura(orientar_z(z, MEDIDAS), z, MEDIDAS).endswith("1 lóbulo no tiene medidas.")
    assert frase_lectura(orientar_z(vacio, MEDIDAS), vacio, MEDIDAS) == "Este paciente no tiene medidas de TC."


def test_reading_does_not_guess_when_no_measure_has_a_damage_direction():
    z = _z_lobulos({"LSD": (-3.0, 3.0)})
    sin_sentido = leer_medidas(list(z.columns), {})

    frase = frase_lectura(orientar_z(z, sin_sentido), z, sin_sentido)

    assert "No se puede dar una lectura" in frase


def test_numbers_use_decimal_comma_and_a_real_minus_sign():
    assert fmt(-2.84, 1) == "−2,8"
    assert fmt(2.84, 1, signo=True) == "+2,8"
    assert fmt(-0.04, 1, signo=True) == "0,0"
    assert fmt(float("nan")) == "sin dato"
