"""Medidas del árbol de vías aéreas a partir de su máscara.

En enfermedad precoz se pierden ramas pequeñas antes de que cambie la densidad.
Aquí se mide cuánto árbol se ve (ramas, longitud), el calibre de las vías
centrales en relación con el tamaño del pulmón (disanapsia) y el grosor de la
pared bronquial.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage
from skimage.morphology import skeletonize

from maps.geometry import Spacing, bounding_box, distance_to

MIN_BRANCH_MM = 3.0  # por debajo, un segmento del esqueleto es ruido de la máscara
# Las vías centrales son las más anchas: tráquea, bronquios principales, lobares y los primeros
# segmentarios. Elegirlas por calibre es más estable que por generación, que cambia con cada
# bifurcación de más o de menos que deje el esqueleto.
CENTRAL_BRANCHES = 15
MIN_CENTRAL_MM = 6.0
# Por debajo de este diámetro de luz una vía cuenta como fina: son las que se pierden primero.
FINE_DIAMETER_MM = 3.0
# Pi10 se ajusta con vías de perímetro interno entre 6 y 20 mm, donde la TC resuelve la pared.
PI10_PERIMETER_MM = (6.0, 20.0)
_NEIGHBOURS = np.ones((3, 3, 3), dtype=np.uint8)


@dataclass(frozen=True)
class Tree:
    """Esqueleto del árbol partido en ramas, con la generación de cada una."""

    skeleton: np.ndarray  # bool
    branch_of: np.ndarray  # int, 0 fuera de rama y 1..n la rama de cada vóxel del esqueleto
    generation: np.ndarray  # generación de la rama i en la posición i; -1 si no está unida a la tráquea
    length_mm: np.ndarray  # longitud de la rama i en la posición i
    connected: np.ndarray  # bool, la parte del esqueleto unida a la tráquea


def _degree(skeleton: np.ndarray) -> np.ndarray:
    degree = ndimage.convolve(skeleton.astype(np.uint8), _NEIGHBOURS, mode="constant") - 1
    return np.where(skeleton, degree, 0)


def _neighbour_pairs(shape: tuple[int, ...], spacing: Spacing):
    """Cada pareja de vóxeles vecinos (26 vecinos), una sola vez: sus dos recortes y su distancia en mm."""
    for offset in np.ndindex(3, 3, 3):
        step = np.array(offset) - 1
        if tuple(step) <= (0, 0, 0):
            continue
        a = tuple(slice(max(-s, 0), shape[i] - max(s, 0)) for i, s in enumerate(step))
        b = tuple(slice(max(s, 0), shape[i] - max(-s, 0)) for i, s in enumerate(step))
        yield a, b, float(np.linalg.norm(step * np.array(spacing)))


def _skeleton_length_mm(skeleton: np.ndarray, spacing: Spacing) -> float:
    """Suma las distancias físicas entre vóxeles vecinos del esqueleto, así no depende del vóxel."""
    return sum(float(np.count_nonzero(skeleton[a] & skeleton[b])) * distance
               for a, b, distance in _neighbour_pairs(skeleton.shape, spacing))


def _segment_lengths_mm(labels: np.ndarray, n: int, spacing: Spacing) -> np.ndarray:
    """Longitud física del segmento i en la posición i - 1.

    Suma las distancias entre vóxeles vecinos del mismo segmento y añade un
    paso más, el que lo une al resto del árbol. Contar vóxeles por el
    espaciado medio daba la misma longitud a una rama vertical y a una
    horizontal cuando el corte es más grueso que el píxel.
    """
    links = np.zeros(n + 1)
    for a, b, distance in _neighbour_pairs(labels.shape, spacing):
        same = (labels[a] == labels[b]) & (labels[a] > 0)
        links += np.bincount(labels[a][same], minlength=n + 1) * distance
    voxels = np.bincount(labels.ravel(), minlength=n + 1).astype(float)
    step = np.where(voxels > 1, links / np.maximum(voxels - 1, 1), float(np.mean(spacing)))
    return (links + step)[1:]


def _prune_spurs(skeleton: np.ndarray, lumen_radius: np.ndarray, spacing: Spacing) -> np.ndarray:
    """Quita las ramitas terminales que apenas salen de la pared de su vía.

    Un saliente de la máscara deja en el esqueleto una ramita que nace en el
    eje de la vía. Lo que cuenta es cuánto sobresale de la pared: su longitud
    menos el radio de la vía de la que sale. Si se dejan, parten en dos esa vía
    y le suman una generación que no existe.
    """
    degree = _degree(skeleton)
    segments, n = ndimage.label(skeleton & (degree <= 2), structure=_NEIGHBOURS)
    if n == 0:
        return skeleton
    index = np.arange(1, n + 1)
    size_mm = _segment_lengths_mm(segments, n, spacing)
    parent_radius = np.asarray(ndimage.maximum(lumen_radius, segments, index=index))
    has_end = np.asarray(ndimage.maximum(degree == 1, segments, index=index)).astype(bool)
    near_junction = ndimage.binary_dilation(degree >= 3, structure=_NEIGHBOURS)
    touches_junction = np.asarray(ndimage.maximum(near_junction, segments, index=index)).astype(bool)
    spur = index[has_end & touches_junction & (size_mm - parent_radius < MIN_BRANCH_MM)]
    return skeleton & ~np.isin(segments, spur)


def build_tree(airway: np.ndarray, lumen_radius: np.ndarray, spacing: Spacing) -> Tree:
    """Esqueleto, ramas y generaciones. La raíz es la rama que llega más arriba: la tráquea.

    Espera el volumen en LPS, con z creciente hacia la cabeza. `lumen_radius` es
    la distancia de cada vóxel de la luz a su pared.
    """
    skeleton = _prune_spurs(skeletonize(airway).astype(bool), lumen_radius, spacing)
    degree = _degree(skeleton)
    is_junction = skeleton & (degree >= 3)
    segments, n_segments = ndimage.label(skeleton & ~is_junction, structure=_NEIGHBOURS)
    if n_segments == 0:
        return Tree(skeleton, segments, np.full(1, -1, dtype=int), np.zeros(1), skeleton)
    # Un tramo muy corto sin extremo libre es un puente dentro de un nudo, no una rama:
    # el adelgazamiento los deja en vías anchas como la tráquea. Se absorbe en el nudo.
    index = np.arange(1, n_segments + 1)
    size_mm = _segment_lengths_mm(segments, n_segments, spacing)
    has_end = np.asarray(ndimage.maximum(degree == 1, segments, index=index)).astype(bool)
    is_junction |= np.isin(segments, index[~has_end & (size_mm < MIN_BRANCH_MM)])
    segments, n_segments = ndimage.label(skeleton & ~is_junction, structure=_NEIGHBOURS)
    junctions, _ = ndimage.label(is_junction, structure=_NEIGHBOURS)

    # Qué tramos del esqueleto toca cada nudo.
    grown = ndimage.grey_dilation(junctions, footprint=_NEIGHBOURS)
    touching = (grown > 0) & (segments > 0)
    by_junction: dict[int, set[int]] = {}
    for junction, segment in zip(grown[touching], segments[touching]):
        by_junction.setdefault(int(junction), set()).add(int(segment))

    # Un nudo con solo dos tramos no es una bifurcación: los dos tramos son la misma rama.
    parent = np.arange(n_segments + 1)

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = int(parent[i])
        return i

    for touched in by_junction.values():
        if len(touched) == 2:
            first, second = touched
            parent[find(first)] = find(second)
    roots = np.array([find(i) for i in range(n_segments + 1)])
    merged = np.unique(roots[1:])
    lookup = np.zeros(n_segments + 1, dtype=int)
    lookup[1:] = np.searchsorted(merged, roots[1:]) + 1
    branch_of = lookup[segments]
    n = len(merged)

    neighbours: dict[int, set[int]] = {}
    for touched in by_junction.values():
        branches = {int(lookup[t]) for t in touched}
        if len(branches) >= 3:
            for branch in branches:
                neighbours.setdefault(branch, set()).update(branches - {branch})

    generation = np.full(n + 1, -1, dtype=int)
    length = np.zeros(n + 1)
    length[1:] = _segment_lengths_mm(branch_of, n, spacing)
    # La raíz es la tráquea: dentro del trozo mayor del esqueleto, la rama más ancha y, entre las casi
    # igual de anchas, la que llega más arriba. Un fragmento suelto por encima no puede serlo.
    components, _ = ndimage.label(skeleton, structure=_NEIGHBOURS)
    sizes = np.bincount(components.ravel())
    sizes[0] = 0
    in_main = np.unique(branch_of[(components == sizes.argmax()) & (branch_of > 0)])
    index = np.arange(1, n + 1)
    radius = np.asarray(ndimage.mean(lumen_radius, branch_of, index=index))
    top = np.asarray(ndimage.maximum(np.indices(skeleton.shape)[0], branch_of, index=index))
    wide = [b for b in in_main if radius[b - 1] >= 0.8 * radius[in_main - 1].max()]
    root = int(max(wide, key=lambda b: top[b - 1]))
    generation[root] = 0
    frontier = [root]
    while frontier:
        following = []
        for branch in frontier:
            for other in neighbours.get(branch, ()):
                if generation[other] < 0:
                    generation[other] = generation[branch] + 1
                    following.append(other)
        frontier = following
    return Tree(skeleton, branch_of, generation, length, components == sizes.argmax())


def airway_metrics(
    airway: np.ndarray, spacing: Spacing, lung_volume_ml: float, wall: np.ndarray | None = None
) -> dict[str, float]:
    """Resumen del árbol. `airway` es la máscara (z, y, x) de la luz y `wall` la de la pared; `spacing` en mm."""
    return measure_airways(airway, spacing, lung_volume_ml, wall)[0]


def measure_airways(
    airway: np.ndarray, spacing: Spacing, lung_volume_ml: float, wall: np.ndarray | None = None,
    lobes: np.ndarray | None = None,
) -> tuple[dict[str, float], dict[int, float]]:
    """El resumen del árbol y, con `lobes`, la longitud de vía aérea dentro de cada lóbulo.

    `lobes` es el volumen de etiquetas de lóbulo, de la misma forma que
    `airway`. El segundo valor va de etiqueta de lóbulo a milímetros de
    esqueleto dentro de él; la tráquea y los bronquios principales quedan fuera
    de todos.
    """
    if not airway.any():
        raise ValueError("la máscara de vía aérea está vacía")
    voxel_ml = float(np.prod(spacing)) / 1000.0
    box = bounding_box(airway, margin=4)
    airway = airway[box].astype(bool)
    lumen_radius = distance_to(~airway, spacing)
    tree = build_tree(airway, lumen_radius, spacing)
    by_lobe = {}
    if lobes is not None:
        inside = lobes[box]
        by_lobe = {int(label): _skeleton_length_mm(tree.skeleton & (inside == label), spacing)
                   for label in np.unique(inside[tree.skeleton]) if label > 0}
    n = len(tree.generation) - 1
    real = (tree.length_mm[1:] >= MIN_BRANCH_MM) & (tree.generation[1:] >= 0)
    n_branches = int(real.sum())
    litres = lung_volume_ml / 1000.0
    lung_side_mm = (lung_volume_ml * 1000.0) ** (1.0 / 3.0)

    # Radio medio de la luz en cada rama.
    index = np.arange(1, n + 1)
    radius = np.asarray(ndimage.mean(lumen_radius, tree.branch_of, index=index)) if n else np.array([])
    candidates = np.flatnonzero(real & (tree.length_mm[1:] >= MIN_CENTRAL_MM))
    widest = candidates[np.argsort(radius[candidates])[::-1][:CENTRAL_BRANCHES]]
    central_diameter = float(np.exp(np.log(2.0 * radius[widest]).mean())) if widest.size else float("nan")

    # La longitud, repartida por el calibre de la luz en cada punto del esqueleto.
    fine = tree.skeleton & (2.0 * lumen_radius < FINE_DIAMETER_MM)
    fine_mm, wide_mm = _skeleton_length_mm(fine, spacing), _skeleton_length_mm(tree.skeleton & ~fine, spacing)

    out = {
        "via_volumen_ml": float(airway.sum()) * voxel_ml,
        "via_longitud_mm": _skeleton_length_mm(tree.skeleton, spacing),
        # Solo lo que está unido a la tráquea: sin los fragmentos que la segmentación deja sueltos.
        "via_longitud_conectada_mm": _skeleton_length_mm(tree.skeleton & tree.connected, spacing),
        "via_longitud_fina_mm": fine_mm,
        "via_longitud_gruesa_mm": wide_mm,
        "via_fraccion_fina": fine_mm / (fine_mm + wide_mm) if fine_mm + wide_mm > 0 else float("nan"),
        # Extremos libres del árbol unido a la tráquea: las vías más periféricas que se llegan a ver.
        "via_extremos": float(np.count_nonzero((_degree(tree.skeleton) == 1) & tree.connected)),
        "via_ramas": float(n_branches),
        "via_ramas_por_litro": n_branches / litres,
        "via_generaciones": float(tree.generation[1:][real].max()) if real.any() else float("nan"),
        "via_calibre_central_mm": central_diameter,
        # Calibre de las vías centrales partido por el lado del cubo de igual volumen que el pulmón.
        "via_disanapsia": central_diameter / lung_side_mm,
    }
    if wall is not None and wall[box].any():
        outer_radius = distance_to(~(airway | wall[box].astype(bool)), spacing)
        outer = np.asarray(ndimage.mean(outer_radius, tree.branch_of, index=index))
        perimeter = 2.0 * np.pi * radius
        wall_area = np.pi * np.clip(outer**2 - radius**2, 0.0, None)
        lo, hi = PI10_PERIMETER_MM
        fit = real & (perimeter >= lo) & (perimeter <= hi) & (outer > radius)
        out["via_grosor_pared_mm"] = float(np.mean(outer[fit] - radius[fit])) if fit.any() else float("nan")
        out["via_pared_pct"] = float(100.0 * np.mean(wall_area[fit] / (np.pi * outer[fit] ** 2))) if fit.any() else float("nan")
        if fit.sum() >= 8 and np.ptp(perimeter[fit]) > 0:
            # Pi10: raíz del área de pared que la recta de regresión da a una vía de 10 mm de perímetro interno.
            slope, intercept = np.polyfit(perimeter[fit], np.sqrt(wall_area[fit]), 1)
            out["via_pi10_mm"] = float(intercept + 10.0 * slope)
        else:
            out["via_pi10_mm"] = float("nan")
    return out, by_lobe
