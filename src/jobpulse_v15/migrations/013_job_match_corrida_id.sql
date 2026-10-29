-- 013_job_match_corrida_id.sql
-- Cambia la clave primaria de job_match a (job_id, corrida_id) para permitir
-- múltiples corridas y compararlas entre sí.
-- No es idempotente: ALTER TABLE falla si ya existe.
-- La BD versionada (user_version) evita ejecución doble.

DROP TABLE IF EXISTS job_match;

CREATE TABLE job_match (
  job_id           TEXT    NOT NULL,
  corrida_id       TEXT    NOT NULL,
  estado           TEXT    NOT NULL CHECK (estado IN (
    'calificada', 'revisar_a_mano', 'baja_compatibilidad',
    'descartada', 'datos_insuficientes', 'sin_requisitos'
  )),
  puntaje          REAL,
  cubiertos        TEXT,
  faltantes        TEXT,
  motivo           TEXT,
  cobertura        REAL,
  evaluado_at      TEXT    NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (job_id, corrida_id),
  FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_job_match_estado ON job_match(estado);
CREATE INDEX IF NOT EXISTS idx_job_match_corrida ON job_match(corrida_id);
CREATE INDEX IF NOT EXISTS idx_job_match_cobertura ON job_match(cobertura);

-- ---------------------------------------------------------------
-- Fin de la migración 013
-- ---------------------------------------------------------------