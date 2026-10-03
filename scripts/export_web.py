"""Exporta una cohorte ya puntuada al formato que lee la app web (`web/lib/cohorte.ts`).

Escribe `cohorte.json` y los cortes de TC de cada sujeto en `previews/`. Con la
cohorte del reto son datos de sujetos: la salida se queda en MareNostrum y la
app la lee de allí en cada petición.

    python scripts/export_web.py mn5/cohorte.early.toml --duro outputs/cohorte_duro_v2 --masks outputs/cohorte --out outputs/web-data

`--masks` es la cohorte procesada con `--save-masks`: de ahí sale el árbol bronquial de cada sujeto.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from scipy.ndimage import gaussian_filter

from maps.cohort import damage_score, lung_volume, oriented_z, region_z_applied
from maps.measures import LOG_FLOOR, LOG_MEASURES, MEASURES, WHOLE_LUNG
from maps.persist import load_model

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from maps_render import cargar_preview, encuadre, orientar_cabeza_arriba, ventana_pulmon  # noqa: E402

LOBES = {1: "LSI", 2: "LII", 3: "LSD", 4: "LM", 5: "LID"}
HEIGHT_PX = 560
# Las medidas que nombra el reto, además de las dos de la puntuación. La app las enseña siempre.
TRADITIONAL = ["laa950", "via_grosor_pared_mm", "via_pi10_mm", "via_disanapsia"]
# Columna de la tabla del reto que alimenta cada campo clínico de la app.
CLINICAL = {"edad": "edat_round_v1", "talla": "altura_v1", "paquetes_ano": "paquetes_año_v1", "fev1_fvc": "fev1_fvc_post_v1",
            "fev1_pct": "FEV1pp_GLI_v1", "dlco_pct": "DLCO_v1", "cat": "CAT_v1", "kvp": "kvp"}


def number(value: object, decimals: int = 3) -> float | None:
    """Un número redondeado, o None si falta: JSON no admite NaN."""
    if value is None or pd.isna(value) or not math.isfinite(float(value)):
        return None
    return round(float(value), decimals)


def airway_projection(masks: Path) -> np.ndarray:
    """El árbol bronquial visto de frente, con el mismo recorte que los cortes de `maps.features.coronal_preview`."""
    data = np.load(masks)
    lung = data["lobes"] > 0
    z_any, x_any = np.flatnonzero(lung.any(axis=(1, 2))), np.flatnonzero(lung.any(axis=(0, 1)))
    margin = 10
    z0, z1 = max(z_any[0] - margin, 0), min(z_any[-1] + margin, lung.shape[0])
    x0, x1 = max(x_any[0] - margin, 0), min(x_any[-1] + margin, lung.shape[2])
    return data["airway"][z0:z1, :, x0:x1].any(axis=1)[::-1]


def export_slices(source: Path, target: Path, subjects: list[str], masks: Path | None) -> dict[str, dict]:
    """Cada corte coronal en gris y su mapa de lóbulos, con la proporción real, y el centro de cada lóbulo."""
    target.mkdir(parents=True, exist_ok=True)
    images = {}
    for subject in subjects:
        path = source / f"{subject}.npz"
        preview = cargar_preview(path) if path.exists() else None
        if preview is None:
            continue
        height_mm = preview.hu.shape[1] * preview.espaciado[0]
        width_mm = preview.hu.shape[2] * preview.espaciado[1]
        size = (int(round(HEIGHT_PX * width_mm / height_mm)), HEIGHT_PX)
        slices = []
        # Un filtro gaussiano de 1 mm, el mismo que usa `laa950_smooth`: quita el grano de la TC y marca el enfisema que se mide.
        sigma = (1.0 / preview.espaciado[0], 1.0 / preview.espaciado[1])
        for k in range(preview.cortes):
            smooth = gaussian_filter(preview.hu[k].astype(np.float32), sigma)
            grey = Image.fromarray(ventana_pulmon(smooth)).resize(size, Image.Resampling.BICUBIC)
            labels = Image.fromarray(preview.lobes[k].astype(np.uint8)).resize(size, Image.Resampling.NEAREST)
            grey.save(target / f"{subject}-{k}.png", optimize=True)
            # Los píxeles de pulmón por debajo de -950 HU (0 o 255): la app los pinta en rojo.
            emphysema = (preview.lobes[k] > 0) & (smooth < -950)
            Image.fromarray(emphysema.astype(np.uint8) * 255).resize(size, Image.Resampling.NEAREST).save(
                target / f"{subject}-{k}-enfisema.png", optimize=True)
            # El mapa guarda el número de lóbulo (0 a 5) como nivel de gris: el navegador lo lee píxel a píxel.
            labels.save(target / f"{subject}-{k}-lobulos.png", optimize=True)
            matrix, centres = np.asarray(labels), {}
            for label, name in LOBES.items():
                rows, columns = np.nonzero(matrix == label)
                if rows.size >= 0.004 * matrix.size:
                    centres[name] = [round(float(np.median(columns)) / size[0], 4), round(float(np.median(rows)) / size[1], 4)]
            slices.append({"centros": centres})
        tree = masks / "sujetos" / subject / "masks.npz" if masks is not None else None
        has_tree = False
        if tree is not None and tree.exists():
            projection = airway_projection(tree)
            with np.load(path) as raw:
                raw_lobes, mm = raw["lobes"], tuple(float(v) for v in np.asarray(raw["spacing"]).ravel())
            if projection.shape == raw_lobes.shape[1:]:
                # La misma orientación y el mismo encuadre que `cargar_preview` da a los cortes.
                repeated, oriented = orientar_cabeza_arriba(np.broadcast_to(projection, raw_lobes.shape), raw_lobes)
                rows, columns = encuadre(oriented, mm)
                # Máscara del árbol (0 o 255), del tamaño de los cortes: se superpone a cualquiera de ellos.
                Image.fromarray(repeated[0][rows, columns].astype(np.uint8) * 255).resize(size, Image.Resampling.NEAREST).save(
                    target / f"{subject}-arbol.png", optimize=True)
                has_tree = True
        images[subject] = {"ancho": size[0], "alto": size[1], "cortes": slices, "arbol": has_tree}
    return images


def frozen_view(cohort: Path, emphysema: str, airway: str) -> tuple[dict[str, dict], dict]:
    """Lo que el modelo probado en reserva dijo de cada sujeto de reserva, y sus umbrales.

    Ese modelo se ajustó sin ellos. El modelo final sí los usa, así que para
    enseñar una inferencia sobre un sujeto no visto hay que usar estos valores.
    """
    subjects = pd.read_csv(cohort / "subjects.csv", dtype={"subject_id": str}).set_index("subject_id")
    zscores = pd.read_csv(cohort / "zscores.csv", dtype={"subject_id": str})
    features = pd.read_csv(cohort / "features.csv", dtype={"subject_id": str})
    whole = features[features["region"] == WHOLE_LUNG].set_index("subject_id")
    models, model = load_model(cohort)
    checks = json.loads((cohort / "comprobaciones.json").read_text())
    threshold, limit, grey = model["umbral_dano"], checks["limite_de_normalidad"]["umbral"], checks["zona_gris"]
    expected = models[WHOLE_LUNG].expected(subjects.loc[whole.index.intersection(subjects.index)])
    for measure in LOG_MEASURES:
        if measure in expected:
            expected[measure] = 10 ** expected[measure] - LOG_FLOOR
    z = {measure: damage_score(zscores, (measure,)) for measure in (emphysema, airway)}
    out = {}
    for subject, row in subjects[subjects["particion"] == "reserva"].iterrows():
        score = row["puntuacion_dano"]
        out[subject] = {
            "puntuacion": number(score, 2), "dano_tc": bool(row["dano_tc"] == "sí"), "clase": row["clase_maps"], "motivo": row["clase_motivo"],
            "cerca_umbral": bool(abs(score - threshold) < grey),
            "nivel_tc": "alta" if score >= limit else "intermedia" if score >= threshold else "esperada",
            "z": {"enfisema": number(z[emphysema].get(subject), 2), "via": number(z[airway].get(subject), 2)},
            "valores": {emphysema: number(whole.loc[subject, emphysema]), airway: number(whole.loc[subject, airway], 0)},
            "esperado": {emphysema: number(max(expected[emphysema].get(subject, np.nan), 0.0)), airway: number(expected[airway].get(subject), 0)},
        }
    return out, {"umbral_dano": threshold, "umbral_normalidad": limit, "zona_gris": grey, "sujetos_de_ajuste": int(model["sujetos_de_ajuste"])}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--duro", type=Path, required=True, help="cohorte de los mismos sujetos con otro kernel de reconstrucción")
    parser.add_argument("--masks", type=Path, help="cohorte procesada con --save-masks, para el árbol bronquial")
    parser.add_argument("--reserva", type=Path, help="reserva.json de la prueba del modelo anterior, para enseñarla junto a este")
    parser.add_argument("--congelado", type=Path,
                        help="cohorte del modelo que se probó en reserva: sus sujetos de reserva llevan además lo que ese modelo dijo de ellos")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    config = tomllib.loads(args.config.read_text())
    cohort = Path(config["cohorte"])
    normative = config["normativo"]
    covariates, categorical = normative["covariables"], normative.get("categoricas", [])
    panel = tuple(config["puntuacion"]["medidas"])
    rule = config["clasificacion"]
    model = json.loads((cohort / "modelo.json").read_text())

    subjects = pd.read_csv(cohort / "subjects.csv", dtype={"subject_id": str}).set_index("subject_id")
    features = pd.read_csv(cohort / "features.csv", dtype={"subject_id": str})
    zscores = pd.read_csv(cohort / "zscores.csv", dtype={"subject_id": str})
    hard = pd.read_csv(args.duro / "features.csv", dtype={"subject_id": str})
    hard = hard[hard["subject_id"].isin(subjects.index)]
    reference = subjects["referencia"].astype(bool)
    hard_subjects = subjects.drop(columns="volumen_pulmon_ml").join(lung_volume(hard), how="inner")
    hard_score = damage_score(region_z_applied(features, hard, subjects, hard_subjects, reference, covariates, categorical), panel)

    whole = features[features["region"] == WHOLE_LUNG].set_index("subject_id")
    whole_hard = hard[hard["region"] == WHOLE_LUNG].set_index("subject_id")
    # z por sujeto de cada medida, orientado para que más sea peor.
    z = {measure: damage_score(zscores, (measure,)) for measure in [*panel, *TRADITIONAL]}
    emphysema, airway = panel
    lobar = oriented_z(zscores, (emphysema,)).set_index([zscores["subject_id"], zscores["region"]])[emphysema].unstack("region")

    # Lo que el modelo espera de cada medida en el pulmón entero de cada sujeto, en sus unidades.
    models, _ = load_model(cohort)
    expected = models[WHOLE_LUNG].expected(subjects.loc[whole.index.intersection(subjects.index)])
    for measure in LOG_MEASURES:
        if measure in expected:
            expected[measure] = 10 ** expected[measure] - LOG_FLOOR
    checks = json.loads((cohort / "comprobaciones.json").read_text())
    threshold, grey_zone = model["umbral_dano"], checks["zona_gris"]
    normal_limit = checks["limite_de_normalidad"]["umbral"]
    # La puntuación de cada sujeto con modelos que no lo vieron en ningún paso (scripts/nested_cv.py).
    unseen = cohort / "fuera_de_muestra.csv"
    unseen = (pd.read_csv(unseen, dtype={"subject_id": str}).set_index("subject_id")["puntuacion_fuera_de_muestra"]
              if unseen.exists() else pd.Series(dtype=float))

    # La puntuación ciega: lo esperado ajustado sin saber quién es caso (scripts/blind_threshold.py).
    blind = cohort / "ciego.csv"
    blind = pd.read_csv(blind, dtype={"subject_id": str}).set_index("subject_id") if blind.exists() else pd.DataFrame()
    frozen, frozen_model = frozen_view(args.congelado, emphysema, airway) if args.congelado else ({}, None)
    images = export_slices(cohort / "previews", args.out / "previews", list(subjects.index), args.masks)
    rows = []
    for subject, row in subjects.sort_values("puntuacion_dano", ascending=False).iterrows():
        rows.append({
            "id": subject,
            # "reserva": el modelo no vio a este sujeto ni para ajustar lo esperado ni para fijar el umbral.
            # Un sujeto recuperado de la otra reconstrucción no estuvo en la prueba de reserva, aunque le tocara ese grupo.
            "particion": "desarrollo" if bool(row.get("de_repuesto", False)) else row["particion"],
            "clase": row["clase_maps"], "motivo": row["clase_motivo"],
            "caso": bool(row[rule["caso"]] == 1), "dano_tc": bool(row["dano_tc"] == "sí"),
            # Tan cerca del umbral que otra reconstrucción de la misma TC podría cambiar la decisión.
            "cerca_umbral": bool(abs(row["puntuacion_dano"] - threshold) < grey_zone),
            "esperado": {emphysema: number(max(expected[emphysema].get(subject, np.nan), 0.0)),
                         airway: number(expected[airway].get(subject), 0)},
            # Con dos decimales, los mismos que lleva la frase de la clase: así la cifra y la frase no difieren en 0,01.
            "puntuacion": number(row["puntuacion_dano"], 2),
            "fuera_de_muestra": number(unseen.get(subject)),
            "ciego": {"puntuacion": number(blind.loc[subject, "puntuacion_ciega"]), "grupo": blind.loc[subject, "grupo_por_la_tc"]}
            if subject in blind.index else None,
            # Tres niveles: por debajo del umbral, entre el umbral y el límite de normalidad, y por encima de este.
            "nivel_tc": ("alta" if row["puntuacion_dano"] >= normal_limit else "intermedia" if row["puntuacion_dano"] >= threshold else "esperada")
            if pd.notna(row["puntuacion_dano"]) else None,
            "z": {"enfisema": number(z[emphysema].get(subject), 2), "via": number(z[airway].get(subject), 2)},
            "valores": {"laa950_smooth": number(whole.loc[subject, emphysema]), "via_longitud_mm": number(whole.loc[subject, airway], 0)},
            "tradicionales": [{"medida": m, "nombre": MEASURES[m][0], "unidad": MEASURES[m][1],
                               "valor": number(whole.loc[subject, m]), "z": number(z[m].get(subject), 2)} for m in TRADITIONAL],
            "lobulos": {name: number(lobar.loc[subject, name], 2) for name in LOBES.values()},
            "kernels": {
                "laa950": [number(whole.loc[subject, "laa950"]), number(whole_hard["laa950"].get(subject))],
                "puntuacion": [number(row["puntuacion_dano"]), number(hard_score.get(subject))],
            },
            "clinica": {name: number(row[column], 3 if name == "fev1_fvc" else 1) for name, column in CLINICAL.items()}
            | {"sexo": "H" if row["sexo"] == "hombre" else "M", "fuma": bool(row["fuma"] == "fuma")},
            # Lo que dijo de este sujeto el modelo ajustado sin él y probado en reserva. None si no era de reserva.
            "congelado": frozen.get(subject),
            "imagen": subject if subject in images else None,
            "arbol": bool(images.get(subject, {}).get("arbol", False)),
        })

    connection = pd.read_csv(cohort / "conexion.csv") if (cohort / "conexion.csv").exists() else pd.DataFrame()
    reserve = args.reserva or cohort / "reserva.json"
    out = {
        "aviso": None,
        "umbral_dano": threshold, "umbral_normalidad": normal_limit, "umbral_cociente": 0.70, "zona_gris": grey_zone,
        "sujetos": rows, "imagenes": images,
        "congelado": frozen_model,
        # El experimento ciego en agregados, y los sujetos elegidos para la demo (scripts/pick_examples.py).
        "umbral_natural": json.loads((cohort / "umbral_natural.json").read_text()) if (cohort / "umbral_natural.json").exists() else None,
        "ejemplos": json.loads((cohort / "ejemplos.json").read_text()) if (cohort / "ejemplos.json").exists() else None,
        # Por qué dos medidas: la comparación fuera de muestra y el embudo de selección.
        "complejidad": json.loads((cohort / "complejidad.json").read_text()) if (cohort / "complejidad.json").exists() else None,
        "embudo": json.loads((cohort / "embudo.json").read_text()) if (cohort / "embudo.json").exists() else None,
        # Con qué va la puntuación dentro de los controles y dentro de los casos (scripts/explore_outliers.py).
        "discordantes": json.loads((cohort / "discordantes.json").read_text()) if (cohort / "discordantes.json").exists() else None,
        "comprobaciones": checks,
        "escalera": json.loads((cohort / "evidence.json").read_text()),
        # La prueba en los sujetos de reserva. None mientras no se haya hecho.
        "reserva": json.loads(reserve.read_text()) if reserve.exists() else None,
        # La validación cruzada anidada con todos los sujetos. None si no se ha hecho.
        "validacion": json.loads((cohort / "validacion_anidada.json").read_text()) if (cohort / "validacion_anidada.json").exists() else None,
        "conexion": {
            "rasgo": ", ".join(sorted(connection["rasgo"].unique())) if len(connection) else "",
            "covariables": config.get("molecular", {}).get("covariables", []),
            "filas": [{"exposicion": r["exposicion"], "coeficiente": number(r["coef"], 2), "p": number(r["p"], 2), "n": int(r["n"])}
                      for _, r in connection.iterrows()],
        },
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "cohorte.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    by_split = subjects["particion"].value_counts().to_dict()
    print(f"{len(rows)} sujetos {by_split}, {len(images)} con imagen, en {args.out}")


if __name__ == "__main__":
    main()
