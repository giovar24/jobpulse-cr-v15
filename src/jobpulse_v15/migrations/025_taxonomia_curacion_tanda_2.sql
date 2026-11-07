-- 025_taxonomia_curacion_tanda_2.sql
-- CURACION DE LA TAXONOMIA, TANDA 2 (Ola 4.2 · segunda tanda).
--
-- MOTIVACION (objetivo del software): encontrar, entre TODOS los puestos, los
-- que tienen requisitos mas compatibles con la persona del CV. Para comparar
-- un requisito del aviso con un hecho del perfil, los dos tienen que hablar
-- el mismo idioma: la tabla `concepto` (variante de texto -> codigo
-- canonico). El motor SOLO compara los requisitos CON `codigo_canonico`
-- (`AND codigo_canonico IS NOT NULL`): los demas se IGNORAN en silencio.
--
-- DEMANDA (audit del corpus real, 2026-11-07, via
-- `taxonomia.demanda_corpus`): la cola `concepto_no_normalizado` tiene 1225
-- variantes pendientes; 28 son las que VARIOS avisos piden (>= 2 avisos) y
-- por eso son esta tanda. Las demas (1197 puestas por UN solo aviso) quedan
-- para futuras tandas.
--
-- Que hace esta migracion (mismo patron que la 023):
--   1. ALIAS de conceptos que YA existen: el aviso nombra la misma
--      competencia de otra forma o una subcategoria ("power brakes" es una
--      maquina-herramienta de la MISMA lista que ya cubrio la 023:
--      "small lathes, power mills, extruding machines, drills or punch
--      presses, power brakes, shears or saws").
--   2. CONCEPTOS NUEVOS: herramientas, metodos y competencias concretas que
--      el corpus pide y no tenian ningun codigo (TUV, macOS, servidores,
--      sistemas operativos, validacion, variance analysis...).
--
-- REGLAS que respeta (las mismas de la 021/023):
--   * Solo variantes en minusculas, sin acentos y con espacios simples: el
--     resolver de `conceptos` compara `LOWER(TRIM(value_code))` y el modulo
--     `skills_fuente` normaliza igual.
--   * Las variantes NO son codigos: el codigo canonico agrupa las sinonimas.
--   * Idempotente: solo agrega filas que faltan (PRIMARY KEY
--     (categoria, variante)).
--   * NO toca la cola `concepto_no_normalizado` (la reconstruye
--     `jobpulse-v15 taxonomy curate --apply` desde el corpus).
--
-- Criterio de curacion (igual que la 023): solo entra lo que nombra una
-- COMPETENCIA, una HERRAMIENTA, una NORMA o un METODO concreto. Se deja
-- fuera lo que es una funcion, un sector, una palabra vacia o una tarea.
--
-- VARIANTES QUE SE DEJAN EN LA COLA A PROPOSITO (9 de las 28) y por que:
--   * "espanol c1", "ingles c1", "english target language": FANTASMA de
--     `taxonomia.demanda_corpus` (lee `jobs.skills` crudos). El extractor NO
--     crea requisitos skill con esos textos (verificado 2026-11-07: 0 filas
--     en `job_requirements` con category='skill' y value_code tipo '%c1%');
--     ya los convierte en requisito de IDIOMA con su nivel
--     (ej. ane-121813 -> language 'es' qualifier 'c1' codigo 'espanol').
--     Curarlos aqui como skills seria incorrecto: `cumple_skill` solo mira
--     hechos del perfil categoria 'skill' y el perfil registra 'espanol'
--     como IDIOMA -> un falso "faltante". El arreglo correcto es de codigo
--     (demanda_corpus), no de datos.
--   * "data driven settings", "external services", "upgrades", "website":
--     vagas o propias del producto del empleador; no nombran una competencia
--     comprobable.
--   * "four seasons": nombre de la EMPRESA (aparece en los skills de sus
--     propios avisos), no una competencia.
--   * "providing product information": tarea del puesto, no competencia
--     (la misma razon que excluye `es_variante_encolable`).

-- ---------------------------------------------------------------------------
-- 1. ALIAS DE CONCEPTOS QUE YA EXISTEN
-- ---------------------------------------------------------------------------
INSERT OR IGNORE INTO concepto (codigo_canonico, categoria, variante, origen, tipo) VALUES
  -- --- manufactura: maquinas-herramienta (misma lista que ya curo la 023) ---
  ('tooling-especializado', 'skill', 'power brakes',            'ambos', 'existencia'),
  -- --- desarrollo web: la variante nombra los dos, el codigo es uno ---
  ('html',                  'skill', 'html css',                'ambos', 'existencia'),
  -- --- calidad: NC/CAPAs (non-conformances + corrective & preventive actions) ---
  ('acciones-correctivas',  'skill', 'nc capas',                'ambos', 'existencia'),
  -- --- gestion de servicios / cadena de suministro ---
  ('operational-support',   'skill', 'service operations',      'ambos', 'existencia'),
  ('abastecimiento',        'skill', 'supply chain engineering','ambos', 'existencia'),
  -- --- informes (el aviso pide informe de ventas = reporting) ---
  ('reporting',             'skill', 'informe de ventas',       'ambos', 'existencia'),
  -- --- alimentos: subcategorias de la competencia umbrella (igual que
  --     'windows 10' -> windows en la 023) ---
  ('manipulacion-alimentos','skill', 'almacenamiento al vacio',  'ambos', 'existencia'),
  ('manipulacion-alimentos','skill', 'preliminado de alimentos', 'ambos', 'existencia');

-- ---------------------------------------------------------------------------
-- 2. CONCEPTOS NUEVOS: herramientas, metodos y competencias que el corpus pide
-- ---------------------------------------------------------------------------
INSERT OR IGNORE INTO concepto (codigo_canonico, categoria, variante, origen, tipo) VALUES
  -- --- normativa: cuerpo normativo junto a FDA ("FDA, TUV, etc.") ---
  ('tuv',                'skill', 'tuv',                       'ambos', 'existencia'),
  -- --- comercial B2B ---
  ('b2b',                'skill', 'b2b sales',                 'ambos', 'existencia'),
  -- --- sistemas operativos (el corpus pide el conjunto y los avisos
  --     concretos ya tenian windows/linux) ---
  ('macos',              'skill', 'macos',                     'ambos', 'existencia'),
  ('sistemas-operativos','skill', 'sistemas operativos',        'ambos', 'existencia'),
  -- --- lenguaje de programacion R (analytics HPE, administracion Coopecaja) ---
  ('r',                  'skill', 'r',                         'ambos', 'existencia'),
  -- --- infraestructura ---
  ('servidores',         'skill', 'servers',                   'ambos', 'existencia'),
  ('servidores',         'skill', 'servidores',                'ambos', 'existencia'),
  -- --- competencias de gestion (la 023 ya creo 'liderazgo' con el mismo
  --     criterio de competencia blanda pedida por el corpus) ---
  ('organizacion',       'skill', 'organizacion',              'ambos', 'existencia'),
  ('comunicacion',       'skill', 'comunicacion',              'ambos', 'existencia'),
  ('comunicacion',       'skill', 'listening skills',          'ambos', 'existencia'),
  -- --- validacion (ES/EN: mismas familias de avisos; 'data validation'
  --     sigue en su codigo 'data-validation', no se re-apunta) ---
  ('validacion',         'skill', 'validacion',                'ambos', 'existencia'),
  ('validacion',         'skill', 'validation',                'ambos', 'existencia'),
  -- --- metodo contable: analisis de varianzas (Aptiv, Cardinal Health) ---
  ('variance-analysis',  'skill', 'variance analysis',          'ambos', 'existencia');
