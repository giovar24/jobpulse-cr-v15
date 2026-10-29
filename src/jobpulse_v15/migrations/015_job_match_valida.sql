-- 015_job_match_valida.sql
-- Marca que corrida de job_match sigue vigente. Cada cambio de regla genera una
-- corrida nueva y deja las anteriores con valida = 0 (trazabilidad: nunca se
-- actualiza en el sitio una corrida ya emitida).
ALTER TABLE job_match ADD COLUMN valida INTEGER NOT NULL DEFAULT 1;

CREATE INDEX IF NOT EXISTS idx_job_match_valida ON job_match(valida);
CREATE INDEX IF NOT EXISTS idx_job_match_corrida_valida ON job_match(corrida_id, valida);
