"""Mapa de daño por lóbulos de un volumen de TC (serie DICOM o NIfTI).

Es el camino que se usará con los datos de la hackathon: segmenta lóbulos,
calcula la densitometría clásica y el mapa de la ResNet por lóbulo y guarda una
tabla y una figura coronal. Necesita el modelo de parches que deja
`exp_slices.py`.

    uv run python scripts/run_volume.py data/lidc/LIDC-IDRI-0002
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from matplotlib.colors import LinearSegmentedColormap
from scipy import ndimage

from maps.backbone import PatchEncoder
from maps.ct import read_volume_hu
from maps.lungs import LOBES, pick_device, segment
from maps.pipeline import embed_slice
from maps.qct import densitometry
from maps.weak import DISEASE_LIKE

ROOT = Path(__file__).resolve().parents[1]
MIN_LUNG_PIXELS = 2000


def find_series_dir(path: Path) -> Path:
    """TCIA anida la serie en subcarpetas; baja hasta la que contiene los .dcm."""
    if path.is_file() or any(path.glob("*.dcm")):
        return path
    candidates = sorted({p.parent for p in path.rglob("*.dcm")}, key=lambda d: -len(list(d.glob("*.dcm"))))
    if not candidates:
        raise FileNotFoundError(f"no hay DICOM en {path}")
    return candidates[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("volume", type=Path)
    parser.add_argument("--model", type=Path, default=ROOT / "outputs" / "patch_model_radimagenet.pt")
    parser.add_argument("--step-mm", type=float, default=5.0, help="separación entre cortes axiales analizados")
    parser.add_argument("--out", type=Path, default=ROOT / "outputs" / "volumes")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    name = args.volume.name.split(".")[0]

    saved = torch.load(args.model, weights_only=False)
    model = saved["model"]
    torch.set_num_threads(8)
    encoder = PatchEncoder(saved["pretraining"]).to(pick_device())

    start = time.time()
    hu, (sz, sy, sx) = read_volume_hu(find_series_dir(args.volume))
    lobes = segment(hu, lobes=True)
    print(f"{name}: {hu.shape}, vóxel {sz:.2f}x{sy:.2f}x{sx:.2f} mm, lóbulos en {time.time() - start:.0f} s")

    # Misma escala física por celda que en los cortes con los que se entrenó el modelo.
    scale = saved["scale"] * sx / saved["pixel_mm"]
    step = max(int(round(args.step_mm / sz)), 1)
    damage = np.full(hu.shape, np.nan, dtype=np.float32)
    analysed = []
    start = time.time()
    for z in range(0, hu.shape[0], step):
        lung = lobes[z] > 0
        if lung.sum() < MIN_LUNG_PIXELS:
            continue
        emb = embed_slice(encoder, hu[z], lung, scale=scale)
        if len(emb.features) == 0:
            continue
        damage[z] = emb.to_map(model.score(emb.features.float()), hu[z].shape)
        analysed.append(z)
    print(f"mapa de la ResNet en {len(analysed)} cortes, {time.time() - start:.0f} s")

    rows = []
    for label, lobe in LOBES.items():
        mask = lobes == label
        if not mask.any():
            continue
        values = damage[mask]
        values = values[~np.isnan(values)]
        rows.append({
            "volumen": name, "lóbulo": lobe, "volumen_ml": mask.sum() * sz * sy * sx / 1000,
            **densitometry(hu, mask),
            "damage_mean": float(values.mean()) if len(values) else np.nan,
            "damage_p95": float(np.percentile(values, 95)) if len(values) else np.nan,
            "damage_burden": 100 * float(np.mean(values > DISEASE_LIKE)) if len(values) else np.nan,
        })
    table = pd.DataFrame(rows)
    table.to_csv(args.out / f"{name}_lobes.csv", index=False)
    print(table[["lóbulo", "volumen_ml", "laa950", "perc15", "damage_mean", "damage_burden"]].round(2).to_string(index=False))

    plot_coronal(hu, lobes, damage, analysed, (sz, sy, sx), table, args.out / f"{name}_map.png", name)


def plot_coronal(hu, lobes, damage, analysed, spacing, table, path, name) -> None:
    sz, sy, sx = spacing
    # Interpola el daño entre los cortes analizados para la reconstrucción coronal.
    dense = np.stack([damage[z] for z in analysed])
    filled = np.where(np.isnan(dense), 0, dense)
    weight = (~np.isnan(dense)).astype(np.float32)
    factor = (hu.shape[0] / len(analysed), 1, 1)
    num, den = ndimage.zoom(filled, factor, order=1), ndimage.zoom(weight, factor, order=1)
    volume = np.where((den > 0.5) & (lobes > 0), num / np.maximum(den, 1e-6), np.nan)

    heat = LinearSegmentedColormap.from_list(
        "damage", [(0.92, 0.41, 0.2, 0.0), (0.92, 0.41, 0.2, 0.55), (0.75, 0.05, 0.05, 0.9)])
    vmin, vmax = 0.3, 1.1  # misma escala que la galería de cortes
    lung_rows = np.flatnonzero((lobes > 0).any(axis=(0, 2)))
    picks = np.linspace(lung_rows[0], lung_rows[-1], 6)[1:-1].astype(int)

    fig, axes = plt.subplots(1, len(picks) + 1, figsize=(3.1 * (len(picks) + 1), 3.8),
                             constrained_layout=True, facecolor="#fcfcfb",
                             gridspec_kw={"width_ratios": [1] * len(picks) + [1.15]})
    aspect = sz / sx
    for ax, y in zip(axes, picks):
        ax.imshow(np.clip((hu[::-1, y] + 1100) / 1000, 0, 1), cmap="gray", aspect=aspect, vmin=0, vmax=1)
        ax.imshow(volume[::-1, y], cmap=heat, vmin=vmin, vmax=vmax, aspect=aspect)
        ax.set_xticks([]), ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
    axes[0].set_title(f"{name}: mapa de daño, cortes coronales (ant. a post.)", loc="left", fontsize=10, fontweight="bold")

    ax = axes[-1]
    ax.barh(table["lóbulo"][::-1], table["damage_burden"][::-1], color="#2a78d6", height=0.6)
    for lobe, value in zip(table["lóbulo"], table["damage_burden"]):
        ax.text(value + 0.8, lobe, f"{value:.0f} %", va="center", fontsize=9, color="#0b0b0b")
    ax.set_title("Parénquima con textura de enfisema", loc="left", fontsize=10, fontweight="bold")
    ax.set_xlabel("% del lóbulo", color="#52514e")
    ax.set_xlim(0, max(table["damage_burden"].max() * 1.25, 10))
    ax.set_facecolor("#fcfcfb")
    ax.tick_params(colors="#898781")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.savefig(path, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
