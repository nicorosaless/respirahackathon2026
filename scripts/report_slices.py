"""Métricas y figuras del experimento de cortes.

Lee la tabla y los mapas que deja `exp_slices.py` y compara los dos mapas de
daño de la ResNet con la densitometría clásica, sobre todo en el rango que
importa para EPOC precoz: sin enfisema frente a enfisema mínimo.

    uv run python scripts/report_slices.py --pretraining radimagenet
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

from maps.emphysema_db import SEVERITY
from maps.fusion import bootstrap_auc, compare_blocks
from maps.qct import EMPHYSEMA_HU

ROOT = Path(__file__).resolve().parents[1]

DEEP, CLASSIC, FUSED, NORMATIVE = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#898781", "#e1e0d9", "#fcfcfb"
QCT_COLUMNS = ["laa950", "laa910", "laa950_smooth", "perc15", "haa", "mld", "sd", "skew", "kurtosis"]
WEAK_COLUMNS = ["weak_mean", "weak_p95", "weak_sd", "weak_burden"]
NORMATIVE_COLUMNS = ["normative_mean", "normative_p95", "normative_sd"]
# Signo fijado de antemano: +1 si más valor significa más daño.
SINGLE_SCORES = {
    "weak_mean": ("ResNet débil, media", +1, DEEP),
    "weak_burden": ("ResNet débil, % de pulmón", +1, DEEP),
    "normative_mean": ("ResNet normativo, media", +1, NORMATIVE),
    "normative_p95": ("ResNet normativo, p95", +1, NORMATIVE),
    "laa950": ("%LAA-950", +1, CLASSIC),
    "laa950_smooth": ("%LAA-950 suavizado", +1, CLASSIC),
    "laa910": ("%LAA-910", +1, CLASSIC),
    "perc15": ("Perc15", -1, CLASSIC),
}
TASKS = {
    "sin enfisema vs mínimo": lambda s: s <= 1,
    "sin enfisema vs cualquier grado": lambda s: s >= 0,
}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "text.color": INK,
    "axes.edgecolor": "#c3c2b7", "axes.labelcolor": "#52514e", "axes.facecolor": SURFACE,
    "figure.facecolor": SURFACE, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True, "axes.titleweight": "bold",
    "axes.titlesize": 11, "axes.titlelocation": "left",
})


def single_score_metrics(table: pd.DataFrame) -> pd.DataFrame:
    severity, groups = table["severity"].to_numpy(), table["subject"].to_numpy()
    rows = []
    for column, (label, sign, _) in SINGLE_SCORES.items():
        score = sign * table[column].to_numpy()
        row = {"variable": label, "spearman_severidad": float(spearmanr(score, severity).statistic)}
        for task, keep in TASKS.items():
            mask = keep(severity)
            auc, lo, hi = bootstrap_auc((severity[mask] > 0).astype(int), score[mask], groups[mask])
            row[f"auc {task}"] = auc
            row[f"ic95 {task}"] = f"{lo:.2f}-{hi:.2f}"
        rows.append(row)
    return pd.DataFrame(rows)


def paired_differences(table: pd.DataFrame, n: int = 2000) -> pd.DataFrame:
    """Diferencia de AUC entre la ResNet débil y cada índice clásico, remuestreando los mismos sujetos."""
    severity, groups = table["severity"].to_numpy(), table["subject"].to_numpy()
    rows = []
    for task, keep in TASKS.items():
        mask = keep(severity)
        y, g = (severity[mask] > 0).astype(int), groups[mask]
        by_subject = [np.flatnonzero(g == s) for s in np.unique(g)]
        deep = table.loc[mask, "weak_mean"].to_numpy()
        for column in ("perc15", "laa910", "laa950"):
            label, sign, _ = SINGLE_SCORES[column]
            classic = sign * table.loc[mask, column].to_numpy()
            rng = np.random.default_rng(0)
            diffs = []
            for _ in range(n):
                pick = np.concatenate([by_subject[i] for i in rng.integers(0, len(by_subject), len(by_subject))])
                if len(np.unique(y[pick])) == 2:
                    diffs.append(roc_auc_score(y[pick], deep[pick]) - roc_auc_score(y[pick], classic[pick]))
            lo, hi = np.percentile(diffs, [2.5, 97.5])
            rows.append({"tarea": task, "comparación": f"ResNet débil - {label}",
                         "diferencia_auc": roc_auc_score(y, deep) - roc_auc_score(y, classic),
                         "ic95_inf": lo, "ic95_sup": hi})
    return pd.DataFrame(rows)


def block_metrics(table: pd.DataFrame) -> pd.DataFrame:
    severity, groups = table["severity"].to_numpy(), table["subject"].to_numpy()
    frames = []
    for task, keep in TASKS.items():
        mask = keep(severity)
        y = (severity[mask] > 0).astype(int)
        normative = compare_blocks({"ResNet normativo": table.loc[mask, NORMATIVE_COLUMNS]}, y, groups[mask])
        blocks = {"densitometría": table.loc[mask, QCT_COLUMNS], "ResNet débil": table.loc[mask, WEAK_COLUMNS]}
        result = pd.concat([normative, compare_blocks(blocks, y, groups[mask])], ignore_index=True)
        result.insert(0, "tarea", task)
        frames.append(result)
    return pd.concat(frames, ignore_index=True)


def plot_severity(table: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 3.9), constrained_layout=True)
    rng = np.random.default_rng(0)
    panels = [
        ("weak_mean", "ResNet débil: parecido medio a tejido enfermo", DEEP),
        ("perc15", "Perc15 (HU), densitometría clásica", CLASSIC),
    ]
    for ax, (column, title, color) in zip(axes, panels):
        for level in range(len(SEVERITY)):
            values = table.loc[table["severity"] == level, column].to_numpy()
            if len(values) == 0:
                continue
            ax.scatter(level + rng.uniform(-0.16, 0.16, len(values)), values, s=22, color=color,
                       alpha=0.75, edgecolor=SURFACE, linewidth=0.8, zorder=3)
            ax.hlines(np.median(values), level - 0.28, level + 0.28, color=INK, linewidth=2, zorder=4)
        ax.set_xticks(range(len(SEVERITY)), [f"{s}\n(n={int((table['severity'] == i).sum())})"
                                              for i, s in enumerate(SEVERITY)])
        ax.set_title(title)
        ax.grid(axis="x", visible=False)
    fig.suptitle("Cada punto es un corte; la raya negra es la mediana por grado de severidad",
                 x=0.01, ha="left", fontsize=9, color="#52514e")
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_auc(blocks: pd.DataFrame, singles: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 3.4), constrained_layout=True, sharex=True)
    colors = {"densitometría": CLASSIC, "ResNet débil": DEEP, "densitometría+ResNet débil": FUSED,
              "ResNet normativo": NORMATIVE}
    for ax, task in zip(axes, TASKS):
        rows = blocks[blocks["tarea"] == task].iloc[::-1].reset_index(drop=True)
        for i, row in rows.iterrows():
            ax.hlines(i, row["ic95_inf"], row["ic95_sup"], color=colors[row["bloque"]], linewidth=2)
            ax.scatter(row["auc"], i, s=70, color=colors[row["bloque"]], edgecolor=SURFACE, linewidth=2, zorder=3)
            ax.text(row["ic95_sup"] + 0.012, i, f"{row['auc']:.2f}", va="center", color=INK, fontsize=10)
        ax.set_yticks(range(len(rows)), rows["bloque"])
        ax.axvline(0.5, color=MUTED, linewidth=1, linestyle=(0, (2, 2)))
        ax.set_xlim(0.4, 1.06)
        ax.set_ylim(-0.6, len(rows) - 0.4)
        ax.set_title(task.capitalize())
        ax.set_xlabel("AUC fuera de muestra, IC 95 %")
        ax.grid(axis="y", visible=False)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _alpha_ramp(rgb: tuple[float, float, float], dark: tuple[float, float, float]) -> LinearSegmentedColormap:
    """Un solo tono: transparente donde no hay daño, opaco y oscuro donde hay más."""
    return LinearSegmentedColormap.from_list("damage", [(*rgb, 0.0), (*rgb, 0.55), (*dark, 0.9)])


def _square_crop(lung: np.ndarray, margin: int = 14) -> tuple[slice, slice]:
    rows, cols = np.flatnonzero(lung.any(axis=1)), np.flatnonzero(lung.any(axis=0))
    side = max(rows[-1] - rows[0], cols[-1] - cols[0]) + 2 * margin
    top = int(np.clip((rows[0] + rows[-1] - side) // 2, 0, lung.shape[0] - side))
    left = int(np.clip((cols[0] + cols[-1] - side) // 2, 0, lung.shape[1] - side))
    return slice(top, top + side), slice(left, left + side)


def plot_gallery(table: pd.DataFrame, hu_all: np.ndarray, lung_all: np.ndarray,
                 maps: dict[str, np.ndarray], path: Path) -> None:
    """Un corte por grado de severidad: TC, densitometría clásica y los dos mapas de la ResNet."""
    picks = []
    for level in range(len(SEVERITY)):
        rows = table[table["severity"] == level]
        if len(rows):
            # el corte mediano del grado, no el más vistoso
            order = rows["weak_mean"].sort_values()
            picks.append(order.index[len(order) // 2])
    normal = maps["normative"][table["severity"].to_numpy() == 0]
    normative_range = (np.nanpercentile(normal, 50), np.nanpercentile(maps["normative"], 99.5))
    orange = _alpha_ramp((0.93, 0.63, 0.0), (0.75, 0.42, 0.0))
    red = _alpha_ramp((0.92, 0.41, 0.2), (0.75, 0.05, 0.05))
    laa_colour = np.array([0.16, 0.47, 0.84, 0.9])

    fig, axes = plt.subplots(4, len(picks), figsize=(2.5 * len(picks), 10.6), constrained_layout=True)
    for column, index in enumerate(picks):
        hu, lung, row = hu_all[index], lung_all[index], table.loc[index]
        box = _square_crop(lung)
        base = np.clip((hu + 1100) / 1000, 0, 1)[box]
        laa = np.zeros((*hu.shape, 4), dtype=np.float32)
        laa[(hu < EMPHYSEMA_HU) & lung] = laa_colour
        panels = [
            (SEVERITY[row.severity].capitalize(), None, None),
            (f"%LAA-950 = {row.laa950:.1f} · Perc15 = {row.perc15:.0f}", laa[box], None),
            (f"distancia media = {row.normative_mean:.1f}", maps["normative"][index][box], (orange, *normative_range)),
            (f"pulmón afectado = {row.weak_burden:.0f} %", maps["weak"][index][box], (red, 0.3, 1.1)),
        ]
        for ax, (title, layer, scale) in zip(axes[:, column], panels):
            ax.imshow(base, cmap="gray", vmin=0, vmax=1)
            if scale is not None:
                ax.imshow(layer, cmap=scale[0], vmin=scale[1], vmax=scale[2])
            elif layer is not None:
                ax.imshow(layer)
            ax.set_title(title, fontsize=9, fontweight="bold" if layer is None else "normal")
            ax.set_xticks([]), ax.set_yticks([])
            ax.grid(False)
            for spine in ax.spines.values():
                spine.set_visible(False)
    labels = ["TC, ventana de pulmón", "Clásico: vóxeles < -950 HU", "ResNet normativo (sin etiquetas)",
              "ResNet con etiquetas débiles"]
    for ax, label in zip(axes[:, 0], labels):
        ax.set_ylabel(label, fontsize=10, color=INK)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pretraining", choices=["imagenet", "radimagenet"], default="radimagenet")
    parser.add_argument("--out", type=Path, default=ROOT / "outputs" / "slices")
    args = parser.parse_args()

    table = pd.read_csv(args.out / f"slices_{args.pretraining}.csv")
    maps = dict(np.load(args.out / f"maps_{args.pretraining}.npz"))
    lungs = np.load(args.out / "lungs.npz")
    singles, blocks = single_score_metrics(table), block_metrics(table)
    pd.set_option("display.width", 200, "display.max_columns", 20)
    print(singles.round(3).to_string(index=False), "\n")
    print(blocks.round(3).to_string(index=False), "\n")
    differences = paired_differences(table)
    print(differences.round(3).to_string(index=False))
    (args.out / f"metrics_{args.pretraining}.json").write_text(json.dumps(
        {"variables": singles.to_dict("records"), "bloques": blocks.to_dict("records"),
         "diferencias": differences.to_dict("records")},
        indent=2, ensure_ascii=False))
    plot_severity(table, args.out / f"severity_{args.pretraining}.png")
    plot_auc(blocks, singles, args.out / f"auc_{args.pretraining}.png")
    plot_gallery(table, lungs["hu"].astype(np.float32), lungs["lung"], maps, args.out / f"gallery_{args.pretraining}.png")


if __name__ == "__main__":
    main()
