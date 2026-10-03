import numpy as np
import pytest

from maps.airways import airway_metrics


def _tube(mask: np.ndarray, start, end, radius_mm: float, spacing) -> None:
    """Pinta un cilindro entre dos puntos dados en mm."""
    grid = np.stack(np.meshgrid(*[np.arange(n) * s for n, s in zip(mask.shape, spacing)], indexing="ij"), axis=-1)
    start, end = np.array(start, float), np.array(end, float)
    axis = end - start
    t = np.clip(((grid - start) @ axis) / (axis @ axis), 0, 1)
    distance = np.linalg.norm(grid - (start + t[..., None] * axis), axis=-1)
    mask |= distance <= radius_mm


def _y_tree(spacing, radius_mm: float = 3.0, spur: bool = False) -> np.ndarray:
    """Tráquea de 40 mm que baja desde arriba y se divide en dos ramas de 30 mm.

    El eje 0 es z y crece hacia la cabeza, así que la tráquea ocupa los z altos.
    """
    shape = tuple(int(round(mm / s)) for mm, s in zip((90, 60, 80), spacing))
    mask = np.zeros(shape, dtype=bool)
    _tube(mask, (80, 30, 40), (40, 30, 40), radius_mm, spacing)
    _tube(mask, (40, 30, 40), (16, 30, 22), radius_mm, spacing)
    _tube(mask, (40, 30, 40), (16, 30, 58), radius_mm, spacing)
    if spur:
        _tube(mask, (60, 30, 40), (60, 30, 45.5), 1.0, spacing)  # un saliente de la pared, no una rama
    return mask


UNIT = (1.0, 1.0, 1.0)


def test_a_trachea_with_two_bronchi_has_three_branches_and_one_generation():
    out = airway_metrics(_y_tree(UNIT), UNIT, lung_volume_ml=5000)

    assert out["via_ramas"] == 3
    assert out["via_generaciones"] == 1
    assert out["via_calibre_central_mm"] == pytest.approx(6.0, abs=1.5)


def test_a_bump_on_the_wall_is_not_counted_as_a_branch_or_a_generation():
    out = airway_metrics(_y_tree(UNIT, spur=True), UNIT, lung_volume_ml=5000)

    assert out["via_ramas"] == 3
    assert out["via_generaciones"] == 1


def test_length_is_in_millimetres_whatever_the_voxel_size():
    fine = airway_metrics(_y_tree(UNIT), UNIT, lung_volume_ml=5000)
    coarse = airway_metrics(_y_tree((2.0, 1.0, 1.0)), (2.0, 1.0, 1.0), lung_volume_ml=5000)

    # 40 + 30 + 30 mm, menos lo que el esqueleto recorta en los extremos romos
    assert 80 < fine["via_longitud_mm"] < 110
    assert coarse["via_longitud_mm"] == pytest.approx(fine["via_longitud_mm"], rel=0.2)


def test_the_same_airways_in_a_bigger_lung_score_lower_dysanapsis():
    tree = _y_tree(UNIT)
    small_lung = airway_metrics(tree, UNIT, lung_volume_ml=4000)
    big_lung = airway_metrics(tree, UNIT, lung_volume_ml=7000)

    assert big_lung["via_disanapsia"] < small_lung["via_disanapsia"]
    assert small_lung["via_disanapsia"] == pytest.approx(small_lung["via_calibre_central_mm"] / 4_000_000 ** (1 / 3))


def test_wall_thickness_is_recovered_from_lumen_and_wall_masks():
    spacing = (0.5, 0.5, 0.5)
    lumen = _y_tree(spacing, radius_mm=2.0)
    wall = _y_tree(spacing, radius_mm=3.5) & ~lumen  # pared de 1,5 mm alrededor de una luz de 2 mm de radio

    out = airway_metrics(lumen, spacing, lung_volume_ml=5000, wall=wall)

    assert out["via_grosor_pared_mm"] == pytest.approx(1.5, abs=0.5)
    assert out["via_pared_pct"] == pytest.approx(100 * (3.5**2 - 2.0**2) / 3.5**2, abs=10)


def test_empty_mask_is_rejected():
    with pytest.raises(ValueError, match="vacía"):
        airway_metrics(np.zeros((4, 4, 4), dtype=bool), UNIT, lung_volume_ml=5000)


def test_branch_lengths_are_physical_when_slices_are_thicker_than_pixels():
    # Con cortes de 3 mm y píxeles de 1 mm, una rama vertical de 40 mm tiene tres veces menos vóxeles
    # que una horizontal igual de larga. Contar vóxeles por el espaciado medio las confundía.
    from maps.airways import build_tree
    from maps.geometry import distance_to

    spacing = (3.0, 1.0, 1.0)
    mask = np.zeros((30, 60, 90), dtype=bool)
    _tube(mask, (80, 30, 45), (40, 30, 45), 3.0, spacing)  # tráquea vertical, 40 mm
    _tube(mask, (40, 30, 45), (40, 30, 5), 3.0, spacing)   # dos bronquios horizontales, 40 mm cada uno
    _tube(mask, (40, 30, 45), (40, 30, 85), 3.0, spacing)

    tree = build_tree(mask, distance_to(~mask, spacing), spacing)
    lengths = np.sort(tree.length_mm[1:][tree.generation[1:] >= 0])

    assert len(lengths) == 3
    assert lengths == pytest.approx([37, 37, 37], abs=9)


def test_a_loose_fragment_above_the_trachea_does_not_become_the_root():
    tree = _y_tree(UNIT)
    tree[86:89, 29:31, 60:62] = True  # un trozo suelto de la segmentación, más arriba que la tráquea

    out = airway_metrics(tree, UNIT, lung_volume_ml=5000)

    assert out["via_ramas"] == 3
    assert out["via_generaciones"] == 1
    assert out["via_longitud_conectada_mm"] == pytest.approx(airway_metrics(_y_tree(UNIT), UNIT, 5000)["via_longitud_mm"], rel=0.05)


def test_length_is_split_between_fine_and_wide_airways_by_lumen_diameter():
    spacing = (0.5, 0.5, 0.5)
    shape = tuple(int(round(mm / s)) for mm, s in zip((90, 60, 80), spacing))
    mask = np.zeros(shape, dtype=bool)
    _tube(mask, (80, 30, 40), (40, 30, 40), 4.0, spacing)    # tráquea de 8 mm de luz, 40 mm
    _tube(mask, (40, 30, 40), (16, 30, 22), 1.0, spacing)    # dos vías de 2 mm de luz, 30 mm cada una
    _tube(mask, (40, 30, 40), (16, 30, 58), 1.0, spacing)

    out = airway_metrics(mask, spacing, lung_volume_ml=5000)

    assert out["via_longitud_fina_mm"] == pytest.approx(60, abs=12)
    assert out["via_longitud_gruesa_mm"] == pytest.approx(40, abs=10)
    assert out["via_fraccion_fina"] == pytest.approx(0.6, abs=0.1)
    assert out["via_extremos"] == 3  # el de la tráquea y uno por vía


def test_airway_length_is_also_given_inside_each_lobe():
    from maps.airways import measure_airways

    tree = _y_tree(UNIT)
    lobes = np.zeros(tree.shape, dtype=np.uint8)
    lobes[:38, :, :38] = 1   # el bronquio que baja hacia x pequeños entra en el lóbulo 1
    lobes[:38, :, 42:] = 3   # y el otro en el lóbulo 3; la tráquea queda fuera de los dos

    _, by_lobe = measure_airways(tree, UNIT, lung_volume_ml=5000, lobes=lobes)

    assert set(by_lobe) == {1, 3}
    assert by_lobe[1] == pytest.approx(by_lobe[3], rel=0.2)
    assert 15 < by_lobe[1] < 30  # la parte del bronquio de 30 mm que queda dentro del lóbulo
