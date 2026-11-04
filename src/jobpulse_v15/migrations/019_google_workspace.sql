-- 019_google_workspace.sql
-- Corrige un alias ERRONEO de la taxonomia: Google Workspace NO es
-- Microsoft 365 (son productos distintos). El perfil y algunos avisos
-- quedaron mapeados a 'microsoft-365' por una variante mal escrita.
--
-- Que hace:
--   1. la variante 'google-workspace'/'google workspace' apunta a su propio
--      codigo canonico 'google-workspace';
--   2. los requisitos y los hechos del perfil que estaban mapeados a
--      'microsoft-365' POR ESA variante se corrigen (no se toca ningun otro
--      'microsoft-365': el que de verdad es Microsoft 365 se queda);
--   3. agrega la variante 'active-directory' (la taxonomia solo tenia
--      'active directory') para que el slug del CV resuelva igual.
--
-- Idempotente: solo cambia lo que sigue siendo erroneous.

UPDATE concepto
SET codigo_canonico = 'google-workspace'
WHERE categoria = 'skill'
  AND LOWER(TRIM(variante)) IN ('google-workspace', 'google workspace')
  AND codigo_canonico <> 'google-workspace';

UPDATE job_requirements
SET codigo_canonico = 'google-workspace'
WHERE codigo_canonico = 'microsoft-365'
  AND LOWER(TRIM(value_code)) IN ('google-workspace', 'google workspace');

UPDATE candidate_profile_facts
SET codigo_canonico = 'google-workspace',
    updated_at = CURRENT_TIMESTAMP
WHERE category = 'skill'
  AND codigo_canonico = 'microsoft-365'
  AND LOWER(TRIM(value_code)) IN ('google-workspace', 'google workspace');

INSERT OR IGNORE INTO concepto (codigo_canonico, categoria, variante, origen) VALUES
  ('google-workspace', 'skill', 'google-workspace', 'ambos'),
  ('google-workspace', 'skill', 'google workspace',   'ambos'),
  ('active-directory', 'skill', 'active-directory',   'ambos');
