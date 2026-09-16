-- ============================================================================
-- ETL Project — Data Engineering for Sustainable Development in Colombia
-- Data Warehouse schema (star schema) — ICFES Saber 11 / ODS 4  [MySQL]
--
-- IMPORTANT: this script is idempotent -- it uses CREATE TABLE IF NOT
-- EXISTS, never DROP TABLE. If the tables already exist (with data
-- loaded), running this script again does nothing to them. If a real,
-- deliberate reset is ever needed, do it explicitly by hand (it is not
-- part of this flow).
--
-- Grain of fact_resultado_saber11: one row = one student's attempt at the
-- Saber 11 exam, in a specific academic period (see section 10). That is
-- why the primary key is composite (estu_consecutivo, id_periodo) and not
-- just estu_consecutivo -- see the full explanation in section 13/README.
--
-- "Unknown / not applicable member" convention (standard Kimball
-- technique): each dimension includes a row with surrogate key = -1 for
-- cases where the source attribute is null (e.g. external "validante"
-- students with no associated school). The fact table NEVER loses rows
-- because of this -- each analysis decides whether to include or exclude
-- that member with a targeted WHERE clause (see sql/analytical_queries.sql).
-- ============================================================================

-- Database creation is handled by load.ensure_database_exists() in Python
-- (it uses whatever name you set in DATABASE_URL, inside your .env).
-- If you run this script by hand, first run "USE your_database_name".

-- ----------------------------------------------------------------------------
-- DIM_COLEGIO  (supports R1, R2, R3, R4)
-- id_colegio = -1 represents students with no associated school (external
-- "validante" candidates).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_colegio (
    id_colegio                  INT PRIMARY KEY,
    cole_codigo_icfes           VARCHAR(20)  NOT NULL,
    cole_nombre_establecimiento VARCHAR(255),
    cole_naturaleza             VARCHAR(20)  NOT NULL,   -- OFICIAL / NO OFICIAL / No aplica
    cole_jornada                VARCHAR(20)  NOT NULL,   -- COMPLETA/UNICA/MAÑANA/TARDE/NOCHE/SABATINA/No aplica
    cole_area_ubicacion         VARCHAR(20)  NOT NULL,   -- URBANO / RURAL / No aplica (URBANA already harmonized to URBANO)
    cole_depto_ubicacion        VARCHAR(60)  NOT NULL,
    cole_mcpio_ubicacion        VARCHAR(60),
    UNIQUE KEY uq_cole_codigo (cole_codigo_icfes)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------------------------
-- DIM_GENERO  (supports R5)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_genero (
    id_genero          INT PRIMARY KEY,
    estu_genero         VARCHAR(20) NOT NULL,   -- F / M / No informado
    genero_descripcion  VARCHAR(30) NOT NULL    -- Femenino / Masculino / No informado
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------------------------
-- DIM_PERIODO  (time axis for R1, R2, R4, R5)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_periodo (
    id_periodo  INT PRIMARY KEY,
    periodo     VARCHAR(10) NOT NULL,   -- '2021-2'
    anio        INT NOT NULL,
    semestre    INT NOT NULL,           -- 1 or 2
    UNIQUE KEY uq_periodo (periodo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------------------------
-- FACT_RESULTADO_SABER11
-- Composite PK (estu_consecutivo, id_periodo): matches exactly the grain
-- declared in section 10 ("one student-attempt IN ONE PERIOD"). In
-- practice estu_consecutivo is already unique across the whole dataset
-- (we verified it: the ICFES code embeds the year/period and never
-- repeats across periods), but the composite PK documents the grain
-- explicitly in the schema itself, instead of depending on an
-- implementation detail of an external system (DataIcfes) that is outside
-- our control.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_resultado_saber11 (
    estu_consecutivo         VARCHAR(30) NOT NULL,
    id_colegio               INT NOT NULL,
    id_genero                INT NOT NULL,
    id_periodo               INT NOT NULL,
    punt_lectura_critica     DECIMAL(5,1),
    punt_matematicas         DECIMAL(5,1),
    punt_sociales_ciudadanas DECIMAL(5,1),
    punt_c_naturales         DECIMAL(5,1),
    punt_ingles              DECIMAL(5,1),
    punt_global              DECIMAL(5,1),
    puntaje_sospechoso       BOOLEAN NOT NULL DEFAULT FALSE,  -- TRUE if punt_global = 0 (possibly an annulled/absent exam)
    PRIMARY KEY (estu_consecutivo, id_periodo),
    CONSTRAINT fk_fact_colegio FOREIGN KEY (id_colegio) REFERENCES dim_colegio(id_colegio),
    CONSTRAINT fk_fact_genero  FOREIGN KEY (id_genero)  REFERENCES dim_genero(id_genero),
    CONSTRAINT fk_fact_periodo FOREIGN KEY (id_periodo) REFERENCES dim_periodo(id_periodo),
    INDEX idx_fact_colegio (id_colegio),
    INDEX idx_fact_genero  (id_genero),
    INDEX idx_fact_periodo (id_periodo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
