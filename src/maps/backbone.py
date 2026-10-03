"""ResNet-50 preentrenada usada como extractor denso de textura pulmonar."""

from __future__ import annotations

from typing import Literal

import torch
import torch.nn.functional as F
from torch import nn
from torchvision.models import ResNet50_Weights, resnet50

Pretraining = Literal["imagenet", "radimagenet"]

RADIMAGENET_REPO = "Lab-Rasool/RadImageNet"
RADIMAGENET_FILE = "ResNet50.pt"
# El checkpoint publicado es `nn.Sequential(*resnet50.children())` sin la capa fc.
_RADIMAGENET_MODULES = {"0": "conv1", "1": "bn1", "4": "layer1", "5": "layer2", "6": "layer3", "7": "layer4"}


def _radimagenet_resnet50() -> nn.Module:
    """ResNet-50 con pesos RadImageNet (1,35 M de imágenes de TC, RM y eco)."""
    from huggingface_hub import hf_hub_download

    path = hf_hub_download(RADIMAGENET_REPO, RADIMAGENET_FILE)
    released = torch.load(path, map_location="cpu", weights_only=True)
    state = {}
    for key, value in released.items():
        _, index, rest = key.split(".", 2)
        state[f"{_RADIMAGENET_MODULES[index]}.{rest}"] = value
    model = resnet50(weights=None)
    missing, unexpected = model.load_state_dict(state, strict=False)
    if unexpected or any(not k.startswith("fc.") for k in missing):
        raise RuntimeError(f"pesos RadImageNet no encajan: faltan {missing[:5]}, sobran {unexpected[:5]}")
    return model


class PatchEncoder(nn.Module):
    """Convierte una imagen en una rejilla de embeddings, uno por celda de 8 px.

    Concatena layer2 y layer3: layer2 conserva textura fina (enfisema
    centrolobulillar, paredes) y layer3 aporta contexto de mayor escala.
    """

    stride = 8
    dim = 512 + 1024

    def __init__(self, pretraining: Pretraining = "imagenet") -> None:
        super().__init__()
        if pretraining == "imagenet":
            net = resnet50(weights=ResNet50_Weights.IMAGENET1K_V2)
        elif pretraining == "radimagenet":
            net = _radimagenet_resnet50()
        else:
            raise ValueError(f"preentrenamiento desconocido: {pretraining}")
        self.stem = nn.Sequential(net.conv1, net.bn1, net.relu, net.maxpool)
        self.layer1, self.layer2, self.layer3 = net.layer1, net.layer2, net.layer3
        self.register_buffer("mean", torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1))
        self.register_buffer("std", torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1))
        self.eval().requires_grad_(False)

    @torch.inference_mode()
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """`x`: (B, 3, H, W) en [0, 1]. Devuelve (B, 1536, H/8, W/8)."""
        x = (x - self.mean) / self.std
        f2 = self.layer2(self.layer1(self.stem(x)))
        f3 = self.layer3(f2)
        f2 = F.avg_pool2d(f2, 3, stride=1, padding=1)
        f3 = F.avg_pool2d(f3, 3, stride=1, padding=1)
        f3 = F.interpolate(f3, size=f2.shape[-2:], mode="bilinear", align_corners=False)
        return torch.cat([f2, f3], dim=1)
