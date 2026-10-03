import numpy as np
import pandas as pd
import pytest

from maps.classify import CONTROL, COPD, PRE_COPD, classify, damage_threshold, explain


def test_obstruction_wins_over_everything_and_damage_or_function_make_pre_copd():
    ratio = pd.Series([0.60, 0.80, 0.80, 0.80, 0.80, np.nan])
    score = pd.Series([0.0, 2.0, 0.1, 0.1, np.nan, 2.0])
    function_abnormal = pd.Series([False, False, True, False, False, False])

    classes = classify(ratio, score, function_abnormal, threshold=1.0)

    assert classes.tolist()[:5] == [COPD, PRE_COPD, PRE_COPD, CONTROL, CONTROL]
    assert pd.isna(classes.iloc[5])


def test_threshold_sits_between_the_two_groups_when_they_do_not_overlap():
    score = pd.Series([0.1, 0.2, 0.3, 0.4, 1.6, 1.7, 1.9])
    case = pd.Series([False, False, False, False, True, True, True])

    assert damage_threshold(score, case) == pytest.approx(1.0)


def test_threshold_balances_sensitivity_and_specificity_when_groups_overlap():
    rng = np.random.default_rng(0)
    score = pd.Series(np.r_[rng.normal(0, 1, 400), rng.normal(2, 1, 400)])
    case = pd.Series(np.r_[np.zeros(400, bool), np.ones(400, bool)])

    assert damage_threshold(score, case) == pytest.approx(1.0, abs=0.35)


def test_threshold_needs_both_groups():
    with pytest.raises(ValueError, match="con EPOC y sin EPOC"):
        damage_threshold(pd.Series([0.1, 0.2]), pd.Series([False, False]))


def test_each_class_comes_with_the_numbers_that_decided_it():
    ratio = pd.Series([0.61, 0.74, 0.80, 0.78, 0.75, np.nan])
    score = pd.Series([2.1, 1.25, 0.1, -0.4, np.nan, 2.0])
    function_abnormal = pd.Series([True, False, True, False, False, False])

    reasons = explain(ratio, score, function_abnormal, threshold=0.7, function_rule="FEV1 por debajo del 80 % del predicho")

    assert reasons[0] == "FEV1/FVC de 0,61, por debajo de 0,70: hay obstrucción."
    assert reasons[1] == "Sin obstrucción (FEV1/FVC de 0,74), con la TC parecida a la de la EPOC: puntuación de 1,25 con el umbral en 0,70."
    assert reasons[2] == ("Sin obstrucción (FEV1/FVC de 0,80), con la TC por debajo del umbral (puntuación de 0,10 con el umbral en 0,70), "
                          "con la función alterada: FEV1 por debajo del 80 % del predicho.")
    assert reasons[3] == "Sin obstrucción (FEV1/FVC de 0,78), con la TC por debajo del umbral (puntuación de −0,40 con el umbral en 0,70) y con la función conservada."
    assert reasons[4] == "Sin obstrucción (FEV1/FVC de 0,75), sin TC que medir y con la función conservada."
    assert pd.isna(reasons[5])


def test_without_a_functional_criterion_the_class_depends_only_on_obstruction_and_the_scan():
    ratio = pd.Series([0.61, 0.74, 0.80])
    score = pd.Series([2.1, 1.25, 0.1])
    nobody = pd.Series([False, False, False])

    classes = classify(ratio, score, nobody, threshold=0.7)
    reasons = explain(ratio, score, nobody, threshold=0.7, function_rule=None)

    assert classes.tolist() == [COPD, PRE_COPD, CONTROL]
    assert reasons[1] == "Sin obstrucción (FEV1/FVC de 0,74), con la TC parecida a la de la EPOC: puntuación de 1,25 con el umbral en 0,70."
    assert reasons[2] == "Sin obstrucción (FEV1/FVC de 0,80), con la TC por debajo del umbral (puntuación de 0,10 con el umbral en 0,70)."
