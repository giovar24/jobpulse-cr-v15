-- 024_pipeline_etapa.sql
-- METRICAS POR ETAPA DEL PIPELINE (Ola 4.3).
--
-- MOTIVACION (objetivo del software): auditar POR QUE una corrida "dio menos".
-- El pipeline encadena siete etapas (scrape -> analisis -> ia -> reanalisis ->
-- backfill -> paso5 -> evidencia). Cada una devuelve contadores propios y en
-- formatos distintos, asi que al terminar no se puede responder a la pregunta
-- que de verdad importa: "de TODOS los avisos que entraron, cuantos llegaron
-- al Paso 5, cuantos tenian requisitos, y en que etapa se perdieron".
--
-- Un caso REAL (2026-11-06, Ola 4.2): 705 avisos entraron al analisis, pero
-- 9 acabaron en `sin_requisitos` y 58 cambiaron de estado porque sus
-- requisitos (skills de ANE) no tenian codigo canonico. Sin este registro, ese
-- hueco solo se descubria mirando los estados finales.
--
-- Que guarda cada fila (una por ETAPA y por EJECUCION del pipeline):
--
--   corrida_id     id de la EJECUCION del pipeline (`pipe_<timestamp>`).
--                  Agrupa las etapas de una misma corrida. NO es el
--                  `corrida_id` de `job_match` (el del Paso 5): ese se guarda
--                  en el detalle de la etapa `paso5` (`corrida_paso5`).
--   etapa          nombre de la etapa (scrape|analisis|ia|reanalisis|
--                  backfill|paso5|evidencia).
--   ok             1 si la etapa termino sin error, 0 si fallo.
--   duracion_ms    duracion en milisegundos.
--   avisos         avisos que la etapa proceso (encontrados, analizados,
--                  enriquecidos, re-analizados, evaluados, documentados).
--   requisitos     requisitos que la etapa produjo o evaluo.
--   errores        fallos de la etapa.
--   detalle_json   contadores ESPECIFICOS de la etapa (por_estado,
--                  por_motivo, campos rellenados por la IA, etc.).
--   iniciado_en    marca de tiempo ISO del inicio de la etapa.
--   terminado_en   marca de tiempo ISO del final de la etapa.
--
-- REGLAS que respeta:
--   * No borra ni funde datos: SOLO anade filas (es instrumentacion).
--   * No toca `job_match`, `job_analysis` ni los umbrales del motor: es una
--     tabla de auditoria, no un dato del matching.
--   * Sin claves foraneas a propósito: `corrida_id` es un id logico de la
--     ejecucion del pipeline (no hay tabla de corridas del pipeline), y meter
--     una FK obligaria a crear esa tabla y a borrarla en cada purga.
--   * Los indices ayudan a las consultas de auditoria: por corrida (el caso
--     normal: "ver las etapas de esta corrida") y por etapa (el caso de
--     comparacion: "cuanto tardo la IA estas ultimas veces").

CREATE TABLE IF NOT EXISTS pipeline_etapa (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  corrida_id    TEXT    NOT NULL,
  etapa         TEXT    NOT NULL,
  ok            INTEGER NOT NULL CHECK (ok IN (0,1)),
  duracion_ms   INTEGER NOT NULL CHECK (duracion_ms >= 0),
  avisos        INTEGER NOT NULL DEFAULT 0 CHECK (avisos >= 0),
  requisitos    INTEGER NOT NULL DEFAULT 0 CHECK (requisitos >= 0),
  errores       INTEGER NOT NULL DEFAULT 0 CHECK (errores >= 0),
  detalle_json  TEXT,
  iniciado_en   TEXT    NOT NULL,
  terminado_en  TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pipeline_etapa_corrida
  ON pipeline_etapa (corrida_id, id);

CREATE INDEX IF NOT EXISTS idx_pipeline_etapa_etapa
  ON pipeline_etapa (etapa, id);

-- ---------------------------------------------------------------
-- Fin de la migracion 024
-- ---------------------------------------------------------------
