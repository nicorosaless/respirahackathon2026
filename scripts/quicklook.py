"""Vistazo rápido a todas las TC del manifiesto, sin GPU ni modelos.

Para cada sujeto: lee la serie, separa el pulmón con un umbral y componentes
conexas, mide la densidad y guarda una imagen de control. Es un pulmón
aproximado (incluye la tráquea y deja fuera los vasos), suficiente para ver los
confusores de adquisición antes de tener la segmentación buena.

    python scripts/quicklook.py outputs/manifiesto.csv --out outputs/eda --workers 28
"""

from __future__ import annotations

import argparse
import json
from multiprocessing import Pool
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import ndimage

from maps.archive import series_folder
from maps.ct import read_image, to_hu
from maps.dicom_meta import read_header
from maps.qct import densitometry

AIR_BELOW_HU = -400
MIN_LUNG_ML = 300.0


def crude_lungs(hu: np.ndarray, spacing: tuple[float, float, float]) -> np.ndarray:
    """Aire dentro del cuerpo en bolsas grandes: los pulmones y la tráquea."""
    labels, _ = ndimage.label(hu < AIR_BELOW_HU)
    outside = np.unique(np.concatenate([labels[:, 0, :].ravel(), labels[:, -1, :].ravel(),
                                        labels[:, :, 0].ravel(), labels[:, :, -1].ravel()]))
    sizes = np.bincount(labels.ravel()) * float(np.prod(spacing)) / 1000.0
    sizes[outside] = 0.0
    sizes[0] = 0.0
    return np.isin(labels, np.flatnonzero(sizes >= MIN_LUNG_ML))


def preview(hu: np.ndarray, lung: np.ndarray, spacing: tuple[float, float, float], title: str, path: Path) -> None:
    z = int(np.argmax(lung.sum(axis=(1, 2))))
    y = int(np.argmax(lung.sum(axis=(0, 2))))
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.6), facecolor="black")
    panels = [(hu[z], lung[z], spacing[1] / spacing[2], "axial"),
              (hu[::-1, y], lung[::-1, y], spacing[0] / spacing[2], "coronal")]
    for ax, (image, mask, aspect, name) in zip(axes, panels):
        ax.imshow(image, cmap="gray", vmin=-1350, vmax=150, aspect=aspect)
        ax.contour(mask, levels=[0.5], colors="#f0ab00", linewidths=0.7)
        ax.set_title(f"{title} · {name}", color="white", fontsize=10, loc="left")
        ax.axis("off")
    fig.tight_layout(pad=0.4)
    fig.savefig(path, dpi=110, facecolor="black")
    plt.close(fig)


def process(job: tuple[str, str, str]) -> dict:
    subject, source, out = job
    out = Path(out)
    target = out / "quicklook" / f"{subject}.json"
    if target.exists():
        return json.loads(target.read_text())
    try:
        with series_folder(source) as folder:
            image = read_image(folder)
            first = next(p for p in sorted(folder.rglob("*")) if p.is_file())
            header = read_header(first)
        hu, spacing = to_hu(image)
        lung = crude_lungs(hu, spacing)
        if not lung.any():
            raise ValueError("no se encontró pulmón")
        row = {"subject_id": subject, "volumen_l": float(lung.sum()) * float(np.prod(spacing)) / 1e6,
               "cortes": int(hu.shape[0]), "grosor_real_mm": float(spacing[0]), "pixel_real_mm": float(spacing[2])}
        row |= densitometry(hu, lung)
        row |= {k: header.get(k, "") for k in ("kernel", "kvp", "modelo", "protocolo", "corriente_ma", "exposicion_mas", "fecha", "posicion")}
        preview(hu, lung, spacing, f"sujeto {subject}", out / "previews" / f"{subject}.png")
    except Exception as error:  # un sujeto que falla no debe tirar a los demás
        row = {"subject_id": subject, "error": f"{type(error).__name__}: {error}"}
    target.write_text(json.dumps(row))
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--out", type=Path, default=Path("outputs/eda"))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    for folder in ("quicklook", "previews"):
        (args.out / folder).mkdir(parents=True, exist_ok=True)

    manifest = pd.read_csv(args.manifest, dtype=str)
    jobs = [(row.subject_id, row.carpeta, str(args.out)) for row in manifest.itertuples()]
    with Pool(args.workers) as pool:
        rows = pool.map(process, jobs, chunksize=1)
    table = pd.DataFrame(rows)
    table.to_csv(args.out / "quicklook.csv", index=False)
    failed = table["error"].notna().sum() if "error" in table else 0
    print(f"{len(table) - failed} sujetos medidos, {failed} con error, en {args.out / 'quicklook.csv'}")


if __name__ == "__main__":
    main()
