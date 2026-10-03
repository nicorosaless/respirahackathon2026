"""Une la tabla clínica con las medidas de TC y produce lo que leen el análisis y la app."""

from __future__ import annotations

import re
from collections.abc import Iterable

import numpy as np
import pandas as pd

from maps.measures import LOG_FLOOR, LOG_MEASURES, MEASURES, WHOLE_LUNG
from maps.normative import NormativeModel, cross_fitted_z, fit_normative
from maps.tables import read_table  # noqa: F401  (se reexporta para quien ya lo importaba de aquí)

# Una medida por familia, para que la puntuación no cuente la densidad cinco veces.
DEFAULT_SCORE_MEASURES = ("perc15", "agrupamiento", "vasos_bv5_tbv", "via_ramas_por_litro", "via_disanapsia")
KEYS = ["subject_id", "region"]


def _model_scale(features: pd.DataFrame) -> pd.DataFrame:
    """Las medidas en la escala en la que se ajusta el modelo normativo: logaritmo para `LOG_MEASURES`."""
    out = features.copy()
    for measure in LOG_MEASURES:
        if measure in out:
            out[measure] = np.log10(out[measure] + LOG_FLOOR)
    return out


def region_z(
    features: pd.DataFrame,
    subjects: pd.DataFrame,
    reference: pd.Series,
    covariates: list[str],
    categorical: list[str],
    n_splits: int | None = None,
    seed: int = 0,
) -> pd.DataFrame:
    """z de cada medida en cada región, respecto a lo esperado en los sujetos de referencia.

    `features` es la tabla larga por región; `subjects` y `reference` van
    indexados por `subject_id`. Cada región se ajusta por separado, porque el
    valor normal de un lóbulo superior no es el de uno inferior.

    Cada sujeto de referencia recibe el z de un modelo ajustado con todos los
    demás. Con 40 sujetos de referencia, repartirlos en cinco grupos hacía que
    el umbral de daño dependiera del reparto; `n_splits` y `seed` quedan para
    comprobar esa sensibilidad.
    """
    features = _model_scale(features)
    measures = [c for c in features.columns if c not in KEYS]
    out = []
    for region, rows in features.groupby("region", sort=False):
        rows = rows.set_index("subject_id")
        present = [m for m in measures if rows[m].notna().any()]
        table = rows[present].join(subjects[[*covariates, *categorical]], how="inner")
        z = cross_fitted_z(table, reference.loc[table.index], present, covariates, categorical, n_splits=n_splits, seed=seed)
        z = z.reindex(columns=measures)
        z.insert(0, "region", region)
        out.append(z.reset_index())
    return pd.concat(out, ignore_index=True)[[*KEYS, *measures]]


def fit_region_models(
    features: pd.DataFrame,
    subjects: pd.DataFrame,
    reference: pd.Series,
    covariates: list[str],
    categorical: list[str],
) -> dict[str, NormativeModel]:
    """Un modelo normativo por región, ajustado solo con los sujetos de referencia.

    Es lo que se congela para puntuar después a sujetos que no estaban en la
    cohorte. Cada región modela las medidas que tienen algún dato en ella: las
    de vía aérea, por ejemplo, solo existen en el pulmón entero.
    """
    features = _model_scale(features)
    measures = [c for c in features.columns if c not in KEYS]
    models = {}
    for region, rows in features.groupby("region", sort=False):
        rows = rows.set_index("subject_id")
        present = [m for m in measures if rows[m].notna().any()]
        table = rows[present].join(subjects[[*covariates, *categorical]], how="inner")
        is_reference = reference.loc[table.index].to_numpy(dtype=bool)
        models[region] = fit_normative(table[is_reference], present, covariates, categorical)
    return models


def apply_region_models(
    models: dict[str, NormativeModel],
    features: pd.DataFrame,
    subjects: pd.DataFrame,
    covariates: list[str],
    categorical: list[str],
) -> pd.DataFrame:
    """z de los sujetos de `features` con modelos ya ajustados, en el formato de `region_z`.

    No ajusta nada. Una región que los modelos no conocen, o una medida que no
    se ajustó en esa región, queda en NaN.
    """
    features = _model_scale(features)
    measures = [c for c in features.columns if c not in KEYS]
    out = []
    for region, rows in features.groupby("region", sort=False):
        table = rows.set_index("subject_id")[measures].join(subjects[[*covariates, *categorical]], how="inner")
        if region in models:
            z = models[region].z(table).reindex(columns=measures)
        else:
            z = pd.DataFrame(np.nan, index=table.index, columns=measures)
        z.insert(0, "region", region)
        out.append(z.reset_index())
    return pd.concat(out, ignore_index=True)[[*KEYS, *measures]]


def region_z_applied(
    features_fit: pd.DataFrame,
    features_apply: pd.DataFrame,
    subjects_fit: pd.DataFrame,
    subjects_apply: pd.DataFrame,
    reference: pd.Series,
    covariates: list[str],
    categorical: list[str],
) -> pd.DataFrame:
    """z de `features_apply` con el modelo normativo ajustado en la referencia de `features_fit`.

    Sirve para medir a los mismos sujetos con otra adquisición o reconstrucción
    usando exactamente el mismo modelo, sin reajustar nada.
    """
    # solo se ajustan las regiones que se van a aplicar: las demás no tienen por qué poder ajustarse
    asked = features_fit[features_fit["region"].isin(features_apply["region"])]
    models = fit_region_models(asked, subjects_fit, reference, covariates, categorical)
    z = apply_region_models(models, features_apply, subjects_apply, covariates, categorical)
    # las columnas son las medidas con las que se ajustó, estén o no en `features_apply`
    return z.reindex(columns=[*KEYS, *(c for c in features_fit.columns if c not in KEYS)])


def seen_levels(models: dict[str, NormativeModel], column: str, measures: Iterable[str]) -> set:
    """Valores de una covariable categórica que vio el ajuste de alguna de esas medidas."""
    return {level
            for model in models.values()
            for measure, fit in model.fits.items() if measure in measures
            for level in fit.encoder.levels.get(column, ())}


def query_columns(expression: str, columns: Iterable[str]) -> list[str]:
    """Columnas de la tabla que nombra una expresión de `DataFrame.query`."""
    bare = re.sub(r"'[^']*'|\"[^\"]*\"", "", expression)  # un texto entre comillas es un valor, no una columna
    named = {quoted or plain for quoted, plain in re.findall(r"`([^`]+)`|([^\W\d]\w*)", bare)}
    return [c for c in columns if c in named]


def oriented_z(zscores: pd.DataFrame, measures: tuple[str, ...] = DEFAULT_SCORE_MEASURES) -> pd.DataFrame:
    """z de las medidas elegidas, con el signo puesto para que positivo sea peor.

    Una medida cuyo sentido no se conoce se ignora en vez de sumarla con signo arbitrario.
    """
    oriented = {}
    for measure in measures:
        if measure in zscores and measure in MEASURES:
            sign = 1.0 if MEASURES[measure][3] == "mayor" else -1.0
            oriented[measure] = sign * zscores[measure]
    if not oriented:
        raise ValueError(f"ninguna de las medidas {measures} está en la tabla de z")
    return pd.DataFrame(oriented)


def damage_score(zscores: pd.DataFrame, measures: tuple[str, ...] = DEFAULT_SCORE_MEASURES) -> pd.Series:
    """Una puntuación por sujeto: media de los z orientados para que positivo sea peor.

    Primero se resume cada medida en un número por sujeto (la media de sus
    lóbulos, o el pulmón entero si la medida solo existe ahí) y después se
    promedian las medidas. Así cada medida pesa lo mismo: si se promediara por
    regiones, una medida del árbol bronquial, que solo tiene un valor por
    sujeto, pesaría mucho menos que una que tiene cinco.
    """
    oriented = oriented_z(zscores, measures)
    whole = (zscores["region"] == WHOLE_LUNG).to_numpy()
    subject = zscores["subject_id"]
    lobar = oriented[~whole].groupby(subject[~whole]).mean()
    global_ = oriented[whole].groupby(subject[whole]).mean()
    per_measure = lobar.combine_first(global_)
    return per_measure.mean(axis=1, skipna=True).reindex(pd.unique(subject)).rename("puntuacion_dano")


def worst_lobe(zscores: pd.DataFrame, measures: tuple[str, ...] = DEFAULT_SCORE_MEASURES) -> pd.DataFrame:
    """Por sujeto, el lóbulo donde cada medida se aparta más hacia el daño y su z orientado.

    Da dos columnas por medida, `<medida>_peor_lobulo` y `<medida>_peor_z`. El
    pulmón entero solo se nombra si ningún lóbulo tiene la medida, como pasa
    con las de vía aérea.
    """
    oriented = oriented_z(zscores, measures).set_index([zscores["subject_id"], zscores["region"]])
    out = pd.DataFrame(index=pd.Index(pd.unique(zscores["subject_id"]), name="subject_id"))
    for measure in oriented:
        by_region = oriented[measure].unstack("region")
        lobes = by_region.drop(columns=WHOLE_LUNG, errors="ignore")
        if WHOLE_LUNG in by_region:
            by_region[WHOLE_LUNG] = by_region[WHOLE_LUNG].where(lobes.isna().all(axis=1))
        known = by_region.dropna(how="all")
        out[f"{measure}_peor_lobulo"] = known.idxmax(axis=1)
        out[f"{measure}_peor_z"] = known.max(axis=1)
    return out


def wide_block(zscores: pd.DataFrame, measures: list[str]) -> pd.DataFrame:
    """Bloque de variables de TC por sujeto: una columna por medida y región que tenga datos."""
    missing = [m for m in measures if m not in zscores]
    if missing:
        raise ValueError(f"medidas de TC desconocidas: {missing}")
    wide = zscores.pivot(index="subject_id", columns="region", values=measures)
    wide.columns = [f"{measure}_{region}" for measure, region in wide.columns]
    return wide.dropna(axis=1, how="all")


def lung_volume(features: pd.DataFrame) -> pd.Series:
    """Volumen pulmonar total por sujeto, la covariable que corrige el nivel de inspiración."""
    whole = features[features["region"] == WHOLE_LUNG].set_index("subject_id")
    return whole["volumen_ml"].rename("volumen_pulmon_ml")


def encode_block(table: pd.DataFrame) -> pd.DataFrame:
    """Columnas clínicas listas para el modelo: las categóricas pasan a indicadores 0/1."""
    numeric = table.select_dtypes(include=[np.number, "bool"]).astype(float)
    other = table.drop(columns=numeric.columns)
    if other.empty:
        return numeric
    dummies = pd.get_dummies(other.astype("string"), drop_first=True, dtype=float)
    # get_dummies convierte los ausentes en todo ceros; se devuelven a ausente
    for column in other.columns:
        produced = [c for c in dummies.columns if c.startswith(f"{column}_")]
        dummies.loc[other[column].isna(), produced] = np.nan
    return pd.concat([numeric, dummies], axis=1)
