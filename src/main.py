import logging
import time

import extract
import transform
import dimensional_model as dm
import load
import validate
import report
from config import PERIODOS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

COLS_COLEGIO = [
    "cole_codigo_icfes", "cole_nombre_establecimiento", "cole_naturaleza",
    "cole_jornada", "cole_area_ubicacion", "cole_depto_ubicacion", "cole_mcpio_ubicacion",
]
COLS_HECHOS = COLS_COLEGIO + [
    "estu_consecutivo", "estu_genero", "punt_lectura_critica", "punt_matematicas",
    "punt_sociales_ciudadanas", "punt_c_naturales", "punt_ingles", "punt_global",
]


def pasada_1_construir_dimensiones():
    log.info("=== PASS 1: building dimensions (streaming) ===")
    builder = dm.ColegioDimBuilder()
    for periodo in PERIODOS:
        for chunk in extract.extract_periodo(periodo, usecols=COLS_COLEGIO):
            chunk = transform.clean_chunk(chunk, periodo)
            builder.add_chunk(chunk[COLS_COLEGIO])

    dim_colegio = builder.finalize()
    dim_genero = dm.build_dim_genero()
    dim_periodo = dm.build_dim_periodo()
    return dim_colegio, dim_genero, dim_periodo


def pasada_2_construir_y_cargar_hechos(conn, dim_colegio_lookup, dim_genero_lookup, dim_periodo_lookup):
    log.info("=== PASS 2: building and loading the fact table ===")
    conteos_por_periodo = {}
    for periodo in PERIODOS:
        seen_ids = set()  # reset per period: matches the grain (student-attempt-PERIOD)
        total_periodo = 0
        for chunk in extract.extract_periodo(periodo, usecols=COLS_HECHOS):
            chunk = transform.clean_chunk(chunk, periodo)
            chunk = transform.drop_duplicates_stateful(chunk, seen_ids)
            chunk = dm.map_fact_keys(chunk, dim_colegio_lookup, dim_genero_lookup, dim_periodo_lookup)
            load.load_fact_chunk(conn, chunk)
            total_periodo += len(chunk)
        conteos_por_periodo[periodo] = total_periodo
        log.info("[LOAD] %s: %s rows loaded into fact_resultado_saber11", periodo, total_periodo)
    return conteos_por_periodo


def main():
    t0 = time.time()

    # 0) The database is verified/created BEFORE trying to connect to it --
    #    connecting straight to a database that doesn't exist yet makes
    #    MySQL reject the connection ("Unknown database").
    load.ensure_database_exists()
    conn = load.get_connection()

    # 1) Idempotent schema: if the tables already exist (with data), this
    #    is a no-op -- DROP is never used.
    load.create_schema(conn, "sql/create_dw.sql")

    dim_colegio, dim_genero, dim_periodo = pasada_1_construir_dimensiones()
    load.load_dim(conn, dim_colegio, "dim_colegio")
    load.load_dim(conn, dim_genero, "dim_genero")
    load.load_dim(conn, dim_periodo, "dim_periodo")

    dim_colegio_lookup = dict(zip(dim_colegio["cole_codigo_icfes"], dim_colegio["id_colegio"]))
    dim_genero_lookup = dict(zip(dim_genero["estu_genero"], dim_genero["id_genero"]))
    dim_periodo_lookup = dict(zip(dim_periodo["periodo"], dim_periodo["id_periodo"]))

    conteos_por_periodo = pasada_2_construir_y_cargar_hechos(
        conn, dim_colegio_lookup, dim_genero_lookup, dim_periodo_lookup
    )
    total_esperado = sum(conteos_por_periodo.values())

    log.info("=== VALIDATE ===")
    validate.ejecutar_todas_las_validaciones(conn, total_esperado, conteos_por_periodo)

    log.info("=== REPORT ===")
    report.generar_reportes()

    conn.close()
    log.info("Pipeline finished in %.1f seconds", time.time() - t0)


if __name__ == "__main__":
    main()
