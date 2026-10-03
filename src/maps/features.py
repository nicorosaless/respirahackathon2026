"""De una TC segmentada a una tabla de medidas por región y una vista previa."""

from __future__ import annotations

import numpy as np
import pandas as pd

from maps.airways import measure_airways
from maps.anatomy import LOBES, Anatomy
from maps.geometry import bounding_box
from maps.measures import MEASURES, WHOLE_LUNG, measures_dictionary  # noqa: F401  (reexportados)
from maps.qct import MILD_LOW_ATTENUATION_HU, air_noise, clustering, densitometry, smooth_hu, volume_and_mass
from maps.vessels import small_vessel_mask, vessel_metrics

Spacing = tuple[float, float, float]

PREVIEW_SLICES = 5


def region_table(hu: np.ndarray, anatomy: Anatomy, spacing: Spacing) -> pd.DataFrame:
    """Una fila por lóbulo y otra del pulmón entero. Las medidas del árbol aéreo solo van en la del pulmón."""
    # Todo se mide dentro de la caja del pulmón y la tráquea: el resto del tórax solo cuesta tiempo.
    box = bounding_box((anatomy.lobes > 0) | anatomy.airway, margin=4)
    hu = hu[box]
    anatomy = Anatomy(*(mask[box] for mask in (anatomy.lobes, anatomy.airway, anatomy.airway_wall,
                                                anatomy.arteries, anatomy.veins)))
    smoothed = smooth_hu(hu, spacing)
    # Con -950 HU apenas hay vóxeles en enfermedad temprana; -910 da un patrón medible.
    low = smoothed < MILD_LOW_ATTENUATION_HU
    vessels = anatomy.vessels
    small = small_vessel_mask(vessels, spacing)
    small_arteries = small & anatomy.arteries
    lung = anatomy.lobes > 0
    # El parénquima excluye vasos y vía aérea: si no, su densidad se cuenta como tejido pulmonar.
    parenchyma = lung & ~vessels & ~anatomy.airway & ~anatomy.airway_wall

    regions = {name: anatomy.lobes == label for label, name in LOBES.items()}
    regions[WHOLE_LUNG] = lung
    lung_volume_ml = volume_and_mass(hu, lung, spacing)["volumen_ml"]
    airways, airway_by_lobe = (measure_airways(anatomy.airway, spacing, lung_volume_ml, anatomy.airway_wall, anatomy.lobes)
                               if anatomy.airway.any() else ({}, {}))
    rows = []
    for name, region in regions.items():
        if not region.any():
            continue
        tissue = region & parenchyma
        row = {"region": name}
        row |= volume_and_mass(hu, region, spacing)
        row |= densitometry(hu, tissue, smoothed)
        row["agrupamiento"] = clustering(low, tissue)
        row |= vessel_metrics(vessels, small, region, spacing)
        row["arterias_bv5_tbv"] = vessel_metrics(anatomy.arteries, small_arteries, region, spacing)["vasos_bv5_tbv"]
        if airways:
            # La longitud de vía aérea dentro de cada lóbulo, y su suma en la fila del pulmón entero.
            label = next((label for label, lobe in LOBES.items() if lobe == name), None)
            row["via_longitud_lobar_mm"] = (float(sum(airway_by_lobe.values())) if name == WHOLE_LUNG
                                            else float(airway_by_lobe.get(label, 0.0)))
        if name == WHOLE_LUNG and airways:
            row |= airways
            row["ruido_hu"] = air_noise(hu, anatomy.airway, spacing)
        rows.append(row)
    return pd.DataFrame(rows)


def coronal_preview(hu: np.ndarray, lobes: np.ndarray, spacing: Spacing) -> dict[str, np.ndarray]:
    """Cortes coronales de anterior a posterior, con la cabeza arriba, recortados al pulmón.

    Espera el volumen en LPS: z crece hacia la cabeza, así que se invierte para dibujar.
    """
    lung = lobes > 0
    z_any, y_any, x_any = (np.flatnonzero(lung.any(axis=axes)) for axes in ((1, 2), (0, 2), (0, 1)))
    margin = 10
    z0, z1 = max(z_any[0] - margin, 0), min(z_any[-1] + margin, hu.shape[0])
    x0, x1 = max(x_any[0] - margin, 0), min(x_any[-1] + margin, hu.shape[2])
    picks = np.linspace(y_any[0], y_any[-1], PREVIEW_SLICES + 2)[1:-1].astype(int)
    return {
        "hu": np.stack([hu[z0:z1, y, x0:x1][::-1] for y in picks]).astype(np.int16),
        "lobes": np.stack([lobes[z0:z1, y, x0:x1][::-1] for y in picks]).astype(np.uint8),
        "spacing": np.array([spacing[0], spacing[2]], dtype=np.float32),
    }
