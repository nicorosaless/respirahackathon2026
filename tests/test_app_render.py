"""Imagen de la app MAPS: orientación, encuadre, escala de daño y lectura de previsualizaciones."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from maps_render import (  # noqa: E402
    PreviewInvalida,
    cargar_preview,
    color_dano,
    encuadre,
    orientar_cabeza_arriba,
    ventana_pulmon,
)

LSI, LII, LSD, LM, LID = 1, 2, 3, 4, 5


def _torax() -> tuple[np.ndarray, np.ndarray]:
    """Un corte en la convención de la app: cabeza arriba, derecha del paciente a la izquierda."""
    lobes = np.zeros((1, 12, 16), dtype=np.uint8)
    lobes[0, 2:5, 2:6], lobes[0, 5:7, 2:6], lobes[0, 7:10, 2:6] = LSD, LM, LID
    lobes[0, 2:6, 10:14], lobes[0, 6:10, 10:14] = LSI, LII
    hu = np.arange(lobes.size, dtype=np.int16).reshape(lobes.shape)
    return hu, lobes


def test_slices_already_head_up_are_left_untouched():
    hu, lobes = _torax()

    hu2, lobes2 = orientar_cabeza_arriba(hu, lobes)

    assert np.array_equal(hu2, hu) and np.array_equal(lobes2, lobes)


@pytest.mark.parametrize("volteo", [(1,), (2,), (1, 2)], ids=["cabeza abajo", "espejo", "ambos"])
def test_flipped_slices_come_back_head_up_with_the_right_lung_on_the_left(volteo):
    hu, lobes = _torax()

    hu2, lobes2 = orientar_cabeza_arriba(np.flip(hu, volteo), np.flip(lobes, volteo))

    assert np.array_equal(lobes2, lobes)
    assert np.array_equal(hu2, hu)  # la imagen se voltea igual que las etiquetas


def test_orientation_is_not_guessed_without_the_lobes_that_decide_it():
    hu, lobes = _torax()
    solo_superior_derecho = np.where(lobes == LSD, LSD, 0).astype(np.uint8)
    volteado = np.flip(solo_superior_derecho, (1, 2))

    _, resultado = orientar_cabeza_arriba(np.flip(hu, (1, 2)), volteado)

    assert np.array_equal(resultado, volteado)


def test_frame_is_the_lung_box_plus_a_margin_in_millimetres():
    _, lobes = _torax()

    filas, columnas = encuadre(lobes, (2.0, 1.0), margen_mm=2.0)

    assert (filas.start, filas.stop) == (1, 11)  # pulmón en filas 2..9, margen de 1 fila
    assert (columnas.start, columnas.stop) == (0, 16)  # pulmón en columnas 2..13, margen de 2 recortado al borde


def test_frame_of_a_slice_without_lung_is_the_whole_image():
    filas, columnas = encuadre(np.zeros((2, 5, 7), dtype=np.uint8), (1.0, 1.0))

    assert (filas.stop - filas.start, columnas.stop - columnas.start) == (5, 7)


def test_no_tint_below_two_sd_and_stronger_tint_as_damage_grows():
    assert color_dano(1.99) is None
    assert color_dano(-6.0) is None  # muy desviado, pero en sentido contrario al daño
    assert color_dano(float("nan")) is None
    assert color_dano(None) is None

    pasos = [color_dano(z) for z in (2.0, 3.0, 4.0, 9.0)]
    opacidades = [alfa for _, alfa in pasos]
    assert opacidades[0] < opacidades[1] < opacidades[2] == opacidades[3]
    assert len({color for color, _ in pasos}) == 1  # un solo tono: solo cambia la intensidad


def test_lung_window_keeps_air_black_and_soft_tissue_white():
    gris = ventana_pulmon(np.array([-1350, -600, 150, 400], dtype=np.int16))

    assert gris.tolist() == [0, 127, 255, 255]


def test_preview_is_oriented_and_cropped_to_the_lungs_on_load(tmp_path):
    hu, lobes = _torax()
    ruta = tmp_path / "s1.npz"
    np.savez_compressed(ruta, hu=np.flip(hu, 1), lobes=np.flip(lobes, 1), spacing=np.array([1.0, 1.0]))

    preview = cargar_preview(ruta)

    assert preview.cortes == 1
    assert preview.espaciado == (1.0, 1.0)
    arriba = np.nonzero(preview.lobes == LSD)[1].mean()
    abajo = np.nonzero(preview.lobes == LID)[1].mean()
    assert arriba < abajo


def test_missing_preview_is_none_and_a_broken_one_says_which_file(tmp_path):
    assert cargar_preview(tmp_path / "no_esta.npz") is None

    roto = tmp_path / "roto.npz"
    roto.write_bytes(b"esto no es un npz")
    with pytest.raises(PreviewInvalida, match="roto.npz"):
        cargar_preview(roto)

    hu, lobes = _torax()
    sin_espaciado = tmp_path / "sin_espaciado.npz"
    np.savez(sin_espaciado, hu=hu, lobes=lobes)
    with pytest.raises(PreviewInvalida, match="sin_espaciado.npz"):
        cargar_preview(sin_espaciado)

    formas = tmp_path / "formas.npz"
    np.savez(formas, hu=hu, lobes=lobes[:, :5], spacing=np.array([1.0, 1.0]))
    with pytest.raises(PreviewInvalida, match="misma forma"):
        cargar_preview(formas)
