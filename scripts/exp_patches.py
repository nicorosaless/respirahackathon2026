"""Experimento 1: ¿ve una ResNet preentrenada la textura del enfisema?

Sonda lineal sobre los 168 parches anotados (tejido normal, enfisema
centrolobulillar, enfisema paraseptal), validada dejando fuera un sujeto cada
vez. La referencia es una regresión sobre la densitometría del mismo parche.

    uv run python scripts/exp_patches.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import LeaveOneGroupOut, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from maps.backbone import PatchEncoder
from maps.ct import read_tiff_hu, to_rgb_windows
from maps.emphysema_db import PATTERN, patch_table
from maps.qct import densitometry

ROOT = Path(__file__).resolve().parents[1]
UPSCALE = 4


def embed_patches(encoder: PatchEncoder, patches: np.ndarray) -> np.ndarray:
    x = to_rgb_windows(patches)
    x = F.interpolate(x, scale_factor=UPSCALE, mode="bilinear", align_corners=False)
    return encoder(x).mean(dim=(2, 3)).numpy()


def loso_accuracy(x: np.ndarray, y: np.ndarray, groups: np.ndarray) -> tuple[float, np.ndarray]:
    model = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=5000))
    pred = cross_val_predict(model, x, y, groups=groups, cv=LeaveOneGroupOut())
    return float((pred == y).mean()), pred


def main() -> None:
    out = ROOT / "outputs" / "patches"
    out.mkdir(parents=True, exist_ok=True)
    table = patch_table(ROOT / "data" / "emphysema")
    patches = np.stack([read_tiff_hu(p) for p in table["path"]])
    y, groups = table["pattern"].to_numpy(), table["subject"].to_numpy()
    torch.set_num_threads(8)

    everything = np.ones(patches.shape[1:], dtype=bool)
    features = {"densitometría": pd.DataFrame([densitometry(p, everything) for p in patches]).to_numpy()}
    for pretraining in ("imagenet", "radimagenet"):
        features[f"resnet50-{pretraining}"] = embed_patches(PatchEncoder(pretraining), patches)

    results = {}
    for name, x in features.items():
        acc, pred = loso_accuracy(x, y, groups)
        confusion = pd.crosstab(
            pd.Series(y, name="real").map(PATTERN), pd.Series(pred, name="predicho").map(PATTERN)
        )
        results[name] = {"accuracy": acc, "confusion": confusion.to_dict()}
        print(f"\n{name}: accuracy LOSO = {acc:.3f} ({x.shape[1]} variables)\n{confusion}")
    (out / "patches.json").write_text(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
