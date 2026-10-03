"""Metadatos de adquisición de una serie DICOM: son los confusores del análisis."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path, PurePosixPath

import pydicom

ZIP_SEPARATOR = "::"  # `ruta/al.zip::carpeta/dentro` nombra una serie sin descomprimir el zip

# Etiqueta DICOM -> nombre de columna. El kernel, el grosor y la dosis cambian la
# densidad medida tanto como la enfermedad temprana.
TAGS = {
    "PatientID": "paciente",
    "SeriesInstanceUID": "serie_uid",
    "Modality": "modalidad",
    "SeriesDescription": "serie_descripcion",
    "ProtocolName": "protocolo",
    "ImageType": "tipo_imagen",
    "Manufacturer": "fabricante",
    "ManufacturerModelName": "modelo",
    "ConvolutionKernel": "kernel",
    "SliceThickness": "grosor_mm",
    "PixelSpacing": "pixel_mm",
    "ReconstructionDiameter": "fov_mm",
    "KVP": "kvp",
    "XRayTubeCurrent": "corriente_ma",
    "Exposure": "exposicion_mas",
    "CTDIvol": "ctdi_vol",
    "ContrastBolusAgent": "contraste",
    "PatientPosition": "posicion",
    "PatientSex": "sexo",
    "PatientAge": "edad",
    "StudyDate": "fecha",
}


def _columns(header: pydicom.Dataset) -> dict[str, str]:
    out = {}
    for tag, column in TAGS.items():
        value = header.get(tag)
        if value is not None:
            out[column] = "\\".join(map(str, value)) if isinstance(value, (list, pydicom.multival.MultiValue)) else str(value)
    return out


def read_header(path: Path) -> dict[str, str]:
    return _columns(pydicom.dcmread(path, stop_before_pixels=True, force=True))


def _inventory_folder(root: Path) -> list[dict[str, str]]:
    by_series: dict[tuple[Path, str], dict] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".dcm", ".ima", ""}:
            continue
        try:
            uid = str(pydicom.dcmread(path, stop_before_pixels=True, specific_tags=["SeriesInstanceUID"]).SeriesInstanceUID)
        except Exception:  # no es DICOM
            continue
        key = (path.parent, uid)
        if key not in by_series:
            by_series[key] = {"sujeto": path.relative_to(root).parts[0], "carpeta": str(path.parent),
                              **read_header(path), "cortes": 0}
        by_series[key]["cortes"] += 1
    return list(by_series.values())


def _inventory_zip(path: Path) -> list[dict[str, str]]:
    """Series de un zip por sujeto, sin extraerlo: se lee la cabecera de un fichero por carpeta."""
    by_folder: dict[str, dict] = {}
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            folder = str(PurePosixPath(info.filename).parent)
            row = by_folder.get(folder)
            if row is None:
                try:
                    header = _columns(pydicom.dcmread(io.BytesIO(archive.read(info)), stop_before_pixels=True, force=True))
                except Exception:  # no es DICOM
                    header = {}
                row = by_folder[folder] = {"sujeto": path.stem, "carpeta": f"{path}{ZIP_SEPARATOR}{folder}",
                                           **header, "cortes": 0}
            row["cortes"] += 1
    return list(by_folder.values())


def inventory(root: Path) -> list[dict[str, str]]:
    """Una fila por serie DICOM bajo `root`, con su carpeta, número de cortes y metadatos.

    Acepta carpetas de DICOM sueltos y también un zip por sujeto. El sujeto es
    el nombre del zip o la primera carpeta bajo `root`.
    """
    root = Path(root)
    rows = []
    for archive in sorted(root.glob("*.zip")):
        rows.extend(_inventory_zip(archive))
    return rows + _inventory_folder(root)
