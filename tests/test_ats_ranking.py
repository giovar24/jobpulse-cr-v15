# -*- coding: utf-8 -*-
"""Tests del RANKING ATS (simulacion de ATS) sobre los requisitos reales.

Cubre:
1. El puente perfil -> ATS (hechos de ``candidate_profile_facts``).
2. La cobertura de skills (ruido de fabricantes, alias, subconjuntos).
3. El score: componentes sin dato NO penalizan, "preferred" no bloquea,
   la regla de idioma del aviso y los veredictos.
4. El store de la UI v2 (rankea avisos contra el perfil).
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15.ats import (
    PESOS_RANKING,
    VEREDICTO_SIN_DATOS,
    cobertura_skills,
    componentes_ats,
    es_frase_de_tarea,
    perfil_ats_desde_facts,
    promedios_componentes,
    ranking_ats,
    skills_utiles,
)
from jobpulse_v15.db import Database
from jobpulse_v15.repository import Repository
from jobpulse_v15.ui_v2.data.vacantes import AtsStore, exportar_csv, filtrar, resumen

HECHOS_PERFIL = [
    {
        "category": "skill", "value_code": "active-directory",
        "value_text": "Active Directory", "qualifier": None,
    },
    {
        "category": "skill", "value_code": "excel-avanzado",
        "value_text": "Excel Avanzado", "qualifier": "avanzado",
    },
    {
        "category": "skill", "value_code": "servicenow",
        "value_text": "ServiceNow", "qualifier": None,
    },
    {
        "category": "experience", "value_code": "total",
        "value_text": "Profesional de Soporte IT", "numeric_value": 16.0, "unit": "años",
    },
    {
        "category": "experience", "value_code": "auxis-it",
        "value_text": "IT Support & Application Support Analyst — Auxis (04/2022 a 08/2023)",
        "numeric_value": 1.3, "unit": "años",
    },
    {
        "category": "language", "value_code": "ingles",
        "value_text": "Inglés", "qualifier": "B2",
    },
    {
        "category": "language", "value_code": "espanol",
        "value_text": "Español", "qualifier": "Nativo",
    },
    {
        "category": "education", "value_code": "bachiller-en-educacion-media",
        "value_text": "Bachiller en Educación Media — MEP", "education_status": "completed",
    },
    {
        "category": "education", "value_code": "diplomado-en-electronica",
        "value_text": "Diplomado en Electrónica — INTEC", "education_status": "completed",
    },
    {
        "category": "summary", "value_code": "perfil-profesional",
        "value_text": "Profesional de Soporte IT con más de 14 años de experiencia",
    },
]


class TestPerfilAts(unittest.TestCase):
    """El puente desde los hechos del perfil."""

    def setUp(self):
        self.perfil = perfil_ats_desde_facts(HECHOS_PERFIL)

    def test_toma_las_skills_del_perfil(self):
        self.assertIn("Active Directory", self.perfil["skills"])
        self.assertIn("ServiceNow", self.perfil["skills"])

    def test_el_total_de_experiencia_manda_sobre_los_puestos(self):
        self.assertEqual(self.perfil["experiencia_anios"], 16.0)

    def test_sin_total_suma_los_puestos(self):
        hechos = [h for h in HECHOS_PERFIL if h["value_code"] != "total"]
        self.assertEqual(perfil_ats_desde_facts(hechos)["experiencia_anios"], 1.3)

    def test_traduce_los_codigos_de_idioma(self):
        self.assertEqual(self.perfil["idiomas"], {"es": "nativo", "en": "b2"})

    def test_toma_el_mejor_nivel_educativo(self):
        # bachiller (1) + diplomado (2) -> el mejor
        self.assertEqual(self.perfil["educacion_nivel"], 2)
        self.assertFalse(self.perfil["educacion_en_curso"])

    def test_detecta_estudios_en_curso(self):
        hechos = [
            {
                "category": "education", "value_code": "licenciatura-informatica",
                "value_text": "Licenciatura en Informática", "education_status": "pursuing",
            }
        ]
        self.assertTrue(perfil_ats_desde_facts(hechos)["educacion_en_curso"])

    def test_extrae_el_cargo_de_la_experiencia(self):
        self.assertEqual(self.perfil["titulos"], ["IT Support & Application Support Analyst"])


class TestCoberturaSkills(unittest.TestCase):
    """Cotejo de skills del aviso contra las del perfil."""

    def test_el_fabricante_no_impide_la_cobertura(self):
        pct, cubiertas, faltantes = cobertura_skills(["Microsoft Excel"], ["Excel Avanzado"])
        self.assertEqual(cubiertas, ["Microsoft Excel"])
        self.assertEqual(faltantes, [])
        self.assertEqual(pct, 100.0)

    def test_el_alias_de_fabricante_cubre(self):
        _, cubiertas, _ = cobertura_skills(["Amazon Web Services"], ["AWS"])
        self.assertEqual(cubiertas, ["Amazon Web Services"])

    def test_una_skill_que_no_esta_falta(self):
        _, _, faltantes = cobertura_skills(["Kubernetes"], ["Active Directory", "AWS"])
        self.assertEqual(faltantes, ["Kubernetes"])

    def test_el_subconjunto_cubre(self):
        _, cubiertas, _ = cobertura_skills(["SQL"], ["SQL Server"])
        self.assertEqual(cubiertas, ["SQL"])

    def test_el_mismo_concepto_se_cuenta_una_sola_vez(self):
        pct, cubiertas, faltantes = cobertura_skills(
            ["Microsoft Excel", "Excel avanzado"], ["Excel Avanzado"]
        )
        self.assertEqual(cubiertas, ["Microsoft Excel"])
        self.assertEqual(faltantes, [])
        self.assertEqual(pct, 100.0)

    def test_sin_skills_no_hay_que_cubrir(self):
        self.assertEqual(cobertura_skills([], ["AWS"]), (None, [], []))


class TestRankingAts(unittest.TestCase):
    """El score: componentes, redistributed y veredictos."""

    def setUp(self):
        self.perfil = perfil_ats_desde_facts(HECHOS_PERFIL)

    def test_sin_datos_no_hay_score(self):
        ranking = ranking_ats(self.perfil)
        self.assertTrue(ranking.sin_datos)
        self.assertIsNone(ranking.total)
        self.assertEqual(ranking.veredicto, VEREDICTO_SIN_DATOS)

    def test_el_peso_se_redistribuye_entre_los_componentes_con_dato(self):
        ranking = ranking_ats(
            self.perfil,
            requisitos=[
                {
                    "category": "skill", "value_code": "active-directory",
                    "value_text": "Active Directory", "requirement_level": "required",
                }
            ],
        )
        self.assertEqual(set(ranking.pesos_usados), {"skills"})
        self.assertAlmostEqual(sum(ranking.pesos_usados.values()), 1.0)
        self.assertEqual(ranking.componentes["skills"].pct, 100.0)
        self.assertAlmostEqual(ranking.total, 100.0, places=1)

    def test_con_imputacion_los_pesos_son_fijos(self):
        """Con imputacion el score es comparable entre avisos: un aviso sin
        dato en un componente toma el promedio del corpus y el resto de los
        pesos NO se redistribuyen."""
        ranking = ranking_ats(
            self.perfil,
            imputacion={
                "skills": 40.0, "experiencia": 100.0,
                "educacion": 50.0, "idiomas": 100.0,
            },
        )
        self.assertEqual(ranking.componentes["skills"].pct, 40.0)
        self.assertIn("promedio del corpus", ranking.componentes["skills"].detalle)
        esperado = (
            40.0 * PESOS_RANKING["skills"]
            + 100.0 * PESOS_RANKING["experiencia"]
            + 50.0 * PESOS_RANKING["educacion"]
            + 100.0 * PESOS_RANKING["idiomas"]
        )
        self.assertAlmostEqual(ranking.total, esperado, places=1)

    def test_sin_imputacion_el_componente_sin_dato_se_excluye(self):
        ranking = ranking_ats(self.perfil)
        self.assertIsNone(ranking.componentes["skills"].pct)
        self.assertNotIn("skills", ranking.pesos_usados)

    def test_preferred_no_penaliza(self):
        ranking = ranking_ats(
            self.perfil,
            requisitos=[
                {
                    "category": "skill", "value_code": "kubernetes",
                    "value_text": "Kubernetes", "requirement_level": "preferred",
                }
            ],
        )
        self.assertIsNone(ranking.componentes["skills"].pct)
        self.assertEqual(ranking.skills_faltantes, [])

    def test_usa_las_skills_extraidas_cuando_no_hay_requisitos(self):
        ranking = ranking_ats(self.perfil, skills_vacante=["Active Directory", "Kubernetes"])
        self.assertEqual(ranking.componentes["skills"].pct, 50.0)
        self.assertEqual(ranking.skills_faltantes, ["Kubernetes"])

    def test_la_experiencia_proporcional(self):
        ranking = ranking_ats(
            self.perfil,
            requisitos=[
                {
                    "category": "experience", "value_code": "years_experience",
                    "value_text": "5 years of experience", "minimum": 5.0, "unit": "years",
                    "requirement_level": "required",
                }
            ],
        )
        self.assertEqual(ranking.componentes["experiencia"].pct, 100.0)

    def test_sin_anos_en_el_perfil_no_penaliza(self):
        perfil = perfil_ats_desde_facts([h for h in HECHOS_PERFIL if h["category"] != "experience"])
        ranking = ranking_ats(
            perfil,
            requisitos=[
                {
                    "category": "experience", "value_code": "years_experience",
                    "value_text": "5 years", "minimum": 5.0, "unit": "years",
                    "requirement_level": "required",
                }
            ],
        )
        self.assertIsNone(ranking.componentes["experiencia"].pct)

    def test_educacion_no_cumple_si_el_perfil_no_llega(self):
        ranking = ranking_ats(
            self.perfil,
            requisitos=[
                {
                    "category": "education", "value_code": "bachelor",
                    "value_text": "Bachelor", "requirement_level": "required",
                }
            ],
        )
        # el perfil llega a nivel 2 (diplomado) y el aviso pide 4 (bachelor)
        self.assertEqual(ranking.componentes["educacion"].pct, 50.0)

    def test_estudios_en_curso_no_cumple(self):
        perfil = perfil_ats_desde_facts(
            [
                {
                    "category": "education", "value_code": "diplomado-en-electronica",
                    "value_text": "Diplomado en Electrónica", "education_status": "pursuing",
                }
            ]
        )
        ranking = ranking_ats(
            perfil,
            requisitos=[
                {
                    "category": "education", "value_code": "bachelor",
                    "value_text": "Bachelor", "requirement_level": "required",
                }
            ],
        )
        self.assertEqual(ranking.componentes["educacion"].pct, 0.0)

    def test_el_idioma_se_compara_con_su_nivel(self):
        ranking = ranking_ats(
            self.perfil,
            requisitos=[
                {
                    "category": "language", "value_code": "en",
                    "value_text": "English", "qualifier": "b2", "requirement_level": "required",
                }
            ],
        )
        self.assertEqual(ranking.componentes["idiomas"].pct, 100.0)

    def test_el_idioma_del_aviso_usa_el_codigo_del_corpus(self):
        """En el corpus los requisitos de idioma vienen como "espanol" /
        "ingles" (no "es"/"en"): sin normalizar, el perfil no casaba."""
        for codigo, perfil_codigo in (("espanol", "es"), ("ingles", "en")):
            ranking = ranking_ats(
                self.perfil,
                requisitos=[
                    {
                        "category": "language", "value_code": codigo,
                        "value_text": codigo, "qualifier": None,
                        "requirement_level": "required",
                    }
                ],
            )
            self.assertEqual(
                ranking.componentes["idiomas"].pct, 100.0, codigo
            )

    def test_un_idioma_exigente_baja_el_componente(self):
        ranking = ranking_ats(
            self.perfil,
            requisitos=[
                {
                    "category": "language", "value_code": "ingles",
                    "value_text": "Inglés", "qualifier": "c1",
                    "requirement_level": "required",
                }
            ],
        )
        # el perfil tiene B2 (3) y el aviso pide C1 (4): 3/4
        self.assertEqual(ranking.componentes["idiomas"].pct, 75.0)

    def test_un_idioma_que_no_se_tiene_no_cumple(self):
        ranking = ranking_ats(
            self.perfil,
            requisitos=[
                {
                    "category": "language", "value_code": "fr",
                    "value_text": "French", "qualifier": "b2", "requirement_level": "required",
                }
            ],
        )
        self.assertEqual(ranking.componentes["idiomas"].pct, 0.0)

    def test_veredictos_por_umbral(self):
        fuerte = ranking_ats(
            self.perfil,
            requisitos=[
                {
                    "category": "skill", "value_code": "active-directory",
                    "value_text": "Active Directory", "requirement_level": "required",
                },
                {
                    "category": "experience", "value_code": "years_experience",
                    "value_text": "5 years", "minimum": 5.0, "unit": "years",
                    "requirement_level": "required",
                },
                {
                    "category": "education", "value_code": "bachiller",
                    "value_text": "Bachiller", "requirement_level": "required",
                },
                {
                    "category": "language", "value_code": "ingles",
                    "value_text": "Inglés", "qualifier": "b2",
                    "requirement_level": "required",
                },
            ],
        )
        self.assertEqual(fuerte.veredicto, "fuerte")
        debil = ranking_ats(
            self.perfil,
            requisitos=[
                {
                    "category": "skill", "value_code": "kubernetes",
                    "value_text": "Kubernetes", "requirement_level": "required",
                },
                {
                    "category": "experience", "value_code": "years_experience",
                    "value_text": "50 years", "minimum": 50.0, "unit": "years",
                    "requirement_level": "required",
                },
                {
                    "category": "education", "value_code": "doctorado",
                    "value_text": "Doctorado", "requirement_level": "required",
                },
                {
                    "category": "language", "value_code": "fr",
                    "value_text": "French", "qualifier": "b2",
                    "requirement_level": "required",
                },
            ],
        )
        self.assertEqual(debil.veredicto, "debil")


class TestFiltroSkills(unittest.TestCase):
    """``jobs.skills`` mezcla herramientas con frases de tarea."""

    def test_una_frase_de_tarea_se_descarta(self):
        self.assertTrue(es_frase_de_tarea("elaborar cotizaciones"))
        self.assertTrue(es_frase_de_tarea("soporte a equipos Dell"))
        self.assertTrue(es_frase_de_tarea("account and inventory reconciliation"))

    def test_una_herramienta_se_conserva(self):
        self.assertFalse(es_frase_de_tarea("Active Directory"))
        self.assertFalse(es_frase_de_tarea("ServiceNow"))
        self.assertFalse(es_frase_de_tarea("SQL Server"))
        self.assertFalse(es_frase_de_tarea("Git"))

    def test_el_filtro_conserva_lo_util(self):
        utiles = skills_utiles(
            ["Active Directory", "elaborar cotizaciones", "ServiceNow", "Manejo de Retail Link"]
        )
        self.assertEqual(utiles, ["Active Directory", "ServiceNow"])


class TestPromedios(unittest.TestCase):
    """La imputacion: un componente sin dato toma el promedio del corpus."""

    def test_el_promedio_solo_cuenta_los_que_tienen_dato(self):
        perfil = perfil_ats_desde_facts(HECHOS_PERFIL)
        con_dato = componentes_ats(
            perfil,
            requisitos=[
                {
                    "category": "skill", "value_code": "active-directory",
                    "value_text": "Active Directory", "requirement_level": "required",
                }
            ],
        )
        sin_dato = componentes_ats(perfil)
        promedios = promedios_componentes([con_dato, sin_dato])
        self.assertEqual(promedios["skills"], 100.0)
        self.assertNotIn("experiencia", promedios)


class TestAtsStore(unittest.TestCase):
    """El store rankea los avisos contra el perfil."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "ats.db")
        self.database.initialize()
        self.repository = Repository(self.database)
        self.repository.register_platform("workday", "Workday", "api")
        self.repository.register_site(
            "intel-cr", "workday", "Intel Careers CR",
            "https://intel.example.test", company_name="Intel", country="CR",
        )
        self.repository.save_candidate_profile_facts(HECHOS_PERFIL)

        self._guardar_aviso(
            "workday-REQ-1", "IT Support Specialist", "Intel",
            "Soporte TI con Active Directory y ServiceNow. Se requiere inglés B2 "
            "y dos años de experiencia. Se requiere bachelor's degree.",
            ["Active Directory", "ServiceNow"],
            [("skill", "active-directory", "Active Directory", "required"),
             ("experience", "years_experience", "2 years of experience", "required")],
        )
        self._guardar_aviso(
            "workday-REQ-2", "Senior Accountant", "Acme",
            "Contabilidad general, balance y cierres. Se requiere Excel avanzado "
            "y cinco años de experiencia.",
            ["Excel avanzado", "Contabilidad general"],
            [("skill", "excel", "Microsoft Excel", "required"),
             ("experience", "years_experience", "5 years of experience", "required")],
        )
        self.store = AtsStore(self.repository)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _guardar_aviso(self, job_id, title, company, descripcion, skills, requisitos):
        self.repository.save_job(
            {
                "job_id": job_id,
                "title": title,
                "company": company,
                "country": "CR",
                "location_raw": "San Jose, Costa Rica",
                "posting_language": "en",
                "date_published": "2026-10-20",
                "description_raw": descripcion,
                "requirements_raw": descripcion,
            },
            site_id="intel-cr",
            source_job_id=job_id.split("-")[-1],
            source_url=f"https://intel.example.test/jobs/{job_id}",
        )
        import json

        with self.database.connection() as connection:
            connection.execute(
                "UPDATE jobs SET skills = ? WHERE job_id = ?",
                (json.dumps(skills), job_id),
            )
        self.repository.save_analysis(
            job_id,
            text_hash=f"hash-{job_id}",
            extractor_version="rules-1",
            analysis_status="complete",
            source_site_id="intel-cr",
            source_config_hash="cfg",
            field_statuses={"skill": "found", "experience": "found"},
            requirements=[
                {
                    "category": categoria,
                    "value_code": codigo,
                    "value_text": texto,
                    "requirement_level": nivel,
                    "origin": "rule",
                    "evidence": texto,
                }
                for categoria, codigo, texto, nivel in requisitos
            ],
        )

    def test_ordena_por_score_y_deshace_el_ganador(self):
        filas = self.store.calcular()
        self.assertEqual(len(filas), 2)
        # el aviso de soporte encaja con el perfil; el de contabilidad, no
        self.assertEqual(filas[0].title, "IT Support Specialist")
        self.assertGreater(filas[0].score, filas[1].score)
        self.assertEqual(filas[1].skills_faltantes, ("Contabilidad general",))

    def test_el_score_sale_sin_embeddings(self):
        filas = self.store.calcular()
        self.assertIsNotNone(filas[0].score)

    def test_las_skills_faltantes_son_las_del_aviso(self):
        filas = {fila.title: fila for fila in self.store.calcular()}
        self.assertEqual(
            filas["IT Support Specialist"].skills_cubiertas,
            ("Active Directory", "ServiceNow"),
        )

    def test_filtra_por_texto_y_veredicto(self):
        filas = self.store.calcular()
        self.assertEqual(len(filtrar(filas, texto="accountant")), 1)
        # el aviso de soporte TI es el que mejor encaja: es el "fuerte"
        fuertes = filtrar(filas, veredicto="fuerte")
        self.assertIn("IT Support Specialist", [fila.title for fila in fuertes])
        self.assertEqual(filas[0].title, "IT Support Specialist")
        # y el de contabilidad es el que tiene el gap de skills
        self.assertEqual(filas[1].skills_faltantes, ("Contabilidad general",))

    def test_resumen_cuenta_por_veredicto(self):
        cifras = resumen(self.store.calcular())
        self.assertEqual(cifras["total"], 2)
        self.assertEqual(cifras["fuerte"] + cifras["ajustable"] + cifras["debil"], 2)

    def test_exporta_csv(self):
        filas = self.store.calcular()
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "ranking.csv"
            self.assertEqual(exportar_csv(filas, ruta), 2)
            contenido = ruta.read_text(encoding="utf-8-sig")
            self.assertIn("IT Support Specialist", contenido)
            self.assertIn("Microsoft Excel", contenido)


if __name__ == "__main__":
    unittest.main()
