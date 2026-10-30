# -*- coding: utf-8 -*-
"""Tests del modulo de matching (paso 5) y del bloqueante de educacion.

Patron: tempfile + Database + sqlite3 directo (no toca la BD real).
"""

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15 import matching
from jobpulse_v15.db import Database


def _crear_base(tmpdir: str) -> sqlite3.Connection:
    db = Database(Path(tmpdir) / "test.db")
    db.initialize()
    connection = sqlite3.connect(db.path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _insertar_fact(
    connection: sqlite3.Connection,
    code: str,
    canon: str,
    cat: str,
    education_status: str | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO candidate_profile_facts
            (category, value_code, value_text, codigo_canonico, education_status)
        VALUES (?, ?, ?, ?, ?)
        """,
        (cat, code, code, canon, education_status),
    )


def _insertar_job(
    connection: sqlite3.Connection,
    job_id: str,
    descripcion: str,
    requirements_raw: str | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO jobs (job_id, title, company, description_raw, requirements_raw)
        VALUES (?, ?, ?, ?, ?)
        """,
        (job_id, "Puesto de prueba", "Acme CR", descripcion, requirements_raw),
    )
    connection.execute(
        """
        INSERT INTO job_analysis
            (job_id, text_hash, extractor_version, analysis_status, is_current)
        VALUES (?, 'hash-test', 'test-v1', 'complete', 1)
        """,
        (job_id,),
    )


def _insertar_requisito(
    connection: sqlite3.Connection,
    job_id: str,
    value_code: str,
    canon: str,
    level: str,
    category: str = "education",
    value_text: str | None = None,
    minimum: float | None = None,
    education_status: str | None = None,
) -> None:
    analysis_id = connection.execute(
        "SELECT analysis_id FROM job_analysis WHERE job_id = ?", (job_id,)
    ).fetchone()["analysis_id"]
    connection.execute(
        """
        INSERT INTO job_requirements
            (analysis_id, category, value_code, value_text, requirement_level,
             minimum, codigo_canonico, origin, education_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'manual', ?)
        """,
        (
            analysis_id,
            category,
            value_code,
            value_text or value_code,
            level,
            minimum,
            canon,
            education_status,
        ),
    )


class TestConfirmacionTextual(unittest.TestCase):
    def test_confirma_bachelor_obligatorio(self):
        texto = (
            "We are looking for professionals. Bachelor's Degree in Accounting, "
            "Finance, or a related field. 5+ years of experience in Tax."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertTrue(resultado.confirmada)
        self.assertEqual(resultado.motivo, "confirmado")

    def test_no_confirma_si_dice_equivalent(self):
        texto = "Minimum Bachelor's degree or its equivalent. Strong MS Office skills."
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertFalse(resultado.confirmada)
        self.assertEqual(resultado.motivo, "alternativa")

    def test_no_confirma_si_dice_equivalent_experience(self):
        texto = "Bachelors/University degree or equivalent experience. 3+ years."
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertFalse(resultado.confirmada)
        self.assertEqual(resultado.motivo, "alternativa")

    def test_no_confirma_si_es_preferred(self):
        texto = "A four year college degree is preferred but not required."
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertFalse(resultado.confirmada)
        self.assertEqual(resultado.motivo, "negacion")

    def test_no_confirma_si_es_no_requerido(self):
        texto = "No se requiere bachillerato para el puesto."
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertFalse(resultado.confirmada)

    def test_bachiller_no_es_titulo_universitario(self):
        texto = "Se requiere bachiller en educacion media y 2 anos de experiencia."
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertFalse(resultado.confirmada)

    def test_bachelor_in_high_school_no_es_universitario(self):
        texto = "Basic Requirements: Bachelor in high school/Technical high school."
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertFalse(resultado.confirmada)

    def test_licenciatura_si_es_universitario(self):
        texto = "Requisitos: Licenciatura en Ingenieria Quimica, Mecanica o Industrial."
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertTrue(resultado.confirmada)

    def test_texto_vacio_no_confirma(self):
        self.assertFalse(matching.confirmar_requisito_universitario("").confirmada)
        self.assertFalse(matching.confirmar_requisito_universitario(None).confirmada)

    def test_maestria_cuenta_como_universitario(self):
        texto = "Se requiere maestria en ingenieria de datos."
        self.assertTrue(matching.confirmar_requisito_universitario(texto).confirmada)

    def test_segmentar_separa_por_frases_y_vinetas(self):
        partes = matching.segmentar("Uno. Dos · Tres\n- Cuatro")
        self.assertIn("Dos", partes)
        self.assertIn("Tres", partes)
        self.assertIn("Cuatro", partes)


class TestCasosReales(unittest.TestCase):
    """Casos literales tomados de la BD real (regresiones)."""

    def test_no_university_degree_required_no_confirma(self):
        texto = (
            "Excellent written and verbal communication skills. Fluent English, "
            "both written and spoken. No university degree required. What We Offer "
            "Fully remote position."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertFalse(resultado.confirmada)
        self.assertEqual(resultado.motivo, "negacion")

    def test_titulo_del_puesto_no_es_requisito(self):
        texto = (
            "Intern - Bachelor's Tech This role has been designed as 'Hybrid' with "
            "a requirement that you will work on average 2 days per week from an "
            "HPE office. Who We Are: Hewlett Packard Enterprise."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertFalse(resultado.confirmada)

    def test_associate_or_bachelors_es_alternativa(self):
        texto = (
            "Required Associate's or bachelor's degree in business, Finance, or a "
            "related field 1-2 years of experience in B2B credit, collections."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertFalse(resultado.confirmada)
        self.assertEqual(resultado.motivo, "alternativa")

    def test_bachelors_or_certification_es_alternativa(self):
        texto = (
            "Bachelor's degree or certification in Learning and Development, "
            "Education, Business, or a related field. 2+ years of experience."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertFalse(resultado.confirmada)
        self.assertEqual(resultado.motivo, "alternativa")

    def test_equivalent_practical_experience_es_alternativa(self):
        texto = (
            "Minimum Qualifications Bachelor's degree plus 5+ years of experience "
            "in technical compliance, security, risk, audit, or a related field; "
            "equivalent practical experience may be considered."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertFalse(resultado.confirmada)
        self.assertEqual(resultado.motivo, "alternativa")

    def test_or_a_combination_es_alternativa(self):
        texto = (
            "What We Look For Bachelor's degree, ECG certification, or an equivalent "
            "combination of education and relevant experience required."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertFalse(resultado.confirmada)
        self.assertEqual(resultado.motivo, "alternativa")

    def test_negacion_lejana_no_invalida_requisito_real(self):
        texto = (
            "A previous role preferred no travel. Minimum Qualifications Bachelor's "
            "degree in Accounting, Finance, or a related field. Minimum 2 years of "
            "professional accounting experience. Practical knowledge of core "
            "accounting principles."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertTrue(resultado.confirmada)

    def test_licenciatura_confirma(self):
        texto = (
            "Requisitos Licenciatura/Ingenieria completa en Ingenieria Quimica, "
            "Mecanica, Industrial, de Manufactura, Alimentos o areas relacionadas "
            "Mas de 5 anos de experiencia en ingenieria de procesos."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertTrue(resultado.confirmada)
        self.assertEqual(resultado.termino.lower(), "licenciatura")

    def test_or_other_technical_experience_es_alternativa(self):
        texto = (
            "Required Qualifications 80% completeness of a bachelor's degree "
            "program from a four-year college or university in Business "
            "Administration, Engineering or other technical/scientific experience. "
            "0-2 years supervisory experience."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertFalse(resultado.confirmada)
        self.assertEqual(resultado.motivo, "alternativa")

    def test_bachelor_con_master_alternativo_sigue_confirmando(self):
        texto = (
            "Our minimum requirements for this role · Bachelor's degree and 7 years "
            "of related experience, or a master's degree and 4 years of related "
            "experience, or a PhD and 1 year of related experience."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertTrue(resultado.confirmada)

    def test_advanced_university_studies_es_alternativa(self):
        """Literal de la BD: 'or advanced university studies' es otra VIA.

        'Bachelor's degree in Accounting, Finance, or a related field, or
        advanced university studies in Accounting' NO exige el titulo
        completado -> va a 'revisar_a_mano', no se descarta.
        """
        texto = (
            "Minimum Qualifications Bachelor's degree in Accounting, Finance, or a "
            "related field , or advanced university studies in Accounting. Minimum of "
            "2 years of professional accounting experience."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertFalse(resultado.confirmada)
        self.assertEqual(resultado.motivo, "alternativa")

    def test_advanced_coursework_es_alternativa(self):
        texto = (
            "To succeed in this role, you will need the following qualifications: "
            "University degree or advanced coursework in, Finance, Business "
            "Administration, Computer Science or related quantitative fields."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertFalse(resultado.confirmada)
        self.assertEqual(resultado.motivo, "alternativa")

    def test_equivalent_field_of_study_no_es_alternativa(self):
        """Literal: 'or equivalent field of study' sigue exigiendo un TITULO."""
        texto = (
            "Required Qualifications Bachelor's degree in engineering, Science, "
            "or equivalent field of study. 2 of experience in engineering related "
            "position."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertTrue(resultado.confirmada)
        self.assertEqual(resultado.motivo, "confirmado")
        self.assertTrue(resultado.obligatorio)

    def test_basic_qualifications_bachelor_degree_or_above_es_obligatorio(self):
        """Literal de la BD: encabezado 'Basic Qualifications' + 'or above'."""
        texto = (
            "About You Basic Qualifications 5+ years of experience managing "
            "contracts (including drafting and negotiation) in a corporate "
            "environment Bachelor's Degree or above"
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertTrue(resultado.confirmada)
        self.assertTrue(resultado.obligatorio)
        self.assertFalse(resultado.suave)

    def test_encabezado_qualifications_en_linea_separada_obliga(self):
        texto = (
            "Qualifications\nBachelor's degree in IT or a similar technology-related "
            "discipline. Minimum 8 years of IT experience."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertTrue(resultado.confirmada)
        self.assertTrue(resultado.obligatorio)

    def test_preferred_qualifications_no_hace_obligatorio_el_titulo(self):
        """'Preferred Qualifications' NO obliga: la vacante va a revision."""
        texto = (
            "Preferred Qualifications\nBachelor's degree in Marketing or "
            "Communications. Minimum 3 years of experience."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertFalse(resultado.confirmada)
        # El encabezado "Preferred Qualifications" es un SUAVIZADOR (el titulo
        # solo se prefiere), no una negacion dura ("not required").
        self.assertEqual(resultado.motivo, "suave")
        self.assertTrue(resultado.suave)

    def test_preferred_lejos_del_titulo_queda_como_suave(self):
        """'Preferred' fuera de la ventana de negacion -> marca 'suave'."""
        texto = (
            "Preferred Qualifications and certifications for this role: Bachelor's "
            "degree in Marketing or Communications."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertTrue(resultado.confirmada)
        self.assertFalse(resultado.obligatorio)
        self.assertTrue(resultado.suave)

    def test_experiencia_required_al_final_no_hace_obligatorio_el_titulo(self):
        texto = (
            "Bachelor's degree in Marketing. 3+ years of experience in digital "
            "marketing operations is required."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertTrue(resultado.confirmada)
        self.assertFalse(resultado.obligatorio)

    def test_currently_pursuing_es_requisito_de_estudiante_activo(self):
        """Literal: el requisito es 'estudiante activo', no titulo completado."""
        texto = (
            "Minimum Qualifications Currently pursuing a Bachelor's degree in "
            "Business Administration, Project Management, Marketing, Finance, Data "
            "Analytics, Engineering, or a related field. Must be enrolled as a "
            "full-time student at an accredited university throughout the "
            "internship period."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertTrue(resultado.confirmada)
        self.assertTrue(resultado.en_curso)
        self.assertTrue(resultado.obligatorio)

    def test_must_be_enrolled_es_estudiante_activo(self):
        texto = (
            "Basic Qualifications Currently pursuing a Bachelor's degree in Computer "
            "Science, Information Technology, or related field, with an anticipated "
            "graduation date of June/July 2027 Must be enrolled as a full-time student."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertTrue(resultado.en_curso)

    # -- regresiones de la medicion ampliada (43 casos, 2026-10-29) --------

    def test_alternativamente_anos_de_experiencia_es_alternativa(self):
        """Literal de la BD (workday-Accounts-Payable-Representative_J-020440).

        'Minimum Qualifications Bachelor's degree coursework in Accounting ... and
        1+ year of relevant experience; alternatively, 3+ years of relevant
        professional experience' ofrece OTRA VIA -> NO se descarta.
        """
        texto = (
            "Minimum Qualifications Bachelor's degree coursework in Accounting, "
            "Finance, Business Administration, or a related discipline and 1+ year "
            "of relevant experience; alternatively, 3+ years of relevant "
            "professional experience in Accounts Payable or"
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertFalse(resultado.confirmada)
        self.assertEqual(resultado.motivo, "alternativa")

    def test_preferred_del_masters_no_alcanza_al_bachelors(self):
        """Literal de la BD (workday-Data-Governance-Foundation-Lead-Analyst).

        'Education: Bachelor's/University degree, Master's degree preferred' ->
        el Bachelor's EXIGE y el Master's solo se prefiere: la coma corta el
        alcance del 'preferred'.
        """
        texto = (
            "Education: Bachelor's/University degree, Master's degree preferred"
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertTrue(resultado.confirmada)
        self.assertTrue(resultado.obligatorio)
        self.assertFalse(resultado.suave)

    def test_preferred_al_final_de_una_enumeracion_si_alcanza_a_todos(self):
        """Literal de la BD (workday-Commercial-Support-Specialist).

        "Who you are: Bachelor's or Master's degree preferred in Business
        Administration..." -> los DOS titulos son solo preferidos.
        """
        texto = (
            "Who you are: Bachelor's or Master's degree preferred in Business "
            "Administration, Finance, IT, or a related economics discipline."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertTrue(resultado.suave)
        self.assertFalse(resultado.obligatorio)

    def test_bachillerato_universitario_es_titulo_universitario(self):
        """Literal de la BD (workday-Analista-de-CPFR_887589).

        'Licenciatura o bachillerato universitario en Administracion de Empresas'
        -> ambos son titulos universitarios (en CR 'bachiller' a secas es
        secundaria; 'bachillerato universitario' es universitario).
        """
        texto = (
            "Para tener exito en este puesto, necesitaras las siguientes "
            "calificaciones: Licenciatura o bachillerato universitario en "
            "Administracion de Empresas, Ingenieria Industrial, Logistica, Supply "
            "Chain o una carrera afin."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertTrue(resultado.confirmada)
        self.assertTrue(resultado.obligatorio)

    def test_formacion_licenciatura_es_obligatorio(self):
        """Literal de la BD (cinde-4898): 'Formacion: Licenciatura.'"""
        texto = "Formacion: Licenciatura. Idiomas: Ingles-C1;Espanol-C2."
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertTrue(resultado.confirmada)
        self.assertTrue(resultado.obligatorio)

    def test_encabezado_job_requirements_gobierna_la_clausula_siguiente(self):
        """Literal de la BD (cinde-4892): 'Job Requirements: Active university
        student ...' gobierna 'Currently pursuing a Bachelor's degree ...'."""
        texto = (
            "Job Requirements: Active university student enrolled in an accredited "
            "university in Costa Rica. Currently pursuing a Bachelor's degree in "
            "one of the following (or related fields): o Computer Science o "
            "Software Engineering o Data Science."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertTrue(resultado.confirmada)
        self.assertTrue(resultado.obligatorio)
        self.assertTrue(resultado.en_curso)

    def test_further_requirements_es_encabezado(self):
        """Literal de la BD (workday-Digital-Campaign-Delivery-Associate)."""
        texto = (
            "Further requirements \u25cf Bachelor's degree in Marketing, Business, "
            "Communications, or a related field. \u25cf Strong understanding of "
            "digital marketing principles."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertTrue(resultado.confirmada)
        self.assertTrue(resultado.obligatorio)

    def test_what_you_need_to_bring_es_encabezado(self):
        """Literal de la BD (workday-Escalation-Engineer_1212930-2)."""
        texto = (
            "Calm decision-making under pressure ______________________ What you "
            "need to bring: \u2022 Bachelor's degree in Engineering / Computer "
            "Science / IT \u2022 2-4 years of experience"
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertTrue(resultado.confirmada)
        self.assertTrue(resultado.obligatorio)

    def test_role_requirements_es_encabezado(self):
        """Literal de la BD (workday-Sales-Commercial-Manager_R-257732)."""
        texto = (
            "Role Requirements Bachelor's degree in Business Administration, "
            "Marketing, Economics, Life Sciences, or a related field."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertTrue(resultado.confirmada)
        self.assertTrue(resultado.obligatorio)

    def test_required_al_final_del_titulo_lo_hace_obligatorio(self):
        """Literal de la BD (workday-Director--Manufacturing-Engineering).

        'Education & Experience Bachelor's degree in ... discipline required;
        master's degree or MBA preferred' -> el Bachelor's obliga; el 'preferred'
        del MBA no lo alcanza.
        """
        texto = (
            "Education & Experience Bachelor's degree in Manufacturing, Mechanical, "
            "Electrical, Industrial, or a related Engineering discipline required; "
            "master's degree or MBA preferred."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertTrue(resultado.confirmada)
        self.assertTrue(resultado.obligatorio)
        self.assertFalse(resultado.suave)

    def test_perfil_de_estudiante_activo_es_obligatorio(self):
        """Literal de la BD (workday-Document-Control-Intern_1210991)."""
        texto = (
            "Job Description: Job Family Definition: Students or recent graduates "
            "of college, university, or other accredited academic programs, "
            "pursuing diplomas or degrees (Associate, Bachelor's, Master's, or PhD) "
            "in any field."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertTrue(resultado.confirmada)
        self.assertTrue(resultado.obligatorio)
        self.assertTrue(resultado.en_curso)

    def test_university_students_actively_enrolled_es_obligatorio(self):
        """Literal de la BD (workday-Intern---Bachelors-Tech_1214077)."""
        texto = (
            "Impact/Scope: University students actively enrolled in a "
            "university/college/institution pursuing a Bachelor's degree in a "
            "technical area of study."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertTrue(resultado.confirmada)
        self.assertTrue(resultado.obligatorio)
        self.assertTrue(resultado.en_curso)

    def test_what_youll_need_required_es_encabezado(self):
        """Literal de la BD (workday-Senior-Director--Quality-Engineering)."""
        texto = (
            "What you'll need (Required): Bachelor's Degree in related field with "
            "at least 10 years experience in engineering and leadership positions "
            "in the medical device industry"
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertTrue(resultado.confirmada)
        self.assertTrue(resultado.obligatorio)
        self.assertFalse(resultado.suave)

    def test_education_con_espacio_y_dos_puntos_es_encabezado(self):
        """Literal de la BD (workday-US-Marketing-Governance)."""
        texto = (
            "Education : Bachelor's/University degree, Master's degree preferred"
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertTrue(resultado.confirmada)
        self.assertTrue(resultado.obligatorio)
        self.assertFalse(resultado.suave)

    def test_titulo_completado_no_es_estudiante_activo(self):
        texto = (
            "Required Qualifications Bachelor's degree in Engineering or a related "
            "technical field. Minimum 3 years of experience."
        )
        resultado = matching.confirmar_requisito_universitario(texto)
        self.assertTrue(resultado.confirmada)
        self.assertFalse(resultado.en_curso)


class TestEvaluadorPaso5(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.connection = _crear_base(self.tmpdir.name)
        _insertar_fact(self.connection, "bachiller-en-educacion-media", "educacion-secundaria", "education")
        _insertar_fact(self.connection, "excel", "excel", "skill")
        self.connection.commit()

    def tearDown(self):
        self.connection.close()
        self.tmpdir.cleanup()

    def test_descarta_si_texto_confirma_universitario(self):
        _insertar_job(
            self.connection,
            "job-1",
            "We are looking for professionals. Bachelor's Degree in Accounting required.",
        )
        _insertar_requisito(
            self.connection, "job-1", "bachelor", "educacion-universitaria", "required"
        )
        self.connection.commit()
        evaluador = matching.EvaluadorPaso5(self.connection)
        resultado = evaluador.evaluar_job("job-1")
        self.assertEqual(resultado.estado, matching.ESTADO_DESCARTADA)
        self.assertEqual(resultado.motivo, matching.MOTIVO_BLOQUEANTE)

    def test_revisa_si_hay_alternativa_equivale(self):
        _insertar_job(
            self.connection,
            "job-2",
            "Minimum Bachelor's degree or its equivalent. Strong MS Office skills.",
        )
        _insertar_requisito(
            self.connection, "job-2", "bachelor", "educacion-universitaria", "required"
        )
        self.connection.commit()
        evaluador = matching.EvaluadorPaso5(self.connection)
        resultado = evaluador.evaluar_job("job-2")
        self.assertEqual(resultado.estado, matching.ESTADO_REVISAR)
        self.assertEqual(resultado.motivo, matching.MOTIVO_EDUCACION_NO_CONFIRMADA)

    def test_revisa_si_no_hay_termino_en_el_texto(self):
        _insertar_job(self.connection, "job-3", "Excel Advanced and customer service.")
        _insertar_requisito(
            self.connection, "job-3", "bachelor", "educacion-universitaria", "required"
        )
        self.connection.commit()
        evaluador = matching.EvaluadorPaso5(self.connection)
        resultado = evaluador.evaluar_job("job-3")
        self.assertEqual(resultado.estado, matching.ESTADO_REVISAR)
        self.assertEqual(resultado.motivo, matching.MOTIVO_EDUCACION_NO_CONFIRMADA)

    def test_no_descarta_si_requisito_no_es_required(self):
        _insertar_job(
            self.connection,
            "job-4",
            "We are looking for professionals. Bachelor's Degree in Accounting.",
        )
        _insertar_requisito(
            self.connection, "job-4", "bachelor", "educacion-universitaria", "preferred"
        )
        self.connection.commit()
        evaluador = matching.EvaluadorPaso5(self.connection)
        resultado = evaluador.evaluar_job("job-4")
        self.assertNotEqual(resultado.estado, matching.ESTADO_DESCARTADA)

    def test_no_descarta_si_perfil_alcanza_nivel(self):
        _insertar_fact(self.connection, "licenciatura", "educacion-universitaria", "education")
        self.connection.commit()
        _insertar_job(
            self.connection,
            "job-5",
            "We are looking for professionals. Bachelor's Degree in Accounting.",
        )
        _insertar_requisito(
            self.connection, "job-5", "bachelor", "educacion-universitaria", "required"
        )
        self.connection.commit()
        evaluador = matching.EvaluadorPaso5(self.connection)
        resultado = evaluador.evaluar_job("job-5")
        self.assertNotEqual(resultado.estado, matching.ESTADO_DESCARTADA)

    def test_usa_requirements_raw_si_description_no_tiene_el_termino(self):
        _insertar_job(
            self.connection,
            "job-6",
            "Puesto de ventas en Heredia.",
            requirements_raw="Se requiere Bachelor degree en ingenieria.",
        )
        _insertar_requisito(
            self.connection, "job-6", "bachelor", "educacion-universitaria", "required"
        )
        self.connection.commit()
        evaluador = matching.EvaluadorPaso5(self.connection)
        resultado = evaluador.evaluar_job("job-6")
        self.assertEqual(resultado.estado, matching.ESTADO_DESCARTADA)

    def test_sin_requisitos_mapeados(self):
        _insertar_job(self.connection, "job-7", "Sin requisitos extraidos.")
        self.connection.commit()
        evaluador = matching.EvaluadorPaso5(self.connection)
        resultado = evaluador.evaluar_job("job-7")
        self.assertEqual(resultado.estado, matching.ESTADO_SIN_REQUISITOS)

    def test_descarta_por_el_texto_aunque_el_nivel_no_sea_required(self):
        """El TEXTO obliga aunque el extractor marque 'ambiguous'."""
        _insertar_job(
            self.connection,
            "job-8",
            "Required Qualifications Bachelor's degree in Computer Science or a "
            "related field. 5+ years of experience.",
        )
        _insertar_requisito(
            self.connection, "job-8", "bachelor", "educacion-universitaria", "ambiguous"
        )
        self.connection.commit()
        evaluador = matching.EvaluadorPaso5(self.connection)
        resultado = evaluador.evaluar_job("job-8")
        self.assertEqual(resultado.estado, matching.ESTADO_DESCARTADA)
        self.assertEqual(resultado.motivo, matching.MOTIVO_BLOQUEANTE)

    def test_no_descarta_si_el_texto_solo_lo_prefiere(self):
        """'Preferred' no bloquea, aunque el extractor marque 'required'."""
        _insertar_job(
            self.connection,
            "job-9",
            "Preferred Qualifications Bachelor's degree in Marketing or "
            "Communications. Minimum 3 years of experience.",
        )
        _insertar_requisito(
            self.connection, "job-9", "bachelor", "educacion-universitaria", "required"
        )
        self.connection.commit()
        evaluador = matching.EvaluadorPaso5(self.connection)
        resultado = evaluador.evaluar_job("job-9")
        self.assertEqual(resultado.estado, matching.ESTADO_REVISAR)
        self.assertEqual(resultado.motivo, matching.MOTIVO_EDUCACION_NO_CONFIRMADA)

    def test_requisito_de_estudiante_activo_tiene_motivo_propio(self):
        _insertar_job(
            self.connection,
            "job-10",
            "Minimum Qualifications Currently pursuing a Bachelor's degree in "
            "Business Administration or a related field. Must be enrolled as a "
            "full-time student at an accredited university throughout the "
            "internship period.",
        )
        _insertar_requisito(
            self.connection, "job-10", "bachelor", "educacion-universitaria", "required"
        )
        self.connection.commit()
        evaluador = matching.EvaluadorPaso5(self.connection)
        resultado = evaluador.evaluar_job("job-10")
        self.assertEqual(resultado.estado, matching.ESTADO_DESCARTADA)
        self.assertEqual(resultado.motivo, matching.MOTIVO_TITULO_EN_CURSO)

    def test_requisito_de_estudiante_activo_se_cumple_con_fact_pursuing(self):
        _insertar_fact(
            self.connection,
            "licenciatura-en-curso",
            "educacion-universitaria",
            "education",
            education_status="pursuing",
        )
        self.connection.commit()
        _insertar_job(
            self.connection,
            "job-11",
            "Minimum Qualifications Currently pursuing a Bachelor's degree in "
            "Business Administration or a related field. Must be enrolled as a "
            "full-time student.",
        )
        _insertar_requisito(
            self.connection, "job-11", "bachelor", "educacion-universitaria", "required"
        )
        self.connection.commit()
        evaluador = matching.EvaluadorPaso5(self.connection)
        resultado = evaluador.evaluar_job("job-11")
        self.assertNotEqual(resultado.estado, matching.ESTADO_DESCARTADA)


class TestSemanticaEducationStatus(unittest.TestCase):
    """Semantica de la AUSENCIA del fact 'pursuing' (acordada 2026-10-29).

    * Perfil con hechos educativos y NINGUNO 'pursuing' -> 'no cumple': el
      requisito de estudiante activo BLOQUEA (motivo propio).
    * Perfil SIN NINGUN hecho educativo -> 'no verificable': NO bloquea, la
      vacante va a 'revisar_a_mano' con motivo 'educacion_no_verificable'.
    """

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.connection = _crear_base(self.tmpdir.name)
        self.connection.commit()

    def tearDown(self):
        self.connection.close()
        self.tmpdir.cleanup()

    def _job_estudiante_activo(self, job_id: str) -> None:
        _insertar_job(
            self.connection,
            job_id,
            "Minimum Qualifications Currently pursuing a Bachelor's degree in "
            "Business Administration or a related field. Must be enrolled as a "
            "full-time student.",
        )
        _insertar_requisito(
            self.connection, job_id, "bachelor", "educacion-universitaria", "required"
        )
        self.connection.commit()

    def test_sin_fact_pursuing_es_no_cumple_y_bloquea(self):
        _insertar_fact(
            self.connection,
            "bachiller-en-educacion-media",
            "educacion-secundaria",
            "education",
            education_status="completed",
        )
        self._job_estudiante_activo("job-p1")
        evaluador = matching.EvaluadorPaso5(self.connection)
        resultado = evaluador.evaluar_job("job-p1")
        self.assertEqual(resultado.estado, matching.ESTADO_DESCARTADA)
        self.assertEqual(resultado.motivo, matching.MOTIVO_TITULO_EN_CURSO)

    def test_fact_pursuing_de_nivel_insuficiente_tampoco_cumple(self):
        _insertar_fact(
            self.connection,
            "diplomado-en-curso",
            "educacion-tecnica",
            "education",
            education_status="pursuing",
        )
        self._job_estudiante_activo("job-p2")
        evaluador = matching.EvaluadorPaso5(self.connection)
        resultado = evaluador.evaluar_job("job-p2")
        self.assertEqual(resultado.estado, matching.ESTADO_DESCARTADA)
        self.assertEqual(resultado.motivo, matching.MOTIVO_TITULO_EN_CURSO)

    def test_perfil_sin_hechos_educativos_es_no_verificable(self):
        """Sin hechos educativos NO se puede afirmar que 'no cumple'."""
        self._job_estudiante_activo("job-p3")
        evaluador = matching.EvaluadorPaso5(self.connection)
        resultado = evaluador.evaluar_job("job-p3")
        self.assertEqual(resultado.estado, matching.ESTADO_REVISAR)
        self.assertEqual(resultado.motivo, matching.MOTIVO_EDUCACION_NO_VERIFICABLE)
        self.assertNotEqual(resultado.estado, matching.ESTADO_DESCARTADA)

    def test_perfil_sin_hechos_educativos_titulo_completado_tampoco_bloquea(self):
        _insertar_job(
            self.connection,
            "job-p4",
            "Required Qualifications Bachelor's degree in Accounting required.",
        )
        _insertar_requisito(
            self.connection, "job-p4", "bachelor", "educacion-universitaria", "required"
        )
        self.connection.commit()
        evaluador = matching.EvaluadorPaso5(self.connection)
        resultado = evaluador.evaluar_job("job-p4")
        self.assertEqual(resultado.estado, matching.ESTADO_REVISAR)
        self.assertEqual(resultado.motivo, matching.MOTIVO_EDUCACION_NO_VERIFICABLE)

    def test_fact_pursuing_del_nivel_requerido_cumple(self):
        _insertar_fact(
            self.connection,
            "licenciatura-en-curso",
            "educacion-universitaria",
            "education",
            education_status="pursuing",
        )
        self._job_estudiante_activo("job-p5")
        evaluador = matching.EvaluadorPaso5(self.connection)
        resultado = evaluador.evaluar_job("job-p5")
        self.assertNotEqual(resultado.estado, matching.ESTADO_DESCARTADA)
        self.assertNotEqual(resultado.motivo, matching.MOTIVO_EDUCACION_NO_VERIFICABLE)


class TestCorridas(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.connection = _crear_base(self.tmpdir.name)
        _insertar_fact(self.connection, "bachiller-en-educacion-media", "educacion-secundaria", "education")
        _insertar_job(self.connection, "job-a", "Sin titulo reviewed.")
        _insertar_job(self.connection, "job-b", "Bachelor degree requerido.")
        _insertar_requisito(self.connection, "job-b", "bachelor", "educacion-universitaria", "required")
        self.connection.commit()

    def tearDown(self):
        self.connection.close()
        self.tmpdir.cleanup()

    def test_cada_corrida_es_nueva_y_no_toca_la_anterior(self):
        primera, _ = matching.ejecutar_paso5(self.connection, "20260101_000000")
        segunda, _ = matching.ejecutar_paso5(self.connection, "20260101_010000")
        self.assertNotEqual(primera, segunda)
        filas = self.connection.execute(
            "SELECT corrida_id, COUNT(*) n FROM job_match GROUP BY corrida_id ORDER BY corrida_id"
        ).fetchall()
        self.assertEqual(len(filas), 2)
        self.assertEqual({f["n"] for f in filas}, {2})

    def test_corrida_anterior_queda_invalida(self):
        matching.ejecutar_paso5(self.connection, "20260101_000000")
        matching.ejecutar_paso5(self.connection, "20260101_010000")
        validas = self.connection.execute(
            "SELECT DISTINCT corrida_id FROM job_match WHERE valida = 1"
        ).fetchall()
        self.assertEqual([r["corrida_id"] for r in validas], ["20260101_010000"])

    def test_persiste_columnas_de_conteo(self):
        matching.ejecutar_paso5(self.connection, "20260101_000000")
        fila = self.connection.execute(
            "SELECT * FROM job_match WHERE job_id = 'job-b'"
        ).fetchone()
        self.assertEqual(fila["total_req"], 1)
        self.assertEqual(fila["evaluables"], 1)
        self.assertEqual(fila["estado"], matching.ESTADO_DESCARTADA)


if __name__ == "__main__":
    unittest.main()
