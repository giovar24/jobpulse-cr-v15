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


class TestNormalizacionDeNiveles(unittest.TestCase):
    """El nivel de idioma hay que NORMALIZARLO antes de compararlo.

    Sin normalizar, el gap de idioma se escondia en silencio: la escala
    ``IDIOMA_ORDEN`` solo tenia las claves en mayusculas ("B2") y los
    requisitos traen el nivel en minusculas ("b2"), asi que la comparacion
    caia en "no_verificable" y no se comparaba NADA.
    """

    def test_los_codigos_cefr_se_normalizan(self):
        for valor in ("B2", "b2", " B2 ", "b2+", "B2 +"):
            self.assertEqual(idiomas.normalizar_nivel(valor), "B2", valor)

    def test_un_rango_toma_el_nivel_minimo(self):
        # "C1-C2" exige COMO MINIMO C1: el nivel mas suave que acepta.
        self.assertEqual(idiomas.normalizar_nivel("C1-C2"), "C1")
        self.assertEqual(idiomas.normalizar_nivel("intermedio-avanzado"), "B2")

    def test_las_palabras_de_nivel_se_mapean(self):
        self.assertEqual(idiomas.normalizar_nivel("fluent"), "C1")
        self.assertEqual(idiomas.normalizar_nivel("avanzado/fluyente"), "C1")
        self.assertEqual(idiomas.normalizar_nivel("intermedio"), "B2")
        self.assertEqual(idiomas.normalizar_nivel("basic"), "A2")
        self.assertEqual(idiomas.normalizar_nivel("nativo"), "nativo")

    def test_un_nivel_desconocido_no_se_inventa(self):
        self.assertIsNone(idiomas.normalizar_nivel("avanzadito"))
        self.assertIsNone(idiomas.normalizar_nivel(None))
        self.assertIsNone(idiomas.normalizar_nivel(""))

    def test_el_orden_de_los_niveles(self):
        self.assertEqual(idiomas.orden_nivel("b2"), 4)
        self.assertEqual(idiomas.orden_nivel("B2"), 4)
        self.assertEqual(idiomas.orden_nivel("nativo"), 7)
        self.assertGreater(idiomas.orden_nivel("C1"), idiomas.orden_nivel("B2"))
        self.assertIsNone(idiomas.orden_nivel("xyz"))

    def test_el_nombre_del_idioma_se_mapea_a_su_variante(self):
        self.assertEqual(idiomas.nombre_idioma_a_variante("Inglés"), "ingles")
        self.assertEqual(idiomas.nombre_idioma_a_variante("English"), "ingles")
        self.assertEqual(idiomas.nombre_idioma_a_variante("español"), "espanol")
        self.assertEqual(
            idiomas.nombre_idioma_a_variante("Simplified Chinese (Singapore)"),
            "chino",
        )
        self.assertEqual(idiomas.nombre_idioma_a_variante("inglés B2"), "ingles")

    def test_un_idioma_desconocido_no_se_inventa(self):
        self.assertIsNone(idiomas.nombre_idioma_a_variante("Klingon"))
        self.assertIsNone(idiomas.nombre_idioma_a_variante(None))


class TestIdiomaEnSkill(unittest.TestCase):
    """Etiquetas de skill que en realidad piden un idioma.

    La fuente a veces guarda la peticion de idioma entre las skills
    ("Inglés - C1" en ANE, "English <> Target Language" en Workday). El
    extractor JAMAS crea un requisito skill con eso, asi que curarlos como
    skill daria un falso "faltante": la curacion los manda al lado idioma
    (`taxonomia.demanda_corpus`).
    """

    def test_reconoce_idioma_con_nivel(self):
        self.assertEqual(idiomas.idioma_en_skill("Inglés - C1"), "ingles")
        self.assertEqual(idiomas.idioma_en_skill("Español - C1"), "espanol")
        self.assertEqual(idiomas.idioma_en_skill("ingles c1"), "ingles")

    def test_reconoce_idioma_con_cualquier_cola(self):
        self.assertEqual(
            idiomas.idioma_en_skill("English <> Target Language"), "ingles"
        )
        self.assertEqual(idiomas.idioma_en_skill("english fluency"), "ingles")
        self.assertEqual(
            idiomas.idioma_en_skill("Spanish communication skills"), "espanol"
        )

    def test_un_codigo_de_dos_letras_no_es_idioma(self):
        """En skills, "IT" es tecnologia, no italiano (bug real del corpus)."""
        self.assertIsNone(idiomas.idioma_en_skill("IT"))
        self.assertIsNone(idiomas.idioma_en_skill("it inventory"))
        self.assertIsNone(idiomas.idioma_en_skill("it disaster recovery itdr"))

    def test_lo_que_no_es_idioma_da_none(self):
        self.assertIsNone(idiomas.idioma_en_skill("ServiceNow"))
        self.assertIsNone(idiomas.idioma_en_skill("TecnologiaFutura"))
        self.assertIsNone(idiomas.idioma_en_skill(""))
        self.assertIsNone(idiomas.idioma_en_skill(None))


if __name__ == "__main__":
    unittest.main()
