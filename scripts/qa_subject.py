"""Figura de control de una TC ya procesada: ¿están bien los lóbulos, la vía aérea y los vasos?

Necesita que `extract_subject.py` se haya ejecutado con `--save-masks`.

    python scripts/qa_subject.py data/lidc/LIDC-IDRI-0004 --id LIDC-0004 --cohort outputs/cohorte
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap

from maps.anatomy import LOBES
from maps.ct import read_image, to_hu
from maps.geometry import bounding_box

LOBE_COLOURS = ["#2a78d6", "#1baf7a", "#eda100", "#e87ba4", "#4a3aa7"]  # LSI, LII, LSD, LM, LID
AIRWAY, ARTERY, VEIN = "#eda100", "#e34948", "#2a78d6"


def _overlay(ax, mask: np.ndarray, colour: str, alpha: float, aspect: float) -> None:
    ax.imshow(np.where(mask, 1.0, np.nan), cmap=ListedColormap([colour]), alpha=alpha, aspect=aspect,
              vmin=0, vmax=1, interpolation="nearest")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("volume", type=Path)
    parser.add_argument("--id", required=True)
    parser.add_argument("--cohort", type=Path, required=True)
    args = parser.parse_args()

    folder = args.cohort / "sujetos" / args.id
    masks = np.load(folder / "masks.npz")
    hu, spacing = to_hu(read_image(args.volume))
    box = bounding_box((masks["lobes"] > 0) | masks["airway"], margin=8)
    hu = hu[box]
    lobes, airway, arteries, veins = (masks[k][box] for k in ("lobes", "airway", "arteries", "veins"))
    aspect = spacing[0] / spacing[2]
    base = np.clip((hu + 1100) / 1000, 0, 1)
    middle = hu.shape[1] // 2
    slab = slice(max(middle - 20, 0), middle + 20)

    fig, axes = plt.subplots(1, 3, figsize=(13, 5.2), constrained_layout=True, facecolor="white")
    panels = ["Lóbulos (corte coronal central)", "Vía aérea (proyección de todo el árbol)",
              "Arterias y venas (proyección de 40 cortes)"]
    for ax, title in zip(axes, panels):
        ax.imshow(base[::-1, middle], cmap="gray", aspect=aspect, vmin=0, vmax=1)
        ax.set_title(title, loc="left", fontsize=11, fontweight="bold")
        ax.set_xticks([]), ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
    for label, colour in zip(LOBES, LOBE_COLOURS):
        _overlay(axes[0], (lobes == label)[::-1, middle], colour, 0.45, aspect)
    _overlay(axes[1], airway.any(axis=1)[::-1], AIRWAY, 0.9, aspect)
    _overlay(axes[2], arteries[:, slab].any(axis=1)[::-1], ARTERY, 0.8, aspect)
    _overlay(axes[2], veins[:, slab].any(axis=1)[::-1], VEIN, 0.8, aspect)
    legend = "   ".join(f"{name}" for name in LOBES.values())
    fig.suptitle(f"{args.id}   lóbulos: {legend}   arterias en rojo, venas en azul", x=0.01, ha="left", fontsize=9)
    out = folder / "qa.png"
    fig.savefig(out, dpi=130)
    print(out)


if __name__ == "__main__":
    main()
