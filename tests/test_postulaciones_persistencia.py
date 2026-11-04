# -*- coding: utf-8 -*-
"""Tests de la persistencia de señales de postulación (migracion 018).

Recuerdan la regla de diseño: el estado del PROCESO no es una etiqueta de
aptitud. Aquí se verifica el almacenamiento, el casado con el corpus y que
**el avance nunca se degrada**.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15.db import Database  # noqa: E402
from jobpulse_v15.postulaciones import Senal  # noqa: E402
from jobpulse_v15.repository import Repository  # noqa: E402


class TestPersistenciaPostulaciones(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.initialize()
        self.repository = Repository(self.database)
        self.repository.register_platform("workday", "Workday", "api")
        self.repository.register_site(
            "workday-hpe", "workday", "HPE", "https://hpe.wd5.myworkdayjobs.com/Jobsathpe"
        )
        self._guardar_vacante(
            "workday-Support-Engineer_1211038", "Support-Engineer_1211038"
        )
        self._guardar_vacante("workday-Analyst_1212000", "Analyst_1212000")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _guardar_vacante(self, job_id, source_job_id):
        self.repository.save_job(
            {
                "job_id": job_id,
                "title": "Puesto de prueba",
                "company": "HPE",
                "country": "CR",
                "city": "Heredia",
                "posting_language": "en",
                "description_raw": "Descripcion.",
            },
            site_id="workday-hpe",
            source_job_id=source_job_id,
            source_url=(
                "https://hpe.wd5.myworkdayjobs.com/Jobsathpe/job/Heredia-Costa-Rica/"
                + source_job_id
            ),
        )

    def _senal(self, **kwargs):
        base = {
            "estado": "applied",
            "portal": "workday",
            "source_job_id": "Support-Engineer_1211038",
            "url": (
                "https://hpe.wd5.myworkdayjobs.com/Jobsathpe/job/"
                "Heredia-Costa-Rica/Support-Engineer_1211038"
            ),
            "titulo": "Support Engineer",
            "empresa": "HPE",
            "remitente": "no-reply@myworkdayjobs.com",
            "asunto": "Your application has been received",
            "fecha": "2026-11-03 10:15:00",
        }
        base.update(kwargs)
        return Senal(**base)

    # ------------------------------------------------------------ guardar
    def test_guarda_la_senal_y_la_casa_con_el_corpus(self):
        resultado = self.repository.registrar_senales_postulacion([self._senal()])

        self.assertEqual(resultado["guardadas"], 1)
        self.assertEqual(resultado["casadas"], 1)
        senales = self.repository.listar_senales_postulacion()
        self.assertEqual(len(senales), 1)
        self.assertEqual(
            senales[0]["job_id"], "workday-Support-Engineer_1211038"
        )

    def test_una_senal_sin_corpus_queda_sin_casar(self):
        resultado = self.repository.registrar_senales_postulacion(
            [
                self._senal(
                    source_job_id="Desconocido_999",
                    url=(
                        "https://hpe.wd5.myworkdayjobs.com/Jobsathpe/job/"
                        "Heredia-Costa-Rica/Desconocido_999"
                    ),
                )
            ]
        )

        self.assertEqual(resultado["casadas"], 0)
        senales = self.repository.listar_senales_postulacion()
        self.assertIsNone(senales[0]["job_id"])

    def test_el_estado_por_vacante_se_deriva(self):
        self.repository.registrar_senales_postulacion([self._senal()])

        postulaciones = self.repository.listar_postulaciones()

        self.assertEqual(len(postulaciones), 1)
        self.assertEqual(postulaciones[0]["estado"], "applied")
        self.assertEqual(
            postulaciones[0]["job_id"], "workday-Support-Engineer_1211038"
        )

    def test_el_avance_no_se_degrada(self):
        self.repository.registrar_senales_postulacion([self._senal()])
        self.repository.registrar_senales_postulacion(
            [
                self._senal(
                    estado="interview",
                    fecha="2026-11-04 09:00:00",
                    asunto="Next steps: interview",
                )
            ]
        )
        # Llega un rechazo DESPUES: el avance ya no se pierde.
        self.repository.registrar_senales_postulacion(
            [
                self._senal(
                    estado="rejected",
                    fecha="2026-11-04 18:00:00",
                    asunto="Update on your application",
                )
            ]
        )

        mapa = self.repository.estado_postulacion_por_job()

        self.assertEqual(
            mapa["workday-Support-Engineer_1211038"], "interview"
        )

    def test_es_idempotente(self):
        self.repository.registrar_senales_postulacion([self._senal()])
        resultado = self.repository.registrar_senales_postulacion([self._senal()])

        self.assertEqual(len(self.repository.listar_senales_postulacion()), 1)
        self.assertEqual(resultado["guardadas"], 1)

    def test_filtra_por_estado(self):
        self.repository.registrar_senales_postulacion([self._senal()])
        self.repository.registrar_senales_postulacion(
            [
                self._senal(
                    source_job_id="Analyst_1212000",
                    estado="interview",
                    asunto="Next steps",
                    fecha="2026-11-04 09:00:00",
                )
            ]
        )

        entrevistas = self.repository.listar_senales_postulacion(estado="interview")

        self.assertEqual(len(entrevistas), 1)
        self.assertEqual(entrevistas[0]["estado"], "interview")

    def test_acepta_dicts(self):
        self.repository.registrar_senales_postulacion(
            [
                {
                    "estado": "applied",
                    "portal": "workday",
                    "source_job_id": "Analyst_1212000",
                    "url": "",
                    "fecha": "2026-11-03 10:15:00",
                }
            ]
        )

        senales = self.repository.listar_senales_postulacion()

        self.assertEqual(len(senales), 1)
        self.assertEqual(senales[0]["job_id"], "workday-Analyst_1212000")

    def test_rechaza_un_estado_invalido(self):
        with self.assertRaises(ValueError):
            self.repository.registrar_senales_postulacion(
                [{"estado": "contratado", "portal": "workday"}]
            )


if __name__ == "__main__":
    unittest.main()
