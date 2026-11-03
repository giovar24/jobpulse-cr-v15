# -*- coding: utf-8 -*-
"""Tests de la UI v2 (plana y modular).

Dos bloques:
1. Lógica de datos (SIN Tk): store, filtros, formato y exportación CSV.
2. Humo de la ventana (CON Tk): el shell monta la pestaña y la tabla
   muestra los avisos; al seleccionar uno, el panel de detalle se llena.
"""
from __future__ import annotations

import csv
import gc
import sys
import tempfile
import time
import tkinter as tk
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobpulse_v15.candidate_profile import CandidateProfileSuggestion
from jobpulse_v15.db import Database
from jobpulse_v15.repository import Repository
from jobpulse_v15.ui_v2.app import AppShell, PESTANIAS
from jobpulse_v15.ui_v2.data.jobs import (
    JobsStore,
    RawQuery,
    exportar_csv,
    idioma_texto,
    recortar,
    resumen_por_campo,
    salario_texto,
    ubicacion_texto,
)
from jobpulse_v15.ui_v2.data.profile import (
    ProfileQuery,
    ProfileStore,
    fact_desde_sugerencia,
)
from jobpulse_v15.ui_v2.data.profile import exportar_csv as exportar_perfil_csv
from jobpulse_v15.ui_v2.data.vacantes import AtsStore
from jobpulse_v15.ui_v2.tabs import perfil as perfil_mod
from jobpulse_v15.ui_v2.tabs.base import TabContext
from jobpulse_v15.ui_v2.tabs.vacantes import VacantesTab
from jobpulse_v15.ui_v2.theme import apply_theme


def _tkroot_reintentos(intentos: int = 5) -> tk.Tk:
    """Root de Tk oculto (Windows a veces falla con 'tk.tcl' no usable)."""
    ultimo: tk.TclError | None = None
    for _ in range(intentos):
        try:
            root = tk.Tk()
            root.withdraw()
            return root
        except tk.TclError as exc:
            ultimo = exc
            time.sleep(0.2)
    raise ultimo if ultimo else RuntimeError("tk.Tk() fallo sin detalle")


class TestDatosCrudos(unittest.TestCase):
    """La capa de datos no depende de Tk."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "ui-v2.db")
        self.database.initialize()
        self.repository = Repository(self.database)
        self.repository.register_platform("workday", "Workday", "api")
        self.repository.register_platform("greenhouse", "Greenhouse", "api")
        self.repository.register_site(
            "intel-cr", "workday", "Intel Careers CR",
            "https://intel.example.test", company_name="Intel", country="CR",
        )
        self.repository.register_site(
            "acme-cr", "greenhouse", "Acme CR",
            "https://acme.example.test", company_name="Acme", country="CR",
        )
        self.repository.save_job(
            {
                "job_id": "workday-REQ-1",
                "title": "Software Engineer",
                "company": "Intel",
                "country": "CR",
                "city": "San Jose",
                "region": "San José",
                "location_raw": "San Jose, Costa Rica",
                "posting_language": "en",
                "date_published": "2026-10-20",
                "salary_raw": "USD 65,000-100,000",
                "salary_min": 65000,
                "salary_max": 100000,
                "salary_currency": "USD",
                "salary_period": "annual",
                "description_raw": "x" * 500,
            },
            site_id="intel-cr",
            source_job_id="REQ-1",
            source_url="https://intel.example.test/jobs/1",
        )
        self.repository.save_job(
            {
                "job_id": "greenhouse-REQ-2",
                "title": "Data Analyst",
                "company": "Acme",
                "country": "CR",
                "location_raw": "Costa Rica (Remote)",
                "posting_language": "es",
                "date_published": "2026-10-21",
                "description_raw": "corto",
            },
            site_id="acme-cr",
            source_job_id="REQ-2",
            source_url="https://acme.example.test/jobs/2",
        )
        self.store = JobsStore(self.repository)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_carga_los_avisos_con_su_plataforma(self):
        filas = self.store.load()
        self.assertEqual(len(filas), 2)
        plataformas = {f.job_id: f.platform for f in filas}
        self.assertEqual(plataformas["workday-REQ-1"], "workday")
        self.assertEqual(plataformas["greenhouse-REQ-2"], "greenhouse")

    def test_filtra_por_plataforma(self):
        filas = self.store.load(RawQuery(plataforma="greenhouse"))
        self.assertEqual([f.job_id for f in filas], ["greenhouse-REQ-2"])

    def test_filtra_por_texto(self):
        filas = self.store.load(RawQuery(texto="Data Analyst"))
        self.assertEqual([f.job_id for f in filas], ["greenhouse-REQ-2"])

    def test_filtra_solo_con_descripcion(self):
        filas = self.store.load(RawQuery(solo_con_descripcion=True))
        self.assertEqual([f.job_id for f in filas], ["workday-REQ-1"])

    def test_detalle_trae_texto_crudo_y_fuentes(self):
        detalle = self.store.detail("workday-REQ-1")
        self.assertIsNotNone(detalle)
        self.assertEqual(len(detalle.description_raw), 500)
        self.assertEqual(detalle.row.salary_raw, "USD 65,000-100,000")
        self.assertEqual(len(detalle.sources), 1)
        self.assertEqual(detalle.sources[0]["site_id"], "intel-cr")

    def test_resumen_por_campo(self):
        resumen = resumen_por_campo(self.store.load())
        self.assertEqual(resumen["total"], 2)
        self.assertEqual(resumen["con_descripcion"], 1)
        self.assertEqual(resumen["con_salario"], 1)
        self.assertEqual(resumen["con_fecha"], 2)

    def test_formatos_puros(self):
        fila = self.store.load(RawQuery(plataforma="workday"))[0]
        self.assertEqual(idioma_texto("es"), "Español")
        self.assertEqual(idioma_texto(""), "Sin determinar")
        self.assertIn("USD", salario_texto(fila))
        self.assertEqual(ubicacion_texto(fila), "San Jose, Costa Rica")
        self.assertEqual(recortar("a" * 100, 10), "aaaaaaaaa…")

    def test_exporta_csv(self):
        filas = self.store.load()
        destino = Path(self.temp_dir.name) / "salida.csv"
        total = exportar_csv(filas, destino)
        self.assertEqual(total, 2)
        with destino.open(encoding="utf-8-sig") as archivo:
            leido = list(csv.DictReader(archivo))
        self.assertEqual(len(leido), 2)
        self.assertEqual(leido[0]["job_id"], filas[0].job_id)


class TestShellVisual(unittest.TestCase):
    """El shell monta la app y la pestaña de datos crudos."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "ui-v2.db")
        self.database.initialize()
        self.repository = Repository(self.database)
        self.repository.register_platform("workday", "Workday", "api")
        self.repository.register_site(
            "intel-cr", "workday", "Intel Careers CR",
            "https://intel.example.test", company_name="Intel", country="CR",
        )
        self.repository.save_job(
            {
                "job_id": "workday-REQ-1",
                "title": "Software Engineer",
                "company": "Intel",
                "country": "CR",
                "city": "San Jose",
                "location_raw": "San Jose, Costa Rica",
                "posting_language": "en",
                "date_published": "2026-10-20",
                "description_raw": "x" * 500,
            },
            site_id="intel-cr",
            source_job_id="REQ-1",
            source_url="https://intel.example.test/jobs/1",
        )
        self.root = _tkroot_reintentos()
        self.theme = apply_theme(self.root)
        self.shell = AppShell(self.root, self.repository, theme=self.theme)

    def tearDown(self):
        self.root.update_idletasks()
        self.root.destroy()
        gc.collect()
        self.temp_dir.cleanup()

    def test_registra_las_pestanas_registradas(self):
        self.assertEqual(len(self.shell.instancias), len(PESTANIAS))
        self.assertEqual(self.shell.pestana_activa().key, "crudos")

    def test_la_tabla_muestra_los_avisos(self):
        self.root.update()
        pestana = self.shell.pestana_activa()
        pestana.refresh()
        self.root.update()
        tabla = pestana._widgets["tabla"]
        self.assertEqual(tabla.get_children(), ("workday-REQ-1",))
        valores = tabla.item("workday-REQ-1", "values")
        self.assertIn("Software Engineer", valores)

    def test_seleccionar_una_fila_llena_el_detalle(self):
        self.root.update()
        pestana = self.shell.pestana_activa()
        pestana.refresh()
        tabla = pestana._widgets["tabla"]
        tabla.selection_set("workday-REQ-1")
        self.root.update()
        self.assertIsNotNone(pestana.detalle)
        self.assertEqual(pestana.detalle.row.job_id, "workday-REQ-1")
        self.assertEqual(pestana._widgets["kv"]["job_id"].value_label.cget("text"),
                         "workday-REQ-1")

    def test_las_tarjetas_de_resumen_estan_colocadas(self):
        """Regresion: un StatTile sin empaquetar no lo gestiona ningun gestor."""
        self.root.update()
        pestana = self.shell.pestana_activa()
        pestana.refresh()
        self.root.update()
        for clave, tile in pestana._tiles.items():
            with self.subTest(tarjeta=clave):
                self.assertEqual(tile.winfo_manager(), "pack")
                self.assertTrue(tile.pack_info())

    def test_las_fuentes_ttk_son_interpretables_por_tk(self):
        """Regresion: font='Segoe UI' sin llaves rompe el render del Treeview."""
        from tkinter import font as tkfont
        for estilo in ("Flat.Treeview", "Flat.Treeview.Heading",
                       "Flat.TButton", "TEntry"):
            with self.subTest(estilo=estilo):
                espec = self.theme.styles.lookup(estilo, "font")
                self.assertTrue(espec, f"{estilo} sin fuente")
                fuente = tkfont.Font(root=self.root, font=espec)
                self.assertEqual(fuente.actual("family"), self.theme.metrics.font_family)


class TestShellSinAvisos(unittest.TestCase):
    """La pestaña debe abrir sin avisos (estado vacío) sin romperse."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "vacia.db")
        self.database.initialize()
        self.repository = Repository(self.database)
        self.root = _tkroot_reintentos()
        self.theme = apply_theme(self.root)
        self.shell = AppShell(self.root, self.repository, theme=self.theme)

    def tearDown(self):
        self.root.update_idletasks()
        self.root.destroy()
        gc.collect()
        self.temp_dir.cleanup()

    def test_refresh_sin_avisos_muestra_el_estado_vacio(self):
        self.root.update()
        pestana = self.shell.pestana_activa()
        pestana.refresh()  # no debe lanzar (pack vs grid)
        self.root.update()
        self.assertEqual(pestana._widgets["tabla"].get_children(), ())
        vacio = pestana._widgets["vacio"]
        self.assertEqual(vacio.winfo_manager(), "grid")  # mismo gestor que el marco
        self.assertTrue(vacio.grid_info())
        self.assertEqual(pestana._widgets["estado"].cget("text").split()[0], "0")


class TestPerfilStore(unittest.TestCase):
    """La capa de datos del perfil no depende de Tk."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "perfil.db")
        self.database.initialize()
        self.repository = Repository(self.database)
        self.store = ProfileStore(self.repository)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_guarda_y_lista(self):
        self.store.save("language", "en", "Inglés", qualifier="B2")
        hechos = self.store.load()
        self.assertEqual(len(hechos), 1)
        self.assertEqual(hechos[0].category, "language")
        self.assertEqual(hechos[0].value_code, "en")
        self.assertEqual(hechos[0].nivel_legible, "B2")
        self.assertEqual(hechos[0].origin, "manual")

    def test_actualiza_por_categoria_y_codigo(self):
        self.store.save("skill", "python", "Python")
        self.store.save("skill", "python", "Python avanzado", qualifier="avanzado")
        hechos = self.store.load()
        self.assertEqual(len(hechos), 1)
        self.assertEqual(hechos[0].value_text, "Python avanzado")

    def test_elimina(self):
        self.store.save("skill", "python", "Python")
        fact_id = self.store.load()[0].fact_id
        self.assertTrue(self.store.delete(fact_id))
        self.assertEqual(self.store.load(), [])
        self.assertFalse(self.store.delete(fact_id))

    def test_estado_educacion_y_numero_solo_en_su_categoria(self):
        self.store.save("education", "bachelor", "Bachillerato",
                        education_status="completed")
        self.store.save("experience", "total", "Experiencia", numeric_value="3", unit="years")
        # En otra categoría el estado/numero se descartan (no rompen el guardado).
        self.store.save("skill", "python", "Python",
                        education_status="completed", numeric_value="9")
        por_clave = {(h.category, h.value_code): h for h in self.store.load()}
        self.assertEqual(por_clave[("education", "bachelor")].education_status, "completed")
        self.assertEqual(por_clave[("experience", "total")].numeric_value, 3.0)
        self.assertEqual(por_clave[("experience", "total")].nivel_legible, "3 years")
        self.assertEqual(por_clave[("skill", "python")].education_status, "")
        self.assertIsNone(por_clave[("skill", "python")].numeric_value)

    def test_filtra_por_categoria_y_texto(self):
        self.store.save("skill", "python", "Python")
        self.store.save("language", "en", "Inglés")
        self.assertEqual([h.value_code for h in self.store.load(ProfileQuery(categoria="skill"))],
                         ["python"])
        self.assertEqual([h.value_code for h in self.store.load(ProfileQuery(texto="ingl"))],
                         ["en"])

    def test_resumen(self):
        self.store.save("skill", "python", "Python")
        self.store.save("skill", "sql", "SQL")
        self.store.save("language", "en", "Inglés")
        resumen = self.store.resumen(self.store.load())
        self.assertEqual(resumen.total, 3)
        self.assertEqual(resumen.categorias_cubiertas, 2)
        self.assertEqual(resumen.por_categoria["skill"], 2)
        self.assertEqual(resumen.manuales, 3)
        self.assertEqual(resumen.importados, 0)

    def test_importa_y_revierte(self):
        total = self.store.import_facts("cv.pdf", [
            {"category": "skill", "value_code": "python", "value_text": "Python"},
            {"category": "language", "value_code": "en", "value_text": "Inglés",
             "qualifier": "B2"},
        ])
        self.assertEqual(total, 2)
        self.assertEqual(self.store.resumen(self.store.load()).importados, 2)
        self.assertEqual(len(self.store.importaciones()), 1)
        resultado = self.store.revertir_ultima()
        self.assertEqual(resultado["removed"], 2)
        self.assertEqual(self.store.load(), [])

    def test_fact_desde_sugerencia_respeta_categorias(self):
        skill = fact_desde_sugerencia(CandidateProfileSuggestion(
            category="skill", value_code="python", value_text="Python",
        ))
        self.assertEqual(skill["category"], "skill")
        self.assertIsNone(skill["education_status"])
        self.assertIsNone(skill["numeric_value"])
        edu = fact_desde_sugerencia(CandidateProfileSuggestion(
            category="education", value_code="bachelor", value_text="Bachillerato",
            education_status="completed",
        ))
        self.assertEqual(edu["education_status"], "completed")

    def test_exporta_csv(self):
        self.store.save("skill", "python", "Python")
        destino = Path(self.temp_dir.name) / "perfil.csv"
        total = exportar_perfil_csv(self.store.load(), destino)
        self.assertEqual(total, 1)
        with destino.open(encoding="utf-8-sig") as archivo:
            leido = list(csv.DictReader(archivo))
        self.assertEqual(leido[0]["value_code"], "python")


class TestPerfilTab(unittest.TestCase):
    """La pestaña de perfil monta, lista y permite dar de alta."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "perfil-ui.db")
        self.database.initialize()
        self.repository = Repository(self.database)
        self.root = _tkroot_reintentos()
        self.theme = apply_theme(self.root)
        self.shell = AppShell(self.root, self.repository, theme=self.theme)
        self.shell.mostrar(1)  # pestaña "perfil"
        self.pestana = self.shell.pestana_activa()
        self.assertEqual(self.pestana.key, "perfil")
        # Silencia los diálogos modales durante el test.
        self._patch = unittest.mock.patch.object(
            perfil_mod.messagebox, "showinfo",
            side_effect=lambda *a, **k: None,
        )
        self._patch.start()
        self.addCleanup(self._patch.stop)

    def tearDown(self):
        self.root.update_idletasks()
        self.root.destroy()
        gc.collect()
        self.temp_dir.cleanup()

    def _cargar_fact_manual(self):
        self.pestana._widgets["categoria"].current(0)  # contact
        self.pestana._set_entry("codigo", "nombre")
        self.pestana._set_entry("valor", "Giovanni")
        self.pestana.guardar()

    def test_alta_manual_llena_la_tabla(self):
        self._cargar_fact_manual()
        self.assertEqual(len(self.pestana._widgets["tabla"].get_children()), 1)
        self.assertEqual(self.repository.list_candidate_profile_facts()[0]["value_text"],
                         "Giovanni")

    def test_seleccionar_carga_el_formulario(self):
        self._cargar_fact_manual()
        tabla = self.pestana._widgets["tabla"]
        tabla.selection_set(tabla.get_children()[0])
        self.root.update()
        self.assertEqual(self.pestana._get_entry("codigo"), "nombre")
        self.assertEqual(self.pestana._get_entry("valor"), "Giovanni")
        self.assertEqual(self.pestana._editando_id is not None, True)

    def test_estado_educacion_solo_activo_en_education(self):
        combos = self.pestana._widgets
        combos["categoria"].current(0)  # contact
        self.pestana._aplicar_categoria()
        self.assertEqual(str(combos["estado_educacion"].cget("state")), "disabled")
        categoria_educacion = list(
            perfil_mod.CATEGORIAS
        ).index("education")
        combos["categoria"].current(categoria_educacion)
        self.pestana._aplicar_categoria()
        self.assertEqual(str(combos["estado_educacion"].cget("state")), "readonly")

    def test_refresh_sin_datos_no_rompe(self):
        self.pestana.refresh()
        self.root.update()
        self.assertEqual(self.pestana._widgets["tabla"].get_children(), ())
        self.assertEqual(self.pestana._widgets["vacio"].winfo_manager(), "grid")


class TestVacantesTab(unittest.TestCase):
    """La pestaña del ranking ATS se monta y no rompe el shell."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "ui-v2-vacantes.db")
        self.database.initialize()
        self.repository = Repository(self.database)
        self.root = _tkroot_reintentos()
        self.theme = apply_theme(self.root)

    def tearDown(self):
        self.root.update_idletasks()
        self.root.destroy()
        gc.collect()
        self.temp_dir.cleanup()

    def _pestana(self) -> "VacantesTab":
        contexto = TabContext(
            repository=self.repository,
            theme=self.theme,
            services={"ats_store": AtsStore(self.repository)},
        )
        pestana = VacantesTab(contexto)
        marco = pestana.build(self.root)
        marco.grid(row=0, column=0, sticky="nsew")
        self.root.update()
        return pestana

    def test_la_pestana_esta_registrada(self):
        self.assertIn("vacantes", [clase.key for clase in PESTANIAS])

    def test_se_monta_con_la_tabla_vacia(self):
        pestana = self._pestana()
        pestana.refresh()
        self.root.update()
        self.assertEqual(pestana._widgets["tabla"].get_children(), ())
        self.assertEqual(pestana._widgets["vacio"].winfo_manager(), "grid")
        self.assertIn("estado", pestana._widgets)
        self.assertIn("detalle", pestana._widgets)

    def test_sin_avisos_no_lanza_el_calculo_pesado(self):
        pestana = self._pestana()
        pestana.recalcular()
        self.root.update()
        self.assertFalse(pestana._calculando)
        self.assertEqual(pestana._widgets["estado"].cget("text"), "No hay avisos guardados para rankear.")

    def test_el_calculo_en_segundo_plano_pinta_la_tabla(self):
        """El `after` va por el marco de la pestaña (no es un widget Tk)."""
        self.repository.register_platform("workday", "Workday", "api")
        self.repository.register_site(
            "intel-cr", "workday", "Intel Careers CR",
            "https://intel.example.test", company_name="Intel", country="CR",
        )
        self.repository.save_job(
            {
                "job_id": "workday-REQ-1",
                "title": "IT Support Specialist",
                "company": "Intel",
                "country": "CR",
                "location_raw": "San Jose, Costa Rica",
                "posting_language": "en",
                "date_published": "2026-10-20",
                "description_raw": "Soporte TI con Active Directory y ServiceNow. " * 5,
            },
            site_id="intel-cr",
            source_job_id="REQ-1",
            source_url="https://intel.example.test/jobs/REQ-1",
        )
        pestana = self._pestana()
        with unittest.mock.patch.object(VacantesTab, "_crear_engine", return_value=None):
            pestana.recalcular()
            for _ in range(100):
                self.root.update()
                if not pestana._calculando:
                    break
                time.sleep(0.02)
        self.assertFalse(pestana._calculando)
        self.assertEqual(len(pestana._widgets["tabla"].get_children()), 1)
        self.assertEqual(pestana.filas[0].title, "IT Support Specialist")


if __name__ == "__main__":
    unittest.main()
