import logging

import pandas as pd
import pymysql

from config import DB_CONFIG

log = logging.getLogger(__name__)

FACT_COLS = [
    "estu_consecutivo", "id_colegio", "id_genero", "id_periodo",
    "punt_lectura_critica", "punt_matematicas", "punt_sociales_ciudadanas",
    "punt_c_naturales", "punt_ingles", "punt_global", "puntaje_sospechoso",
]


def get_server_connection():

    return pymysql.connect(
        host=DB_CONFIG["host"], port=int(DB_CONFIG["port"]),
        user=DB_CONFIG["user"], password=DB_CONFIG["password"],
        charset="utf8mb4", autocommit=True,
    )


def ensure_database_exists():
    conn = get_server_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['dbname']}` "
                "CHARACTER SET utf8mb4"
            )
        log.info("[LOAD] database '%s' verified/created", DB_CONFIG["dbname"])
    finally:
        conn.close()


def get_connection():
    return pymysql.connect(
        host=DB_CONFIG["host"], port=int(DB_CONFIG["port"]),
        database=DB_CONFIG["dbname"],
        user=DB_CONFIG["user"], password=DB_CONFIG["password"],
        charset="utf8mb4", autocommit=False,
    )


def create_schema(conn, sql_path: str = "sql/create_dw.sql"):
    with open(sql_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Comment-only lines are dropped before splitting on ";" -- a ";"
    # inside a comment would otherwise break a naive split.
    sql_without_comments = "\n".join(
        line for line in lines if not line.strip().startswith("--")
    )

    with conn.cursor() as cur:
        for statement in sql_without_comments.split(";"):
            statement = statement.strip()
            if statement:
                cur.execute(statement)
    conn.commit()
    log.info(
        "[LOAD] schema verified/created from %s (nothing existing was dropped)",
        sql_path,
    )


def _python_value(value):
    if pd.isna(value):
        return None

    # numpy scalars expose .item(); plain Python types don't.
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return item()
        except ValueError:
            pass
    return value


def _records_from_dataframe(df: pd.DataFrame):
    for row in df.itertuples(index=False, name=None):
        yield tuple(_python_value(value) for value in row)


def load_dim(conn, df: pd.DataFrame, table: str):
    cols = list(df.columns)
    placeholders = ", ".join(["%s"] * len(cols))
    sql = f"INSERT IGNORE INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
    with conn.cursor() as cur:
        cur.executemany(sql, _records_from_dataframe(df))
    conn.commit()
    log.info("[LOAD] %s: %s rows processed (IGNORE if they already existed)", table, len(df))


def load_fact_chunk(conn, chunk: pd.DataFrame):
    if chunk.empty:
        return

    data = chunk[FACT_COLS]
    placeholders = ", ".join(["%s"] * len(FACT_COLS))
    sql = (
        "INSERT IGNORE INTO fact_resultado_saber11 "
        f"({', '.join(FACT_COLS)}) VALUES ({placeholders})"
    )

    with conn.cursor() as cur:
        cur.executemany(sql, _records_from_dataframe(data))
    conn.commit()
