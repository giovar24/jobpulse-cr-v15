# -*- coding: utf-8 -*-
"""Tests de las DECISIONES FIRMADAS del Paso 5 (tabla `job_match_decision`).

Patron: tempfile + Database + sqlite3 directo (no toca la BD real).

Que se comprueba aqui:

* el ancla de la decision (sha256 del TEXTO del aviso): si el texto cambia,
  la firma deja de aplicar;
* el motor aplica la decision SOLO cuando el NO pudo decidir
  (`educacion_no_confirmada`): "bloqueo_real" -> `descartada`, "no_bloqueo" ->
  `revisar_a_mano`, "dudoso" -> sin cambio;
* una decision NUNCA pisa un veredicto que el motor ya dio;
* la hoja de firma (JSON) solo aplica las decisiones cuyo texto sigue igual.
"""
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15 import decisiones
from jobpulse_v15 import matching
from jobpulse_v15.db import Database


def _crear_base(tmpdir: str) -> sqlite3.Connection:
    db = Database(Path(tmpdir) / "test.db")
    db.initialize()
    connection = sqlite3.connect(db.path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _insertar_fact(connection: sqlite3.Connection, code: str, canon: str) -> None:
    connection.execute(
        """
        INSERT INTO candidate_profile_facts
            (category, value_code, value_text, codigo_canonico)
        VALUES ('education', ?, ?, ?)
        """,
        (code, code, canon),
    )


def _insertar_job(
    connection: sqlite3.Connection, job_id: str, descripcion: str
) -> None:
    connection.execute(
        """
        INSERT INTO jobs (job_id, title, company, description_raw, requirements_raw,
                          posting_language)
        VALUES (?, 'Puesto de prueba', 'Acme CR', ?, NULL, 'undetermined')
        """,
        (job_id, descripcion),
    )
    connection.execute(
        """
        INSERT INTO job_analysis
            (job_id, text_hash, extractor_version, analysis_status, is_current)
        VALUES (?, 'hash-test', 'test-v1', 'complete', 1)
        """,
        (job_id,),
    )
    analysis_id = connection.execute(
        "SELECT analysis_id FROM job_analysis WHERE job_id = ?", (job_id,)
    ).fetchone()["analysis_id"]
    connection.execute(
        """
        INSERT INTO job_requirements
            (analysis_id, category, value_code, value_text, requirement_level,
             codigo_canonico, origin)
        VALUES (?, 'education', 'bachelor', 'Bachelor', 'required',
                'educacion-universitaria', 'manual')
        """,
        (analysis_id,),
    )


ALTERNATIVA = "Minimum Bachelor's degree or its equivalent. Strong MS Office skills."


class TestAnclaDeLaDecision(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.connection = _crear_base(self.tmpdir.name)

    def tearDown(self):
        self.connection.close()
        self.tmpdir.cleanup()

    def test_el_texto_es_el_mismo_que_lee_el_motor(self):
        _insertar_job(self.connection, "job-1", ALTERNATIVA)
        self.connection.commit()
        evaluador = matching.EvaluadorPaso5(self.connection)
        self.assertEqual(evaluador.textos_por_job["job-1"], ALTERNATIVA)
        self.assertEqual(
            decisiones.hash_texto(evaluador.textos_por_job["job-1"]),
            decisiones.hash_aviso(None, ALTERNATIVA),
        )

    def test_hash_aviso_une_requirements_y_description(self):
        self.assertEqual(
            decisiones.texto_aviso("req", "desc"), "req\ndesc"
        )
        self.assertEqual(
            decisiones.texto_aviso(None, "desc"), "desc"
        )
        self.assertEqual(
            decisiones.texto_aviso("", ""), ""
        )

    def test_la_decision_no_aplica_si_el_texto_cambio(self):
        _insertar_job(self.connection, "job-1", ALTERNATIVA)
        self.connection.commit()
        texto_hash = decisiones.hash_aviso(None, ALTERNATIVA)
        decisiones.guardar_decision(
            self.connection,
            job_id="job-1",
            dimension=decisiones.DIMENSION_EDUCACION,
            veredicto=decisiones.VEREDICTO_BLOQUEO_REAL,
            criterio="firma sobre el texto original",
            revisor="Revisor",
            fecha="2026-11-08",
            text_hash=texto_hash,
        )
        self.connection.commit()
        # El aviso se re-raspa: cambia el texto.
        self.connection.execute(
            "UPDATE jobs SET description_raw=? WHERE job_id=?",
            ("Otro texto totalmente distinto.", "job-1"),
        )
        self.connection.commit()
        evaluador = matching.EvaluadorPaso5(self.connection)
        self.assertIsNone(evaluador.decision_educacion("job-1"))
        resultado = evaluador.evaluar_job("job-1")
        # La firma NO se aplica: el caso vuelve aRevision manual (el motor
        # vuelve a no poder decidir con el texto nuevo).
        self.assertNotEqual(resultado.estado, matching.ESTADO_DESCARTADA)
        self.assertEqual(resultado.estado, matching.ESTADO_REVISAR)
        self.assertNotEqual(resultado.motivo, matching.MOTIVO_BLOQUEANTE)


class TestLaDecisionEnElMotor(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.connection = _crear_base(self.tmpdir.name)
        _insertar_fact(self.connection, "bachiller", "educacion-secundaria")

    def tearDown(self):
        self.connection.close()
        self.tmpdir.cleanup()

    def _firmar(self, job_id: str, veredicto: str) -> None:
        decisiones.guardar_decision(
            self.connection,
            job_id=job_id,
            dimension=decisiones.DIMENSION_EDUCACION,
            veredicto=veredicto,
            criterio="criterio de prueba",
            revisor="Revisor",
            fecha="2026-11-08",
            text_hash=decisiones.hash_aviso(None, ALTERNATIVA),
        )
        self.connection.commit()

    def test_sin_firma_el_motor_deja_el_caso_para_revision(self):
        _insertar_job(self.connection, "job-1", ALTERNATIVA)
        self.connection.commit()
        evaluador = matching.EvaluadorPaso5(self.connection)
        resultado = evaluador.evaluar_job("job-1")
        self.assertEqual(resultado.estado, matching.ESTADO_REVISAR)
        self.assertEqual(resultado.motivo, matching.MOTIVO_EDUCACION_NO_CONFIRMADA)
        self.assertEqual(resultado.nc_count, 1)

    def test_bloqueo_real_descarta_la_vacante(self):
        _insertar_job(self.connection, "job-1", ALTERNATIVA)
        self.connection.commit()
        self._firmar("job-1", decisiones.VEREDICTO_BLOQUEO_REAL)
        evaluador = matching.EvaluadorPaso5(self.connection)
        resultado = evaluador.evaluar_job("job-1")
        self.assertEqual(resultado.estado, matching.ESTADO_DESCARTADA)
        self.assertEqual(resultado.motivo, matching.MOTIVO_BLOQUEANTE)

    def test_no_bloqueo_deja_la_vacante_para_revision_pero_no_confirmada(self):
        _insertar_job(self.connection, "job-1", ALTERNATIVA)
        self.connection.commit()
        self._firmar("job-1", decisiones.VEREDICTO_NO_BLOQUEO)
        evaluador = matching.EvaluadorPaso5(self.connection)
        resultado = evaluador.evaluar_job("job-1")
        self.assertEqual(resultado.estado, matching.ESTADO_REVISAR)
        self.assertEqual(resultado.motivo, matching.MOTIVO_EDUCACION_NO_CUMPLE)
        self.assertEqual(resultado.nc_count, 0)

    def test_dudoso_no_cambia_nada(self):
        _insertar_job(self.connection, "job-1", ALTERNATIVA)
        self.connection.commit()
        self._firmar("job-1", decisiones.VEREDICTO_DUDOSO)
        evaluador = matching.EvaluadorPaso5(self.connection)
        resultado = evaluador.evaluar_job("job-1")
        self.assertEqual(resultado.estado, matching.ESTADO_REVISAR)
        self.assertEqual(resultado.motivo, matching.MOTIVO_EDUCACION_NO_CONFIRMADA)
        self.assertEqual(resultado.nc_count, 1)

    def test_la_decision_no_pisa_un_veredicto_que_el_motor_ya_dio(self):
        # El texto CONFIRMA el titulo: el motor ya descarta, la decision
        # "no_bloqueo" NO puede rescatarlo.
        texto = "We are looking for professionals. Bachelor's Degree in Accounting required."
        _insertar_job(self.connection, "job-2", texto)
        self.connection.commit()
        decisiones.guardar_decision(
            self.connection,
            job_id="job-2",
            dimension=decisiones.DIMENSION_EDUCACION,
            veredicto=decisiones.VEREDICTO_NO_BLOQUEO,
            criterio="criterio de prueba",
            revisor="Revisor",
            fecha="2026-11-08",
            text_hash=decisiones.hash_aviso(None, texto),
        )
        self.connection.commit()
        evaluador = matching.EvaluadorPaso5(self.connection)
        resultado = evaluador.evaluar_job("job-2")
        self.assertEqual(resultado.estado, matching.ESTADO_DESCARTADA)
        self.assertEqual(resultado.motivo, matching.MOTIVO_BLOQUEANTE)

    def test_la_decision_no_pisa_un_perfil_que_ya_cumple(self):
        _insertar_fact(self.connection, "licenciatura", "educacion-universitaria")
        _insertar_job(self.connection, "job-3", ALTERNATIVA)
        self.connection.commit()
        self._firmar("job-3", decisiones.VEREDICTO_BLOQUEO_REAL)
        evaluador = matching.EvaluadorPaso5(self.connection)
        resultado = evaluador.evaluar_job("job-3")
        self.assertNotEqual(resultado.estado, matching.ESTADO_DESCARTADA)


class TestPersistenciaDeDecisiones(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.connection = _crear_base(self.tmpdir.name)
        _insertar_job(self.connection, "job-1", ALTERNATIVA)
        self.connection.commit()

    def tearDown(self):
        self.connection.close()
        self.tmpdir.cleanup()

    def test_guardar_y_listar(self):
        decisiones.guardar_decision(
            self.connection,
            job_id="job-1",
            dimension=decisiones.DIMENSION_EDUCACION,
            veredicto=decisiones.VEREDICTO_NO_BLOQUEO,
            criterio="el texto ofrece via alternativa",
            revisor="Revisor",
            fecha="2026-11-08",
            text_hash=decisiones.hash_aviso(None, ALTERNATIVA),
        )
        self.connection.commit()
        filas = decisiones.listar_decisiones(self.connection)
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["job_id"], "job-1")
        self.assertEqual(filas[0]["veredicto"], decisiones.VEREDICTO_NO_BLOQUEO)
        vigente = decisiones.decision_vigente(
            self.connection, "job-1", decisiones.DIMENSION_EDUCACION
        )
        self.assertIsNotNone(vigente)
        self.assertEqual(vigente["revisor"], "Revisor")

    def test_firmar_dos_veces_el_mismo_texto_es_un_update(self):
        text_hash = decisiones.hash_aviso(None, ALTERNATIVA)
        for veredicto in (
            decisiones.VEREDICTO_NO_BLOQUEO,
            decisiones.VEREDICTO_BLOQUEO_REAL,
        ):
            decisiones.guardar_decision(
                self.connection,
                job_id="job-1",
                dimension=decisiones.DIMENSION_EDUCACION,
                veredicto=veredicto,
                criterio="criterio %s" % veredicto,
                revisor="Revisor",
                fecha="2026-11-08",
                text_hash=text_hash,
            )
        self.connection.commit()
        filas = decisiones.listar_decisiones(self.connection)
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["veredicto"], decisiones.VEREDICTO_BLOQUEO_REAL)

    def test_validaciones(self):
        with self.assertRaises(ValueError):
            decisiones.validar_dimension("otra")
        with self.assertRaises(ValueError):
            decisiones.validar_veredicto("quizá")
        with self.assertRaises(ValueError):
            decisiones.guardar_decision(
                self.connection,
                job_id="job-1",
                dimension=decisiones.DIMENSION_EDUCACION,
                veredicto=decisiones.VEREDICTO_NO_BLOQUEO,
                criterio="   ",
                revisor="Revisor",
                fecha="2026-11-08",
                text_hash="x",
            )


class TestHojaDeFirma(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.connection = _crear_base(self.tmpdir.name)
        _insertar_job(self.connection, "job-1", ALTERNATIVA)
        self.connection.commit()

    def tearDown(self):
        self.connection.close()
        self.tmpdir.cleanup()

    def _firma(self, texto_hash: str) -> dict:
        return {
            "formato": decisiones.FORMATO_FIRMA,
            "dimension": decisiones.DIMENSION_EDUCACION,
            "revisor": "Revisor",
            "fecha": "2026-11-08",
            "decisiones": [
                {
                    "job_id": "job-1",
                    "veredicto": decisiones.VEREDICTO_NO_BLOQUEO,
                    "criterio": "el texto ofrece via alternativa",
                    "text_hash": texto_hash,
                }
            ],
        }

    def test_aplicar_la_firma(self):
        firma = self._firma(decisiones.hash_aviso(None, ALTERNATIVA))
        resultado = decisiones.aplicar_firma(self.connection, firma)
        self.connection.commit()
        self.assertEqual(resultado["aplicadas"], ["job-1"])
        self.assertEqual(resultado["texto_cambiado"], [])

    def test_la_firma_no_se_aplica_si_el_texto_cambio(self):
        firma = self._firma("hash-de-un-texto-que-no-es-este")
        resultado = decisiones.aplicar_firma(self.connection, firma)
        self.connection.commit()
        self.assertEqual(resultado["aplicadas"], [])
        self.assertEqual(resultado["texto_cambiado"], ["job-1"])
        self.assertEqual(decisiones.listar_decisiones(self.connection), [])

    def test_la_firma_ignora_avisos_que_no_existen(self):
        firma = self._firma(decisiones.hash_aviso(None, ALTERNATIVA))
        firma["decisiones"].append(
            {
                "job_id": "job-inexistente",
                "veredicto": decisiones.VEREDICTO_NO_BLOQUEO,
                "criterio": "no existe",
                "text_hash": "x",
            }
        )
        resultado = decisiones.aplicar_firma(self.connection, firma)
        self.connection.commit()
        self.assertEqual(resultado["desconocidas"], ["job-inexistente"])

    def test_cargar_firma_rechaza_un_json_incompleto(self):
        ruta = Path(self.tmpdir.name) / "firma.json"
        ruta.write_text(
            json.dumps({"dimension": "educacion", "revisor": "X", "fecha": "2026-11-08"}),
            encoding="utf-8",
        )
        with self.assertRaises(ValueError):
            decisiones.cargar_firma(str(ruta))


class TestCitasLiteralesDeLaFirma(unittest.TestCase):
    """Lo que va entre «...» en el criterio es una CITA LITERAL del aviso.

    `verificar_evidencia.py` lo comprueba; la FIRMA lo comprueba tambien (y
    falla al firmar, no tres etapas despues). El caso que lo disparo: un
    criterio que nombraba un escalon de la escalera («estudiante avanzado»)
    como si fuera texto del aviso -> la firma se aceptaba y la evidencia
    fallaba al verificarse.
    """

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.connection = _crear_base(self.tmpdir.name)
        _insertar_job(self.connection, "job-1", ALTERNATIVA)
        self.connection.commit()

    def tearDown(self):
        self.connection.close()
        self.tmpdir.cleanup()

    def _firma(self, criterio: str) -> dict:
        return {
            "formato": decisiones.FORMATO_FIRMA,
            "dimension": decisiones.DIMENSION_EDUCACION,
            "revisor": "Revisor",
            "fecha": "2026-11-08",
            "decisiones": [
                {
                    "job_id": "job-1",
                    "veredicto": decisiones.VEREDICTO_BLOQUEO_REAL,
                    "criterio": criterio,
                    "text_hash": decisiones.hash_aviso(None, ALTERNATIVA),
                }
            ],
        }

    def test_una_cita_literal_se_aplica(self):
        firma = self._firma(
            "El aviso pide «Bachelor's degree or its equivalent» y bloquea."
        )
        resultado = decisiones.aplicar_firma(self.connection, firma)
        self.connection.commit()
        self.assertEqual(resultado["aplicadas"], ["job-1"])
        self.assertEqual(resultado["citas_no_literal"], [])

    def test_una_cita_que_no_es_del_aviso_rechaza_la_firma(self):
        firma = self._firma(
            "El aviso pide «Bachelor's degree» y es el escalon «estudiante avanzado»."
        )
        resultado = decisiones.aplicar_firma(self.connection, firma)
        self.connection.commit()
        self.assertEqual(resultado["aplicadas"], [])
        self.assertEqual(len(resultado["citas_no_literal"]), 1)
        self.assertEqual(resultado["citas_no_literal"][0]["job_id"], "job-1")
        self.assertIn("estudiante avanzado", resultado["citas_no_literal"][0]["citas"])
        # Y NO se escribe nada en la base.
        self.assertEqual(decisiones.listar_decisiones(self.connection), [])

    def test_un_criterio_sin_citas_se_aplica_normalmente(self):
        firma = self._firma("El titulo no bloquea: el texto ofrece via alternativa.")
        resultado = decisiones.aplicar_firma(self.connection, firma)
        self.connection.commit()
        self.assertEqual(resultado["aplicadas"], ["job-1"])
        self.assertEqual(resultado["citas_no_literal"], [])

    def test_validar_citas_devuelve_las_problematicas(self):
        texto = "Se requiere Bachelor's degree or equivalent experience."
        self.assertEqual(
            decisiones.validar_citas("pide «Bachelor's degree»", texto), []
        )
        self.assertEqual(
            decisiones.validar_citas("pide «estudiante avanzado»", texto),
            ["estudiante avanzado"],
        )


class TestCliDecision(unittest.TestCase):
    """El CLI expone la firma: `decision list` y `decision sign --file`."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test.db"
        self.database = Database(self.db_path)
        self.database.initialize()
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute(
            """INSERT INTO jobs (job_id, title, company, description_raw,
                                  posting_language)
               VALUES ('job-1', 'Puesto', 'Acme', ?, 'undetermined')""",
            (ALTERNATIVA,),
        )
        connection.commit()
        connection.close()

    def tearDown(self):
        self.tmpdir.cleanup()

    def _cli(self, *argumentos: str) -> str:
        import io
        from contextlib import redirect_stdout
        from unittest.mock import patch

        from jobpulse_v15.cli import main

        salida = io.StringIO()
        with patch(
            "sys.argv",
            ["jobpulse-v15", "--db", str(self.db_path), *argumentos],
        ), redirect_stdout(salida):
            self.assertEqual(main(), 0)
        return salida.getvalue()

    def test_decision_list_sin_firmas(self):
        salida = self._cli("decision", "list")
        self.assertIn("No hay decisiones firmadas", salida)

    def test_decision_sign_registra_la_hoja(self):
        ruta = Path(self.tmpdir.name) / "firma.json"
        ruta.write_text(
            json.dumps(
                {
                    "formato": 1,
                    "dimension": "educacion",
                    "revisor": "Revisor",
                    "fecha": "2026-11-08",
                    "decisiones": [
                        {
                            "job_id": "job-1",
                            "veredicto": "no_bloqueo",
                            "criterio": "el texto ofrece via alternativa",
                            "text_hash": decisiones.hash_aviso(None, ALTERNATIVA),
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        salida = self._cli("decision", "sign", "--file", str(ruta))
        self.assertIn("job-1", salida)
        listado = self._cli("decision", "list")
        self.assertIn("no_bloqueo", listado)
        self.assertIn("Revisor", listado)

    def test_decision_sign_dry_run_no_escribe(self):
        ruta = Path(self.tmpdir.name) / "firma.json"
        ruta.write_text(
            json.dumps(
                {
                    "formato": 1,
                    "dimension": "educacion",
                    "revisor": "Revisor",
                    "fecha": "2026-11-08",
                    "decisiones": [
                        {
                            "job_id": "job-1",
                            "veredicto": "no_bloqueo",
                            "criterio": "el texto ofrece via alternativa",
                            "text_hash": decisiones.hash_aviso(None, ALTERNATIVA),
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        salida = self._cli("decision", "sign", "--file", str(ruta), "--dry-run")
        self.assertIn('"aplicado": false', salida)
        self.assertIn("No hay decisiones firmadas", self._cli("decision", "list"))


if __name__ == "__main__":
    unittest.main()
