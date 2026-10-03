"""HTML y CSS de la app MAPS. Funciones que reciben números y devuelven marcado.

Todo el texto es fijo. Lo único variable son números y nombres que vienen de
los ficheros de la cohorte, y pasan siempre por `html.escape`.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from html import escape

import numpy as np
import pandas as pd

from maps_core import (
    LOBULOS,
    NOMBRE_LOBULO,
    PULMON,
    UMBRAL_Z,
    Evidencia,
    Medida,
    fmt,
    fmt_auto,
    lista_con_ni,
    lista_con_y,
)
from maps_render import COLOR_DANO, PASOS_DANO, CorteCompuesto

# Tokens de diseño. Superficie blanca dominante, negro para el texto y la estructura, y un
# único acento: el dorado de AstraZeneca (#F0AB00, el que usa astrazeneca.es). El dorado
# significa siempre lo mismo, «daño, lo que hay que mirar», y solo se usa como relleno,
# borde o indicador con texto negro encima: sobre blanco no llega al contraste de un texto.
# Grises, radios, sombra y tiempos salen de la guía de AstraZeneca España; la forma, la
# densidad y los estados de los botones, del botón de Kumo (Cloudflare).
BLANCO = "#ffffff"
TINTA = "#000000"  # guía: color.surface.base
TINTA_2 = "#3c4242"  # guía: color.text.tertiary; 10,4:1 sobre blanco
TINTA_3 = "#636868"  # gris de astrazeneca.es; 5,9:1 sobre blanco
LINEA = "#d2d2d2"  # guía: color.text.inverse
FONDO_2 = "#f8f8f8"  # gris de superficie de astrazeneca.es
FONDO_FUERTE = "#1b1b1b"  # guía: color.surface.strong
GRIS_DATO = "#b1b3b3"  # puntos y barras que no hay que mirar primero
ACENTO = "#{:02x}{:02x}{:02x}".format(*COLOR_DANO)
FUENTE = '"Helvetica Neue", Helvetica, Arial, sans-serif'  # guía: font.family.stack; sin fuentes web


def _mezcla(sobre: tuple[int, int, int], alfa: float) -> str:
    """El dorado con una opacidad dada sobre un color de fondo, como hexadecimal."""
    return "#{:02x}{:02x}{:02x}".format(*(round((1 - alfa) * f + alfa * c) for f, c in zip(sobre, COLOR_DANO)))


def _luminancia(color: str) -> float:
    """Luminancia relativa (WCAG) de un color hexadecimal."""
    canales = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lineales = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canales]
    return 0.2126 * lineales[0] + 0.7152 * lineales[1] + 0.0722 * lineales[2]


# La escala de daño en las tablas: el mismo dorado, más lleno cuanto mayor es la desviación.
COLORES_DANO = tuple(_mezcla((255, 255, 255), en_tabla) for _, _, en_tabla in PASOS_DANO)
# Y en la leyenda de la TC: el dorado tal como queda sobre el gris del pulmón.
GRIS_PULMON = (70, 70, 70)
COLORES_DANO_TC = tuple(_mezcla(GRIS_PULMON, en_tc) for _, en_tc, _ in PASOS_DANO)

Z_MAX_PISTA = 5.0  # la pista de desviación va de -5 a +5 desviaciones estándar
UMBRAL = fmt_auto(UMBRAL_Z)  # el umbral tal como se escribe en los textos
BORDE_ESPERADO = 50 - 50 * UMBRAL_Z / Z_MAX_PISTA  # % de la pista a cada lado de la banda de lo esperado

CSS = f"""
<style>
:root {{
  --superficie: {BLANCO}; --superficie-2: {FONDO_2}; --superficie-fuerte: {FONDO_FUERTE};
  --tinta: {TINTA}; --tinta-2: {TINTA_2}; --tinta-3: {TINTA_3}; --tinta-inversa: {BLANCO}; --tinta-inversa-2: {LINEA};
  --linea: {LINEA}; --gris-dato: {GRIS_DATO};
  --acento: {ACENTO}; --dano-1: {COLORES_DANO[0]}; --dano-2: {COLORES_DANO[1]}; --dano-3: {COLORES_DANO[2]};
  --radio: 2px;            /* guía: radius.xs */
  --radio-pildora: 50px;   /* guía: radius.sm */
  --radio-boton: 8px;      /* Kumo: rounded-lg */
  --sombra-1: rgba(60, 66, 66, 0.3) 0px 2px 5px 0px;   /* guía: shadow.1 */
  --sombra-boton: 0 1px 2px rgba(0, 0, 0, 0.05);       /* Kumo: shadow-xs */
  --transicion: 200ms;     /* guía: motion.duration.instant */
  --foco: 0 0 0 3px var(--acento);  /* con el contorno negro por fuera: foco siempre visible */
}}
[data-testid="stHeader"] {{ display: none; }}
[data-testid="stMainBlockContainer"] {{ padding: 0.7rem 2rem 1rem; max-width: 1560px; }}
[data-testid="stVerticalBlock"] {{ gap: 0.6rem; }}
.maps * {{ box-sizing: border-box; }}
.maps {{ color: var(--tinta); font-family: {FUENTE}; font-variant-numeric: tabular-nums; }}
.maps p {{ margin: 0; }}

/* Botones. Forma, densidad y estados del botón de Kumo: 36 px de alto, 12 px de relleno
   horizontal, radio de 8 px, anillo de 1 px y sombra mínima. El elegido es el primario: negro
   con texto blanco. Los demás son secundarios: blancos con anillo gris. */
[data-testid="stButtonGroup"] [role="radiogroup"] {{ gap: 6px; flex-wrap: nowrap; }}
button[data-variant="segmented_control"] {{
  height: 36px; min-height: 36px; padding: 0 12px; border: 0; border-radius: var(--radio-boton);
  background: var(--superficie); color: var(--tinta);
  box-shadow: 0 0 0 1px var(--linea), var(--sombra-boton);
  cursor: pointer; user-select: none;
  transition: background var(--transicion), box-shadow var(--transicion), color var(--transicion);
}}
button[data-variant="segmented_control"] p {{ font-size: 0.94rem; font-weight: 500; white-space: nowrap; }}
button[data-variant="segmented_control"]:hover:not(:disabled) {{ background: var(--superficie-2); box-shadow: 0 0 0 1px var(--tinta-3), var(--sombra-boton); }}
button[data-variant="segmented_control"]:active:not(:disabled) {{ background: #ebefee; }}
button[data-variant="segmented_control"][data-selected="true"] {{
  background: linear-gradient(to bottom, #333333, var(--tinta)); color: var(--tinta-inversa);
  box-shadow: 0 0 0 1px var(--tinta), inset 0 1px 0 0 #4d4d4d, var(--sombra-boton);
}}
button[data-variant="segmented_control"][data-selected="true"] p {{ color: var(--tinta-inversa); }}
button[data-variant="segmented_control"][data-selected="true"]:hover:not(:disabled) {{
  background: linear-gradient(to bottom, #4d4d4d, var(--tinta)); box-shadow: 0 0 0 1px var(--tinta), inset 0 1px 0 0 #666666, var(--sombra-boton);
}}
button[data-variant="segmented_control"][data-selected="true"]:active:not(:disabled) {{ background: var(--tinta); }}
button[data-variant="segmented_control"]:focus-visible {{
  outline: 2px solid var(--tinta); outline-offset: 3px; box-shadow: var(--foco);
}}
button[data-variant="segmented_control"]:disabled {{ opacity: 0.5; cursor: not-allowed; }}

/* Selectores: el mismo cuerpo que un botón secundario. */
.stSelectbox [role="group"] {{
  min-height: 36px; border: 0; border-radius: var(--radio-boton); background: var(--superficie);
  box-shadow: 0 0 0 1px var(--linea), var(--sombra-boton); transition: box-shadow var(--transicion), background var(--transicion);
}}
.stSelectbox [role="group"]:hover {{ box-shadow: 0 0 0 1px var(--tinta-3), var(--sombra-boton); }}
.stSelectbox [role="group"]:focus-within {{ outline: 2px solid var(--tinta); outline-offset: 3px; box-shadow: var(--foco); }}
.stSelectbox input {{ font-size: 0.94rem; }}
.stSelectbox [role="group"][data-disabled], .stSelectbox input:disabled {{ cursor: not-allowed; }}
[data-testid="stWidgetLabel"] p {{ font-size: 0.86rem; color: var(--tinta-2); }}
.stSlider input:focus-visible + div, .stSlider [data-focus-visible] {{ outline: 2px solid var(--tinta); outline-offset: 3px; }}

/* Aviso de datos sintéticos */
.sintetico {{ background: var(--superficie-fuerte); color: var(--tinta-inversa); border-radius: var(--radio);
  padding: 0.16rem 0.8rem; font-size: 0.84rem; font-weight: 700; }}
.sintetico span {{ font-weight: 400; color: var(--tinta-inversa-2); }}

/* Cabecera */
.marca {{ display: flex; align-items: baseline; gap: 0.6rem; white-space: nowrap; }}
.marca i {{ width: 0.95rem; height: 0.95rem; background: var(--acento); border-radius: var(--radio); align-self: center; flex: none; }}
.marca b {{ font-size: 1.5rem; letter-spacing: 0.02em; }}
.marca span {{ color: var(--tinta-2); font-size: 0.98rem; overflow: hidden; text-overflow: ellipsis; }}

/* Lectura del paciente */
.lectura {{ display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 1.4rem; align-items: center;
  border: 1px solid var(--linea); border-left: 8px solid var(--acento); border-radius: var(--radio);
  padding: 0.6rem 1.1rem; box-shadow: var(--sombra-1); }}
.lectura.sin-dano {{ border-left-color: var(--linea); }}
.lectura .quien {{ display: flex; align-items: center; gap: 0.6rem; font-size: 0.92rem; color: var(--tinta-2); margin-bottom: 0.25rem; }}
.lectura .quien b {{ color: var(--tinta); font-size: 1rem; }}
.chip {{ border: 1px solid var(--tinta); border-radius: var(--radio-pildora); padding: 0.05rem 0.65rem; font-size: 0.84rem; color: var(--tinta); }}
.chip.clase {{ background: var(--acento); border-color: var(--acento); font-weight: 700; }}
.lectura .frase {{ font-size: 1.16rem; line-height: 1.3; font-weight: 700; text-wrap: balance; }}
.lectura .motivo {{ font-size: 0.95rem; line-height: 1.35; color: var(--tinta-2); margin-top: 0.2rem; }}
.cifras {{ display: flex; gap: 0.9rem; }}
.cifra {{ border-left: 1px solid var(--linea); padding-left: 0.85rem; white-space: nowrap; }}
.cifra .n {{ font-size: 1.9rem; font-weight: 700; line-height: 1.1; white-space: nowrap; }}
.cifra .n small {{ font-size: 1rem; font-weight: 700; color: var(--tinta-2); }}
.cifra .t {{ font-size: 0.88rem; color: var(--tinta); font-weight: 700; }}
.cifra .s {{ font-size: 0.8rem; color: var(--tinta-2); }}

/* Títulos de bloque */
.titulo {{ font-size: 1.04rem; font-weight: 700; margin: 0 0 0.1rem; }}
.nota {{ font-size: 0.82rem; color: var(--tinta-2); line-height: 1.35; }}

/* TC */
.tc-marco {{ background: var(--tinta); border-radius: var(--radio); display: flex; justify-content: center; overflow: hidden; }}
/* La altura sigue a la ventana para que la vista quepa sin desplazamiento; la proporción la fija --razon. */
.tc-lienzo {{ position: relative; line-height: 0; aspect-ratio: var(--razon);
  width: min(100%, calc(clamp(280px, 100vh - 440px, 640px) * var(--razon))); }}
.tc-lienzo img {{ display: block; width: 100%; height: 100%; }}
.tc-rotulo {{ position: absolute; transform: translate(-50%, -50%); background: var(--tinta); color: var(--tinta-inversa);
  border-radius: var(--radio); padding: 0.22rem 0.42rem; font-size: 0.84rem; line-height: 1.1; font-weight: 700; white-space: nowrap; }}
.tc-rotulo span {{ font-weight: 400; }}
.tc-rotulo.normal {{ background: rgba(0, 0, 0, 0.6); color: var(--tinta-inversa-2); }}
.tc-lado {{ position: absolute; top: 0.45rem; background: rgba(0, 0, 0, 0.6); color: var(--tinta-inversa); border-radius: var(--radio);
  padding: 0.2rem 0.4rem; font-size: 0.8rem; line-height: 1.1; font-weight: 700; }}
/* Leyenda: los tres pasos van pegados, como una escala, para que se comparen de un vistazo. */
.leyenda {{ display: flex; flex-wrap: wrap; gap: 0.2rem 0.9rem; align-items: center; font-size: 0.82rem; white-space: nowrap; }}
.leyenda i {{ display: inline-block; width: 1.25rem; height: 1.25rem; border-radius: var(--radio); vertical-align: -0.3rem; margin-right: 0.35rem;
  border: 1px solid var(--tinta); }}
.leyenda .escala {{ display: inline-flex; align-items: center; }}
.leyenda .escala b {{ display: inline-block; min-width: 3.9rem; height: 1.25rem; line-height: 1.25rem; padding: 0 0.4rem; text-align: center;
  font-size: 0.78rem; border: 1px solid var(--tinta); margin-left: -1px; }}
.leyenda .escala b:first-child {{ margin-left: 0; border-radius: var(--radio) 0 0 var(--radio); }}
.leyenda .escala b:last-of-type {{ border-radius: 0 var(--radio) var(--radio) 0; margin-right: 0.35rem; }}

/* Tablas. En una ventana estrecha se desplazan dentro de su tarjeta en vez de deformarse. */
.ancho {{ overflow-x: auto; }}
.ancho .matriz {{ min-width: 24rem; }}
.ancho .detalle {{ min-width: 23rem; }}
.desliza .perfil {{ min-width: 18rem; }}
.tabla {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
.tabla th {{ text-align: left; font-weight: 700; color: var(--tinta-2); font-size: 0.78rem; padding: 0.2rem 0.4rem;
  border-bottom: 1px solid var(--tinta); white-space: nowrap; }}
.tabla td {{ padding: 0.26rem 0.4rem; border-bottom: 1px solid var(--linea); vertical-align: middle; }}
.tabla tr:last-child td {{ border-bottom: 0; }}
.tabla .num {{ text-align: right; white-space: nowrap; }}
.tabla .apagado {{ color: var(--tinta-3); }}

.matriz th, .matriz td.z {{ text-align: center; }}
.matriz th:first-child {{ text-align: left; }}
.matriz {{ table-layout: fixed; }}
.matriz col.z {{ width: 2.85rem; }}
.matriz col.entero {{ width: 3.5rem; }}
.matriz td:first-child {{ line-height: 1.15; overflow-wrap: anywhere; }}
.matriz th.grupo {{ border-bottom: 0; padding-bottom: 0; font-weight: 400; }}
.matriz th.sel {{ color: var(--tinta); box-shadow: inset 0 -3px 0 var(--tinta); }}
.matriz td.sel {{ background: var(--superficie-2); }}
.matriz .sep {{ border-left: 1px solid var(--linea); }}
.matriz th {{ line-height: 1.15; vertical-align: bottom; padding-left: 0.1rem; padding-right: 0.1rem; }}
.matriz td.z {{ padding: 0.2rem 0.1rem; }}
.celda {{ display: block; padding: 0.14rem 0; font-size: 0.88rem; border-radius: var(--radio); color: var(--tinta-2);
  border: 1.5px solid transparent; }}
.celda.d1, .celda.d2, .celda.d3 {{ color: var(--tinta); font-weight: 700; }}
.celda.d1 {{ background: var(--dano-1); }} .celda.d2 {{ background: var(--dano-2); }} .celda.d3 {{ background: var(--dano-3); }}
.celda.otro {{ border-color: var(--tinta); color: var(--tinta); }}
.celda.vacio {{ color: var(--tinta-3); }}

/* Pista de desviación: de -5 a +5 desviaciones estándar */
.pista {{ position: relative; height: 1.3rem; min-width: 5.5rem; background: var(--superficie-2); border-radius: var(--radio); }}
.pista .dano {{ position: absolute; top: 0; bottom: 0; background: var(--dano-1); }}
.pista .dano.mayor {{ left: {100 - BORDE_ESPERADO}%; right: 0; }}
.pista .dano.menor {{ left: 0; right: {100 - BORDE_ESPERADO}%; }}
.pista .esperado {{ position: absolute; top: 0; bottom: 0; left: {BORDE_ESPERADO}%; right: {BORDE_ESPERADO}%; background: var(--linea); }}
.pista .cero {{ position: absolute; top: 0; bottom: 0; left: 50%; width: 1px; background: var(--tinta-3); }}
.pista .punto {{ position: absolute; top: 50%; width: 0.85rem; height: 0.85rem; border-radius: 50%; transform: translate(-50%, -50%);
  background: var(--tinta); border: 2px solid var(--superficie); }}
.pista .punto.d1, .pista .punto.d2, .pista .punto.d3 {{ border-color: var(--tinta); background: var(--acento); }}
.pista .punto.otro {{ background: var(--superficie); border-color: var(--tinta); }}

/* Perfil clínico */
.desliza {{ max-height: max(16rem, calc(100vh - 372px)); overflow-y: auto; }}
.desliza thead th {{ position: sticky; top: 0; background: var(--superficie); z-index: 1; }}
.perfil {{ font-size: 0.88rem; table-layout: fixed; }}
.perfil td, .perfil th {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.perfil td {{ padding-top: 0.2rem; padding-bottom: 0.2rem; }}
.perfil td.var {{ font-weight: 700; }}
.perfil td.pct {{ color: var(--tinta-2); text-align: right; }}
.perfil td.ctx {{ color: var(--tinta-2); font-size: 0.82rem; overflow: visible; }}
.franja {{ position: relative; display: flex; align-items: flex-end; gap: 1px; width: 100%; height: 1.3rem; border-bottom: 1px solid var(--gris-dato); }}
.franja i {{ flex: 1 1 0; background: var(--gris-dato); }}
.franja b {{ position: absolute; top: 0; bottom: -1px; width: 2px; margin-left: -1px; background: var(--tinta); }}
.franja b::before {{ content: ""; position: absolute; top: -1px; left: -3px; width: 8px; height: 8px; border-radius: 50%; background: var(--tinta); }}

/* Estados vacíos */
.vacio-caja {{ border: 1px dashed var(--tinta-3); border-radius: var(--radio); padding: 1.4rem 1.2rem; background: var(--superficie-2); }}
.vacio-caja b {{ display: block; font-size: 1rem; margin-bottom: 0.2rem; }}
.vacio-caja span {{ color: var(--tinta-2); font-size: 0.9rem; }}
.vacio-caja.alto {{ min-height: 18rem; display: flex; flex-direction: column; justify-content: center; }}

/* Cohorte: intervalos */
.titular {{ font-size: 1.3rem; font-weight: 700; line-height: 1.25; margin: 0.1rem 0 0.15rem; text-wrap: pretty; }}
.titular.alerta {{ border-left: 8px solid var(--acento); padding-left: 0.7rem; }}
.bosque {{ display: grid; column-gap: 0.75rem; row-gap: 0; align-items: center; font-size: 0.98rem; margin-top: 0.5rem; }}
.bosque .cab {{ font-size: 0.78rem; color: var(--tinta-2); font-weight: 700; padding-bottom: 0.25rem; border-bottom: 1px solid var(--tinta); align-self: end; }}
.bosque .fila {{ padding: 0.5rem 0; border-bottom: 1px solid var(--linea); min-height: 3.4rem; display: flex; align-items: center; }}
.bosque .nombre {{ font-weight: 700; }}
.bosque .valor b {{ font-size: 1.08rem; }}
.bosque .valor span, .bosque .inc span {{ color: var(--tinta-2); font-size: 0.88rem; }}
.bosque .inc.cero, .bosque .inc.cero b {{ color: var(--tinta-3); font-weight: 400; }}
.bosque .der {{ justify-content: flex-end; text-align: right; }}
.eje {{ position: relative; width: 100%; height: 1.5rem; }}
.eje .ci {{ position: absolute; top: 50%; height: 4px; margin-top: -2px; background: var(--tinta); border-radius: var(--radio); }}
.eje .pt {{ position: absolute; top: 50%; width: 0.95rem; height: 0.95rem; border-radius: 50%; background: var(--tinta);
  border: 2px solid var(--superficie); transform: translate(-50%, -50%); }}
.eje .ref {{ position: absolute; top: -1rem; bottom: -1rem; width: 0; border-left: 2px dashed var(--tinta-3); }}
.eje.alerta .pt {{ background: var(--acento); border-color: var(--tinta); }}
.eje .marca-eje {{ position: absolute; top: 0.1rem; transform: translateX(-50%); font-size: 0.78rem; color: var(--tinta-2); white-space: nowrap; }}
.veredicto {{ display: inline-block; border-radius: var(--radio-pildora); padding: 0.14rem 0.75rem; font-size: 0.86rem; font-weight: 700;
  white-space: nowrap; border: 1.5px solid var(--tinta); color: var(--tinta); }}
.veredicto.alerta {{ background: var(--acento); }}
.avisos {{ font-size: 0.84rem; color: var(--tinta-2); }}
.avisos li {{ margin: 0.1rem 0; }}
</style>
"""


def _envolver(cuerpo: str) -> str:
    return f'<div class="maps">{cuerpo}</div>'


def html_sintetico(nota: str = "") -> str:
    """Aviso fijo de datos sintéticos. `nota` es la primera línea del fichero SINTETICO, si la tiene."""
    detalle = escape(nota) if nota else "Ningún valor corresponde a un paciente."
    return _envolver(f'<div class="sintetico">Datos sintéticos. <span>{detalle}</span></div>')


def html_marca() -> str:
    return _envolver('<div class="marca"><i></i><b>MAPS</b><span>Daño pulmonar por lóbulo en la EPOC precoz</span></div>')


def html_vacio(titulo: str, texto: str, alto: bool = False) -> str:
    clase = "vacio-caja alto" if alto else "vacio-caja"
    return _envolver(f'<div class="{clase}"><b>{escape(titulo)}</b><span>{escape(texto)}</span></div>')


def html_titulo(titulo: str, nota: str = "") -> str:
    nota_html = f'<p class="nota">{escape(nota)}</p>' if nota else ""
    return _envolver(f'<p class="titulo">{escape(titulo)}</p>{nota_html}')


def html_nota(texto: str) -> str:
    return _envolver(f'<p class="nota">{escape(texto)}</p>')


# ---------------------------------------------------------------------------
# Paciente
# ---------------------------------------------------------------------------


def _paso(z_orientada: float | None) -> int:
    """0 dentro de lo esperado o sin dato; 1, 2, 3 según el paso de la escala de daño."""
    if z_orientada is None or not math.isfinite(z_orientada):
        return 0
    return sum(z_orientada >= desde for desde, _, _ in PASOS_DANO)


def html_lectura(
    subject_id: str,
    grupo: str | None,
    clasificacion: str | None,
    motivo: str | None,
    frase: str,
    puntuacion: float,
    percentil: float | None,
    n_cohorte: int,
    fuera: int | None,
    con_dato: int,
) -> str:
    chip = f'<span class="chip clase">{escape(clasificacion)}</span>' if clasificacion else ""
    # El grupo descriptivo solo se enseña si dice algo distinto de la clase.
    if grupo and grupo != clasificacion:
        chip += f'<span class="chip">{escape(grupo)}</span>'
    porque = f'<p class="motivo">{escape(motivo)}</p>' if motivo else ""
    cifras = ""
    if math.isfinite(puntuacion):
        pct = f"{percentil:.0f}" if percentil is not None else "–"
        cifras = (
            '<div class="cifras">'
            f'<div class="cifra"><div class="n">{fmt(puntuacion, 1, signo=True)}</div>'
            '<div class="t">Puntuación de daño</div><div class="s">z media; 0 es lo esperado</div></div>'
            f'<div class="cifra"><div class="n">{pct}</div>'
            f'<div class="t">Percentil en la cohorte</div><div class="s">entre {n_cohorte} sujetos con TC</div></div>'
            f'<div class="cifra"><div class="n">{fuera}<small> de {con_dato}</small></div>'
            f'<div class="t">Lóbulos fuera de rango</div><div class="s">{UMBRAL} DE o más hacia el daño</div></div>'
            "</div>"
        )
    clase = "lectura" if fuera else "lectura sin-dano"
    return _envolver(
        f'<div class="{clase}"><div><div class="quien"><b>{escape(subject_id)}</b>{chip}</div>'
        f'<p class="frase">{escape(frase)}</p>{porque}</div>{cifras}</div>'
    )


def html_tc(corte: CorteCompuesto, rotulos: Mapping[int, tuple[str, float | None]]) -> str:
    """La imagen con un rótulo por lóbulo visible. El rótulo lleva la cifra solo si el lóbulo está fuera de rango."""
    partes = [f'<img src="{corte.data_uri}" alt="Corte coronal de la TC con los lóbulos coloreados por su desviación">']
    for etiqueta, (x, y) in corte.centros.items():
        if etiqueta not in rotulos:
            continue
        nombre, z = rotulos[etiqueta]
        posicion = f"left:{100 * x:.1f}%;top:{100 * y:.1f}%"
        if _paso(z):
            partes.append(f'<div class="tc-rotulo" style="{posicion}">{escape(nombre)} <span>{fmt(z, 1)} DE</span></div>')
        elif z is None:
            partes.append(f'<div class="tc-rotulo normal" style="{posicion}">{escape(nombre)} <span>sin dato</span></div>')
        else:
            partes.append(f'<div class="tc-rotulo normal" style="{posicion}">{escape(nombre)}</div>')
    partes.append(
        '<div class="tc-lado" style="left:0.45rem" title="Derecha del paciente">D</div>'
        '<div class="tc-lado" style="right:0.45rem" title="Izquierda del paciente">I</div>'
    )
    razon = f"--razon:{corte.ancho / corte.alto:.4f}"
    return _envolver(f'<div class="tc-marco"><div class="tc-lienzo" style="{razon}">{"".join(partes)}</div></div>')


def html_leyenda(hay_medidas: bool = True) -> str:
    if not hay_medidas:
        return _envolver('<p class="nota">Este paciente no tiene medidas de TC: los lóbulos se muestran sin color.</p>')
    desde = [fmt_auto(z) for z, _, _ in PASOS_DANO]
    pasos = [f"{a} a {b}" for a, b in zip(desde, desde[1:])] + [f"{desde[-1]} o más"]
    # El texto de cada paso va en blanco o en negro según cuál contraste más con su fondo.
    escala = "".join(
        f'<b style="background:{color};color:{TINTA if _luminancia(color) > 0.16 else BLANCO}">{texto}</b>'
        for color, texto in zip(COLORES_DANO_TC, pasos)
    )
    sin_color = "#{:02x}{:02x}{:02x}".format(*GRIS_PULMON)
    return _envolver(
        f'<div class="leyenda"><span><i style="background:{sin_color}"></i>Dentro de lo esperado</span>'
        f'<span class="escala">{escala}DE</span></div>'
        '<p class="nota" style="margin-top:0.15rem">DE: desviaciones estándar respecto a lo esperado, hacia el daño.</p>'
    )


def _celda_z(z: float, z_orientada: float | None) -> str:
    if not math.isfinite(z):
        return '<span class="celda vacio" title="sin dato">–</span>'
    paso = _paso(z_orientada)
    clase = f"celda d{paso}" if paso else "celda otro" if abs(z) >= UMBRAL_Z else "celda"
    return f'<span class="{clase}">{fmt(z, 1, signo=True)}</span>'


def _sentido(medida: Medida) -> str:
    return {"menor": "Peor si baja.", "mayor": "Peor si sube."}.get(medida.peor or "", "Sentido de daño no definido.")


def html_matriz(z: pd.DataFrame, z_orientada: pd.DataFrame, medidas: Mapping[str, Medida], seleccion: str) -> str:
    """Una fila por medida, una columna por lóbulo: la z tal como viene, con color si se desvía hacia el daño."""
    regiones = [r for r in (*LOBULOS, PULMON) if r in z.index]
    primeras = ("LSI", PULMON)  # primera columna de cada bloque: lleva una línea de separación

    def clases(region: str, *otras: str) -> str:
        return " ".join([*otras, "sel" if region == seleccion else "", "sep" if region in primeras else ""]).strip()

    cabecera = "".join(f'<th class="{clases(r)}">{r}</th>' for r in regiones if r != PULMON)
    grupos = '<th class="grupo"></th><th class="grupo" colspan="3">Pulmón derecho</th><th class="grupo sep" colspan="2">Izquierdo</th>'
    if PULMON in regiones:
        grupos += f'<th class="{clases(PULMON)}" rowspan="2">Pulmón<br>entero</th>'
    filas = []
    for clave, medida in medidas.items():
        celdas = "".join(
            f'<td class="{clases(r, "z")}">{_celda_z(float(z.loc[r, clave]), _orientada(z_orientada, r, clave))}</td>'
            for r in regiones
        )
        filas.append(
            f'<tr><td title="{escape(medida.descripcion or medida.nombre)}">{escape(medida.nombre)}</td>{celdas}</tr>'
        )
    columnas = "".join('<col class="z entero">' if r == PULMON else '<col class="z">' for r in regiones)
    return _envolver(
        f'<div class="ancho"><table class="tabla matriz"><colgroup><col>{columnas}</colgroup>'
        f'<thead><tr>{grupos}</tr><tr><th>Medida (z)</th>{cabecera}</tr></thead>'
        f'<tbody>{"".join(filas)}</tbody></table></div>'
    )


def _orientada(z_orientada: pd.DataFrame, region: str, clave: str) -> float | None:
    if clave not in z_orientada.columns or region not in z_orientada.index:
        return None
    return float(z_orientada.loc[region, clave])


def _pista(z: float, medida: Medida, z_orientada: float | None) -> str:
    dano = f'<span class="dano {medida.peor}"></span>' if medida.peor else ""
    if not math.isfinite(z):
        return f'<div class="pista">{dano}<span class="esperado"></span><span class="cero"></span></div>'
    paso = _paso(z_orientada)
    clase = f"punto d{paso}" if paso else "punto otro" if abs(z) >= UMBRAL_Z else "punto"
    posicion = 50 + 50 * float(np.clip(z, -Z_MAX_PISTA, Z_MAX_PISTA)) / Z_MAX_PISTA
    return (
        f'<div class="pista">{dano}<span class="esperado"></span><span class="cero"></span>'
        f'<span class="{clase}" style="left:{posicion:.1f}%"></span></div>'
    )


def html_detalle(
    region: str, valores: pd.DataFrame, z: pd.DataFrame, z_orientada: pd.DataFrame, medidas: Mapping[str, Medida]
) -> str:
    """Las medidas de una región: valor con unidad, z y dónde cae respecto al rango esperado."""
    nombre_region = "Pulmón entero" if region == PULMON else f"Lóbulo {NOMBRE_LOBULO[region]}"
    filas = []
    for clave, medida in medidas.items():
        valor = float(valores.loc[region, clave]) if region in valores.index else float("nan")
        z_region = float(z.loc[region, clave]) if region in z.index else float("nan")
        if math.isfinite(valor):
            decimales = 0 if float(valor).is_integer() else 1 if abs(valor) >= 10 else 2
            texto_valor = f"{fmt(valor, decimales)} {escape(medida.unidad)}".strip()
        else:
            texto_valor = '<span class="apagado">sin dato</span>'
        texto_z = fmt(z_region, 1, signo=True) if math.isfinite(z_region) else '<span class="apagado">–</span>'
        filas.append(
            f'<tr><td title="{escape((medida.descripcion + " " + _sentido(medida)).strip())}">{escape(medida.nombre)}</td>'
            f'<td class="num">{texto_valor}</td><td class="num"><b>{texto_z}</b></td>'
            f"<td>{_pista(z_region, medida, _orientada(z_orientada, region, clave))}</td></tr>"
        )
    return _envolver(
        f'<div class="ancho"><table class="tabla detalle"><thead><tr><th>{escape(nombre_region)}</th>'
        '<th class="num">Valor</th><th class="num">z</th>'
        f'<th title="La pista va de {fmt(-Z_MAX_PISTA, 0)} a {fmt(Z_MAX_PISTA, 0, signo=True)} desviaciones estándar">'
        f"Desviación (±{fmt(Z_MAX_PISTA, 0)} DE)</th></tr></thead>"
        f'<tbody>{"".join(filas)}</tbody></table></div>'
        f'<p class="nota" style="margin-top:0.25rem">Banda gris: rango esperado, de {fmt(-UMBRAL_Z, 0)} a '
        f"{fmt(UMBRAL_Z, 0, signo=True)} DE. Zona amarilla: lado del daño.</p>"
    )


def _franja(valores: np.ndarray, valor: float | None, cajas: int = 18) -> str:
    """Histograma de la cohorte con una marca en el valor del paciente."""
    minimo, maximo = float(valores.min()), float(valores.max())
    rango = (maximo - minimo) or 1.0
    cuentas, _ = np.histogram(valores, bins=cajas, range=(minimo, minimo + rango))
    barras = "".join(f'<i style="height:{100 * c / cuentas.max():.0f}%"></i>' for c in cuentas)
    marca = ""
    if valor is not None and math.isfinite(valor):
        marca = f'<b style="left:{100 * float(np.clip((valor - minimo) / rango, 0, 1)):.1f}%"></b>'
    return f'<div class="franja" title="De {fmt(minimo, 1)} a {fmt(maximo, 1)} en la cohorte">{barras}{marca}</div>'


@dataclass(frozen=True)
class FilaPerfil:
    """Una variable clínica o biológica del paciente y su contexto en la cohorte."""

    nombre: str
    unidad: str = ""
    texto: str | None = None  # valor del paciente ya formateado; None si no hay dato
    valor: float | None = None  # numéricas: el valor, para situarlo en el histograma
    cohorte: np.ndarray | None = None  # numéricas: valores presentes en la cohorte
    percentil: float | None = None
    iguales: int | None = None  # categóricas: sujetos de la cohorte con el mismo valor
    total: int | None = None


def html_perfil(filas: list[FilaPerfil]) -> str:
    cuerpo = []
    for fila in filas:
        unidad = f' <span class="apagado">{escape(fila.unidad)}</span>' if fila.unidad else ""
        texto = escape(fila.texto) + unidad if fila.texto is not None else '<span class="apagado">sin dato</span>'
        if fila.cohorte is not None and fila.cohorte.size:
            contexto = _franja(fila.cohorte, fila.valor)
        elif fila.iguales is not None:
            contexto = f"{fila.iguales} de {fila.total}"
        else:
            contexto = ""
        pct = f"{fila.percentil:.0f}" if fila.percentil is not None else ""
        cuerpo.append(
            f'<tr><td class="var" title="{escape(fila.nombre)}">{escape(fila.nombre)}</td><td class="num">{texto}</td>'
            f'<td class="ctx">{contexto}</td><td class="pct">{pct}</td></tr>'
        )
    return _envolver(
        '<div class="desliza"><table class="tabla perfil">'
        '<colgroup><col style="width:37%"><col style="width:27%"><col style="width:24%"><col style="width:12%"></colgroup>'
        '<thead><tr><th>Variable</th><th class="num">Paciente</th>'
        '<th>Cohorte</th><th class="num" title="Percentil del paciente en la cohorte">Pct.</th></tr></thead>'
        f'<tbody>{"".join(cuerpo)}</tbody></table></div>'
    )


# ---------------------------------------------------------------------------
# Cohorte
# ---------------------------------------------------------------------------


def _eje(valor: float, inf: float, sup: float, minimo: float, maximo: float, referencia: float, alerta: bool = False) -> str:
    def pos(x: float) -> float:
        return 100 * (float(np.clip(x, minimo, maximo)) - minimo) / (maximo - minimo)

    return (
        f'<div class="eje{" alerta" if alerta else ""}"><span class="ref" style="left:{pos(referencia):.1f}%"></span>'
        f'<span class="ci" style="left:{pos(inf):.1f}%;width:{pos(sup) - pos(inf):.1f}%"></span>'
        f'<span class="pt" style="left:{pos(valor):.1f}%"></span></div>'
    )


def _marcas_eje(minimo: float, maximo: float, marcas: list[float], referencia: float) -> str:
    etiquetas = "".join(
        f'<span class="marca-eje" style="left:{100 * (m - minimo) / (maximo - minimo):.1f}%">'
        f'{fmt(m, 1)}{" (azar)" if abs(m - referencia) < 1e-9 else ""}</span>'
        for m in marcas if minimo <= m <= maximo
    )
    return f'<div class="eje">{etiquetas}</div>'


def _intervalo(inf: float, sup: float, decimales: int = 2, signo: bool = False) -> str:
    return f"({fmt(inf, decimales, signo=signo)} a {fmt(sup, decimales, signo=signo)})"


def _en_frase(nombre: str) -> str:
    """«Escáner» pasa a «escáner» dentro de una frase; una sigla como «IMC» no cambia."""
    return nombre[:1].lower() + nombre[1:] if len(nombre) > 1 and nombre[1].islower() else nombre


def html_escalera(evidencia: Evidencia) -> str:
    """Cada escalón con su métrica e intervalo, y lo que añade sobre el escalón anterior."""
    nombre = escape(evidencia.metrica_nombre)
    azar = evidencia.azar
    extremos = [e.ic95_inf for e in evidencia.escalera] + [azar]
    minimo = min(math.floor(min(extremos) * 10) / 10 - 0.1, azar - 0.2)
    maximo = 1.0
    # Con un eje ancho (Spearman va de -0,2 a 1) las marcas cada 0,2 pisan la etiqueta "(azar)".
    rango = maximo - minimo
    marcas = [round(azar + 0.1 * i, 1) for i in range(-12, 13, 1 if rango <= 0.6 else 2 if rango <= 1.0 else 4)]
    celdas = [
        '<div class="cab">Variables del modelo</div>',
        f'<div class="cab">{nombre} e intervalo del 95 %</div>',
        f'<div class="cab der">{nombre} (IC 95 %)</div>',
        '<div class="cab der">Añade sobre el anterior</div>',
        '<div class="cab der">p de permutación</div>',
    ]
    for e in evidencia.escalera:
        if e.incremento is None:
            incremento = '<span>primer escalón</span>'
            clase_inc = "inc cero"
        else:
            rango = (
                " " + _intervalo(e.incremento_ic95_inf, e.incremento_ic95_sup, signo=True)
                if e.incremento_ic95_inf is not None and e.incremento_ic95_sup is not None else ""
            )
            incluye_cero = e.incremento_ic95_inf is not None and e.incremento_ic95_sup is not None and (
                e.incremento_ic95_inf <= 0 <= e.incremento_ic95_sup)
            clase_inc = "inc cero" if incluye_cero else "inc"
            incremento = f"<b>{fmt(e.incremento, 2, signo=True)}</b><span>{rango}</span>"
        p = "" if e.p_permutacion is None else ("&lt; 0,001" if e.p_permutacion < 0.001 else fmt(e.p_permutacion, 3))
        celdas += [
            f'<div class="fila nombre">{escape(e.escalon)}</div>',
            f'<div class="fila">{_eje(e.metrica, e.ic95_inf, e.ic95_sup, minimo, maximo, azar)}</div>',
            f'<div class="fila valor der"><span><b>{fmt(e.metrica, 2)}</b> <span>{_intervalo(e.ic95_inf, e.ic95_sup)}</span></span></div>',
            f'<div class="fila {clase_inc} der"><span>{incremento}</span></div>',
            f'<div class="fila der">{p}</div>',
        ]
    celdas += ["<div></div>", _marcas_eje(minimo, maximo, marcas, azar), "<div></div>", "<div></div>", "<div></div>"]
    return _envolver(
        '<div class="bosque" style="grid-template-columns: 9.5rem minmax(8rem, 1fr) 9.5rem 11.5rem 5.5rem">'
        f'{"".join(celdas)}</div>'
        '<p class="nota" style="margin-top:0.3rem">En gris, los incrementos cuyo intervalo incluye 0: '
        "no se puede afirmar que ese bloque añada información.</p>"
    )


def titular_controles(evidencia: Evidencia) -> tuple[str, bool]:
    """La lectura de los controles negativos en una frase, y si alguna variable se distingue."""
    distingue = [_en_frase(c.variable) for c in evidencia.controles_negativos if c.distingue]
    no_distingue = [_en_frase(c.variable) for c in evidencia.controles_negativos if not c.distingue]
    if not distingue:
        return f"La puntuación no distingue {lista_con_ni(no_distingue)}.", False
    frase = f"La puntuación distingue {lista_con_y(distingue)}."
    if no_distingue:
        frase += f" No distingue {lista_con_ni(no_distingue)}."
    return frase, True


def html_controles(evidencia: Evidencia) -> str:
    """Controles negativos: AUC de la puntuación para separar variables que no deberían importar."""
    titular, alerta = titular_controles(evidencia)
    extremo = max([0.3] + [abs(x - 0.5) + 0.05 for c in evidencia.controles_negativos for x in (c.ic95_inf, c.ic95_sup)])
    minimo, maximo = 0.5 - extremo, 0.5 + extremo
    celdas = [
        '<div class="cab">Variable</div>', '<div class="cab">AUC e intervalo del 95 %</div>',
        '<div class="cab der">AUC (IC 95 %)</div>', '<div class="cab der">Lectura</div>',
    ]
    for c in evidencia.controles_negativos:
        veredicto = '<span class="veredicto alerta">Distingue</span>' if c.distingue else '<span class="veredicto">No distingue</span>'
        celdas += [
            f'<div class="fila nombre">{escape(c.variable)}</div>',
            f'<div class="fila">{_eje(c.auc, c.ic95_inf, c.ic95_sup, minimo, maximo, 0.5, alerta=c.distingue)}</div>',
            f'<div class="fila valor der"><span><b>{fmt(c.auc, 2)}</b> <span>{_intervalo(c.ic95_inf, c.ic95_sup)}</span></span></div>',
            f'<div class="fila der">{veredicto}</div>',
        ]
    marcas = [round(0.5 + 0.1 * i, 1) for i in (-4, -2, 0, 2, 4)]
    celdas += ["<div></div>", _marcas_eje(minimo, maximo, marcas, 0.5), "<div></div>", "<div></div>"]
    return _envolver(
        f'<p class="titular{" alerta" if alerta else ""}">{escape(titular)}</p>'
        '<p class="nota">Si el intervalo incluye 0,5, la puntuación separa esa variable igual que el azar.</p>'
        '<div class="bosque" style="grid-template-columns: 9.5rem minmax(8rem, 1fr) 9.5rem 8.5rem">'
        f'{"".join(celdas)}</div>'
    )


def html_avisos(avisos: list[str]) -> str:
    puntos = "".join(f"<li>{escape(a)}</li>" for a in avisos)
    return _envolver(f'<div class="avisos"><b>Avisos al cargar la cohorte</b><ul>{puntos}</ul></div>')
