# -*- coding: utf-8 -*-
"""RE-ANALISIS INCREMENTAL: que la UI vea lo mismo que la CLI (O12 · Ola 1.1/1.2).

El hueco que separaba la CLI de las UIs: el analisis se hacia ANTES del pase
IA, asi que ``jobs.skills`` / ``jobs.languages`` (que produce la IA) nunca se
convertian en requisitos comparables. La CLI lo resolvia con
``enrich requirements-source --apply`` (re-analisis de TODO); las UIs no
tenian ese paso -> 231 avisos quedaban ``sin_requisitos`` (vs 11 de la CLI).

REGLAS DURAS que estos tests fijan:

1. "obsoleto" = el aviso TIENE campos estructurados y su analisis vigente NO
   los integro (0 requisitos ``origin='source_field'``);
2. un aviso SIN campos estructurados nunca es candidato (no hay nada que
   integrar);
3. el re-analisis solo guarda si el resultado **cambia** (no se infla el
   historial de ``job_analysis``);
4. es **idempotente**: la segunda llamada no encuentra candidatos;
5. el aviso sin texto (descripcion y requisitos vacios) no rompe el lote.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15.analysis_flow import (  # noqa: E402
    analisis_refleja_campos,
    avisos_con_campos_sin_integrar,
    avisos_con_texto_cambiado,
    cuenta_analisis_obsoletos,
    extract_job_analysis,
    reananalizar_con_campos_fuente,
    reananalizar_texto_cambiado,
)
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

    def _job(self, job_id="job-1", **campos):
        datos = {
            "job_id": job_id,
            "title": "Support Engineer",
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
        return job_id

    def _poner_campos(self, job_id, skills=None, languages=None):
        """Simula lo que hace el pase IA: llenar los campos estructurados."""
        with self.database.connection() as connection:
            if skills is not None:
                connection.execute(
                    "UPDATE jobs SET skills = ? WHERE job_id = ?",
                    (skills, job_id),
                )
            if languages is not None:
                connection.execute(
                    "UPDATE jobs SET languages = ? WHERE job_id = ?",
                    (languages, job_id),
                )

    def _analisis_vigentes(self, job_id):
        with self.database.connection() as connection:
            filas = connection.execute(
                """
                SELECT a.analysis_id, a.is_current, a.extractor_version
                FROM job_analysis AS a
                WHERE a.job_id = ?
                ORDER BY a.analysis_id
                """,
                (job_id,),
            ).fetchall()
        return [dict(fila) for fila in filas]

    def _requisitos(self, job_id):
        with self.database.connection() as connection:
            filas = connection.execute(
                """
                SELECT r.category, r.value_text, r.origin, r.codigo_canonico
                FROM job_requirements AS r
                JOIN job_analysis AS a ON a.analysis_id = r.analysis_id
                WHERE a.job_id = ? AND a.is_current = 1
                ORDER BY r.requirement_id
                """,
                (job_id,),
            ).fetchall()
        return [dict(fila) for fila in filas]


class TestDeteccionDeObsoletos(Base):
    """1.2 · quien tiene el analisis obsoleto."""

    def test_un_aviso_con_skills_y_analisis_viejo_es_candidato(self):
        job_id = self._job()
        extract_job_analysis(self.repository, job_id)  # analisis ANTES de la IA
        self._poner_campos(job_id, skills=json.dumps(["Python"]))

        self.assertEqual(avisos_con_campos_sin_integrar(self.repository), [job_id])
        self.assertEqual(cuenta_analisis_obsoletos(self.repository), 1)

    def test_un_aviso_sin_campos_estructurados_no_es_candidato(self):
        job_id = self._job()
        extract_job_analysis(self.repository, job_id)

        self.assertEqual(avisos_con_campos_sin_integrar(self.repository), [])

    def test_un_aviso_ya_integrado_no_es_candidato(self):
        job_id = self._job()
        extract_job_analysis(self.repository, job_id)
        self._poner_campos(job_id, skills=json.dumps(["Python"]))
        reananalizar_con_campos_fuente(self.repository)

        self.assertEqual(avisos_con_campos_sin_integrar(self.repository), [])

    def test_un_aviso_sin_analisis_no_es_candidato(self):
        # Sin analisis vigente no hay nada que "reflejar": lo crea el paso
        # normal de analisis, no el re-analisis.
        job_id = self._job()
        self._poner_campos(job_id, skills=json.dumps(["Python"]))

        self.assertEqual(avisos_con_campos_sin_integrar(self.repository), [])

    def test_los_campos_vacios_no_cuentan_como_dato(self):
        job_id = self._job()
        extract_job_analysis(self.repository, job_id)
        self._poner_campos(job_id, skills="[]", languages="{}")

        self.assertEqual(avisos_con_campos_sin_integrar(self.repository), [])

    def test_detecta_tambien_los_idiomas(self):
        job_id = self._job()
        extract_job_analysis(self.repository, job_id)
        self._poner_campos(job_id, languages=json.dumps({"ingles": "B2"}))

        self.assertEqual(cuenta_analisis_obsoletos(self.repository), 1)


class TestReanalisisIncremental(Base):
    """1.1 · el re-análisis que faltaba en las UIs."""

    def test_reanaliza_e_integra_los_campos_estructurados(self):
        job_id = self._job()
        extract_job_analysis(self.repository, job_id)
        self._poner_campos(job_id, skills=json.dumps(["Python", "SQL"]))

        stats = reananalizar_con_campos_fuente(self.repository)

        self.assertEqual(stats["candidatos"], 1)
        self.assertEqual(stats["reanalizados"], 1)
        self.assertEqual(stats["errores"], 0)
        origenes = {fila["origin"] for fila in self._requisitos(job_id)}
        self.assertIn("source_field", origenes)
        codigos = {fila["codigo_canonico"] for fila in self._requisitos(job_id)}
        self.assertIn("python", codigos)

    def test_no_inventa_filas_de_job_analysis(self):
        # El texto del aviso no cambio: el `text_hash` es el mismo y el
        # guardado hace UPSERT (actualiza la fila vigente). El historial
        # queda auditable sin inflarlo.
        job_id = self._job()
        extract_job_analysis(self.repository, job_id)
        self._poner_campos(job_id, skills=json.dumps(["Python"]))

        reananalizar_con_campos_fuente(self.repository)

        analyses = self._analisis_vigentes(job_id)
        self.assertEqual(len(analyses), 1)
        self.assertEqual(analyses[0]["is_current"], 1)

    def test_es_idempotente(self):
        job_id = self._job()
        extract_job_analysis(self.repository, job_id)
        self._poner_campos(job_id, skills=json.dumps(["Python"]))
        reananalizar_con_campos_fuente(self.repository)

        segunda = reananalizar_con_campos_fuente(self.repository)

        self.assertEqual(segunda["candidatos"], 0)
        self.assertEqual(segunda["reanalizados"], 0)
        self.assertEqual(len(self._analisis_vigentes(job_id)), 1)

    def test_el_dry_run_no_guarda_nada(self):
        job_id = self._job()
        extract_job_analysis(self.repository, job_id)
        self._poner_campos(job_id, skills=json.dumps(["Python"]))

        stats = reananalizar_con_campos_fuente(self.repository, dry_run=True)

        self.assertEqual(stats["candidatos"], 1)
        self.assertEqual(stats["reanalizados"], 1)
        origenes = {fila["origin"] for fila in self._requisitos(job_id)}
        self.assertNotIn("source_field", origenes)

    def test_avisa_el_progreso(self):
        job_id = self._job()
        extract_job_analysis(self.repository, job_id)
        self._poner_campos(job_id, skills=json.dumps(["Python"]))
        mensajes = []

        reananalizar_con_campos_fuente(self.repository, on_progress=mensajes.append)

        self.assertTrue(any(job_id in mensaje for mensaje in mensajes), mensajes)

    def test_analisis_refleja_campos_antes_y_despues(self):
        job_id = self._job()
        extract_job_analysis(self.repository, job_id)
        self._poner_campos(job_id, skills=json.dumps(["Python"]))

        self.assertFalse(analisis_refleja_campos(self.repository, job_id))

        reananalizar_con_campos_fuente(self.repository)

        self.assertTrue(analisis_refleja_campos(self.repository, job_id))

    def test_un_aviso_sin_texto_no_rompe_el_lote(self):
        vacio = self._job(job_id="job-vacio", description_raw="   ")
        ok = self._job(job_id="job-ok")
        extract_job_analysis(self.repository, ok)
        self._poner_campos(ok, skills=json.dumps(["Python"]))
        self._poner_campos(vacio, skills=json.dumps(["Python"]))

        stats = reananalizar_con_campos_fuente(self.repository)

        # El vacio no se puede analizar (no tiene texto): no es error del lote.
        self.assertEqual(stats["candidatos"], 1)
        self.assertEqual(stats["reanalizados"], 1)
        self.assertEqual(stats["errores"], 0)

    def test_no_toca_los_avisos_que_no_necesitan_reanalisis(self):
        job_id = self._job()
        extract_job_analysis(self.repository, job_id)

        stats = reananalizar_con_campos_fuente(self.repository)

        self.assertEqual(stats["candidatos"], 0)
        self.assertEqual(stats["reanalizados"], 0)


class TestReanalisisPorTextoNuevo(Base):
    """Ola 4.1: el scraper trajo MÁS texto del que se había analizado.

    Caso real (2026-11-06): el parser de ANE no leía "Nivel académico" ni
    "Experiencia laboral" de la ficha. Al arreglarlo, el texto del aviso
    cambia → el ``text_hash`` del análisis vigente ya no describe al aviso y
    hay que re-analizarlo (si no, el motor evalúa el texto viejo).
    """

    def _cambiar_texto(self, job_id, texto):
        with self.database.connection() as connection:
            connection.execute(
                "UPDATE jobs SET description_raw = ? WHERE job_id = ?",
                (texto, job_id),
            )

    def test_un_aviso_con_texto_nuevo_es_candidato(self):
        job_id = self._job()
        extract_job_analysis(self.repository, job_id)
        self._cambiar_texto(
            job_id,
            "Buscamos una persona con experiencia en el area. "
            "Nivel academico: Licenciatura. Experiencia laboral: 2 anos.",
        )

        self.assertEqual(avisos_con_texto_cambiado(self.repository), [job_id])

    def test_un_aviso_sin_cambio_no_es_candidato(self):
        job_id = self._job()
        extract_job_analysis(self.repository, job_id)

        self.assertEqual(avisos_con_texto_cambiado(self.repository), [])

    def test_reanaliza_y_el_analisis_vigente_describe_el_texto_nuevo(self):
        job_id = self._job()
        extract_job_analysis(self.repository, job_id)
        self._cambiar_texto(
            job_id,
            "Se requiere licencia de conducir B1 para la flota de la empresa.",
        )

        stats = reananalizar_texto_cambiado(self.repository)

        self.assertEqual(stats["candidatos"], 1)
        self.assertEqual(stats["reanalizados"], 1)
        self.assertEqual(stats["errores"], 0)
        self.assertEqual(avisos_con_texto_cambiado(self.repository), [])
        # El texto nuevo se ve en los requisitos del análisis vigente.
        textos = " ".join(fila["value_text"] for fila in self._requisitos(job_id))
        self.assertIn("B1", textos)

    def test_es_idempotente(self):
        job_id = self._job()
        extract_job_analysis(self.repository, job_id)
        self._cambiar_texto(job_id, "Otro texto completamente distinto.")
        reananalizar_texto_cambiado(self.repository)

        segunda = reananalizar_texto_cambiado(self.repository)

        self.assertEqual(segunda["candidatos"], 0)
        self.assertEqual(segunda["reanalizados"], 0)

    def test_el_dry_run_no_guarda_nada(self):
        job_id = self._job()
        extract_job_analysis(self.repository, job_id)
        self._cambiar_texto(job_id, "Texto nuevo que no se debe guardar todavia.")

        stats = reananalizar_texto_cambiado(self.repository, dry_run=True)

        self.assertEqual(stats["candidatos"], 1)
        self.assertEqual(stats["reanalizados"], 1)
        # Sigue pendiente (no se guardo nada).
        self.assertEqual(avisos_con_texto_cambiado(self.repository), [job_id])

    def test_un_aviso_sin_texto_no_rompe_el_lote(self):
        """Un aviso que se quedó sin texto no se re-analiza ni rompe el lote.

        Sin texto no hay nada que analizar (`preparar_analisis` lanza), así que
        el aviso se salta (no se toca su análisis vigente) y el resto del
        lote sigue.
        """
        vacio = self._job(job_id="job-vacio")
        ok = self._job(job_id="job-ok")
        extract_job_analysis(self.repository, ok)
        extract_job_analysis(self.repository, vacio)
        self._cambiar_texto(ok, "Texto nuevo del aviso bueno.")
        self._cambiar_texto(vacio, "   ")

        stats = reananalizar_texto_cambiado(self.repository)

        self.assertEqual(stats["errores"], 0)
        self.assertEqual(stats["reanalizados"], 1)
        # El aviso sin texto no entra ni como candidato ni como error.
        self.assertNotIn(vacio, avisos_con_texto_cambiado(self.repository))

    def test_avisa_el_progreso(self):
        job_id = self._job()
        extract_job_analysis(self.repository, job_id)
        self._cambiar_texto(job_id, "Un texto nuevo para este aviso.")
        mensajes = []

        reananalizar_texto_cambiado(self.repository, on_progress=mensajes.append)

        self.assertTrue(any(job_id in mensaje for mensaje in mensajes), mensajes)


if __name__ == "__main__":
    unittest.main()
