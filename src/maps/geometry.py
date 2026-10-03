"""Distancias en milímetros sobre máscaras 3D, con el filtro multihilo de SimpleITK."""

from __future__ import annotations

import numpy as np
import SimpleITK as sitk

Spacing = tuple[float, float, float]


def bounding_box(mask: np.ndarray, margin: int = 0) -> tuple[slice, ...]:
    """Caja mínima que contiene la máscara, ampliada `margin` vóxeles sin salirse del volumen."""
    box = []
    for axis in range(mask.ndim):
        other = tuple(a for a in range(mask.ndim) if a != axis)
        hits = np.flatnonzero(mask.any(axis=other))
        if hits.size == 0:
            raise ValueError("la máscara está vacía")
        box.append(slice(max(int(hits[0]) - margin, 0), min(int(hits[-1]) + 1 + margin, mask.shape[axis])))
    return tuple(box)


def distance_to(target: np.ndarray, spacing: Spacing) -> np.ndarray:
    """Distancia en mm de cada vóxel al vóxel más cercano de `target`. Vale 0 dentro de `target`.

    Equivale a `scipy.ndimage.distance_transform_edt(~target, sampling=spacing)`,
    que con volúmenes de TC enteros tarda más de un minuto.
    """
    image = sitk.GetImageFromArray(target.astype(np.uint8))
    image.SetSpacing(tuple(float(s) for s in reversed(spacing)))
    signed = sitk.SignedMaurerDistanceMap(image, insideIsPositive=False, squaredDistance=False, useImageSpacing=True)
    return np.maximum(sitk.GetArrayFromImage(signed), 0.0)
