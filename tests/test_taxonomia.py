# -*- coding: utf-8 -*-
"""Tests de la curacion de la taxonomia (`jobpulse_v15.taxonomia`).

Por que existe: la cola `concepto_no_normalizado` es la lista de trabajo de
la taxonomia (que variantes del corpus todavia no tienen codigo canonico).
Con el corpus real tenia 1988 filas, 1976 de ellas sin resolver: la mayoria
eran actividades ("despachar"), palabras vacias ("analysis") o sectores
("construccion"). `taxonomia.curar` la reconstruye desde el corpus: deja lo
que de verdad falta y lo cuenta por avisos que lo piden.

Patron: tempfile + Database + Repository (no toca la BD real).
"""

import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15 import taxonomia
from jobpulse_v15.db import Database
from jobpulse_v15.repository import Repository


class TestTaxonomia(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.tmpdir.name) / "test.db")
        self.database.initialize()
        self.repository = Repository(self.database)
        self.repository.register_platform(
            "workday", "Workday", "api", default_language="en"
        )
        self.repository.register_site(
            "intel-cr",
            "workday",
            "Intel Careers Costa Rica",
            "https://example.test/jobs",
            company_name="Intel",
            country="CR",
        )
        self._crear_aviso("job-1", ["Excel", "TecnologiaFutura", "Despachar"])
        self._crear_aviso("job-2", ["Excel", "Despachar"])
    def tearDown(self):
        self.tmpdir.cleanup()

    def _crear_aviso(self, job_id, skills):
        self.repository.save_job(
            {
                "job_id": job_id,
                "title": "Analyst",
                "company": "Intel",
                "country": "CR",
                "description_raw": "Se requiere Excel avanzado.",
            },
            site_id="intel-cr",
            source_job_id="S-%s" % job_id,
        )
        # `jobs.skills` lo escribe el pase de enriquecimiento (columna JSON);
        # `save_job` no la toca.
        with closing(sqlite3.connect(self.database.path)) as connection:
            connection.execute(
                "UPDATE jobs SET skills = ? WHERE job_id = ?",
                (json.dumps(skills), job_id),
            )
            connection.commit()

    def _cola(self):
        with closing(sqlite3.connect(self.database.path)) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(
                """
                SELECT categoria, texto, origen, veces
                FROM concepto_no_normalizado
                ORDER BY categoria, texto, origen
                """
            ).fetchall()

    def test_la_demanda_separa_resueltas_ruido_y_pendientes(self):
        with closing(sqlite3.connect(self.database.path)) as connection:
            demanda = taxonomia.demanda_corpus(connection)
        # 'excel' resuelve (esta en la taxonomia), 'despachar' es actividad y
        # 'tecnologiafutura' es una competencia que la taxonomia no cubre.
        self.assertIn(("skill", "excel"), demanda["resueltas"])
        self.assertIn(("skill", "despachar"), demanda["ruido"])
        self.assertIn(("skill", "tecnologiafutura"), demanda["pendientes"])
        # 'despachar' lo piden los dos avisos: la cuenta es por aviso.
        self.assertEqual(demanda["ruido"][("skill", "despachar")], 2)

    def test_curar_sin_apply_no_escribe(self):
        with closing(sqlite3.connect(self.database.path)) as connection:
            connection.execute(
                """
                INSERT INTO concepto_no_normalizado (categoria, texto, origen, veces)
                VALUES ('skill', 'cola-vieja', 'oferta', 7)
                """
            )
            connection.commit()
            informe = taxonomia.curar(connection, aplicar=False)
            filas = connection.execute(
                "SELECT COUNT(*) FROM concepto_no_normalizado"
            ).fetchone()[0]
        self.assertEqual(informe["modo"], "dry_run")
        self.assertEqual(filas, 1)
        self.assertEqual(informe["a_borrar"], 1)

    def test_curar_reconstruye_la_cola_desde_el_corpus(self):
        with closing(sqlite3.connect(self.database.path)) as connection:
            connection.execute(
                """
                INSERT INTO concepto_no_normalizado (categoria, texto, origen, veces)
                VALUES ('skill', 'cola-vieja', 'oferta', 7)
                """
            )
            connection.execute(
                """
                INSERT INTO concepto_no_normalizado (categoria, texto, origen, veces)
                VALUES ('skill', 'tecnologiafutura', 'cv', 2)
                """
            )
            connection.commit()
            informe = taxonomia.curar(connection, aplicar=True)
            filas = connection.execute(
                """
                SELECT categoria, texto, origen, veces
                FROM concepto_no_normalizado
                ORDER BY texto
                """
            ).fetchall()
        # La fila historica (el corpus ya no la pide) se borra; el ruido
        # ('despachar') nunca se encola; lo pendiente queda con el numero de
        # AVISOS que lo piden; y la fila del perfil ('cv') no se toca.
        self.assertEqual(
            [(r[0], r[1], r[2], r[3]) for r in filas],
            [
                ("skill", "tecnologiafutura", "cv", 2),
                ("skill", "tecnologiafutura", "oferta", 1),
            ],
        )
        self.assertEqual(informe["demanda"]["pendientes"], 1)

    def test_curar_es_idempotente(self):
        with closing(sqlite3.connect(self.database.path)) as connection:
            taxonomia.curar(connection, aplicar=True)
            primera = connection.execute(
                "SELECT COUNT(*) FROM concepto_no_normalizado"
            ).fetchone()[0]
            taxonomia.curar(connection, aplicar=True)
            segunda = connection.execute(
                "SELECT COUNT(*) FROM concepto_no_normalizado"
            ).fetchone()[0]
        self.assertEqual(primera, segunda)

    def test_el_idioma_disfrazado_de_skill_no_se_encola_como_skill(self):
        """"Inglés - C1" entre las skills es peticion de IDIOMA.

        El extractor nunca crea un requisito skill con eso (los idiomas se
        comparan contra los hechos de idioma del perfil): curar "ingles c1"
        como skill daria un falso "faltante". La demanda lo cuenta en el
        lado idioma — resuelto, porque 'ingles' esta en la taxonomia — y la
        cola no lo pide. "IT" en cambio es tecnologia: sigue siendo skill.
        """
        self._crear_aviso(
            "job-3", ["Inglés - C1", "English <> Target Language", "IT"]
        )
        with closing(sqlite3.connect(self.database.path)) as connection:
            demanda = taxonomia.demanda_corpus(connection)
        self.assertNotIn(("skill", "ingles c1"), demanda["pendientes"])
        self.assertNotIn(
            ("skill", "english target language"), demanda["pendientes"]
        )
        self.assertEqual(demanda["resueltas"][("language", "ingles")], 2)
        # "IT" no es italiano (bug real corregido por la 026): es skill.
        self.assertNotIn(("language", "italiano"), demanda["resueltas"])
        self.assertIn(("skill", "it"), demanda["pendientes"])

    def test_curar_borra_los_idiomas_disfrazados_de_la_cola(self):
        """Si la cola tenia la variante fantasma, curar la limpia."""
        with closing(sqlite3.connect(self.database.path)) as connection:
            connection.execute(
                """
                INSERT INTO concepto_no_normalizado (categoria, texto, origen, veces)
                VALUES ('skill', 'ingles c1', 'oferta', 2)
                """
            )
            connection.commit()
            taxonomia.curar(connection, aplicar=True)
            filas = [
                (r[0], r[1])
                for r in connection.execute(
                    "SELECT categoria, texto FROM concepto_no_normalizado"
                ).fetchall()
            ]
        self.assertNotIn(("skill", "ingles c1"), filas)


if __name__ == "__main__":
    unittest.main()
