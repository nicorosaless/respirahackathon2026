"""Mapa de daño con etiquetas débiles: solo hace falta saber el grupo del sujeto.

Cada parche hereda la etiqueta de su sujeto o de su corte (referencia frente a
enfermedad establecida) y se ajusta un modelo lineal sobre los embeddings de la
ResNet. Aplicado a un sujeto nuevo da, por parche, cuánto se parece su tejido
al de la enfermedad establecida. Nadie tiene que dibujar lesiones.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch

DISEASE_LIKE = 0.5  # los objetivos del ajuste son 0 (referencia) y 1 (enfermedad)


@dataclass(frozen=True)
class PatchModel:
    mean: torch.Tensor
    scale: torch.Tensor
    weights: torch.Tensor
    bias: float

    def score(self, features: torch.Tensor) -> np.ndarray:
        """Por parche: cerca de 0 es tejido de referencia, cerca de 1 tejido como el enfermo."""
        z = (features.double() - self.mean) / self.scale
        return (z @ self.weights + self.bias).numpy()


def fit_patch_model(features: torch.Tensor, diseased: np.ndarray, *, ridge: float = 0.01) -> PatchModel:
    """Regresión ridge con las dos clases pesando lo mismo.

    `ridge` es la penalización por parche de entrenamiento, sobre embeddings
    estandarizados. El equilibrio de clases evita que el umbral 0.5 se desplace
    cuando hay muchos más parches de un grupo que del otro.
    """
    y = torch.as_tensor(np.asarray(diseased, dtype=np.float64))
    if y.min() == y.max():
        raise ValueError("hacen falta parches de referencia y parches de enfermedad")
    x = features.double()
    mean, scale = x.mean(0), x.std(0) + 1e-6
    x = torch.cat([(x - mean) / scale, torch.ones(len(x), 1, dtype=torch.double)], dim=1)
    weight = torch.where(y > 0, 0.5 / y.mean(), 0.5 / (1 - y.mean()))
    penalty = ridge * len(x) * torch.eye(x.shape[1], dtype=torch.double)
    penalty[-1, -1] = 0.0  # el sesgo no se penaliza
    xw = x * weight[:, None]
    beta = torch.linalg.solve(xw.T @ x + penalty, xw.T @ y)
    return PatchModel(mean, scale, beta[:-1], float(beta[-1]))
