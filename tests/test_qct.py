import numpy as np
import pytest

from maps.qct import densitometry


def test_laa950_counts_only_lung_voxels_below_threshold():
    hu = np.full((8, 8), -850.0)
    hu[:4] = -980.0  # mitad superior enfisematosa
    hu[0, 0] = 500.0  # hueso fuera de la máscara
    lung = np.ones_like(hu, dtype=bool)
    lung[0, 0] = False

    out = densitometry(hu, lung)

    assert out["laa950"] == pytest.approx(100 * 31 / 63)
    assert out["laa910"] == pytest.approx(100 * 31 / 63)
    assert out["perc15"] == pytest.approx(-980.0)


def test_empty_lung_mask_is_rejected():
    with pytest.raises(ValueError, match="vacía"):
        densitometry(np.zeros((4, 4)), np.zeros((4, 4), dtype=bool))


def test_clustered_low_attenuation_scores_higher_than_scattered():
    from maps.qct import clustering

    rng = np.random.default_rng(0)
    region = np.ones((40, 40, 40), dtype=bool)
    scattered = rng.random(region.shape) < 0.05
    focus = np.zeros_like(region)
    focus[5:20, 5:20, 5:19] = True  # un foco con el mismo 5 % de vóxeles

    assert clustering(scattered, region) < 0.05
    assert clustering(focus, region) > 0.8


def test_mass_tells_air_from_tissue_at_equal_volume():
    from maps.qct import volume_and_mass

    region = np.ones((10, 10, 10), dtype=bool)
    normal = volume_and_mass(np.full(region.shape, -850.0), region, (1.0, 1.0, 1.0))
    emphysema = volume_and_mass(np.full(region.shape, -950.0), region, (1.0, 1.0, 1.0))

    assert normal["volumen_ml"] == emphysema["volumen_ml"] == pytest.approx(1.0)
    assert normal["masa_g"] == pytest.approx(0.15)
    assert emphysema["masa_g"] == pytest.approx(0.05)


def test_smoothing_blurs_the_same_millimetres_whatever_the_voxel_size():
    from maps.qct import smooth_hu

    def edge_width_mm(step_mm: float) -> float:
        z = np.arange(0, 60, step_mm)
        hu = np.where(z < 30, -1000.0, 0.0)[:, None, None] * np.ones((1, 8, 8))
        profile = smooth_hu(hu, (step_mm, 1.0, 1.0))[:, 4, 4]
        fine = np.interp(np.arange(0, 60, 0.05), z, profile)
        return 0.05 * float(np.count_nonzero((fine > -900) & (fine < -100)))  # del 10 al 90 % del salto

    assert edge_width_mm(1.25) == pytest.approx(edge_width_mm(0.625), rel=0.15)


def test_noise_is_read_from_the_air_deep_inside_the_trachea():
    from maps.qct import air_noise

    rng = np.random.default_rng(0)
    z, y, x = np.mgrid[:40, :40, :40]
    lumen = (y - 20) ** 2 + (x - 20) ** 2 <= 8**2  # tráquea de 8 mm de radio
    hu = np.where(lumen, -1000.0, -50.0) + rng.normal(0, 25, lumen.shape)

    assert air_noise(hu, lumen, (1.0, 1.0, 1.0)) == pytest.approx(25, rel=0.15)
    thin = (y - 20) ** 2 + (x - 20) ** 2 <= 2**2
    assert np.isnan(air_noise(hu, thin, (1.0, 1.0, 1.0)))  # sin aire lejos de la pared no hay dónde medir
