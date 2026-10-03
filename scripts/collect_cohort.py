"""Junta las salidas por sujeto en las tablas de la cohorte que leen el análisis y la app.

    python scripts/collect_cohort.py outputs/cohorte --calidad outputs/calidad_series.csv
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from maps.measures import measures_dictionary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cohort", type=Path)
    parser.add_argument("--calidad", type=Path, help="CSV de check_series.py: deja fuera las series incompletas")
    parser.add_argument("--repuesto", type=Path,
                        help="otra cohorte de los mismos sujetos (otra reconstrucción): de ahí salen los que aquí tienen la serie incompleta")
    parser.add_argument("--calidad-repuesto", type=Path, help="CSV de check_series.py de la cohorte de repuesto")
    args = parser.parse_args()

    folders = sorted(p for p in (args.cohort / "sujetos").iterdir() if (p / "features.csv").exists())
    if not folders:
        raise SystemExit(f"no hay sujetos procesados en {args.cohort / 'sujetos'}")
    replaced = []
    if args.calidad is not None:
        quality = pd.read_csv(args.calidad, dtype={"subject_id": str})
        incomplete = set(quality.loc[~quality["completa"].astype(bool), "subject_id"])
        dropped = sorted(p.name for p in folders if p.name in incomplete)
        folders = [p for p in folders if p.name not in incomplete]
        if args.repuesto is not None:
            spare_ok = None
            if args.calidad_repuesto is not None:
                spare = pd.read_csv(args.calidad_repuesto, dtype={"subject_id": str})
                spare_ok = set(spare.loc[spare["completa"].astype(bool), "subject_id"])
            for subject in dropped:
                folder = args.repuesto / "sujetos" / subject
                if (folder / "features.csv").exists() and (spare_ok is None or subject in spare_ok):
                    folders.append(folder)
                    replaced.append(subject)
        print(f"serie incompleta ({len(dropped)}): {dropped}; recuperados de {args.repuesto}: {replaced}")
    features = pd.concat([pd.read_csv(p / "features.csv", dtype={"subject_id": str}) for p in folders], ignore_index=True)
    features.to_csv(args.cohort / "features.csv", index=False)
    acquisition = pd.DataFrame([json.loads((p / "meta.json").read_text()) for p in folders])
    # Qué reconstrucción se midió en cada sujeto: la de la cohorte o, si estaba incompleta, la de repuesto.
    acquisition["de_repuesto"] = acquisition["subject_id"].astype(str).isin(replaced)
    acquisition.to_csv(args.cohort / "adquisicion.csv", index=False)
    (args.cohort / "measures.json").write_text(json.dumps(measures_dictionary(), indent=2, ensure_ascii=False))
    print(f"{features['subject_id'].nunique()} sujetos, {features.shape[1] - 2} medidas por región")


if __name__ == "__main__":
    main()
