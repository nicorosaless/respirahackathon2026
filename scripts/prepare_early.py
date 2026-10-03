"""Tabla clínica de la cohorte EARLY lista para el análisis.

Lee el CSV del reto, añade las variables derivadas y los grupos, y pone
etiquetas legibles a sexo y tabaco. Escribe una tabla por sujeto que se queda
en MareNostrum, junto a las salidas.

    python scripts/prepare_early.py <tabla.csv> --manifest outputs/manifiesto.csv --out outputs/clinica_early.csv

Con `--manifest` reparte además a los sujetos con TC en desarrollo y reserva.
La reserva (1 de cada 5, estratificada por caso) no se usa para ajustar ni para
elegir nada: se evalúa una sola vez, al final.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from maps.early import derive
from maps.tables import read_table


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("table", type=Path)
    parser.add_argument("--out", type=Path, default=Path("outputs/clinica_early.csv"))
    parser.add_argument("--manifest", type=Path, help="lista de sujetos con TC; activa el reparto desarrollo/reserva")
    parser.add_argument("--semilla", type=int, default=2026)
    args = parser.parse_args()

    t = derive(read_table(args.table))
    t["sexo"] = t["sexo_num_v1"].map({1: "hombre", 2: "mujer"})
    t["fuma"] = t["actual_fuma_num_v1"].map({0: "no fuma", 1: "fuma"})
    t["enfisema_visual"] = t["enfisema_SI_v1"].map({0.0: "no", 1.0: "sí"})
    if args.manifest is not None:
        with_ct = set(pd.read_csv(args.manifest, dtype=str)["subject_id"])
        t["particion"] = "sin TC"
        rng = np.random.default_rng(args.semilla)
        for _, rows in t[t["random_id"].astype(str).isin(with_ct)].groupby("caso_v1"):
            order = rng.permutation(rows.index.to_numpy())
            held = max(1, round(len(order) / 5))
            t.loc[order[:held], "particion"] = "reserva"
            t.loc[order[held:], "particion"] = "desarrollo"
        print(pd.crosstab(t["particion"], t["caso_v1"]).to_string())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    t.to_csv(args.out, index=False)
    print(f"{len(t)} sujetos y {t.shape[1]} columnas en {args.out}")
    print(t["grupo"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()
