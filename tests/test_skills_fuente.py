# -*- coding: utf-8 -*-
"""CAMPOS ESTRUCTURADOS DEL AVISO -> requisitos comparables con el perfil.

El extractor por reglas (``analysis.RuleBasedExtractor``) solo lee el TEXTO.
Los avisos reales traen sus competencias en ``jobs.skills`` y los idiomas que
PIDEN en ``jobs.languages``. Sin integrar esos campos, 135 de 535 avisos del
corpus quedan SIN NINGUN requisito comparable: el motor no puede decir si el
perfil califica (banda ``sin_datos``). El dato existia; el sistema no lo
usaba.

REGLAS DURAS que este modulo respeta (y que estos tests fijan):

1. solo lo que resuelve a un concepto canonico (lo demas va a la cola
   ``concepto_no_normalizado``);
2. las frases de tarea NO son competencias (mismo criterio que el ranking
   ATS: ``ats.es_frase_de_tarea``);
3. el nivel del requisito es ``inferred``: el campo dice QUE pide el aviso,
   no si es obligatorio;
4. la evidencia es literal (la etiqueta que trae el campo);
5. no se duplica lo que el texto del aviso ya dio.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15 import skills_fuente  # noqa: E402
from jobpulse_v15.analysis_flow import extract_job_analysis, preparar_analisis  # noqa: E402
from jobpulse_v15.db import Database  # noqa: E402
from jobpulse_v15.repository import Repository  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.initialize()
        self.repository = Repository(self.database)
        self.repository.register_platform("workday", "Workday", "api")
        self.repository.register_site(
            "sitio", "workday", "Sitio", "https://example.test/jobs"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _job(self, job_id="job-1", title="Support Engineer", **campos):
        datos = {
            "job_id": job_id,
            "title": title,
            "company": "Example",
            "country": "CR",
            "posting_language": "en",
            "description_raw": "Buscamos una persona con experiencia en el area.",
        }
        datos.update(campos)
        self.repository.save_job(
            datos,
            site_id="sitio",
            source_job_id=job_id,
        )
        # `skills` y `languages` no los escribe `save_job` (los escribe el
        # pase de IA); se simula el estado real de la base.
        for columna in ("skills", "languages"):
            if columna in datos:
                with self.database.connection() as connection:
                    connection.execute(
                        f"UPDATE jobs SET {columna} = ? WHERE job_id = ?",
                        (datos[columna], job_id),
                    )
        return job_id

    def _requisitos_vigentes(self, job_id):
        with self.database.connection() as connection:
            filas = connection.execute(
                """
                SELECT r.category, r.value_code, r.value_text, r.qualifier,
                       r.requirement_level, r.evidence, r.origin,
                       r.codigo_canonico
                FROM job_requirements AS r
                JOIN job_analysis AS a ON a.analysis_id = r.analysis_id
                WHERE a.job_id = ? AND a.is_current = 1
                ORDER BY r.requirement_id
                """,
                (job_id,),
            ).fetchall()
        return [dict(fila) for fila in filas]


class TestParseoDeCampos(unittest.TestCase):
    """El formato real es JSON; el resto es tolerancia con datos viejos."""

    def test_parsea_el_array_json_real(self):
        self.assertEqual(
            skills_fuente.parsear_skills('["Python", "SQL"]'), ["Python", "SQL"]
        )

    def test_parsea_texto_plano_separado_por_comas(self):
        self.assertEqual(
            skills_fuente.parsear_skills("Python, SQL"), ["Python", "SQL"]
        )

    def test_sin_datos_devuelve_lista_vacia(self):
        for valor in (None, "", "null", "[]", "   "):
            self.assertEqual(skills_fuente.parsear_skills(valor), [])

    def test_descarta_repetidos_ignorando_mayusculas_y_acentos(self):
        self.assertEqual(
            skills_fuente.parsear_skills('["Python", "python", "PYTHON"]'),
            ["Python"],
        )

    def test_parsea_languages_json(self):
        self.assertEqual(
            skills_fuente.parsear_languages('{"ingles": "B2"}'), {"ingles": "B2"}
        )

    def test_parsea_languages_texto(self):
        self.assertEqual(
            skills_fuente.parsear_languages("ingles:B2; espanol:nativo"),
            {"ingles": "B2", "espanol": "nativo"},
        )

    def test_languages_sin_datos_devuelve_vacio(self):
        for valor in (None, "", "null", "{}", "[]"):
            self.assertEqual(skills_fuente.parsear_languages(valor), {})


class TestClasificacion(Base):
    """Solo lo que resuelve a un concepto canonico es comparable."""

    def test_una_skill_de_la_taxonomia_resuelve(self):
        with self.database.connection() as connection:
            resolucion = skills_fuente.clasificar(connection, "Python")
        self.assertIsNotNone(resolucion)
        self.assertEqual(resolucion[0], "skill")
        self.assertEqual(resolucion[2], "python")

    def test_la_variante_emita_es_la_cruda_de_la_taxonomia(self):
        # Si se emitiera la etiqueta normalizada, el resolutor de
        # `conceptos` no encontraria "active directory" y el requisito
        # quedaria SIN codigo (invisible para el motor).
        with self.database.connection() as connection:
            resolucion = skills_fuente.clasificar(connection, "Active Directory")
        self.assertIsNotNone(resolucion)
        self.assertEqual(resolucion[1], "active directory")

    def test_una_skill_desconocida_no_resuelve(self):
        with self.database.connection() as connection:
            self.assertIsNone(
                skills_fuente.clasificar(connection, "tecnologia-de-marte-futuro")
            )

    def test_el_alias_de_la_migracion_021_resuelve(self):
        # "consultas SQL" es la misma competencia que "SQL".
        with self.database.connection() as connection:
            resolucion = skills_fuente.clasificar(connection, "consultas SQL")
        self.assertIsNotNone(resolucion)
        self.assertEqual(resolucion[2], "sql")

    def test_la_clase_de_licencia_se_resuelve(self):
        with self.database.connection() as connection:
            resolucion = skills_fuente.clasificar(connection, "Licencia B3")
        self.assertIsNotNone(resolucion)
        self.assertEqual(resolucion[0], "license")
        self.assertEqual(resolucion[2], "licencia-conducir")

    def test_un_codigo_de_dos_letras_no_resuelve_como_idioma(self):
        """"IT" es tecnologia, no italiano (bug real: indeed-d4b1295866756a8c
        acabo con requisito de idioma italiano por pedir "IT" entre sus
        skills). Los codigos de dos letras son claves internas del extractor
        de reglas (`analysis.py` emite value_code 'en'/'es'), nunca etiquetas
        naturales; el resolutor directo (`conceptos.resolver`) sigue
        entendiendolos porque mira la variante, no pasa por aqui.
        """
        with self.database.connection() as connection:
            self.assertIsNone(skills_fuente.clasificar(connection, "IT"))
            self.assertIsNone(skills_fuente.clasificar(connection, "it"))
            self.assertIsNone(skills_fuente.clasificar(connection, "en"))
            # Los NOMBRES de idioma si resuelven (etiqueta natural).
            self.assertEqual(
                skills_fuente.clasificar(connection, "ingles"),
                ("language", "ingles", "ingles"),
            )
            # Las variantes cortas de skill ('r', tanda 2) siguen vivas.
            self.assertEqual(
                skills_fuente.clasificar(connection, "R"), ("skill", "r", "r")
            )


class TestRequisitosDeFuente(Base):
    """Las reglas duras del pipeline."""

    def _requisitos(self, **kwargs):
        with self.database.connection() as connection:
            requisitos, sin_concepto = skills_fuente.requisitos_de_fuente(
                connection, **kwargs
            )
        return requisitos, sin_concepto

    def test_una_skill_resoluble_genera_un_requisito_inferido(self):
        requisitos, _ = self._requisitos(skills='["Python"]')

        self.assertEqual(len(requisitos), 1)
        requisito = requisitos[0]
        self.assertEqual(requisito["category"], "skill")
        self.assertEqual(requisito["requirement_level"], "inferred")
        self.assertEqual(requisito["origin"], "source_field")
        self.assertEqual(requisito["evidence"], "Python")

    def test_las_frases_de_tarea_se_descartan(self):
        # "soporte a equipos Dell" es una TAREA, no una competencia: contarla
        # penaliza a todos los avisos por igual y esconde los gaps reales.
        requisitos, sin_concepto = self._requisitos(
            skills='["soporte a equipos Dell", "elaborar cotizaciones"]'
        )

        self.assertEqual(requisitos, [])
        self.assertEqual(sin_concepto, [])

    def test_un_skill_it_no_genera_requisito_de_idioma(self):
        # Bug real (2026-11-07): "IT" entre las skills acabo como requisito
        # de idioma ITALIANO. Ahora va a la cola como skill pendiente.
        requisitos, sin_concepto = self._requisitos(skills='["IT"]')

        self.assertEqual(requisitos, [])
        self.assertEqual(sin_concepto, [("skill", "it")])

    def test_lo_que_no_resuelve_va_a_la_cola(self):
        # "Zabbix" es una competencia real que la taxonomia todavia no
        # conoce: se encola para curarla (no se inventa un codigo).
        requisitos, sin_concepto = self._requisitos(skills='["Zabbix"]')

        self.assertEqual(requisitos, [])
        self.assertEqual(sin_concepto, [("skill", "zabbix")])

    def test_no_se_duplica_lo_que_ya_cubre_otro_requisito(self):
        requisitos, _ = self._requisitos(
            skills='["Python"]', ya_cubiertos={"python"}
        )

        self.assertEqual(requisitos, [])

    def test_el_idioma_de_la_fuente_normaliza_el_nivel(self):
        requisitos, _ = self._requisitos(languages='{"inglés": "B2+"}')

        self.assertEqual(len(requisitos), 1)
        self.assertEqual(requisitos[0]["category"], "language")
        self.assertEqual(requisitos[0]["qualifier"], "B2")
        self.assertEqual(requisitos[0]["value_code"], "ingles")

    def test_un_idioma_desconocido_va_a_la_cola(self):
        requisitos, sin_concepto = self._requisitos(languages='{"klingon": "C2"}')

        self.assertEqual(requisitos, [])
        self.assertEqual(sin_concepto, [("language", "klingon")])


class TestIntegracionConElAnalisis(Base):
    """El analisis guarda texto + campos estructurados en el mismo pase."""

    def test_el_analisis_incluye_los_requisitos_de_la_fuente(self):
        job_id = self._job(skills=json.dumps(["Python", "SQL"]))

        resultado = extract_job_analysis(self.repository, job_id)

        self.assertEqual(resultado["requisitos_fuente"], 2)
        codigos = {
            fila["codigo_canonico"] for fila in self._requisitos_vigentes(job_id)
        }
        self.assertIn("python", codigos)
        self.assertIn("sql", codigos)

    def test_los_requisitos_de_la_fuente_nacen_con_codigo_canonico(self):
        job_id = self._job(skills=json.dumps(["Python"]))

        extract_job_analysis(self.repository, job_id)

        for fila in self._requisitos_vigentes(job_id):
            self.assertIsNotNone(fila["codigo_canonico"], fila)

    def test_lo_que_no_resuelve_se_encola_en_la_taxonomia(self):
        job_id = self._job(skills=json.dumps(["Zabbix"]))

        extract_job_analysis(self.repository, job_id)

        with self.database.connection() as connection:
            fila = connection.execute(
                "SELECT veces FROM concepto_no_normalizado WHERE texto=?",
                ("zabbix",),
            ).fetchone()
        self.assertIsNotNone(fila)
        self.assertGreaterEqual(fila["veces"], 1)

    def test_la_simulacion_no_escribe_nada(self):
        job_id = self._job(skills=json.dumps(["Python"]))

        with self.database.connection() as connection:
            job = self.repository.get_job(job_id)
            preparado = preparar_analisis(job, connection)

        self.assertEqual(len(preparado["requisitos_fuente"]), 1)
        self.assertEqual(self._requisitos_vigentes(job_id), [])

    def test_la_version_del_analisis_distingue_el_pipeline_nuevo(self):
        job_id = self._job(skills=json.dumps(["Python"]))

        extract_job_analysis(self.repository, job_id)

        with self.database.connection() as connection:
            version = connection.execute(
                "SELECT extractor_version FROM job_analysis "
                "WHERE job_id = ? AND is_current = 1",
                (job_id,),
            ).fetchone()["extractor_version"]
        self.assertTrue(version.endswith("+fuente"), version)

    def test_una_categoria_ambigua_deja_todos_sus_requisitos_ambiguos(self):
        # Invariante del repositorio: estado 'ambiguous' <=> TODOS los
        # requisitos de la categoria son 'ambiguous'.
        job_id = self._job(
            title="QA Tester",
            description_raw="Se requiere UAT y bases de datos y metodologias agiles.",
            skills=json.dumps(["UAT", "consultas SQL"]),
        )

        extract_job_analysis(self.repository, job_id)

        with self.database.connection() as connection:
            estados = {
                f["category"]: f["field_status"]
                for f in connection.execute(
                    "SELECT jfs.category, jfs.field_status FROM job_field_status AS jfs "
                    "JOIN job_analysis AS ja ON ja.analysis_id = jfs.analysis_id "
                    "WHERE ja.job_id = ? AND ja.is_current = 1",
                    (job_id,),
                ).fetchall()
            }
        if estados.get("skill") == "ambiguous":
            for fila in self._requisitos_vigentes(job_id):
                if fila["category"] == "skill":
                    self.assertEqual(fila["requirement_level"], "ambiguous")


if __name__ == "__main__":
    unittest.main()
