-- 017_educacion_granular.sql
-- Granularidad del nivel educativo (la que faltaba desde la 009).
--
-- La 009 solo traia 4 codigos canonicos (secundaria / tecnico /
-- universitaria / posgrado). Con la escalera de `matching` (1=secundaria,
-- 2=superior de ciclo corto, 3=universitario, 4=posgrado) faltaban las
-- VARIANTES de texto mas usadas en los avisos, que se quedaban sin codigo
-- (y el Paso 5 las descarta: `codigo_canonico IS NOT NULL`).
--
-- Decisiones (coherentes con la regla dura del texto, AGENTS.md):
--   * master / MBA / postgraduate / doctorate -> posgrado (4);
--   * associate degree / two-year college degree / technical degree /
--     tecnico superior -> superior de ciclo corto (2);
--   * "bachiller" a secas -> secundaria (1) en CR: NO es universitario
--     (el "bachillerato universitario" SI lo es y lo decide el TEXTO).
--
-- Idempotente: solo agrega filas que faltan.

INSERT OR IGNORE INTO concepto (codigo_canonico, categoria, variante, origen, nivel_orden) VALUES
  -- --- 4: posgrado ---
  ('educacion-posgrado',      'education', 'master',                  'ambos', 4),
  ('educacion-posgrado',      'education', 'master degree',           'ambos', 4),
  ('educacion-posgrado',      'education', "master's degree",         'ambos', 4),
  ('educacion-posgrado',      'education', 'masters degree',          'ambos', 4),
  ('educacion-posgrado',      'education', 'mba',                     'ambos', 4),
  ('educacion-posgrado',      'education', 'mba degree',              'ambos', 4),
  ('educacion-posgrado',      'education', 'postgraduate degree',     'ambos', 4),
  ('educacion-posgrado',      'education', 'postgraduate',            'ambos', 4),
  ('educacion-posgrado',      'education', 'doctorate',               'ambos', 4),
  ('educacion-posgrado',      'education', 'phd',                     'ambos', 4),
  -- --- 2: superior de ciclo corto ---
  ('educacion-tecnica',       'education', 'associate degree',        'ambos', 2),
  ('educacion-tecnica',       'education', "associate's degree",      'ambos', 2),
  ('educacion-tecnica',       'education', 'associate',               'ambos', 2),
  ('educacion-tecnica',       'education', 'technical degree',        'ambos', 2),
  ('educacion-tecnica',       'education', 'tecnico superior',        'ambos', 2),
  ('educacion-tecnica',       'education', 'postsecondary certificate','ambos', 2),
  ('educacion-tecnica',       'education', 'community college degree','ambos', 2),
  ('educacion-tecnica',       'education', 'two year college degree', 'ambos', 2),
  ('educacion-tecnica',       'education', 'diplomado',               'ambos', 2),
  ('educacion-tecnica',       'education', 'diplomado tecnico',       'ambos', 2),
  -- --- 1: secundaria ---
  ('educacion-secundaria',    'education', 'bachiller',               'ambos', 1),
  ('educacion-secundaria',    'education', 'educacion media',         'ambos', 1),
  ('educacion-secundaria',    'education', 'secondary education',     'ambos', 1);

-- La escalera de niveles (nivel_escala) queda alineada con los codigos
-- canonicos que usa el motor.
INSERT OR IGNORE INTO nivel_escala (categoria, codigo, orden) VALUES
  ('education', 'secundaria',    1),
  ('education', 'tecnico',       2),
  ('education', 'universitaria', 3),
  ('education', 'posgrado',      4);
