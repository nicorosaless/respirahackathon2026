import numpy as np
import pytest

from maps.vessels import small_vessel_mask, vessel_metrics


def _two_vessels(spacing) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Un vaso grueso (radio 4 mm) y uno fino (radio 0,8 mm), paralelos, de 60 mm."""
    shape = tuple(int(round(mm / s)) for mm, s in zip((70, 40, 40), spacing))
    z, y, x = np.meshgrid(*[np.arange(n) * s for n, s in zip(shape, spacing)], indexing="ij")
    inside = (z > 5) & (z < 65)
    thick = inside & (np.hypot(y - 12, x - 20) <= 4.0)
    thin = inside & (np.hypot(y - 30, x - 20) <= 0.8)
    return thick | thin, thick, thin


@pytest.mark.parametrize("spacing", [(0.5, 0.5, 0.5), (1.0, 0.5, 0.5)])
def test_only_the_thin_vessel_counts_as_small(spacing):
    vessels, thick, thin = _two_vessels(spacing)

    small = small_vessel_mask(vessels, spacing)

    assert np.count_nonzero(small & thin) / np.count_nonzero(thin) > 0.95
    assert np.count_nonzero(small & thick) / np.count_nonzero(thick) < 0.1


def test_small_vessel_fraction_is_reported_per_region():
    spacing = (0.5, 0.5, 0.5)
    vessels, thick, thin = _two_vessels(spacing)
    small = small_vessel_mask(vessels, spacing)
    thin_side = np.zeros_like(vessels)
    thin_side[:, 44:, :] = True  # y > 22 mm: solo contiene el vaso fino

    whole = vessel_metrics(vessels, small, np.ones_like(vessels), spacing)
    part = vessel_metrics(vessels, small, thin_side, spacing)

    assert whole["vasos_bv5_tbv"] == pytest.approx(thin.sum() / vessels.sum(), abs=0.03)
    assert part["vasos_bv5_tbv"] > 0.95
