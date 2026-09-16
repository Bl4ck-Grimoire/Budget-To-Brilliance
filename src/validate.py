import logging

log = logging.getLogger(__name__)


def validar_conteo_total(conn, total_esperado: int) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM fact_resultado_saber11")
        (total_cargado,) = cur.fetchone()
    ok = total_cargado == total_esperado
    log.info("[VALIDATE] total count: expected=%s loaded=%s -> %s",
              total_esperado, total_cargado, "OK" if ok else "MISMATCH")
    return ok


def validar_conteo_por_periodo(conn, esperado_por_periodo: dict) -> bool:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT p.periodo, COUNT(*) FROM fact_resultado_saber11 f
            JOIN dim_periodo p ON f.id_periodo = p.id_periodo
            GROUP BY p.periodo ORDER BY p.periodo
        """)
        cargado_por_periodo = dict(cur.fetchall())

    all_ok = True
    for periodo, esperado in esperado_por_periodo.items():
        cargado = cargado_por_periodo.get(periodo, 0)
        ok = cargado == esperado
        all_ok = all_ok and ok
        log.info("[VALIDATE] %s: expected=%s loaded=%s -> %s", periodo, esperado, cargado, "OK" if ok else "MISMATCH")
    return all_ok


def validar_nulos_criticos(conn) -> bool:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                SUM(id_colegio IS NULL) AS null_colegio,
                SUM(id_genero IS NULL)  AS null_genero,
                SUM(id_periodo IS NULL) AS null_periodo
            FROM fact_resultado_saber11
        """)
        null_colegio, null_genero, null_periodo = cur.fetchone()
    ok = (null_colegio, null_genero, null_periodo) == (0, 0, 0)
    log.info("[VALIDATE] nulls in FKs -> colegio=%s genero=%s periodo=%s (%s)",
              null_colegio, null_genero, null_periodo, "OK" if ok else "FAIL")
    return ok


def validar_unicidad_grano(conn) -> bool:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) FROM (
                SELECT estu_consecutivo, id_periodo FROM fact_resultado_saber11
                GROUP BY estu_consecutivo, id_periodo HAVING COUNT(*) > 1
            ) t
        """)
        (duplicates,) = cur.fetchone()
    ok = duplicates == 0
    log.info("[VALIDATE] duplicates of (estu_consecutivo, periodo) in the DW: %s -> %s", duplicates, "OK" if ok else "FAIL")
    return ok


def validar_integridad_referencial(conn) -> bool:
    checks = {
        "colegio": "LEFT JOIN dim_colegio d ON f.id_colegio = d.id_colegio WHERE d.id_colegio IS NULL",
        "genero": "LEFT JOIN dim_genero d ON f.id_genero = d.id_genero WHERE d.id_genero IS NULL",
        "periodo": "LEFT JOIN dim_periodo d ON f.id_periodo = d.id_periodo WHERE d.id_periodo IS NULL",
    }
    all_ok = True
    with conn.cursor() as cur:
        for name, join_clause in checks.items():
            cur.execute(f"SELECT COUNT(*) FROM fact_resultado_saber11 f {join_clause}")
            (orphans,) = cur.fetchone()
            ok = orphans == 0
            all_ok = all_ok and ok
            log.info("[VALIDATE] orphans in %s: %s -> %s", name, orphans, "OK" if ok else "FAIL")
    return all_ok


def validar_rango_puntajes(conn) -> bool:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) FROM fact_resultado_saber11
            WHERE punt_global < 0 OR punt_global > 500
        """)
        (out_of_range,) = cur.fetchone()
    ok = out_of_range == 0
    log.info("[VALIDATE] scores outside [0,500]: %s -> %s", out_of_range, "OK" if ok else "FAIL")
    return ok


def ejecutar_todas_las_validaciones(conn, total_esperado: int, esperado_por_periodo: dict) -> bool:
    results = [
        validar_conteo_total(conn, total_esperado),
        validar_conteo_por_periodo(conn, esperado_por_periodo),
        validar_nulos_criticos(conn),
        validar_unicidad_grano(conn),
        validar_integridad_referencial(conn),
        validar_rango_puntajes(conn),
    ]
    all_ok = all(results)
    log.info("[VALIDATE] overall result: %s", "ALL VALIDATIONS PASSED" if all_ok else "THERE ARE FAILURES")
    return all_ok
