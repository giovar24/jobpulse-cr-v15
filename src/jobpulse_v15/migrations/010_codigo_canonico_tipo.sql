-- 010_codigo_canonico_tipo.sql
-- Agrega tipo de comparación a concepto y columna codigo_canonico a job_requirements.
-- No es idempotente (ALTER TABLE ADD COLUMN falla si la columna ya existe).
-- La BD versionada evita ejecución doble.

-- ---------------------------------------------------------------
-- 1. Columna tipo en concepto (qué comparación usar en Paso 5)
-- ---------------------------------------------------------------
-- Valores: 'existencia' (default), 'numerico', 'nivel'
-- - existencia: coincide si codigo_canonico del CV = codigo_canonico de la oferta
-- - numerico:   compara años (minimum del requisito vs numeric_value del fact)
-- - nivel:      compara nivel (qualifier del requisito vs qualifier del fact, usando nivel_escala)

ALTER TABLE concepto ADD COLUMN tipo TEXT NOT NULL DEFAULT 'existencia'
  CHECK (tipo IN ('existencia','numerico','nivel'));

-- Actualizar tipos para conceptos que ya existen
UPDATE concepto SET tipo = 'numerico' WHERE codigo_canonico = 'experiencia-anos';
UPDATE concepto SET tipo = 'nivel'    WHERE categoria = 'license';

-- ---------------------------------------------------------------
-- 2. Columna codigo_canonico en job_requirements
-- ---------------------------------------------------------------
ALTER TABLE job_requirements ADD COLUMN codigo_canonico TEXT;

CREATE INDEX IF NOT EXISTS idx_jobreq_canonico ON job_requirements(codigo_canonico);

-- ---------------------------------------------------------------
-- 3. Poblar codigo_canonico para requisitos actuales
--    Busca en concepto normalizando value_code (lower, trim)
-- ---------------------------------------------------------------
UPDATE job_requirements
SET codigo_canonico = (
  SELECT c.codigo_canonico
  FROM concepto c
  WHERE c.variante = LOWER(TRIM(job_requirements.value_code))
    AND c.categoria = job_requirements.category
)
WHERE value_code IS NOT NULL
  AND codigo_canonico IS NULL;

-- ---------------------------------------------------------------
-- 4. Enviar a cola los que no encontraron concepto
-- ---------------------------------------------------------------
INSERT OR IGNORE INTO concepto_no_normalizado (categoria, texto, origen, veces)
SELECT DISTINCT r.category, r.value_code, 'oferta', COUNT(*)
FROM job_requirements r
JOIN job_analysis a ON a.analysis_id = r.analysis_id
WHERE a.is_current = 1
  AND r.value_code IS NOT NULL
  AND r.codigo_canonico IS NULL
GROUP BY r.category, r.value_code;

-- ---------------------------------------------------------------
-- Fin de la migración 010
-- ---------------------------------------------------------------