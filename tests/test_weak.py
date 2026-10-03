import numpy as np
import pytest
import torch

from maps.weak import DISEASE_LIKE, fit_patch_model


def _patches(n_reference: int, n_diseased: int, seed: int) -> tuple[torch.Tensor, np.ndarray]:
    rng = np.random.default_rng(seed)
    reference = rng.normal(0.0, 1.0, (n_reference, 8))
    diseased = rng.normal(0.0, 1.0, (n_diseased, 8))
    diseased[:, 0] += 4.0  # la enfermedad desplaza una sola dirección del embedding
    labels = np.r_[np.zeros(n_reference, dtype=bool), np.ones(n_diseased, dtype=bool)]
    return torch.from_numpy(np.vstack([reference, diseased])).float(), labels


def test_unseen_diseased_patches_score_above_unseen_reference_patches():
    model = fit_patch_model(*_patches(300, 300, seed=0))
    features, labels = _patches(200, 200, seed=1)

    scores = model.score(features)

    assert np.mean(scores[labels] > DISEASE_LIKE) > 0.9
    assert np.mean(scores[~labels] < DISEASE_LIKE) > 0.9


def test_class_imbalance_does_not_move_the_decision_threshold():
    model = fit_patch_model(*_patches(3000, 100, seed=0))
    features, labels = _patches(200, 200, seed=1)

    scores = model.score(features)

    assert np.mean(scores[labels] > DISEASE_LIKE) > 0.9
    assert np.mean(scores[~labels] < DISEASE_LIKE) > 0.9


def test_a_single_group_cannot_be_fitted():
    features, _ = _patches(50, 0, seed=0)
    with pytest.raises(ValueError, match="referencia y parches de enfermedad"):
        fit_patch_model(features, np.zeros(50, dtype=bool))
