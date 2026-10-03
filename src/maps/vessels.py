"""Poda vascular: qué parte del volumen de sangre está en vasos pequeños.

En la literatura es BV5/TBV, el volumen en vasos de sección menor de 5 mm²
partido por el volumen vascular total. Baja cuando se pierden vasos distales.
"""

from __future__ import annotations

import numpy as np

from maps.geometry import Spacing, bounding_box, distance_to

SMALL_VESSEL_RADIUS_MM = (5.0 / np.pi) ** 0.5  # sección de 5 mm²


def small_vessel_mask(vessels: np.ndarray, spacing: Spacing, radius_mm: float = SMALL_VESSEL_RADIUS_MM) -> np.ndarray:
    """Vóxeles de vaso que no sobreviven a una apertura con una bola del radio dado.

    La apertura se hace con dos mapas de distancia en mm, así el resultado no
    depende de que el vóxel sea anisótropo.
    """
    small = np.zeros(vessels.shape, dtype=bool)
    if not vessels.any():
        return small
    box = bounding_box(vessels, margin=2)
    inside = vessels[box].astype(bool)
    core = distance_to(~inside, spacing) > radius_mm
    small[box] = inside & (distance_to(core, spacing) > radius_mm) if core.any() else inside
    return small


def vessel_metrics(vessels: np.ndarray, small: np.ndarray, region: np.ndarray, spacing: Spacing) -> dict[str, float]:
    """Volumen vascular de una región (lóbulo o pulmón entero) y fracción en vasos pequeños."""
    voxel_ml = float(np.prod(spacing)) / 1000.0
    region_ml = float(region.sum()) * voxel_ml
    if region_ml == 0:
        raise ValueError("la región está vacía")
    total_ml = float(np.count_nonzero(vessels & region)) * voxel_ml
    small_ml = float(np.count_nonzero(small & region)) * voxel_ml
    return {
        "vasos_ml": total_ml,
        "vasos_por_litro": 1000.0 * total_ml / region_ml,
        "vasos_pequenos_ml": small_ml,
        "vasos_bv5_tbv": small_ml / total_ml if total_ml > 0 else float("nan"),
    }
