"""Imagen de la TC: ventana de pulmón, orientación, encuadre y tinte por lóbulo.

Solo numpy y Pillow. La TC queda siempre en gris; el color es una capa por
lóbulo que solo aparece cuando el lóbulo se desvía hacia el daño.

Convención de las previsualizaciones (`previews/<subject_id>.npz`), tal como
las escribe `make_fixture.py`:

- eje 0: cortes coronales, de anterior a posterior;
- eje 1 (filas): la fila 0 es la más craneal (cabeza arriba);
- eje 2 (columnas): la columna 0 es la derecha del paciente (convención radiológica).

La app no se fía de la convención: `orientar_cabeza_arriba` la comprueba con las
etiquetas de los lóbulos y voltea lo que haga falta.
"""

from __future__ import annotations

import base64
import io
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from maps_core import UMBRAL_Z

# Ventana de pulmón habitual: centro -600 HU, ancho 1500 HU.
VENTANA_CENTRO_HU = -600.0
VENTANA_ANCHO_HU = 1500.0

ATENUACION_FUERA = 0.62

SUPERIORES, INFERIORES = (1, 3), (2, 5)  # LSI, LSD / LII, LID
DERECHOS, IZQUIERDOS = (3, 4, 5), (1, 2)

# Escala de daño: un solo tono, el dorado de AstraZeneca, más lleno cuanto mayor es la
# desviación. Por debajo del umbral no hay color. La TC queda en gris y el dorado no se
# confunde con ella; los pasos se distinguen por luminosidad, así que también se leen con
# daltonismo, y el rótulo de cada lóbulo repite la cifra.
COLOR_DANO = (240, 171, 0)  # #F0AB00
# Cada paso: (z orientada desde la que aplica, opacidad sobre la TC, opacidad sobre el blanco de las tablas).
PASOS_DANO = (
    (UMBRAL_Z, 0.22, 0.30),
    (UMBRAL_Z + 1, 0.45, 0.62),
    (UMBRAL_Z + 2, 0.72, 1.00),
)


def color_dano(z_orientada: float | None) -> tuple[tuple[int, int, int], float] | None:
    """Color y opacidad del tinte para una z orientada; None si está dentro de lo esperado o no hay dato."""
    if z_orientada is None or not np.isfinite(z_orientada):
        return None
    elegido = None
    for desde, en_tc, _ in PASOS_DANO:
        if z_orientada >= desde:
            elegido = (COLOR_DANO, en_tc)
    return elegido


def ventana_pulmon(hu: np.ndarray) -> np.ndarray:
    """HU a gris de 8 bits con la ventana de pulmón."""
    minimo = VENTANA_CENTRO_HU - VENTANA_ANCHO_HU / 2
    gris = (hu.astype(np.float32) - minimo) / VENTANA_ANCHO_HU
    return (np.clip(gris, 0.0, 1.0) * 255.0).astype(np.uint8)


def _centro(lobes: np.ndarray, etiquetas: tuple[int, ...], eje: int) -> float | None:
    posiciones = np.nonzero(np.isin(lobes, etiquetas))[eje]
    return float(posiciones.mean()) if posiciones.size else None


def orientar_cabeza_arriba(hu: np.ndarray, lobes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Deja los cortes (k, filas, columnas) con la cabeza arriba y la derecha del paciente a la izquierda.

    La anatomía lo decide: los lóbulos superiores tienen que quedar por encima
    de los inferiores y el pulmón derecho a la izquierda de la imagen. Si faltan
    las etiquetas necesarias para comprobar un eje, ese eje no se toca.
    """
    arriba, abajo = _centro(lobes, SUPERIORES, 1), _centro(lobes, INFERIORES, 1)
    if arriba is not None and abajo is not None and arriba > abajo:
        hu, lobes = hu[:, ::-1, :], lobes[:, ::-1, :]
    derecha, izquierda = _centro(lobes, DERECHOS, 2), _centro(lobes, IZQUIERDOS, 2)
    if derecha is not None and izquierda is not None and derecha > izquierda:
        hu, lobes = hu[:, :, ::-1], lobes[:, :, ::-1]
    return hu, lobes


def encuadre(lobes: np.ndarray, espaciado: tuple[float, float], margen_mm: float = 14.0) -> tuple[slice, slice]:
    """Recorte común a todos los cortes: la caja de los pulmones más un margen. Sin pulmón, la imagen entera."""
    _, filas, columnas = np.nonzero(lobes)
    if filas.size == 0:
        return slice(0, lobes.shape[1]), slice(0, lobes.shape[2])
    mf = int(round(margen_mm / espaciado[0]))
    mc = int(round(margen_mm / espaciado[1]))
    return (
        slice(max(int(filas.min()) - mf, 0), min(int(filas.max()) + mf + 1, lobes.shape[1])),
        slice(max(int(columnas.min()) - mc, 0), min(int(columnas.max()) + mc + 1, lobes.shape[2])),
    )


class PreviewInvalida(Exception):
    """El fichero existe pero no cumple el contrato. El mensaje se muestra tal cual."""


@dataclass(frozen=True)
class Preview:
    hu: np.ndarray  # (k, filas, columnas), ya orientado y recortado a los pulmones
    lobes: np.ndarray
    espaciado: tuple[float, float]  # mm por fila, mm por columna

    @property
    def cortes(self) -> int:
        return int(self.hu.shape[0])


def cargar_preview(ruta: Path) -> Preview | None:
    """Lee `previews/<subject_id>.npz`. None si no existe; `PreviewInvalida` si no se puede usar."""
    if not ruta.exists():
        return None
    try:
        with np.load(ruta) as datos:
            hu, lobes, espaciado = datos["hu"], datos["lobes"], np.asarray(datos["spacing"], dtype=float).ravel()
    except (KeyError, ValueError, OSError, zipfile.BadZipFile) as error:
        raise PreviewInvalida(
            f"previews/{ruta.name} no es un .npz con las matrices hu, lobes y spacing. Hay que volver a generarlo."
        ) from error
    if hu.ndim != 3 or hu.shape != lobes.shape or 0 in hu.shape:
        raise PreviewInvalida(
            f"previews/{ruta.name}: hu y lobes tienen que tener la misma forma (cortes, filas, columnas). "
            f"Ahora son {hu.shape} y {lobes.shape}."
        )
    if espaciado.size != 2 or not np.all(np.isfinite(espaciado)) or np.any(espaciado <= 0):
        raise PreviewInvalida(f"previews/{ruta.name}: spacing tiene que ser (mm por fila, mm por columna), dos números positivos.")
    hu, lobes = orientar_cabeza_arriba(hu, lobes)
    mm = (float(espaciado[0]), float(espaciado[1]))
    filas, columnas = encuadre(lobes, mm)
    return Preview(np.ascontiguousarray(hu[:, filas, columnas]), np.ascontiguousarray(lobes[:, filas, columnas]), mm)


@dataclass(frozen=True)
class CorteCompuesto:
    data_uri: str
    ancho: int
    alto: int
    centros: dict[int, tuple[float, float]]  # etiqueta -> (x, y) en fracción de la imagen


def _bordes(etiquetas: np.ndarray) -> np.ndarray:
    """Píxeles de pulmón que tocan otra etiqueta: el contorno de cada lóbulo."""
    borde = np.zeros(etiquetas.shape, dtype=bool)
    borde[:-1, :] |= etiquetas[:-1, :] != etiquetas[1:, :]
    borde[1:, :] |= etiquetas[1:, :] != etiquetas[:-1, :]
    borde[:, :-1] |= etiquetas[:, :-1] != etiquetas[:, 1:]
    borde[:, 1:] |= etiquetas[:, 1:] != etiquetas[:, :-1]
    return borde & (etiquetas > 0)


def componer_corte(
    hu: np.ndarray,
    lobes: np.ndarray,
    espaciado: tuple[float, float],
    z_por_etiqueta: dict[int, float],
    alto_px: int = 760,
    resaltada: int | None = None,
) -> CorteCompuesto:
    """Un corte coronal en gris con cada lóbulo teñido según su z orientada.

    `espaciado` es (mm por fila, mm por columna) y fija la proporción. Los
    lóbulos dentro de lo esperado quedan sin color, solo con su contorno.
    """
    alto_mm, ancho_mm = hu.shape[0] * espaciado[0], hu.shape[1] * espaciado[1]
    tamano = (max(int(round(alto_px * ancho_mm / alto_mm)), 1), alto_px)
    gris = np.asarray(Image.fromarray(ventana_pulmon(hu)).resize(tamano, Image.Resampling.BICUBIC), dtype=np.float32)
    etiquetas = np.asarray(Image.fromarray(lobes.astype(np.uint8)).resize(tamano, Image.Resampling.NEAREST))

    # Fuera del pulmón la imagen se atenúa: sigue siendo la TC en gris, pero la vista va al parénquima.
    gris = np.where(etiquetas > 0, gris, gris * ATENUACION_FUERA)
    rgb = np.repeat(gris[:, :, None], 3, axis=2)
    centros: dict[int, tuple[float, float]] = {}
    for etiqueta in np.unique(etiquetas):
        if etiqueta == 0:
            continue
        mascara = etiquetas == etiqueta
        filas, columnas = np.nonzero(mascara)
        if filas.size >= 0.004 * mascara.size:  # demasiado pequeño para rotularlo
            centros[int(etiqueta)] = (float(np.median(columnas)) / tamano[0], float(np.median(filas)) / tamano[1])
        tinte = color_dano(z_por_etiqueta.get(int(etiqueta)))
        if tinte is not None:
            color, alfa = tinte
            rgb[mascara] = (1 - alfa) * rgb[mascara] + alfa * np.asarray(color, dtype=np.float32)

    borde = _bordes(etiquetas)
    rgb[borde] = 0.55 * rgb[borde] + 0.45 * 255.0
    if resaltada is not None:
        propio = _bordes(np.where(etiquetas == resaltada, resaltada, 0))
        grueso = propio.copy()
        grueso[1:, :] |= propio[:-1, :]
        grueso[:, 1:] |= propio[:, :-1]
        rgb[grueso] = 255.0

    salida = io.BytesIO()
    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).save(salida, format="JPEG", quality=88)
    data_uri = "data:image/jpeg;base64," + base64.b64encode(salida.getvalue()).decode("ascii")
    return CorteCompuesto(data_uri=data_uri, ancho=tamano[0], alto=tamano[1], centros=centros)
