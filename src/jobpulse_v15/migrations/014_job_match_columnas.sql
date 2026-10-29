-- 014_job_match_columnas.sql
-- Agrega columnas de conteo a job_match para guardar estadísticas detalladas.
-- No es idempotente: ALTER TABLE falla si la columna ya existe.
-- La BD versionada (user_version) evita ejecución doble.

ALTER TABLE job_match ADD COLUMN cubiertos_count INTEGER;
ALTER TABLE job_match ADD COLUMN faltantes_count INTEGER;
ALTER TABLE job_match ADD COLUMN no_v_count INTEGER;
ALTER TABLE job_match ADD COLUMN nc_count INTEGER;
ALTER TABLE job_match ADD COLUMN total_req INTEGER;
ALTER TABLE job_match ADD COLUMN evaluables INTEGER;

-- ---------------------------------------------------------------
-- Fin de la migración 014
-- ---------------------------------------------------------------