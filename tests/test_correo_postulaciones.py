# -*- coding: utf-8 -*-
"""Tests del lector de correo de postulaciones (IMAP).

NUNCA hay red en los tests: se usan mensajes .eml sinteticos y un doble de
IMAP. Lo que se verifica ademas:
  * el cuerpo del correo NUNCA se guarda (solo derivados minimos);
  * un rechazo es una SENAL DE PROCESO, no una etiqueta de aptitud.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15.correo_postulaciones import (  # noqa: E402
    ConfigCorreo,
    ErrorCorreoPostulaciones,
    consulta_gmail,
    consulta_imap_estandar,
    mensaje_a_diccionario,
    mensaje_a_senal,
    recolectar_senales,
)
from jobpulse_v15.postulaciones import (  # noqa: E402
    ESTADO_APPLIED,
    ESTADO_INTERVIEW,
    ESTADO_REJECTED,
    PORTAL_WORKDAY,
)

EML_APLICACION = """From: no-reply@myworkdayjobs.com
To: persona@example.com
Subject: Your application for Support Engineer has been received
Date: Tue, 03 Nov 2026 10:15:00 -0600
Content-Type: text/plain; charset="utf-8"

Thank you for applying to Example Corp.
Apply here: https://example.wd1.myworkdayjobs.com/en-US/External/job/
Costa-Rica/Support-Engineer_R38059
"""

EML_ENTREVISTA = """From: talent@example.com
Subject: Next steps for Support Engineer
Date: Wed, 04 Nov 2026 09:00:00 -0600
Content-Type: text/plain; charset="utf-8"

We would like to schedule an interview with the hiring team.
"""

EML_RECHAZO = """From: no-reply@myworkdayjobs.com
Subject: Update on your application
Date: Wed, 04 Nov 2026 11:00:00 -0600
Content-Type: text/plain; charset="utf-8"

After careful consideration we have not selected your application for this
position. We encourage you to apply again.
"""

EML_PUBLICIDAD = """From: boletin@example.com
Subject: Our new coffee menu is here
Date: Wed, 04 Nov 2026 08:00:00 -0600
Content-Type: text/plain; charset="utf-8"

Check out our latest promotions.
"""

EML_HTML = """From: no-reply@myworkdayjobs.com
Subject: Your application has been received
Date: Wed, 04 Nov 2026 08:00:00 -0600
Content-Type: text/html; charset="utf-8"

<html><body><p>Thank you for applying.</p>
<a href="https://example.wd1.myworkdayjobs.com/en-US/External/job/Costa-Rica/Analyst_JR1234">
Apply</a></body></html>
"""


class _IMAPFalso:
    """Doble minimo de IMAP4_SSL (nunca red)."""

    def __init__(self, mensajes):
        self.mensajes = list(mensajes)
        self.buscadas: list = []
        self.login_recibido = None
        self.cerrado = False

    def login(self, usuario, password):
        self.login_recibido = (usuario, password)
        return ("OK", [b""])

    def select(self, carpeta):
        return ("OK", [b"1"])

    def search(self, charset, *criterios):
        self.buscadas.append(criterios)
        # IMAP real devuelve los numeros separados por espacio en UN bloque.
        numeros = " ".join(str(i) for i in range(1, len(self.mensajes) + 1))
        return ("OK", [numeros.encode()])

    def fetch(self, numero, opciones):
        indice = int(numero) - 1
        return ("OK", [(b"1 (RFC822 {1}", self.mensajes[indice])])

    def logout(self):
        self.cerrado = True
        return ("BYE", [b""])


class TestConsulta(unittest.TestCase):
    def test_consulta_gmail_filtra_por_dominio_y_antiguedad(self):
        consulta = consulta_gmail(("myworkdayjobs.com", "greenhouse.io"), 30)

        self.assertIn("newer_than:30d", consulta)
        self.assertIn("myworkdayjobs.com", consulta)
        self.assertIn("greenhouse.io", consulta)

    def test_consulta_imap_estandar_usa_since(self):
        from datetime import datetime

        consulta = consulta_imap_estandar(
            30, datetime(2026, 8, 1)
        )

        self.assertEqual(consulta, "SINCE 01-Aug-2026")


class TestMensajes(unittest.TestCase):
    def test_cabeceras_y_cuerpo(self):
        datos = mensaje_a_diccionario(EML_APLICACION)

        self.assertEqual(datos["remitente"], "no-reply@myworkdayjobs.com")
        self.assertIn("Support Engineer", datos["asunto"])
        self.assertIn("Thank you for applying", datos["cuerpo"])
        self.assertTrue(datos["fecha"].startswith("2026-11-03"))

    def test_clasifica_aplicacion(self):
        senal = mensaje_a_senal(EML_APLICACION)

        self.assertIsNotNone(senal)
        self.assertEqual(senal.estado, ESTADO_APPLIED)
        self.assertEqual(senal.portal, PORTAL_WORKDAY)
        self.assertEqual(senal.source_job_id, "Support-Engineer_R38059")

    def test_clasifica_entrevista(self):
        senal = mensaje_a_senal(EML_ENTREVISTA)

        self.assertEqual(senal.estado, ESTADO_INTERVIEW)

    def test_clasifica_rechazo(self):
        senal = mensaje_a_senal(EML_RECHAZO)

        self.assertEqual(senal.estado, ESTADO_REJECTED)

    def test_el_correo_no_relevante_no_produce_senal(self):
        self.assertIsNone(mensaje_a_senal(EML_PUBLICIDAD))

    def test_html_sin_texto_plano(self):
        senal = mensaje_a_senal(EML_HTML)

        self.assertIsNotNone(senal)
        self.assertEqual(senal.estado, ESTADO_APPLIED)
        self.assertEqual(senal.source_job_id, "Analyst_JR1234")

    def test_la_senal_no_guarda_el_cuerpo(self):
        senal = mensaje_a_senal(EML_RECHAZO)

        self.assertFalse(hasattr(senal, "cuerpo"))
        # Lo que se conserva son derivados minimos.
        self.assertNotIn("careful consideration", senal.__dict__.values())


class TestRecoleccion(unittest.TestCase):
    def test_recolecta_las_senales_y_descarta_el_resto(self):
        imap = _IMAPFalso([EML_APLICACION, EML_PUBLICIDAD, EML_ENTREVISTA])

        senales = recolectar_senales(
            usuario="persona@example.com",
            password="app-password",
            config=ConfigCorreo(usuario="persona@example.com"),
            fabrica_imap=lambda host, puerto: imap,
        )

        self.assertEqual([s.estado for s in senales], [ESTADO_APPLIED, ESTADO_INTERVIEW])
        self.assertEqual(imap.login_recibido, ("persona@example.com", "app-password"))
        self.assertTrue(imap.cerrado)

    def test_sin_credencial_no_intenta_conectar(self):
        with self.assertRaises(ErrorCorreoPostulaciones):
            recolectar_senales(
                usuario="",
                password="",
                fabrica_imap=lambda host, puerto: _IMAPFalso([]),
            )

    def test_fallo_de_login_no_deja_la_sesion_abierta(self):
        class _IMAPFallido(_IMAPFalso):
            def login(self, usuario, password):
                raise RuntimeError("credenciales invalidas")

        imap = _IMAPFallido([])
        with self.assertRaises(ErrorCorreoPostulaciones):
            recolectar_senales(
                usuario="persona@example.com",
                password="mala",
                fabrica_imap=lambda host, puerto: imap,
            )
        self.assertTrue(imap.cerrado)


if __name__ == "__main__":
    unittest.main()
