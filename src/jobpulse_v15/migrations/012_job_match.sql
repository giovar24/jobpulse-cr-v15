-- 012_job_match.sql
-- Tabla de decisión final por oferta (Paso 7 del flujo).
-- Persiste el resultado del Paso 5 con cobertura, motivo y corrida_id para
-- poder comparar corridas y validar ajustes de reglas.
-- No es idempotente: ALTER/CREATE falla si la tabla ya existe.
-- La BD versionada (user_version) evita ejecución doble.

CREATE TABLE IF NOT EXISTS job_match (
  job_id           TEXT    NOT NULL PRIMARY KEY REFERENCES jobs(job_id) ON DELETE CASCADE,
  estado           TEXT    NOT NULL CHECK (estado IN (
    'calificada', 'revisar_a_mano', 'baja_compatibilidad',
    'descartada', 'datos_insuficientes', 'sin_requisitos'
  )),
  puntaje          REAL,
  cubiertos        TEXT,       -- JSON con requisitos cumplidos
  faltantes        TEXT,       -- JSON con requisitos faltantes
  motivo           TEXT,       -- motivo explícito de la decisión
  cobertura        REAL,       -- fracción de requisitos evaluables (0-1)
  corrida_id       TEXT        NOT NULL,  -- identificador de la corrida para comparar versiones
  evaluado_at      TEXT        NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_job_match_estado ON job_match(estado);
CREATE INDEX IF NOT EXISTS idx_job_match_corrida ON job_match(corrida_id);
CREATE INDEX IF NOT EXISTS idx_job_match_cobertura ON job_match(cobertura);

-- ---------------------------------------------------------------
-- Fin de la migración 012
-- ---------------------------------------------------------------