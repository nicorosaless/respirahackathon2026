import time

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from maps.molecular import associate, genomic_inflation, max_t_permutation


def _ids(n: int) -> pd.Index:
    return pd.Index([f"s{i:03d}" for i in range(n)], name="subject_id")


def _noise(n: int, n_features: int, seed: int, prefix: str = "cg") -> pd.DataFrame:
    """Rasgos moleculares sin relación con nada: normales independientes."""
    values = np.random.default_rng(seed).normal(size=(n, n_features))
    return pd.DataFrame(values, index=_ids(n), columns=[f"{prefix}{i:06d}" for i in range(n_features)])


def _subjects(n: int, seed: int) -> tuple[pd.Series, pd.DataFrame]:
    """Puntuación de daño que sube con la edad, y covariables con una categórica de tres niveles."""
    rng = np.random.default_rng(seed)
    age = rng.normal(60, 8, n)
    covariates = pd.DataFrame(
        {"edad": age, "sexo": rng.choice(["H", "M"], n), "escaner": rng.choice(["A", "B", "C"], n)}, index=_ids(n)
    )
    exposure = pd.Series(0.08 * (age - 60) + rng.normal(size=n), index=_ids(n), name="dano")
    return exposure, covariates


def _planted(n: int = 80, n_null: int = 5000, n_real: int = 20, effect: float = 0.8, seed: int = 0):
    """Rasgos nulos más `n_real` que suben `effect` por unidad de exposición (ruido de desviación 1)."""
    exposure, covariates = _subjects(n, seed)
    molecular = _noise(n, n_null, seed + 1)
    real = _noise(n, n_real, seed + 2, prefix="real").add(effect * exposure, axis=0)
    return pd.concat([molecular, real], axis=1), exposure, covariates, list(real.columns)


def test_planted_effects_are_recovered_and_null_features_are_not_flagged():
    molecular, exposure, covariates, real = _planted()

    result = associate(molecular, exposure, covariates)

    flagged = result.index[result["fdr"] < 0.05]
    assert len(flagged.intersection(real)) >= 18
    assert len(flagged.difference(real)) <= 2
    assert result.loc[real, "coef"].mean() == pytest.approx(0.8, abs=0.1)
    assert list(result.columns) == ["coef", "se", "t", "p", "fdr", "n"]
    assert result["p"].is_monotonic_increasing
    assert set(result.index) == set(molecular.columns)
    assert (result["n"] == 80).all()


@pytest.mark.parametrize(("n", "adjusted"), [(80, False), (30, True)])
def test_under_a_pure_null_p_values_are_uniform(n, adjusted):
    # Con 30 sujetos y cinco columnas de covariables, contar mal los grados de
    # libertad inflaría lambda en torno a un 25 %.
    exposure, covariates = _subjects(n, seed=3)

    result = associate(_noise(n, 20_000, seed=4), exposure, covariates if adjusted else None, min_subjects=10)

    assert genomic_inflation(result["p"]) == pytest.approx(1.0, abs=0.05)
    assert (result["p"] < 0.05).mean() == pytest.approx(0.05, abs=0.006)
    assert (result["fdr"] < 0.05).sum() <= 1


def test_genomic_inflation_reads_one_on_uniform_p_values_and_more_when_they_pile_up_near_zero():
    uniform = np.random.default_rng(0).uniform(size=50_000)

    assert genomic_inflation(uniform) == pytest.approx(1.0, abs=0.03)
    assert genomic_inflation(uniform**2) > 2.0
    assert genomic_inflation(np.append(uniform, [np.nan, np.nan])) == genomic_inflation(uniform)
    # p = 0,5 es la mediana bajo la hipótesis nula: lambda vale exactamente 1
    assert genomic_inflation(pd.Series([0.5, 0.5, 0.5])) == pytest.approx(1.0)
    with pytest.raises(ValueError, match="entre 0 y 1"):
        genomic_inflation([0.2, 1.5])
    with pytest.raises(ValueError, match="ningún p-valor"):
        genomic_inflation([np.nan])


def test_a_confounder_is_flagged_when_omitted_and_not_when_included():
    exposure, covariates = _subjects(80, seed=5)
    molecular = _noise(80, 300, seed=6)
    # un CpG que cambia con la edad, no con el daño; el daño también sube con la edad
    molecular["reloj"] = 0.25 * (covariates["edad"] - 60) + np.random.default_rng(7).normal(0, 0.5, 80)

    crude = associate(molecular, exposure)
    adjusted = associate(molecular, exposure, covariates)

    assert crude.loc["reloj", "fdr"] < 0.05
    assert adjusted.loc["reloj", "fdr"] > 0.05
    assert adjusted.loc["reloj", "p"] > 0.01


def _messy_inputs() -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    """Como llegan los datos de verdad: orden distinto, sujetos de más y de menos, huecos."""
    molecular, exposure, covariates, _ = _planted(n=60, n_null=4, n_real=2, seed=8)
    molecular.iloc[[3, 17, 18, 40], 1] = np.nan  # un rasgo con huecos
    exposure = exposure.sample(frac=1.0, random_state=0)  # otro orden
    exposure.iloc[2] = np.nan
    exposure = exposure.drop(exposure.index[5])
    exposure["sin_omicas"] = 1.0
    covariates.loc["s010", "edad"] = np.nan
    covariates.loc["s011", "escaner"] = None
    return molecular, exposure, covariates


def test_statistics_agree_with_statsmodels_including_missing_values_and_a_categorical_covariate():
    smf = pytest.importorskip("statsmodels.formula.api")
    from statsmodels.stats.multitest import multipletests

    molecular, exposure, covariates = _messy_inputs()

    result = associate(molecular, exposure, covariates)

    table = covariates.join(exposure.rename("dano"), how="inner")
    for feature in molecular.columns:
        rows = table.assign(y=molecular[feature]).dropna()
        fit = smf.ols("y ~ dano + edad + C(sexo) + C(escaner)", rows).fit()
        ours = result.loc[feature]
        assert ours["coef"] == pytest.approx(fit.params["dano"], rel=1e-8)
        assert ours["se"] == pytest.approx(fit.bse["dano"], rel=1e-8)
        assert ours["t"] == pytest.approx(fit.tvalues["dano"], rel=1e-8)
        assert ours["p"] == pytest.approx(fit.pvalues["dano"], rel=1e-7)
        assert ours["n"] == fit.nobs
    # 60 sujetos menos cuatro sin exposición o covariable; el rasgo con huecos pierde otros cuatro
    assert sorted(result["n"]) == [52, 56, 56, 56, 56, 56]
    assert result["fdr"].to_numpy() == pytest.approx(multipletests(result["p"], method="fdr_bh")[1])


def test_without_covariates_it_is_the_simple_regression_of_each_feature_on_the_exposure():
    molecular, exposure, _, _ = _planted(n=40, n_null=3, n_real=2, seed=9)

    result = associate(molecular, exposure)

    for feature in molecular.columns:
        fit = stats.linregress(exposure, molecular[feature])
        assert result.loc[feature, "coef"] == pytest.approx(fit.slope)
        assert result.loc[feature, "se"] == pytest.approx(fit.stderr)
        assert result.loc[feature, "p"] == pytest.approx(fit.pvalue)


def test_redundant_covariates_do_not_change_the_answer():
    molecular, exposure, covariates, _ = _planted(n=60, n_null=20, n_real=2, seed=10)
    redundant = covariates.assign(centro="único", edad_meses=12 * covariates["edad"])

    pd.testing.assert_frame_equal(associate(molecular, exposure, redundant), associate(molecular, exposure, covariates))


def test_features_that_cannot_be_tested_get_nan_and_stay_out_of_the_fdr():
    molecular, exposure, covariates, _ = _planted(n=60, n_null=200, n_real=5, seed=11)
    testable = associate(molecular, exposure, covariates)
    extra = molecular.copy()
    extra["constante"] = 0.37
    extra["casi_vacio"] = molecular.iloc[:, 0].where(np.arange(60) < 12)
    extra["vacio"] = np.nan
    extra["es_la_edad"] = covariates["edad"]  # las covariables lo explican entero

    result = associate(extra, exposure, covariates)

    untestable = ["constante", "casi_vacio", "vacio", "es_la_edad"]
    assert result.loc[untestable, ["coef", "se", "t", "p", "fdr"]].isna().all(axis=None)
    assert result.loc[untestable, "n"].to_dict() == {"constante": 60, "casi_vacio": 12, "vacio": 0, "es_la_edad": 60}
    assert list(result.index[-4:].sort_values()) == sorted(untestable)  # los NaN van al final
    pd.testing.assert_frame_equal(result.iloc[:-4], testable)


def test_many_features_with_missing_values_match_fitting_each_one_alone():
    molecular, exposure, covariates, _ = _planted(n=60, n_null=300, n_real=5, seed=12)
    holes = np.random.default_rng(13).uniform(size=molecular.shape) < 0.02
    molecular = molecular.mask(holes)

    result = associate(molecular, exposure, covariates)

    for feature in molecular.columns[::25]:
        alone = associate(molecular[[feature]], exposure, covariates)
        pd.testing.assert_series_equal(
            result.loc[feature, ["coef", "se", "t", "p", "n"]], alone.loc[feature, ["coef", "se", "t", "p", "n"]]
        )
    assert (result["n"] == (~holes).sum(axis=0)[molecular.columns.get_indexer(result.index)]).all()


def test_max_t_detects_a_planted_effect_and_stays_quiet_under_the_null():
    molecular, exposure, covariates, _ = _planted(n_null=2000, n_real=5)
    null = molecular.iloc[:, :2000]

    found = max_t_permutation(molecular, exposure, covariates, n_permutations=200, seed=0)
    quiet = max_t_permutation(null, exposure, covariates, n_permutations=200, seed=0)

    assert found["p"] == pytest.approx(1 / 201)  # ninguna permutación llega al máximo observado
    assert found["max_t"] > found["umbral_5"]
    assert quiet["p"] > 0.1
    assert quiet["max_t"] < quiet["umbral_5"]
    assert set(found) == {"max_t", "p", "umbral_5"}
    # el máximo observado es el de la tabla de asociación
    assert found["max_t"] == pytest.approx(associate(molecular, exposure, covariates)["t"].abs().max())


def test_max_t_is_reproducible_and_does_not_blame_the_exposure_for_what_a_covariate_explains():
    exposure, covariates = _subjects(80, seed=5)
    age = covariates["edad"]
    noise = _noise(80, 200, seed=6)
    molecular = noise.mul(0.5).add(0.25 * (age - 60), axis=0)  # todos los rasgos cambian con la edad

    crude = max_t_permutation(molecular, exposure, n_permutations=200, seed=1)
    adjusted = max_t_permutation(molecular, exposure, covariates, n_permutations=200, seed=1)

    assert crude["p"] < 0.02
    assert adjusted["p"] > 0.1
    assert adjusted == max_t_permutation(molecular, exposure, covariates, n_permutations=200, seed=1)


def test_max_t_rejects_a_true_null_about_one_time_in_twenty_with_few_subjects():
    # 25 sujetos, exposición ligada a la edad y rasgos que dependen de la edad:
    # si la permutación no respetara las covariables, rechazaría casi siempre.
    rejections = 0
    for seed in range(200):
        exposure, covariates = _subjects(25, seed)
        molecular = _noise(25, 40, seed + 1000).add(0.2 * (covariates["edad"] - 60), axis=0)
        out = max_t_permutation(molecular, exposure, covariates[["edad", "sexo"]], n_permutations=99, seed=seed)
        rejections += out["p"] <= 0.05

    assert 2 <= rejections <= 20  # 10 esperados


def test_max_t_tolerates_missing_values_by_imputing_the_feature_mean():
    molecular, exposure, covariates, _ = _planted(n_null=300, n_real=5)
    holes = np.random.default_rng(14).uniform(size=molecular.shape) < 0.02
    molecular = molecular.mask(holes)
    molecular["constante"] = 1.0
    molecular["vacio"] = np.nan

    found = max_t_permutation(molecular, exposure, covariates, n_permutations=100, seed=0)

    assert found["p"] == pytest.approx(1 / 101)
    assert np.isfinite(found["max_t"]) and np.isfinite(found["umbral_5"])


def test_two_hundred_thousand_features_take_seconds():
    exposure, covariates = _subjects(80, seed=0)
    molecular = _noise(80, 200_000, seed=1)

    start = time.perf_counter()
    result = associate(molecular, exposure, covariates)
    elapsed = time.perf_counter() - start

    assert len(result) == 200_000
    assert result["p"].notna().all()
    assert elapsed < 10.0


def test_invalid_inputs_are_rejected():
    molecular, exposure, covariates, _ = _planted(n=40, n_null=10, n_real=0)

    with pytest.raises(ValueError, match="quedan 12 sujetos.*al menos 20"):
        associate(molecular, exposure.iloc[:12], covariates)
    with pytest.raises(ValueError, match="quedan 0 sujetos"):
        associate(molecular, exposure.rename(lambda name: f"otro_{name}"), covariates)
    wide = pd.concat([covariates, _noise(40, 32, seed=2, prefix="cov")], axis=1)
    with pytest.raises(ValueError, match="quedan 40 sujetos.*al menos 43"):  # 38 columnas del modelo + 5
        associate(molecular, exposure, wide)
    with pytest.raises(ValueError, match="exposición es constante"):
        associate(molecular, exposure * 0 + 3.0, covariates)
    with pytest.raises(ValueError, match="exposición.*combinación lineal de las covariables"):
        associate(molecular, 2 * covariates["edad"] - 7, covariates)
    with pytest.raises(ValueError, match="exposición.*combinación lineal de las covariables"):
        associate(molecular, (covariates["sexo"] == "M").astype(float), covariates)
    with pytest.raises(ValueError, match="exposición.*numérica"):
        associate(molecular, covariates["sexo"])
    with pytest.raises(ValueError, match="'cg000003'.*numérica"):
        associate(molecular.assign(cg000003="alto"), exposure, covariates)
    with pytest.raises(ValueError, match="repetidos.*molecular"):
        associate(pd.concat([molecular, molecular.iloc[:1]]), exposure, covariates)
    with pytest.raises(ValueError, match="repetidos.*exposición"):
        associate(molecular, pd.concat([exposure, exposure.iloc[:1]]), covariates)
    with pytest.raises(ValueError, match="quedan 12 sujetos"):
        max_t_permutation(molecular, exposure.iloc[:12], covariates)
    with pytest.raises(ValueError, match="n_permutations"):
        max_t_permutation(molecular, exposure, covariates, n_permutations=0)
