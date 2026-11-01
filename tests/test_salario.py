# -*- coding: utf-8 -*-
"""Tests de la señal de salario (jobpulse_v15.salario).

Cubre la puerta que decide si un aviso DECLARA su compensacion (marca de
salario + moneda) y que el contador de huecos (SQL) diga EXACTAMENTE lo
mismo que el extractor (Python).

Contexto: antes el prompt de salario solo se disparaba si el aviso traia el
campo `salary_raw` de la fuente, y las APIs de empleo casi nunca lo traen
(0 de 354 avisos en la corrida por la UI del 2026-11-01): los 14 avisos que
SI declaraban su compensacion en el texto nunca se procesaban.
"""
import unittest

from jobpulse_v15 import salario


class TestDeclaraSalario(unittest.TestCase):
    def test_reconoce_declaraciones_reales(self):
        casos = [
            "Estimated base salary: $19,984,600 CRC annually",
            "Compensation is of 420,000 colones per month.",
            "Hourly Rate: $10 to $23 USD per hour",
            "Earn $15 USD Per Hour",
            "Compensation: USD 1,400 – 1,600 per month",
            "Salary: ₡ 625000, Position Type: Full-time",
            "El salario base es de 1.200.000 colones mensuales.",
        ]
        for texto in casos:
            with self.subTest(texto=texto):
                self.assertTrue(salario.declara_salario(texto))

    def test_ignora_marca_sin_monto(self):
        # "compensation" generico sin cifra no es un dato de salario
        self.assertFalse(
            salario.declara_salario("We offer generous compensation and stock options")
        )

    def test_ignora_cifra_que_no_es_salario(self):
        # ingresos / funding / ventas: no son compensacion del puesto
        self.assertFalse(
            salario.declara_salario(
                "We have raised $200 million in funding and $500 million in revenue"
            )
        )
        self.assertFalse(
            salario.declara_salario("Our masteries run from $4,000 to $6,000")
        )

    def test_ignora_texto_vacio(self):
        self.assertFalse(salario.declara_salario(None, "", "   "))

    def test_acepta_varios_textos(self):
        self.assertTrue(
            salario.declara_salario(
                "Puesto de ventas.", "La compensacion es de $2,000 USD mensuales."
            )
        )

    def test_tolera_acentos(self):
        self.assertTrue(
            salario.declara_salario("La remuneración es de $1,000 USD al mes")
        )
        self.assertTrue(
            salario.declara_salario("El salario es de 2.000.000 colones")
        )


class TestContextoSalario(unittest.TestCase):
    def test_recorta_alrededor_de_la_marca(self):
        texto = "x" * 5000 + " Compensation: USD 1,400 per month " + "y" * 5000
        contexto = salario.contexto_salario(texto)
        self.assertIsNotNone(contexto)
        self.assertIn("Compensation", contexto)
        self.assertLess(len(contexto), 2000)

    def test_devuelve_none_sin_marca(self):
        self.assertIsNone(salario.contexto_salario("Un aviso sincompensacion"))

    def test_usa_el_texto_original(self):
        texto = "Compensation: USD 1,400 per month"
        self.assertEqual(salario.contexto_salario(texto), texto.strip())


class TestPredicadoSql(unittest.TestCase):
    def test_usa_el_mismo_regex_que_python(self):
        import re
        import sqlite3

        from jobpulse_v15 import salario as mod

        con = sqlite3.connect(":memory:")
        mod.registrar_funciones(con)
        con.execute(
            "CREATE TABLE jobs (salary_min INTEGER, salary_raw TEXT,"
            " description_raw TEXT, requirements_raw TEXT)"
        )
        filas = [
            (None, "", "Estimated base salary: $19,984,600 CRC annually", ""),
            (None, "", "We raised $200 million in funding", ""),
            (None, "", "We offer great compensation and learning programs", ""),
            (None, "1 000 000 CRC", "", ""),
            (1000, "", "Compensation: USD 1,400 per month", ""),
        ]
        con.executemany(
            "INSERT INTO jobs VALUES (?,?,?,?)", filas
        )
        sql = mod.predicado_sql_hueco()
        ids = [r[0] for r in con.execute(f"SELECT salary_min FROM jobs WHERE {sql}")]
        # solo el aviso que declara un salario de verdad (y el que trae
        # salary_raw) quedan como hueco pendiente
        self.assertEqual(len(ids), 2)
        con.close()

    def test_el_regex_sql_es_el_de_python(self):
        import re

        from jobpulse_v15 import salario as mod

        self.assertTrue(
            re.search(
                mod._PATRON_SALARIO_Y_MONEDA,
                "Compensation: USD 1,400 per month",
                re.IGNORECASE,
            )
        )
        self.assertFalse(
            re.search(
                mod._PATRON_SALARIO_Y_MONEDA,
                "We raised $200 million in funding",
                re.IGNORECASE,
            )
        )
        self.assertFalse(
            re.search(
                mod._PATRON_SALARIO_Y_MONEDA,
                "great compensation package and continuous learning",
                re.IGNORECASE,
            )
        )


if __name__ == "__main__":
    unittest.main()
