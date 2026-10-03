"""Lectura de tablas clínicas tal como llegan: el borde donde se limpian los formatos."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def _decimal_commas(table: pd.DataFrame) -> pd.DataFrame:
    """Convierte a número las columnas de texto que son números con coma decimal ("3,52")."""
    for column in table.select_dtypes(exclude="number").columns:
        text = table[column].astype("string").str.strip()
        converted = pd.to_numeric(text.str.replace(",", ".", regex=False), errors="coerce").astype("float64")
        if text.notna().any() and converted.notna().sum() == text.notna().sum():
            table[column] = converted
    return table


def read_table(path: Path) -> pd.DataFrame:
    """Lee la tabla clínica en el formato en que venga: CSV, TSV, Excel, SPSS, R o Parquet."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".csv", ".tsv", ".txt"}:
        return _decimal_commas(pd.read_csv(path, sep=None, engine="python"))
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix == ".sav":
        return pd.read_spss(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix in {".rds", ".rdata", ".rda"}:
        import pyreadr

        frames = pyreadr.read_r(str(path))
        return next(iter(frames.values()))
    raise ValueError(f"no sé leer tablas {suffix}: {path}")
