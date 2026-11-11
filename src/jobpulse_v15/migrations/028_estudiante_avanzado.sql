-- 028_estudiante_avanzado.sql
-- ESCALON "ESTUDIANTE AVANZADO" EN LA ESCALERA EDUCATIVA.
--
-- MOTIVACION (regla de negocio 2026-11-08, ver
-- `docs/REGLAS_NEGOCIO_EDUCACION.md`): la escalera firmada es
--
--   posgrado > titulo universitario > estudiante sin graduar con 80 %+ de
--   los creditos > diploma tecnico > bachillerato de secundaria
--
-- pero el motor solo tenia CUATRO escalones (1 secundaria, 2 ciclo corto,
-- 3 universitario, 4 posgrado). Consecuencia (R2): un hecho educativo
-- `education_status='pursuing'` contaba como titulo universitario COMPLETO,
-- contra la regla: un estudiante avanzado NO es un titulado.
--
-- Este cambio inserta el escalon intermedio y CORRE los dos superiores:
--
--   1 secundaria
--   2 superior de ciclo corto (tecnico)
--   3 estudiante avanzado        <-- NUEVO
--   4 titulo universitario
--   5 posgrado
--
-- Se aplica a `nivel_escala` (documentacion de la escalera) y a
-- `concepto.nivel_orden` (lo que lee el motor en `nivel_concepto`).
--
-- REGLAS que respeta:
--   * Es una MIGRACION DE DATOS: nunca se hace UPDATE a mano.
--   * No toca `job_match`: los estados solo cambian con una CORRIDA NUEVA
--     del Paso 5. La medicion obligatoria en copia debe dar CERO cambios de
--     banda/estado en el corpus (el perfil real no tiene hechos `pursuing`).
--   * Se aplica UNA sola vez (la secuencia la guarda `PRAGMA user_version`),
--     por eso el corrimiento es un `+1` y no un upsert idempotente.
--   * Los `nivel_orden` NULL (variantes de CV sin nivel) se dejan como estan:
--     `nivel_concepto` toma `MAX(nivel_orden)` por codigo canonico.

-- 1. Escalera de referencia: posgrado y universitario suben un lugar.
UPDATE nivel_escala
   SET orden = 5
 WHERE categoria = 'education' AND codigo = 'posgrado';

UPDATE nivel_escala
   SET orden = 4
 WHERE categoria = 'education' AND codigo = 'universitaria';

INSERT OR IGNORE INTO nivel_escala (categoria, codigo, orden) VALUES
  ('education', 'estudiante_avanzado', 3);

-- 2. Niveles de los conceptos: todo lo que era 3 (universitario) o 4
--    (posgrado) sube un escalon. Secundaria (1) y ciclo corto (2) no cambian.
UPDATE concepto
   SET nivel_orden = nivel_orden + 1
 WHERE categoria = 'education' AND nivel_orden >= 3;

-- ---------------------------------------------------------------
-- Fin de la migracion 028
-- ---------------------------------------------------------------
