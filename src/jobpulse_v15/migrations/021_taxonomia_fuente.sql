-- 021_taxonomia_fuente.sql
-- Taxonomia que crece con los CAMPOS ESTRUCTURADOS de los avisos
-- (`jobs.skills` y `jobs.languages`).
--
-- MOTIVACION (objetivo del software): encontrar, entre TODOS los puestos, los
-- que tienen requisitos mas compatibles con la persona del CV. Para comparar
-- un requisito del aviso con un hecho del perfil, los dos tienen que hablar
-- el mismo idioma: la tabla `concepto` (variante de texto -> codigo
-- canonico). El motor SOLO compara los requisitos CON `codigo_canonico`
-- (`AND codigo_canonico IS NOT NULL`): los demas se IGNORAN en silencio.
--
-- AUDIT del corpus real (2026-11-04):
--   * 535 avisos, 461 con `jobs.skills` informado (1776 skills distintas
--     utiles, 2438 menciones) y 511 con `jobs.languages`.
--   * Con la taxonomia de la 020 solo resolvian 45 de esas 2438 menciones:
--     el 98% de las skills de la fuente NO era comparable con el perfil.
--   * 135 avisos quedaban en la banda `sin_datos` del motor de viabilidad
--     (sin NINGUN requisito comparable): no se podia decir si el perfil
--     calificaba.
--
-- Que hace esta migracion:
--   1. Los IDIOMAS que faltaban (el corpus los pide y no tenian concepto:
--      un aviso que pide alemán era invisible para el motor).
--   2. ALIAS de los conceptos que ya existen: los avisos escriben la misma
--      competencia de otra forma ("Microsoft Office applications" es
--      microsoft-365; "consultas SQL" es sql).
--   3. Conceptos NUEVOS para las competencias, herramientas, normas y
--      metodos que el corpus pide mas veces (retail, manufactura, calidad,
--      contabilidad, finanzas, IT/soporte, RRHH).
--
-- Reglas que respeta:
--   * Solo variantes en minusculas, sin acentos y con espacios simples: el
--     resolver de `conceptos` compara `LOWER(TRIM(value_code))` y el modulo
--     `skills_fuente` normaliza igual (minusculas, sin acentos).
--   * Las variantes NO son codigos: el codigo canonico agrupa las sinonimas.
--   * Idempotente: solo agrega filas que faltan (PRIMARY KEY
--     (categoria, variante)).
--
-- La taxonomia sigue creciendo: lo que aun no esta aqui se encola en
-- `concepto_no_normalizado` (la cola que el extractor y el backfill llenan).
--
-- Criterio de curacion (2026-11-04, antes de aplicarse a la BD real): solo
-- entra lo que nombra una COMPETENCIA, una HERRAMIENTA, una NORMA o un
-- METODO concreto. Se deja fuera lo que es una funcion ("ventas"), un sector
-- ("construccion"), una palabra vacia ("analysis", "planning") o una tarea
-- ("despachar", "empacar"): contarlas como competencia penaliza a todos los
-- avisos por igual y esconde los gaps reales.

-- ---------------------------------------------------------------------------
-- 1. IDIOMAS QUE FALTABAN (el corpus los pide y no tenian concepto)
-- ---------------------------------------------------------------------------
INSERT OR IGNORE INTO concepto (codigo_canonico, categoria, variante, origen, tipo) VALUES
  ('aleman',      'language', 'aleman',      'ambos', 'existencia'),
  ('aleman',      'language', 'german',      'ambos', 'existencia'),
  ('aleman',      'language', 'de',          'ambos', 'existencia'),
  ('italiano',    'language', 'italiano',    'ambos', 'existencia'),
  ('italiano',    'language', 'italian',     'ambos', 'existencia'),
  ('italiano',    'language', 'it',          'ambos', 'existencia'),
  ('chino',       'language', 'chino',       'ambos', 'existencia'),
  ('chino',       'language', 'chinese',     'ambos', 'existencia'),
  ('chino',       'language', 'mandarin',    'ambos', 'existencia'),
  ('chino',       'language', 'simplified chinese', 'ambos', 'existencia'),
  ('chino',       'language', 'traditional chinese', 'ambos', 'existencia'),
  ('japones',     'language', 'japones',     'ambos', 'existencia'),
  ('japones',     'language', 'japanese',    'ambos', 'existencia'),
  ('coreano',     'language', 'coreano',     'ambos', 'existencia'),
  ('coreano',     'language', 'korean',      'ambos', 'existencia'),
  ('arabe',       'language', 'arabe',       'ambos', 'existencia'),
  ('arabe',       'language', 'arabic',      'ambos', 'existencia'),
  ('neerlandes',  'language', 'neerlandes',  'ambos', 'existencia'),
  ('neerlandes',  'language', 'dutch',       'ambos', 'existencia');

-- ---------------------------------------------------------------------------
-- 2. ALIAS DE LOS CONCEPTOS QUE YA EXISTIAN
--    (los avisos nombran la misma competencia de otra forma)
-- ---------------------------------------------------------------------------
INSERT OR IGNORE INTO concepto (codigo_canonico, categoria, variante, origen, tipo) VALUES
  -- microsoft-365 / office
  ('microsoft-365', 'skill', 'microsoft office',           'ambos', 'existencia'),
  ('microsoft-365', 'skill', 'microsoft office applications', 'ambos', 'existencia'),
  ('microsoft-365', 'skill', 'office applications',        'ambos', 'existencia'),
  ('microsoft-365', 'skill', 'microsoft 365 apps',        'ambos', 'existencia'),
  ('microsoft-365', 'skill', 'microsoft 365 applications', 'ambos', 'existencia'),
  -- excel
  ('excel', 'skill', 'microsoft excel applications', 'ambos', 'existencia'),
  ('excel', 'skill', 'excel intermedio',            'ambos', 'existencia'),
  ('excel', 'skill', 'excel avanzado',               'ambos', 'existencia'),
  ('excel', 'skill', 'microsoft excel avanzado',     'ambos', 'existencia'),
  -- sql
  ('sql', 'skill', 'consultas sql',                 'ambos', 'existencia'),
  ('sql', 'skill', 'sql queries',                   'ambos', 'existencia'),
  ('sql', 'skill', 'consultas y reportes sql',      'ambos', 'existencia'),
  ('sql', 'skill', 'mysql',                         'ambos', 'existencia'),
  ('sql', 'skill', 'postgres',                      'ambos', 'existencia'),
  ('sql', 'skill', 'postgresql',                    'ambos', 'existencia'),
  ('sql', 'skill', 'bases de datos',                'ambos', 'existencia'),
  -- service now
  ('servicenow', 'skill', 'service now',            'ambos', 'existencia'),
  ('servicenow', 'skill', 'servicenow now',         'ambos', 'existencia'),
  ('servicenow', 'skill', 'servicenow itsm',        'ambos', 'existencia'),
  -- active directory
  ('active-directory', 'skill', 'azure active directory',   'ambos', 'existencia'),
  ('active-directory', 'skill', 'microsoft active directory','ambos', 'existencia'),
  ('active-directory', 'skill', 'ad ds',                  'ambos', 'existencia'),
  -- linux / windows / redes
  ('linux',   'skill', 'red hat linux', 'ambos', 'existencia'),
  ('linux',   'skill', 'ubuntu',         'ambos', 'existencia'),
  ('linux',   'skill', 'linux server',   'ambos', 'existencia'),
  -- control de versiones
  ('git', 'skill', 'gitlab',          'ambos', 'existencia'),
  ('git', 'skill', 'bitbucket',       'ambos', 'existencia'),
  ('git', 'skill', 'version control', 'ambos', 'existencia'),
  -- nube
  ('aws',   'skill', 'amazon web services', 'ambos', 'existencia'),
  ('azure', 'skill', 'microsoft azure',       'ambos', 'existencia'),
  ('gcp',   'skill', 'google cloud',         'ambos', 'existencia'),
  ('gcp',   'skill', 'google cloud platform', 'ambos', 'existencia'),
  -- html / css
  ('html', 'skill', 'html5', 'ambos', 'existencia'),
  ('css',  'skill', 'css3',  'ambos', 'existencia'),
  -- seis sigma
  ('six_sigma', 'skill', 'dmaic',          'ambos', 'existencia'),
  ('six_sigma', 'skill', 'six sigma black belt', 'ambos', 'existencia'),
  ('six_sigma', 'skill', 'six sigma green belt', 'ambos', 'existencia'),
  -- office / herramientas de google
  ('google-workspace', 'skill', 'g suite',          'ambos', 'existencia'),
  ('google-workspace', 'skill', 'google apps',      'ambos', 'existencia'),
  ('google-workspace', 'skill', 'google workspace apps', 'ambos', 'existencia');

-- ---------------------------------------------------------------------------
-- 3. CONCEPTOS NUEVOS: lo que el corpus pide mas veces
-- ---------------------------------------------------------------------------

-- --- retail / supermercado / bodega -----------------------------------------
INSERT OR IGNORE INTO concepto (codigo_canonico, categoria, variante, origen, tipo) VALUES
  ('apertura-caja',      'skill', 'apertura de caja',        'ambos', 'existencia'),
  ('apertura-caja',      'skill', 'apertura de turno',       'ambos', 'existencia'),
  ('cierre-caja',        'skill', 'cierre de caja',          'ambos', 'existencia'),
  ('cobro',              'skill', 'cobro',                   'ambos', 'existencia'),
  ('transacciones-cobro','skill', 'transacciones de cobro',  'ambos', 'existencia'),
  ('frenteos',           'skill', 'frenteos',                'ambos', 'existencia'),
  ('frenteos',           'skill', 'efectuar frenteos',       'ambos', 'existencia'),
  ('facturacion',        'skill', 'facturacion',             'ambos', 'existencia'),
  ('cotizaciones',       'skill', 'cotizaciones',            'ambos', 'existencia'),
  ('ferreteria',         'skill', 'ferreteria',              'ambos', 'existencia'),
  ('ferreteria',         'skill', 'conocimientos en ferreteria',   'ambos', 'existencia'),
  ('ferreteria',         'skill', 'conocimientos en construccion', 'ambos', 'existencia'),
  ('abastecimiento',     'skill', 'abastecimiento',          'ambos', 'existencia'),
  ('inventarios',        'skill', 'manejo de inventarios',   'ambos', 'existencia'),
  ('inventarios',        'skill', 'manejo de inventario',    'ambos', 'existencia'),
  ('inventarios',        'skill', 'control de inventarios',  'ambos', 'existencia'),
  ('inventarios',        'skill', 'analisis de inventario',  'ambos', 'existencia'),
  ('acomodacion-mercaderia','skill', 'acomodacion de mercaderia', 'ambos', 'existencia');

-- --- manufactura / calidad / farma / alimentos ------------------------------
INSERT OR IGNORE INTO concepto (codigo_canonico, categoria, variante, origen, tipo) VALUES
  ('manufactura-procesos', 'skill', 'procesos de manufactura',   'ambos', 'existencia'),
  ('manufactura-procesos', 'skill', 'manufacturing processes',   'ambos', 'existencia'),
  ('gmp',                  'skill', 'gmp',                      'ambos', 'existencia'),
  ('gmp',                  'skill', 'gmp s',                    'ambos', 'existencia'),
  ('gdp',                  'skill', 'gdp',                      'ambos', 'existencia'),
  ('gdp',                  'skill', 'gdp s',                    'ambos', 'existencia'),
  ('iso-13485',            'skill', 'iso 13485',                'ambos', 'existencia'),
  ('fda',                  'skill', 'fda',                      'ambos', 'existencia'),
  ('medtech',              'skill', 'medtech',                  'ambos', 'existencia'),
  ('dispositivos-medicos', 'skill', 'medical device manufacturing', 'ambos', 'existencia'),
  ('dispositivos-medicos', 'skill', 'dispositivos medicos',     'ambos', 'existencia'),
  ('sala-limpia',          'skill', 'clean room',               'ambos', 'existencia'),
  ('sala-limpia',          'skill', 'salas limpias',            'ambos', 'existencia'),
  ('control-calidad',      'skill', 'quality control',          'ambos', 'existencia'),
  ('aseguramiento-calidad','skill', 'quality assurance',        'ambos', 'existencia'),
  ('aseguramiento-calidad','skill', 'qa',                       'ambos', 'existencia'),
  ('sistemas-calidad',     'skill', 'quality systems',          'ambos', 'existencia'),
  ('sops',                 'skill', 'sops',                     'ambos', 'existencia'),
  ('cnc',                  'skill', 'cnc',                      'ambos', 'existencia'),
  ('cnc',                  'skill', 'numerically controlled',   'ambos', 'existencia'),
  ('tooling-especializado','skill', 'specialized tooling',     'ambos', 'existencia'),
  ('microscopio',          'skill', 'microscope',               'ambos', 'existencia'),
  ('agujas',               'skill', 'needles',                  'ambos', 'existencia'),
  ('tijeras',              'skill', 'scissors',                 'ambos', 'existencia'),
  ('pinzas',               'skill', 'forceps',                  'ambos', 'existencia'),
  ('manipulacion-alimentos','skill', 'manipulacion de alimentos','ambos', 'existencia'),
  ('seguridad-alimentaria','skill', 'seguridad alimentaria',    'ambos', 'existencia'),
  ('reciclaje',            'skill', 'programa de reciclaje',    'ambos', 'existencia'),
  ('regulacion-normativa', 'skill', 'regulacion y normativa',   'ambos', 'existencia'),
  ('trazabilidad',         'skill', 'trazabilidad',             'ambos', 'existencia');

-- --- contabilidad / finanzas / auditoria -------------------------------------
INSERT OR IGNORE INTO concepto (codigo_canonico, categoria, variante, origen, tipo) VALUES
  ('asientos-contables',  'skill', 'journal entries',       'ambos', 'existencia'),
  ('revenue-recognition', 'skill', 'revenue recognition',   'ambos', 'existencia'),
  ('revenue-deferrals',   'skill', 'revenue deferrals',     'ambos', 'existencia'),
  ('libro-mayor',         'skill', 'general ledger',        'ambos', 'existencia'),
  ('contabilidad-activos','skill', 'asset accounting',      'ambos', 'existencia'),
  ('activos-fijos',       'skill', 'fixed assets',           'ambos', 'existencia'),
  ('contabilidad-arrendamientos','skill', 'lease accounting', 'ambos', 'existencia'),
  ('presupuestos',        'skill', 'budgeting',              'ambos', 'existencia'),
  ('pronosticos',         'skill', 'forecasting',            'ambos', 'existencia'),
  ('pricing',             'skill', 'pricing',                'ambos', 'existencia'),
  ('payroll',             'skill', 'payroll',                'ambos', 'existencia'),
  ('asc-606',             'skill', 'asc 606',                'ambos', 'existencia'),
  ('sox-compliance',      'skill', 'sox compliance',         'ambos', 'existencia'),
  ('sox-tests',           'skill', 'sox tests',              'ambos', 'existencia'),
  ('us-gaap',             'skill', 'us gaap',                'ambos', 'existencia'),
  ('capex',               'skill', 'capex',                  'ambos', 'existencia'),
  ('audit-readiness',     'skill', 'audit readiness',        'ambos', 'existencia'),
  ('controles-internos',  'skill', 'internal controls',      'ambos', 'existencia'),
  ('credit-checks',       'skill', 'credit checks',          'ambos', 'existencia'),
  ('kyc',                 'skill', 'kyc',                    'ambos', 'existencia'),
  ('gdpr',                'skill', 'gdpr',                   'ambos', 'existencia'),
  ('tcpa',                'skill', 'tcpa',                   'ambos', 'existencia'),
  ('master-data',         'skill', 'master data',            'ambos', 'existencia'),
  ('proformas',           'skill', 'proformas',              'ambos', 'existencia'),
  ('etmf',                'skill', 'etmf',                   'ambos', 'existencia'),
  ('regulatory-approvals','skill', 'regulatory approvals',   'ambos', 'existencia'),
  ('regulatory-compliance','skill', 'regulatory compliance',  'ambos', 'existencia'),
  ('compliance',          'skill', 'compliance',             'ambos', 'existencia'),
  ('data-risk-taxonomy',  'skill', 'data risk taxonomy',     'ambos', 'existencia');

-- --- IT / soporte / redes / desarrollo --------------------------------------
INSERT OR IGNORE INTO concepto (codigo_canonico, categoria, variante, origen, tipo) VALUES
  ('troubleshooting',     'skill', 'troubleshooting',              'ambos', 'existencia'),
  ('troubleshooting',     'skill', 'troubleshoot',                 'ambos', 'existencia'),
  ('troubleshooting',     'skill', 'troubleshoot technical issues','ambos', 'existencia'),
  ('soporte-tecnico',     'skill', 'soporte tecnico',              'ambos', 'existencia'),
  ('soporte-tecnico',     'skill', 'technical support',            'ambos', 'existencia'),
  ('soporte-tecnico',     'skill', 'soporte de aplicaciones',      'ambos', 'existencia'),
  ('crm',                 'skill', 'crm',                          'ambos', 'existencia'),
  ('crm',                 'skill', 'crm platforms',                'ambos', 'existencia'),
  ('pos',                 'skill', 'pos',                          'ambos', 'existencia'),
  ('erp',                 'skill', 'erp systems',                  'ambos', 'existencia'),
  ('workday',             'skill', 'workday',                      'ambos', 'existencia'),
  ('salesforce',          'skill', 'salesforce',                   'ambos', 'existencia'),
  ('dns',                 'skill', 'dns',                          'ambos', 'existencia'),
  ('firewall',            'skill', 'firewall',                     'ambos', 'existencia'),
  ('firewall',            'skill', 'firewalls',                    'ambos', 'existencia'),
  ('bgp',                 'skill', 'bgp',                          'ambos', 'existencia'),
  ('tcp-ip',              'skill', 'tcp ip',                       'ambos', 'existencia'),
  ('redes',               'skill', 'redes',                        'ambos', 'existencia'),
  ('redes',               'skill', 'networking',                   'ambos', 'existencia'),
  ('redes',               'skill', 'network',                      'ambos', 'existencia'),
  ('redes',               'skill', 'switching',                    'ambos', 'existencia'),
  ('redes',               'skill', 'connectivity',                 'ambos', 'existencia'),
  ('nat',                 'skill', 'nat',                          'ambos', 'existencia'),
  ('ipsec',               'skill', 'ipsec',                        'ambos', 'existencia'),
  ('aruba',               'skill', 'hpe aruba networking',         'ambos', 'existencia'),
  ('hardware',            'skill', 'hardware',                     'ambos', 'existencia'),
  ('hardware',            'skill', 'computer hardware',            'ambos', 'existencia'),
  ('windows',             'skill', 'windows',                      'ambos', 'existencia'),
  ('ci-cd',               'skill', 'ci cd',                        'ambos', 'existencia'),
  ('ci-cd',               'skill', 'ci cd pipelines',              'ambos', 'existencia'),
  ('ci-cd',               'skill', 'integracion continua ci',      'ambos', 'existencia'),
  ('docker',              'skill', 'docker',                       'ambos', 'existencia'),
  ('kubernetes',          'skill', 'kubernetes',                   'ambos', 'existencia'),
  ('ansible',             'skill', 'ansible',                      'ambos', 'existencia'),
  ('terraform',           'skill', 'terraform',                    'ambos', 'existencia'),
  ('postman',             'skill', 'postman',                      'ambos', 'existencia'),
  ('jira',                'skill', 'jira',                         'ambos', 'existencia'),
  ('sharepoint',          'skill', 'sharepoint',                   'ambos', 'existencia'),
  ('power-apps',          'skill', 'power apps',                   'ambos', 'existencia'),
  ('power-automate',      'skill', 'power automate',               'ambos', 'existencia'),
  ('powerpoint',          'skill', 'powerpoint',                   'ambos', 'existencia'),
  ('node-js',             'skill', 'node.js',                      'ambos', 'existencia'),
  ('graphql',             'skill', 'graphql',                      'ambos', 'existencia'),
  ('rest-api',            'skill', 'rest',                         'ambos', 'existencia'),
  ('rest-api',            'skill', 'rest apis',                    'ambos', 'existencia'),
  ('rest-api',            'skill', 'restful apis',                 'ambos', 'existencia'),
  ('api',                 'skill', 'apis',                         'ambos', 'existencia'),
  ('ai',                  'skill', 'ai',                           'ambos', 'existencia'),
  ('ai',                  'skill', 'artificial intelligence',      'ambos', 'existencia'),
  ('ai',                  'skill', 'ai tools',                     'ambos', 'existencia'),
  ('prompt-engineering',  'skill', 'prompt engineering',           'ambos', 'existencia'),
  ('rag',                 'skill', 'rag',                          'ambos', 'existencia'),
  ('analisis-de-datos',   'skill', 'data analysis',                'ambos', 'existencia'),
  ('analisis-de-datos',   'skill', 'data analytics',               'ambos', 'existencia'),
  ('analisis-de-datos',   'skill', 'analytics',                    'ambos', 'existencia'),
  ('analisis-de-datos',   'skill', 'exploratory data analysis',    'ambos', 'existencia'),
  ('data-entry',          'skill', 'data entry',                   'ambos', 'existencia'),
  ('data-pipelines',      'skill', 'data pipelines',               'ambos', 'existencia'),
  ('data-validation',     'skill', 'data validation',              'ambos', 'existencia'),
  ('dashboards',          'skill', 'dashboards',                   'ambos', 'existencia'),
  ('incident-response',   'skill', 'incident response',            'ambos', 'existencia'),
  ('automatizacion',      'skill', 'automation',                   'ambos', 'existencia'),
  ('automatizacion',      'skill', 'automatizacion',               'ambos', 'existencia'),
  ('metodologias-agiles', 'skill', 'metodologias agiles',           'ambos', 'existencia'),
  ('metodologias-agiles', 'skill', 'agile',                        'ambos', 'existencia'),
  ('metodologias-agiles', 'skill', 'scrum',                        'ambos', 'existencia'),
  ('metodologias-agiles', 'skill', 'kanban',                       'ambos', 'existencia'),
  ('lean',                'skill', 'kaizen',                       'ambos', 'existencia'),
  ('lean',                'skill', 'lean methods',                 'ambos', 'existencia'),
  ('lean',                'skill', 'lean manufacturing',           'ambos', 'existencia'),
  ('mejora-de-procesos',  'skill', 'process improvements',         'ambos', 'existencia'),
  ('mejora-de-procesos',  'skill', 'process improvement initiatives', 'ambos', 'existencia'),
  ('mejora-de-procesos',  'skill', 'process optimization',         'ambos', 'existencia'),
  ('root-cause-analysis', 'skill', 'root cause analysis',          'ambos', 'existencia'),
  ('root-cause-analysis', 'skill', 'root-cause analysis',          'ambos', 'existencia'),
  ('problem-solving',     'skill', 'problem-solving',              'ambos', 'existencia'),
  ('problem-solving',     'skill', 'problem solve',                'ambos', 'existencia'),
  ('creative-thinking',   'skill', 'creative thinking',            'ambos', 'existencia'),
  ('testing',             'skill', 'testing',                      'ambos', 'existencia'),
  ('testing',             'skill', 'test tooling',                 'ambos', 'existencia'),
  ('pruebas-unitarias',   'skill', 'pruebas unitarias',            'ambos', 'existencia'),
  ('uat',                 'skill', 'uat',                          'ambos', 'existencia'),
  ('desarrollo-software', 'skill', 'desarrollo de software',       'ambos', 'existencia'),
  ('desarrollo-aplicaciones','skill', 'desarrollo de aplicaciones','ambos', 'existencia'),
  ('code-review',         'skill', 'revisiones de codigo',         'ambos', 'existencia'),
  ('technical-writing',   'skill', 'technical writing skills',     'ambos', 'existencia'),
  ('atencion-al-cliente', 'skill', 'customer service skills',      'ambos', 'existencia'),
  ('atencion-al-cliente', 'skill', 'customer support',             'ambos', 'existencia'),
  ('atencion-al-cliente', 'skill', 'customer success',             'ambos', 'existencia'),
  ('atencion-al-cliente', 'skill', 'servicio al cliente',          'ambos', 'existencia'),
  ('configuracion',       'skill', 'configuracion',                'ambos', 'existencia'),
  ('mantenimiento',       'skill', 'mantenimiento',                'ambos', 'existencia'),
  ('mantenimiento',       'skill', 'maintenance',                  'ambos', 'existencia'),
  ('mantenimiento',       'skill', 'mantenimiento preventivo',     'ambos', 'existencia'),
  ('mantenimiento',       'skill', 'preventive maintenance',       'ambos', 'existencia'),
  ('operational-support', 'skill', 'operational support',          'ambos', 'existencia'),
  ('supplier-support',    'skill', 'supplier support',             'ambos', 'existencia'),
  ('security',            'skill', 'security',                     'ambos', 'existencia'),
  ('integracion-aplicaciones','skill', 'integracion de aplicaciones','ambos', 'existencia'),
  ('implementacion-aplicaciones','skill', 'implementacion de aplicaciones','ambos', 'existencia');

-- --- comunicacion / marketing / traduccion ----------------------------------
INSERT OR IGNORE INTO concepto (codigo_canonico, categoria, variante, origen, tipo) VALUES
  ('traduccion',       'skill', 'translation',              'ambos', 'existencia'),
  ('interpretacion',   'skill', 'bilingual interpreter',    'ambos', 'existencia'),
  ('interpretacion',   'skill', 'interpretation protocols', 'ambos', 'existencia'),
  ('interpretacion',   'skill', 'consecutive interpretation services', 'ambos', 'existencia'),
  ('proofreading',     'skill', 'proofreading',             'ambos', 'existencia'),
  ('content-creation', 'skill', 'content creation',         'ambos', 'existencia'),
  ('programmatic-media','skill', 'programmatic media',      'ambos', 'existencia'),
  ('email',            'skill', 'email',                    'ambos', 'existencia');

-- --- administracion / proyecto / rrhh ----------------------------------------
INSERT OR IGNORE INTO concepto (codigo_canonico, categoria, variante, origen, tipo) VALUES
  ('project-planning',   'skill', 'project planning',   'ambos', 'existencia'),
  ('project-planning',   'skill', 'project plans',      'ambos', 'existencia'),
  ('project-planning',   'skill', 'project coordination','ambos', 'existencia'),
  ('project-planning',   'skill', 'milestones',         'ambos', 'existencia'),
  ('scenario-planning',  'skill', 'scenario planning',  'ambos', 'existencia'),
  ('production-planning','skill', 'production planning','ambos', 'existencia'),
  ('procurement',        'skill', 'procurement',        'ambos', 'existencia'),
  ('coaching',           'skill', 'coaching',           'ambos', 'existencia'),
  ('training',           'skill', 'training',           'ambos', 'existencia'),
  ('research',           'skill', 'research',           'ambos', 'existencia'),
  ('documentation',      'skill', 'documentation',      'ambos', 'existencia'),
  ('reporting',          'skill', 'reports',            'ambos', 'existencia'),
  ('reporting',          'skill', 'reporting',          'ambos', 'existencia'),
  ('standardization',    'skill', 'standardization',    'ambos', 'existencia'),
  ('accuracy',           'skill', 'accuracy',           'ambos', 'existencia'),
  ('auditoria',          'skill', 'auditing',           'ambos', 'existencia');
