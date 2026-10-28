-- O8 ciclo de vida: columna `dup_of` para marcar republicaciones reconocidas.
-- Las copias heredan el estado manual del original (ver ciclo_vida.py) y nacen
-- ocultas via user_job_state (skip_automatic=1). Nunca se borra ni se funde:
-- la marca es auditable y revocable con un UPDATE.
ALTER TABLE jobs ADD COLUMN dup_of TEXT;

CREATE INDEX idx_jobs_dup_of ON jobs(dup_of);
