# -*- coding: utf-8 -*-
"""Tests del catalogo geografico de Costa Rica (``ubicaciones_cr``).

La jerarquia es **pais -> provincia -> canton -> distrito** (de mayor a
menor) y el ULTIMO recurso para los campos de ciudad que la ubicacion no
resuelve es la tabla de lugares leida del TEXTO del aviso.
"""

import unittest

from jobpulse_v15 import ubicaciones_cr as u
from jobpulse_v15.workday import WorkdayFetcher


class TestCatalogo(unittest.TestCase):
    """La semilla se carga completa y sin ambiguedades."""

    def test_catalogo_completo(self):
        self.assertEqual(len(u.provincias()), 7)
        self.assertEqual(len(u.cantones_unicos()), 84)
        self.assertGreaterEqual(len(u.distritos_unicos()), 350)

    def test_resolver_respeta_el_orden_de_mayor_a_menor(self):
        # Primero la provincia, despues el canton y al final el distrito.
        self.assertEqual(u.resolver("San Jose")[0], u.NIVEL_PROVINCIA)
        self.assertEqual(u.resolver("Grecia")[0], u.NIVEL_CANTON)
        self.assertEqual(u.resolver("Ulloa")[0], u.NIVEL_DISTRITO)

    def test_canton_deduce_la_provincia(self):
        self.assertEqual(
            u.resolver("Grecia"), (u.NIVEL_CANTON, "Alajuela", "Grecia", "Grecia")
        )

    def test_nombre_ambiguo_entre_canton_y_distrito(self):
        # "Belen" es canton en Heredia y distrito en Guanacaste: sin contexto
        # no se decide (no se adivina).
        self.assertEqual(len(u.candidatos("Belen")), 2)
        self.assertIsNone(u.resolver_direccion("Belen, Costa Rica")["region"])
        # Con la provincia nombrada, si se decide.
        self.assertEqual(
            u.resolver_direccion("Belen, Heredia"),
            {"city": "Belén", "region": "Heredia"},
        )

    def test_distrito_deduce_canton_y_provincia(self):
        self.assertEqual(
            u.resolver("Ulloa"),
            (u.NIVEL_DISTRITO, "Heredia", "Heredia", "Ulloa"),
        )

    def test_lugar_desconocido_no_se_resuelve(self):
        self.assertIsNone(u.resolver("Ultra Park II"))
        self.assertIsNone(u.resolver("Lagunilla"))


class TestResolverDireccion(unittest.TestCase):
    """La resolucion de una ubicacion completa."""

    def resolver(self, texto, **kwargs):
        return u.resolver_direccion(texto, **kwargs)

    def test_provincia_nombrada_es_cierta(self):
        self.assertEqual(
            self.resolver("San Jose, Costa Rica"),
            {"city": None, "region": "San José"},
        )

    def test_canton_nombrado_da_ciudad_y_provincia(self):
        self.assertEqual(
            self.resolver("Grecia, Costa Rica"),
            {"city": "Grecia", "region": "Alajuela"},
        )

    def test_distrito_ambiguo_se_desambigua_con_el_canton(self):
        # "San Antonio" aparece en 8 distritos: el canton "Belen" lo fija.
        self.assertEqual(
            self.resolver("San Antonio, Belen, Heredia, Costa Rica"),
            {"city": "San Antonio", "region": "Heredia"},
        )

    def test_lugar_ambiguo_sin_canton_no_inventa_provincia(self):
        # "Lagunilla" no esta en la division territorial: no se adivina.
        self.assertEqual(
            self.resolver("Lagunilla, Costa Rica"),
            {"city": "Lagunilla", "region": None},
        )

    def test_jerarquia_completa(self):
        self.assertEqual(
            self.resolver("San Antonio, Belen, Heredia, Costa Rica"),
            {"city": "San Antonio", "region": "Heredia"},
        )
        self.assertEqual(
            self.resolver("Tres Rios, La Union, Cartago, Costa Rica"),
            {"city": "Tres Ríos", "region": "Cartago"},
        )

    def test_el_ruido_no_es_ciudad(self):
        casos = {
            "Costa Rica Remote": (None, None),
            "Global Service Center- Costa Rica": (None, None),
            "Costa Rica-Cartago-Wet Plant": (None, "Cartago"),
            "San Jose, Costa Rica Local Office": (None, "San José"),
            "San Jose, Central, Costa Rica": (None, "San José"),
        }
        for texto, (ciudad, provincia) in casos.items():
            with self.subTest(texto=texto):
                resultado = self.resolver(texto)
                self.assertEqual(resultado["city"], ciudad)
                self.assertEqual(resultado["region"], provincia)

    def test_acepta_cualquier_separador(self):
        for texto in (
            "Grecia, Costa Rica",
            "Grecia - Costa Rica",
            "Grecia / Costa Rica",
            "Grecia_Costa Rica",
            "Grecia Costa Rica",
        ):
            with self.subTest(texto=texto):
                self.assertEqual(
                    self.resolver(texto),
                    {"city": "Grecia", "region": "Alajuela"},
                )


class TestTablaDeLugares(unittest.TestCase):
    """El ULTIMO recurso: un lugar conocido nombrado en el TEXTO del aviso."""

    TEXTO_ULTRA = (
        "Benefits: This is a hybrid position based in Ultra Park II, "
        "Lagunilla (Heredia). On-site presence is required only when necessary."
    )
    TEXTO_AFZ = "You will be based at our office in AFZ, Heredia on Mondays."

    def test_ultra_park_da_lagunilla_heredia(self):
        self.assertEqual(
            u.resolver_lugar(self.TEXTO_ULTRA),
            ("Ultra Park II", "Lagunilla", "Heredia"),
        )

    def test_afz_da_lagunilla_heredia(self):
        self.assertEqual(
            u.resolver_lugar(self.TEXTO_AFZ),
            ("AFZ", "Lagunilla", "Heredia"),
        )

    def test_el_texto_resuelve_lo_que_la_ubicacion_no(self):
        self.assertEqual(
            u.resolver_direccion(
                "Global Service Center- Costa Rica",
                descripcion=self.TEXTO_ULTRA,
                work_mode="hybrid",
            ),
            {"city": "Lagunilla", "region": "Heredia"},
        )

    def test_no_se_aplica_a_los_trabajos_remotos(self):
        # Un aviso remoto no tiene sede que resolver.
        self.assertEqual(
            u.resolver_direccion(
                "Costa Rica", descripcion=self.TEXTO_ULTRA, work_mode="remote"
            ),
            {"city": None, "region": None},
        )

    def test_no_se_aplica_si_el_texto_dice_remoto(self):
        self.assertEqual(
            u.resolver_direccion(
                "Costa Rica",
                descripcion="This is a fully remote position. " + self.TEXTO_ULTRA,
            ),
            {"city": None, "region": None},
        )

    def test_no_contradice_la_provincia_ya_resuelta(self):
        # El texto habla de Heredia, pero la ubicacion dice Alajuela: no se
        # pisa la provincia ya conocida.
        self.assertEqual(
            u.resolver_direccion(
                "Costa Rica - Alajuela",
                descripcion=self.TEXTO_ULTRA,
                work_mode="hybrid",
            ),
            {"city": None, "region": "Alajuela"},
        )

    def test_lugares_ambiguos_no_se_eligen(self):
        texto = "You will rotate between Ultra Park II (Heredia) and Coyol (Alajuela)."
        self.assertIsNone(u.resolver_lugar(texto))


class TestRuido(unittest.TestCase):
    def test_ciudad_basura(self):
        self.assertTrue(u.ciudad_es_basura("GCG_Costa Rica_San Jose"))
        self.assertTrue(u.ciudad_es_basura("Costa Rica"))
        self.assertFalse(u.ciudad_es_basura("Heredia"))
        self.assertFalse(u.ciudad_es_basura(None))

    def test_descriptores_no_son_ciudad(self):
        self.assertFalse(u.es_ciudad_plausible("Central"))
        self.assertFalse(u.es_ciudad_plausible("Ciudad del Este"))
        self.assertFalse(u.es_ciudad_plausible("Local Office"))
        self.assertTrue(u.es_ciudad_plausible("Lagunilla"))

    def test_solo_costa_rica(self):
        self.assertTrue(u.es_costa_rica("CR", "Costa Rica"))
        self.assertTrue(u.es_costa_rica("CRI", "Costa Rica"))
        self.assertFalse(u.es_costa_rica("MX", "Mexico"))
        self.assertFalse(u.es_costa_rica("CR", "Mexico"))


class TestAdaptadorWorkday(unittest.TestCase):
    """El adaptador de Workday usa el catalogo compartido."""

    def test_otro_pais_no_se_normaliza(self):
        self.assertEqual(
            WorkdayFetcher.normalize_location("Alajuela, Costa Rica", "MX", "Mexico"),
            {"city": None, "region": None},
        )

    def test_delega_en_el_catalogo(self):
        self.assertEqual(
            WorkdayFetcher.normalize_location("Grecia, Costa Rica", "CR", "Costa Rica"),
            {"city": "Grecia", "region": "Alajuela"},
        )


if __name__ == "__main__":
    unittest.main()
