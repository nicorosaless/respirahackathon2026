"""Escribe una cohorte sintética con el contrato de datos de la app MAPS.

Sirve para desarrollar y para ensayar la demo sin datos de pacientes. Los
sujetos, sus medidas y la evidencia son inventados: los identificadores empiezan
por SINT- y el directorio lleva un fichero SINTETICO que hace que la app muestre
un aviso fijo. La única parte real es la anatomía de las previsualizaciones, que
sale de una TC pública (LIDC-IDRI) y es la misma para todos los sujetos.

    PYTHONPATH=src python app/make_fixture.py --tc data/lidc/LIDC-IDRI-0004

La segmentación de lóbulos tarda unos 2 minutos en CPU. Se hace una vez y queda
en `outputs/fixture_cache/`; las ejecuciones siguientes no la repiten ni
necesitan la TC.

Convención de las previsualizaciones (la app la comprueba con los lóbulos):
eje 0 de anterior a posterior, fila 0 craneal, columna 0 a la derecha del
paciente.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from maps_core import LOBULOS, PULMON
from maps_render import orientar_cabeza_arriba

RAIZ = Path(__file__).resolve().parents[1]
CORTES = 7

GRUPOS = {"referencia": 24, "pre-COPD": 20, "EPOC": 16}
# Daño latente por grupo (media, desviación), en unidades de z.
DANO_LATENTE = {"referencia": (0.0, 0.4), "pre-COPD": (1.2, 0.6), "EPOC": (2.0, 0.7)}
# El enfisema del fumador predomina en los lóbulos superiores.
PESO_LOBULO = {"LSD": 1.2, "LM": 0.75, "LID": 0.7, "LSI": 1.1, "LII": 0.65}

# clave: (measures.json, carga sobre el daño latente, valor esperado, desviación estándar)
MEDIDAS = {
    "perc15": ({"nombre": "Perc15", "unidad": "HU", "peor": "menor",
                "descripcion": "Percentil 15 de la densidad del lóbulo. Más negativo es más enfisema."}, 1.0, -915.0, 12.0),
    "laa950": ({"nombre": "%LAA-950", "unidad": "%", "peor": "mayor",
                "descripcion": "Porcentaje del lóbulo por debajo de -950 HU."}, 0.9, 2.5, None),
    "ramas_via_aerea": ({"nombre": "Ramas de vía aérea", "unidad": "ramas", "peor": "menor",
                         "descripcion": "Número de ramas del árbol bronquial visibles en la TC."}, 0.7, 36.0, 6.0),
    "bv5_tbv": ({"nombre": "Vasos pequeños (BV5/TBV)", "unidad": "%", "peor": "menor",
                 "descripcion": "Fracción del volumen de sangre en vasos de menos de 5 mm² de sección."}, 0.6, 58.0, 5.0),
    "compacidad": ({"nombre": "Compacidad del enfisema", "unidad": "", "peor": "mayor",
                    "descripcion": "Índice de agrupamiento de los vóxeles de baja densidad, de 0 a 1."}, 0.8, 0.30, 0.08),
}

# Números inventados. En la cohorte real este fichero lo escribe el análisis.
EVIDENCIA = {
    "objetivo": "DLCO por debajo del límite inferior de la normalidad",
    "metrica_nombre": "AUC",
    "escalera": [
        {"escalon": "Clínica sola", "metrica": 0.64, "ic95_inf": 0.53, "ic95_sup": 0.74,
         "incremento": None, "incremento_ic95_inf": None, "incremento_ic95_sup": None, "p_permutacion": 0.012},
        {"escalon": "+ densitometría", "metrica": 0.71, "ic95_inf": 0.61, "ic95_sup": 0.80,
         "incremento": 0.07, "incremento_ic95_inf": -0.01, "incremento_ic95_sup": 0.15, "p_permutacion": 0.001},
        {"escalon": "+ medidas nuevas", "metrica": 0.76, "ic95_inf": 0.67, "ic95_sup": 0.84,
         "incremento": 0.05, "incremento_ic95_inf": 0.01, "incremento_ic95_sup": 0.10, "p_permutacion": 0.001},
        {"escalon": "+ ómicas", "metrica": 0.78, "ic95_inf": 0.69, "ic95_sup": 0.86,
         "incremento": 0.02, "incremento_ic95_inf": -0.03, "incremento_ic95_sup": 0.07, "p_permutacion": 0.001},
    ],
    "controles_negativos": [
        {"variable": "Escáner", "auc": 0.52, "ic95_inf": 0.41, "ic95_sup": 0.63},
        {"variable": "Sexo", "auc": 0.47, "ic95_inf": 0.36, "ic95_sup": 0.58},
    ],
}


def anatomia(tc: Path, cache: Path) -> dict[str, np.ndarray]:
    """Cortes coronales y lóbulos de la TC pública, ya orientados. Usa la caché si existe."""
    if cache.exists():
        with np.load(cache) as guardado:
            return {clave: guardado[clave] for clave in ("hu", "lobes", "spacing")}
    if not tc.exists():
        raise SystemExit(
            f"No hay caché en {cache} ni TC en {tc}. Indica la serie DICOM con --tc "
            "o genera la cohorte sin imágenes con --sin-previews."
        )

    # La GPU de la máquina es de otros procesos y aquí no hace falta.
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    from maps.ct import read_volume_hu
    from maps.lungs import segment

    hu, (sz, _, sx) = read_volume_hu(tc)
    print(f"Segmentando lóbulos de {tc.name} {hu.shape} en CPU, unos 2 minutos")
    lobes = segment(hu, lobes=True)

    # Volumen (z, y, x). Un corte coronal es un plano de y constante: quedan filas z y columnas x.
    con_pulmon = np.flatnonzero((lobes > 0).any(axis=(0, 2)))
    planos = np.linspace(con_pulmon[0], con_pulmon[-1], CORTES + 2)[1:-1].round().astype(int)
    cortes_hu = np.stack([hu[:, y, :] for y in planos])
    cortes_lobes = np.stack([lobes[:, y, :] for y in planos])
    # SimpleITK entrega z de caudal a craneal; aquí se deja la fila 0 craneal.
    cortes_hu, cortes_lobes = orientar_cabeza_arriba(cortes_hu, cortes_lobes)

    resultado = {
        "hu": np.ascontiguousarray(np.rint(cortes_hu)).astype(np.int16),
        "lobes": np.ascontiguousarray(cortes_lobes).astype(np.uint8),
        "spacing": np.asarray([sz, sx], dtype=np.float32),
    }
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, **resultado)
    return resultado


def sujetos_sinteticos(n: int, rng: np.random.Generator) -> tuple[pd.DataFrame, np.ndarray]:
    """Tabla clínica y biológica inventada, y el daño latente de cada sujeto."""
    total = sum(GRUPOS.values())
    grupo = np.concatenate([[nombre] * max(round(n * cuantos / total), 1) for nombre, cuantos in GRUPOS.items()])
    grupo = np.resize(grupo, n)
    rng.shuffle(grupo)
    dano = np.array([rng.normal(*DANO_LATENTE[g]) for g in grupo])
    epoc = grupo == "EPOC"
    mujer = rng.random(n) < 0.45

    fev1_fvc = np.where(
        epoc,
        np.minimum(0.63 - 0.02 * dano + rng.normal(0, 0.04, n), 0.69),
        np.maximum(0.79 - 0.012 * dano + rng.normal(0, 0.035, n), 0.70),
    )
    tabla = pd.DataFrame({
        "subject_id": [f"SINT-{i + 1:03d}" for i in range(n)],
        "grupo": grupo,
        "edad": rng.integers(35, 51, n),
        "sexo": np.where(mujer, "mujer", "hombre"),
        "talla_cm": np.round(np.where(mujer, 163, 176) + rng.normal(0, 6.5, n)),
        "imc": np.round(rng.normal(26, 3.5, n), 1),
        "paquetes_ano": np.round(10 + rng.gamma(2.0, 4.0, n) + 4 * np.clip(dano, 0, None)),
        "fumador_activo": np.where(rng.random(n) < 0.6, "sí", "no"),
        "escaner": rng.choice(["A", "B"], n),
        "fev1_fvc": np.round(fev1_fvc, 2),
        "fev1_pct_pred": np.round(np.where(epoc, 84, 101) - 4 * dano + rng.normal(0, 9, n)),
        "dlco_pct_pred": np.round(93 - 7 * dano + rng.normal(0, 8, n)),
        "cat": np.round(np.clip(4 + 3 * dano + rng.normal(0, 3, n), 0, 40)),
        "mmrc": np.round(np.clip(0.3 + 0.5 * dano + rng.normal(0, 0.6, n), 0, 4)),
        "eosinofilos_cel_ul": np.round(rng.lognormal(np.log(180), 0.5, n), -1),
        "pcr_mg_l": np.round(rng.lognormal(np.log(1.5) + 0.15 * dano, 0.6, n), 1),
        "cc16_ng_ml": np.round(np.clip(8 - 0.8 * dano + rng.normal(0, 1.8, n), 1, None), 1),
    })
    # No todos los sujetos tienen todas las pruebas.
    for columna, fraccion in {"dlco_pct_pred": 0.08, "cat": 0.05, "pcr_mg_l": 0.10, "cc16_ng_ml": 0.25}.items():
        tabla.loc[rng.random(n) < fraccion, columna] = np.nan
    return tabla, dano


def medidas_sinteticas(ids: list[str], dano: np.ndarray, rng: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame]:
    """features.csv y zscores.csv: una fila por sujeto y región."""
    valores, zs = [], []
    for sid, d in zip(ids, dano):
        heterogeneidad = rng.lognormal(0, 0.25, len(LOBULOS))
        z_lobulos = {}
        for lobulo, h in zip(LOBULOS, heterogeneidad):
            z_lobulos[lobulo] = {
                clave: signo(meta) * (d * PESO_LOBULO[lobulo] * h * carga + rng.normal(0, 0.75))
                for clave, (meta, carga, _, _) in MEDIDAS.items()
            }
        z_lobulos[PULMON] = {
            clave: float(np.mean([z_lobulos[lobulo][clave] for lobulo in LOBULOS])) * 1.15 for clave in MEDIDAS
        }
        for region, z_region in z_lobulos.items():
            zs.append({"subject_id": sid, "region": region, **{k: round(v, 2) for k, v in z_region.items()}})
            valores.append({"subject_id": sid, "region": region, **{k: valor(k, v) for k, v in z_region.items()}})
    return pd.DataFrame(valores), pd.DataFrame(zs)


def signo(meta: dict[str, str]) -> int:
    return 1 if meta["peor"] == "mayor" else -1


def valor(clave: str, z: float) -> float:
    """Valor de la medida que corresponde a una z, alrededor de un valor esperado fijo."""
    _, _, esperado, desviacion = MEDIDAS[clave]
    if clave == "laa950":  # distribución asimétrica: la z actúa sobre el logaritmo
        return round(float(esperado * np.exp(0.55 * z)), 1)
    if clave == "ramas_via_aerea":
        return float(max(round(esperado + desviacion * z), 4))
    if clave == "compacidad":
        return round(float(np.clip(esperado + desviacion * z, 0.0, 1.0)), 2)
    return round(float(esperado + desviacion * z), 1)


def escribir_previews(directorio: Path, ids: list[str], imagen: dict[str, np.ndarray]) -> None:
    """La misma anatomía para todos: un fichero y enlaces duros, o copias si el sistema no los admite."""
    directorio.mkdir(parents=True, exist_ok=True)
    primero = directorio / f"{ids[0]}.npz"
    np.savez_compressed(primero, **imagen)
    for sid in ids[1:]:
        destino = directorio / f"{sid}.npz"
        try:
            os.link(primero, destino)
        except OSError:
            shutil.copyfile(primero, destino)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--salida", type=Path, default=RAIZ / "outputs" / "cohorte_sintetica")
    parser.add_argument("--tc", type=Path, default=RAIZ / "data" / "lidc" / "LIDC-IDRI-0004",
                        help="serie DICOM pública de la que sale la anatomía de las previsualizaciones")
    parser.add_argument("--cache", type=Path, default=RAIZ / "outputs" / "fixture_cache" / "anatomia_coronal.npz")
    parser.add_argument("--sujetos", type=int, default=60)
    parser.add_argument("--semilla", type=int, default=7)
    parser.add_argument("--sin-previews", action="store_true", help="no escribe imágenes; la app lo indica en cada paciente")
    args = parser.parse_args()

    rng = np.random.default_rng(args.semilla)
    sujetos, dano = sujetos_sinteticos(args.sujetos, rng)
    ids = sujetos["subject_id"].tolist()
    valores, zs = medidas_sinteticas(ids, dano, rng)

    # Estados incompletos que la app tiene que resolver: un sujeto sin imagen,
    # otro sin medidas de TC y otro con un lóbulo sin segmentar.
    sin_preview, sin_medidas, sin_lobulo_medio = ids[-2], ids[-1], ids[-3]
    incompleto = (valores["subject_id"] == sin_medidas) | (
        (valores["subject_id"] == sin_lobulo_medio) & (valores["region"] == "LM")
    )
    valores, zs = valores[~incompleto], zs[~incompleto]

    if args.salida.exists():
        # Solo se sobrescribe una cohorte sintética anterior, nunca otro directorio.
        if any(args.salida.iterdir()) and not (args.salida / "SINTETICO").exists():
            raise SystemExit(f"{args.salida} ya existe y no es una cohorte sintética. Elige otro directorio con --salida.")
        shutil.rmtree(args.salida)
    args.salida.mkdir(parents=True)
    # La primera línea es la que la app muestra en su aviso de datos sintéticos.
    imagen = (
        "No hay imágenes de TC." if args.sin_previews
        else "La imagen es una TC pública (LIDC-IDRI) repetida en todos los sujetos."
    )
    (args.salida / "SINTETICO").write_text(
        f"Ningún valor corresponde a un paciente. {imagen}\n"
        "Cohorte generada por app/make_fixture.py para desarrollar y ensayar la demo.\n",
        encoding="utf-8",
    )
    sujetos.to_csv(args.salida / "subjects.csv", index=False)
    valores.to_csv(args.salida / "features.csv", index=False)
    zs.to_csv(args.salida / "zscores.csv", index=False)
    (args.salida / "measures.json").write_text(
        json.dumps({clave: meta for clave, (meta, *_) in MEDIDAS.items()}, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.salida / "evidence.json").write_text(json.dumps(EVIDENCIA, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.sin_previews:
        print("Sin previsualizaciones (--sin-previews)")
    else:
        escribir_previews(args.salida / "previews", [s for s in ids if s != sin_preview], anatomia(args.tc, args.cache))
    print(f"Cohorte sintética de {len(ids)} sujetos en {args.salida}")


if __name__ == "__main__":
    main()
