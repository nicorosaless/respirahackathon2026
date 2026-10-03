"""Inferencia en directo para la demo: el modelo congelado puntúa a un sujeto que no vio.

Carga el modelo que se probó en la reserva, comprueba que es el mismo fichero
cuyo hash se escribió en el protocolo y que el sujeto es de la reserva (no entró
en el ajuste). Después lo puntúa desde sus medidas de TC y su tabla clínica, sin
reajustar nada, y enseña cada paso: medida, valor esperado, z, puntuación,
umbral y clase. Al final compara con lo que la web enseña de ese sujeto.

Imprime los valores de un solo sujeto anonimizado, los mismos que la web. Solo
se ejecuta en MareNostrum durante la demo.

    python scripts/demo_inferencia.py --sujeto 44
"""

from __future__ import annotations

import argparse
import hashlib
import time
from pathlib import Path

import numpy as np
import pandas as pd

from maps.cohort import WHOLE_LUNG, damage_score, lung_volume
from maps.measures import LOG_FLOOR, LOG_MEASURES
from maps.persist import load_model
from predict import predict

# Los del protocolo de la reserva (docs/protocolo-reserva.md), escritos antes de la prueba.
PROTOCOL_HASHES = {"modelo.pkl": "c14db8eeae6b8b86", "modelo.json": "89275e2d65ed3fdb"}
NAMES = {"laa950_smooth": "enfisema (%LAA-950 suavizado)", "via_longitud_mm": "longitud del árbol bronquial (mm)"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sujeto", required=True)
    parser.add_argument("--modelo", type=Path, default=Path("outputs/cohorte_v3"))
    args = parser.parse_args()
    started = time.perf_counter()

    print(f"1. Modelo congelado en {args.modelo}")
    for name, expected in PROTOCOL_HASHES.items():
        digest = hashlib.sha256((args.modelo / name).read_bytes()).hexdigest()[:16]
        print(f"   {name}: sha256 {digest} {'= protocolo' if digest == expected else 'NO COINCIDE con el protocolo ' + expected}")
    models, description = load_model(args.modelo)
    print(f"   ajustado con {description['sujetos_de_ajuste']} sujetos; umbral de daño {description['umbral_dano']:.2f}")

    subjects = pd.read_csv(args.modelo / "subjects.csv", dtype={"subject_id": str}).set_index("subject_id")
    if args.sujeto not in subjects.index or subjects.loc[args.sujeto, "particion"] != "reserva":
        raise SystemExit(f"el sujeto {args.sujeto} no es de la reserva: el modelo congelado sí lo vio")
    print(f"2. Sujeto {args.sujeto}: de la reserva, apartado antes de elegir medidas; el modelo no lo vio")

    features = pd.read_csv(args.modelo / "features.csv", dtype={"subject_id": str})
    features = features[features["subject_id"] == args.sujeto]
    clinical = subjects.loc[[args.sujeto]].drop(columns=["volumen_pulmon_ml", "puntuacion_dano", "dano_tc", "clase_maps", "clase_motivo"],
                                               errors="ignore").join(lung_volume(features))
    row = clinical.iloc[0]
    print(f"   entra: {row['edat_round_v1']:.0f} años, {row['sexo']}, {row['altura_v1']:.0f} cm, {row['fuma']}, "
          f"pulmón {row['volumen_pulmon_ml'] / 1000:.1f} L, {row['kvp']:.0f} kVp")

    prediction, zscores = predict(models, description, features, clinical)
    expected = models[WHOLE_LUNG].expected(clinical)
    whole = features[features["region"] == WHOLE_LUNG].iloc[0]
    print("3. Cada medida frente a lo esperado para alguien como él o ella")
    for measure in description["medidas"]:
        value = whole[measure]
        mean = expected[measure].iloc[0]
        mean = 10 ** mean - LOG_FLOOR if measure in LOG_MEASURES else mean
        z = damage_score(zscores, (measure,)).get(args.sujeto, np.nan)
        print(f"   {NAMES.get(measure, measure)}: medido {value:.2f}, esperado {max(mean, 0):.2f}, z {z:+.2f} (positivo es peor)")
    result = prediction.iloc[0]
    print(f"4. Puntuación de daño (media de los z): {result['puntuacion_dano']:.2f}; umbral {description['umbral_dano']:.2f}")
    print(f"5. Clase: {result['clase_maps']} — {result['clase_motivo']}")

    stored = subjects.loc[args.sujeto, "puntuacion_dano"]
    same = np.isclose(result["puntuacion_dano"], stored, atol=1e-9)
    print(f"6. La web enseña {stored:.2f} para este sujeto: {'coincide' if same else 'NO coincide'}")
    print(f"   {time.perf_counter() - started:.1f} s")


if __name__ == "__main__":
    main()
