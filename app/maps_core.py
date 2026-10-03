"""Lógica de la app MAPS sin interfaz: carga de la cohorte, orientación de las z,
puntuación de daño y la frase de lectura.

Nada de este módulo importa Streamlit. Todo se prueba con pytest.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# Orden de lectura en pantalla: pulmón derecho (a la izquierda de la imagen), de arriba abajo.
LOBULOS = ("LSD", "LM", "LID", "LSI", "LII")
PULMON = "pulmon"
NOMBRE_LOBULO = {
    "LSD": "superior derecho",
    "LM": "medio",
    "LID": "inferior derecho",
    "LSI": "superior izquierdo",
    "LII": "inferior izquierdo",
}
# Etiquetas de `lobes` en las previsualizaciones (las mismas que `maps.lungs.LOBES`).
ETIQUETA_A_LOBULO = {1: "LSI", 2: "LII", 3: "LSD", 4: "LM", 5: "LID"}

# Una medida a menos de 2 desviaciones estándar de lo esperado está dentro del rango esperado.
# Es el único sitio donde se fija el umbral: la escala de color y los textos lo leen de aquí.
UMBRAL_Z = 2.0
COLUMNA_PUNTUACION = "puntuacion_dano"
# La clase (control, pre-EPOC, EPOC) y la frase que dice qué números la decidieron. Las escribe el análisis.
COLUMNA_CLASE = "clase_maps"
COLUMNA_MOTIVO = "clase_motivo"

CLAVES = ["subject_id", "region"]
MENOS = "−"
SIN_DATO = "sin dato"


class CohorteInvalida(Exception):
    """El directorio no contiene lo mínimo para abrir la app. El mensaje se muestra tal cual."""


# ---------------------------------------------------------------------------
# Medidas y orientación
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Medida:
    clave: str
    nombre: str
    unidad: str = ""
    descripcion: str = ""
    peor: str | None = None  # "menor", "mayor" o None si measures.json no lo dice

    @property
    def signo(self) -> int | None:
        """+1 si más es peor, -1 si menos es peor, None si no se sabe."""
        return {"mayor": 1, "menor": -1}.get(self.peor or "")


def leer_medidas(columnas: list[str], descripcion: Mapping[str, object]) -> dict[str, Medida]:
    """Una `Medida` por columna de los CSV, en el orden de los CSV.

    Las columnas que no están en measures.json se muestran con su nombre de
    columna y sin sentido de daño.
    """
    medidas = {}
    for clave in columnas:
        info = descripcion.get(clave)
        if not isinstance(info, Mapping):
            medidas[clave] = Medida(clave=clave, nombre=clave)
            continue
        peor = str(info.get("peor", "")).strip().lower()
        medidas[clave] = Medida(
            clave=clave,
            nombre=str(info.get("nombre") or clave),
            unidad=str(info.get("unidad") or ""),
            descripcion=str(info.get("descripcion") or ""),
            peor=peor if peor in ("menor", "mayor") else None,
        )
    return medidas


def orientar_z(z: pd.DataFrame, medidas: Mapping[str, Medida]) -> pd.DataFrame:
    """Reorienta las z para que positivo signifique siempre más daño.

    Las medidas sin sentido conocido (`peor` ausente) se descartan: no se puede
    decir si su desviación es daño.
    """
    signos = {c: medidas[c].signo for c in z.columns if c in medidas and medidas[c].signo is not None}
    return z[list(signos)] * pd.Series(signos, dtype=float)


def puntuacion_dano(z_orientada_lobulos: pd.DataFrame) -> float:
    """Puntuación de daño de un sujeto: media de sus z orientadas sobre lóbulos y medidas.

    Entrada: una fila por lóbulo, una columna por medida, positivo es peor.
    Las celdas sin dato no cuentan. Devuelve NaN si no hay ninguna.

    Es el único sitio donde se define la puntuación. Para cambiarla basta con
    sustituir esta función.
    """
    valores = z_orientada_lobulos.to_numpy(dtype=float)
    if not np.isfinite(valores).any():
        return float("nan")
    return float(np.nanmean(valores))


def desviacion_por_lobulo(z_orientada_lobulos: pd.DataFrame, medida: str | None = None) -> pd.Series:
    """El número que tiñe cada lóbulo: la z orientada de `medida` o, sin medida, la mayor del lóbulo."""
    if medida is not None:
        if medida not in z_orientada_lobulos.columns:
            return pd.Series(np.nan, index=z_orientada_lobulos.index)
        return z_orientada_lobulos[medida]
    return z_orientada_lobulos.max(axis=1, skipna=True)


# ---------------------------------------------------------------------------
# Carga
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Escalon:
    escalon: str
    metrica: float
    ic95_inf: float
    ic95_sup: float
    incremento: float | None = None
    incremento_ic95_inf: float | None = None
    incremento_ic95_sup: float | None = None
    p_permutacion: float | None = None


@dataclass(frozen=True)
class ControlNegativo:
    variable: str
    auc: float
    ic95_inf: float
    ic95_sup: float

    @property
    def distingue(self) -> bool:
        """El intervalo del 95 % deja fuera 0,5: la puntuación separa esta variable."""
        return not (self.ic95_inf <= 0.5 <= self.ic95_sup)


@dataclass(frozen=True)
class Evidencia:
    objetivo: str
    metrica_nombre: str
    escalera: tuple[Escalon, ...]
    controles_negativos: tuple[ControlNegativo, ...]

    @property
    def azar(self) -> float:
        """Valor de la métrica sin señal: 0,5 para AUC, 0 para una correlación."""
        return 0.5 if self.metrica_nombre.strip().upper() == "AUC" else 0.0


@dataclass
class Cohorte:
    directorio: Path
    sujetos: pd.DataFrame  # índice subject_id; columnas clínicas y biológicas tal como vienen
    valores: pd.DataFrame  # índice (subject_id, region); una columna por medida de TC
    z: pd.DataFrame  # mismas claves y columnas que `valores`
    medidas: dict[str, Medida]
    evidencia: Evidencia | None
    sintetica: bool
    nota_sintetica: str = ""  # primera línea del fichero SINTETICO: qué es sintético en esta cohorte
    avisos: list[str] = field(default_factory=list)

    def previsualizacion(self, subject_id: str) -> Path:
        return self.directorio / "previews" / f"{subject_id}.npz"


def _numero(valor: object) -> float | None:
    if valor is None or isinstance(valor, bool):
        return None
    try:
        numero = float(valor)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return numero if math.isfinite(numero) else None


def _normalizar_region(region: object) -> str | None:
    texto = str(region).strip()
    if texto.upper() in LOBULOS:
        return texto.upper()
    if texto.lower() in ("pulmon", "pulmón"):
        return PULMON
    return None


def _leer_por_region(ruta: Path, avisos: list[str], que: str) -> pd.DataFrame:
    vacio = pd.DataFrame(index=pd.MultiIndex.from_arrays([[], []], names=CLAVES))
    if not ruta.exists():
        avisos.append(f"Falta {ruta.name}: no hay {que}.")
        return vacio
    try:
        tabla = pd.read_csv(ruta, dtype={"subject_id": str})
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as error:
        avisos.append(f"No se puede leer {ruta.name}: {error}.")
        return vacio
    if not set(CLAVES) <= set(tabla.columns):
        avisos.append(f"{ruta.name} no tiene las columnas subject_id y region: no hay {que}.")
        return vacio
    tabla["region"] = tabla["region"].map(_normalizar_region)
    desconocidas = int(tabla["region"].isna().sum())
    if desconocidas:
        avisos.append(f"{ruta.name}: {desconocidas} filas con una región desconocida, no se usan.")
        tabla = tabla[tabla["region"].notna()]
    tabla = tabla.drop_duplicates(CLAVES).set_index(CLAVES)
    return tabla.apply(pd.to_numeric, errors="coerce").astype(float)


def leer_evidencia(ruta: Path, avisos: list[str]) -> Evidencia | None:
    """Valida evidence.json. Una entrada mal formada se descarta con aviso, no rompe la vista."""
    if not ruta.exists():
        return None
    try:
        crudo = json.loads(ruta.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        avisos.append(f"No se puede leer {ruta.name}: {error}.")
        return None
    if not isinstance(crudo, Mapping):
        avisos.append(f"{ruta.name} no es un objeto JSON.")
        return None

    escalera, controles, descartadas = [], [], 0
    for fila in crudo.get("escalera") or []:
        base = [_numero(fila.get(k)) for k in ("metrica", "ic95_inf", "ic95_sup")] if isinstance(fila, Mapping) else []
        if not base or None in base or not fila.get("escalon"):
            descartadas += 1
            continue
        escalera.append(Escalon(
            str(fila["escalon"]), *base,
            incremento=_numero(fila.get("incremento")),
            incremento_ic95_inf=_numero(fila.get("incremento_ic95_inf")),
            incremento_ic95_sup=_numero(fila.get("incremento_ic95_sup")),
            p_permutacion=_numero(fila.get("p_permutacion")),
        ))
    for fila in crudo.get("controles_negativos") or []:
        base = [_numero(fila.get(k)) for k in ("auc", "ic95_inf", "ic95_sup")] if isinstance(fila, Mapping) else []
        if not base or None in base or not fila.get("variable"):
            descartadas += 1
            continue
        controles.append(ControlNegativo(str(fila["variable"]), *base))
    if descartadas:
        avisos.append(f"{ruta.name}: {descartadas} entradas incompletas, no se muestran.")
    return Evidencia(
        objetivo=str(crudo.get("objetivo") or ""),
        metrica_nombre=str(crudo.get("metrica_nombre") or "AUC"),
        escalera=tuple(escalera),
        controles_negativos=tuple(controles),
    )


def cargar_cohorte(directorio: str | Path) -> Cohorte:
    """Lee un directorio de cohorte. Solo subjects.csv es imprescindible.

    Lo demás puede faltar: cada ausencia deja un aviso en `Cohorte.avisos` y la
    vista correspondiente lo dice.
    """
    directorio = Path(directorio)
    if not directorio.is_dir():
        raise CohorteInvalida(f"No existe el directorio de la cohorte: {directorio}")
    ruta_sujetos = directorio / "subjects.csv"
    if not ruta_sujetos.exists():
        raise CohorteInvalida(f"Falta subjects.csv en {directorio}")
    try:
        sujetos = pd.read_csv(ruta_sujetos, dtype={"subject_id": str})
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as error:
        raise CohorteInvalida(f"No se puede leer subjects.csv: {error}") from error
    if "subject_id" not in sujetos.columns:
        raise CohorteInvalida("subjects.csv no tiene la columna subject_id")

    avisos: list[str] = []
    sujetos = sujetos[sujetos["subject_id"].notna()]
    repetidos = int(sujetos["subject_id"].duplicated().sum())
    if repetidos:
        avisos.append(f"subjects.csv: {repetidos} identificadores repetidos, se usa la primera fila de cada uno.")
        sujetos = sujetos.drop_duplicates("subject_id")
    sujetos = sujetos.set_index("subject_id")
    if len(sujetos) == 0:  # `.empty` también es cierto sin columnas clínicas, y eso sí es válido
        raise CohorteInvalida("subjects.csv no tiene ningún sujeto")

    valores = _leer_por_region(directorio / "features.csv", avisos, "valores de las medidas de TC")
    z = _leer_por_region(directorio / "zscores.csv", avisos, "desviaciones (z) de las medidas de TC")
    columnas = list(dict.fromkeys([*valores.columns, *z.columns]))
    valores = valores.reindex(columns=columnas)
    z = z.reindex(columns=columnas)

    descripcion: Mapping[str, object] = {}
    ruta_medidas = directorio / "measures.json"
    if ruta_medidas.exists():
        try:
            leido = json.loads(ruta_medidas.read_text(encoding="utf-8"))
            if isinstance(leido, Mapping):
                descripcion = leido
            else:
                avisos.append("measures.json no es un objeto JSON: las medidas se muestran sin describir.")
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            avisos.append(f"No se puede leer measures.json: {error}.")
    elif columnas:
        avisos.append("Falta measures.json: las medidas se muestran sin describir y no entran en la puntuación.")
    # "mostrar": false en measures.json retira una medida de la app. Sirve para
    # enseñar una por familia cuando el pipeline calcula muchas.
    ocultas = {c for c, info in descripcion.items() if isinstance(info, Mapping) and info.get("mostrar") is False}
    columnas = [c for c in columnas if c not in ocultas]
    valores, z = valores[columnas], z[columnas]
    medidas = leer_medidas(columnas, descripcion)
    sin_sentido = [m.clave for m in medidas.values() if m.signo is None]
    if sin_sentido and descripcion:
        avisos.append("Medidas sin sentido de daño en measures.json, fuera de la puntuación: " + ", ".join(sin_sentido) + ".")

    marca_sintetica = directorio / "SINTETICO"
    nota_sintetica = ""
    if marca_sintetica.is_file():
        lineas = marca_sintetica.read_text(encoding="utf-8", errors="replace").splitlines()
        nota_sintetica = lineas[0].strip()[:240] if lineas else ""

    return Cohorte(
        directorio=directorio,
        sujetos=sujetos,
        valores=valores,
        z=z,
        medidas=medidas,
        evidencia=leer_evidencia(directorio / "evidence.json", avisos),
        sintetica=marca_sintetica.exists(),
        nota_sintetica=nota_sintetica,
        avisos=avisos,
    )


# ---------------------------------------------------------------------------
# Derivados por sujeto y por cohorte
# ---------------------------------------------------------------------------


def tabla_sujeto(tabla: pd.DataFrame, subject_id: str) -> pd.DataFrame:
    """Filas de un sujeto con índice de región: los cinco lóbulos y, si existe, el pulmón entero."""
    if tabla.empty or subject_id not in tabla.index.get_level_values("subject_id"):
        return pd.DataFrame(index=pd.Index(LOBULOS, name="region"), columns=tabla.columns, dtype=float)
    filas = tabla.xs(subject_id, level="subject_id")
    regiones = [*LOBULOS, PULMON] if PULMON in filas.index else list(LOBULOS)
    return filas.reindex(regiones)


def puntuaciones_cohorte(cohorte: Cohorte) -> pd.Series:
    """Puntuación de daño de cada sujeto de subjects.csv. NaN si no tiene z en ningún lóbulo.

    Si subjects.csv ya trae `puntuacion_dano`, manda esa: es la que usó el
    análisis de evidencia y la app no debe enseñar otra distinta.
    """
    if COLUMNA_PUNTUACION in cohorte.sujetos.columns:
        return pd.to_numeric(cohorte.sujetos[COLUMNA_PUNTUACION], errors="coerce").rename("puntuacion_dano")
    orientada = orientar_z(cohorte.z, cohorte.medidas)
    orientada = orientada[orientada.index.get_level_values("region").isin(LOBULOS)]
    por_sujeto = {sid: puntuacion_dano(filas) for sid, filas in orientada.groupby(level="subject_id")}
    return pd.Series(por_sujeto, dtype=float).reindex(cohorte.sujetos.index).rename("puntuacion_dano")


def percentil(valor: float, cohorte: pd.Series) -> float | None:
    """Percentil del valor entre los datos presentes de la cohorte (rango medio en los empates)."""
    datos = pd.to_numeric(cohorte, errors="coerce").dropna().to_numpy(dtype=float)
    if not math.isfinite(valor) or datos.size == 0:
        return None
    return float(100.0 * ((datos < valor).sum() + 0.5 * (datos == valor).sum()) / datos.size)


def columnas_por_tipo(sujetos: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Separa las columnas clínicas en numéricas y categóricas.

    Una columna numérica con dos valores o menos (0/1, sí/no codificado) se
    trata como categórica: su histograma no dice nada.
    """
    numericas, categoricas = [], []
    for columna in sujetos.columns:
        if columna in (COLUMNA_PUNTUACION, COLUMNA_MOTIVO):  # ya se enseñan en la lectura, no son datos clínicos
            continue
        serie = sujetos[columna]
        if pd.api.types.is_bool_dtype(serie):
            categoricas.append(columna)
        elif pd.api.types.is_numeric_dtype(serie):
            (numericas if serie.nunique(dropna=True) > 2 else categoricas).append(columna)
        else:
            convertida = pd.to_numeric(serie, errors="coerce")
            es_numerica = serie.notna().any() and convertida.notna().sum() == serie.notna().sum()
            (numericas if es_numerica and convertida.nunique() > 2 else categoricas).append(columna)
    return numericas, categoricas


def columnas_de_grupo(sujetos: pd.DataFrame, max_niveles: int = 8) -> list[str]:
    """Columnas categóricas que sirven para agrupar: entre 2 y `max_niveles` valores. `grupo` va primero."""
    _, categoricas = columnas_por_tipo(sujetos)
    candidatas = [c for c in categoricas if 2 <= sujetos[c].nunique(dropna=True) <= max_niveles]
    return sorted(candidatas, key=lambda c: c.strip().lower() not in ("grupo", "group"))


# Orden clínico de los grupos cuando se reconocen sus nombres; el resto va después, por orden alfabético.
ORDEN_CLINICO = ("referencia", "control", "sano", "control sin criterios", "control con síntomas o dlco baja",
                 "control con enfisema", "pre-copd", "precopd", "pre-epoc", "preepoc", "prism", "epoc", "copd")


def orden_grupos(niveles: list[str]) -> list[str]:
    def clave(nivel: str) -> tuple[int, str]:
        nombre = nivel.strip().lower()
        return (ORDEN_CLINICO.index(nombre) if nombre in ORDEN_CLINICO else len(ORDEN_CLINICO), nombre)

    return sorted(niveles, key=clave)


def resumen_por_grupo(puntuaciones: pd.Series, grupos: pd.Series) -> pd.DataFrame:
    """Por grupo: n, media de la puntuación e intervalo de confianza del 95 % de la media (t de Student).

    Solo cuentan los sujetos con puntuación y con grupo. Con un solo sujeto no hay intervalo.
    """
    datos = pd.DataFrame({"puntuacion": puntuaciones, "grupo": grupos}).dropna()
    datos["grupo"] = datos["grupo"].astype(str)
    filas = []
    for grupo in orden_grupos(sorted(datos["grupo"].unique())):
        valores = datos.loc[datos["grupo"] == grupo, "puntuacion"].to_numpy(dtype=float)
        n, media = valores.size, float(valores.mean())
        margen = float(stats.t.ppf(0.975, n - 1) * valores.std(ddof=1) / math.sqrt(n)) if n > 1 else float("nan")
        filas.append({"grupo": grupo, "n": n, "media": media, "ic95_inf": media - margen, "ic95_sup": media + margen})
    return pd.DataFrame(filas, columns=["grupo", "n", "media", "ic95_inf", "ic95_sup"])


# Nombres legibles de las columnas clínicas que la app conoce. Una columna que
# no esté aquí se muestra con su nombre tal cual, sin unidad. Editar aquí cuando
# se conozcan las columnas de la cohorte real.
ETIQUETAS_CLINICAS: dict[str, tuple[str, str]] = {
    "grupo": ("Grupo", ""),
    "edad": ("Edad", "años"),
    "sexo": ("Sexo", ""),
    "talla_cm": ("Talla", "cm"),
    "imc": ("IMC", "kg/m²"),
    "paquetes_ano": ("Tabaco", "paq-año"),
    "fumador_activo": ("Fumador activo", ""),
    "escaner": ("Escáner", ""),
    "fev1_fvc": ("FEV1/FVC", ""),
    "fev1_pct_pred": ("FEV1", "% pred."),
    "dlco_pct_pred": ("DLCO", "% pred."),
    "cat": ("CAT", "puntos"),
    "mmrc": ("mMRC", ""),
    "eosinofilos_cel_ul": ("Eosinófilos", "cél/µL"),
    "pcr_mg_l": ("PCR", "mg/L"),
    "cc16_ng_ml": ("CC16", "ng/mL"),
}


def etiqueta_columna(columna: str) -> tuple[str, str]:
    """(nombre legible, unidad) de una columna clínica; si no se conoce, su propio nombre."""
    return ETIQUETAS_CLINICAS.get(columna.strip().lower(), (columna, ""))


# ---------------------------------------------------------------------------
# Texto: números en formato español y la frase de lectura
# ---------------------------------------------------------------------------


def fmt(valor: float | None, decimales: int = 1, signo: bool = False) -> str:
    """Número con coma decimal y signo menos tipográfico. `signo` añade + a los positivos."""
    if valor is None or not math.isfinite(valor):
        return SIN_DATO
    redondeado = round(float(valor), decimales)
    if redondeado == 0:
        redondeado = 0.0  # evita "-0,0"
    texto = f"{abs(redondeado):.{decimales}f}".replace(".", ",")
    if redondeado < 0:
        return MENOS + texto
    return ("+" if signo and redondeado > 0 else "") + texto


def fmt_auto(valor: float | None) -> str:
    """Número de una variable clínica cualquiera: los decimales dependen de la magnitud."""
    if valor is None or not math.isfinite(valor):
        return SIN_DATO
    if float(valor).is_integer():
        return fmt(valor, 0)
    magnitud = abs(valor)
    return fmt(valor, 0 if magnitud >= 100 else 1 if magnitud >= 10 else 2)


def frase_lectura(z_orientada_lobulos: pd.DataFrame, z_lobulos: pd.DataFrame, medidas: Mapping[str, Medida]) -> str:
    """La lectura del paciente en una frase fija, construida solo con sus números.

    `z_orientada_lobulos` decide qué lóbulo y qué medida se nombran; `z_lobulos`
    (las z tal como vienen) dice si el valor está por encima o por debajo.
    """
    orientada = z_orientada_lobulos.reindex([r for r in LOBULOS if r in z_orientada_lobulos.index])
    if not np.isfinite(z_lobulos.to_numpy(dtype=float)).any():
        return "Este paciente no tiene medidas de TC."
    if orientada.empty or not np.isfinite(orientada.to_numpy(dtype=float)).any():
        return "Hay medidas de TC, pero ninguna tiene definido su sentido de daño. No se puede dar una lectura."
    maximos = desviacion_por_lobulo(orientada).reindex(list(LOBULOS))
    sin_dato = int(maximos.isna().sum())
    falta = "" if sin_dato == 0 else " 1 lóbulo no tiene medidas." if sin_dato == 1 else f" {sin_dato} lóbulos no tienen medidas."
    if not (maximos >= UMBRAL_Z).any():
        return (
            f"Ningún lóbulo se desvía hacia el daño {fmt_auto(UMBRAL_Z)} desviaciones estándar o más. "
            "Las medidas están dentro de lo esperado para su edad, sexo y talla." + falta
        )
    lobulo = str(maximos.idxmax())
    clave = str(orientada.loc[lobulo].idxmax())
    z_cruda = float(z_lobulos.loc[lobulo, clave])
    sentido = "por encima" if z_cruda > 0 else "por debajo"
    return (
        f"El lóbulo {NOMBRE_LOBULO[lobulo]} es el que más se desvía: {medidas[clave].nombre} está "
        f"{fmt(abs(z_cruda), 1)} desviaciones estándar {sentido} de lo esperado para su edad, sexo y talla." + falta
    )


def lista_con_ni(nombres: list[str]) -> str:
    """«escáner», «escáner ni sexo», «escáner, centro ni sexo»."""
    if len(nombres) <= 1:
        return "".join(nombres)
    return ", ".join(nombres[:-1]) + " ni " + nombres[-1]


def lista_con_y(nombres: list[str]) -> str:
    if len(nombres) <= 1:
        return "".join(nombres)
    return ", ".join(nombres[:-1]) + " y " + nombres[-1]
