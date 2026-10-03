"""Lectura de TC a unidades Hounsfield y preparación para una red RGB."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import SimpleITK as sitk

AIR_HU = -1024

# Tres ventanas en los tres canales que espera una ResNet preentrenada:
# parénquima completo, rango de baja atenuación (enfisema) y rango de alta
# atenuación (vía aérea engrosada, cambios intersticiales).
WINDOWS_HU = ((-1024, -400), (-1024, -850), (-850, -250))


def read_tiff_hu(path: Path) -> np.ndarray:
    """Corte de la base de enfisema: int16 ya en HU, con -3024 fuera del FOV."""
    import tifffile

    return np.maximum(tifffile.imread(path).astype(np.float32), AIR_HU)


def read_image(path: Path, series_uid: str | None = None) -> sitk.Image:
    """Lee un NIfTI o una carpeta DICOM, orientado a LPS.

    Una carpeta puede traer varias series (localizador, otro kernel). Sin
    `series_uid` se toma la de más cortes.
    """
    path = Path(path)
    if path.is_dir():
        reader = sitk.ImageSeriesReader()
        uids = reader.GetGDCMSeriesIDs(str(path))
        if not uids:
            raise ValueError(f"no hay una serie DICOM en {path}")
        files = {uid: reader.GetGDCMSeriesFileNames(str(path), uid) for uid in uids}
        if series_uid is None:
            series_uid = max(files, key=lambda uid: len(files[uid]))
        elif series_uid not in files:
            raise ValueError(f"la serie {series_uid} no está en {path}")
        reader.SetFileNames(files[series_uid])
        image = reader.Execute()
    else:
        image = sitk.ReadImage(str(path))
    # Con LPS el índice x crece hacia la izquierda del paciente y z hacia la cabeza.
    return sitk.DICOMOrient(image, "LPS")


def to_hu(image: sitk.Image) -> tuple[np.ndarray, tuple[float, float, float]]:
    """Matriz (z, y, x) en HU y espaciado (z, y, x) en mm."""
    hu = np.maximum(sitk.GetArrayFromImage(image).astype(np.float32), AIR_HU)
    sx, sy, sz = image.GetSpacing()
    return hu, (sz, sy, sx)


def read_volume_hu(path: Path) -> tuple[np.ndarray, tuple[float, float, float]]:
    """Lee una serie DICOM (carpeta) o un NIfTI. Devuelve (z, y, x) en HU y el espaciado en mm."""
    return to_hu(read_image(path))


def to_rgb_windows(hu: np.ndarray) -> "torch.Tensor":
    """(..., H, W) en HU -> (..., 3, H, W) en [0, 1], una ventana por canal."""
    import torch  # solo el experimento con ResNet lo necesita; el resto del paquete funciona sin torch

    x = torch.as_tensor(hu, dtype=torch.float32)
    channels = [((x - lo) / (hi - lo)).clamp(0, 1) for lo, hi in WINDOWS_HU]
    return torch.stack(channels, dim=-3)
