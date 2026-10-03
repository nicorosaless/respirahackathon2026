import numpy as np
import pytest
import torch

from maps.damage import ReferenceBank, knn_distance


def _bank() -> ReferenceBank:
    feats = torch.tensor([[0.0, 0.0], [0.0, 1.0], [10.0, 10.0], [10.0, 11.0]])
    return ReferenceBank(feats, np.array(["a", "a", "b", "b"]))


def test_patch_near_reference_scores_lower_than_far_patch():
    queries = torch.tensor([[0.0, 0.5], [5.0, 5.0]])
    near, far = knn_distance(queries, _bank(), k=1)
    assert near < far


def test_excluding_a_subject_removes_its_own_patches_from_the_reference():
    query = torch.tensor([[0.0, 0.0]])
    with_self = knn_distance(query, _bank(), k=1)[0]
    without_self = knn_distance(query, _bank(), exclude_subject="a", k=1)[0]
    assert with_self == pytest.approx(0.0)
    assert without_self == pytest.approx(np.hypot(10, 10))


def test_bank_smaller_than_k_is_rejected():
    with pytest.raises(ValueError, match="al menos"):
        knn_distance(torch.zeros(1, 2), _bank(), exclude_subject="a", k=3)
