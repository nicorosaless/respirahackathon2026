"""Procesa una TC: segmenta, mide por lóbulo y guarda tabla, vista previa y metadatos.

Es la unidad de trabajo del job array. Cada TC escribe solo en su carpeta, así
que se pueden lanzar cientos en paralelo.

    python scripts/extract_subject.py data/lidc/LIDC-IDRI-0002 --id LIDC-0002 --out outputs/cohorte

La TC puede ser una carpeta DICOM, un NIfTI o una serie dentro de un zip,
escrita como `sujeto.zip::carpeta/de/la/serie`.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from maps.anatomy import segment_anatomy
from maps.archive import series_folder
from maps.ct import read_image, to_hu
from maps.dicom_meta import read_header
from maps.features import coronal_preview, region_table
from maps.lungs import pick_device


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("volume", help="carpeta DICOM, fichero NIfTI o zip::carpeta")
    parser.add_argument("--id", required=True, help="identificador del sujeto en las tablas")
    parser.add_argument("--out", type=Path, required=True, help="directorio de la cohorte")
    parser.add_argument("--series-uid", help="serie concreta si la carpeta tiene varias")
    parser.add_argument("--force", action="store_true", help="recalcula aunque ya exista")
    parser.add_argument("--save-masks", action="store_true", help="guarda las máscaras para revisarlas")
    args = parser.parse_args()

    target = args.out / "sujetos" / args.id
    if (target / "features.csv").exists() and not args.force:
        print(f"{args.id}: ya procesado")
        return
    target.mkdir(parents=True, exist_ok=True)
    (args.out / "previews").mkdir(exist_ok=True)

    start = time.time()
    with series_folder(args.volume) as volume:
        image = read_image(volume, args.series_uid)
        header = {}
        if volume.is_dir():
            first = next((p for p in sorted(volume.rglob("*")) if p.is_file()), None)
            header = read_header(first) if first is not None else {}
    hu, spacing = to_hu(image)
    anatomy = segment_anatomy(image, device="gpu" if pick_device().type == "cuda" else "cpu")
    segmented = time.time()
    if args.save_masks:
        np.savez_compressed(target / "masks.npz", lobes=anatomy.lobes, airway=anatomy.airway,
                            airway_wall=anatomy.airway_wall, arteries=anatomy.arteries, veins=anatomy.veins)

    table = region_table(hu, anatomy, spacing)
    table.insert(0, "subject_id", args.id)
    table.to_csv(target / "features.csv", index=False)
    np.savez_compressed(args.out / "previews" / f"{args.id}.npz", **coronal_preview(hu, anatomy.lobes, spacing))

    meta = {"subject_id": args.id, "origen": args.volume, "forma": list(hu.shape),
            "espaciado_mm": [round(float(s), 4) for s in spacing],
            "segundos_segmentacion": round(segmented - start, 1),
            "segundos_medidas": round(time.time() - segmented, 1)} | header
    (target / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"{args.id}: {hu.shape}, segmentación {meta['segundos_segmentacion']} s, medidas {meta['segundos_medidas']} s")


if __name__ == "__main__":
    main()
