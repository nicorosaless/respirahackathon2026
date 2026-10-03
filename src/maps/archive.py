"""Series DICOM guardadas dentro de un zip por sujeto."""

from __future__ import annotations

import tempfile
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from maps.dicom_meta import ZIP_SEPARATOR


@contextmanager
def series_folder(source: str) -> Iterator[Path]:
    """Carpeta en disco con la serie.

    `source` es una carpeta o `ruta.zip::carpeta/dentro`. En el segundo caso se
    extrae solo esa serie a un directorio temporal (en `$TMPDIR`, que en los
    nodos de cómputo es disco local) y se borra al salir.
    """
    if ZIP_SEPARATOR not in source:
        yield Path(source)
        return
    archive_path, folder = source.split(ZIP_SEPARATOR, 1)
    prefix = folder.rstrip("/") + "/"
    with tempfile.TemporaryDirectory(prefix="maps-") as tmp, zipfile.ZipFile(archive_path) as archive:
        members = [name for name in archive.namelist() if name.startswith(prefix) and not name.endswith("/")]
        if not members:
            raise ValueError(f"{archive_path} no contiene ficheros en {folder}")
        archive.extractall(tmp, members)
        yield Path(tmp) / folder
