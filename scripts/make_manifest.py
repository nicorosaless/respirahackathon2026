"""Del inventario de series a la lista de TC que procesar: una serie por sujeto.

Regla por defecto, pensada para la cohorte del reto: TC axial original de tórax,
sin contraste, de corte fino. Entre las que cumplen se prefiere el kernel
STANDARD, luego la fecha más antigua (la TC basal) y luego la de más cortes.
Los sujetos sin ninguna serie válida se listan y quedan fuera.

    python scripts/make_manifest.py outputs/inventario.csv --out outputs/manifiesto.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("inventory", type=Path)
    parser.add_argument("--out", type=Path, default=Path("outputs/manifiesto.csv"))
    parser.add_argument("--min-cortes", type=int, default=100)
    parser.add_argument("--max-grosor", type=float, default=1.25, help="grosor de corte máximo en mm")
    parser.add_argument("--protocolo", default="torax|tórax|chest|thorax", help="expresión regular; vacío para no filtrar")
    parser.add_argument("--kernel-preferido", default="STANDARD")
    parser.add_argument("--con-contraste", action="store_true", help="admite también series con contraste")
    args = parser.parse_args()

    table = pd.read_csv(args.inventory, dtype=str).fillna("")
    everyone = set(table["sujeto"])
    table["cortes"] = table["cortes"].astype(int)
    table["grosor"] = pd.to_numeric(table["grosor_mm"], errors="coerce")
    keep = (table["cortes"] >= args.min_cortes) & (table["grosor"] <= args.max_grosor)
    for column, needed in (("modalidad", "CT"), ("tipo_imagen", "ORIGINAL"), ("tipo_imagen", "AXIAL")):
        if column in table:
            keep &= table[column].str.contains(needed) | (table[column] == "")
    if args.protocolo and "protocolo" in table and (table["protocolo"] != "").any():
        keep &= table["protocolo"].str.contains(args.protocolo, case=False, regex=True)
    if not args.con_contraste and "contraste" in table:
        keep &= table["contraste"] == ""
    table = table[keep]
    if table.empty:
        raise SystemExit("ninguna serie cumple los filtros")

    table["otro_kernel"] = table["kernel"] != args.kernel_preferido
    chosen = table.sort_values(["otro_kernel", "fecha", "cortes"], ascending=[True, True, False]).drop_duplicates("sujeto")
    chosen = chosen.sort_values("sujeto", key=lambda ids: ids.str.zfill(8))
    manifest = chosen.rename(columns={"sujeto": "subject_id"})[["subject_id", "carpeta", "serie_uid"]]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(args.out, index=False)

    missing = sorted(everyone - set(chosen["sujeto"]), key=lambda s: s.zfill(8))
    other = chosen.loc[chosen["otro_kernel"], "sujeto"].tolist()
    print(f"{len(manifest)} sujetos en {args.out}")
    print(f"sin serie válida ({len(missing)}): {missing}")
    print(f"con un kernel distinto de {args.kernel_preferido} ({len(other)}): {other}")
    for column in ("kernel", "kvp", "modelo", "grosor_mm"):
        if column in chosen:
            print(f"{column}: {dict(chosen[column].value_counts())}")


if __name__ == "__main__":
    main()
