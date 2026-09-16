import logging

import pandas as pd

from config import PERIODOS

log = logging.getLogger(__name__)

COLS_COLEGIO = [
    "cole_codigo_icfes", "cole_nombre_establecimiento", "cole_naturaleza",
    "cole_jornada", "cole_area_ubicacion", "cole_depto_ubicacion", "cole_mcpio_ubicacion",
]


class ColegioDimBuilder:

    def __init__(self):
        self._seen: dict[str, dict] = {}

    def add_chunk(self, chunk: pd.DataFrame) -> None:
        chunk = chunk.dropna(subset=["cole_codigo_icfes"])
        chunk = chunk.drop_duplicates(subset=["cole_codigo_icfes"])
        for record in chunk.to_dict("records"):
            codigo = record["cole_codigo_icfes"]
            if codigo not in self._seen:
                self._seen[codigo] = record

    def finalize(self) -> pd.DataFrame:
        dim = pd.DataFrame(list(self._seen.values()), columns=COLS_COLEGIO)
        dim = dim.reset_index(drop=True)
        dim.insert(0, "id_colegio", range(1, len(dim) + 1))

        not_applicable = pd.DataFrame([{
            "id_colegio": -1,
            "cole_codigo_icfes": "NO_APLICA",
            "cole_nombre_establecimiento": "No aplica (sin colegio -- validante)",
            "cole_naturaleza": "No aplica",
            "cole_jornada": "No aplica",
            "cole_area_ubicacion": "No aplica",
            "cole_depto_ubicacion": "No aplica",
            "cole_mcpio_ubicacion": "No aplica",
        }])
        result = pd.concat([not_applicable, dim], ignore_index=True)
        log.info("[DIM_COLEGIO] %s unique schools + 1 'not applicable' member", len(dim))
        return result


def build_dim_genero() -> pd.DataFrame:
    return pd.DataFrame([
        {"id_genero": 1, "estu_genero": "F", "genero_descripcion": "Femenino"},
        {"id_genero": 2, "estu_genero": "M", "genero_descripcion": "Masculino"},
        {"id_genero": -1, "estu_genero": "No informado", "genero_descripcion": "No informado"},
    ])


def build_dim_periodo(periodos: list = None) -> pd.DataFrame:
    rows = []
    for i, p in enumerate(periodos or PERIODOS, start=1):
        anio, sem = p.split("-")
        rows.append({"id_periodo": i, "periodo": p, "anio": int(anio), "semestre": int(sem)})
    return pd.DataFrame(rows)


def map_fact_keys(chunk: pd.DataFrame, dim_colegio_lookup: dict,
                   dim_genero_lookup: dict, dim_periodo_lookup: dict) -> pd.DataFrame:
    """Adds id_colegio / id_genero / id_periodo to the fact chunk, using -1
    for any value that is null or not found in the respective dimension."""
    chunk = chunk.copy()
    chunk["id_colegio"] = chunk["cole_codigo_icfes"].map(dim_colegio_lookup).fillna(-1).astype(int)
    chunk["id_genero"] = chunk["estu_genero"].map(dim_genero_lookup).fillna(-1).astype(int)
    chunk["id_periodo"] = chunk["periodo"].map(dim_periodo_lookup).fillna(-1).astype(int)
    return chunk
