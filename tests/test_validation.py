import numpy as np
import pandas as pd
import pytest

from maps.validation import evidence_ladder, nuisance_association

# Ajustes pequeños para que el archivo corra en segundos; los de producción son los de por defecto.
FAST = {"n_repeats": 2, "n_bootstrap": 300, "n_permutations": 0}


def _noise(n: int, n_columns: int, seed: int, prefix: str) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(rng.normal(size=(n, n_columns)), columns=[f"{prefix}{i}" for i in range(n_columns)])


def _two_sources(n: int, seed: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """Dos bloques con señal independiente y el daño latente que explican entre los dos."""
    clinic, imaging = _noise(n, 3, seed, "clinica"), _noise(n, 4, seed + 1, "imagen")
    noise = np.random.default_rng(seed + 2).normal(size=n)
    latent = clinic["clinica0"] + 1.5 * imaging["imagen0"] + 0.7 * noise
    return clinic, imaging, latent


def test_rungs_accumulate_blocks_in_order():
    clinic, imaging, latent = _two_sources(80, seed=0)

    ladder = evidence_ladder({"clínica": clinic, "imagen": imaging}, latent, task="regression", **FAST)

    assert list(ladder["escalon"]) == ["clínica", "clínica+imagen"]
    assert list(ladder["n_variables"]) == [3, 7]
    assert list(ladder.columns) == [
        "escalon", "n_variables", "metrica", "ic95_inf", "ic95_sup",
        "incremento", "incremento_ic95_inf", "incremento_ic95_sup", "p_permutacion",
    ]  # fmt: skip
    assert ladder.loc[0, ["incremento", "incremento_ic95_inf", "incremento_ic95_sup"]].isna().all()


@pytest.mark.parametrize("task", ["classification", "regression"])
def test_a_noise_block_on_top_of_an_informative_one_adds_nothing(task):
    clinic, _, latent = _two_sources(150, seed=0)
    latent = latent - 1.5 * _two_sources(150, seed=0)[1]["imagen0"]  # solo la clínica informa
    y = latent > latent.median() if task == "classification" else latent

    ladder = evidence_ladder({"clínica": clinic, "ruido": _noise(150, 6, 9, "ruido")}, y, task=task, **FAST)

    informative, with_noise = ladder.iloc[0], ladder.iloc[1]
    assert informative["ic95_inf"] > (0.5 if task == "classification" else 0.0)
    assert with_noise["incremento_ic95_inf"] < 0.0 < with_noise["incremento_ic95_sup"]
    assert abs(with_noise["incremento"]) < 0.05


@pytest.mark.parametrize("task", ["classification", "regression"])
def test_an_informative_second_block_adds_a_positive_increment(task):
    clinic, imaging, latent = _two_sources(150, seed=0)
    y = latent > latent.median() if task == "classification" else latent

    ladder = evidence_ladder({"clínica": clinic, "imagen": imaging}, y, task=task, **FAST)

    added = ladder.iloc[1]
    assert added["incremento"] == pytest.approx(added["metrica"] - ladder.loc[0, "metrica"])
    assert added["incremento"] > 0.1
    assert added["incremento_ic95_inf"] > 0.0


@pytest.mark.parametrize("task", ["classification", "regression"])
def test_a_target_unrelated_to_every_block_stays_at_chance(task):
    clinic, imaging, _ = _two_sources(100, seed=0)
    unrelated = pd.Series(np.random.default_rng(5).normal(size=100))
    y = unrelated > unrelated.median() if task == "classification" else unrelated
    chance = 0.5 if task == "classification" else 0.0

    ladder = evidence_ladder(
        {"clínica": clinic, "imagen": imaging}, y, task=task, n_repeats=3, n_bootstrap=300, n_permutations=20
    )

    assert (ladder["p_permutacion"] > 0.1).all()
    assert (ladder["ic95_inf"] < chance).all() and (ladder["ic95_sup"] > chance).all()


def test_a_real_association_gets_the_smallest_possible_permutation_p():
    clinic, imaging, latent = _two_sources(100, seed=0)

    ladder = evidence_ladder(
        {"imagen": imaging}, latent, task="regression", n_repeats=2, n_bootstrap=100, n_permutations=30
    )

    assert ladder.loc[0, "p_permutacion"] == pytest.approx(1 / 31)


@pytest.mark.parametrize("task", ["classification", "regression"])
def test_a_wide_noise_block_is_not_optimistic(task):
    # 10 veces más columnas que sujetos: cualquier ajuste hecho fuera del fold de
    # entrenamiento (selección, escalado, elección de regularización) daría aquí
    # una métrica por encima del azar.
    n = 60
    unrelated = pd.Series(np.random.default_rng(1).normal(size=n))
    y = unrelated > unrelated.median() if task == "classification" else unrelated
    chance = 0.5 if task == "classification" else 0.0

    ladder = evidence_ladder({"ómicas": _noise(n, 10 * n, 2, "gen")}, y, task=task, **FAST)

    row = ladder.iloc[0]
    assert row["n_variables"] == 10 * n
    assert row["metrica"] < chance + 0.15
    assert row["ic95_inf"] < chance


def test_a_wide_noise_block_does_not_bury_a_real_signal():
    clinic, _, latent = _two_sources(60, seed=0)
    latent = clinic["clinica0"] + 0.5 * np.random.default_rng(3).normal(size=60)

    ladder = evidence_ladder(
        {"clínica": clinic, "ómicas": _noise(60, 600, 2, "gen")}, latent, task="regression", **FAST
    )

    assert ladder.loc[0, "metrica"] > 0.6
    assert ladder.loc[1, "metrica"] > 0.3
    assert ladder.loc[1, "incremento"] < 0.0  # el ruido cuesta, y la escalera lo dice


def test_subjects_without_target_are_dropped_and_missing_features_are_imputed():
    clinic, imaging, latent = _two_sources(90, seed=0)
    blocks = {"clínica": clinic.copy(), "imagen": imaging}
    blocks["clínica"].iloc[::7, 1] = np.nan
    y = latent.copy()
    y.iloc[:10] = np.nan

    ladder = evidence_ladder(blocks, y, task="regression", **FAST)
    without_them = evidence_ladder({k: b.iloc[10:] for k, b in blocks.items()}, y.iloc[10:], task="regression", **FAST)

    pd.testing.assert_frame_equal(ladder, without_them)
    assert ladder["metrica"].notna().all()


def test_invalid_inputs_are_rejected():
    clinic, imaging, latent = _two_sources(40, seed=0)
    binary = latent > latent.median()

    with pytest.raises(ValueError, match="'imagen'.*índice"):
        evidence_ladder({"clínica": clinic, "imagen": imaging.iloc[1:]}, latent, task="regression", **FAST)
    with pytest.raises(ValueError, match="dos clases"):
        evidence_ladder({"clínica": clinic}, latent, task="classification", **FAST)
    with pytest.raises(ValueError, match="clase minoritaria"):
        evidence_ladder({"clínica": clinic}, latent > latent.nlargest(4).min(), task="classification", **FAST)
    with pytest.raises(ValueError, match="'sexo'.*'clínica'"):
        evidence_ladder({"clínica": clinic.assign(sexo="M")}, binary, task="classification", **FAST)
    with pytest.raises(ValueError, match="task"):
        evidence_ladder({"clínica": clinic}, binary, task="ranking", **FAST)


def test_an_unrelated_binary_nuisance_gives_auc_near_one_half():
    rng = np.random.default_rng(0)
    score = pd.Series(rng.normal(size=300))
    scanner = pd.Series(rng.choice(["A", "B"], 300))

    out = nuisance_association(score, scanner, n_bootstrap=500)

    assert 0.5 <= out["auc"] < 0.56
    assert out["ic95_inf"] < 0.5 < out["ic95_sup"]
    assert out["n"] == 300 and sorted(out["niveles"]) == ["A", "B"]


@pytest.mark.parametrize("direction", [1.0, -1.0])
def test_a_related_binary_nuisance_gives_auc_clearly_above_one_half(direction):
    rng = np.random.default_rng(0)
    scanner = pd.Series(rng.choice(["A", "B"], 300))
    score = pd.Series(rng.normal(size=300)) + direction * 1.5 * (scanner == "B")

    out = nuisance_association(score, scanner, n_bootstrap=500)

    assert out["auc"] > 0.8
    assert out["ic95_inf"] > 0.7


def test_a_nuisance_with_several_levels_reports_kruskal_wallis_and_eta_squared():
    rng = np.random.default_rng(0)
    centre = pd.Series(rng.choice(["bcn", "mad", "pmi"], 300))
    unrelated = pd.Series(rng.normal(size=300))
    related = unrelated + 1.5 * (centre == "pmi")

    null, shifted = nuisance_association(unrelated, centre), nuisance_association(related, centre)

    assert null["p_kruskal"] > 0.05 and null["eta2"] < 0.02
    assert shifted["p_kruskal"] < 1e-6 and shifted["eta2"] > 0.2
    assert "auc" not in shifted


def test_nuisance_rows_with_missing_values_are_dropped():
    rng = np.random.default_rng(0)
    score = pd.Series(rng.normal(size=100))
    sex = pd.Series(rng.choice(["F", "M"], 100)).astype(object)
    score.iloc[:5] = np.nan
    sex.iloc[5:12] = None

    out = nuisance_association(score, sex, n_bootstrap=200)

    assert out["n"] == 88
    assert out == nuisance_association(score.iloc[12:], sex.iloc[12:], n_bootstrap=200)
    with pytest.raises(ValueError, match="dos niveles"):
        nuisance_association(score, pd.Series("F", index=score.index))
