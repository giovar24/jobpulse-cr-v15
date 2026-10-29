-- 009_concepto_normalizacion.sql
-- Tabla global de conceptos: mapea variantes de texto a un código canónico.
-- Sin referencia a ningún CV ni perfil. Sirve para cualquier candidato.
-- Idempotente: se puede ejecutar más de una vez sin duplicar datos.

-- ---------------------------------------------------------------
-- 1. Escala ordenada para educación e idiomas
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS nivel_escala (
  categoria TEXT    NOT NULL CHECK (categoria IN ('education','language')),
  codigo    TEXT    NOT NULL,
  orden     INTEGER NOT NULL CHECK (orden > 0),
  PRIMARY KEY (categoria, codigo)
);

INSERT OR IGNORE INTO nivel_escala (categoria, codigo, orden) VALUES
  ('education', 'secundaria',   1),
  ('education', 'tecnico',      2),
  ('education', 'universitaria',3),
  ('education', 'posgrado',     4),
  ('language',  'A1', 1),
  ('language',  'A2', 2),
  ('language',  'B1', 3),
  ('language',  'B2', 4),
  ('language',  'C1', 5),
  ('language',  'C2', 6);

-- ---------------------------------------------------------------
-- 2. Tabla de conceptos (variante de texto -> código canónico)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS concepto (
  codigo_canonico TEXT    NOT NULL,
  categoria       TEXT    NOT NULL CHECK (categoria IN
                    ('skill','language','license','education','experience')),
  variante        TEXT    NOT NULL,
  origen          TEXT    NOT NULL CHECK (origen IN ('oferta','cv','ambos')),
  nivel_orden     INTEGER,
  activa          INTEGER NOT NULL DEFAULT 1 CHECK (activa IN (0,1)),
  PRIMARY KEY (categoria, variante)
);

CREATE INDEX IF NOT EXISTS idx_concepto_canonico ON concepto (codigo_canonico);
CREATE INDEX IF NOT EXISTS idx_concepto_categoria ON concepto (categoria);

-- ---------------------------------------------------------------
-- 3. Cola de variantes no normalizadas (crecimiento con datos reales)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS concepto_no_normalizado (
  categoria   TEXT    NOT NULL,
  texto       TEXT    NOT NULL,
  origen      TEXT    NOT NULL CHECK (origen IN ('oferta','cv','ambos')),
  veces       INTEGER NOT NULL DEFAULT 1 CHECK (veces >= 1),
  codigo_canonico_sugerido TEXT NULL,
  PRIMARY KEY (categoria, texto, origen)
);

CREATE INDEX IF NOT EXISTS idx_no_normalizado_categoria ON concepto_no_normalizado(categoria, veces DESC);

-- ---------------------------------------------------------------
-- 4. Idiomas (el nivel de competencia va en qualifier del fact/requisito)
-- ---------------------------------------------------------------
INSERT OR IGNORE INTO concepto (codigo_canonico, categoria, variante, origen) VALUES
  ('ingles',    'language', 'en',       'ambos'),
  ('ingles',    'language', 'english',  'ambos'),
  ('ingles',    'language', 'ingles',   'ambos'),
  ('espanol',   'language', 'es',       'ambos'),
  ('espanol',   'language', 'spanish',  'ambos'),
  ('espanol',   'language', 'espanol',  'ambos'),
  ('frances',   'language', 'fr',       'ambos'),
  ('frances',   'language', 'french',   'ambos'),
  ('frances',   'language', 'frances',  'ambos'),
  ('portugues', 'language', 'pt',       'ambos'),
  ('portugues', 'language', 'portuguese','ambos'),
  ('portugues', 'language', 'portugues', 'ambos');

-- ---------------------------------------------------------------
-- 5. Educación (nivel_orden referencia a nivel_escala.orden)
-- ---------------------------------------------------------------
INSERT OR IGNORE INTO concepto (codigo_canonico, categoria, variante, origen, nivel_orden) VALUES
  ('educacion-secundaria', 'education', 'secondary',               'oferta', 1),
  ('educacion-secundaria', 'education', 'high school',             'ambos',  1),
  ('educacion-secundaria', 'education', 'bachillerato',            'ambos',  1),
  ('educacion-universitaria','education','bachelor',               'ambos', 3),
  ('educacion-universitaria','education','university_degree',      'oferta', 3),
  ('educacion-universitaria','education','licenciatura',           'ambos',  3),
  ('educacion-tecnica',    'education', 'tecnico',                 'ambos',  2),
  ('educacion-tecnica',    'education', 'tecnologo',               'ambos',  2),
  ('educacion-posgrado',   'education', 'maestria',                'ambos',  4),
  ('educacion-posgrado',   'education', 'posgrado',                'ambos',  4);

-- ---------------------------------------------------------------
-- 6. Experiencia (la cantidad de años se evalúa numéricamente en el Paso 5)
-- ---------------------------------------------------------------
INSERT OR IGNORE INTO concepto (codigo_canonico, categoria, variante, origen) VALUES
  ('experiencia-anos', 'experience', 'years_experience', 'oferta'),
  ('experiencia-anos', 'experience', 'experiencia',      'ambos'),
  ('experiencia-anos', 'experience', 'anos de experiencia','ambos');

-- ---------------------------------------------------------------
-- 7. Licencias de conducir
-- ---------------------------------------------------------------
INSERT OR IGNORE INTO concepto (codigo_canonico, categoria, variante, origen, nivel_orden) VALUES
  ('licencia-conducir', 'license', 'a1', 'ambos', NULL),
  ('licencia-conducir', 'license', 'b1', 'ambos', NULL),
  ('licencia-conducir', 'license', 'b2', 'ambos', NULL),
  ('licencia-conducir', 'license', 'c1', 'ambos', NULL);

-- ---------------------------------------------------------------
-- 8. Skills de alta frecuencia en ofertas (genéricas, no de ningún CV)
-- ---------------------------------------------------------------
INSERT OR IGNORE INTO concepto (codigo_canonico, categoria, variante, origen) VALUES
  ('excel',         'skill', 'excel',               'ambos'),
  ('excel',         'skill', 'excel avanzado',      'ambos'),
  ('excel',         'skill', 'microsoft excel',     'ambos'),
  ('python',        'skill', 'python',              'ambos'),
  ('sql',           'skill', 'sql',                 'ambos'),
  ('sql',           'skill', 'sql server',          'ambos'),
  ('sql',           'skill', 'microsoft sql server','ambos'),
  ('microsoft-365', 'skill', 'microsoft 365',       'ambos'),
  ('microsoft-365', 'skill', 'office 365',          'ambos'),
  ('microsoft-365', 'skill', 'm365',                'ambos'),
  ('active-directory','skill','active directory',   'ambos'),
  ('aws',           'skill', 'aws',                 'ambos'),
  ('azure',         'skill', 'azure',               'ambos'),
  ('gcp',           'skill', 'gcp',                 'ambos'),
  ('linux',         'skill', 'linux',               'ambos'),
  ('power-bi',      'skill', 'power_bi',            'oferta'),
  ('power-bi',      'skill', 'power bi',            'ambos'),
  ('sap',           'skill', 'sap',                 'ambos'),
  ('javascript',    'skill', 'javascript',          'ambos'),
  ('git',           'skill', 'git',                 'ambos'),
  ('servicenow',    'skill', 'servicenow',          'ambos'),
  ('okta',          'skill', 'okta',                'ambos');

-- ---------------------------------------------------------------
-- Fin de la migración 009
-- ---------------------------------------------------------------
