-- 027_job_match_decision.sql
-- DECISIONES FIRMADAS DEL PASO 5 (Paso 7 · "tabla de decisiones").
--
-- MOTIVACION (objetivo del software): el motor NO puede decidir, por si solo,
-- si un requisito educativouniversitario bloquea o no. La regla es
-- deliberadamente conservadora: "descartada" solo si el TEXTO confirma el
-- titulo obligatorio SIN negacion y SIN alternativa. Cuando el texto ofrece
-- una via alternativa ("or equivalent experience"), el motor deja el caso en
-- `revisar_a_mano / educacion_no_confirmada` y espera un VEREDICTO HUMANO.
--
-- El veredicto lo firma una SEGUNDA persona (la revision previa la hizo el
-- autor de la regla -> se descarta por sesgo). Hasta ahora esa firma vivia
-- solo en un documento de texto: el motor no la podia leer, asi que los casos
-- firmados seguian contando como "pendientes" para siempre.
--
-- Que guarda cada fila (una decision por (aviso, dimension, texto revisado)):
--
--   job_id      aviso al que aplica la decision (FK a jobs).
--   dimension   dimension del matching ('educacion' es la unica abierta hoy;
--               la tabla admite mas para el futuro).
--   veredicto   'bloqueo_real' | 'no_bloqueo' | 'dudoso'.
--   criterio    POR QUE sefirmo ese veredicto (texto de la segunda persona).
--   revisor     quien firmo.
--   fecha       fecha de la firma (ISO).
--   text_hash   sha256 del TEXTO del aviso en el momento de la firma. Si el
--               texto cambia (el aviso se re-scrapea), la decision deja de
--               aplicar: el caso vuelve a `educacion_no_confirmada` y hay que
--               volver a firmarlo. Esto evita que una firma vieja se aplique
--               a un texto que nadie reviso.
--   corrida_id  corrida de `job_match` en la que se registro la decision
--               (trazabilidad: que corrida la consumio).
--
-- REGLAS que respeta:
--   * Solo anade una tabla: NO toca `job_match`, `job_analysis` ni los
--     umbrales del motor. El cambio de estados lo produce una CORRIDA NUEVA
--     del Paso 5, nunca un UPDATE de la anterior.
--   * `UNIQUE (job_id, dimension, text_hash)`: firmar dos veces el MISMO
--     texto es un UPDATE (la segunda firma manda); un texto distinto es una
--     fila nueva (historico).
--   * FK a `jobs` con ON DELETE CASCADE: si se purga el aviso, su decision
--     se purga con el (no queda una decision huerfana).
--   * Sin claves foraneas a `job_match`: `corrida_id` es un id logico de
--     corrida (se invalida al correr de nuevo), no una fila viva.

CREATE TABLE IF NOT EXISTS job_match_decision (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id      TEXT    NOT NULL,
  dimension   TEXT    NOT NULL CHECK (dimension IN ('educacion')),
  veredicto   TEXT    NOT NULL CHECK (veredicto IN (
                'bloqueo_real', 'no_bloqueo', 'dudoso'
              )),
  criterio    TEXT    NOT NULL,
  revisor     TEXT    NOT NULL,
  fecha       TEXT    NOT NULL,
  text_hash   TEXT    NOT NULL,
  corrida_id  TEXT,
  FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE,
  UNIQUE (job_id, dimension, text_hash)
);

CREATE INDEX IF NOT EXISTS idx_job_match_decision_job
  ON job_match_decision (job_id, dimension);

-- ---------------------------------------------------------------
-- Fin de la migracion 027
-- ---------------------------------------------------------------
