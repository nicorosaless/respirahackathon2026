"""Recalcula las medidas de todos los sujetos a partir de las máscaras ya guardadas.

Cambiar una medida no exige volver a segmentar: la segmentación (GPU, un minuto
por TC) quedó en `masks.npz`. Esto relee la TC, aplica `region_table` con el
código actual y escribe una cohorte nueva. En un nodo de CPU son unos minutos.

    python scripts/remeasure.py outputs/manifiesto.csv --masks outputs/cohorte --out outputs/cohorte_v2 --workers 28
"""

from __future__ import annotations

import argparse
import json
import shutil
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

from maps.anatomy import Anatomy
from maps.archive import series_folder
from maps.ct import read_image, to_hu
from maps.features import region_table


def process(job: tuple[str, str, str, str, str]) -> str:
    subject, source, series_uid, masks_root, out_root = job
    saved = Path(masks_root) / "sujetos" / subject
    target = Path(out_root) / "sujetos" / subject
    try:
        masks = np.load(saved / "masks.npz")
        anatomy = Anatomy(masks["lobes"], masks["airway"], masks["airway_wall"], masks["arteries"], masks["veins"])
        with series_folder(source) as folder:
            hu, spacing = to_hu(read_image(folder, series_uid or None))
        if hu.shape != anatomy.lobes.shape:
            raise ValueError(f"la TC mide {hu.shape} y las máscaras {anatomy.lobes.shape}: no son la misma serie")
        # Misma forma no basta: las máscaras se guardaron con el espaciado de la serie que se segmentó.
        saved_spacing = json.loads((saved / "meta.json").read_text())["espaciado_mm"]
        if not np.allclose(spacing, saved_spacing, atol=1e-3):
            raise ValueError(f"la TC tiene espaciado {spacing} y las máscaras {saved_spacing}: no son la misma serie")
        table = region_table(hu, anatomy, spacing)
        table.insert(0, "subject_id", subject)
        target.mkdir(parents=True, exist_ok=True)
        table.to_csv(target / "features.csv", index=False)
        shutil.copy(saved / "meta.json", target / "meta.json")
        return ""
    except Exception as error:  # un sujeto que falla no debe tirar a los demás
        return f"{subject}: {type(error).__name__}: {error}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--masks", type=Path, required=True, help="cohorte con las máscaras guardadas")
    parser.add_argument("--out", type=Path, required=True, help="cohorte nueva con las medidas recalculadas")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    manifest = pd.read_csv(args.manifest, dtype=str).fillna("")
    jobs = [(row.subject_id, row.carpeta, row.serie_uid, str(args.masks), str(args.out)) for row in manifest.itertuples()]
    with Pool(args.workers) as pool:
        errors = [e for e in pool.map(process, jobs, chunksize=1) if e]
    print(f"{len(jobs) - len(errors)} sujetos recalculados en {args.out}, {len(errors)} con error")
    for error in errors:
        print("  ", error)


if __name__ == "__main__":
    main()
