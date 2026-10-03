"""Guarda el modelo ajustado para puntuar después a sujetos que no estaban en la cohorte.

Son dos ficheros en el directorio de la cohorte. `modelo.json` se lee a simple
vista: las medidas de la puntuación, las covariables, el umbral de daño y la
regla funcional. `modelo.pkl` lleva los modelos normativos por región, que son
coeficientes y no se leen a mano.
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path

from maps.normative import NormativeModel

FORMAT = 1  # sube cuando cambie lo que se guarda o los campos de NormativeModel
SIGNATURE = "maps-modelo"
DESCRIPTION_FILE, MODELS_FILE = "modelo.json", "modelo.pkl"


def save_model(path: Path, models: dict[str, NormativeModel], description: dict) -> None:
    """Escribe en el directorio `path` los modelos por región y su descripción legible."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    (path / DESCRIPTION_FILE).write_text(json.dumps(description, indent=2, ensure_ascii=False))
    with (path / MODELS_FILE).open("wb") as file:
        # la cabecera va en su propio pickle: se lee aunque el resto ya no se sepa cargar
        pickle.dump((SIGNATURE, FORMAT), file)
        pickle.dump(models, file)


def load_model(path: Path) -> tuple[dict[str, NormativeModel], dict]:
    """Modelos por región y descripción guardados por `save_model` en el directorio `path`.

    Cargar un pickle ejecuta el código que lleve dentro. Aquí vale porque solo
    se cargan ficheros que hemos escrito nosotros: no lo uses con un modelo que
    venga de fuera.
    """
    path = Path(path)
    for name in (DESCRIPTION_FILE, MODELS_FILE):
        if not (path / name).is_file():
            raise ValueError(f"no hay modelo guardado en {path}: falta {name}, que escribe scripts/score_cohort.py")
    with (path / MODELS_FILE).open("rb") as file:
        try:
            signature, version = pickle.load(file)
        except Exception:  # un fichero ajeno puede fallar de cualquier manera al deserializar
            signature, version = None, None
        if signature != SIGNATURE:
            raise ValueError(f"{path / MODELS_FILE} no es un modelo guardado por save_model")
        if version != FORMAT:
            raise ValueError(
                f"{path / MODELS_FILE} está en formato {version} y este código lee el formato {FORMAT}: "
                "vuelve a ejecutar scripts/score_cohort.py para guardarlo de nuevo"
            )
        try:
            models = pickle.load(file)
        except Exception as error:
            raise ValueError(
                f"{path / MODELS_FILE} dice ser del formato {FORMAT} pero no se puede cargar ({error}): "
                "vuelve a ejecutar scripts/score_cohort.py"
            ) from error
    return models, json.loads((path / DESCRIPTION_FILE).read_text())
