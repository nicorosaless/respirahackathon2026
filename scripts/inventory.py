"""Lo primero que hay que ejecutar sobre los datos: qué series de TC hay y con qué protocolo.

Recorre un directorio y deja un CSV con una fila por serie DICOM (kernel,
grosor, fabricante, dosis, número de cortes) y por NIfTI. De ahí salen la lista
de TC que procesar y los confusores de adquisición.

    python scripts/inventory.py <datos del reto> --out outputs/inventario.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from maps.dicom_meta import inventory


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--out", type=Path, default=Path("outputs/inventario.csv"))
    args = parser.parse_args()

    rows = inventory(args.root)
    for path in sorted(args.root.rglob("*.nii*")):
        rows.append({"carpeta": str(path), "serie_descripcion": "NIfTI", "cortes": -1})
    table = pd.DataFrame(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.out, index=False)
    print(f"{len(table)} series en {args.out}")
    if len(table):
        print(f"{table['sujeto'].nunique()} sujetos")
        for column in ("modalidad", "fabricante", "modelo", "kernel", "grosor_mm", "serie_descripcion"):
            if column in table:
                print(f"\n{table[column].value_counts(dropna=False).head(12).to_string()}")


if __name__ == "__main__":
    main()
