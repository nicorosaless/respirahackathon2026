"""Segmentación pulmonar y lobar con la U-Net preentrenada de lungmask."""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import torch
from lungmask import LMInferer

LOBES = {1: "LSI", 2: "LII", 3: "LSD", 4: "LM", 5: "LID"}
MIN_FREE_VRAM_GIB = 2.5
BATCH_SIZE = 6  # el valor por defecto de lungmask (20) agota 3 GiB de VRAM


def pick_device() -> torch.device:
    """GPU solo si queda memoria de sobra: la tarjeta se comparte con otros servicios."""
    if torch.cuda.is_available():
        free, _ = torch.cuda.mem_get_info()
        if free / 2**30 >= MIN_FREE_VRAM_GIB:
            return torch.device("cuda")
    return torch.device("cpu")


@lru_cache(maxsize=2)
def _inferer(lobes: bool) -> LMInferer:
    force_cpu = pick_device().type == "cpu"
    if lobes:
        # Sin `fillmodel="R231"`: la fusión de los dos modelos tarda 7 min por volumen en CPU.
        return LMInferer(modelname="LTRCLobes", force_cpu=force_cpu, batch_size=BATCH_SIZE, tqdm_disable=True)
    return LMInferer(modelname="R231", force_cpu=force_cpu, batch_size=BATCH_SIZE, tqdm_disable=True)


def segment(hu_zyx: np.ndarray, *, lobes: bool = False) -> np.ndarray:
    """Etiquetas por vóxel. Sin lóbulos: 1 derecho, 2 izquierdo. Con lóbulos: ver `LOBES`."""
    return _inferer(lobes).apply(hu_zyx)
