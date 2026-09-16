import pandas as pd

# Mapping of known/inconsistent values -> canonical value
_AREA_HARMONIZATION = {
    "URBANA": "URBANO",
    "URBANO": "URBANO",
    "RURAL": "RURAL",
}

PUNT_COLS = [
    "punt_lectura_critica", "punt_matematicas", "punt_sociales_ciudadanas",
    "punt_c_naturales", "punt_ingles", "punt_global",
]


def clean_chunk(chunk: pd.DataFrame, periodo: str) -> pd.DataFrame:
    chunk = chunk.copy()

    # 1) Standardized period (overwrites the file's own code, e.g. 20212)
    chunk["periodo"] = periodo

    # 2) Harmonize location area (URBANA/URBANO -> URBANO)
    if "cole_area_ubicacion" in chunk.columns:
        chunk["cole_area_ubicacion"] = chunk["cole_area_ubicacion"].map(_AREA_HARMONIZATION).where(
            chunk["cole_area_ubicacion"].notna(), other=pd.NA
        )

    # 3) Numeric types on the scores
    for col in PUNT_COLS:
        if col in chunk.columns:
            chunk[col] = pd.to_numeric(chunk[col], errors="coerce")

    # 4) Flag suspicious scores (punt_global == 0) without dropping them
    if "punt_global" in chunk.columns:
        chunk["puntaje_sospechoso"] = chunk["punt_global"].eq(0)

    return chunk


def drop_duplicates_stateful(chunk: pd.DataFrame, seen_ids: set) -> pd.DataFrame:
    # (1) duplicates within this same chunk
    chunk = chunk.drop_duplicates(subset=["estu_consecutivo"], keep="first")

    # (2) duplicates against IDs already seen in earlier chunks
    already_seen = chunk["estu_consecutivo"].isin(seen_ids)
    if already_seen.any():
        chunk = chunk.loc[~already_seen].copy()

    seen_ids.update(chunk["estu_consecutivo"].tolist())
    return chunk
