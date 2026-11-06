-- jobpulse:transaccion-propia
-- 022_site_requiere_login.sql
-- Estado "requiere_login" en la SALUD de los sitios (O13 · Ola 3.3).
--
-- MOTIVACION: un sitio que devuelve 0 avisos porque PIDE INICIAR SESION no
-- esta roto: es otro estado. Antes caia en `zero_results` y llenaba la
-- racha de "sitio muerto" (3 corridas con 0 avisos -> `review_required=1`),
-- que el usuario tenia que revisar a mano sin saber que lo que faltaba era
-- iniciar sesion. Con este estado la UI y el CLI dicen exactamente que pasa:
-- "este sitio exige iniciar sesion".
--
-- IMPORTANTE (pide login):
--   * NO suma a `consecutive_zero_runs` (no es una racha de ceros);
--   * NO se pausa solo el sitio;
--   * `mark_site_reviewed` lo acknowledges (limpia la bandera de revision)
--     pero la salud sigue diciendo `requiere_login` hasta que un barrido
--     con sesion devuelva avisos.
--
-- SQLite no permite cambiar un CHECK con ALTER TABLE: hay que recrear la
-- tabla. La receta oficial (https://sqlite.org/lang_altertable.html#otheralter)
-- es: crear la tabla nueva, copiar los datos, borrar la vieja y renombrar
-- la nueva. Para eso hace falta apagar las claves foraneas (`PRAGMA
-- foreign_keys`), que SQLite NO deja cambiar con una transaccion abierta:
-- por eso esta migracion gestiona su propia transaccion (marcador
-- `jobpulse:transaccion-propia`).
PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

-- ------------------------------------------------------------------ sitios
CREATE TABLE source_sites_new (
    site_id TEXT PRIMARY KEY,
    platform_id TEXT NOT NULL REFERENCES source_platforms(platform_id),
    site_name TEXT NOT NULL,
    company_name TEXT,
    base_url TEXT NOT NULL,
    country TEXT,
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    run_groups_json TEXT NOT NULL DEFAULT '[]',
    site_config_json TEXT NOT NULL DEFAULT '{}',
    health_status TEXT NOT NULL DEFAULT 'unknown'
        CHECK (health_status IN (
            'unknown', 'healthy', 'zero_results', 'needs_review', 'error',
            'unsupported', 'requiere_login'
        )),
    consecutive_zero_runs INTEGER NOT NULL DEFAULT 0
        CHECK (consecutive_zero_runs >= 0),
    review_required INTEGER NOT NULL DEFAULT 0 CHECK (review_required IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO source_sites_new (
    site_id, platform_id, site_name, company_name, base_url, country,
    enabled, run_groups_json, site_config_json, health_status,
    consecutive_zero_runs, review_required, created_at, updated_at
)
SELECT
    site_id, platform_id, site_name, company_name, base_url, country,
    enabled, run_groups_json, site_config_json, health_status,
    consecutive_zero_runs, review_required, created_at, updated_at
FROM source_sites;

DROP TABLE source_sites;

ALTER TABLE source_sites_new RENAME TO source_sites;

CREATE INDEX idx_source_sites_enabled ON source_sites(enabled, platform_id);

-- ------------------------------------------- corrida del sitio (por sitio)
CREATE TABLE source_run_sites_new (
    run_id INTEGER NOT NULL REFERENCES source_runs(run_id) ON DELETE CASCADE,
    site_id TEXT NOT NULL REFERENCES source_sites(site_id),
    status TEXT NOT NULL DEFAULT 'running'
        CHECK (status IN (
            'running', 'ok', 'zero_results', 'error', 'skipped', 'unsupported',
            'requires_login'
        )),
    jobs_found INTEGER NOT NULL DEFAULT 0 CHECK (jobs_found >= 0),
    jobs_valid INTEGER NOT NULL DEFAULT 0 CHECK (jobs_valid >= 0),
    jobs_new INTEGER NOT NULL DEFAULT 0 CHECK (jobs_new >= 0),
    jobs_duplicate INTEGER NOT NULL DEFAULT 0 CHECK (jobs_duplicate >= 0),
    error_message TEXT,
    review_required INTEGER NOT NULL DEFAULT 0 CHECK (review_required IN (0, 1)),
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT,
    PRIMARY KEY (run_id, site_id)
);

INSERT INTO source_run_sites_new (
    run_id, site_id, status, jobs_found, jobs_valid, jobs_new, jobs_duplicate,
    error_message, review_required, started_at, finished_at
)
SELECT
    run_id, site_id, status, jobs_found, jobs_valid, jobs_new, jobs_duplicate,
    error_message, review_required, started_at, finished_at
FROM source_run_sites;

DROP TABLE source_run_sites;

ALTER TABLE source_run_sites_new RENAME TO source_run_sites;

CREATE INDEX idx_source_run_sites_site ON source_run_sites(site_id, run_id);

COMMIT;

PRAGMA foreign_keys = ON;
