import numpy as np
import pandas as pd
import pytest

from maps.normative import cross_fitted_z, fit_normative

NOISE_SD = 10.0  # HU de variación entre sanos que las covariables no explican
COVARIATES = ["talla", "edad", "escaner"]


def _cohort(n: int, seed: int, *, shift: float = 0.0) -> pd.DataFrame:
    """Perc15 simulado: depende de talla, edad y escáner. `shift` es el daño, en HU."""
    rng = np.random.default_rng(seed)
    talla = rng.normal(170.0, 9.0, n)
    edad = rng.uniform(35.0, 50.0, n)
    escaner = rng.choice(["A", "B"], n)
    perc15 = -900.0 + 2.0 * (talla - 170.0) - 0.5 * (edad - 42.0) + 25.0 * (escaner == "B")
    perc15 = perc15 + rng.normal(0.0, NOISE_SD, n) + shift
    return pd.DataFrame({"talla": talla, "edad": edad, "escaner": escaner, "perc15": perc15})


def _wide_cohort(n: int, n_covariates: int, seed: int) -> pd.DataFrame:
    """Muchas covariables y una medida que no depende de ninguna."""
    rng = np.random.default_rng(seed)
    table = pd.DataFrame(rng.normal(size=(n, n_covariates)), columns=[f"c{i}" for i in range(n_covariates)])
    table["medida"] = rng.normal(size=n)
    return table


def test_a_measure_driven_by_height_gives_z_unrelated_to_height_in_new_subjects():
    rng = np.random.default_rng(0)
    talla = rng.normal(170.0, 9.0, 2300)
    table = pd.DataFrame({"talla": talla, "medida": 3.0 * talla + rng.normal(0.0, 5.0, 2300)})
    reference, new = table.iloc[:300], table.iloc[300:]

    z = fit_normative(reference, ["medida"], ["talla"]).z(new)["medida"]

    assert np.corrcoef(new["medida"], new["talla"])[0, 1] > 0.9
    assert abs(np.corrcoef(z, new["talla"])[0, 1]) < 0.06


def test_a_scanner_offset_does_not_reach_z():
    model = fit_normative(_cohort(400, seed=0), ["perc15"], COVARIATES, categorical=["escaner"])
    new = _cohort(2000, seed=1)

    z = model.z(new)["perc15"]

    assert new.groupby("escaner")["perc15"].mean().diff().iloc[-1] > 2 * NOISE_SD
    assert z.groupby(new["escaner"]).mean().abs().max() < 0.15


def test_a_group_shifted_two_residual_sd_scores_two():
    table = pd.concat(
        [_cohort(400, seed=0), _cohort(400, seed=1, shift=2 * NOISE_SD)], ignore_index=True
    )
    reference = pd.Series(np.arange(800) < 400)

    z = cross_fitted_z(table, reference, ["perc15"], COVARIATES, categorical=["escaner"])["perc15"]

    assert z[~reference].mean() == pytest.approx(2.0, abs=0.2)
    assert z[reference].mean() == pytest.approx(0.0, abs=0.15)


def test_cross_fitted_z_of_reference_subjects_is_standard_normal():
    table = _cohort(500, seed=2)
    reference = pd.Series(True, index=table.index)

    z = cross_fitted_z(table, reference, ["perc15"], COVARIATES, categorical=["escaner"])["perc15"]

    assert z.mean() == pytest.approx(0.0, abs=0.1)
    assert z.std() == pytest.approx(1.0, abs=0.1)


def test_cross_fitting_does_not_make_reference_subjects_look_tighter_than_unseen_ones():
    # 60 sujetos de referencia y 20 covariables: el ajuste absorbe parte del
    # ruido de los sujetos que ha visto. El resto de la tabla son sujetos de la
    # misma población que el modelo no ha visto, y sirven de vara de medir.
    table = _wide_cohort(2060, 20, seed=3)
    covariates = [c for c in table.columns if c != "medida"]
    reference = pd.Series(np.arange(len(table)) < 60)

    in_sample = fit_normative(table[reference], ["medida"], covariates).z(table)["medida"]
    cross_fitted = cross_fitted_z(table, reference, ["medida"], covariates, n_splits=None)["medida"]

    # quien no es de referencia se compara con el modelo de todas las referencias
    pd.testing.assert_series_equal(cross_fitted[~reference], in_sample[~reference])
    unseen_sd = cross_fitted[~reference].std()
    assert in_sample[reference].std() < 0.8 * unseen_sd
    assert cross_fitted[reference].std() > 0.85 * unseen_sd  # 60 valores: su dispersión baila un 10 %


def test_cross_fitted_z_is_reproducible_and_keeps_the_index():
    table = _cohort(120, seed=4).set_index(pd.Index([f"s{i:03d}" for i in range(120)]))
    reference = pd.Series(np.arange(120) % 3 > 0, index=table.index)

    first = cross_fitted_z(table, reference, ["perc15"], ["talla", "edad"], seed=7)
    second = cross_fitted_z(table, reference, ["perc15"], ["talla", "edad"], seed=7)

    pd.testing.assert_frame_equal(first, second)
    assert first.index.equals(table.index)
    assert list(first.columns) == ["perc15"]


def test_a_category_unseen_at_fit_time_gives_nan_only_for_those_rows():
    model = fit_normative(_cohort(200, seed=0), ["perc15"], COVARIATES, categorical=["escaner"])
    new = _cohort(6, seed=1)
    new.loc[[1, 4], "escaner"] = "C"

    z = model.z(new)["perc15"]

    assert z[[1, 4]].isna().all()
    assert z.drop([1, 4]).notna().all()


def test_missing_values_give_nan_for_that_measure_only():
    reference = _cohort(200, seed=0)
    reference["mld"] = reference["perc15"] + 60.0
    reference.loc[0, "mld"] = np.nan  # un hueco al ajustar no impide el ajuste
    model = fit_normative(reference, ["perc15", "mld"], COVARIATES, categorical=["escaner"])
    new = _cohort(5, seed=1)
    new["mld"] = new["perc15"] + 60.0
    new.loc[0, "talla"] = np.nan
    new.loc[1, "escaner"] = None
    new.loc[2, "mld"] = np.nan

    z = model.z(new)

    assert z.loc[[0, 1]].isna().all().all()
    assert np.isnan(z.loc[2, "mld"]) and np.isfinite(z.loc[2, "perc15"])
    assert z.loc[[3, 4]].notna().all().all()


def test_too_few_reference_subjects_are_rejected():
    table = _cohort(40, seed=0)
    table.loc[8:, "perc15"] = np.nan  # quedan 8 con la medida: justo 3 covariables + 5

    fit_normative(table, ["perc15"], COVARIATES, categorical=["escaner"])
    table.loc[7, "perc15"] = np.nan
    with pytest.raises(ValueError, match="'perc15' tiene 7 sujetos de referencia.*al menos 8"):
        fit_normative(table, ["perc15"], COVARIATES, categorical=["escaner"])
    with pytest.raises(ValueError, match="sujetos de referencia"):
        cross_fitted_z(_cohort(40, seed=0), pd.Series(np.arange(40) < 6), ["perc15"], ["talla", "edad"])


def test_every_scanner_costs_reference_subjects():
    # 3 escáneres son 2 columnas: con talla y edad hacen falta 4 + 5 sujetos, no 3 + 5
    table = _cohort(8, seed=0)
    table["escaner"] = ["A", "A", "A", "B", "B", "B", "C", "C"]

    with pytest.raises(ValueError, match="tiene 8 sujetos de referencia.*al menos 9"):
        fit_normative(table, ["perc15"], COVARIATES, categorical=["escaner"])


def test_a_categorical_covariate_only_needs_to_be_named_as_categorical():
    table = _cohort(100, seed=0)

    named_twice = fit_normative(table, ["perc15"], COVARIATES, categorical=["escaner"]).z(table)
    named_once = fit_normative(table, ["perc15"], ["talla", "edad"], categorical=["escaner"]).z(table)

    pd.testing.assert_frame_equal(named_once, named_twice)


def test_missing_and_mistyped_columns_are_named():
    table = _cohort(50, seed=0)

    with pytest.raises(ValueError, match="'imc'"):
        fit_normative(table, ["perc15"], ["talla", "imc"])
    with pytest.raises(ValueError, match="'laa950'"):
        fit_normative(table, ["laa950"], ["talla"])
    with pytest.raises(ValueError, match="'escaner'.*categorical"):
        fit_normative(table, ["perc15"], COVARIATES)  # texto como covariable numérica
    with pytest.raises(ValueError, match="'edad'"):
        fit_normative(table, ["perc15"], ["talla", "edad"]).z(table.drop(columns="edad"))


def test_the_expected_value_is_what_the_z_is_measured_from():
    rng = np.random.default_rng(3)
    n = 80
    table = pd.DataFrame({"talla": rng.normal(170, 9, n), "sexo": rng.choice(["H", "M"], n)})
    table["medida"] = 50 + 0.5 * (table["talla"] - 170) + 4 * (table["sexo"] == "H") + rng.normal(0, 2, n)
    model = fit_normative(table, ["medida"], ["talla"], ["sexo"])

    expected = model.expected(table)["medida"]

    # quien mide justo lo esperado tiene z cero, y lo esperado sigue a las covariables
    exact = table.assign(medida=expected)
    assert np.allclose(model.z(exact)["medida"], 0.0)
    tall_man = pd.DataFrame({"talla": [190.0], "sexo": ["H"]})
    short_woman = pd.DataFrame({"talla": [155.0], "sexo": ["M"]})
    assert model.expected(tall_man)["medida"][0] - model.expected(short_woman)["medida"][0] == pytest.approx(21.5, abs=2.0)


def test_leaving_one_out_gives_the_same_z_whatever_the_seed():
    # Con pocos sujetos de referencia, el reparto en grupos movía el z de cada uno y, con él, el umbral.
    table = _cohort(60, seed=4)
    reference = pd.Series(np.arange(len(table)) < 40)

    first = cross_fitted_z(table, reference, ["perc15"], COVARIATES, categorical=["escaner"], n_splits=None, seed=0)
    second = cross_fitted_z(table, reference, ["perc15"], COVARIATES, categorical=["escaner"], n_splits=None, seed=7)
    folded = cross_fitted_z(table, reference, ["perc15"], COVARIATES, categorical=["escaner"], n_splits=5, seed=7)

    pd.testing.assert_frame_equal(first, second)
    assert not np.allclose(first["perc15"][reference], folded["perc15"][reference])
    # cada sujeto de referencia se compara con el modelo de los otros 39: nadie con uno que lo vio
    without_first = fit_normative(table[reference].iloc[1:], ["perc15"], COVARIATES, ["escaner"]).z(table.iloc[[0]])
    assert first["perc15"].iloc[0] == pytest.approx(without_first["perc15"].iloc[0])


def test_z_of_new_subjects_has_unit_spread_even_with_few_reference_subjects():
    # 40 sujetos de referencia y 8 columnas de covariables, como en la cohorte del reto. Si la escala
    # sale de los residuos del ajuste, que son más pequeños que el error con un sujeto nuevo, el z de
    # los sujetos nuevos se infla un 20 o 30 %.
    spreads = []
    for seed in range(60):
        rng = np.random.default_rng(seed)
        n = 2040
        table = pd.DataFrame(rng.normal(size=(n, 3)), columns=["a", "b", "c"])
        table["sexo"] = rng.choice(["H", "M"], n)
        table["fuma"] = rng.choice(["sí", "no"], n)
        table["kvp"] = rng.choice([80, 100, 120], n)
        table["medida"] = table["a"] + 0.5 * (table["sexo"] == "H") + rng.normal(size=n)
        model = fit_normative(table.iloc[:40], ["medida"], ["a", "b", "c"], ["sexo", "fuma", "kvp"])
        spreads.append(model.z(table.iloc[40:])["medida"].std())

    assert np.mean(spreads) == pytest.approx(1.0, abs=0.08)
