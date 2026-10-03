"""Asociación de la TC y la clínica con determinaciones moleculares, al estilo de un EWAS.

Con unos 80 sujetos y cientos de miles de CpG no cabe un modelo conjunto: se
ajusta un modelo lineal por rasgo molecular, `rasgo ~ exposición + covariables`,
y se controla la multiplicidad. La exposición es una sola variable por sujeto,
por ejemplo la puntuación de daño de la TC. `associate` da la tabla por rasgo,
`genomic_inflation` dice si esos p-valores están inflados en conjunto y
`max_t_permutation` responde a una única pregunta, si hay alguna asociación,
sin apoyarse en la normalidad de los residuos.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from scipy import stats

from maps.cohort import encode_block
from maps.normative import SPARE_ROWS

MIN_SUBJECTS = 20
CHUNK_VALUES = 2_000_000  # valores por trozo de columnas: unos 16 MB por matriz intermedia
TOLERANCE = 1e-10  # fracción de la variación por debajo de la cual una columna no aporta nada propio


@dataclass(frozen=True)
class _Design:
    """Los sujetos que entran en el modelo y lo que se sabe de ellos, ya alineado."""

    rows: np.ndarray  # posición de cada sujeto en la tabla molecular
    exposure: np.ndarray
    nuisance: np.ndarray  # término independiente y covariables codificadas
    needed: int  # sujetos mínimos para ajustar un rasgo


def _design(
    molecular: pd.DataFrame, exposure: pd.Series, covariates: pd.DataFrame | None, min_subjects: int
) -> _Design:
    """Valida las entradas, alinea por sujeto y descarta a quien le falta la exposición o una covariable."""
    if covariates is None:
        covariates = pd.DataFrame(index=molecular.index)
    indexes = {"molecular": molecular.index, "exposición": exposure.index, "covariables": covariates.index}
    for name, index in indexes.items():
        if not index.is_unique:
            raise ValueError(f"hay sujetos repetidos en el índice de la tabla de {name}")
    if not is_numeric_dtype(exposure):
        raise ValueError("la exposición debe ser numérica; si es un grupo, codifícalo como 0/1")
    odd = molecular.select_dtypes(exclude=[np.number, "bool"]).columns
    if len(odd):
        raise ValueError(f"la columna '{odd[0]}' de la tabla molecular no es numérica")

    x = exposure.reindex(molecular.index).to_numpy(dtype=float, na_value=np.nan)
    covariates = covariates.reindex(molecular.index)
    kept = ~np.isnan(x) & covariates.notna().all(axis=1).to_numpy()
    x = x[kept]
    # las categorías se codifican con los sujetos que quedan: un nivel que solo
    # tenían los descartados no debe gastar una columna
    encoded = encode_block(covariates.loc[kept]).to_numpy(dtype=float)
    nuisance = np.column_stack([np.ones(len(x)), encoded])
    if not (np.isfinite(x).all() and np.isfinite(nuisance).all()):
        raise ValueError("la exposición o las covariables tienen valores infinitos")

    columns = nuisance.shape[1] + 1
    needed = max(min_subjects, columns + SPARE_ROWS)
    if len(x) < needed:
        raise ValueError(
            f"quedan {len(x)} sujetos con datos moleculares, exposición y covariables y hacen falta al menos "
            f"{needed}: el mínimo pedido es {min_subjects} y el modelo tiene {columns} columnas, más {SPARE_ROWS}"
        )
    if np.ptp(x) == 0:
        raise ValueError("la exposición es constante en los sujetos que quedan: no hay nada que asociar")
    if np.isnan(_own_variation(_basis(nuisance), x[:, None])[1][0]):
        raise ValueError(
            "la exposición es combinación lineal de las covariables: su efecto no se puede separar del de ellas"
        )
    return _Design(np.flatnonzero(kept), x, nuisance, needed)


def _basis(nuisance: np.ndarray) -> np.ndarray:
    """Base ortonormal de lo que explican las covariables.

    Una covariable constante o repetida no añade dirección ni gasta un grado de
    libertad: el coeficiente de la exposición es el mismo con ella que sin ella.
    """
    norms = np.linalg.norm(nuisance, axis=0)
    # a norma uno, para que la edad en años y un volumen en mililitros pesen igual al medir el rango
    u, s, _ = np.linalg.svd(nuisance / np.where(norms > 0, norms, 1.0), full_matrices=False)
    return u[:, s > TOLERANCE * s[0]]


def _own_variation(q: np.ndarray, columns: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Lo que queda de cada columna al quitarle las covariables, y su suma de cuadrados.

    La suma es NaN si la columna es constante o las covariables la explican
    entera. Lo que quedaría es error de redondeo, y dividirlo daría un t enorme
    sin ningún significado.
    """
    residual = columns - q @ (q.T @ columns)
    own = (residual**2).sum(axis=0)
    total = ((columns - columns.mean(axis=0)) ** 2).sum(axis=0)
    own[(np.ptp(columns, axis=0) == 0) | (own <= TOLERANCE * total)] = np.nan
    return residual, own


def _partial_fits(q: np.ndarray, exposures: np.ndarray, features: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Coeficiente y error típico de cada exposición (columnas) sobre cada rasgo (columnas), dadas las covariables.

    Por Frisch-Waugh, el coeficiente de la exposición en el modelo completo es
    el de la regresión simple entre los residuos de la exposición y los del
    rasgo. Eso deja todos los rasgos, y todas las permutaciones de la
    exposición, en un producto de matrices. Devuelve dos matrices de
    exposiciones por rasgos, con NaN donde un lado no tiene variación propia.
    """
    x, sxx = _own_variation(q, exposures)
    y, syy = _own_variation(q, features)
    sxy = x.T @ y
    degrees = len(q) - q.shape[1] - 1
    with np.errstate(invalid="ignore", divide="ignore"):
        coef = sxy / sxx[:, None]
        rss = np.clip(syy - coef * sxy, 0.0, None)
        se = np.sqrt(rss / (degrees * sxx[:, None]))
    coef[np.isnan(se)] = np.nan
    return coef, se


def _chunks(molecular: pd.DataFrame, rows: np.ndarray, width: int) -> Iterator[tuple[int, np.ndarray]]:
    """Trozos de columnas, con solo los sujetos del diseño: la tabla entera nunca se copia de una vez."""
    for start in range(0, molecular.shape[1], width):
        block = molecular.iloc[:, start : start + width].to_numpy(dtype=float, na_value=np.nan)
        yield start, block[rows]  # la indexación copia: el trozo se puede modificar


def associate(
    molecular: pd.DataFrame,
    exposure: pd.Series,
    covariates: pd.DataFrame | None = None,
    *,
    min_subjects: int = MIN_SUBJECTS,
) -> pd.DataFrame:
    """Un modelo lineal por rasgo molecular: cuánto cambia el rasgo por unidad de exposición.

    `molecular` tiene un sujeto por fila y un rasgo numérico por columna;
    `exposure` y `covariates` van indexadas por el mismo identificador de
    sujeto y se alinean por él, en cualquier orden. Las covariables numéricas
    entran tal cual y las demás como indicadores, con un nivel de base. Se
    descarta a quien le falta la exposición o alguna covariable.

    Para cada rasgo se ajusta por mínimos cuadrados
    `rasgo ~ término independiente + exposición + covariables`. Devuelve una
    fila por rasgo, ordenadas por `p`:

    - `coef`, `se`, `t`: coeficiente de la exposición, su error típico y su cociente.
    - `p`: bilateral, con la t de Student de los grados de libertad del rasgo.
    - `fdr`: p ajustado por Benjamini-Hochberg entre los rasgos contrastados.
    - `n`: sujetos usados para ese rasgo.

    Un rasgo con huecos (los infinitos cuentan como huecos) se ajusta con los
    sujetos que lo tienen. Si le quedan menos sujetos que el mínimo, si es
    constante o si las covariables lo explican entero, sus estadísticos son
    NaN y no cuenta en el FDR: no se le hizo ningún contraste.

    Se rechaza si quedan menos de `min_subjects` sujetos o menos que columnas
    del modelo + 5, y si la exposición es constante o combinación lineal de las
    covariables.
    """
    design = _design(molecular, exposure, covariates, min_subjects)
    n_subjects, n_features = len(design.rows), molecular.shape[1]
    coef, se, degrees = (np.full(n_features, np.nan) for _ in range(3))
    n = np.zeros(n_features, dtype=int)
    everyone = np.ones(n_subjects, dtype=bool)

    for start, values in _chunks(molecular, design.rows, max(1, CHUNK_VALUES // n_subjects)):
        missing = ~np.isfinite(values)
        incomplete = missing.any(axis=0)
        groups = [(everyone, np.flatnonzero(~incomplete))]
        if incomplete.any():
            # los rasgos con los mismos huecos comparten sujetos y se ajustan
            # juntos; en el peor caso es un ajuste por rasgo
            columns = np.flatnonzero(incomplete)
            patterns, member = np.unique(missing[:, columns], axis=1, return_inverse=True)
            member = member.ravel()
            groups += [(~patterns[:, i], columns[member == i]) for i in range(patterns.shape[1])]
        for present, columns in groups:
            where = start + columns
            n[where] = present.sum()
            if len(columns) == 0 or present.sum() < design.needed:
                continue
            complete = present is everyone
            block = values if complete and len(columns) == values.shape[1] else values[:, columns]
            q = _basis(design.nuisance[present])
            fits = _partial_fits(q, design.exposure[present][:, None], block if complete else block[present])
            coef[where], se[where] = fits[0][0], fits[1][0]
            degrees[where] = present.sum() - q.shape[1] - 1

    with np.errstate(invalid="ignore", divide="ignore"):
        t = coef / se
    p = 2 * stats.t.sf(np.abs(t), degrees)
    tested = np.isfinite(p)
    fdr = np.full(n_features, np.nan)
    if tested.any():
        fdr[tested] = stats.false_discovery_control(p[tested], method="bh")
    result = pd.DataFrame({"coef": coef, "se": se, "t": t, "p": p, "fdr": fdr, "n": n}, index=molecular.columns)
    return result.sort_values("p", kind="stable")


def genomic_inflation(p_values: np.ndarray | pd.Series) -> float:
    """Lambda de un EWAS: mediana de los ji-cuadrado de los p-valores entre la que se espera sin asociación.

    Vale 1 cuando los p-valores son uniformes. Bastante más de 1 quiere decir
    que hay demasiados p pequeños en todo el genoma, lo que suele ser una
    covariable que falta (tipos celulares, lote) antes que biología. Los NaN no
    cuentan.
    """
    p = np.asarray(p_values, dtype=float)
    p = p[~np.isnan(p)]
    if len(p) == 0:
        raise ValueError("no hay ningún p-valor con el que calcular lambda")
    if ((p < 0) | (p > 1)).any():
        raise ValueError("los p-valores deben estar entre 0 y 1")
    return float(np.median(stats.chi2.isf(p, df=1)) / stats.chi2.ppf(0.5, df=1))  # el divisor es 0,4549


def _mean_imputed(values: np.ndarray, minimum: int) -> np.ndarray:
    """Huecos de cada rasgo sustituidos por su media. Un rasgo con menos de `minimum` sujetos queda fuera (NaN)."""
    missing = ~np.isfinite(values)
    available = len(values) - missing.sum(axis=0)
    means = np.where(missing, 0.0, values).sum(axis=0) / np.maximum(available, 1)
    filled = np.where(missing, means, values)
    filled[:, available < minimum] = np.nan
    return filled


def max_t_permutation(
    molecular: pd.DataFrame,
    exposure: pd.Series,
    covariates: pd.DataFrame | None = None,
    *,
    n_permutations: int = 1000,
    seed: int = 0,
) -> dict:
    """¿Hay alguna asociación entre la exposición y los rasgos? Una sola prueba, por permutación.

    El estadístico es el mayor |t| entre todos los rasgos. Su distribución nula
    se obtiene permutando la exposición y repitiendo el cálculo, así que la
    correlación entre rasgos y las colas no normales ya están dentro, y el
    resultado es un único p sin corrección por multiplicidad pendiente.

    Con covariables no se permuta la exposición cruda, que rompería su relación
    con ellas: se permutan sus residuos respecto a las covariables y se les
    vuelve a sumar la parte ajustada, que es el esquema de Freedman-Lane
    llevado al lado de la exposición (el procedimiento de Smith en Winkler et
    al., 2014). Sin covariables es la permutación de siempre.

    Devuelve `max_t` (el observado), `p` (fracción de permutaciones cuyo máximo
    lo iguala o supera, con la corrección +1) y `umbral_5` (percentil 95 del
    máximo nulo: un |t| por encima es significativo al 5 % en toda la tabla).

    Solo en esta función, los huecos de un rasgo se rellenan con su media, para
    que todos los rasgos compartan sujetos y cada permutación sea un producto
    de matrices. El relleno es el mismo en el cálculo observado y en los
    permutados, de modo que la comparación sigue siendo justa; los |t| de esos
    rasgos son aproximados y el valor exacto es el de `associate`. Los rasgos
    que `associate` dejaría en NaN tampoco entran aquí. Las entradas se validan
    igual que allí, con el mínimo de sujetos por defecto.
    """
    if n_permutations < 1:
        raise ValueError("n_permutations debe ser al menos 1")
    design = _design(molecular, exposure, covariates, MIN_SUBJECTS)
    n_subjects = len(design.rows)
    q = _basis(design.nuisance)
    fitted = q @ (q.T @ design.exposure)
    residual = design.exposure - fitted
    rng = np.random.default_rng(seed)
    orders = np.vstack([np.arange(n_subjects), *(rng.permutation(n_subjects) for _ in range(n_permutations))])
    exposures = fitted[:, None] + residual[orders].T  # la primera columna es la exposición observada

    largest = np.zeros(n_permutations + 1)
    # aquí la matriz grande es permutaciones por rasgos, no sujetos por rasgos
    for _, values in _chunks(molecular, design.rows, max(1, CHUNK_VALUES // max(n_subjects, len(orders)))):
        coef, se = _partial_fits(q, exposures, _mean_imputed(values, design.needed))
        with np.errstate(invalid="ignore", divide="ignore"):
            t = np.abs(coef / se)
        largest = np.fmax(largest, np.fmax.reduce(t, axis=1, initial=0.0))  # fmax pasa por alto los NaN

    observed, null = largest[0], largest[1:]
    return {
        "max_t": float(observed),
        "p": float(1 + np.sum(null >= observed)) / (1 + n_permutations),
        "umbral_5": float(np.percentile(null, 95)),
    }
