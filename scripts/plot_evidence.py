"""La figura de evidencia de la demo, dibujada con los agregados de `check_score.py`.

No lee datos de sujetos: solo `docs/figuras/comprobaciones.json`, que trae
cuantiles por clase, acuerdos entre reconstrucciones y AUC por estrato, y
`reserva.json`, con el resultado en los sujetos de reserva.

    python scripts/plot_evidence.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIGURES = Path(__file__).resolve().parents[1] / "docs" / "figuras"
INK, SOFT, RULE = "#111111", "#5a6060", "#d2d2d2"
BLUE, ORANGE, AQUA, GOLD = "#2a78d6", "#eb6834", "#1baf7a", "#f0ab00"
CLASS_COLOURS = {"control": AQUA, "pre-EPOC": GOLD, "EPOC": ORANGE}
# Las medidas que nombra el reto y las dos de la puntuación, de menos a más estable.
STABILITY = ["laa950", "perc15", "via_pi10_mm", "via_grosor_pared_mm", "via_disanapsia", "via_longitud_mm", "laa950_smooth"]
LABELS = {"laa950": "%LAA-950 clásico", "perc15": "Perc15", "via_pi10_mm": "Pi10, aproximado", "via_grosor_pared_mm": "Grosor de pared, estimado",
          "via_disanapsia": "Disanapsia, aproximada", "via_longitud_mm": "Longitud de vía aérea", "laa950_smooth": "%LAA-950 suavizado"}
STRATA = {("kvp", "80"): "80 kVp", ("kvp", "100"): "100 kVp", ("kvp", "120"): "120 kVp", ("sexo", "hombre"): "Hombres",
          ("sexo", "mujer"): "Mujeres", ("fuma", "fuma"): "Fuman", ("fuma", "no fuma"): "No fuman"}


def clean(ax: plt.Axes, title: str, subtitle: str) -> None:
    ax.set_title(title, loc="left", fontsize=13, fontweight="bold", color=INK, pad=24)
    ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=9.5, color=SOFT, va="bottom")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(RULE)
    ax.tick_params(colors=SOFT, labelsize=9.5, length=0)


def main() -> None:
    checks = json.loads((FIGURES / "comprobaciones.json").read_text())
    figure, (left, middle, right) = plt.subplots(1, 3, figsize=(16.5, 4.9), gridspec_kw={"width_ratios": [1, 1.15, 1.25]})

    # 1. La puntuación en cada clase, a partir de sus cuantiles.
    for position, (name, q) in enumerate(checks["por_clase"].items()):
        colour = CLASS_COLOURS[name]
        left.plot([position, position], [q["p10"], q["p90"]], color=colour, linewidth=1.6, solid_capstyle="butt")
        left.add_patch(plt.Rectangle((position - 0.28, q["p25"]), 0.56, q["p75"] - q["p25"], facecolor=colour, alpha=0.3,
                                     edgecolor=colour, linewidth=1.6))
        left.plot([position - 0.28, position + 0.28], [q["p50"], q["p50"]], color=colour, linewidth=2.6)
    threshold = checks["umbral_dano"]
    left.axhline(threshold, color=INK, linewidth=1, linestyle=(0, (4, 3)))
    left.text(-0.55, threshold + 2.0, f"umbral\n{threshold:.2f}".replace(".", ","), fontsize=9, color=INK, va="bottom")
    left.plot([-0.4, -0.4], [threshold, threshold + 1.95], color=INK, linewidth=0.6)
    left.set_xticks(range(len(checks["por_clase"])), [f"{name}\nn = {q['n']}" for name, q in checks["por_clase"].items()])
    left.set_xlim(-0.6, len(checks["por_clase"]) - 0.4)
    left.set_ylabel("Puntuación de daño (z)", color=SOFT, fontsize=10)
    clean(left, "La puntuación sube de control a EPOC", "Mediana, cuartiles y percentiles 10 a 90")

    # 2. Acuerdo entre las dos reconstrucciones de la misma adquisición.
    by_measure = {row["medida"]: row for row in checks["por_medida"]}
    names = [LABELS[m] for m in STABILITY] + ["Puntuación de daño"]
    values = [by_measure[m]["icc_kernel"] for m in STABILITY] + [checks["otra_reconstruccion"]["icc"]]
    colours = [BLUE if by_measure[m]["en_la_puntuacion"] else RULE for m in STABILITY] + [INK]
    bars = middle.barh(names, values, color=colours, height=0.62)
    for bar, value in zip(bars, values):
        middle.text(value + 0.015, bar.get_y() + bar.get_height() / 2, f"{value:.2f}".replace(".", ","), va="center",
                    fontsize=9.5, color=INK)
    middle.set_xlim(0, 1.12)
    middle.set_xticks([0, 0.5, 1], ["0", "0,5", "1"])
    middle.set_xlabel("Acuerdo entre kernels (ICC)", color=SOFT, fontsize=10)
    clean(middle, "Casi no cambia con la reconstrucción", "Misma adquisición, dos kernels. En azul, lo que entra en la puntuación")

    # 3. Separa EPOC de control dentro de cada estrato.
    rows = [("Todos", checks["separa_epoc"])]
    rows += [(STRATA[(s["variable"], s["nivel"])], s) for s in checks["por_estrato"] if (s["variable"], s["nivel"]) in STRATA]
    rows += [("Otro kernel", checks["otra_reconstruccion"]["separa_epoc"])]
    # En naranja, lo que no es de los mismos sujetos con los que se ajustó.
    nested = FIGURES / "validacion_anidada.json"
    if nested.exists():
        current = next(r for r in json.loads(nested.read_text())["resultados"]
                       if r["medida"] == "via_longitud_mm" and r["referencia"] == "todos los controles")
        rows += [("Fuera de muestra", {"auc": current["auc"], "ic95": [current["auc"], current["auc"]], "n": checks["sujetos"]})]
    reserve = FIGURES / "reserva.json"
    if reserve.exists():
        rows += [("Reserva, 15 no vistos", json.loads(reserve.read_text())["separa_epoc"])]
    for position, (name, s) in enumerate(reversed(rows)):
        colour = ORANGE if name.startswith(("Reserva", "Fuera")) else INK if name in ("Todos", "Otro kernel") else BLUE
        right.plot(s["ic95"], [position, position], color=colour, linewidth=1.6)
        right.plot(s["auc"], position, "o", color=colour, markersize=7)
        right.text(1.03, position, f"{s['auc']:.2f}".replace(".", ",") + f"  (n = {s['n']})", va="center", fontsize=9.5, color=INK)
    right.axvline(0.5, color=RULE, linewidth=1)
    right.text(0.51, -0.45, "azar", fontsize=9, color=SOFT)
    right.set_yticks(range(len(rows)), [name for name, _ in reversed(rows)])
    right.set_xlim(0.4, 1.3)
    right.set_xticks([0.5, 0.75, 1.0], ["0,5", "0,75", "1"])
    right.set_xlabel("AUC para EPOC, con IC del 95 %", color=SOFT, fontsize=10)
    clean(right, "Separa la EPOC en cada subgrupo", "Los 80 sujetos. En naranja, fuera de muestra")

    figure.tight_layout(w_pad=3)
    figure.savefig(FIGURES / "evidencia.png", dpi=200, facecolor="white")
    print(FIGURES / "evidencia.png")


if __name__ == "__main__":
    main()
