"""Qué TC hay de verdad en el inventario: cuál sirve por sujeto y con qué protocolo.

Lee el CSV de `inventory.py` y resume en agregados. Sirve para decidir la regla
con la que `make_manifest.py` elige una serie por sujeto.

    python scripts/explore_inventory.py outputs/inventario.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

HARD_KERNELS = ["BONEPLUS", "BONE", "LUNG", "DETAIL"]


def counts(series: pd.Series, top: int = 20) -> dict:
    return dict(series.value_counts().head(top))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("inventory", type=Path)
    args = parser.parse_args()
    pd.set_option("display.width", 230, "display.max_rows", 200)

    t = pd.read_csv(args.inventory, dtype=str).fillna("")
    t["cortes"] = t["cortes"].astype(int)
    t["grosor"] = pd.to_numeric(t["grosor_mm"], errors="coerce")
    t["protocolo_norm"] = t["protocolo"].str.lower().str.replace(r"\s+", " ", regex=True)
    axial = t[(t["modalidad"] == "CT") & (t["cortes"] >= 50)
              & t["tipo_imagen"].str.contains("ORIGINAL") & t["tipo_imagen"].str.contains("AXIAL")]
    print(f"series axiales originales con 50+ cortes: {len(axial)} en {axial['sujeto'].nunique()} sujetos")
    print("protocolos:", counts(axial["protocolo_norm"]))
    print("descripciones:", counts(axial["serie_descripcion"].str.lower(), 30))

    chest = axial[axial["protocolo_norm"].str.contains("torax|tórax") & (axial["contraste"] == "")]
    thin = chest[chest["grosor"] <= 1.25]
    standard = thin[thin["kernel"] == "STANDARD"]
    hard = thin[thin["kernel"].isin(HARD_KERNELS)]
    everyone = set(t["sujeto"])
    print(f"\nsujetos con TC fina de tórax sin contraste: {thin['sujeto'].nunique()} de {len(everyone)}")
    print(f"  kernel STANDARD: {standard['sujeto'].nunique()} | kernel duro: {hard['sujeto'].nunique()} | "
          f"los dos: {len(set(standard['sujeto']) & set(hard['sujeto']))}")
    print("  solo kernel duro:", sorted(set(hard["sujeto"]) - set(standard["sujeto"]), key=int))
    print("  sin ninguna fina de tórax:", sorted(everyone - set(thin["sujeto"]), key=int))
    without = t[t["sujeto"].isin(everyone - set(thin["sujeto"])) & (t["modalidad"] == "CT") & (t["cortes"] >= 50)]
    print("  lo que tienen esos sujetos:", counts((without["protocolo_norm"] + " | " + without["kernel"] + " | "
                                                    + without["grosor_mm"] + " | cte=" + without["contraste"]), 12))

    first = standard.sort_values(["fecha", "cortes"], ascending=[True, False]).drop_duplicates("sujeto")
    print("\nfechas distintas con serie STANDARD fina por sujeto:",
          dict(standard.groupby("sujeto")["fecha"].nunique().value_counts().sort_index()))
    print("de la primera TC STANDARD fina de cada sujeto:")
    print("  año:", dict(first["fecha"].str[:4].value_counts().sort_index()))
    for column in ("modelo", "kvp", "grosor_mm", "protocolo_norm", "posicion"):
        print(f"  {column}:", counts(first[column]))
    print("  cortes:", first["cortes"].describe()[["min", "25%", "50%", "75%", "max"]].round(0).to_dict())
    pixel = first["pixel_mm"].str.split("\\", regex=False).str[0].astype(float)
    print("  píxel en mm:", pixel.describe()[["min", "50%", "max"]].round(2).to_dict())

    paired = axial[axial["protocolo_norm"].str.contains("insp") | axial["serie_descripcion"].str.contains("esp|exp", case=False)]
    print(f"\ninspiración y espiración: {len(paired)} series en {paired['sujeto'].nunique()} sujetos")
    print("  descripciones:", counts(paired["serie_descripcion"]))


if __name__ == "__main__":
    main()
