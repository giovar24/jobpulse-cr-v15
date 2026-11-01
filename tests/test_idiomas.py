# -*- coding: utf-8 -*-
"""Tests del detector de idioma del aviso (``idiomas``).

El detector es DETERMINISTA (cuenta palabras funcionales, no usa IA) y
conservador: si el texto es corto o esta en un idioma que no se distingue,
devuelve 'undetermined' en vez de adivinar.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15 import idiomas


TEXTO_ES = (
    "Puesto de ventas en Heredia, Costa Rica. Buscamos una persona con "
    "experiencia en atencion al cliente y buena disposicion para trabajar en "
    "equipo. Se requiere bachillerato completo y licencia de conducir. "
    "Ofrecemos salario segun experiencia y horario de lunes a viernes."
)

TEXTO_EN = (
    "We are looking for a sales associate to join our team in Heredia, Costa "
    "Rica. The ideal candidate has experience in customer service and is able "
    "to work with the team. A high school diploma and a valid driver license "
    "are required. We offer a competitive salary and a Monday to Friday "
    "schedule with benefits for all employees."
)

TEXTO_MIXTO = (
    "El Analista de Cumplimiento es un puesto de nivel inicial a cargo de "
    "participar del control, la gestion y la supervision de informes "
    "regulatorios. About the Compliance Analyst: this is an entry level role "
    "with our team, and you will be part of the regulatory reporting process "
    "and the day to day monitoring of the compliance controls."
)


class TestDetectorDeIdioma(unittest.TestCase):
    def test_detecta_espanol(self):
        self.assertEqual(idiomas.detectar_idioma_del_aviso(TEXTO_ES), "es")

    def test_detecta_ingles(self):
        self.assertEqual(idiomas.detectar_idioma_del_aviso(TEXTO_EN), "en")

    def test_detecta_texto_mixto(self):
        self.assertEqual(idiomas.detectar_idioma_del_aviso(TEXTO_MIXTO), "mixed")

    def test_texto_corto_no_se_adivina(self):
        self.assertEqual(
            idiomas.detectar_idioma_del_aviso("Vacante"), "undetermined"
        )

    def test_texto_vacio_no_se_adivina(self):
        self.assertEqual(
            idiomas.detectar_idioma_del_aviso("", None, ""), "undetermined"
        )

    def test_acepta_varios_textos_del_aviso(self):
        self.assertEqual(
            idiomas.detectar_idioma_del_aviso("Sales Associate", TEXTO_EN), "en"
        )

    def test_codigo_canonico_del_idioma(self):
        self.assertEqual(idiomas.codigo_canonico_del_idioma("es"), "espanol")
        self.assertEqual(idiomas.codigo_canonico_del_idioma("en"), "ingles")
        self.assertIsNone(idiomas.codigo_canonico_del_idioma("mixed"))
        self.assertIsNone(idiomas.codigo_canonico_del_idioma("undetermined"))


if __name__ == "__main__":
    unittest.main()
