# -*- coding: utf-8 -*-
"""Tests del normalizador de codigos canonicos (`jobpulse_v15.conceptos`).

Por que existe: la migracion 010 relleno `job_requirements.codigo_canonico`
como backfill ONE-TIME. Nada rellenaba la columna al INSERTAR, asi que todo
requisito nuevo quedaba en NULL y el Paso 5 lo descartaba
(`AND codigo_canonico IS NOT NULL`) -> la vacante se evaluaba con 0
requisitos y caia en `sin_requisitos`.

Patron: tempfile + Database + Repository (no toca la BD real).
"""

import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15 import matching
from jobpulse_v15.db import Database
from jobpulse_v15.repository import Repository


def _requisito(category, value_code, level="ambiguous", evidence="Evidencia."):
    return {
        "category": category,
        "value_code": value_code,
        "value_text": value_code,
        "requirement_level": level,
        "evidence": evidence,
        "origin": "rule",
        "confidence": 0.9,
    }


class TestConceptos(unittest.TestCase):
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
        self.repository.save_job(
            {
                "job_id": "job-1",
                "title": "Analyst",
                "company": "Intel",
                "country": "CR",
                "description_raw": "Excel avanzado y Licenciatura en Ingenieria.",
            },
            site_id="intel-cr",
            source_job_id="J-1",
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def _codigos(self, job_id="job-1"):
        with closing(sqlite3.connect(self.database.path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT category, value_code, codigo_canonico
                FROM job_requirements q
                JOIN job_analysis a ON a.analysis_id = q.analysis_id
                WHERE a.job_id = ? AND a.is_current = 1
                """,
                (job_id,),
            ).fetchall()
        return {r["value_code"]: r["codigo_canonico"] for r in rows}

    def test_save_analysis_resuelve_el_codigo_canonico(self):
        self.repository.save_analysis(
            "job-1",
            text_hash="hash-1",
            extractor_version="rules-1",
            analysis_status="partial",
            field_statuses={
                "language": "not_mentioned",
                "education": "found",
                "license": "not_mentioned",
                "experience": "not_mentioned",
                "skill": "found",
            },
            requirements=[
                _requisito("education", "university_degree", level="inferred"),
                _requisito("skill", "excel", level="required"),
            ],
        )
        codigos = self._codigos()
        self.assertEqual(codigos["university_degree"], "educacion-universitaria")
        self.assertEqual(codigos["excel"], "excel")

    def test_variante_sin_concepto_queda_null_y_se_encola(self):
        self.repository.save_analysis(
            "job-1",
            text_hash="hash-1",
            extractor_version="rules-1",
            analysis_status="partial",
            field_statuses={
                "language": "not_mentioned",
                "education": "not_mentioned",
                "license": "not_mentioned",
                "experience": "not_mentioned",
                "skill": "ambiguous",
            },
            requirements=[_requisito("skill", "autocad")],
        )
        self.assertIsNone(self._codigos()["autocad"])
        with closing(sqlite3.connect(self.database.path)) as connection:
            cola = connection.execute(
                """
                SELECT veces FROM concepto_no_normalizado
                WHERE categoria = 'skill' AND texto = 'autocad' AND origen = 'oferta'
                """
            ).fetchone()
        self.assertIsNotNone(cola)
        self.assertEqual(cola[0], 1)

    def test_la_cola_acumula_cada_aparicion(self):
        for _ in range(2):
            self.repository.save_analysis(
                "job-1",
                text_hash="hash-%d" % _,
                extractor_version="rules-1",
                analysis_status="partial",
                field_statuses={
                    "language": "not_mentioned",
                    "education": "not_mentioned",
                    "license": "not_mentioned",
                    "experience": "not_mentioned",
                    "skill": "ambiguous",
                },
                requirements=[_requisito("skill", "autocad")],
            )
        with closing(sqlite3.connect(self.database.path)) as connection:
            veces = connection.execute(
                """
                SELECT veces FROM concepto_no_normalizado
                WHERE categoria = 'skill' AND texto = 'autocad' AND origen = 'oferta'
                """
            ).fetchone()[0]
        self.assertEqual(veces, 2)

    def test_no_usa_conceptos_inactivos(self):
        with closing(sqlite3.connect(self.database.path)) as connection:
            connection.execute(
                "UPDATE concepto SET activa = 0 WHERE variante = 'excel'"
            )
            connection.commit()
        self.repository.save_analysis(
            "job-1",
            text_hash="hash-1",
            extractor_version="rules-1",
            analysis_status="partial",
            field_statuses={
                "language": "not_mentioned",
                "education": "not_mentioned",
                "license": "not_mentioned",
                "experience": "not_mentioned",
                "skill": "ambiguous",
            },
            requirements=[_requisito("skill", "excel")],
        )
        self.assertIsNone(self._codigos()["excel"])

    def test_el_paso5_ve_el_requisito_guardado(self):
        """Regresion: requisito nuevo con codigo canonico debe contar en el Paso 5."""
        self.repository.save_analysis(
            "job-1",
            text_hash="hash-1",
            extractor_version="rules-1",
            analysis_status="partial",
            field_statuses={
                "language": "not_mentioned",
                "education": "not_mentioned",
                "license": "not_mentioned",
                "experience": "not_mentioned",
                "skill": "found",
            },
            requirements=[_requisito("skill", "excel", level="required")],
        )
        with closing(sqlite3.connect(self.database.path)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute(
                """
                INSERT INTO candidate_profile_facts
                    (category, value_code, value_text, codigo_canonico)
                VALUES ('skill', 'excel', 'excel', 'excel')
                """
            )
            connection.commit()
            resultado = matching.EvaluadorPaso5(connection).evaluar_job("job-1")
        self.assertEqual(resultado.total_req, 1)
        self.assertNotEqual(resultado.estado, matching.ESTADO_SIN_REQUISITOS)


if __name__ == "__main__":
    unittest.main()
