import csv
import logging
from pathlib import Path
from typing import Iterator

import pandas as pd

from config import PERIODOS, RAW_DATA_DIR, CHUNK_SIZE, periodo_a_nombre_archivo

log = logging.getLogger(__name__)


def _detect_encoding(archivo: Path, sample_bytes: int = 200_000) -> str:
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            with open(archivo, "r", encoding=enc) as f:
                f.read(sample_bytes)
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"


def _detect_separator(archivo: Path, encoding: str) -> str:
    with open(archivo, "r", encoding=encoding, errors="replace") as f:
        sample = f.read(65_536)
    try:
        return csv.Sniffer().sniff(sample, delimiters="|;,\t\xac").delimiter
    except csv.Error:
        first_line = sample.splitlines()[0] if sample else ""
        candidates = ["|", ";", ",", "\t", "\xac"]
        return max(candidates, key=first_line.count)


def localizar_archivo(periodo: str) -> dict:
    """Locates the file for a period and detects its encoding/separator."""
    archivo = RAW_DATA_DIR / periodo_a_nombre_archivo(periodo)
    if not archivo.exists():
        raise FileNotFoundError(
            f"Could not find '{archivo}'. Place the DataIcfes .txt files in "
            f"{RAW_DATA_DIR}, or adjust ICFES_RAW_DIR in your .env."
        )
    encoding = _detect_encoding(archivo)
    separador = _detect_separator(archivo, encoding)
    return {"periodo": periodo, "archivo": archivo, "encoding": encoding, "separador": separador}


def extract_periodo(periodo: str, chunksize: int = CHUNK_SIZE, usecols: list = None) -> Iterator[pd.DataFrame]:
    info = localizar_archivo(periodo)
    log.info("[EXTRACT] %s <- %s (encoding=%s, sep=%r, usecols=%s)",
              periodo, info["archivo"].name, info["encoding"], info["separador"],
              usecols if usecols else "all")
    yield from pd.read_csv(
        info["archivo"], sep=info["separador"], encoding=info["encoding"],
        chunksize=chunksize, usecols=usecols, low_memory=False,
    )


def extract_todos_los_periodos(periodos: list = None) -> Iterator[tuple]:
    for periodo in periodos or PERIODOS:
        for chunk in extract_periodo(periodo):
            yield periodo, chunk
