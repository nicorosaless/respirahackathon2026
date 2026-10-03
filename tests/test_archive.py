import zipfile
from pathlib import Path

import numpy as np
import pydicom
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

from maps.archive import series_folder
from maps.dicom_meta import inventory


def _slice(path: Path, series_uid: str, kernel: str, thickness: float) -> None:
    meta = FileMetaDataset()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    meta.MediaStorageSOPClassUID = pydicom.uid.CTImageStorage
    meta.MediaStorageSOPInstanceUID = generate_uid()
    ds = FileDataset(str(path), {}, file_meta=meta, preamble=bytes(128))
    ds.SOPClassUID, ds.SOPInstanceUID = meta.MediaStorageSOPClassUID, meta.MediaStorageSOPInstanceUID
    ds.SeriesInstanceUID, ds.Modality = series_uid, "CT"
    ds.ConvolutionKernel, ds.SliceThickness = kernel, thickness
    ds.Rows = ds.Columns = 2
    ds.BitsAllocated, ds.BitsStored, ds.HighBit, ds.PixelRepresentation = 16, 16, 15, 1
    ds.SamplesPerPixel, ds.PhotometricInterpretation = 1, "MONOCHROME2"
    ds.PixelData = np.zeros((2, 2), dtype=np.int16).tobytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    ds.save_as(path)


def _subject_zip(tmp_path: Path) -> Path:
    """Un sujeto como llega en el reto: 7.zip con 7/ST000000/SE00000X/CT00000N."""
    source = tmp_path / "src" / "7" / "ST000000"
    thin, scout = generate_uid(), generate_uid()
    for i in range(5):
        _slice(source / "SE000002" / f"CT{i:06d}", thin, "B31f", 1.0)
    _slice(source / "SE000004" / "CT000000", scout, "T20f", 600.0)
    archive = tmp_path / "7.zip"
    with zipfile.ZipFile(archive, "w") as out:
        for path in sorted((tmp_path / "src").rglob("*")):
            if path.is_file():
                out.write(path, path.relative_to(tmp_path / "src"))
    return archive


def test_inventory_lists_each_series_of_a_zipped_subject(tmp_path):
    archive = _subject_zip(tmp_path)

    rows = {row["carpeta"].split("::")[1]: row for row in inventory(tmp_path) if "::" in row["carpeta"]}

    assert set(rows) == {"7/ST000000/SE000002", "7/ST000000/SE000004"}
    main = rows["7/ST000000/SE000002"]
    assert (main["sujeto"], main["cortes"], main["kernel"], main["grosor_mm"]) == ("7", 5, "B31f", "1.0")
    assert main["carpeta"].startswith(str(archive))


def test_series_folder_extracts_only_the_requested_series(tmp_path):
    archive = _subject_zip(tmp_path)

    with series_folder(f"{archive}::7/ST000000/SE000002") as folder:
        extracted = folder
        names = sorted(p.name for p in folder.iterdir())
        siblings = [p.name for p in folder.parent.iterdir()]

    assert names == [f"CT{i:06d}" for i in range(5)]
    assert siblings == ["SE000002"]
    assert not extracted.exists()


def test_a_plain_folder_is_used_in_place(tmp_path):
    with series_folder(str(tmp_path)) as folder:
        assert folder == tmp_path
