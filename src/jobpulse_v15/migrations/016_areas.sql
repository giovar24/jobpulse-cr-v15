-- 016_areas.sql
-- Filtro por area de empleo.
--
-- 1. Taxonomia de areas DEFINIDA POR EL SISTEMA (area) + reglas de
--    clasificacion (area_regla) + clasificacion de cada oferta (job_area).
-- 2. El perfil marca sus areas como hechos (category='area') -> se extiende
--    el CHECK de candidate_profile_facts (reconstruccion de la tabla; se
--    copian TODAS las filas, no se borra ni se funde nada).
-- 3. El Paso 5 marca las ofertas fuera de las areas del perfil con el estado
--    'fuera_de_area' -> se extiende el CHECK de job_match (reconstruccion;
--    se copian TODAS las corridas historicas).
--
-- Nota: la taxonomia y las reglas se cargan desde la semilla
-- src/jobpulse_v15/seeds/areas.json (comando CLI `init-areas`), no aqui:
-- la configuracion vive en la BD, no en el codigo.

-- ---------------------------------------------------------------
-- 1. Taxonomia y reglas
-- ---------------------------------------------------------------
CREATE TABLE area (
  codigo      TEXT    NOT NULL PRIMARY KEY CHECK (length(trim(codigo)) > 0),
  nombre      TEXT    NOT NULL CHECK (length(trim(nombre)) > 0),
  descripcion TEXT,
  orden       INTEGER NOT NULL DEFAULT 0,
  activa      INTEGER NOT NULL DEFAULT 1 CHECK (activa IN (0, 1))
);

CREATE TABLE area_regla (
  regla_id  INTEGER PRIMARY KEY AUTOINCREMENT,
  area_codigo TEXT NOT NULL REFERENCES area(codigo) ON DELETE CASCADE,
  patron     TEXT    NOT NULL CHECK (length(trim(patron)) > 0),
  fuente     TEXT    NOT NULL DEFAULT 'titulo'
             CHECK (fuente IN ('titulo', 'descripcion', 'ambos')),
  prioridad  INTEGER NOT NULL DEFAULT 0,
  activa     INTEGER NOT NULL DEFAULT 1 CHECK (activa IN (0, 1)),
  UNIQUE (area_codigo, patron, fuente)
);

CREATE INDEX idx_area_regla_area ON area_regla(area_codigo, activa);

CREATE TABLE job_area (
  job_id      TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
  area_codigo TEXT NOT NULL REFERENCES area(codigo) ON DELETE CASCADE,
  confianza   TEXT NOT NULL DEFAULT 'titulo'
              CHECK (confianza IN ('titulo', 'descripcion', 'manual')),
  evidencia   TEXT,
  clasificado_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (job_id, area_codigo)
);

CREATE INDEX idx_job_area_area ON job_area(area_codigo);

-- ---------------------------------------------------------------
-- 2. El perfil puede marcar areas (facts category='area')
-- ---------------------------------------------------------------
CREATE TABLE candidate_profile_facts_new (
    profile_fact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL CHECK (
        category IN (
            'language', 'education', 'license', 'experience', 'skill',
            'certification', 'work_authorization', 'schedule', 'availability',
            'other', 'contact', 'summary', 'project', 'area'
        )
    ),
    value_code TEXT NOT NULL COLLATE NOCASE CHECK (length(trim(value_code)) > 0),
    value_text TEXT NOT NULL CHECK (length(trim(value_text)) > 0),
    qualifier TEXT,
    education_status TEXT CHECK (
        education_status IS NULL OR education_status IN (
            'completed', 'pursuing', 'unspecified'
        )
    ),
    numeric_value REAL CHECK (numeric_value IS NULL OR numeric_value >= 0),
    unit TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    origin TEXT NOT NULL DEFAULT 'manual'
        CHECK (origin IN ('manual', 'imported')),
    source_import_id INTEGER REFERENCES candidate_profile_imports(
        profile_import_id
    ) ON DELETE SET NULL,
    codigo_canonico TEXT,
    UNIQUE(category, value_code)
);

INSERT INTO candidate_profile_facts_new (
    profile_fact_id, category, value_code, value_text, qualifier,
    education_status, numeric_value, unit, notes, created_at, updated_at,
    origin, source_import_id, codigo_canonico
)
SELECT
    profile_fact_id, category, value_code, value_text, qualifier,
    education_status, numeric_value, unit, notes, created_at, updated_at,
    origin, source_import_id, codigo_canonico
FROM candidate_profile_facts;

DROP TABLE candidate_profile_facts;
ALTER TABLE candidate_profile_facts_new RENAME TO candidate_profile_facts;

CREATE INDEX idx_candidate_profile_category
    ON candidate_profile_facts(category, value_code);
CREATE INDEX idx_cpf_canonico ON candidate_profile_facts(codigo_canonico);

-- ---------------------------------------------------------------
-- 3. Nuevo estado del Paso 5: 'fuera_de_area'
-- ---------------------------------------------------------------
CREATE TABLE job_match_new (
  job_id           TEXT    NOT NULL,
  corrida_id       TEXT    NOT NULL,
  estado           TEXT    NOT NULL CHECK (estado IN (
    'calificada', 'revisar_a_mano', 'baja_compatibilidad',
    'descartada', 'datos_insuficientes', 'sin_requisitos',
    'fuera_de_area'
  )),
  puntaje          REAL,
  cubiertos        TEXT,
  faltantes        TEXT,
  motivo           TEXT,
  cobertura        REAL,
  evaluado_at      TEXT    NOT NULL DEFAULT (datetime('now')),
  cubiertos_count  INTEGER,
  faltantes_count  INTEGER,
  no_v_count       INTEGER,
  nc_count         INTEGER,
  total_req        INTEGER,
  evaluables       INTEGER,
  valida           INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY (job_id, corrida_id),
  FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);

INSERT INTO job_match_new (
    job_id, corrida_id, estado, puntaje, cubiertos, faltantes, motivo,
    cobertura, evaluado_at, cubiertos_count, faltantes_count, no_v_count,
    nc_count, total_req, evaluables, valida
)
SELECT
    job_id, corrida_id, estado, puntaje, cubiertos, faltantes, motivo,
    cobertura, evaluado_at, cubiertos_count, faltantes_count, no_v_count,
    nc_count, total_req, evaluables, valida
FROM job_match;

DROP TABLE job_match;
ALTER TABLE job_match_new RENAME TO job_match;

CREATE INDEX idx_job_match_estado ON job_match(estado);
CREATE INDEX idx_job_match_corrida ON job_match(corrida_id);
CREATE INDEX idx_job_match_cobertura ON job_match(cobertura);
CREATE INDEX idx_job_match_valida ON job_match(valida);
CREATE INDEX idx_job_match_corrida_valida ON job_match(corrida_id, valida);
