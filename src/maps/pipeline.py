"""Del corte en HU a embeddings por parche dentro del pulmón."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
import torch.nn.functional as F
from scipy import ndimage

from maps.backbone import PatchEncoder
from maps.ct import to_rgb_windows

# Fracción mínima de la celda que debe ser pulmón. Descarta las celdas de borde,
# donde la pleura y la pared torácica dominarían la distancia al banco.
MIN_LUNG_FRACTION = 0.9


@dataclass(frozen=True)
class SliceEmbedding:
    features: torch.Tensor  # (n_celdas, d), float16
    cells: np.ndarray  # (n_celdas, 2), fila y columna en la rejilla
    grid: tuple[int, int]

    def to_map(self, values: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
        """Coloca un valor por celda en la rejilla y lo amplía al tamaño del corte. NaN fuera del pulmón."""
        grid = np.full(self.grid, np.nan, dtype=np.float32)
        grid[self.cells[:, 0], self.cells[:, 1]] = values
        filled = np.where(np.isnan(grid), 0.0, grid)
        weight = (~np.isnan(grid)).astype(np.float32)
        zoom = (shape[0] / self.grid[0], shape[1] / self.grid[1])
        num = ndimage.zoom(filled, zoom, order=1)
        den = ndimage.zoom(weight, zoom, order=1)
        return np.where(den > 0.5, num / np.maximum(den, 1e-6), np.nan)


def embed_slice(
    encoder: PatchEncoder, hu: np.ndarray, lung: np.ndarray, *, scale: float = 2.0
) -> SliceEmbedding:
    """Embeddings de las celdas de la rejilla que caen dentro del pulmón.

    `scale` amplía el corte antes de la red: con 2.0 cada celda cubre 4x4 px
    originales (unos 3 mm), suficiente para textura lobulillar.
    """
    device = next(encoder.parameters()).device
    x = to_rgb_windows(hu).unsqueeze(0).to(device)
    if scale != 1.0:
        x = F.interpolate(x, scale_factor=scale, mode="bilinear", align_corners=False)
    fmap = encoder(x)[0]  # (d, gh, gw)
    gh, gw = fmap.shape[-2:]
    fraction = F.adaptive_avg_pool2d(torch.from_numpy(lung[None, None].astype(np.float32)), (gh, gw))[0, 0]
    cells = torch.nonzero(fraction >= MIN_LUNG_FRACTION)
    feats = fmap[:, cells[:, 0], cells[:, 1]].T.to(torch.float16).cpu()
    return SliceEmbedding(feats, cells.numpy(), (gh, gw))
