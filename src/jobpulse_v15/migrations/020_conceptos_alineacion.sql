-- 020_conceptos_alineacion.sql
-- Conceptos que faltaban para ALINEAR bien los requisitos con el perfil.
--
-- MOTIVACION (objetivo del software): encontrar, entre todos los puestos,
-- los que tienen requisitos mas compatibles con la persona del CV. Para eso
-- cada requisito del aviso tiene que poder COMPARARSE con el perfil, y el
-- motor (matching) SOLO compara los requisitos con `codigo_canonico`
-- (`AND codigo_canonico IS NOT NULL`): los que no lo tienen se IGNORAN en
-- silencio.
--
-- AUDIT del corpus real (2026-11-04, 1071 requisitos vigentes):
--   * 993 con codigo (92.7%) -> comparables
--   * 78 SIN codigo (7.3%)  -> IGNORADOS por el motor:
--       - 49 skills: six_sigma (12), tableau (11), java (8), c# (5),
--         c++ (5), typescript (4), autocad (3), solidworks (1)
--       - 29 licenses: 25 "Driver's license" sin clase + b3 (3) + a2 (1)
--
-- Con estos conceptos, esas 49 skills dejan de ser invisibles: los avisos
-- que piden Java o Tableau ya se evaluan CON ese requisito (antes se
-- evaluaban sin el, y por eso parecian mas compatibles de lo que son).
--
-- Las licencias siguen el criterio de EXISTENCIA (tipo='existencia', como las
-- que ya habia): la comparacion es "el perfil tiene licencia de conducir".
-- Las clases de Costa Rica que faltaban (a2, b3, c2, d1-d3, e1-e2, f1) se
-- mapean al mismo codigo, y se agregan las variantes genericas en ingles y
-- espanol para las licencias sin clase ("licencia de conducir al dia").
--
-- Idempotente: solo agrega filas que faltan (PRIMARY KEY (categoria,variante)).

INSERT OR IGNORE INTO concepto (codigo_canonico, categoria, variante, origen, tipo) VALUES
  -- --- skills que el corpus pide y la taxonomia no tenia ---
  ('java',            'skill', 'java',              'ambos', 'existencia'),
  ('java',            'skill', 'java 8',            'ambos', 'existencia'),
  ('java',            'skill', 'java se',           'ambos', 'existencia'),
  ('java',            'skill', 'core java',         'ambos', 'existencia'),
  ('tableau',         'skill', 'tableau',           'ambos', 'existencia'),
  ('tableau',         'skill', 'tableau desktop',   'ambos', 'existencia'),
  ('tableau',         'skill', 'tableau server',    'ambos', 'existencia'),
  ('tableau',         'skill', 'tableau prep',      'ambos', 'existencia'),
  ('six_sigma',       'skill', 'six sigma',         'ambos', 'existencia'),
  ('six_sigma',       'skill', 'six_sigma',         'ambos', 'existencia'),
  ('six_sigma',       'skill', 'sixsigma',          'ambos', 'existencia'),
  ('six_sigma',       'skill', 'lean six sigma',    'ambos', 'existencia'),
  ('c++',             'skill', 'c++',               'ambos', 'existencia'),
  ('c++',             'skill', 'c plus plus',       'ambos', 'existencia'),
  ('c++',             'skill', 'cplusplus',         'ambos', 'existencia'),
  ('c#',              'skill', 'c#',                'ambos', 'existencia'),
  ('c#',              'skill', 'c sharp',           'ambos', 'existencia'),
  ('c#',              'skill', 'csharp',            'ambos', 'existencia'),
  ('typescript',      'skill', 'typescript',        'ambos', 'existencia'),
  ('autocad',         'skill', 'autocad',           'ambos', 'existencia'),
  ('autocad',         'skill', 'auto cad',          'ambos', 'existencia'),
  ('solidworks',      'skill', 'solidworks',        'ambos', 'existencia'),
  ('solidworks',      'skill', 'solid works',       'ambos', 'existencia'),
  -- --- licencias de conducir: clases de Costa Rica que faltaban ---
  ('licencia-conducir', 'license', 'a2',             'ambos', 'existencia'),
  ('licencia-conducir', 'license', 'b3',             'ambos', 'existencia'),
  ('licencia-conducir', 'license', 'c2',             'ambos', 'existencia'),
  ('licencia-conducir', 'license', 'd1',             'ambos', 'existencia'),
  ('licencia-conducir', 'license', 'd2',             'ambos', 'existencia'),
  ('licencia-conducir', 'license', 'd3',             'ambos', 'existencia'),
  ('licencia-conducir', 'license', 'e1',             'ambos', 'existencia'),
  ('licencia-conducir', 'license', 'e2',             'ambos', 'existencia'),
  ('licencia-conducir', 'license', 'f1',             'ambos', 'existencia'),
  -- --- licencias genericas (sin clase): "licencia de conducir al dia" ---
  ('licencia-conducir', 'license', "driver's license", 'ambos', 'existencia'),
  ('licencia-conducir', 'license', 'driver license',   'ambos', 'existencia'),
  ('licencia-conducir', 'license', 'driving license',  'ambos', 'existencia'),
  ('licencia-conducir', 'license', 'licencia de conducir',   'ambos', 'existencia'),
  ('licencia-conducir', 'license', 'licencia para conducir', 'ambos', 'existencia'),
  ('licencia-conducir', 'license', 'licencia conducir',      'ambos', 'existencia');
