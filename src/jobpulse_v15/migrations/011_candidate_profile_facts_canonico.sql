-- 011_candidate_profile_facts_canonico.sql
-- Agrega columna codigo_canonico a candidate_profile_facts.
-- No es idempotente: ALTER TABLE ADD COLUMN falla si la columna ya existe.
-- La BD versionada (user_version) evita ejecución doble.

ALTER TABLE candidate_profile_facts ADD COLUMN codigo_canonico TEXT;

CREATE INDEX IF NOT EXISTS idx_cpf_canonico ON candidate_profile_facts(codigo_canonico);

-- ---------------------------------------------------------------
-- Fin de la migración 011
-- ---------------------------------------------------------------