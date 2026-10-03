"""Comprueba que cada serie del manifiesto es un volumen completo.

Lee la posición de todos los cortes de cada serie. Una serie con huecos entre
cortes no es un volumen: SimpleITK la lee suponiendo paso uniforme y el
resultado tiene la geometría mal. Deja un CSV con una fila por sujeto.

    python scripts/check_series.py outputs/manifiesto.csv --out outputs/calidad_series.csv --workers 28
"""

from __future__ import annotations

import argparse
import io
import zipfile
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd
import pydicom

from maps.dicom_meta import ZIP_SEPARATOR

MAX_GAP_RATIO = 1.5  # un hueco mayor que vez y media el paso habitual es un corte que falta


def slice_positions(source: str, series_uid: str = "") -> np.ndarray:
    """Posición de cada corte de la serie a lo largo de la normal al corte, en mm."""
    if ZIP_SEPARATOR in source:
        archive_path, folder = source.split(ZIP_SEPARATOR, 1)
        with zipfile.ZipFile(archive_path) as archive:
            names = [n for n in archive.namelist() if n.startswith(folder.rstrip("/") + "/") and not n.endswith("/")]
            headers = [pydicom.dcmread(io.BytesIO(archive.read(n)), stop_before_pixels=True, force=True) for n in names]
    else:
        headers = [pydicom.dcmread(p, stop_before_pixels=True, force=True) for p in sorted(Path(source).rglob("*")) if p.is_file()]
    headers = [h for h in headers if "ImagePositionPatient" in h and (not series_uid or str(h.get("SeriesInstanceUID", "")) == series_uid)]
    positions = []
    for header in headers:
        orientation = np.array(header.get("ImageOrientationPatient", [1, 0, 0, 0, 1, 0]), dtype=float)
        normal = np.cross(orientation[:3], orientation[3:])
        positions.append(float(np.dot(normal, np.array(header.ImagePositionPatient, dtype=float))))
    return np.sort(positions)


def check(job: tuple[str, str, str]) -> dict:
    subject, source, series_uid = job
    z = slice_positions(source, series_uid)
    steps = np.diff(z)
    if len(steps) == 0 or not np.isfinite(steps).all() or np.median(steps) <= 0:
        # Con menos de dos posiciones distintas no hay serie que comprobar.
        return {"subject_id": subject, "cortes": len(z), "paso_mm": float("nan"), "huecos": 0, "hueco_max_mm": 0.0,
                "falta_mm": 0.0, "completa": False}
    step = float(np.median(steps))
    gaps = steps[steps > MAX_GAP_RATIO * step]
    return {"subject_id": subject, "cortes": len(z), "paso_mm": round(step, 3),
            "huecos": len(gaps), "hueco_max_mm": round(float(gaps.max()), 2) if len(gaps) else 0.0,
            "falta_mm": round(float((gaps - step).sum()), 1), "completa": len(gaps) == 0}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--out", type=Path, default=Path("outputs/calidad_series.csv"))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    manifest = pd.read_csv(args.manifest, dtype=str).fillna("")
    uids = manifest["serie_uid"] if "serie_uid" in manifest else [""] * len(manifest)
    with Pool(args.workers) as pool:
        rows = pool.map(check, list(zip(manifest["subject_id"], manifest["carpeta"], uids)), chunksize=1)
    table = pd.DataFrame(rows)
    table.to_csv(args.out, index=False)
    bad = table[~table["completa"]]
    print(f"{len(table) - len(bad)} series completas y {len(bad)} con huecos, en {args.out}")
    if len(bad):
        print(bad.drop(columns="completa").to_string(index=False))


if __name__ == "__main__":
    main()
