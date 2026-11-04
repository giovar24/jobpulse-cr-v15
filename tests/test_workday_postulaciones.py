# -*- coding: utf-8 -*-
"""Tests del parser de "Mis postulaciones" de Workday (sin red).

El parser es PURO: se prueba con HTML/JSON sinteticos. La red (CDP) solo
se valida en vivo, con el navegador del usuario.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15.postulaciones import (  # noqa: E402
    ESTADO_APPLIED,
    ESTADO_INTERVIEW,
    ESTADO_OFFER,
    ESTADO_RECRUITER,
    ESTADO_REJECTED,
    ESTADO_WITHDRAWN,
)
from jobpulse_v15.workday_postulaciones import (  # noqa: E402
    a_senales,
    mapear_estado,
    parsear_html_aplicaciones,
    parsear_json_aplicaciones,
    patrones_candidato,
    referencia_de_url_workday,
)

HTML_APLICACIONES = """
<html><body>
  <div data-automation-id="application-table-row">
    <a data-automation-id="job-posting-link"
       href="https://hpe.wd5.myworkdayjobs.com/Jobsathpe/job/Heredia-Costa-Rica/Support-Engineer_1211038">
       Support Engineer
    </a>
    <div data-automation-id="application-status">Applied</div>
    <div data-automation-id="application-company">HPE</div>
  </div>
  <div data-automation-id="application-table-row">
    <a data-automation-id="job-posting-link"
       href="https://hpe.wd5.myworkdayjobs.com/Jobsathpe/job/Heredia-Costa-Rica/Analyst_1212000">
       Data Analyst
    </a>
    <div data-automation-id="application-status">Interview</div>
  </div>
</body></html>
"""

JSON_APLICACIONES = {
    "appliedJobs": [
        {
            "title": "Support Engineer",
            "companyName": "HPE",
            "applicationStatus": "APPLIED",
            "dateApplied": "2026-10-20",
            "jobPostingInfo": {
                "jobReqId": "Support-Engineer_1211038",
                "externalPath": "/job/Heredia-Costa-Rica/Support-Engineer_1211038",
                "title": "Support Engineer",
                "companyName": "HPE",
            },
        },
        {
            "title": "Data Analyst",
            "companyName": "HPE",
            "applicationStatus": "INTERVIEW",
            "jobPostingInfo": {
                "jobReqId": "Analyst_1212000",
                "externalPath": "/job/Heredia-Costa-Rica/Analyst_1212000",
            },
        },
    ]
}


class TestMapeoDeEstados(unittest.TestCase):
    def test_estados_conocidos(self):
        self.assertEqual(mapear_estado("APPLIED"), ESTADO_APPLIED)
        self.assertEqual(mapear_estado("SCREENING"), ESTADO_RECRUITER)
        self.assertEqual(mapear_estado("INTERVIEW"), ESTADO_INTERVIEW)
        self.assertEqual(mapear_estado("OFFER"), ESTADO_OFFER)
        self.assertEqual(mapear_estado("REJECTED"), ESTADO_REJECTED)
        self.assertEqual(mapear_estado("WITHDRAWN"), ESTADO_WITHDRAWN)

    def test_variantes_de_texto(self):
        self.assertEqual(mapear_estado("In Progress"), ESTADO_APPLIED)
        self.assertEqual(mapear_estado("PHONE_SCREEN"), ESTADO_INTERVIEW)
        self.assertEqual(mapear_estado("not-selected"), ESTADO_REJECTED)

    def test_estado_desconocido(self):
        self.assertEqual(mapear_estado("WAT"), "")


class TestReferencias(unittest.TestCase):
    def test_referencia_de_la_url(self):
        self.assertEqual(
            referencia_de_url_workday(
                "https://hpe.wd5.myworkdayjobs.com/Jobsathpe/job/"
                "Heredia-Costa-Rica/Support-Engineer_1211038"
            ),
            "Support-Engineer_1211038",
        )

    def test_url_vacia(self):
        self.assertEqual(referencia_de_url_workday(""), "")


class TestParserJSON(unittest.TestCase):
    def test_extrae_las_aplicaciones(self):
        aplicaciones = parsear_json_aplicaciones(JSON_APLICACIONES)

        self.assertEqual(len(aplicaciones), 2)
        self.assertEqual(aplicaciones[0].estado, ESTADO_APPLIED)
        self.assertEqual(aplicaciones[0].source_job_id, "Support-Engineer_1211038")
        self.assertEqual(aplicaciones[0].empresa, "HPE")
        self.assertEqual(aplicaciones[1].estado, ESTADO_INTERVIEW)

    def test_ignora_lo_que_no_es_postulacion(self):
        aplicaciones = parsear_json_aplicaciones(
            {"total": 0, "appliedJobs": [], "facets": [{"name": "x"}]}
        )

        self.assertEqual(aplicaciones, [])

    def test_texto_json_invalido(self):
        self.assertEqual(parsear_json_aplicaciones("no es json"), [])

    def test_las_senales_no_cargan_el_cuerpo(self):
        senales = a_senales(parsear_json_aplicaciones(JSON_APLICACIONES))

        self.assertEqual(len(senales), 2)
        self.assertEqual(senales[0].portal, "workday")
        self.assertFalse(hasattr(senales[0], "cuerpo"))


class TestParserHTML(unittest.TestCase):
    def test_extrae_las_filas(self):
        aplicaciones = parsear_html_aplicaciones(HTML_APLICACIONES)

        self.assertEqual(len(aplicaciones), 2)
        self.assertEqual(aplicaciones[0].estado, ESTADO_APPLIED)
        self.assertEqual(
            aplicaciones[0].source_job_id, "Support-Engineer_1211038"
        )
        self.assertEqual(aplicaciones[0].titulo, "Support Engineer")
        self.assertEqual(aplicaciones[1].estado, ESTADO_INTERVIEW)

    def test_html_vacio(self):
        self.assertEqual(parsear_html_aplicaciones(""), [])


class TestPatronesDeURL(unittest.TestCase):
    def test_deriva_las_urls_del_portal(self):
        patrones = patrones_candidato(
            "https://hpe.wd5.myworkdayjobs.com/Jobsathpe"
        )

        self.assertIn(
            "https://hpe.wd5.myworkdayjobs.com/Jobsathpe/candidate", patrones
        )
        self.assertIn("https://hpe.wd5.myworkdayjobs.com/candidate", patrones)

    def test_sin_url_no_hay_patrones(self):
        self.assertEqual(patrones_candidato(""), [])


if __name__ == "__main__":
    unittest.main()
