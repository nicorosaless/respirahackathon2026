"""Elige los sujetos que se enseñan en la demo: uno típico de cada clase y un ejemplo de inferencia.

Se eligen por sus números, sin mirar imágenes:

- De cada clase, el sujeto más cercano a la mediana de su clase en puntuación y
  en FEV1/FVC, entre los que tienen la segmentación en orden (árbol casi todo
  unido a la tráquea), se midieron con la reconstrucción estándar y no están
  cerca del umbral.
- Para la inferencia, un sujeto de reserva (el modelo probado no lo vio) con
  obstrucción y con la TC claramente por encima del umbral de ese modelo.

Escribe `ejemplos.json` en el directorio de la cohorte. Lleva identificadores de
sujeto: se queda con la cohorte y solo lo lee la aplicación.

    python scripts/pick_examples.py mn5/cohorte.final.toml --congelado outputs/cohorte_v3
"""

from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

import pandas as pd

from maps.classify import CLASSES
from maps.measures import WHOLE_LUNG

MIN_CONNECTED = 0.90  # parte del árbol unida a la tráquea para dar la segmentación por buena
ALTERNATIVES = 3


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--congelado", type=Path, required=True, help="cohorte del modelo que se probó en reserva")
    args = parser.parse_args()
    cohort = Path(tomllib.loads(args.config.read_text())["cohorte"])
    t = pd.read_csv(cohort / "subjects.csv", dtype={"subject_id": str}).set_index("subject_id")
    whole = pd.read_csv(cohort / "features.csv", dtype={"subject_id": str})
    whole = whole[whole["region"] == WHOLE_LUNG].set_index("subject_id")
    checks = json.loads((cohort / "comprobaciones.json").read_text())
    threshold = json.loads((cohort / "modelo.json").read_text())["umbral_dano"]

    connected = (whole["via_longitud_conectada_mm"] / whole["via_longitud_mm"]).reindex(t.index)
    good = (connected >= MIN_CONNECTED) & ~t["de_repuesto"].astype(bool) & t["puntuacion_dano"].notna() \
        & ((t["puntuacion_dano"] - threshold).abs() >= checks["zona_gris"]) & (cohort / "previews").exists()
    out = {"criterio": "el más cercano a la mediana de su clase en puntuación y FEV1/FVC, con la segmentación en orden", "clases": {}}
    for name in CLASSES:
        members = t[(t["clase_maps"] == name) & good]
        # Distancia a la mediana de la clase, en desviaciones de la clase.
        distance = sum(((members[c] - members[c].median()) / members[c].std()) ** 2 for c in ("puntuacion_dano", "fev1_fvc_post_v1"))
        ranked = distance.sort_values().index.tolist()
        out["clases"][name] = {"elegido": ranked[0], "alternativas": ranked[1:1 + ALTERNATIVES], "candidatos": len(ranked)}

    frozen = pd.read_csv(args.congelado / "subjects.csv", dtype={"subject_id": str}).set_index("subject_id")
    frozen_threshold = json.loads((args.congelado / "modelo.json").read_text())["umbral_dano"]
    frozen_grey = json.loads((args.congelado / "comprobaciones.json").read_text())["zona_gris"]
    reserve = frozen[(frozen["particion"] == "reserva") & frozen.index.isin(t.index[good.reindex(t.index).fillna(False)])]
    clear = reserve[(reserve["caso_v1"] == 1) & (reserve["puntuacion_dano"] - frozen_threshold >= frozen_grey)]
    # El caso más representativo: el de puntuación mediana entre los claros.
    ranked = (clear["puntuacion_dano"] - clear["puntuacion_dano"].median()).abs().sort_values().index.tolist()
    out["inferencia"] = {"elegido": ranked[0] if ranked else None, "alternativas": ranked[1:1 + ALTERNATIVES], "candidatos": len(ranked),
                         "criterio": "sujeto de reserva con obstrucción y la TC claramente por encima del umbral del modelo que no lo vio"}
    (cohort / "ejemplos.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print({name: entry["candidatos"] for name, entry in out["clases"].items()}, "| inferencia:", out["inferencia"]["candidatos"], "candidatos")


if __name__ == "__main__":
    main()
