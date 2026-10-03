"""Experimento 2: mapas de daño en los 115 cortes HRCT, dejando fuera un sujeto cada vez.

Compara dos formas de convertir los embeddings de la ResNet en un mapa:

  normativo  distancia de cada parche a un banco de parches de cortes sin
             enfisema. No usa ninguna etiqueta de enfermedad.
  débil      modelo lineal de parches entrenado con cortes sin enfisema frente
             a cortes con enfisema leve o mayor. Los cortes de enfisema mínimo
             no entran nunca en el entrenamiento: son el análogo de la EPOC
             precoz y solo se usan para evaluar.

Guarda una tabla por corte, los mapas y el modelo de parches entrenado con
todos los sujetos, que es el que usa `run_volume.py`.

    uv run python scripts/exp_slices.py --pretraining radimagenet
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from maps.backbone import PatchEncoder
from maps.ct import read_tiff_hu
from maps.damage import ReferenceBank, knn_distance
from maps.emphysema_db import slice_table
from maps.lungs import pick_device, segment
from maps.pipeline import embed_slice
from maps.qct import densitometry
from maps.weak import DISEASE_LIKE, fit_patch_model

ROOT = Path(__file__).resolve().parents[1]
BANK_CELLS_PER_SLICE = 400
TRAIN_CELLS_PER_SLICE = 600
ESTABLISHED_SEVERITY = 2  # leve o mayor
PIXEL_MM = 0.78  # resolución en plano de la base de enfisema


def load_slices(table: pd.DataFrame, cache: Path) -> tuple[np.ndarray, np.ndarray]:
    """HU y máscara pulmonar de cada corte; la segmentación se guarda porque es lo más lento."""
    if cache.exists():
        saved = np.load(cache)
        return saved["hu"].astype(np.float32), saved["lung"]
    hu = np.stack([read_tiff_hu(path) for path in table["path"]])
    # Corte a corte: no son contiguos, así que el posproceso 3D de lungmask no aplica.
    lung = np.stack([segment(h[None])[0] > 0 for h in hu])
    np.savez_compressed(cache, hu=hu.astype(np.int16), lung=lung)
    return hu, lung


def sample_cells(embeddings, rows: np.ndarray, per_slice: int, rng) -> tuple[torch.Tensor, np.ndarray]:
    """Submuestra de celdas de los cortes `rows`, con el índice de corte de cada una."""
    feats, owner = [], []
    for i in rows:
        n = len(embeddings[i].features)
        pick = rng.choice(n, min(per_slice, n), replace=False)
        feats.append(embeddings[i].features[pick].float())
        owner.append(np.full(len(pick), i))
    return torch.cat(feats), np.concatenate(owner)


def summarise(prefix: str, score: np.ndarray, burden_above: float | None = None) -> dict[str, float]:
    out = {
        f"{prefix}_mean": float(score.mean()),
        f"{prefix}_p95": float(np.percentile(score, 95)),
        f"{prefix}_sd": float(score.std()),
    }
    if burden_above is not None:
        out[f"{prefix}_burden"] = 100.0 * float(np.mean(score > burden_above))
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pretraining", choices=["imagenet", "radimagenet"], default="radimagenet")
    parser.add_argument("--scale", type=float, default=2.0)
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "emphysema")
    parser.add_argument("--out", type=Path, default=ROOT / "outputs" / "slices")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    table = slice_table(args.data)
    severity, subjects = table["severity"].to_numpy(), table["subject"].to_numpy()
    torch.set_num_threads(8)
    rng = np.random.default_rng(0)

    hus, lungs = load_slices(table, args.out / "lungs.npz")
    encoder = PatchEncoder(args.pretraining).to(pick_device())
    start = time.time()
    embeddings = [embed_slice(encoder, hu, lung, scale=args.scale) for hu, lung in zip(hus, lungs)]
    print(f"{len(table)} cortes, backbone {args.pretraining}: embeddings en {time.time() - start:.0f} s, "
          f"{np.median([len(e.features) for e in embeddings]):.0f} celdas por corte")

    # Normativo: banco de cortes sin enfisema.
    bank_feats, owner = sample_cells(embeddings, np.flatnonzero(severity == 0), BANK_CELLS_PER_SLICE, rng)
    bank = ReferenceBank(bank_feats, subjects[owner])

    # Débil: sin enfisema frente a enfisema establecido; el grado mínimo queda fuera.
    train_rows = np.flatnonzero((severity == 0) | (severity >= ESTABLISHED_SEVERITY))
    train_feats, owner = sample_cells(embeddings, train_rows, TRAIN_CELLS_PER_SLICE, rng)
    train_diseased, train_subjects = severity[owner] > 0, subjects[owner]

    start = time.time()
    rows = [dict() for _ in range(len(table))]
    normative_maps, weak_maps = [None] * len(table), [None] * len(table)
    for subject in np.unique(subjects):
        keep = torch.from_numpy(train_subjects != subject)
        model = fit_patch_model(train_feats[keep], train_diseased[keep.numpy()])
        for i in np.flatnonzero(subjects == subject):
            emb, shape = embeddings[i], hus[i].shape
            feats = emb.features.float()
            distance = knn_distance(feats, bank, exclude_subject=subject)
            likeness = model.score(feats)
            rows[i] = {**summarise("normative", distance), **summarise("weak", likeness, DISEASE_LIKE)}
            normative_maps[i] = emb.to_map(distance, shape)
            weak_maps[i] = emb.to_map(likeness, shape)
    print(f"mapas fuera de muestra en {time.time() - start:.0f} s")

    qct = pd.DataFrame([densitometry(hu, lung) for hu, lung in zip(hus, lungs)])
    result = pd.concat([table.drop(columns="path"), qct, pd.DataFrame(rows)], axis=1)
    result.to_csv(args.out / f"slices_{args.pretraining}.csv", index=False)
    np.savez_compressed(
        args.out / f"maps_{args.pretraining}.npz",
        normative=np.stack(normative_maps).astype(np.float32),
        weak=np.stack(weak_maps).astype(np.float32),
    )

    final = fit_patch_model(train_feats, train_diseased)
    torch.save(
        {"model": final, "pretraining": args.pretraining, "scale": args.scale, "pixel_mm": PIXEL_MM},
        args.out.parent / f"patch_model_{args.pretraining}.pt",
    )
    print(result.groupby("severity")[["laa950", "perc15", "normative_mean", "weak_mean", "weak_burden"]].mean().round(2))


if __name__ == "__main__":
    main()
