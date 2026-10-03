"""App de demostración del reto MAPS: un paciente y la evidencia de la cohorte.

    PYTHONPATH=src python -m streamlit run app/maps_app.py -- --cohort <directorio>

El directorio de la cohorte también se puede dar con la variable MAPS_COHORT.
La app no hace ninguna petición fuera de la máquina y no genera texto: todas las
frases son plantillas fijas rellenadas con números de la cohorte.
"""

from __future__ import annotations

import argparse
import html
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import maps_ui as ui
from maps_core import (
    ETIQUETA_A_LOBULO,
    LOBULOS,
    PULMON,
    UMBRAL_Z,
    Cohorte,
    CohorteInvalida,
    cargar_cohorte,
    columnas_de_grupo,
    COLUMNA_CLASE,
    COLUMNA_MOTIVO,
    COLUMNA_PUNTUACION,
    columnas_por_tipo,
    desviacion_por_lobulo,
    etiqueta_columna,
    fmt,
    fmt_auto,
    frase_lectura,
    orientar_z,
    percentil,
    puntuaciones_cohorte,
    resumen_por_grupo,
    tabla_sujeto,
)
from maps_render import CorteCompuesto, Preview, PreviewInvalida, cargar_preview, componer_corte

RAIZ = Path(__file__).resolve().parents[1]
FICHEROS = ("subjects.csv", "features.csv", "zscores.csv", "measures.json", "evidence.json", "SINTETICO")


# ---------------------------------------------------------------------------
# Carga, con caché: cambiar de paciente no vuelve a leer nada del disco
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Datos:
    cohorte: Cohorte
    puntuaciones: pd.Series
    numericas: dict[str, np.ndarray]  # columna clínica numérica -> valores presentes en la cohorte


def directorio_cohorte() -> Path | None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--cohort")
    args, _ = parser.parse_known_args(sys.argv[1:])
    elegido = args.cohort or os.environ.get("MAPS_COHORT")
    if elegido:
        return Path(elegido).expanduser()
    por_defecto = RAIZ / "outputs" / "cohorte_sintetica"
    return por_defecto if por_defecto.is_dir() else None


def firma(directorio: Path) -> tuple[tuple[str, int], ...]:
    """Cambia cuando cambia un fichero de la cohorte, para que la caché se renueve sola."""
    return tuple((n, (directorio / n).stat().st_mtime_ns) for n in FICHEROS if (directorio / n).exists())


@st.cache_resource(show_spinner=False, max_entries=4)
def cargar(directorio: str, firma_ficheros: tuple) -> Datos:
    """`firma_ficheros` solo forma parte de la clave de la caché."""
    cohorte = cargar_cohorte(directorio)
    numericas, _ = columnas_por_tipo(cohorte.sujetos)
    valores = {c: pd.to_numeric(cohorte.sujetos[c], errors="coerce").dropna().to_numpy(dtype=float) for c in numericas}
    return Datos(cohorte, puntuaciones_cohorte(cohorte), valores)


@st.cache_resource(show_spinner=False, max_entries=32)
def preview(ruta: str, mtime: int) -> Preview | str | None:
    """La previsualización de un sujeto, None si falta o el motivo si no se puede leer.

    `mtime` solo forma parte de la clave de la caché.
    """
    try:
        return cargar_preview(Path(ruta))
    except PreviewInvalida as error:
        return str(error)


@st.cache_data(show_spinner=False, max_entries=512)
def corte(
    ruta: str, mtime: int, indice: int, z_por_etiqueta: tuple[tuple[int, float], ...], resaltada: int | None
) -> CorteCompuesto:
    imagen = preview(ruta, mtime)
    assert isinstance(imagen, Preview)
    return componer_corte(
        imagen.hu[indice], imagen.lobes[indice], imagen.espaciado, dict(z_por_etiqueta), resaltada=resaltada
    )


# ---------------------------------------------------------------------------
# Vista de paciente
# ---------------------------------------------------------------------------


def columna_grupo(datos: Datos) -> str | None:
    candidatas = columnas_de_grupo(datos.cohorte.sujetos)
    return candidatas[0] if candidatas and candidatas[0].strip().lower() in ("grupo", "group") else None


def filas_perfil(datos: Datos, subject_id: str) -> list[ui.FilaPerfil]:
    """Una fila por columna de subjects.csv, en su orden: el valor del paciente y su sitio en la cohorte."""
    sujetos = datos.cohorte.sujetos
    paciente = sujetos.loc[subject_id]
    filas = []
    for columna in sujetos.columns:
        if columna in (COLUMNA_PUNTUACION, COLUMNA_CLASE, COLUMNA_MOTIVO):  # ya están en la banda de lectura
            continue
        nombre, unidad = etiqueta_columna(columna)
        crudo = paciente[columna]
        if columna in datos.numericas:
            valor = pd.to_numeric(pd.Series([crudo]), errors="coerce").iloc[0]
            if pd.isna(valor):
                filas.append(ui.FilaPerfil(nombre, cohorte=datos.numericas[columna]))
            else:
                filas.append(ui.FilaPerfil(
                    nombre, unidad, fmt_auto(float(valor)), valor=float(valor), cohorte=datos.numericas[columna],
                    percentil=percentil(float(valor), pd.Series(datos.numericas[columna])),
                ))
        elif pd.isna(crudo):
            filas.append(ui.FilaPerfil(nombre))
        else:
            if isinstance(crudo, (bool, np.bool_)):
                texto = "sí" if crudo else "no"
            elif isinstance(crudo, (int, float, np.number)):
                texto = fmt_auto(float(crudo))
            else:
                texto = str(crudo)
            filas.append(ui.FilaPerfil(
                nombre, unidad, texto,
                iguales=int((sujetos[columna] == crudo).sum()), total=int(sujetos[columna].notna().sum()),
            ))
    return filas


def vista_paciente(datos: Datos, subject_id: str) -> None:
    cohorte = datos.cohorte
    z = tabla_sujeto(cohorte.z, subject_id)
    valores = tabla_sujeto(cohorte.valores, subject_id)
    z_orientada = orientar_z(z, cohorte.medidas)
    lobulos_orientados = z_orientada.loc[list(LOBULOS)]
    hay_medidas = bool(np.isfinite(z.to_numpy(dtype=float)).any() or np.isfinite(valores.to_numpy(dtype=float)).any())
    maximos = desviacion_por_lobulo(lobulos_orientados)
    puntuacion = float(datos.puntuaciones.get(subject_id, float("nan")))

    grupo_columna = columna_grupo(datos)
    grupo = cohorte.sujetos.loc[subject_id, grupo_columna] if grupo_columna else None
    clasificacion, motivo = (
        cohorte.sujetos.loc[subject_id, c] if c in cohorte.sujetos.columns else None for c in (COLUMNA_CLASE, COLUMNA_MOTIVO)
    )
    st.html(ui.html_lectura(
        subject_id,
        str(grupo) if grupo is not None and pd.notna(grupo) else None,
        str(clasificacion) if clasificacion is not None and pd.notna(clasificacion) else None,
        str(motivo) if motivo is not None and pd.notna(motivo) else None,
        frase_lectura(lobulos_orientados, z, cohorte.medidas),
        puntuacion,
        percentil(puntuacion, datos.puntuaciones),
        int(datos.puntuaciones.notna().sum()),
        int((maximos >= UMBRAL_Z).sum()),
        int(maximos.notna().sum()),
    ))

    col_tc, col_tabla, col_perfil = st.columns([0.37, 0.36, 0.27], gap="medium")

    # La tabla va antes en el código: el lóbulo elegido en ella se resalta en la TC.
    region = None
    with col_tabla.container(border=True):
        if not hay_medidas:
            st.html(ui.html_titulo("Desviación por lóbulo y medida"))
            st.html(ui.html_vacio(
                "No hay medidas de TC para este paciente",
                "No aparece en features.csv ni en zscores.csv. Su perfil clínico sí está disponible.",
                alto=True,
            ))
        else:
            st.html(ui.html_titulo(
                "Desviación por lóbulo y medida",
                f"z: desviaciones estándar respecto a lo esperado. Con color, {ui.UMBRAL} o más hacia el daño; "
                f"con borde, {ui.UMBRAL} o más en sentido contrario.",
            ))
            regiones = list(z.index)
            mas_desviado = str(maximos.idxmax()) if maximos.notna().any() else regiones[0]
            hueco_matriz = st.container()
            region = st.segmented_control(
                "Región del detalle", regiones, default=mas_desviado, required=True, key=f"region_{subject_id}",
                format_func=lambda r: "Pulmón entero" if r == PULMON else r, label_visibility="collapsed",
            )
            hueco_matriz.html(ui.html_matriz(z, z_orientada, cohorte.medidas, region))
            st.html(ui.html_detalle(region, valores, z, z_orientada, cohorte.medidas))

    with col_tc.container(border=True):
        ruta = cohorte.previsualizacion(subject_id)
        imagen = preview(str(ruta), ruta.stat().st_mtime_ns if ruta.exists() else 0)
        if imagen is None:
            st.html(ui.html_titulo("TC, corte coronal"))
            st.html(ui.html_vacio(
                "No hay imagen de TC para este paciente",
                f"Falta previews/{subject_id}.npz. Las medidas por lóbulo no dependen de la imagen.",
                alto=True,
            ))
        elif isinstance(imagen, str):
            st.html(ui.html_titulo("TC, corte coronal"))
            st.html(ui.html_vacio("La imagen de TC no se puede mostrar", imagen, alto=True))
        else:
            hueco_imagen = st.container()
            izquierda, derecha = st.columns([0.5, 0.5], gap="medium")
            hay_z = bool(maximos.notna().any())
            medida_tinte = derecha.selectbox(
                "Color según", [None, *z_orientada.columns], key="tinte", disabled=not hay_z,
                format_func=lambda c: "Mayor desviación" if c is None else cohorte.medidas[c].nombre,
                help="La cifra que tiñe cada lóbulo: su medida más desviada hacia el daño, o una medida concreta.",
            )
            indice = 1
            if imagen.cortes > 1:
                indice = izquierda.slider(
                    "Corte, de anterior a posterior", 1, imagen.cortes, value=(imagen.cortes + 1) // 2,
                    key=f"corte_{imagen.cortes}",
                )
            tinte = desviacion_por_lobulo(lobulos_orientados, medida_tinte)
            z_por_etiqueta = tuple(
                (etiqueta, round(float(tinte[lobulo]), 2))
                for etiqueta, lobulo in ETIQUETA_A_LOBULO.items() if pd.notna(tinte.get(lobulo))
            )
            resaltada = next((e for e, lobulo in ETIQUETA_A_LOBULO.items() if lobulo == region), None)
            compuesto = corte(str(ruta), ruta.stat().st_mtime_ns, indice - 1, z_por_etiqueta, resaltada)
            rotulos = {e: (lobulo, dict(z_por_etiqueta).get(e)) for e, lobulo in ETIQUETA_A_LOBULO.items()}
            with hueco_imagen:
                st.html(ui.html_titulo(f"TC, corte coronal {indice} de {imagen.cortes}"))
                st.html(ui.html_tc(compuesto, rotulos))
                st.html(ui.html_leyenda(hay_z))

    with col_perfil.container(border=True):
        filas = filas_perfil(datos, subject_id)
        if filas:
            st.html(ui.html_titulo(
                "Perfil clínico y biológico",
                f"Histograma: los {len(cohorte.sujetos)} sujetos. Marca: este paciente.",
            ))
            st.html(ui.html_perfil(filas))
        else:
            st.html(ui.html_titulo("Perfil clínico y biológico"))
            st.html(ui.html_vacio("No hay variables clínicas", "subjects.csv solo tiene la columna subject_id.", alto=True))


# ---------------------------------------------------------------------------
# Vista de cohorte
# ---------------------------------------------------------------------------


def figura_grupos(puntuaciones: pd.Series, grupos: pd.Series, resumen: pd.DataFrame, seleccionado: str | None) -> go.Figure:
    """Un punto por sujeto y, por grupo, la media con su intervalo de confianza del 95 %."""
    niveles = resumen["grupo"].tolist()
    posicion = {g: i for i, g in enumerate(niveles)}
    datos = pd.DataFrame({"puntuacion": puntuaciones, "grupo": grupos.astype("string")}).dropna()
    datos = datos[datos["grupo"].isin(niveles)]
    dispersion = np.random.default_rng(0).uniform(-0.2, 0.2, len(datos))
    y = datos["grupo"].map(posicion).to_numpy(dtype=float) + 0.12 + dispersion

    fig = go.Figure()
    fig.add_vline(x=0, line_color=ui.TINTA_3, line_width=2, line_dash="dash")
    fig.add_trace(go.Scatter(
        x=datos["puntuacion"], y=y, mode="markers", customdata=[html.escape(str(s)) for s in datos.index],
        marker={"size": 10, "color": ui.GRIS_DATO, "opacity": 0.9, "line": {"color": ui.BLANCO, "width": 1}},
        hovertemplate="%{customdata}<br>Puntuación de daño %{x:+.1f}<extra></extra>",
    ))
    if seleccionado in datos.index:
        fig.add_trace(go.Scatter(
            x=[datos.loc[seleccionado, "puntuacion"]], y=[y[datos.index.get_loc(seleccionado)]], mode="markers+text",
            # El paciente elegido es lo que hay que mirar: el único punto con el acento.
            marker={"size": 15, "color": ui.ACENTO, "line": {"color": ui.TINTA, "width": 2.5}},
            text=[html.escape(str(seleccionado))], textposition="bottom center", textfont={"size": 13, "color": ui.TINTA},
            hoverinfo="skip",
        ))
    con_ic = resumen["ic95_inf"].notna()
    fig.add_trace(go.Scatter(
        x=resumen["media"], y=[posicion[g] - 0.3 for g in niveles], mode="markers",
        marker={"symbol": "diamond", "size": 14, "color": ui.TINTA},
        error_x={
            "type": "data", "symmetric": False, "color": ui.TINTA, "thickness": 3, "width": 0,
            "array": (resumen["ic95_sup"] - resumen["media"]).where(con_ic, 0),
            "arrayminus": (resumen["media"] - resumen["ic95_inf"]).where(con_ic, 0),
        },
        hoverinfo="skip",
    ))
    for g, m, a, b in zip(niveles, resumen["media"], resumen["ic95_inf"], resumen["ic95_sup"]):
        intervalo = f" ({fmt(a, 2, signo=True)} a {fmt(b, 2, signo=True)})" if math.isfinite(a) else ""
        fig.add_annotation(
            x=m, y=posicion[g] - 0.3, yshift=20, text=f"<b>{fmt(m, 2, signo=True)}</b>{intervalo}", showarrow=False,
            font={"size": 15, "color": ui.TINTA}, bgcolor="rgba(255,255,255,0.9)", borderpad=1,
        )
    fig.update_yaxes(
        tickmode="array", tickvals=list(posicion.values()),
        # Plotly interpreta etiquetas HTML en los textos: los nombres que vienen de los datos se escapan.
        ticktext=[f"<b>{html.escape(g)}</b><br>n = {n}" for g, n in zip(niveles, resumen["n"])],
        range=[len(niveles) - 0.45, -0.75], showgrid=False, zeroline=False, fixedrange=True, tickfont={"size": 16},
        automargin=True,
    )
    fig.update_xaxes(
        title={"text": "Puntuación de daño (z media; 0 es lo esperado)", "font": {"size": 15}, "standoff": 8},
        showgrid=True, gridcolor="#ebefee", zeroline=False, fixedrange=True, tickfont={"size": 14}, ticks="outside",
        tickcolor=ui.TINTA, linecolor=ui.TINTA, showline=True, tickformat="+.1f", automargin=True,
    )
    fig.update_layout(
        height=max(120 + 130 * len(niveles), 340), margin={"l": 96, "r": 16, "t": 8, "b": 56}, showlegend=False,
        font={"family": ui.FUENTE, "color": ui.TINTA}, plot_bgcolor=ui.BLANCO, paper_bgcolor=ui.BLANCO,
        separators=",.", dragmode=False,
        hoverlabel={"font": {"family": ui.FUENTE, "size": 15, "color": ui.BLANCO}, "bgcolor": ui.TINTA},
    )
    return fig


def vista_cohorte(datos: Datos, directorio: Path, seleccionado: str | None) -> None:
    cohorte = datos.cohorte
    col_grupos, col_evidencia = st.columns([0.37, 0.63], gap="medium")

    with col_grupos.container(border=True):
        st.html(ui.html_titulo("Puntuación de daño por grupo"))
        candidatas = columnas_de_grupo(cohorte.sujetos)
        if not datos.puntuaciones.notna().any():
            st.html(ui.html_vacio(
                "No hay puntuaciones de daño",
                "Hacen falta zscores.csv y measures.json con el sentido de daño de cada medida.", alto=True,
            ))
        elif not candidatas:
            st.html(ui.html_vacio(
                "No hay ninguna columna para agrupar",
                "subjects.csv no tiene columnas categóricas de entre 2 y 8 valores.", alto=True,
            ))
        else:
            columna = st.selectbox("Agrupar por", candidatas, key="grupo", format_func=lambda c: etiqueta_columna(c)[0])
            resumen = resumen_por_grupo(datos.puntuaciones, cohorte.sujetos[columna])
            st.plotly_chart(
                figura_grupos(datos.puntuaciones, cohorte.sujetos[columna], resumen, seleccionado),
                theme=None, config={"displayModeBar": False}, key="figura_grupos",
            )
            fuera = int(datos.puntuaciones.notna().sum() - resumen["n"].sum())
            st.html(ui.html_nota(
                "Punto: un sujeto. Rombo y barra: media del grupo y su intervalo de confianza del 95 %."
                + (f" El punto amarillo es {seleccionado}." if seleccionado in datos.puntuaciones.dropna().index else "")
                + (f" {fuera} sujetos sin dato en esta columna no aparecen." if fuera else "")
            ))

    evidencia = cohorte.evidencia
    with col_evidencia:
        with st.container(border=True):
            st.html(ui.html_titulo("Controles negativos"))
            if evidencia is None:
                st.html(ui.html_vacio(
                    "No hay evidencia de cohorte",
                    f"Falta evidence.json en {directorio}. Lo escribe el análisis de validación.",
                ))
            elif not evidencia.controles_negativos:
                st.html(ui.html_vacio("No hay controles negativos", "evidence.json no trae la lista controles_negativos."))
            else:
                st.html(ui.html_controles(evidencia))
        with st.container(border=True):
            if evidencia is None:
                st.html(ui.html_titulo("Escalera de evidencia"))
                st.html(ui.html_vacio(
                    "No hay escalera de evidencia",
                    "Aparecerá aquí cuando exista evidence.json: cada bloque de variables con su métrica y su intervalo.",
                ))
            elif not evidencia.escalera:
                st.html(ui.html_titulo("Escalera de evidencia"))
                st.html(ui.html_vacio("No hay escalera de evidencia", "evidence.json no trae la lista escalera."))
            else:
                objetivo = f"Objetivo: {evidencia.objetivo}. " if evidencia.objetivo else ""
                st.html(ui.html_titulo(
                    "Escalera de evidencia",
                    f"{objetivo}Cada escalón añade un bloque de variables al anterior, con la misma validación por sujeto.",
                ))
                st.html(ui.html_escalera(evidencia))

    if cohorte.avisos:
        st.html(ui.html_avisos(cohorte.avisos))


# ---------------------------------------------------------------------------
# Página
# ---------------------------------------------------------------------------


def etiqueta_paciente(datos: Datos, subject_id: str) -> str:
    puntuacion = datos.puntuaciones.get(subject_id, float("nan"))
    if pd.isna(puntuacion):
        return f"{subject_id} · sin medidas de TC"
    return f"{subject_id} · daño {fmt(float(puntuacion), 1, signo=True)}"


def main() -> None:
    st.set_page_config(page_title="MAPS: daño pulmonar por lóbulo", layout="wide", initial_sidebar_state="collapsed")
    st.html(ui.CSS)

    directorio = directorio_cohorte()
    if directorio is None:
        st.html(ui.html_marca())
        st.html(ui.html_vacio(
            "No se ha indicado la cohorte",
            "Arranca la app con «-- --cohort <directorio>» al final del comando o con la variable MAPS_COHORT.", alto=True,
        ))
        return
    try:
        datos = cargar(str(directorio), firma(directorio) if directorio.is_dir() else ())
    except CohorteInvalida as error:
        st.html(ui.html_marca())
        st.html(ui.html_vacio("No se puede abrir la cohorte", str(error), alto=True))
        return

    if datos.cohorte.sintetica:
        st.html(ui.html_sintetico(datos.cohorte.nota_sintetica))

    col_marca, col_vista, col_paciente, col_orden = st.columns([0.36, 0.17, 0.27, 0.20], vertical_alignment="bottom", gap="medium")
    col_marca.html(ui.html_marca())
    vista = col_vista.segmented_control(
        "Vista", ["Paciente", "Cohorte"], default="Paciente", required=True, key="vista", bind="query-params",
        label_visibility="collapsed",
    )

    if vista == "Paciente":
        orden = col_orden.segmented_control(
            "Ordenar por", ["Mayor daño", "Identificador"], default="Mayor daño", required=True, key="orden",
        )
        ids = list(datos.cohorte.sujetos.index)
        if orden == "Mayor daño":
            ids = list(datos.puntuaciones.sort_values(ascending=False, na_position="last", kind="stable").index)
        else:
            ids = sorted(ids)
        # El paciente va en la URL (?paciente=<subject_id>) para poder abrir la demo en un caso concreto.
        en_url = st.query_params.get("paciente")
        subject_id = col_paciente.selectbox(
            f"Paciente ({len(ids)} en la cohorte)", ids, index=ids.index(en_url) if en_url in ids else 0,
            key="paciente_elegido", persist_state="session",
            format_func=lambda s: etiqueta_paciente(datos, s), placeholder="Escribe para buscar",
        )
        st.query_params["paciente"] = subject_id
        vista_paciente(datos, subject_id)
    else:
        col_paciente.html(ui.html_nota(
            f"{len(datos.cohorte.sujetos)} sujetos, {int(datos.puntuaciones.notna().sum())} con puntuación de daño."
        ))
        vista_cohorte(datos, directorio, st.session_state.get("paciente_elegido") or st.query_params.get("paciente"))


main()
