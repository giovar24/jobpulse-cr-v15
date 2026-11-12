# -*- coding: utf-8 -*-
"""Tests del CLI de VIABILIDAD y POSTULACIONES.

Fijan el contrato de la linea de comandos (flags, salida y efectos) para que
la CLI, la UI v2 y el motor no diverjan.

Recordatorio de diseño: la viabilidad es AJUSTE TECNICO (no probabilidad de
contratar) y las postulaciones son el estado del PROCESO (un rechazo NO
dice si el perfil califica).
"""
import csv
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15.cli import main
from jobpulse_v15.db import Database
from jobpulse_v15.repository import Repository


class TestCliViabilidad(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.initialize()
        self.repository = Repository(self.database)
        self.repository.register_platform("workday", "Workday", "api")
        self.repository.register_site(
            "workday-test", "workday", "Test", "https://example.test/jobs"
        )
        self.repository.save_candidate_profile_fact("skill", "excel", "Excel")
        self.repository.save_candidate_profile_fact("skill", "sql", "SQL")
        self._guardar_vacante("job-bueno", [("skill", "excel"), ("skill", "sql")])
        self._guardar_vacante(
            "job-con-falta", [("skill", "excel"), ("skill", "python")]
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _guardar_vacante(self, job_id, skills):
        self.repository.save_job(
            {
                "job_id": job_id,
                "title": f"Puesto {job_id}",
                "company": "Example",
                "country": "CR",
                "city": "San Jose",
                "posting_language": "en",
                "description_raw": "Descripcion.",
            },
            site_id="workday-test",
            source_job_id=job_id,
        )
        requisitos = [
            {
                "category": categoria,
                "value_code": codigo,
                "value_text": codigo,
                "requirement_level": "required",
                "evidence": f"{codigo} is required.",
                "origin": "rule",
                "confidence": 0.9,
            }
            for categoria, codigo in skills
        ]
        self.repository.save_analysis(
            job_id,
            text_hash=f"hash-{job_id}",
            extractor_version="rules-1",
            analysis_status="complete",
            field_statuses={"skill": "found"},
            requirements=requisitos,
        )

    def _cli(self, *argumentos: str) -> str:
        salida = io.StringIO()
        with patch(
            "sys.argv",
            ["jobpulse-v15", "--db", str(self.database.path), *argumentos],
        ), redirect_stdout(salida):
            self.assertEqual(main(), 0)
        return salida.getvalue()

    def test_viabilidad_list_devuelve_el_ajuste_por_vacante(self):
        salida = self._cli("viabilidad", "list")

        datos = json.loads(salida)
        self.assertIn("bandas", datos)
        self.assertIn("vacantes", datos)
        self.assertEqual(len(datos["vacantes"]), 2)
        bandas = {fila["job_id"]: fila["banda"] for fila in datos["vacantes"]}
        self.assertEqual(bandas["job-bueno"], "aplicar")
        # Falta un obligatorio -> nunca "aplicar".
        self.assertEqual(bandas["job-con-falta"], "revisar")

    def test_viabilidad_list_filtra_por_banda(self):
        salida = self._cli("viabilidad", "list", "--banda", "aplicar")

        datos = json.loads(salida)
        self.assertEqual(len(datos["vacantes"]), 1)
        self.assertEqual(datos["vacantes"][0]["job_id"], "job-bueno")

    def test_viabilidad_list_escribe_csv(self):
        destino = Path(self.temp_dir.name) / "viabilidad.csv"

        self._cli(
            "viabilidad", "list", "--format", "csv", "--output", str(destino)
        )

        with destino.open(encoding="utf-8") as archivo:
            filas = list(csv.DictReader(archivo))
        self.assertEqual(len(filas), 2)
        self.assertIn("banda", filas[0])
        self.assertIn("ajuste", filas[0])


class TestCliProfileCanonico(unittest.TestCase):
    """CAPA B: `enrich profile-canonico` (simulacion y aplicacion)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.initialize()
        self.repository = Repository(self.database)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _cli(self, *argumentos: str) -> str:
        salida = io.StringIO()
        with patch(
            "sys.argv",
            ["jobpulse-v15", "--db", str(self.database.path), *argumentos],
        ), redirect_stdout(salida):
            self.assertEqual(main(), 0)
        return salida.getvalue()

    def test_dry_run_no_toca_la_base(self):
        with self.database.connection() as connection:
            connection.execute(
                """
                INSERT INTO candidate_profile_facts (
                    category, value_code, value_text, codigo_canonico
                ) VALUES ('skill', 'excel', 'Excel', NULL)
                """
            )

        salida = self._cli("enrich", "profile-canonico")
        datos = json.loads(salida)

        self.assertEqual(datos["mode"], "dry_run")
        self.assertEqual(datos["facts_sin_codigo"], 1)
        self.assertEqual(datos["updated"], 0)
        self.assertEqual(datos["pendientes"][0]["value_code"], "excel")
        # La base NO se toco.
        with self.database.connection() as connection:
            codigo = connection.execute(
                "SELECT codigo_canonico FROM candidate_profile_facts "
                "WHERE value_code='excel'"
            ).fetchone()["codigo_canonico"]
        self.assertIsNone(codigo)

    def test_apply_rellena_el_codigo(self):
        with self.database.connection() as connection:
            connection.execute(
                """
                INSERT INTO candidate_profile_facts (
                    category, value_code, value_text, codigo_canonico
                ) VALUES ('skill', 'excel', 'Excel', NULL)
                """
            )

        salida = self._cli("enrich", "profile-canonico", "--apply")
        datos = json.loads(salida)

        self.assertEqual(datos["mode"], "apply")
        self.assertEqual(datos["updated"], 1)
        with self.database.connection() as connection:
            codigo = connection.execute(
                "SELECT codigo_canonico FROM candidate_profile_facts "
                "WHERE value_code='excel'"
            ).fetchone()["codigo_canonico"]
        self.assertEqual(codigo, "excel")

    def test_es_idempotente(self):
        with self.database.connection() as connection:
            connection.execute(
                """
                INSERT INTO candidate_profile_facts (
                    category, value_code, value_text, codigo_canonico
                ) VALUES ('skill', 'excel', 'Excel', NULL)
                """
            )

        self._cli("enrich", "profile-canonico", "--apply")
        datos = json.loads(self._cli("enrich", "profile-canonico", "--apply"))

        self.assertEqual(datos["updated"], 0)
        self.assertEqual(datos["facts_sin_codigo"], 0)


class TestCliRequirementsCanonico(unittest.TestCase):
    """`enrich requirements-canonico`: los requisitos viejos con la taxonomia actual."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.initialize()
        self.repository = Repository(self.database)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _cli(self, *argumentos: str) -> str:
        salida = io.StringIO()
        with patch(
            "sys.argv",
            ["jobpulse-v15", "--db", str(self.database.path), *argumentos],
        ), redirect_stdout(salida):
            self.assertEqual(main(), 0)
        return salida.getvalue()

    def _requisito_sin_codigo(self):
        self.repository.register_platform("workday", "Workday", "api")
        self.repository.register_site(
            "workday-test", "workday", "Test", "https://example.test/jobs"
        )
        self.repository.save_job(
            {
                "job_id": "job-1",
                "title": "Puesto",
                "company": "Example",
                "country": "CR",
                "posting_language": "en",
                "description_raw": "Descripcion.",
            },
            site_id="workday-test",
            source_job_id="job-1",
        )
        with self.database.connection() as connection:
            connection.execute(
                """
                INSERT INTO job_analysis (
                    job_id, text_hash, extractor_version, analysis_status
                ) VALUES ('job-1', 'hash', 'rules-1', 'complete')
                """
            )
            analysis_id = connection.execute(
                "SELECT analysis_id FROM job_analysis WHERE job_id='job-1'"
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

    def test_dry_run_no_toca_la_base(self):
        self._requisito_sin_codigo()

        datos = json.loads(self._cli("enrich", "requirements-canonico"))

        self.assertEqual(datos["mode"], "dry_run")
        self.assertEqual(datos["requisitos_sin_codigo"], 1)
        self.assertEqual(datos["updated"], 0)
        self.assertEqual(datos["pendientes"][0]["value_code"], "java")

    def test_apply_rellena_el_codigo(self):
        self._requisito_sin_codigo()

        datos = json.loads(self._cli("enrich", "requirements-canonico", "--apply"))

        self.assertEqual(datos["mode"], "apply")
        self.assertEqual(datos["updated"], 1)
        with self.database.connection() as connection:
            codigo = connection.execute(
                "SELECT codigo_canonico FROM job_requirements "
                "WHERE value_code='java'"
            ).fetchone()["codigo_canonico"]
        self.assertEqual(codigo, "java")

    def test_es_idempotente(self):
        self._requisito_sin_codigo()
        self._cli("enrich", "requirements-canonico", "--apply")

        datos = json.loads(self._cli("enrich", "requirements-canonico", "--apply"))

        self.assertEqual(datos["updated"], 0)


class TestCliRequirementsSource(unittest.TestCase):
    """`enrich requirements-source`: re-analisis con los CAMPOS ESTRUCTURADOS.

    El texto del aviso no lo dice todo: las competencias y los idiomas que
    PIDE vienen en `jobs.skills` / `jobs.languages`. Sin integrarlos, muchos
    avisos no tienen NINGUN requisito comparable con el perfil (banda
    `sin_datos`). El comando simula por omision.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.initialize()
        self.repository = Repository(self.database)
        self.repository.register_platform("workday", "Workday", "api")
        self.repository.register_site(
            "workday-test", "workday", "Test", "https://example.test/jobs"
        )
        self.repository.save_job(
            {
                "job_id": "job-1",
                "title": "Puesto",
                "company": "Example",
                "country": "CR",
                "posting_language": "en",
                "description_raw": "Descripcion.",
            },
            site_id="workday-test",
            source_job_id="job-1",
        )
        with self.database.connection() as connection:
            connection.execute(
                "UPDATE jobs SET skills = ? WHERE job_id = 'job-1'",
                (json.dumps(["Python", "soporte a equipos Dell"]),),
            )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _cli(self, *argumentos: str) -> str:
        salida = io.StringIO()
        with patch(
            "sys.argv",
            ["jobpulse-v15", "--db", str(self.database.path), *argumentos],
        ), redirect_stdout(salida):
            self.assertEqual(main(), 0)
        return salida.getvalue()

    def _requisitos(self):
        with self.database.connection() as connection:
            return connection.execute(
                "SELECT COUNT(*) FROM job_requirements"
            ).fetchone()[0]

    def test_dry_run_no_toca_la_base(self):
        datos = json.loads(self._cli("enrich", "requirements-source"))

        self.assertEqual(datos["mode"], "dry_run")
        self.assertEqual(datos["avisos"], 1)
        # "soporte a equipos Dell" es una frase de tarea: no es competencia.
        self.assertEqual(datos["requisitos_fuente"], 1)
        self.assertEqual(self._requisitos(), 0)

    def test_apply_guards_los_requisitos_de_la_fuente(self):
        datos = json.loads(self._cli("enrich", "requirements-source", "--apply"))

        self.assertEqual(datos["mode"], "apply")
        self.assertEqual(datos["analizados"], 1)
        self.assertEqual(datos["requisitos_fuente"], 1)
        self.assertEqual(self._requisitos(), 1)
        with self.database.connection() as connection:
            fila = connection.execute(
                "SELECT value_code, codigo_canonico, origin FROM job_requirements"
            ).fetchone()
        self.assertEqual(fila["value_code"], "python")
        self.assertEqual(fila["codigo_canonico"], "python")
        self.assertEqual(fila["origin"], "source_field")

    def test_apply_es_idempotente(self):
        self._cli("enrich", "requirements-source", "--apply")

        datos = json.loads(self._cli("enrich", "requirements-source", "--apply"))

        self.assertEqual(datos["requisitos_fuente"], 1)
        self.assertEqual(self._requisitos(), 1)

    def test_lo_que_no_resuelve_va_a_la_cola_de_la_taxonomia(self):
        with self.database.connection() as connection:
            connection.execute(
                "UPDATE jobs SET skills = ? WHERE job_id = 'job-1'",
                (json.dumps(["Zabbix"]),),
            )

        self._cli("enrich", "requirements-source", "--apply")

        with self.database.connection() as connection:
            fila = connection.execute(
                "SELECT veces FROM concepto_no_normalizado WHERE texto='zabbix'"
            ).fetchone()
        self.assertIsNotNone(fila)


class TestCliPostulaciones(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.initialize()
        self.repository = Repository(self.database)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _cli(self, *argumentos: str) -> str:
        salida = io.StringIO()
        with patch(
            "sys.argv",
            ["jobpulse-v15", "--db", str(self.database.path), *argumentos],
        ), redirect_stdout(salida):
            self.assertEqual(main(), 0)
        return salida.getvalue()

    def test_postulaciones_list_sin_datos(self):
        salida = self._cli("postulaciones", "list")

        self.assertEqual(json.loads(salida), [])

    def test_el_cli_avisa_cuando_aplica_migraciones(self):
        # Una migracion NUNCA debe aplicarse en silencio sobre la base real:
        # el CLI lo dice explicitamente.
        destino = Path(self.temp_dir.name) / "nueva.db"
        salida = io.StringIO()
        with patch(
            "sys.argv",
            ["jobpulse-v15", "--db", str(destino), "postulaciones", "list"],
        ), redirect_stdout(salida):
            self.assertEqual(main(), 0)

        self.assertIn("[esquema]", salida.getvalue())
        self.assertIn("migraciones", salida.getvalue())

    def test_el_cli_no_avisa_si_no_hay_migraciones_pendientes(self):
        self.database.initialize()
        salida = self._cli("postulaciones", "list")

        self.assertNotIn("[esquema]", salida)

    def test_postulaciones_correo_sin_credencial_no_falla(self):
        salida = self._cli("postulaciones", "correo")

        self.assertIn("credencial", salida.lower())

    def test_postulaciones_correo_guarda_lo_que_Clasifica(self):
        senales = [
            {
                "estado": "applied",
                "portal": "workday",
                "source_job_id": "X_123",
                "url": "",
                "fecha": "2026-11-03 10:00:00",
                "remitente": "no-reply@myworkdayjobs.com",
                "asunto": "Your application has been received",
            }
        ]
        with patch(
            "jobpulse_v15.correo_postulaciones.recolectar_senales",
            return_value=senales,
        ), patch(
            "jobpulse_v15.cli.credencial",
            return_value={"usuario": "persona@example.com", "password": "app"},
        ):
            salida = self._cli("postulaciones", "correo", "--apply")

        self.assertIn("Senales guardadas", salida)
        self.assertEqual(len(self.repository.listar_senales_postulacion()), 1)

    def test_postulaciones_correo_dry_run_no_guarda(self):
        senales = [
            {
                "estado": "applied",
                "portal": "workday",
                "source_job_id": "X_123",
                "url": "",
                "fecha": "2026-11-03 10:00:00",
            }
        ]
        with patch(
            "jobpulse_v15.correo_postulaciones.recolectar_senales",
            return_value=senales,
        ), patch(
            "jobpulse_v15.cli.credencial",
            return_value={"usuario": "persona@example.com", "password": "app"},
        ):
            salida = self._cli("postulaciones", "correo")

        self.assertIn("dry-run", salida)
        self.assertEqual(self.repository.listar_senales_postulacion(), [])


if __name__ == "__main__":
    unittest.main()
