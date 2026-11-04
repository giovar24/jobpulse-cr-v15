# -*- coding: utf-8 -*-
"""CAPA B: los hechos del perfil llevan `codigo_canonico` (el motor los ve).

Sin esto, `candidate_profile_facts.codigo_canonico` queda NULL y el Paso 5 /
el motor de viabilidad los IGNORAN (filtran por `codigo_canonico IS NOT
NULL`): el perfil es invisible.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15.db import Database  # noqa: E402
from jobpulse_v15.repository import Repository  # noqa: E402


class TestPerfilCanonico(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.initialize()
        self.repository = Repository(self.database)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _codigos(self):
        with self.database.connection() as connection:
            return {
                (row["category"], row["value_code"]): row["codigo_canonico"]
                for row in connection.execute(
                    "SELECT category, value_code, codigo_canonico "
                    "FROM candidate_profile_facts"
                )
            }

    def test_guardar_un_fact_resuelve_el_codigo_canonico(self):
        self.repository.save_candidate_profile_fact("skill", "excel", "Excel")

        self.assertEqual(self._codigos()[("skill", "excel")], "excel")

    def test_el_alias_de_fabricante_tambien_resuelve(self):
        self.repository.save_candidate_profile_fact(
            "skill", "excel avanzado", "Excel Avanzado"
        )

        self.assertEqual(self._codigos()[("skill", "excel avanzado")], "excel")

    def test_guardar_no_pisa_un_codigo_ya_escrito(self):
        with self.database.connection() as connection:
            connection.execute(
                """
                INSERT INTO candidate_profile_facts (
                    category, value_code, value_text, codigo_canonico
                ) VALUES ('skill', 'active-directory', 'Active Directory',
                          'active-directory')
                """
            )
        # 'active directory' (con espacio) SI existe en la taxonomia; la
        # variante 'active-directory' no, asi que el resolver devuelve None.
        self.repository.save_candidate_profile_fact(
            "skill", "active-directory", "Active Directory"
        )

        self.assertEqual(
            self._codigos()[("skill", "active-directory")], "active-directory"
        )

    def test_importar_resuelve_el_codigo_canonico(self):
        self.repository.import_candidate_profile_facts(
            "cv-test",
            [
                {
                    "category": "skill",
                    "value_code": "servicenow",
                    "value_text": "ServiceNow",
                },
                {
                    "category": "language",
                    "value_code": "ingles",
                    "value_text": "Ingles",
                    "qualifier": "B2",
                },
            ],
        )

        codigos = self._codigos()
        self.assertEqual(codigos[("skill", "servicenow")], "servicenow")
        self.assertEqual(codigos[("language", "ingles")], "ingles")

    def test_una_variante_sin_concepto_queda_null_y_se_encola_como_cv(self):
        self.repository.save_candidate_profile_fact(
            "skill", "mi-tecnologia-exclusiva", "Mi Tecnologia"
        )

        self.assertIsNone(self._codigos()[("skill", "mi-tecnologia-exclusiva")])
        with self.database.connection() as connection:
            fila = connection.execute(
                "SELECT origen, veces FROM concepto_no_normalizado "
                "WHERE categoria='skill' AND texto='mi-tecnologia-exclusiva'"
            ).fetchone()
        self.assertIsNotNone(fila)
        self.assertEqual(fila["origen"], "cv")

    def test_backfill_rellena_los_null_y_respeta_los_existentes(self):
        with self.database.connection() as connection:
            connection.execute(
                """
                INSERT INTO candidate_profile_facts (
                    category, value_code, value_text, codigo_canonico
                ) VALUES ('skill', 'excel', 'Excel', NULL)
                """
            )
            connection.execute(
                """
                INSERT INTO candidate_profile_facts (
                    category, value_code, value_text, codigo_canonico
                ) VALUES ('skill', 'inventada', 'Inventada', 'inventada')
                """
            )

        actualizados = self.repository.backfill_candidate_profile_canonico()

        self.assertEqual(actualizados, 1)
        codigos = self._codigos()
        self.assertEqual(codigos[("skill", "excel")], "excel")
        self.assertEqual(codigos[("skill", "inventada")], "inventada")

    def test_backfill_es_idempotente(self):
        with self.database.connection() as connection:
            connection.execute(
                """
                INSERT INTO candidate_profile_facts (
                    category, value_code, value_text, codigo_canonico
                ) VALUES ('skill', 'excel', 'Excel', NULL)
                """
            )

        self.assertEqual(self.repository.backfill_candidate_profile_canonico(), 1)
        self.assertEqual(self.repository.backfill_candidate_profile_canonico(), 0)


class TestColaDelPerfil(unittest.TestCase):
    """La cola del perfil solo crece con CONCEPTOS, no con basura.

    Los hechos de `experience` del CV son TITULOS DE PUESTO ('Soporte
    Tecnico'): no son conceptos que falten en la taxonomia. Encolarlos
    ensuciaria `concepto_no_normalizado` con datos que jamas se van a
    convertir en codigo canonico.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.initialize()
        self.repository = Repository(self.database)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _cola(self):
        with self.database.connection() as connection:
            return [
                (row["categoria"], row["texto"], row["origen"])
                for row in connection.execute(
                    "SELECT categoria, texto, origen FROM concepto_no_normalizado"
                )
            ]

    def test_un_titulo_de_puesto_no_se_encola(self):
        self.repository.save_candidate_profile_fact(
            "experience", "soporte-tecnico", "Soporte Tecnico"
        )

        self.assertEqual(self._cola(), [])

    def test_un_contacto_no_se_encola(self):
        self.repository.save_candidate_profile_fact("contact", "email", "correo")

        self.assertEqual(self._cola(), [])

    def test_una_skill_sin_concepto_si_se_encola(self):
        self.repository.save_candidate_profile_fact(
            "skill", "mi-tecnologia-exclusiva", "Mi Tecnologia"
        )

        self.assertEqual(
            self._cola(),
            [("skill", "mi-tecnologia-exclusiva", "cv")],
        )

    def test_una_experiencia_conceptual_si_recibe_codigo(self):
        # 'years_experience' SI es un concepto de la taxonomia: recibe su
        # codigo, aunque los titulos de puesto no lo hagan.
        self.repository.save_candidate_profile_fact(
            "experience", "years_experience", "Anios de experiencia"
        )

        with self.database.connection() as connection:
            codigo = connection.execute(
                "SELECT codigo_canonico FROM candidate_profile_facts "
                "WHERE category='experience' AND value_code='years_experience'"
            ).fetchone()["codigo_canonico"]
        self.assertEqual(codigo, "experiencia-anos")
        self.assertEqual(self._cola(), [])

    def test_el_backfill_no_encola_titulos_de_puesto(self):
        with self.database.connection() as connection:
            connection.execute(
                """
                INSERT INTO candidate_profile_facts (
                    category, value_code, value_text, codigo_canonico
                ) VALUES ('experience', 'soporte-tecnico', 'Soporte Tecnico', NULL)
                """
            )

        self.assertEqual(self.repository.backfill_candidate_profile_canonico(), 0)
        self.assertEqual(self._cola(), [])


if __name__ == "__main__":
    unittest.main()
