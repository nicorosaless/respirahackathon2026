"""Datos de ejemplo para la app web: sujetos SIMULADOS con los agregados reales del repo.

La app web lee un solo fichero, `public/data/cohorte.json`, y los cortes de TC de
`public/data/previews/`. Este script los escribe sin tocar ningún dato del reto:

- Los sujetos son inventados. Se generan para que su reparto por clase y sus
  medianas se parezcan a los de `docs/cifras.md`, y van marcados como simulados.
- Las cifras de las comprobaciones y de la escalera se copian de
  `docs/figuras/comprobaciones.json` y `docs/figuras/escalera.json`, que son agregados
  de los 80 sujetos con el modelo final. `validacion_anidada.json` es la validación de
  ese modelo fuera de muestra.
- Los cortes de TC son de LIDC-IDRI (públicas, CC BY 3.0), ya segmentadas.
- La primera prueba, en 15 sujetos de reserva y con el modelo anterior (`reserva`), se
  copia de `docs/figuras/reserva.json` si existe. Si no, va `null` y la app dice que
  está pendiente. Lo mismo con la validación (`validacion`), el experimento ciego
  (`umbral_natural`), la complejidad (`complejidad`) y el embudo (`embudo`).

    python web/scripts/make_fixture.py --previews outputs/cohorte/previews --mascaras outputs/cohorte/sujetos

Con `--docs` se leen los agregados de otro checkout del repo.

El contrato del fichero está en `web/lib/cohorte.ts`. La cohorte real saldrá de
MareNostrum con esa misma forma.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "app"))

from maps_render import cargar_preview, encuadre, orientar_cabeza_arriba, ventana_pulmon  # noqa: E402

LOBULOS = {1: "LSI", 2: "LII", 3: "LSD", 4: "LM", 5: "LID"}
UMBRAL_COCIENTE = 0.70
ALTO_PX = 560
SUJETOS_RESERVA = 15
# El modelo que se probó en reserva se ajustó con 62 sujetos. Entre dos reconstrucciones, su puntuación se movía 0,186:
# es la zona gris de aquel modelo (`docs/cifras.md` del 2 de octubre a mediodía; `reserva.json` no la trae).
SUJETOS_DEL_MODELO_PROBADO = 62
ZONA_GRIS_DEL_MODELO_PROBADO = 0.186
# El mismo margen que `maps.features.coronal_preview` deja alrededor del pulmón.
MARGEN_PREVIEW = 10


def numero(valor: float, decimales: int) -> str:
    # El 5 final redondea hacia arriba, igual que `num` en la web: −0,295 es −0,30 en los dos sitios.
    escala = 10 ** decimales
    redondeado = math.floor(abs(valor) * escala + 0.5 + 1e-9) / escala
    return f"{'−' if valor < 0 and redondeado else ''}{redondeado:.{decimales}f}".replace(".", ",")


def motivo(cociente: float, puntuacion: float, umbral: float) -> str:
    """La misma plantilla que `maps.classify.explain`. La función (PRISm) ya no entra en la regla."""
    if cociente < UMBRAL_COCIENTE:
        return f"FEV1/FVC de {numero(cociente, 2)}, por debajo de {numero(UMBRAL_COCIENTE, 2)}: hay obstrucción."
    inicio = f"Sin obstrucción (FEV1/FVC de {numero(cociente, 2)})"
    # Se escribe la puntuación que se guarda (tres decimales): así la frase y la cifra grande de la web dicen lo mismo.
    medido = f"puntuación de {numero(round(puntuacion, 3), 2)} con el umbral en {numero(umbral, 2)}"
    if puntuacion >= umbral:
        return f"{inicio}, con la TC parecida a la de la EPOC: {medido}."
    return f"{inicio}, con la TC por debajo del umbral ({medido})."


def exportar_cortes(origen: Path, destino: Path) -> dict[str, dict]:
    """Cada TC pública como cortes en gris y su mapa de lóbulos, con la proporción real."""
    destino.mkdir(parents=True, exist_ok=True)
    imagenes = {}
    for ruta in sorted(origen.glob("*.npz")):
        preview = cargar_preview(ruta)
        if preview is None:
            continue
        alto_mm = preview.hu.shape[1] * preview.espaciado[0]
        ancho_mm = preview.hu.shape[2] * preview.espaciado[1]
        tamano = (int(round(ALTO_PX * ancho_mm / alto_mm)), ALTO_PX)
        cortes = []
        # El filtro gaussiano de 1 mm de `laa950_smooth`, como `scripts/export_web.py` con la cohorte real.
        sigma = (1.0 / preview.espaciado[0], 1.0 / preview.espaciado[1])
        for k in range(preview.cortes):
            suave = gaussian_filter(preview.hu[k].astype(np.float32), sigma)
            gris = Image.fromarray(ventana_pulmon(suave)).resize(tamano, Image.Resampling.BICUBIC)
            etiquetas = Image.fromarray(preview.lobes[k].astype(np.uint8)).resize(tamano, Image.Resampling.NEAREST)
            gris.save(destino / f"{ruta.stem}-{k}.png", optimize=True)
            # Los píxeles de pulmón por debajo de -950 HU: la app los pinta en rojo.
            enfisema = (preview.lobes[k] > 0) & (suave < -950)
            Image.fromarray(enfisema.astype(np.uint8) * 255).resize(tamano, Image.Resampling.NEAREST).save(
                destino / f"{ruta.stem}-{k}-enfisema.png", optimize=True)
            # El mapa guarda el número de lóbulo (0 a 5) como nivel de gris: el navegador lo lee píxel a píxel.
            etiquetas.save(destino / f"{ruta.stem}-{k}-lobulos.png", optimize=True)
            matriz, centros = np.asarray(etiquetas), {}
            for etiqueta, nombre in LOBULOS.items():
                filas, columnas = np.nonzero(matriz == etiqueta)
                if filas.size >= 0.004 * matriz.size:
                    centros[nombre] = [round(float(np.median(columnas)) / tamano[0], 4),
                                       round(float(np.median(filas)) / tamano[1], 4)]
            cortes.append({"centros": centros})
        imagenes[ruta.stem] = {"ancho": tamano[0], "alto": tamano[1], "cortes": cortes}
    return imagenes


def exportar_arboles(mascaras: Path | None, origen: Path, destino: Path, imagenes: dict[str, dict]) -> set[str]:
    """La máscara del árbol bronquial de cada TC, proyectada de delante atrás y encuadrada como sus cortes.

    Repite el recorte de `maps.features.coronal_preview` (mismo rango en z y en x, z invertido) y después la
    orientación y el encuadre de `cargar_preview`, para que la máscara se pueda poner encima de cualquier corte.
    Devuelve las TC que tienen máscara.
    """
    con_arbol: set[str] = set()
    if mascaras is None:
        return con_arbol
    for clave, imagen in imagenes.items():
        ruta = mascaras / clave / "masks.npz"
        if not ruta.exists():
            continue
        with np.load(ruta) as datos:
            pulmon, via = datos["lobes"] > 0, datos["airway"].astype(bool)
        z_con, x_con = (np.flatnonzero(pulmon.any(axis=ejes)) for ejes in ((1, 2), (0, 1)))
        z0, z1 = max(z_con[0] - MARGEN_PREVIEW, 0), min(z_con[-1] + MARGEN_PREVIEW, pulmon.shape[0])
        x0, x1 = max(x_con[0] - MARGEN_PREVIEW, 0), min(x_con[-1] + MARGEN_PREVIEW, pulmon.shape[2])
        proyeccion = via[z0:z1, :, x0:x1].any(axis=1)[::-1]
        with np.load(origen / f"{clave}.npz") as datos:
            lobulos, espaciado = datos["lobes"], np.asarray(datos["spacing"], dtype=float).ravel()
        if proyeccion.shape != lobulos.shape[1:]:
            print(f"{clave}: la máscara del árbol ({proyeccion.shape}) no coincide con los cortes ({lobulos.shape[1:]}); se omite")
            continue
        repetida, orientados = orientar_cabeza_arriba(np.broadcast_to(proyeccion, lobulos.shape), lobulos)
        filas, columnas = encuadre(orientados, (float(espaciado[0]), float(espaciado[1])))
        mascara = Image.fromarray(repetida[0][filas, columnas].astype(np.uint8) * 255)
        mascara = mascara.resize((imagen["ancho"], imagen["alto"]), Image.Resampling.BICUBIC).point(lambda v: 255 if v >= 128 else 0)
        mascara.save(destino / f"{clave}-arbol.png", optimize=True)
        con_arbol.add(clave)
    return con_arbol


# (clase, puntuación en el umbral o por encima, FEV1 por debajo del 80 %, cuántos). El reparto es el de `docs/cifras.md`:
# con los 80 sujetos, 38 control, 14 posible pre-EPOC y 28 EPOC. La clase intermedia es solo "sin obstrucción y con la
# TC parecida a la de la EPOC": un FEV1 bajo ya no cambia la clase, aunque algún sujeto lo tenga.
# Los 15 de reserva son los de la primera prueba: 6 con EPOC y 9 sin obstrucción, 4 de ellos por encima del umbral.
GRUPOS_RESERVA = [("control", False, False, 4), ("control", False, True, 1), ("pre-EPOC", True, False, 4), ("EPOC", True, False, 6)]
# El resto: los 62 con los que se ajustó el primer modelo y los 3 recuperados con la otra reconstrucción.
GRUPOS_DESARROLLO = [("control", False, False, 30), ("control", False, True, 3), ("pre-EPOC", True, False, 8), ("pre-EPOC", True, True, 2),
                     ("EPOC", True, False, 20), ("EPOC", False, False, 2)]
# Las medidas que nombra el reto y no entran en la puntuación: (clave, nombre, unidad, valor típico, cuánto cambia por desviación).
TRADICIONALES = [("laa950", "%LAA-950", "%", None, None), ("via_grosor_pared_mm", "Grosor de pared, estimado", "mm", 1.25, 0.09),
                 ("via_pi10_mm", "Pi10, aproximado", "mm", 3.75, 0.12), ("via_disanapsia", "Disanapsia, aproximada", "", 0.46, -0.03)]


def lectura_congelada(extra: np.random.Generator, modelo: dict, sujeto: dict, umbral_final: float) -> dict:
    """Lo que dijo de un sujeto de reserva el modelo ajustado sin él, coherente con la prueba real.

    El sujeto queda al mismo lado del umbral de aquel modelo que del umbral del modelo final: así los 15 simulados
    reproducen la tabla de la prueba (los 6 con obstrucción por encima; de los 9 sin ella, 4 por encima).
    Las medidas son las mismas; cambian lo esperado, las desviaciones y la puntuación.
    """
    umbral, normalidad = modelo["umbral_dano"], modelo["umbral_normalidad"]
    desplazamiento = (umbral - umbral_final) + float(extra.normal(0, 0.06))
    puntuacion = sujeto["puntuacion"] + desplazamiento
    puntuacion = max(puntuacion, umbral + 0.03) if sujeto["dano_tc"] else min(puntuacion, umbral - 0.03)
    desplazamiento = puntuacion - sujeto["puntuacion"]
    cociente = sujeto["clinica"]["fev1_fvc"]
    dano = puntuacion >= umbral
    clase = "EPOC" if cociente < UMBRAL_COCIENTE else "pre-EPOC" if dano else "control"
    return {
        "puntuacion": round(puntuacion, 3),
        "dano_tc": dano,
        "clase": clase,
        "motivo": motivo(cociente, puntuacion, umbral),
        "cerca_umbral": abs(puntuacion - umbral) < modelo["zona_gris"],
        "nivel_tc": "alta" if puntuacion >= normalidad else "intermedia" if dano else "esperada",
        "z": {"enfisema": round(sujeto["z"]["enfisema"] + desplazamiento, 2), "via": round(sujeto["z"]["via"] + desplazamiento, 2)},
        "valores": dict(sujeto["valores"]),
        "esperado": {"laa950_smooth": round(sujeto["esperado"]["laa950_smooth"] * 1.04, 3),
                     "via_longitud_mm": int(round(sujeto["esperado"]["via_longitud_mm"] - 25))},
    }


def exportar_tc_publica(origen: Path, mascaras: Path | None, destino: Path, clave: str) -> None:
    """La TC pública que enseñan las diapositivas: un corte y, como capas transparentes, los lóbulos y el árbol bronquial.

    Las diapositivas nunca enseñan una TC de la cohorte del reto: usan estas imágenes, que no viven en `data/`.
    `tc-duro.png` no es otra reconstrucción: es el mismo corte realzado, para ilustrar qué cambia con otro filtro.
    """
    from PIL import ImageFilter

    destino.mkdir(parents=True, exist_ok=True)
    preview = cargar_preview(origen / f"{clave}.npz")
    corte = preview.cortes // 2
    alto_mm, ancho_mm = preview.hu.shape[1] * preview.espaciado[0], preview.hu.shape[2] * preview.espaciado[1]
    tamano = (int(round(900 * ancho_mm / alto_mm)), 900)
    gris = Image.fromarray(ventana_pulmon(preview.hu[corte])).resize(tamano, Image.Resampling.BICUBIC)
    gris.save(destino / "tc.png", optimize=True)
    rng = np.random.default_rng(3)
    realzado = np.asarray(gris.filter(ImageFilter.UnsharpMask(radius=3, percent=260, threshold=0)), dtype=float)
    Image.fromarray(np.clip(realzado + rng.normal(0, 13, realzado.shape), 0, 255).astype(np.uint8)).save(destino / "tc-duro.png", optimize=True)

    etiquetas = np.asarray(Image.fromarray(preview.lobes[corte].astype(np.uint8)).resize(tamano, Image.Resampling.NEAREST))
    # Un píxel es borde si su vecino de abajo o de la derecha es de otro lóbulo. Tres píxeles de grosor, para que se vea de lejos.
    borde = np.zeros(etiquetas.shape, dtype=bool)
    borde[:-1, :] |= etiquetas[:-1, :] != etiquetas[1:, :]
    borde[:, :-1] |= etiquetas[:, :-1] != etiquetas[:, 1:]
    borde = np.asarray(Image.fromarray(borde.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(3))) > 0
    capa = np.zeros((*etiquetas.shape, 4), dtype=np.uint8)
    capa[etiquetas == 0] = (0, 0, 0, 110)  # lo de fuera del pulmón se apaga
    capa[borde] = (255, 255, 255, 235)
    Image.fromarray(capa, "RGBA").filter(ImageFilter.GaussianBlur(0.6)).save(destino / "tc-lobulos.png", optimize=True)

    arbol = Image.open(destino.parent / "data" / "previews" / f"{clave}-arbol.png").convert("L").resize(tamano, Image.Resampling.BICUBIC)
    blanco = Image.new("RGBA", tamano, (255, 255, 255, 0))
    blanco.putalpha(arbol)
    blanco.save(destino / "tc-arbol.png", optimize=True)


def experimento_ciego(extra: np.random.Generator, sujetos: list[dict], natural: dict | None) -> None:
    """El grupo ciego de cada sujeto simulado, con los recuentos reales de `umbral_natural.json`.

    Sin etiquetas, la TC parte la cohorte en un grupo alto y otro bajo. En el alto caen casi todos los que tienen
    obstrucción y unos pocos sin ella: aquí se reparten por su puntuación, para que los recuentos coincidan.
    """
    if natural is None:
        for sujeto in sujetos:
            sujeto["ciego"] = None
        return
    grupos = natural["dos_grupos_por_la_tc"]
    umbral = float(grupos["umbral_de_puntuacion"])
    casos_arriba = int(grupos["con_obstruccion_por_encima"].split(" de ")[0])
    controles_arriba = int(grupos["por_encima"]) - casos_arriba
    for caso, cuantos in ((True, casos_arriba), (False, controles_arriba)):
        grupo = sorted((s for s in sujetos if s["caso"] == caso), key=lambda s: -s["puntuacion"])
        for puesto, sujeto in enumerate(grupo):
            alto = puesto < cuantos
            ciega = 0.55 * sujeto["puntuacion"] + float(extra.normal(0, 0.3))
            ciega = max(ciega, umbral + 0.04 + abs(float(extra.normal(0, 0.15)))) if alto else min(ciega, umbral - 0.04 - abs(float(extra.normal(0, 0.15))))
            sujeto["ciego"] = {"puntuacion": round(ciega, 3), "grupo": "alto" if alto else "bajo"}


def elegir_ejemplos(sujetos: list[dict], zona_gris: float) -> dict:
    """Los sujetos simulados que abre la demo, con la misma forma que `scripts/pick_examples.py`."""
    def eleccion(candidatos: list[dict], distancia) -> dict:
        orden = sorted(candidatos, key=distancia)
        return {"elegido": orden[0]["id"] if orden else None, "alternativas": [s["id"] for s in orden[1:4]], "candidatos": len(orden)}

    clases = {}
    for clase in ("control", "pre-EPOC", "EPOC"):
        grupo = [s for s in sujetos if s["clase"] == clase]
        centro = float(np.median([s["puntuacion"] for s in grupo]))
        cociente = float(np.median([s["clinica"]["fev1_fvc"] for s in grupo]))
        candidatos = [s for s in grupo if s["arbol"] and not s["cerca_umbral"]]
        clases[clase] = eleccion(candidatos, lambda s: abs(s["puntuacion"] - centro) + 10 * abs(s["clinica"]["fev1_fvc"] - cociente))
    reserva = [s for s in sujetos if s["particion"] == "reserva" and s["congelado"] and s["arbol"] and s["caso"] and s["congelado"]["dano_tc"]]
    return {
        "criterio": "De cada clase, el sujeto más cercano a la mediana de su clase en puntuación y en FEV1/FVC, con el árbol segmentado y lejos del umbral.",
        "clases": clases,
        "inferencia": {**eleccion(reserva, lambda s: -s["congelado"]["puntuacion"]),
                       "criterio": "Un sujeto de reserva con obstrucción y con la TC claramente por encima del umbral del modelo probado."},
    }


def simular_grupo(rng: np.random.Generator, extra: np.random.Generator, umbral: float, normalidad: float, zona_gris: float, imagenes: list[str],
                  con_arbol: set[str], grupos: list[tuple[str, bool, bool, int]], particion: str, modelo_probado: dict | None) -> list[dict]:
    """Sujetos inventados con el reparto de clases pedido."""
    sujetos = []
    for clase, dano, fev1_bajo, cuantos in grupos:
        for _ in range(cuantos):
            if clase == "EPOC":
                # Con el modelo final, alguna persona con EPOC queda por debajo del umbral.
                puntuacion = float(np.clip(rng.gamma(2.0, 0.7) + umbral + 0.05, None, 5.6)) if dano else float(umbral - rng.uniform(0.1, 0.5))
                cociente = float(np.clip(0.672 - 0.026 * puntuacion + rng.normal(0, 0.028), 0.42, 0.689))
                fev1 = float(np.clip(78 - 4.0 * puntuacion + rng.normal(0, 9), 38, 96))
            else:
                if dano:
                    puntuacion = float(umbral + 0.04 + abs(rng.normal(0, 0.4)))
                else:
                    puntuacion = float(min(rng.normal(-0.25, 0.4), umbral - 0.04))
                # En la reserva el cociente no se queda en 0,70 redondeado: al revelarlo tiene que leerse a qué lado cae.
                cociente = float(np.clip(rng.normal(0.74 if dano else 0.785, 0.03), 0.705 if particion == "desarrollo" else 0.715, 0.88))
                fev1 = float(rng.uniform(66, 79)) if fev1_bajo else float(np.clip(rng.normal(97, 9), 81, 122))
            # La vía aérea lleva más señal que el enfisema: a esta edad casi no hay enfisema.
            reparto = float(rng.normal(0.35, 0.55))
            z_via, z_enfisema = puntuacion + reparto, puntuacion - reparto
            lobulos = {nombre: round(float(z_enfisema + (0.35 if nombre in ("LSD", "LSI") else -0.15)
                                           + rng.normal(0, 0.45)), 2) for nombre in ("LSD", "LM", "LID", "LSI", "LII")}
            sexo = str(rng.choice(["H", "M"]))
            fuma = bool(rng.random() < (0.55 if clase == "EPOC" else 0.82))
            # Las dos reconstrucciones de la misma TC. El %LAA-950 clásico cambia de sujeto a sujeto
            # con el kernel (acuerdo de 0,17); la puntuación no (0,98).
            clasico = float(10 ** (-0.75 + 0.33 * z_enfisema + rng.normal(0, 0.18)))
            clasico_duro = float(10 ** (0.62 + 0.10 * z_enfisema + rng.normal(0, 0.26)))
            otra_puntuacion = puntuacion + float(rng.normal(0, 0.15))
            edad = int(rng.integers(35, 51))
            talla = int(round((176 if sexo == "H" else 163) + rng.normal(0, 6)))
            paquetes = round(float(np.clip(rng.normal({"control": 19, "pre-EPOC": 23, "EPOC": 29}[clase], 7), 10, 60)), 1)
            dlco = round(float(np.clip(rng.normal(75, 13), 40, 115)), 1)
            cat = int(np.clip(round(rng.normal({"control": 5, "pre-EPOC": 9, "EPOC": 11}[clase], 4)), 0, 32))
            kvp = int(rng.choice([80, 100, 120], p=[0.26, 0.52, 0.22]))
            imagen = str(rng.choice(imagenes)) if imagenes else None
            if particion == "reserva" and con_arbol and extra.random() < 0.7:
                # En la reserva se prefieren las TC con árbol segmentado: la vista de inferencia lo enseña en el segundo paso.
                imagen = str(extra.choice(sorted(con_arbol)))

            # Lo esperado para su edad, sexo, talla y tabaco, y el valor medido que da esa desviación.
            # El enfisema se compara en logaritmo: la desviación dice cuántas veces se multiplica.
            esperado_enfisema = 0.04 * (1.0 if fuma else 1.3) * (1 + 0.01 * (edad - 42))
            esperado_via = 5300 + 16 * (talla - 170) - 9 * (edad - 42) - (90 if fuma else 0)
            tradicionales = []
            for clave, nombre, unidad, tipico, por_desviacion in TRADICIONALES:
                if clave == "laa950":
                    valor, z = clasico, z_enfisema + float(extra.normal(0, 0.8))
                else:
                    z = 0.45 * puntuacion + float(extra.normal(0, 0.9))
                    valor = tipico + por_desviacion * z
                # La disanapsia falta cuando no se encuentran bastantes vías centrales.
                falta = clave == "via_disanapsia" and extra.random() < 0.05
                tradicionales.append({"medida": clave, "nombre": nombre, "unidad": unidad,
                                      "valor": None if falta else round(float(valor), 3), "z": None if falta else round(z, 2)})

            sujetos.append({
                "particion": particion,
                "clase": clase,
                "motivo": motivo(cociente, puntuacion, umbral),
                "caso": cociente < UMBRAL_COCIENTE,
                "dano_tc": puntuacion >= umbral,
                "cerca_umbral": abs(puntuacion - umbral) < zona_gris,
                "puntuacion": round(puntuacion, 3),
                # La puntuación con un modelo que no vio al sujeto se parece mucho, no es idéntica.
                "fuera_de_muestra": round(puntuacion + float(extra.normal(0, 0.1)), 3),
                "nivel_tc": "alta" if puntuacion >= normalidad else "intermedia" if puntuacion >= umbral else "esperada",
                "z": {"enfisema": round(z_enfisema, 2), "via": round(z_via, 2)},
                "valores": {
                    "laa950_smooth": round(esperado_enfisema * 10 ** (0.42 * z_enfisema), 3),
                    "via_longitud_mm": int(round(esperado_via - 430 * z_via)),
                },
                "esperado": {"laa950_smooth": round(esperado_enfisema, 3), "via_longitud_mm": int(round(esperado_via))},
                "tradicionales": tradicionales,
                "lobulos": lobulos,
                "kernels": {
                    "laa950": [round(clasico, 3), round(clasico_duro, 3)],
                    "puntuacion": [round(puntuacion, 3), round(otra_puntuacion, 3)],
                },
                "clinica": {
                    "edad": edad,
                    "sexo": sexo,
                    "talla": talla,
                    "fuma": fuma,
                    # En la tabla del reto faltan los paquetes-año de algunos sujetos.
                    "paquetes_ano": None if extra.random() < 0.05 else paquetes,
                    "fev1_fvc": round(cociente, 3),
                    "fev1_pct": round(fev1, 1),
                    "dlco_pct": dlco,
                    "cat": cat,
                    "kvp": kvp,
                },
                "imagen": imagen,
                "arbol": imagen in con_arbol,
            })
            # Solo los de reserva llevan la lectura del modelo que no los vio.
            sujetos[-1]["congelado"] = (lectura_congelada(extra, modelo_probado, sujetos[-1], umbral)
                                        if particion == "reserva" and modelo_probado else None)
    return sujetos


def simular_sujetos(rng: np.random.Generator, umbral: float, normalidad: float, zona_gris: float, imagenes: list[str], con_arbol: set[str],
                    modelo_probado: dict | None) -> list[dict]:
    """80 sujetos inventados con el reparto de clases de la cohorte: 65 de desarrollo y los 15 de la primera prueba."""
    extra = np.random.default_rng(2026)
    salida = []
    for grupos, particion, prefijo in ((GRUPOS_DESARROLLO, "desarrollo", "SIM-"), (GRUPOS_RESERVA, "reserva", "SIM-R")):
        assert sum(grupo[3] for grupo in grupos) == (SUJETOS_RESERVA if particion == "reserva" else 65)
        sujetos = simular_grupo(rng, extra, umbral, normalidad, zona_gris, imagenes, con_arbol, grupos, particion, modelo_probado)
        assert particion != "reserva" or len(sujetos) == SUJETOS_RESERVA
        orden = rng.permutation(len(sujetos))
        salida += [{"id": f"{prefijo}{i:02d}", **sujetos[j]} for i, j in enumerate(orden, start=1)]
    # El caso con el que se abre la vista de sujeto (pre-EPOC solo por la TC, el de más puntuación) lleva una TC con el árbol.
    entrada = [s for s in salida if s["clase"] == "pre-EPOC" and s["dano_tc"] and s["particion"] == "desarrollo"]
    if entrada and con_arbol:
        caso = max(entrada, key=lambda s: s["puntuacion"])
        caso["imagen"], caso["arbol"] = sorted(con_arbol)[0], True
    return salida


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--previews", type=Path, required=True, help="directorio con los .npz de las TC públicas")
    parser.add_argument("--mascaras", type=Path, help="directorio con <TC>/masks.npz, para la máscara del árbol bronquial")
    parser.add_argument("--docs", type=Path, default=REPO / "docs", help="de dónde se leen los agregados (figuras/*.json)")
    parser.add_argument("--out", type=Path, default=REPO / "web" / "public" / "data")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    figuras = args.docs / "figuras"
    comprobaciones = json.loads((figuras / "comprobaciones.json").read_text())
    escalera = json.loads((figuras / "escalera.json").read_text())
    # La primera prueba, en los sujetos de reserva, y la validación del modelo final. Son agregados reales: no se inventan.
    reserva = json.loads((figuras / "reserva.json").read_text()) if (figuras / "reserva.json").exists() else None
    validacion = json.loads((figuras / "validacion_anidada.json").read_text()) if (figuras / "validacion_anidada.json").exists() else None
    # Con qué va la puntuación dentro de cada grupo: el análisis exploratorio de `scripts/explore_outliers.py`.
    discordantes = json.loads((figuras / "discordantes.json").read_text()) if (figuras / "discordantes.json").exists() else None
    # El experimento ciego: la TC parte la cohorte en dos grupos sin saber quién es caso.
    natural = json.loads((figuras / "umbral_natural.json").read_text()) if (figuras / "umbral_natural.json").exists() else None
    # Menos es más: la AUC fuera de muestra según cuántas medidas entran, la clínica y la caída del FEV1.
    complejidad = json.loads((figuras / "complejidad.json").read_text()) if (figuras / "complejidad.json").exists() else None
    # Cómo se eligieron las dos medidas: los tres filtros por los que pasa cada una de las 27.
    embudo = json.loads((figuras / "embudo.json").read_text()) if (figuras / "embudo.json").exists() else None
    umbral = float(comprobaciones["umbral_dano"])
    # A menos de esta distancia del umbral la decisión se avisa como poco firme: lo que se mueve la puntuación entre los dos filtros del escáner.
    zona_gris = float(comprobaciones["zona_gris"])
    # El límite superior de normalidad de la referencia: por encima, la TC está "por encima de lo normal".
    normalidad = float(comprobaciones["limite_de_normalidad"]["umbral"])
    imagenes = exportar_cortes(args.previews, args.out / "previews")
    con_arbol = exportar_arboles(args.mascaras, args.previews, args.out / "previews", imagenes)
    # El modelo que se probó en reserva: sus umbrales salen de `reserva.json`. Sin esa prueba no hay lectura congelada.
    modelo_probado = {
        "umbral_dano": round(float(reserva["umbral_dano"]), 3),
        "umbral_normalidad": float(reserva["limite_de_normalidad"]["umbral"]),
        "zona_gris": ZONA_GRIS_DEL_MODELO_PROBADO,
        "sujetos_de_ajuste": SUJETOS_DEL_MODELO_PROBADO,
    } if reserva else None
    sujetos = simular_sujetos(np.random.default_rng(args.seed), umbral, normalidad, zona_gris, sorted(imagenes), con_arbol, modelo_probado)
    assert len(sujetos) == comprobaciones["sujetos"], f"el reparto simulado suma {len(sujetos)} y la cohorte tiene {comprobaciones['sujetos']}"
    experimento_ciego(np.random.default_rng(11), sujetos, natural)
    if con_arbol:
        exportar_tc_publica(args.previews, args.mascaras, args.out.parent / "publica", sorted(con_arbol)[0])

    cohorte = {
        "aviso": f"Sujetos simulados sobre TC públicas de LIDC-IDRI. Las cifras son las de los {comprobaciones['sujetos']} sujetos de la cohorte del reto.",
        "umbral_dano": umbral,
        "umbral_normalidad": normalidad,
        "umbral_cociente": UMBRAL_COCIENTE,
        "zona_gris": zona_gris,
        "sujetos": sujetos,
        "imagenes": imagenes,
        "congelado": modelo_probado,
        "comprobaciones": comprobaciones,
        "escalera": escalera,
        "reserva": reserva,
        "validacion": validacion,
        "discordantes": discordantes,
        "umbral_natural": natural,
        "complejidad": complejidad,
        "embudo": embudo,
        "ejemplos": elegir_ejemplos(sujetos, zona_gris),
        # `docs/cifras.md`, "Palabras": el paso Connect con el modelo final y el único biomarcador de la tabla del reto.
        "conexion": {
            "rasgo": "FENO, en logaritmo",
            "covariables": ["edad", "sexo", "talla", "tabaco", "asma"],
            "filas": [
                {"exposicion": "Puntuación de daño", "coeficiente": 0.12, "p": 0.22, "n": 74},
                {"exposicion": "z de %LAA-950 suavizado", "coeficiente": 0.07, "p": 0.30, "n": 74},
                {"exposicion": "z de longitud de vía aérea", "coeficiente": 0.11, "p": 0.33, "n": 74},
                {"exposicion": "FEV1/FVC", "coeficiente": 0.39, "p": 0.72, "n": 74},
            ],
        },
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "cohorte.json").write_text(json.dumps(cohorte, ensure_ascii=False, indent=1))
    for particion in ("desarrollo", "reserva"):
        grupo = [s for s in sujetos if s["particion"] == particion]
        clases = {c: sum(s["clase"] == c for s in grupo) for c in ("control", "pre-EPOC", "EPOC")}
        print(f"{particion}: {len(grupo)} sujetos simulados {clases}, {sum(s['arbol'] for s in grupo)} con árbol")
    print(f"{len(imagenes)} TC públicas, {len(con_arbol)} con máscara del árbol, reserva {'copiada' if reserva else 'pendiente'}, "
          f"validación {'copiada' if validacion else 'pendiente'}, en {args.out}")


if __name__ == "__main__":
    main()
