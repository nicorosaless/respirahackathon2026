"""Fichas para elegir el caso de la demo: los controles de desarrollo que la TC marca como dañados.

Para cada uno dibuja, a partir de las máscaras guardadas, el árbol bronquial
entero y los lóbulos, y escribe al lado sus números y la frase de su clase. Hay
que mirar que el árbol sea un árbol y que los lóbulos estén donde deben antes
de enseñarlo. Son datos de sujetos: la salida se queda en MareNostrum y se ve
por el portal.

    python scripts/qa_cases.py mn5/cohorte.early.toml --masks outputs/cohorte --out outputs/eda/casos
"""

from __future__ import annotations

import argparse
import html
import tomllib
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap

from maps.anatomy import LOBES
from maps.geometry import bounding_box
from maps.measures import MEASURES, WHOLE_LUNG

LOBE_COLOURS = ["#2a78d6", "#1baf7a", "#eda100", "#e87ba4", "#4a3aa7"]  # LSI, LII, LSD, LM, LID
AIRWAY = "#f0ab00"


def draw(masks: Path, spacing: tuple[float, float, float], out: Path) -> None:
    data = np.load(masks)
    box = bounding_box((data["lobes"] > 0) | data["airway"], margin=8)
    lobes, airway = data["lobes"][box], data["airway"][box].astype(bool)
    aspect = spacing[0] / spacing[2]
    fig, (left, right) = plt.subplots(1, 2, figsize=(9, 5), constrained_layout=True, facecolor="white")
    lung = (lobes > 0).any(axis=1)[::-1]
    left.imshow(np.where(lung, 0.85, 1.0), cmap="gray", vmin=0, vmax=1, aspect=aspect)
    left.imshow(np.where(airway.any(axis=1)[::-1], 1.0, np.nan), cmap=ListedColormap([AIRWAY]), vmin=0, vmax=1,
                aspect=aspect, interpolation="nearest")
    left.set_title("Árbol bronquial, proyección de frente", loc="left", fontsize=10, fontweight="bold")
    middle = lobes.shape[1] // 2
    right.imshow(np.ones_like(lobes[::-1, middle], dtype=float), cmap="gray", vmin=0, vmax=1, aspect=aspect)
    for label, colour in zip(LOBES, LOBE_COLOURS):
        right.imshow(np.where((lobes == label)[::-1, middle], 1.0, np.nan), cmap=ListedColormap([colour]), vmin=0, vmax=1,
                     aspect=aspect, alpha=0.7, interpolation="nearest")
    right.set_title("Lóbulos, corte coronal central", loc="left", fontsize=10, fontweight="bold")
    for ax in (left, right):
        ax.set_xticks([]), ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
    fig.savefig(out, dpi=110)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--masks", type=Path, required=True, help="cohorte procesada con --save-masks")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    config = tomllib.loads(args.config.read_text())
    cohort = Path(config["cohorte"])
    panel = config["puntuacion"]["medidas"]

    subjects = pd.read_csv(cohort / "subjects.csv", dtype={"subject_id": str}).set_index("subject_id")
    features = pd.read_csv(cohort / "features.csv", dtype={"subject_id": str})
    zscores = pd.read_csv(cohort / "zscores.csv", dtype={"subject_id": str})
    whole = {name: table[table["region"] == WHOLE_LUNG].set_index("subject_id") for name, table in (("valor", features), ("z", zscores))}
    rule = config["clasificacion"]
    chosen = subjects.query(rule["ajuste"]) if "ajuste" in rule else subjects
    chosen = chosen[(chosen[rule["caso"]] == 0) & (chosen["dano_tc"] == "sí")].sort_values("puntuacion_dano", ascending=False)

    args.out.mkdir(parents=True, exist_ok=True)
    cards = []
    for subject, row in chosen.iterrows():
        folder = args.masks / "sujetos" / subject
        if not (folder / "masks.npz").exists():
            continue
        spacing = tuple(float(v) for v in str(row["espaciado_mm"]).strip("()[] ").replace(",", " ").split())
        draw(folder / "masks.npz", spacing, args.out / f"{subject}.png")
        numbers = "".join(
            f"<li>{html.escape(MEASURES[m][0])}: {whole['valor'].loc[subject, m]:.3g} {html.escape(MEASURES[m][1])}, "
            f"z de {whole['z'].loc[subject, m]:+.1f}</li>" for m in panel)
        cards.append(
            f"<section><h2>Sujeto {html.escape(subject)}</h2><p><b>{html.escape(str(row['clase_maps']))}.</b> "
            f"{html.escape(str(row['clase_motivo']))}</p><ul><li>FEV1 de {row['FEV1pp_GLI_v1']:.0f} % del predicho</li>"
            f"{numbers}</ul><img src='{html.escape(subject)}.png' alt='Árbol bronquial y lóbulos'>"
            f"<p>En la app: <code>?paciente={html.escape(subject)}</code></p></section>")
    page = ("<!doctype html><html lang='es'><meta charset='utf-8'><title>Casos para la demo</title>"
            "<style>body{font:16px/1.5 Helvetica,Arial,sans-serif;max-width:980px;margin:24px auto;padding:0 20px}"
            "h2{border-left:6px solid #f0ab00;padding-left:10px;margin-top:2em}img{max-width:100%;border:1px solid #d2d2d2}</style>"
            "<h1>Casos para la demo</h1><p>Controles de desarrollo con daño en la TC, de mayor a menor puntuación. "
            "El z del pulmón entero va sin orientar: en la longitud de vía aérea, negativo es peor. "
            "Elegir uno con el árbol limpio y, mejor, con el FEV1 por encima del 80 %: así es pre-EPOC solo por la TC.</p>"
            + "".join(cards) + "</html>")
    (args.out / "index.html").write_text(page)
    print(f"{len(cards)} fichas en {args.out}")


if __name__ == "__main__":
    main()
