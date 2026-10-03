import numpy as np
from scipy import ndimage

from maps.geometry import bounding_box, distance_to


def test_distance_matches_the_reference_transform_with_anisotropic_voxels():
    rng = np.random.default_rng(0)
    target = rng.random((20, 24, 28)) < 0.02
    spacing = (1.25, 0.7, 0.7)

    ours = distance_to(target, spacing)
    reference = ndimage.distance_transform_edt(~target, sampling=spacing)

    assert np.allclose(ours, reference, atol=1e-3)


def test_bounding_box_keeps_the_mask_and_respects_the_volume_edge():
    mask = np.zeros((10, 10, 10), dtype=bool)
    mask[0:2, 4:6, 7:9] = True

    box = bounding_box(mask, margin=3)

    assert mask[box].sum() == mask.sum()
    assert box == (slice(0, 5), slice(1, 9), slice(4, 10))
