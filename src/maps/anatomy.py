"""Lóbulos, vía aérea y vasos pulmonares con TotalSegmentator."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import SimpleITK as sitk

LOBES = {1: "LSI", 2: "LII", 3: "LSD", 4: "LM", 5: "LID"}
_LOBE_CLASSES = {
    "lung_upper_lobe_left": 1,
    "lung_lower_lobe_left": 2,
    "lung_upper_lobe_right": 3,
    "lung_middle_lobe_right": 4,
    "lung_lower_lobe_right": 5,
}


@dataclass(frozen=True)
class Anatomy:
    lobes: np.ndarray  # (z, y, x) uint8, 0 fondo y 1-5 según `LOBES`
    airway: np.ndarray  # (z, y, x) bool, luz de tráquea y bronquios
    airway_wall: np.ndarray  # (z, y, x) bool, pared bronquial
    arteries: np.ndarray  # (z, y, x) bool, arterias dentro del pulmón
    veins: np.ndarray  # (z, y, x) bool, venas dentro del pulmón

    @property
    def vessels(self) -> np.ndarray:
        return self.arteries | self.veins


def _run(task: str, source: Path, target: Path, device: str, **options) -> np.ndarray:
    from totalsegmentator.python_api import totalsegmentator

    totalsegmentator(str(source), str(target), task=task, ml=True, device=device, quiet=True, **options)
    return sitk.GetArrayFromImage(sitk.ReadImage(str(target)))


def segment_anatomy(image: sitk.Image, *, device: str = "gpu") -> Anatomy:
    """Segmenta una TC ya orientada a LPS. `device` es "gpu" o "cpu"."""
    from totalsegmentator.map_to_binary import class_map

    total_ids = {name: label for label, name in class_map["total"].items()}
    vessel_ids = {name: label for label, name in class_map["lung_vessels"].items()}
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "ct.nii.gz"
        sitk.WriteImage(image, str(source))
        total = _run("total", source, Path(tmp) / "total.nii.gz", device,
                     roi_subset=[*_LOBE_CLASSES, "trachea"])
        tree = _run("lung_vessels", source, Path(tmp) / "vessels.nii.gz", device)

    lobes = np.zeros(total.shape, dtype=np.uint8)
    for name, label in _LOBE_CLASSES.items():
        lobes[total == total_ids[name]] = label
    if not lobes.any():
        raise ValueError("TotalSegmentator no encontró pulmón en la imagen")
    lung = lobes > 0
    return Anatomy(
        lobes=lobes,
        airway=(total == total_ids["trachea"]) | (tree == vessel_ids["lung_airways"]),
        airway_wall=tree == vessel_ids["lung_airways_wall"],
        arteries=(tree == vessel_ids["lung_arteries"]) & lung,
        veins=(tree == vessel_ids["lung_veins"]) & lung,
    )
