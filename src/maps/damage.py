"""Mapa de daño sin etiquetas: distancia de cada parche al pulmón de referencia.

Idea (PatchCore): se guardan los embeddings de parches de pulmones sanos en un
banco de memoria. El daño de un parche nuevo es su distancia a los vecinos más
próximos del banco. No hace falta ninguna anotación de lesión, solo saber qué
sujetos sirven de referencia.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch


@dataclass(frozen=True)
class ReferenceBank:
    """Embeddings de parches de referencia y el sujeto del que sale cada uno."""

    features: torch.Tensor  # (n, d), float32
    subjects: np.ndarray  # (n,), id de sujeto por fila

    def __post_init__(self) -> None:
        if len(self.features) != len(self.subjects):
            raise ValueError("features y subjects deben tener la misma longitud")


def knn_distance(
    queries: torch.Tensor,
    bank: ReferenceBank,
    *,
    exclude_subject: str | None = None,
    k: int = 5,
    chunk: int = 4096,
) -> np.ndarray:
    """Distancia media a los `k` vecinos del banco para cada parche consultado.

    `exclude_subject` retira del banco los parches de ese sujeto: sin eso, un
    sujeto de referencia se compararía consigo mismo y saldría siempre sano.
    """
    feats = bank.features
    if exclude_subject is not None:
        feats = feats[torch.from_numpy(bank.subjects != exclude_subject)]
    if len(feats) < k:
        raise ValueError(f"el banco tiene {len(feats)} parches, hacen falta al menos {k}")
    out = []
    for start in range(0, len(queries), chunk):
        d = torch.cdist(queries[start : start + chunk], feats)
        out.append(d.topk(k, dim=1, largest=False).values.mean(dim=1))
    return torch.cat(out).numpy()
