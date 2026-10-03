"""Base pública de enfisema en TC (Sørensen et al., IEEE TMI 2010).

39 sujetos (9 nunca fumadores, 10 fumadores, 20 fumadores con EPOC), tres
cortes HRCT por sujeto con patrón dominante y severidad consensuados por un
radiólogo y un neumólogo, más 168 parches anotados.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

SEVERITY = ("sin enfisema", "mínimo", "leve", "moderado", "grave", "muy grave")
PATTERN = {1: "NT", 2: "CLE", 3: "PSE", 4: "PLE"}


def slice_table(root: Path) -> pd.DataFrame:
    """Una fila por corte: ruta, sujeto, nivel, severidad (0-5) y patrón dominante."""
    severity = pd.read_csv(root / "slice_severity.csv", header=None, names=["slice", "severity"])
    pattern = pd.read_csv(root / "slice_labels.csv", header=None, names=["slice", "pattern"])
    table = severity.merge(pattern, on="slice", validate="one_to_one")
    table[["subject", "level"]] = table["slice"].str.split("_", expand=True)
    table["path"] = [root / "slices" / f"{name}.tiff" for name in table["slice"]]
    missing = [p for p in table["path"] if not p.exists()]
    if missing:
        raise FileNotFoundError(f"faltan cortes, ejecuta scripts/fetch_data.sh: {missing[:3]}")
    return table


def patch_table(root: Path) -> pd.DataFrame:
    """Una fila por parche de 61x61: ruta, sujeto y clase (NT, CLE, PSE)."""
    labels = pd.read_csv(root / "patch_labels.csv", header=None, names=["pattern"])
    subjects = pd.read_csv(root / "patch_subjects.csv", header=None, names=["subject"])
    table = pd.concat([labels, subjects], axis=1)
    table["path"] = [root / "patches" / f"patch{i}.tiff" for i in range(1, len(table) + 1)]
    return table
