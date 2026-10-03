"""Modelo normativo: cuánto se aparta cada medida de lo esperado para esa persona.

Perc15 o el volumen de un lóbulo cambian con la edad, el sexo, la talla, el
volumen pulmonar y el escáner también en gente sana. Con los sujetos de
referencia se ajusta qué valor se espera dadas esas covariables, y de cada
sujeto se reporta la desviación en unidades de la dispersión entre sanos. Así
el sesgo se quita de la medida misma, no del clasificador que venga después.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from sklearn.model_selection import KFold, LeaveOneOut

MAD_TO_SD = 1.4826  # con residuos normales, 1.4826 * MAD estima la desviación típica
SPARE_ROWS = 5  # sujetos que deben sobrar tras gastar uno por covariable


def _floats(column: pd.Series) -> np.ndarray:
    return column.to_numpy(dtype=float, na_value=np.nan)


@dataclass(frozen=True)
class _Encoder:
    """Covariables a matriz de diseño, con la escala y las categorías vistas al ajustar."""

    numeric: tuple[str, ...]
    center: np.ndarray
    spread: np.ndarray
    levels: dict[str, tuple]

    def design(self, table: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        """Matriz de diseño y qué filas tienen todas sus covariables dentro de lo ajustado."""
        numeric = np.column_stack([np.ones(len(table)), *(_floats(table[c]) for c in self.numeric)])
        numeric[:, 1:] = (numeric[:, 1:] - self.center) / self.spread
        usable = ~np.isnan(numeric).any(axis=1)
        dummies = []
        for name, levels in self.levels.items():
            usable &= table[name].isin(levels).to_numpy()
            # el primer nivel queda como base: lo recoge el término independiente
            dummies += [table[name].isin([level]).to_numpy(dtype=float) for level in levels[1:]]
        return np.column_stack([numeric, *dummies]), usable


@dataclass(frozen=True)
class _MeasureFit:
    encoder: _Encoder
    beta: np.ndarray
    scale: float

    def z(self, table: pd.DataFrame, measure: str) -> np.ndarray:
        x, usable = self.encoder.design(table)
        z = (_floats(table[measure]) - x @ self.beta) / self.scale
        # una categoría no vista tendría el efecto del nivel base: mejor no opinar
        z[~usable] = np.nan
        return z

    def expected(self, table: pd.DataFrame) -> np.ndarray:
        x, usable = self.encoder.design(table)
        expected = x @ self.beta
        expected[~usable] = np.nan
        return expected


@dataclass(frozen=True)
class NormativeModel:
    """Un ajuste por medida. Cada uno usa sus propias filas completas."""

    fits: dict[str, _MeasureFit]
    covariates: tuple[str, ...]

    def z(self, table: pd.DataFrame) -> pd.DataFrame:
        """Desviación de cada medida respecto a lo esperado, en dispersiones de referencia.

        Da NaN donde falta la medida o una covariable, y donde una covariable
        categórica toma un valor que el ajuste de esa medida no vio.
        """
        _require_columns(table, [*self.fits, *self.covariates])
        return pd.DataFrame({m: fit.z(table, m) for m, fit in self.fits.items()}, index=table.index)

    def expected(self, table: pd.DataFrame) -> pd.DataFrame:
        """Lo que el modelo espera de cada medida en cada sujeto, dadas sus covariables.

        Es el valor con el que se compara: `z` es la medida menos esto, partido por la dispersión.
        """
        _require_columns(table, list(self.covariates))
        return pd.DataFrame({m: fit.expected(table) for m, fit in self.fits.items()}, index=table.index)


def _require_columns(table: pd.DataFrame, columns: Sequence[str]) -> None:
    for name in columns:
        if name not in table.columns:
            raise ValueError(f"falta la columna '{name}' en la tabla")


def _split_covariates(covariates: Sequence[str], categorical: Sequence[str]) -> tuple[list[str], list[str]]:
    return [c for c in covariates if c not in categorical], list(categorical)


def _fit_measure(table: pd.DataFrame, measure: str, numeric: list[str], categorical: list[str]) -> _MeasureFit:
    complete = table[[measure, *numeric, *categorical]].notna().all(axis=1).to_numpy()
    rows = table.loc[complete]
    # las categorías se aprenden de las filas de esta medida: un escáner cuyos
    # sujetos no tienen la medida no tiene efecto estimado para ella
    levels = {c: tuple(pd.unique(rows[c])) for c in categorical}
    n_columns = len(numeric) + sum(len(seen) - 1 for seen in levels.values())
    needed = max(n_columns, len(numeric) + len(categorical)) + SPARE_ROWS
    if len(rows) < needed:
        raise ValueError(
            f"la medida '{measure}' tiene {len(rows)} sujetos de referencia completos y hacen falta "
            f"al menos {needed}: {needed - SPARE_ROWS} columnas de covariables más {SPARE_ROWS}"
        )
    values = np.column_stack([np.empty((len(rows), 0)), *(_floats(rows[c]) for c in numeric)])
    spread = values.std(axis=0)
    spread[spread == 0] = 1.0  # una covariable constante no aporta ni debe dividir por cero
    encoder = _Encoder(tuple(numeric), values.mean(axis=0), spread, levels)
    x, _ = encoder.design(rows)
    y = _floats(rows[measure])
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    residuals = y - x @ beta
    # La escala es la del error con un sujeto que el ajuste no vio: el residuo de cada sujeto de
    # referencia si se le hubiera dejado fuera, que en mínimos cuadrados es residuo / (1 - palanca).
    # Con los residuos del propio ajuste, que son más pequeños, el z de los sujetos nuevos sale inflado.
    leverage = np.einsum("ij,ji->i", x, np.linalg.pinv(x))
    free = (1.0 - leverage) > 1e-6  # un sujeto solo en su categoría no tiene error fuera de muestra
    left_out = residuals[free] / (1.0 - leverage[free])
    # la MAD aguanta que algún sujeto "de referencia" no esté tan sano
    scale = MAD_TO_SD * np.median(np.abs(left_out - np.median(left_out))) if left_out.size else 0.0
    if scale == 0:
        scale = residuals.std()
    return _MeasureFit(encoder, beta, float(scale) if scale > 0 else np.nan)


def fit_normative(
    table: pd.DataFrame,
    measures: Sequence[str],
    covariates: Sequence[str],
    categorical: Sequence[str] = (),
) -> NormativeModel:
    """Ajusta, con sujetos de referencia, el valor esperado de cada medida según las covariables.

    `table` solo debe contener sujetos de referencia, uno por fila. Para cada
    medida se ajusta un modelo lineal: las covariables numéricas se estandarizan
    y las de `categorical` se codifican one-hot (basta nombrarlas ahí; pueden
    estar también en `covariates`). La escala del z es 1.4826 * MAD de los
    residuos dejando fuera a cada sujeto, o la desviación típica de los residuos
    si esa MAD es cero.

    Las filas a las que falta la medida o una covariable no entran en el ajuste
    de esa medida. Si quedan menos filas que covariables + 5, se rechaza: con
    tan pocos sujetos el z no significaría nada. Una covariable categórica
    cuenta por sus columnas one-hot, que es lo que gasta sujetos.
    """
    numeric, categorical = _split_covariates(covariates, categorical)
    _require_columns(table, [*measures, *numeric, *categorical])
    for name in [*measures, *numeric]:
        if not is_numeric_dtype(table[name]):
            raise ValueError(
                f"la columna '{name}' no es numérica; si es una covariable categórica, nómbrala en `categorical`"
            )
    fits = {m: _fit_measure(table, m, numeric, categorical) for m in measures}
    return NormativeModel(fits, (*numeric, *categorical))


def cross_fitted_z(
    table: pd.DataFrame,
    reference: pd.Series,
    measures: Sequence[str],
    covariates: Sequence[str],
    categorical: Sequence[str] = (),
    *,
    n_splits: int | None = 5,
    seed: int = 0,
) -> pd.DataFrame:
    """z de toda la cohorte sin que ningún sujeto se compare con un modelo que lo vio.

    `reference` marca, con el índice de `table`, quién es de referencia. Los
    demás reciben el z del modelo ajustado con todas las referencias. Cada
    sujeto de referencia recibe el z de un modelo ajustado sin su fold: si se
    usara el modelo que lo vio, sus residuos saldrían encogidos y la referencia
    parecería más homogénea que los sujetos a los que se compara.

    Un sujeto de referencia cuya categoría (por ejemplo, su escáner) no aparece
    en los otros folds queda en NaN, igual que una categoría no vista. El
    mínimo de sujetos de `fit_normative` se exige también al ajuste de cada
    fold, que tiene (n_splits - 1) / n_splits de las referencias.

    Con `n_splits=None` se deja fuera a un sujeto cada vez. El resultado no
    depende de `seed`, y cada sujeto de referencia se compara con un modelo
    ajustado con todos los demás, que es lo más parecido a lo que le pasa a un
    sujeto nuevo.
    """
    if not reference.index.equals(table.index) or reference.isna().any():
        raise ValueError("`reference` debe tener el mismo índice que `table` y ningún valor ausente")
    is_reference = reference.to_numpy(dtype=bool)
    z = fit_normative(table.loc[is_reference], measures, covariates, categorical).z(table).to_numpy(copy=True)
    rows = np.flatnonzero(is_reference)
    splitter = LeaveOneOut() if n_splits is None else KFold(n_splits, shuffle=True, random_state=seed)
    for train, test in splitter.split(rows):
        fold = fit_normative(table.iloc[rows[train]], measures, covariates, categorical)
        z[rows[test]] = fold.z(table.iloc[rows[test]]).to_numpy()
    return pd.DataFrame(z, index=table.index, columns=list(measures))
