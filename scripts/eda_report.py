"""EDA de la cohorte: figuras agregadas y una página privada con ejemplos.

Escribe en `<out>/`:
  figuras/*.png   distribuciones por grupo y confusores de adquisición (agregados)
  perfiles.csv    medianas por grupo (agregado)
  index.html      cuatro sujetos de ejemplo con su TC y su ficha, y la galería de TC

`index.html` enseña datos de sujetos: se queda en MareNostrum y se ve por túnel.
Por la salida estándar solo salen agregados.

    python scripts/eda_report.py <tabla.csv> outputs/eda
"""

from __future__ import annotations

import argparse
import html
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from maps.early import GROUPS, derive
from maps.tables import read_table

COLOURS = dict(zip(GROUPS, ["#2a78d6", "#1baf7a", "#eda100", "#eb6834"]))
SHORT = dict(zip(GROUPS, ["control\nsin criterios", "control\nsíntomas o\nDLCO baja", "control\ncon enfisema", "EPOC"]))
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#898781", "#e1e0d9", "#fcfcfb"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9.5, "text.color": INK, "axes.edgecolor": "#c3c2b7",
    "axes.labelcolor": "#52514e", "axes.facecolor": SURFACE, "figure.facecolor": SURFACE,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.titleweight": "bold", "axes.titlesize": 10.5, "axes.titlelocation": "left",
})

CLINICAL = [("fev1_fvc_post_v1", "FEV1/FVC tras broncodilatador"), ("FEV1pp_GLI_v1", "FEV1, % del predicho"),
            ("DLCO_v1", "DLCO, % del predicho"), ("CAT_v1", "CAT (síntomas, 0 a 40)"),
            ("paquetes_año_v1", "Paquetes-año"), ("FENO_v1", "FENO, ppb")]
CT = [("perc15", "Perc15, HU"), ("laa950", "%LAA-950"), ("volumen_l", "Volumen pulmonar, L")]
CARD = [("grupo", "Grupo"), ("edat_round_v1", "Edad"), ("sexo", "Sexo"), ("altura_v1", "Talla, cm"),
        ("imc_v1", "IMC"), ("fuma", "Fuma en la visita 1"), ("paquetes_año_v1", "Paquetes-año"),
        ("fev1_fvc_post_v1", "FEV1/FVC posbroncodilatador"), ("FEV1pp_GLI_v1", "FEV1, % predicho"),
        ("DLCO_v1", "DLCO, % predicho"), ("CAT_v1", "CAT"), ("mmrc_num_v1", "mMRC"), ("FENO_v1", "FENO"),
        ("enfisema", "Enfisema visual"), ("kvp", "kVp de la TC"), ("modelo", "Escáner"),
        ("perc15", "Perc15 (pulmón aproximado), HU"), ("laa950", "%LAA-950 (pulmón aproximado)"),
        ("volumen_l", "Volumen pulmonar en la TC, L"), ("caida_fev1_ml_ano", "Caída del FEV1, mL/año")]


def boxes(ax, table: pd.DataFrame, column: str, by: str, levels: list, colours: list[str], labels: list[str]) -> None:
    """Cajas sin puntos sueltos: la figura no enseña valores de ningún sujeto."""
    groups = [table.loc[table[by] == level, column].dropna().to_numpy(dtype=float) for level in levels]
    shown = [(g, c, f"{label}\nn={len(g)}") for g, c, label in zip(groups, colours, labels) if len(g) >= 5]
    if not shown:
        return
    parts = ax.boxplot([g for g, _, _ in shown], patch_artist=True, showfliers=False, widths=0.55,
                       medianprops={"color": INK, "linewidth": 1.8}, whiskerprops={"color": "#52514e"},
                       capprops={"color": "#52514e"})
    for patch, (_, colour, _) in zip(parts["boxes"], shown):
        patch.set(facecolor=colour, edgecolor=SURFACE, linewidth=1.5)
    ax.set_xticks(range(1, len(shown) + 1), [label for _, _, label in shown], fontsize=8)
    ax.grid(axis="x", visible=False)


def figure_clinical(t: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(13, 7.2), constrained_layout=True)
    for ax, (column, title) in zip(axes.ravel(), CLINICAL):
        boxes(ax, t, column, "grupo", list(GROUPS), [COLOURS[g] for g in GROUPS], [SHORT[g] for g in GROUPS])
        ax.set_title(title)
    axes[0, 0].axhline(0.7, color=INK, linewidth=1, linestyle=(0, (3, 3)))
    axes[0, 2].axhline(80, color=INK, linewidth=1, linestyle=(0, (3, 3)))
    axes[1, 0].axhline(10, color=INK, linewidth=1, linestyle=(0, (3, 3)))
    fig.suptitle("Visita 1 por grupo. Caja: P25 a P75; raya: mediana; bigotes: hasta 1,5 veces el rango intercuartílico. "
                 "Línea discontinua: umbral clínico.", x=0.01, ha="left", fontsize=9, color="#52514e")
    fig.savefig(path, dpi=140)
    plt.close(fig)


def figure_confounders(t: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(len(CT), 3, figsize=(13, 9.6), constrained_layout=True)
    splits = [("kvp", "kVp", sorted(t["kvp"].dropna().unique()), lambda v: f"{int(v)} kVp"),
              ("modelo", "escáner", list(t["modelo"].value_counts().index), str),
              ("fuma", "tabaco", ["no fuma", "fuma"], str)]
    for row, (column, title) in enumerate(CT):
        for ax, (by, by_title, levels, fmt) in zip(axes[row], splits):
            boxes(ax, t, column, by, levels, ["#2a78d6"] * len(levels), [fmt(level) for level in levels])
            ax.set_title(f"{title} · por {by_title}")
    fig.suptitle("TC basal, pulmón aproximado por umbral. Si la adquisición no importara, las cajas de cada panel estarían alineadas.",
                 x=0.01, ha="left", fontsize=9, color="#52514e")
    fig.savefig(path, dpi=140)
    plt.close(fig)


def figure_ct_by_group(t: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.9), constrained_layout=True)
    for ax, (column, title) in zip(axes, CT):
        boxes(ax, t, column, "grupo", list(GROUPS), [COLOURS[g] for g in GROUPS], [SHORT[g] for g in GROUPS])
        ax.set_title(title)
    fig.suptitle("TC basal por grupo, sin ajustar por adquisición ni por talla.", x=0.01, ha="left", fontsize=9, color="#52514e")
    fig.savefig(path, dpi=140)
    plt.close(fig)


def figure_follow_up(t: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6), constrained_layout=True)
    for level, colour, label in ((0, "#2a78d6", "control"), (1, "#eb6834", "EPOC")):
        values = t.loc[t["caso_v1"] == level, "caida_fev1_ml_ano"].dropna()
        axes[0].hist(values, bins=np.arange(-240, 241, 40), color=colour, alpha=0.75, label=f"{label} (n={len(values)})",
                     edgecolor=SURFACE, linewidth=1.2)
    axes[0].axvline(0, color=INK, linewidth=1)
    axes[0].set_title("Caída del FEV1 entre visitas, mL por año")
    axes[0].set_xlabel("positivo es perder función")
    axes[0].legend(frameon=False)
    axes[1].hist(t["anos_seguimiento"].dropna(), bins=np.arange(2.5, 10.1, 0.5), color="#2a78d6", edgecolor=SURFACE, linewidth=1.2)
    axes[1].set_title("Años entre la visita 1 y la visita 2")
    for ax in axes:
        ax.set_ylabel("sujetos")
        ax.grid(axis="x", visible=False)
    fig.savefig(path, dpi=140)
    plt.close(fig)


def profiles(t: pd.DataFrame) -> pd.DataFrame:
    """Medianas por grupo: el retrato agregado de cada tipo de sujeto."""
    rows = {}
    for group, part in t.groupby("grupo", observed=True):
        rows[group] = {
            "n": len(part), "con TC útil": int(part["perc15"].notna().sum()),
            "edad": part["edat_round_v1"].median(), "% mujeres": 100 * (part["sexo_num_v1"] == 2).mean(),
            "% fuma": 100 * part["actual_fuma_num_v1"].mean(), "paquetes-año": part["paquetes_año_v1"].median(),
            "FEV1/FVC": part["fev1_fvc_post_v1"].median(), "FEV1 %pred": part["FEV1pp_GLI_v1"].median(),
            "DLCO %pred": part["DLCO_v1"].median(), "CAT": part["CAT_v1"].median(), "mMRC": part["mmrc_num_v1"].median(),
            "FENO": part["FENO_v1"].median(), "Perc15 HU": part["perc15"].median(), "%LAA-950": part["laa950"].median(),
            "volumen TC L": part["volumen_l"].median(), "caída FEV1 mL/año": part["caida_fev1_ml_ano"].median(),
        }
    return pd.DataFrame(rows).T


def fmt(value) -> str:
    if isinstance(value, (float, np.floating)):
        return "sin dato" if np.isnan(value) else f"{value:.2f}".rstrip("0").rstrip(".").replace(".", ",")
    return html.escape(str(value))


def page(t: pd.DataFrame, out: Path) -> int:
    """Página con cuatro sujetos de ejemplo, uno por grupo, y la galería de todas las TC."""
    cards = []
    with_ct = t[t["perc15"].notna()]
    for group in GROUPS:
        part = with_ct[with_ct["grupo"] == group].sort_values("perc15")
        if part.empty:
            continue
        row = part.iloc[len(part) // 2]  # el de densidad mediana de su grupo, no el más llamativo
        rows = "".join(f"<tr><th>{html.escape(label)}</th><td>{fmt(row[column])}</td></tr>" for column, label in CARD)
        cards.append(f'<section><h2>Sujeto {html.escape(str(row["subject_id"]))} · {html.escape(group)}</h2>'
                     f'<div class="pair"><img src="previews/{row["subject_id"]}.png"><table>{rows}</table></div></section>')
    gallery = "".join(f'<figure><img loading="lazy" src="previews/{sid}.png"><figcaption>{sid} · {html.escape(str(g))}</figcaption></figure>'
                      for sid, g in zip(with_ct["subject_id"], with_ct["grupo"]))
    figures = "".join(f'<img class="wide" src="figuras/{name}.png">' for name in ("clinica_por_grupo", "tc_por_grupo", "tc_confusores", "seguimiento"))
    (out / "index.html").write_text(f"""<!doctype html><html lang="es"><meta charset="utf-8"><title>EDA del reto MAPS</title>
<style>body{{font:15px/1.45 Helvetica,Arial,sans-serif;margin:24px auto;max-width:1280px;padding:0 20px;color:#000}}
h1{{font-size:26px}}h2{{font-size:18px;border-left:6px solid #f0ab00;padding-left:10px;margin-top:34px}}
.pair{{display:grid;grid-template-columns:minmax(0,3fr) minmax(0,2fr);gap:20px;align-items:start}}img{{max-width:100%}}
table{{border-collapse:collapse;width:100%;font-size:14px}}th{{text-align:left;font-weight:400;color:#3c4242}}
th,td{{border-bottom:1px solid #d2d2d2;padding:4px 8px 4px 0}}td{{font-weight:700;text-align:right}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}figure{{margin:0}}figcaption{{font-size:12px;color:#3c4242}}
.wide{{width:100%;margin:8px 0 18px}}.warn{{background:#000;color:#fff;padding:8px 12px}}</style>
<p class="warn">Datos de sujetos del reto. Esta página vive en MareNostrum y se ve por túnel. No la descargues ni la captures fuera del equipo.</p>
<h1>EDA del reto MAPS</h1><p>Cuatro sujetos de ejemplo, uno por grupo: el de densidad pulmonar mediana de su grupo. El contorno dorado es el pulmón aproximado por umbral.</p>
{''.join(cards)}<h2>Figuras agregadas</h2>{figures}<h2>Todas las TC basales ({len(with_ct)})</h2><div class="grid">{gallery}</div></html>""")
    return len(cards)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("clinical", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    (args.out / "figuras").mkdir(parents=True, exist_ok=True)

    t = derive(read_table(args.clinical))
    t["subject_id"] = t["random_id"].astype(str)
    quick = pd.read_csv(args.out / "quicklook.csv", dtype={"subject_id": str})
    if "error" in quick:
        print("TC con error:", int(quick["error"].notna().sum()))
        quick = quick[quick["error"].isna()]
    t = t.merge(quick, on="subject_id", how="left")
    t["sexo"] = t["sexo_num_v1"].map({1: "hombre", 2: "mujer"})
    t["fuma"] = t["actual_fuma_num_v1"].map({0: "no fuma", 1: "fuma"})
    t["enfisema"] = t["enfisema_SI_v1"].map({0.0: "no", 1.0: "sí"}).fillna("sin dato")
    t["kvp"] = pd.to_numeric(t["kvp"], errors="coerce")

    figure_clinical(t, args.out / "figuras" / "clinica_por_grupo.png")
    figure_ct_by_group(t, args.out / "figuras" / "tc_por_grupo.png")
    figure_confounders(t, args.out / "figuras" / "tc_confusores.png")
    figure_follow_up(t, args.out / "figuras" / "seguimiento.png")
    table = profiles(t)
    table.to_csv(args.out / "perfiles.csv")
    pd.set_option("display.width", 250, "display.max_columns", 30)
    print(table.round(2).T.to_string())
    print("\nmedianas de la TC por kVp:\n", t.groupby("kvp")[["perc15", "laa950", "sd", "volumen_l"]].median().round(2).join(t.groupby("kvp").size().rename("n")).to_string())
    print("\nkVp por grupo:\n", pd.crosstab(t["grupo"], t["kvp"]).to_string())
    print("\nmodelo por kVp:\n", pd.crosstab(t["modelo"], t["kvp"]).to_string())
    print(f"\npágina con {page(t, args.out)} ejemplos en {args.out / 'index.html'}")


if __name__ == "__main__":
    main()
