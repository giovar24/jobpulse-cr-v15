# -*- coding: utf-8 -*-
"""ALINEACION: que los requisitos del aviso y los del perfil se comparen.

Objetivo del software: encontrar, entre TODOS los puestos, los que tienen
requisitos mas compatibles con la persona del CV.

Para eso hacen falta dos cosas:

1. que cada requisito del aviso tenga `codigo_canonico` (el motor SOLO
   compara los que lo tienen: `AND codigo_canonico IS NOT NULL`; los demas
   se IGNORAN en silencio);
2. que la taxonomia cubra las variantes que aparecen en los avisos reales
   (migracion 020: java, tableau, six_sigma, c++, c#, typescript, autocad,
   solidworks y las clases de licencia de CR).

Y una regla dura para las LICENCIAS: si el perfil no registra ninguna, no se
puede afirmar que no la tenga -> 'no_verificable' (nunca se descarta por
falta de informacion; misma regla que los idiomas).
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15 import analysis  # noqa: E402
from jobpulse_v15.db import Database  # noqa: E402
from jobpulse_v15.matching import EvaluadorPaso5  # noqa: E402
from jobpulse_v15.repository import Repository  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.initialize()
        self.repository = Repository(self.database)
        self.repository.register_platform("workday", "Workday", "api")
        self.repository.register_site(
            "sitio", "workday", "Sitio", "https://example.test/jobs"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _job(self, job_id="job-1", title="Support Engineer"):
        self.repository.save_job(
            {
                "job_id": job_id,
                "title": title,
                "company": "Example",
                "country": "CR",
                "posting_language": "en",
                "description_raw": "Descripcion.",
            },
            site_id="sitio",
            source_job_id=job_id,
        )
        return job_id

    def _analisis(self, job_id, requirements, status="complete"):
        categorias = {req["category"] for req in requirements}
        self.repository.save_analysis(
            job_id,
            text_hash=f"hash-{job_id}",
            extractor_version="rules-1",
            analysis_status=status,
            field_statuses={c: "found" for c in sorted(categorias)},
            requirements=requirements,
        )

    def _codigos(self, job_id=None):
        with self.database.connection() as connection:
            if job_id:
                filas = connection.execute(
                    """
                    SELECT r.value_code, r.codigo_canonico
                    FROM job_requirements AS r
                    JOIN job_analysis AS a ON a.analysis_id = r.analysis_id
                    WHERE a.job_id = ? AND a.is_current = 1
                    """,
                    (job_id,),
                ).fetchall()
            else:
                filas = connection.execute(
                    "SELECT value_code, codigo_canonico FROM job_requirements"
                ).fetchall()
        return {f["value_code"]: f["codigo_canonico"] for f in filas}


class TestTaxonomiaDeAlineacion(Base):
    """La migracion 020 cubre lo que el corpus real pedia."""

    def test_las_skills_que_pedia_el_corpus_existen(self):
        for codigo in (
            "java",
            "tableau",
            "six_sigma",
            "c++",
            "c#",
            "typescript",
            "autocad",
            "solidworks",
        ):
            with self.database.connection() as connection:
                fila = connection.execute(
                    "SELECT codigo_canonico FROM concepto "
                    "WHERE categoria='skill' AND variante=?",
                    (codigo,),
                ).fetchone()
            self.assertIsNotNone(fila, f"falta el concepto {codigo}")
            self.assertEqual(fila["codigo_canonico"], codigo)

    def test_las_clases_de_licencia_de_cr_existen(self):
        for clase in ("a1", "a2", "b1", "b2", "b3", "c1", "c2", "d1", "d3", "e1", "f1"):
            with self.database.connection() as connection:
                fila = connection.execute(
                    "SELECT codigo_canonico FROM concepto "
                    "WHERE categoria='license' AND variante=?",
                    (clase,),
                ).fetchone()
            self.assertIsNotNone(fila, f"falta la licencia {clase}")
            self.assertEqual(fila["codigo_canonico"], "licencia-conducir")

    def test_la_licencia_generica_sin_clase_tiene_concepto(self):
        with self.database.connection() as connection:
            fila = connection.execute(
                "SELECT codigo_canonico FROM concepto "
                "WHERE categoria='license' AND variante=\"driver's license\""
            ).fetchone()
        self.assertIsNotNone(fila)
        self.assertEqual(fila["codigo_canonico"], "licencia-conducir")

    def test_un_requisito_nuevo_nace_con_codigo(self):
        # Al GUARDAR el analisis (no hace falta backfill para lo nuevo).
        job_id = self._job()
        self._analisis(
            job_id,
            [
                {
                    "category": "skill",
                    "value_code": "java",
                    "value_text": "Java",
                    "requirement_level": "required",
                    "evidence": "Required: Java.",
                    "origin": "rule",
                    "confidence": 0.9,
                }
            ],
        )

        self.assertEqual(self._codigos(job_id)["java"], "java")


class TestExtractorDeLicencias(unittest.TestCase):
    """La clase de licencia se pierde en 'licencia de conducir B1'."""

    def test_detecta_la_clase_despues_de_de_conducir(self):
        requisitos = analysis.RuleBasedExtractor()._extract_license(
            "Licencia de conducir B1 al dia, con al menos un año de vigencia."
        )

        self.assertEqual(len(requisitos), 1)
        self.assertEqual(requisitos[0]["value_code"], "B1")

    def test_detecta_la_clase_en_ingles(self):
        requisitos = analysis.RuleBasedExtractor()._extract_license(
            "Valid driver's license class B1 mandatory."
        )

        self.assertEqual(requisitos[0]["value_code"], "B1")

    def test_sin_clase_no_inventa_una(self):
        requisitos = analysis.RuleBasedExtractor()._extract_license(
            "Licencia de conducir al dia."
        )

        self.assertEqual(len(requisitos), 1)
        self.assertIsNone(requisitos[0]["value_code"])

    def test_detecta_licencia_para_equipo_especial(self):
        requisitos = analysis.RuleBasedExtractor()._extract_license(
            "Licencia de conducir para equipo especial D3"
        )

        self.assertEqual(requisitos[0]["value_code"], "D3")


class TestBackfillDeRequisitos(Base):
    """Los requisitos YA guardados tienen quePickup las conceptos nuevos."""

    def test_el_backfill_rellena_los_requisitos_sin_codigo(self):
        job_id = self._job()
        # Se inserta a mano (como si el requisito hubiera nacido antes de que
        # existiera el concepto 'java').
        with self.database.connection() as connection:
            connection.execute(
                """
                INSERT INTO job_analysis (
                    job_id, text_hash, extractor_version, analysis_status
                ) VALUES (?, 'hash', 'rules-1', 'complete')
                """,
                (job_id,),
            )
            analysis_id = connection.execute(
                "SELECT analysis_id FROM job_analysis WHERE job_id=?", (job_id,)
            ).fetchone()["analysis_id"]
            connection.execute(
                """
                INSERT INTO job_requirements (
                    analysis_id, category, value_code, value_text,
                    requirement_level, evidence, origin, confidence
                ) VALUES (?, 'skill', 'java', 'Java', 'required',
                          'Required: Java.', 'rule', 0.9)
                """,
                (analysis_id,),
            )

        # Sin codigo: el motor lo ignora.
        self.assertIsNone(self._codigos(job_id)["java"])

        resultado = self.repository.backfill_requirements_canonico()

        self.assertEqual(resultado["actualizados"], 1)
        self.assertEqual(self._codigos(job_id)["java"], "java")

    def test_el_backfill_es_idempotente(self):
        job_id = self._job()
        self._analisis(
            job_id,
            [
                {
                    "category": "skill",
                    "value_code": "tableau",
                    "value_text": "Tableau",
                    "requirement_level": "required",
                    "evidence": "Tableau.",
                    "origin": "rule",
                    "confidence": 0.9,
                }
            ],
        )
        # Se "des-resuelve" para simular el requisito viejo.
        with self.database.connection() as connection:
            connection.execute(
                "UPDATE job_requirements SET codigo_canonico=NULL"
            )

        self.repository.backfill_requirements_canonico()
        segundo = self.repository.backfill_requirements_canonico()

        self.assertEqual(segundo["actualizados"], 0)
        self.assertEqual(segundo["revisados"], 0)

    def test_el_backfill_no_pisa_un_codigo_ya_escrito(self):
        job_id = self._job()
        self._analisis(
            job_id,
            [
                {
                    "category": "skill",
                    "value_code": "java",
                    "value_text": "Java",
                    "requirement_level": "required",
                    "evidence": "Java.",
                    "origin": "rule",
                    "confidence": 0.9,
                }
            ],
        )
        with self.database.connection() as connection:
            connection.execute(
                "UPDATE job_requirements SET codigo_canonico='codigo-a-mano'"
            )

        self.repository.backfill_requirements_canonico()

        self.assertEqual(self._codigos(job_id)["java"], "codigo-a-mano")

    def test_el_backfill_resuelve_por_el_texto_si_no_hay_codigo(self):
        # Caso real del corpus: licencia sin clase -> value_code NULL.
        job_id = self._job()
        with self.database.connection() as connection:
            connection.execute(
                """
                INSERT INTO job_analysis (
                    job_id, text_hash, extractor_version, analysis_status
                ) VALUES (?, 'hash', 'rules-1', 'complete')
                """,
                (job_id,),
            )
            analysis_id = connection.execute(
                "SELECT analysis_id FROM job_analysis WHERE job_id=?", (job_id,)
            ).fetchone()["analysis_id"]
            connection.execute(
                """
                INSERT INTO job_requirements (
                    analysis_id, category, value_code, value_text,
                    requirement_level, evidence, origin, confidence
                ) VALUES (?, 'license', NULL, "Driver's license", 'inferred',
                          'Licencia de conducir al dia.', 'rule', 0.9)
                """,
                (analysis_id,),
            )

        self.repository.backfill_requirements_canonico()

        with self.database.connection() as connection:
            codigo = connection.execute(
                "SELECT codigo_canonico FROM job_requirements "
                "WHERE category='license'"
            ).fetchone()["codigo_canonico"]
        self.assertEqual(codigo, "licencia-conducir")


class TestReglaDeLicencias(Base):
    """Licencia: si el perfil no registra ninguna, no se puede afirmar que
    no la tenga -> 'no_verificable' (misma regla que los idiomas)."""

    def _evaluador(self):
        with self.database.connection() as connection:
            return EvaluadorPaso5(connection)

    def test_perfil_sin_licencias_no_penaliza(self):
        evaluador = self._evaluador()

        self.assertEqual(evaluador.cumple_license("licencia-conducir"), "no_verificable")

    def test_perfil_con_la_licencia_cumple(self):
        self.repository.save_candidate_profile_fact(
            "license", "b3", "Licencia de conducir B3"
        )
        evaluador = self._evaluador()

        self.assertTrue(evaluador.cumple_license("licencia-conducir"))

    def test_perfil_con_otra_licencia_no_cumple(self):
        self.repository.save_candidate_profile_fact(
            "license", "b3", "Licencia de conducir B3"
        )
        evaluador = self._evaluador()

        self.assertFalse(evaluador.cumple_license("otra-licencia"))


class TestComparacionDeIdiomaPorNivel(Base):
    """El idioma se compara por NIVEL, no solo por nombre.

    Fallo silencioso (corregido): la escala de niveles tenia las claves en
    MAYUSCULAS ("B2") y los requisitos traen el nivel en minusculas ("b2"):
    la comparacion caia en "no_verificable" y el gap de idioma NO se veia.
    """

    def _evaluador(self):
        with self.database.connection() as connection:
            return EvaluadorPaso5(connection)

    def test_el_perfil_registra_el_nivel(self):
        self.repository.save_candidate_profile_fact(
            "language", "ingles", "Ingles", qualifier="B2"
        )

        evaluador = self._evaluador()

        self.assertTrue(evaluador.cumple_language("ingles", "b2"))

    def test_un_nivel_menor_no_cumple(self):
        self.repository.save_candidate_profile_fact(
            "language", "ingles", "Ingles", qualifier="B2"
        )

        evaluador = self._evaluador()

        self.assertFalse(evaluador.cumple_language("ingles", "C1"))

    def test_un_nivel_mayor_cumple(self):
        self.repository.save_candidate_profile_fact(
            "language", "ingles", "Ingles", qualifier="C1"
        )

        evaluador = self._evaluador()

        self.assertTrue(evaluador.cumple_language("ingles", "B2"))

    def test_un_nivel_desconocido_no_se_pisa(self):
        self.repository.save_candidate_profile_fact(
            "language", "ingles", "Ingles", qualifier="B2"
        )

        evaluador = self._evaluador()

        self.assertEqual(
            evaluador.cumple_language("ingles", "avanzadito"), "no_verificable"
        )


if __name__ == "__main__":
    unittest.main()
