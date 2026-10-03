import numpy as np
import pandas as pd
import pytest

from maps.cohort import damage_score, encode_block, region_z, wide_block


def _cohort(n: int = 120, seed: int = 0) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """Sujetos cuya densidad depende de la talla; los 30 últimos tienen además daño (-25 HU)."""
    rng = np.random.default_rng(seed)
    ids = [f"s{i:03d}" for i in range(n)]
    height = rng.normal(170, 9, n)
    damaged = np.arange(n) >= n - 30
    subjects = pd.DataFrame({"talla": height, "sexo": rng.choice(["H", "M"], n)}, index=pd.Index(ids, name="subject_id"))
    rows = []
    for region, offset in (("LSD", -10.0), ("LID", 0.0)):
        perc15 = -850 + offset - 0.8 * (height - 170) + rng.normal(0, 8, n) - 25 * damaged
        rows.append(pd.DataFrame({"subject_id": ids, "region": region, "perc15": perc15,
                                  "via_ramas_por_litro": np.nan}))
    reference = pd.Series(~damaged, index=subjects.index)
    return pd.concat(rows, ignore_index=True), subjects, reference


def test_damaged_subjects_deviate_and_height_no_longer_explains_the_score():
    features, subjects, reference = _cohort()

    zscores = region_z(features, subjects, reference, ["talla"], ["sexo"])
    score = damage_score(zscores, ("perc15",))

    assert score[~reference].mean() > 2.0  # 25 HU de daño con 8 HU de dispersión
    assert abs(score[reference].mean()) < 0.3
    assert abs(np.corrcoef(score[reference], subjects.loc[reference, "talla"])[0, 1]) < 0.2


def test_lower_density_counts_as_more_damage():
    zscores = pd.DataFrame({"subject_id": ["a", "b"], "region": ["LSD", "LSD"], "perc15": [-3.0, 0.5]})

    score = damage_score(zscores, ("perc15",))

    assert score["a"] == pytest.approx(3.0)
    assert score["b"] == pytest.approx(-0.5)


def test_a_measure_with_no_data_in_a_region_stays_empty_instead_of_failing():
    features, subjects, reference = _cohort()

    zscores = region_z(features, subjects, reference, ["talla"], [])

    assert zscores["via_ramas_por_litro"].isna().all()
    assert list(wide_block(zscores, ["perc15", "via_ramas_por_litro"]).columns) == ["perc15_LID", "perc15_LSD"]


def test_categorical_clinical_columns_become_indicators_and_keep_missing_values():
    table = pd.DataFrame({"edad": [40.0, 45.0, 50.0], "sexo": ["H", "M", None]})

    block = encode_block(table)

    assert list(block.columns) == ["edad", "sexo_M"]
    assert block["sexo_M"].tolist()[:2] == [0.0, 1.0]
    assert np.isnan(block["sexo_M"].iloc[2])


def test_decimal_commas_are_read_as_numbers_and_text_stays_text(tmp_path):
    from maps.tables import read_table

    path = tmp_path / "clinica.csv"
    path.write_text('id,fev1,grupo,dlco\n1,"3,52",control,80\n2,"2,4",caso,\n3,,caso,"61,5"\n')

    table = read_table(path)

    assert table["fev1"].tolist()[:2] == [3.52, 2.4]
    assert np.isnan(table["fev1"].iloc[2])
    assert table["dlco"].iloc[2] == 61.5
    assert table["grupo"].tolist() == ["control", "caso", "caso"]


def test_a_whole_lung_measure_weighs_as_much_as_one_measured_in_every_lobe():
    rows = [{"subject_id": "a", "region": lobe, "laa950_smooth": 0.0, "via_ramas_por_litro": np.nan}
            for lobe in ("LSD", "LM", "LID", "LSI", "LII")]
    rows.append({"subject_id": "a", "region": "pulmon", "laa950_smooth": 0.0, "via_ramas_por_litro": -4.0})
    zscores = pd.DataFrame(rows)

    score = damage_score(zscores, ("laa950_smooth", "via_ramas_por_litro"))

    # enfisema normal (0) y cuatro desviaciones menos de ramas (daño 4): la media de las dos medidas
    assert score["a"] == pytest.approx(2.0)


def test_low_attenuation_percentages_are_compared_as_ratios_not_as_differences():
    # En la referencia el %LAA-950 está pegado a cero. En escala lineal, un 3 % y un 30 % quedan a
    # decenas y centenas de desviaciones; lo que importa es cuántas veces se multiplica.
    rng = np.random.default_rng(0)
    n = 80
    ids = [f"s{i:03d}" for i in range(n)]
    subjects = pd.DataFrame({"talla": rng.normal(170, 9, n)}, index=pd.Index(ids, name="subject_id"))
    laa = 0.3 * 10 ** rng.normal(0, 0.3, n)
    laa[-2:] = [3.0, 30.0]
    features = pd.DataFrame({"subject_id": ids, "region": "LSD", "laa950_smooth": laa})
    reference = pd.Series(np.arange(n) < n - 2, index=subjects.index)

    z = region_z(features, subjects, reference, ["talla"], []).set_index("subject_id")["laa950_smooth"]

    assert 2.0 < z["s078"] < 5.0  # diez veces la mediana, con 0,3 décadas de dispersión
    assert z["s079"] == pytest.approx(2 * z["s078"], rel=0.15)
