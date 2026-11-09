-- 026_taxonomia_curacion_tanda_3.sql
-- CURACION DE LA TAXONOMIA, TANDA 3 (Ola 4.2 · tercera tanda).
--
-- MOTIVACION (objetivo del software): encontrar, entre TODOS los puestos, los
-- que tienen requisitos mas compatibles con la persona del CV. Para comparar
-- un requisito del aviso con un hecho del perfil, los dos tienen que hablar
-- el mismo idioma: la tabla `concepto` (variante de texto -> codigo
-- canonico). El motor SOLO compara los requisitos CON `codigo_canonico`
-- (`AND codigo_canonico IS NOT NULL`): los demas se IGNORAN en silencio y la
-- vacante parece mas compatible de lo que es.
--
-- DEMANDA (audit del corpus real, 2026-11-08, via
-- `taxonomia.demanda_corpus` sobre la corrida local `20261107_225916`):
-- la cola `concepto_no_normalizado` tiene 1198 variantes pendientes; 57 son
-- las que VARIOS avisos piden (>= 2 avisos reales) y por eso son esta tanda.
-- Las demas (1141 puestas por UN solo aviso) quedan para futuras tandas.
--
-- Que hace esta migracion (mismo patron que la 023 y la 025):
--   1. ALIAS de conceptos que YA existen: el aviso nombra la misma
--      competencia de otra forma o una subcategoria ("interpretacion de
--      planos" es lo mismo que "lectura de planos"; "sap basico" es SAP).
--   2. CONCEPTOS NUEVOS: herramientas, metodos, procesos y competencias
--      concretas que el corpus pide y no tenian ningun codigo (negociacion,
--      marketing automation, order to cash, cocteleria, preparacion de
--      alimentos...).
--
-- REGLAS que respeta (las mismas de la 021/023/025):
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
-- COMPETENCIA, una HERRAMIENTA, una NORMA, un PROCESO o un METODO concreto.
-- Se deja fuera lo que es una funcion, un sector, una palabra vacia o una
-- tarea.
--
-- VARIANTES QUE SE DEJAN EN LA COLA A PROPOSITO (9 de las 57) y por que:
--   * "website": canal o activo propio del empleador, no una competencia
--     comprobable (aparece como skill en avisos de atencion al cliente y en
--     uno de marketing digital: son contextos distintos).
--   * "data driven settings", "upgrades": ajustes o versiones del producto
--     del empleador; no nombran una competencia (mismo criterio que la 025).
--   * "four seasons": nombre de la EMPRESA (aparece en los skills de sus
--     propios avisos), no una competencia.
--   * "explore products", "providing product information": TAREAS del puesto,
--     no competencias (la misma razon que excluye `es_variante_encolable`).
--   * "buenas practicas": demasiado vaga; en los dos avisos que la piden
--     significa cosas distintas (practicas culinarias y practicas de
--     desarrollo).
--   * "asesor": el CARGO del puesto repetido como skill, no una competencia.
--   * "liviano": calificador ambiguo ("vehiculo liviano" en los dos avisos);
--     no dice que competencia se pide.

-- ---------------------------------------------------------------------------
-- 1. ALIAS DE CONCEPTOS QUE YA EXISTEN (25 variantes)
-- ---------------------------------------------------------------------------
INSERT OR IGNORE INTO concepto (codigo_canonico, categoria, variante, origen, tipo) VALUES
  -- --- lectura de planos: la misma competencia, nombrada de tres formas ---
  ('lectura-planos',        'skill', 'interpretacion de planos',   'ambos', 'existencia'),
  ('lectura-planos',        'skill', 'interpretacion de diagramas','ambos', 'existencia'),
  ('lectura-planos',        'skill', 'planos',                    'ambos', 'existencia'),
  ('lectura-planos',        'skill', 'drawings',                  'ambos', 'existencia'),
  -- --- diagnostico de fallas: la competencia generica de detectar y aislar ---
  ('troubleshooting',       'skill', 'diagnostico',               'ambos', 'existencia'),
  ('troubleshooting',       'skill', 'investigate technical problems', 'ambos', 'existencia'),
  ('troubleshooting',       'skill', 'network diagnostics',       'ambos', 'existencia'),
  -- --- finanzas ---
  ('analisis-negocio',      'skill', 'business analysis',         'ambos', 'existencia'),
  ('facturacion',           'skill', 'invoicing',                 'ambos', 'existencia'),
  ('cuentas-por-cobrar',    'skill', 'collections',               'ambos', 'existencia'),
  -- --- gestion: "supply chain" es la misma familia que "abastecimiento" ---
  ('abastecimiento',        'skill', 'supply chain',              'ambos', 'existencia'),
  ('project-planning',      'skill', 'timelines',                 'ambos', 'existencia'),
  ('reclutamiento',         'skill', 'seleccion',                 'ambos', 'existencia'),
  -- --- herramientas ya curadas ---
  ('sap',                   'skill', 'sap basico',                'ambos', 'existencia'),
  ('servidores',            'skill', 'iis',                       'ambos', 'existencia'),
  ('servidores',            'skill', 'web server technologies',   'ambos', 'existencia'),
  ('data-entry',            'skill', 'digitacion',                'ambos', 'existencia'),
  -- --- electromecanica ---
  ('electricidad',          'skill', 'destrezas electricas',      'ambos', 'existencia'),
  ('mecanica-industrial',   'skill', 'destrezas mecanicas',       'ambos', 'existencia'),
  -- --- alimentos: almacenamiento y conservacion son manejo de alimentos ---
  ('manipulacion-alimentos','skill', 'almacenamiento de alimentos','ambos', 'existencia'),
  ('manipulacion-alimentos','skill', 'conservacion de alimentos', 'ambos', 'existencia'),
  -- --- higiene e inocuidad: mismo dominio que la seguridad alimentaria ---
  ('seguridad-alimentaria', 'skill', 'protocolos de higiene',     'ambos', 'existencia'),
  -- --- atencion al cliente por telefono (canal, no competencia aparte) ---
  ('atencion-al-cliente',   'skill', 'phone',                     'ambos', 'existencia'),
  ('atencion-al-cliente',   'skill', 'phone calls',               'ambos', 'existencia'),
  ('atencion-al-cliente',   'skill', 'llamadas salientes outbound','ambos', 'existencia');

-- ---------------------------------------------------------------------------
-- 2. CONCEPTOS NUEVOS: herramientas, metodos, procesos y competencias (23)
-- ---------------------------------------------------------------------------
INSERT OR IGNORE INTO concepto (codigo_canonico, categoria, variante, origen, tipo) VALUES
  -- --- comercial y ventas ---
  ('negociacion',       'skill', 'negociacion',                'ambos', 'existencia'),
  ('cierre-ventas',     'skill', 'cierre de ventas',            'ambos', 'existencia'),
  -- --- marketing: familia de plataformas (Marketo, Eloqua...) ---
  ('marketing-automation','skill','marketing automation',       'ambos', 'existencia'),
  -- --- riesgos: evaluacion de riesgos (FMEA, riesgo de terceros, residual) ---
  ('evaluacion-riesgos','skill', 'risk assessments',            'ambos', 'existencia'),
  -- --- finanzas: proceso order-to-cash (facturacion-cobro-caja) ---
  ('order-to-cash',     'skill', 'order to cash',               'ambos', 'existencia'),
  -- --- infraestructura: orquestacion de contenedores (Docker, k8s...) ---
  ('containerization',  'skill', 'containerization technologies','ambos', 'existencia'),
  -- --- normativa clinica: ICH (junto a FDA y GCP) ---
  ('ich',               'skill', 'ich',                         'ambos', 'existencia'),
  -- --- hoteleria: PMS OnQ y el proceso de reservacion ---
  ('onq',               'skill', 'onq',                         'ambos', 'existencia'),
  ('reservaciones',     'skill', 'procesos de reservaciones',   'ambos', 'existencia'),
  -- --- gastronomia: cocteleria, preparacion en frio, coccion y montaje ---
  ('cocteleria',        'skill', 'cocteleria',                  'ambos', 'existencia'),
  ('cocteleria',        'skill', 'tecnicas de mixologia',       'ambos', 'existencia'),
  ('preparacion-alimentos','skill','tecnicas culinarias basicas','ambos', 'existencia'),
  ('preparacion-alimentos','skill','cortes',                    'ambos', 'existencia'),
  ('preparacion-alimentos','skill','ensaladas',                 'ambos', 'existencia'),
  ('preparacion-alimentos','skill','guarniciones',              'ambos', 'existencia'),
  ('tecnicas-coccion',  'skill', 'tecnicas de coccion',         'ambos', 'existencia'),
  ('tecnicas-montaje',  'skill', 'tecnicas de montaje',         'ambos', 'existencia'),
  -- --- vehiculos: manejo de motocicleta y exigencia de vehiculo propio ---
  ('moto',              'skill', 'moto',                        'ambos', 'existencia'),
  ('vehiculo-propio',   'skill', 'vehiculo propio',             'ambos', 'existencia'),
  -- --- ventanas y fachadas de aluminio (ventanas, interpretacion de planos) ---
  ('ventaneria',        'skill', 'sistemas de ventaneria',      'ambos', 'existencia'),
  -- --- instalacion de seguridad electronica: alarma, panel y tarjeta ---
  ('alarma',            'skill', 'alarma',                      'ambos', 'existencia'),
  ('paneles-control',   'skill', 'paneles',                     'ambos', 'existencia'),
  ('tarjetas-acceso',   'skill', 'tarjetas',                    'ambos', 'existencia');
