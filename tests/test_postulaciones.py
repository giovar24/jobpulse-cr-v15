# -*- coding: utf-8 -*-
"""Tests del nucleo de postulaciones (clasificacion de senales, sin red)."""
import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15.postulaciones import (  # noqa: E402
    ESTADO_APPLIED,
    ESTADO_INTERVIEW,
    ESTADO_OFFER,
    ESTADO_RECRUITER,
    ESTADO_REJECTED,
    ESTADO_WITHDRAWN,
    PORTAL_GREENHOUSE,
    PORTAL_LINKEDIN,
    PORTAL_WORKDAY,
    clasificar,
    clasificar_mensajes,
    estado_mas_avanzado,
    formatear_fecha,
    portal_del_remitente,
    referencia_de_url,
)

WORKDAY = "no-reply@myworkdayjobs.com"


class TestClasificacion(unittest.TestCase):
    def test_aviso_de_aplicacion_recibida(self):
        senal = clasificar(
            WORKDAY,
            "Your application for Support Engineer has been received",
            "Thank you for applying to Example Corp.",
        )
        self.assertIsNotNone(senal)
        self.assertEqual(senal.estado, ESTADO_APPLIED)
        self.assertEqual(senal.portal, PORTAL_WORKDAY)

    def test_entrevista_gana_a_la_patron_generica(self):
        senal = clasificar(
            WORKDAY,
            "Next steps: interview for Support Engineer",
            "We would like to schedule an interview with the hiring team.",
        )
        self.assertEqual(senal.estado, ESTADO_INTERVIEW)

    def test_rechazo_explicito(self):
        senal = clasificar(
            WORKDAY,
            "Update on your application for Support Engineer",
            "We have decided not to move forward with your application.",
        )
        self.assertEqual(senal.estado, ESTADO_REJECTED)
        self.assertTrue(senal.es_cierre)
        self.assertFalse(senal.es_avance)

    def test_no_seleccionado_no_es_el_mismo_que_rechazado(self):
        senal = clasificar(
            WORKDAY,
            "Update on your application",
            "After careful consideration we have not selected your application "
            "for this position. We encourage you to apply again.",
        )
        self.assertEqual(senal.estado, ESTADO_REJECTED)

    def test_oferta(self):
        senal = clasificar(
            "recruiter@example.com",
            "Job offer - Support Engineer",
            "We are pleased to offer you the position.",
        )
        self.assertEqual(senal.estado, ESTADO_OFFER)
        self.assertTrue(senal.es_avance)

    def test_contacto_de_reclutador(self):
        senal = clasificar(
            "talent@example.com",
            "About your application",
            "A recruiter from Example Corp will be in touch with more information.",
        )
        self.assertEqual(senal.estado, ESTADO_RECRUITER)

    def test_retirada(self):
        senal = clasificar(
            WORKDAY,
            "Application withdrawn",
            "Your application has been withdrawn.",
        )
        self.assertEqual(senal.estado, ESTADO_WITHDRAWN)

    def test_correo_no_relacionado_no_produce_senal(self):
        self.assertIsNone(
            clasificar(
                "boletin@example.com",
                "Our new coffee menu is here",
                "Check out our latest promotions and discounts.",
            )
        )

    def test_publicidad_que_usa_la_palabra_application_no_produce_senal(self):
        # "job application" sin un verbo de estado no es una notificacion.
        senal = clasificar(
            "noticias@example.com",
            "Tips for your job application",
            "Our career advice guide is available.",
        )
        self.assertIsNone(senal)

    def test_el_mensaje_conserva_solo_derivados(self):
        senal = clasificar(
            WORKDAY,
            "Your application has been received",
            "Apply here: https://example.wd1.myworkdayjobs.com/en-US/External/job/"
            "Costa-Rica/Support-Engineer_R38059",
        )
        self.assertEqual(senal.estado, ESTADO_APPLIED)
        self.assertEqual(senal.source_job_id, "Support-Engineer_R38059")
        self.assertEqual(senal.portal, PORTAL_WORKDAY)


class TestReferencias(unittest.TestCase):
    def test_portal_por_remitente(self):
        self.assertEqual(portal_del_remitente(WORKDAY), PORTAL_WORKDAY)
        self.assertEqual(
            portal_del_remitente("no-reply@greenhouse.io"), PORTAL_GREENHOUSE
        )
        self.assertEqual(
            portal_del_remitente("notifications-noreply@linkedin.com"),
            PORTAL_LINKEDIN,
        )
        self.assertEqual(portal_del_remitente("someone@example.com"), "otro")

    def test_referencia_workday(self):
        portal, ref = referencia_de_url(
            "https://example.wd1.myworkdayjobs.com/en-US/External/job/"
            "Costa-Rica/Support-Engineer_R38059"
        )
        self.assertEqual(portal, PORTAL_WORKDAY)
        self.assertEqual(ref, "Support-Engineer_R38059")

    def test_referencia_workday_con_querystring(self):
        portal, ref = referencia_de_url(
            "https://example.wd1.myworkdayjobs.com/en-US/External/job/"
            "Costa-Rica/Analyst_JR-12345?src=LinkedIn"
        )
        self.assertEqual(portal, PORTAL_WORKDAY)
        self.assertEqual(ref, "Analyst_JR-12345")

    def test_referencia_greenhouse(self):
        portal, ref = referencia_de_url(
            "https://boards.greenhouse.io/example/jobs/4012345"
        )
        self.assertEqual(portal, PORTAL_GREENHOUSE)
        self.assertEqual(ref, "4012345")

    def test_referencia_linkedin(self):
        portal, ref = referencia_de_url(
            "https://www.linkedin.com/jobs/view/support-engineer-at-example-4123456789"
        )
        self.assertEqual(portal, PORTAL_LINKEDIN)
        self.assertEqual(ref, "4123456789")

    def test_url_desconocida(self):
        self.assertEqual(referencia_de_url("https://example.com/ofertas"), ("otro", ""))


class TestEstadoFinal(unittest.TestCase):
    def test_el_avance_no_se_degrada(self):
        self.assertEqual(
            estado_mas_avanzado([ESTADO_APPLIED, ESTADO_INTERVIEW]),
            ESTADO_INTERVIEW,
        )
        self.assertEqual(
            estado_mas_avanzado([ESTADO_APPLIED, ESTADO_REJECTED]),
            ESTADO_REJECTED,
        )
        self.assertEqual(
            estado_mas_avanzado(
                [ESTADO_APPLIED, ESTADO_INTERVIEW, ESTADO_REJECTED]
            ),
            ESTADO_INTERVIEW,
        )

    def test_la_oferta_manda(self):
        self.assertEqual(
            estado_mas_avanzado([ESTADO_INTERVIEW, ESTADO_OFFER]),
            ESTADO_OFFER,
        )

    def test_solo_aplicada(self):
        self.assertEqual(estado_mas_avanzado([ESTADO_APPLIED]), ESTADO_APPLIED)
        self.assertEqual(estado_mas_avanzado([]), "")


class TestLote(unittest.TestCase):
    def test_clasificar_lote_descarta_lo_irrelevante(self):
        senales = clasificar_mensajes(
            [
                {
                    "remitente": WORKDAY,
                    "asunto": "Your application has been received",
                    "cuerpo": "Thank you for applying.",
                },
                {
                    "remitente": "boletin@example.com",
                    "asunto": "Weekly news",
                    "cuerpo": "Nothing to do with jobs.",
                },
                {
                    "remitente": "recruiter@example.com",
                    "asunto": "Next steps",
                    "cuerpo": "We would like to schedule an interview.",
                },
            ]
        )
        self.assertEqual(
            [s.estado for s in senales], [ESTADO_APPLIED, ESTADO_INTERVIEW]
        )

    def test_fecha_iso(self):
        self.assertEqual(
            formatear_fecha(datetime(2026, 11, 4, 8, 30, 15)),
            "2026-11-04 08:30:15",
        )


if __name__ == "__main__":
    unittest.main()
