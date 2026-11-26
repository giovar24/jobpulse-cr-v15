# -*- coding: utf-8 -*-
"""Tests de los huecos del perfil (`jobpulse_v15.perfil_huecos`).

Por que existe: la deteccion de Â«lo que el corpus pide y el perfil no
tieneÂ» es el flujo de **Completar perfil** de la UI v2. Tiene que ser
- **implementacion unica** (UI y tool CLI la comparten),
- **agnostica del titular** (nada hardcodeado: todo sale de la BD),
- **relleno una sola vez** (recalculado en cada llamada),
- y **solo lectura**.

Patron: tempfile + Database + Repository (no toca la BD real).
"""

import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15 import areas as areas_mod
from jobpulse_v15 import perfil_huecos
from jobpulse_v15.db import Database
from jobpulse_v15.repository import Repository
from jobpulse_v15.ui_v2.data.profile import ProfileStore


def _requisito(category, value_code, level="ambiguous", evidence="Evidencia."):
    return {
        "category": category,
        "value_code": value_code,
        "value_text": value_code,
        "requirement_level": level,
        "evidence": evidence,
        "origin": "rule",
        "confidence": 0.9,
    }


class BasePerfilHuecos(unittest.TestCase):
    """Base: BD temporal con 1 aviso y 1 concepto de prueba."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.tmpdir.name) / "huecos.db")
        self.database.initialize()
        self.repository = Repository(self.database)
        self.repository.register_platform(
            "workday", "Workday", "api", default_language="en"
        )
        self.repository.register_site(
            "acme-cr", "workday", "Acme", "https://example.test/jobs",
            company_name="Acme", country="CR",
        )
        self.repository.save_job(
            {
                "job_id": "job-1",
                "title": "Analista",
                "company": "Acme",
                "country": "CR",
                "description_raw": "Se requiere Python y Excel.",
            },
            site_id="acme-cr",
            source_job_id="J-1",
        )
        # Conceptos de prueba (la taxonomia de una BD nueva no trae 'python').
        with closing(sqlite3.connect(self.database.path)) as connection:
            connection.execute(
                "INSERT OR IGNORE INTO concepto "
                "(categoria, variante, codigo_canonico, origen) VALUES "
                "('skill', 'python', 'python', 'test'),"
                "('skill', 'excel', 'excel', 'test'),"
                "('language', 'ingles', 'ingles', 'test')"
            )
            # El catalogo de areas lo siembra areas.sembrar_taxonomia (no la
            # migracion): sin esto areas_catalogo viene vacio.
            areas_mod.sembrar_taxonomia(connection)
            connection.commit()

    def tearDown(self):
        self.tmpdir.cleanup()

    def _analizar(self, requisitos, job_id="job-1"):
        # field_status debe cuadrar con requirement_level (regla del repo):
        # un nivel 'ambiguous' exige status 'ambiguous' y viceversa.
        estados: dict[str, str] = {
            "language": "not_mentioned",
            "education": "not_mentioned",
            "license": "not_mentioned",
            "experience": "not_mentioned",
            "skill": "not_mentioned",
        }
        for req in requisitos:
            categoria = req["category"]
            if req["requirement_level"] == "ambiguous":
                estados[categoria] = "ambiguous"
            elif estados.get(categoria, "not_mentioned") != "ambiguous":
                estados[categoria] = "found"
        self.repository.save_analysis(
            job_id,
            text_hash=f"hash-{job_id}",
            extractor_version="rules-1",
            analysis_status="partial",
            field_statuses=estados,
            requirements=requisitos,
        )

    def _huecos(self):
        with closing(sqlite3.connect(self.database.path)) as connection:
            connection.row_factory = sqlite3.Row
            return perfil_huecos.calcular_huecos(connection)


class TestCalculoHuecos(BasePerfilHuecos):
    def test_detecta_lo_que_el_corpus_pide(self):
        self._analizar([_requisito("skill", "python", level="required")])
        huecos = self._huecos()
        skills = huecos.por_categoria()["skill"]
        self.assertEqual([h.codigo for h in skills], ["python"])
        self.assertEqual(skills[0].avisos, 1)
        self.assertEqual(skills[0].categoria, "skill")
        self.assertEqual(skills[0].niveles, ("required",))

    def test_relleno_una_sola_vez(self):
        """Al registrar el dato, el hueco desaparece (idempotente)."""
        self._analizar([_requisito("skill", "python", level="required")])
        self.assertIn("python", [h.codigo for h in self._huecos().faltan])

        self.repository.save_candidate_profile_facts(
            [{"category": "skill", "value_code": "python", "value_text": "Python"}]
        )
        self.assertNotIn("python", [h.codigo for h in self._huecos().faltan])

        # Recalcular otra vez no lo vuelve a mostrar.
        self.assertNotIn("python", [h.codigo for h in self._huecos().faltan])

    def test_preferred_no_genera_hueco(self):
        self._analizar([_requisito("skill", "python", level="preferred")])
        self.assertEqual(self._huecos().faltan, ())

    def test_requisito_sin_codigo_canonico_no_genera_hueco(self):
        """Sin codigo el motor lo ignora: tampoco debe prometerse como hueco."""
        with closing(sqlite3.connect(self.database.path)) as connection:
            connection.execute(
                "INSERT OR IGNORE INTO concepto "
                "(categoria, variante, codigo_canonico, origen) VALUES "
                "('skill', 'zzz-sin-concepto', NULL, 'test')"
            )
            connection.commit()
        self._analizar([_requisito("skill", "zzz-sin-concepto")])
        self.assertEqual(
            [h.codigo for h in self._huecos().faltan if h.categoria == "skill"], []
        )

    def test_solo_las_categorias_que_el_motor_lee(self):
        self._analizar(
            [
                _requisito("skill", "python"),
                _requisito("experience", "5-years"),
            ]
        )
        categorias = {h.categoria for h in self._huecos().faltan}
        self.assertEqual(categorias, {"skill"})

    def test_ordenado_por_numero_de_avisos(self):
        self.repository.save_job(
            {
                "job_id": "job-2",
                "title": "Otro",
                "company": "Acme",
                "country": "CR",
                "description_raw": "Python otra vez.",
            },
            site_id="acme-cr",
            source_job_id="J-2",
        )
        self._analizar([_requisito("skill", "excel"), _requisito("skill", "python")])
        self._analizar([_requisito("skill", "python")], job_id="job-2")
        skills = self._huecos().por_categoria()["skill"]
        self.assertEqual([h.codigo for h in skills], ["python", "excel"])
        self.assertEqual([h.avisos for h in skills], [2, 1])

    def test_es_agnostico_del_titular(self):
        """Los huecos salen de la BD: cambian si cambian los datos."""
        self._analizar([_requisito("skill", "python")])
        primeros = [h.codigo for h in self._huecos().faltan]

        # Otro perfil con otros datos -> otros huecos, sin tocar el corpus.
        self.repository.clear_candidate_profile_facts()
        self.repository.save_candidate_profile_facts(
            [{"category": "skill", "value_code": "python", "value_text": "Python"}]
        )
        segundos = [h.codigo for h in self._huecos().faltan]

        self.assertEqual(primeros, ["python"])
        self.assertEqual(segundos, [])

    def test_solo_lectura_no_encola_nada(self):
        self._analizar([_requisito("skill", "zzz-no-existe")])
        with closing(sqlite3.connect(self.database.path)) as connection:
            antes = connection.execute(
                "SELECT COUNT(*) FROM concepto_no_normalizado"
            ).fetchone()[0]
        self._huecos()
        with closing(sqlite3.connect(self.database.path)) as connection:
            despues = connection.execute(
                "SELECT COUNT(*) FROM concepto_no_normalizado"
            ).fetchone()[0]
        self.assertEqual(antes, despues)

    def test_areas_sin_marcar_muestrado_catalogo(self):
        huecos = self._huecos()
        self.assertEqual(huecos.areas_marcadas, ())
        # La migracion siembra el catalogo de areas.
        self.assertTrue(huecos.areas_catalogo)
        self.assertFalse(huecos.vacios)

    def test_area_marcada_deja_de_ser_hueco(self):
        self.repository.save_candidate_profile_facts(
            [{"category": "area", "value_code": "informatica", "value_text": "InformÃ¡tica"}]
        )
        self.assertIn("informatica", self._huecos().areas_marcadas)

    def test_hecho_motor_sin_codigo_se_reporta(self):
        with closing(sqlite3.connect(self.database.path)) as connection:
            connection.execute(
                "INSERT INTO candidate_profile_facts "
                "(category, value_code, value_text) VALUES "
                "('skill', 'sin-resolver', 'Sin resolver')"
            )
            connection.commit()
        huecos = self._huecos()
        self.assertEqual(len(huecos.sin_canonico), 1)
        self.assertEqual(huecos.sin_canonico[0].categoria, "skill")
        self.assertFalse(huecos.vacios)

    def test_categorias_cerradas_traen_opciones(self):
        huecos = self._huecos()
        cerradas = {o.categoria for o in huecos.opciones}
        self.assertTrue(cerradas <= {"education", "license"})


class TestStorePerfil(BasePerfilHuecos):
    """La capa de datos de la UI expone la MISMA implementacion."""

    def setUp(self):
        super().setUp()
        self.store = ProfileStore(self.repository)

    def test_store_huecos_usa_la_implementacion_unica(self):
        self._analizar([_requisito("skill", "python", level="required")])
        huecos = self.store.huecos()
        self.assertIn("python", [h.codigo for h in huecos.faltan])
        self.assertEqual(huecos.resumen_linea(), "skill 1")

    def test_store_huecos_refleja_lo_guardado(self):
        self._analizar([_requisito("skill", "python", level="required")])
        self.store.save("skill", "python", "Python")
        self.assertNotIn("python", [h.codigo for h in self.store.huecos().faltan])

    def test_reemplazar_perfil_borra_lo_anterior(self):
        """Cargar a OTRA persona: el perfil se limpia, el corpus no."""
        self._analizar([_requisito("skill", "python", level="required")])
        self.store.save("skill", "python", "Python")
        self.store.save("language", "en", "InglÃ©s")
        self.assertEqual(len(self.store.load()), 2)

        borrado = self.store.reemplazar()

        self.assertEqual(borrado["hechos"], 2)
        self.assertEqual(self.store.load(), [])
        # El corpus sigue intacto.
        with closing(sqlite3.connect(self.database.path)) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 1
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM job_requirements").fetchone()[0],
                1,
            )
        # Y los huecos vuelven (el perfil quedo vacio).
        self.assertIn("python", [h.codigo for h in self.store.huecos().faltan])

    def test_reemplazar_perfil_puede_guardar_lo_nuevo(self):
        self.store.save("skill", "python", "Python")
        self.store.reemplazar(
            [{"category": "skill", "value_code": "excel", "value_text": "Excel"}]
        )
        hechos = self.store.load()
        self.assertEqual([h.value_code for h in hechos], ["excel"])

    def test_reemplazar_borra_las_importaciones(self):
        """Si no se borran, 'Revertir importaciÃ³n' restaurarÃ­a al anterior."""
        self.store.import_facts(
            "cv-viejo",
            [{"category": "skill", "value_code": "python", "value_text": "Python"}],
        )
        self.assertEqual(len(self.store.importaciones()), 1)
        self.store.reemplazar()
        self.assertEqual(self.store.importaciones(), [])
        self.assertIsNone(self.store.revertir_ultima())


if __name__ == "__main__":
    unittest.main()

