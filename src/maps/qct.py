"""Biomarcadores densitométricos clásicos de TC pulmonar.

Son la referencia contra la que se compara cualquier modelo profundo: baratos,
interpretables y ya aceptados en clínica (%LAA-950, Perc15).
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage, stats

from maps.geometry import distance_to

EMPHYSEMA_HU = -950
MILD_LOW_ATTENUATION_HU = -910
HIGH_ATTENUATION_HU = (-600, -250)


SMOOTHING_MM = 1.0
NOISE_DEPTH_MM = 3.0  # el aire a menos de esto de la pared mezcla tejido y no sirve para medir ruido
MIN_NOISE_VOXELS = 200


def smooth_hu(hu: np.ndarray, spacing: tuple[float, ...] | None = None) -> np.ndarray:
    """Filtro gaussiano de 1 mm de desviación típica en cada eje, antes de umbralizar.

    Con `spacing` (mm por vóxel) el filtro mide lo mismo en todas las TC, tengan
    el corte que tengan. Sin él se aplica un vóxel por eje.
    """
    sigma = 1.0 if spacing is None else [SMOOTHING_MM / s for s in spacing]
    return ndimage.gaussian_filter(hu.astype(np.float32), sigma=sigma)


def air_noise(hu: np.ndarray, airway: np.ndarray, spacing: tuple[float, float, float]) -> float:
    """Ruido de la imagen, en HU: dispersión del aire en el centro de la tráquea y los bronquios grandes.

    Ahí todo es aire, así que lo que varía es ruido. Se mide del percentil 50
    al 84, que es una desviación típica si el ruido es simétrico y no se
    altera cuando el escáner recorta los valores por debajo de -1024 HU.
    """
    core = hu[distance_to(~airway, spacing) >= NOISE_DEPTH_MM]
    if core.size < MIN_NOISE_VOXELS:
        return float("nan")
    median, upper = np.percentile(core, [50, 84.13])
    return float(upper - median)


def densitometry(hu: np.ndarray, lung: np.ndarray, smoothed: np.ndarray | None = None) -> dict[str, float]:
    """Resume la distribución de densidades dentro de la máscara pulmonar.

    `hu` y `lung` tienen la misma forma, 2D o 3D. El kernel de reconstrucción
    duro infla %LAA por ruido, así que se reporta también tras un suavizado.
    Pasa `smoothed` (de `smooth_hu`) cuando midas varias regiones del mismo volumen.
    """
    voxels = hu[lung]
    if voxels.size == 0:
        raise ValueError("la máscara pulmonar está vacía")
    smooth = (smooth_hu(hu) if smoothed is None else smoothed)[lung]
    lo, hi = HIGH_ATTENUATION_HU
    return {
        "laa950": 100.0 * float(np.mean(voxels < EMPHYSEMA_HU)),
        "laa910": 100.0 * float(np.mean(voxels < MILD_LOW_ATTENUATION_HU)),
        "laa950_smooth": 100.0 * float(np.mean(smooth < EMPHYSEMA_HU)),
        "perc15": float(np.percentile(voxels, 15)),
        "haa": 100.0 * float(np.mean((voxels >= lo) & (voxels <= hi))),
        "mld": float(voxels.mean()),
        "sd": float(voxels.std()),
        "skew": float(stats.skew(voxels, axis=None)),
        "kurtosis": float(stats.kurtosis(voxels, axis=None)),
    }


def volume_and_mass(hu: np.ndarray, region: np.ndarray, spacing: tuple[float, float, float]) -> dict[str, float]:
    """Volumen y masa de una región. La masa separa "más aire" de "menos tejido"."""
    voxel_ml = float(np.prod(spacing)) / 1000.0
    volume_ml = float(region.sum()) * voxel_ml
    if volume_ml == 0:
        raise ValueError("la región está vacía")
    # Densidad en g/ml: aire (-1000 HU) pesa 0 y agua (0 HU) pesa 1.
    mass_g = float(((hu[region] + 1000.0) / 1000.0).sum()) * voxel_ml
    return {"volumen_ml": volume_ml, "masa_g": mass_g, "densidad_g_l": 1000.0 * mass_g / volume_ml}


MIN_LOW_VOXELS = 100  # con menos, el patrón espacial es ruido


def clustering(low: np.ndarray, region: np.ndarray) -> float:
    """Probabilidad de que el vecino de un vóxel de baja atenuación también lo sea.

    Con reparto al azar vale lo mismo que la fracción de baja atenuación; con
    focos compactos se acerca a 1. Distingue el enfisema real, que forma focos,
    del ruido, que sale disperso.
    """
    low = low & region
    if int(low.sum()) < MIN_LOW_VOXELS:
        return float("nan")
    both = either = 0
    for axis in range(low.ndim):
        a = [slice(None)] * low.ndim
        b = [slice(None)] * low.ndim
        a[axis], b[axis] = slice(0, -1), slice(1, None)
        a, b = tuple(a), tuple(b)
        pair_in_region = region[a] & region[b]
        both += int(np.count_nonzero(low[a] & low[b]))
        either += int(np.count_nonzero((low[a] | low[b]) & pair_in_region))
    # Entre las parejas con algún vóxel bajo, cuántas tienen los dos.
    return both / either if either else float("nan")
