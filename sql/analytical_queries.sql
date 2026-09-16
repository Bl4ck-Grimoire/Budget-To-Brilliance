-- ============================================================================
-- Analytical queries R1-R5 -- all of them run against the Data Warehouse
-- (never against the source file nor an intermediate DataFrame, as
-- required by section 15).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- R1: Official vs. non-official gap, by period
-- (excludes the "No aplica" member -- students with no school -- because
--  R1 specifically compares types of school)
-- ----------------------------------------------------------------------------
SELECT
    p.periodo,
    c.cole_naturaleza,
    ROUND(AVG(f.punt_global), 1) AS puntaje_global_promedio,
    COUNT(*) AS n_estudiantes
FROM fact_resultado_saber11 f
JOIN dim_colegio c ON f.id_colegio = c.id_colegio
JOIN dim_periodo p ON f.id_periodo = p.id_periodo
WHERE c.cole_naturaleza <> 'No aplica'
GROUP BY p.periodo, c.cole_naturaleza
ORDER BY p.periodo, c.cole_naturaleza;


-- ----------------------------------------------------------------------------
-- R2: Average score by school shift (jornada), controlling for naturaleza
-- ----------------------------------------------------------------------------
SELECT
    c.cole_naturaleza,
    c.cole_jornada,
    ROUND(AVG(f.punt_global), 1) AS puntaje_global_promedio,
    COUNT(*) AS n_estudiantes
FROM fact_resultado_saber11 f
JOIN dim_colegio c ON f.id_colegio = c.id_colegio
WHERE c.cole_jornada <> 'No aplica'
GROUP BY c.cole_naturaleza, c.cole_jornada
ORDER BY c.cole_naturaleza, puntaje_global_promedio DESC;


-- ----------------------------------------------------------------------------
-- R3: Urban-rural gap by department (top 10 largest gap)
-- ----------------------------------------------------------------------------
SELECT
    depto,
    urbano_prom,
    rural_prom,
    ROUND(urbano_prom - rural_prom, 1) AS brecha
FROM (
    SELECT
        c.cole_depto_ubicacion AS depto,
        AVG(CASE WHEN c.cole_area_ubicacion = 'URBANO' THEN f.punt_global END) AS urbano_prom,
        AVG(CASE WHEN c.cole_area_ubicacion = 'RURAL'  THEN f.punt_global END) AS rural_prom,
        COUNT(*) AS n
    FROM fact_resultado_saber11 f
    JOIN dim_colegio c ON f.id_colegio = c.id_colegio
    WHERE c.cole_area_ubicacion <> 'No aplica'
    GROUP BY c.cole_depto_ubicacion
    HAVING n >= 200
) t
WHERE urbano_prom IS NOT NULL AND rural_prom IS NOT NULL
ORDER BY brecha DESC
LIMIT 10;


-- ----------------------------------------------------------------------------
-- R4: Departmental ranking of the average global score, by period
-- (top/bottom 5 of the most recent period, as an example of the general
--  pattern)
-- ----------------------------------------------------------------------------
SELECT
    p.periodo,
    c.cole_depto_ubicacion AS depto,
    ROUND(AVG(f.punt_global), 1) AS puntaje_global_promedio,
    COUNT(*) AS n_estudiantes
FROM fact_resultado_saber11 f
JOIN dim_colegio c ON f.id_colegio = c.id_colegio
JOIN dim_periodo p ON f.id_periodo = p.id_periodo
WHERE c.cole_depto_ubicacion <> 'No aplica' AND p.periodo = '2025-2'
GROUP BY p.periodo, c.cole_depto_ubicacion
HAVING n_estudiantes >= 200
ORDER BY puntaje_global_promedio DESC;
-- (for the full 2021-2 to 2025-2 evolution, drop the period filter and add
--  ORDER BY p.periodo, puntaje_global_promedio DESC)


-- ----------------------------------------------------------------------------
-- R5: Gender gap in the global score and by subject area, by period
-- ----------------------------------------------------------------------------
SELECT
    p.periodo,
    g.genero_descripcion,
    ROUND(AVG(f.punt_global), 1)              AS punt_global_prom,
    ROUND(AVG(f.punt_matematicas), 1)         AS punt_matematicas_prom,
    ROUND(AVG(f.punt_lectura_critica), 1)     AS punt_lectura_critica_prom,
    COUNT(*) AS n_estudiantes
FROM fact_resultado_saber11 f
JOIN dim_genero g ON f.id_genero = g.id_genero
JOIN dim_periodo p ON f.id_periodo = p.id_periodo
WHERE g.estu_genero IN ('F', 'M')
GROUP BY p.periodo, g.genero_descripcion
ORDER BY p.periodo, g.genero_descripcion;
