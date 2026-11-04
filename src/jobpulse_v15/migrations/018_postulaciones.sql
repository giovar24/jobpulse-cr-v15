-- 018_postulaciones.sql
-- Señales de POSTULACIÓN del usuario: estado del PROCESO, NO de aptitud.
--
-- REGLA DE DISEÑO (acordada 2026-11-04): **ser rechazado NO significa que
-- el perfil no califique para el puesto**. El reclutador humano decide por
-- presupuesto, timing, competencia, sesgos y azar. Por eso estas tablas
-- guardan el historial del PROCESO para uso operativo:
--   1. no reprocesar lo ya postulado;
--   2. medir el funnel propio ("de los que postule, cuantos llegaron a
--      entrevista"), con la advertencia de ruido humano;
--   3. revisar posibles falsos positivos del ranking (1 señal, no prueba).
-- NUNCA se usan para reentrenar el score de ajuste técnico.
--
-- PRIVACIDAD: del correo solo se guardan DERIVADOS MÍNIMOS (estado, fecha,
-- remitente, asunto, referencia del aviso). NUNCA el cuerpo del mensaje.

-- ---------------------------------------------------------------------------
-- 1. Bitácora de señales (un renglón por notificación detectada)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS postulacion_senal (
    senal_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id        TEXT REFERENCES jobs(job_id) ON DELETE SET NULL,
    portal        TEXT NOT NULL DEFAULT 'otro',
    source_job_id TEXT NOT NULL DEFAULT '',
    source_url    TEXT NOT NULL DEFAULT '',
    estado        TEXT NOT NULL CHECK (estado IN (
                      'applied', 'recruiter_contact', 'interview', 'offer',
                      'rejected', 'withdrawn'
                  )),
    fecha         TEXT NOT NULL DEFAULT '',
    remitente     TEXT NOT NULL DEFAULT '',
    asunto        TEXT NOT NULL DEFAULT '',
    titulo        TEXT NOT NULL DEFAULT '',
    empresa       TEXT NOT NULL DEFAULT '',
    detectado_en  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (portal, source_job_id, estado, fecha, remitente, asunto)
);

CREATE INDEX IF NOT EXISTS idx_postulacion_senal_job
    ON postulacion_senal(job_id);
CREATE INDEX IF NOT EXISTS idx_postulacion_senal_fecha
    ON postulacion_senal(fecha DESC);
CREATE INDEX IF NOT EXISTS idx_postulacion_senal_ref
    ON postulacion_senal(portal, source_job_id);

-- ---------------------------------------------------------------------------
-- 2. Estado ACTUAL por vacante (derivado de la bitácora)
--    El avance NUNCA se degrada: un 'interview' posterior no vuelve a
--    'rejected' (ver postulaciones.estado_mas_avanzado).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS postulacion (
    job_id        TEXT PRIMARY KEY REFERENCES jobs(job_id) ON DELETE CASCADE,
    estado        TEXT NOT NULL CHECK (estado IN (
                      'applied', 'recruiter_contact', 'interview', 'offer',
                      'rejected', 'withdrawn'
                  )),
    portal        TEXT NOT NULL DEFAULT '',
    ultima_fecha  TEXT NOT NULL DEFAULT '',
    actualizado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_postulacion_estado ON postulacion(estado);
