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
import os
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
from jobpulse_v15 import scraper
from jobpulse_v15.ui_v2 import configuracion as config_ui
from jobpulse_v15.ui_v2.app import AppShell, PESTANIAS
from jobpulse_v15.ui_v2.data.fuentes import FuentesStore
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
from jobpulse_v15.ui_v2.tabs import configuracion as config_mod
from jobpulse_v15.ui_v2.tabs import perfil as perfil_mod
from jobpulse_v15.ui_v2.tabs import scraping as scraping_mod
from jobpulse_v15.ui_v2.tabs.base import TabContext
from jobpulse_v15.ui_v2.tabs.vacantes import VacantesTab
from jobpulse_v15.ui_v2.theme import PALETAS, apply_theme


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


class TestConfiguracionPersistencia(unittest.TestCase):
    """ui_config.json (merge con claves ajenas) y .env (update selectivo). SIN Tk."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ruta_cfg = Path(self.temp_dir.name) / "ui_config.json"
        self._parches = [
            unittest.mock.patch.object(config_ui, "ARCHIVO", self.ruta_cfg),
        ]
        for parche in self._parches:
            parche.start()
            self.addCleanup(parche.stop)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_guardar_hace_merge_y_no_pisa_claves_ajenas(self):
        """Regresión: el mismo archivo escribe ciclo_vida y la UI clásica."""
        config_ui.guardar({"otra_clave": 1})
        config_ui.guardar({config_ui.CLAVE_PALETA: "oscuro"})
        datos = config_ui.cargar()
        self.assertEqual(datos["otra_clave"], 1)
        self.assertEqual(config_ui.paleta_actual(), "oscuro")

    def test_cargar_sin_archivo_o_ilegible_devuelve_vacio(self):
        self.assertEqual(config_ui.cargar(Path(self.temp_dir.name) / "no.json"), {})
        roto = Path(self.temp_dir.name) / "roto.json"
        roto.write_text("{no es json", encoding="utf-8")
        self.assertEqual(config_ui.cargar(roto), {})

    def test_directorio_csv_solo_si_la_carpeta_existe(self):
        self.assertIsNone(config_ui.directorio_csv())
        carpeta = Path(self.temp_dir.name) / "exports"
        carpeta.mkdir()
        config_ui.guardar({config_ui.CLAVE_CSV_DIR: str(carpeta)})
        self.assertEqual(config_ui.directorio_csv(), str(carpeta))
        # Carpeta borrada después de guardar → el diálogo cae al default de Tk.
        config_ui.guardar({config_ui.CLAVE_CSV_DIR: str(carpeta / "borrada")})
        self.assertIsNone(config_ui.directorio_csv())

    def test_guardar_env_actualiza_solo_las_claves_pedidas(self):
        env = Path(self.temp_dir.name) / ".env"
        env.write_text("# comentario\nOTRA=1\nIA_MODEL=viejo\n", encoding="utf-8")
        config_ui.guardar_env({"IA_MODEL": "nuevo", "IA_RPM": ""}, ruta=env)
        lineas = env.read_text(encoding="utf-8").splitlines()
        self.assertIn("# comentario", lineas)      # comentarios intactos
        self.assertIn("OTRA=1", lineas)            # claves ajenas intactas
        self.assertIn("IA_MODEL=nuevo", lineas)    # pedida → actualizada
        self.assertNotIn("IA_MODEL=viejo", lineas)
        self.assertIn("IA_RPM=", lineas)           # vacío = sin tope (opt-in)

    def test_guardar_env_agrega_clave_nueva_y_sana_saltos(self):
        env = Path(self.temp_dir.name) / ".env"
        env.write_text("EXISTE=1\n", encoding="utf-8")
        config_ui.guardar_env({"IA_MODEL": "a\nb"}, ruta=env)
        texto = env.read_text(encoding="utf-8")
        self.assertIn("EXISTE=1", texto)
        self.assertIn("IA_MODEL=a b", texto)  # un salto rompería el archivo
        self.assertNotIn("IA_MODEL=a\nb", texto)


class TestFuentesStore(unittest.TestCase):
    """Sondas de scraping (source_sites) SIN Tk."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "fuentes.db")
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
        self.store = FuentesStore(self.repository)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_lista_las_sondas_con_su_plataforma(self):
        filas = self.store.sitios()
        self.assertEqual(len(filas), 2)
        por_id = {f.site_id: f for f in filas}
        self.assertEqual(por_id["intel-cr"].plataforma, "Workday")
        self.assertEqual(por_id["intel-cr"].tipo, "api")
        self.assertTrue(por_id["intel-cr"].activo)

    def test_plataformas_ordenadas_y_conteo(self):
        self.assertEqual(self.store.plataformas(), ["Greenhouse", "Workday"])
        self.assertEqual(self.store.conteo(), (2, 2))

    def test_alternar_persiste_en_la_bd_sin_borrar_nada(self):
        cambiadas = self.store.alternar(["intel-cr", "acme-cr"], False)
        self.assertEqual(cambiadas, 2)
        self.assertEqual(self.store.conteo(), (0, 2))
        habilitados = {s["site_id"]: s["enabled"]
                       for s in self.repository.list_sites()}
        self.assertEqual(habilitados, {"intel-cr": False, "acme-cr": False})
        # Reactivar vuelve al estado original (nada se pierde).
        self.store.alternar(["intel-cr", "acme-cr"], True)
        self.assertEqual(self.store.conteo(), (2, 2))

    def test_alternar_un_id_inexistente_no_cambia_nada(self):
        self.assertEqual(self.store.alternar(["no-existe"], False), 0)
        self.assertEqual(self.store.conteo(), (2, 2))


class TestConfiguracionTab(unittest.TestCase):
    """La pestaña de Configuración monta, pausa sondas y cambia esquemas."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        temp = Path(self.temp_dir.name)
        self.database = Database(temp / "config-ui.db")
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
        self.ruta_cfg = temp / "ui_config.json"

        # Nada de red, nada de diálogos modales, nada de .env real.
        self.showinfo = unittest.mock.MagicMock(side_effect=lambda *a, **k: None)
        self.showwarning = unittest.mock.MagicMock(side_effect=lambda *a, **k: None)
        self.showerror = unittest.mock.MagicMock(side_effect=lambda *a, **k: None)
        # La pestaña actualiza os.environ al guardar: se restaura al final.
        self._env_ia = {clave: os.environ.get(clave) for clave in
                        ("IA_PROVEEDOR", "IA_BASE_URL", "IA_MODEL",
                         "IA_API_KEY", "IA_MAX_LLAMADAS", "IA_RPM")}
        self.addCleanup(self._restaurar_env_ia)
        config_mod._HANDLE_SERVIDOR = None  # el global no se hereda entre tests
        parches = [
            unittest.mock.patch.object(config_ui, "ARCHIVO", self.ruta_cfg),
            unittest.mock.patch.object(config_mod, "servidor_arriba",
                                        return_value=False),
            unittest.mock.patch.object(config_mod, "confirmar",
                                        return_value=True),
            unittest.mock.patch.object(config_mod.messagebox, "showinfo",
                                        self.showinfo),
            unittest.mock.patch.object(config_mod.messagebox, "showwarning",
                                        self.showwarning),
            unittest.mock.patch.object(config_mod.messagebox, "showerror",
                                        self.showerror),
            unittest.mock.patch("dotenv.load_dotenv", return_value=False),
            unittest.mock.patch("jobpulse_v15.ia_servidor.load_dotenv",
                                return_value=False),
        ]
        for parche in parches:
            parche.start()
            self.addCleanup(parche.stop)
        self.addCleanup(setattr, config_mod, "_HANDLE_SERVIDOR", None)

        self.root = _tkroot_reintentos()
        self.theme = apply_theme(self.root)
        self.shell = AppShell(self.root, self.repository, theme=self.theme)
        self.shell.mostrar(4)  # pestaña "configuracion"
        self.pestana = self.shell.pestana_activa()
        self.assertEqual(self.pestana.key, "configuracion")

    def tearDown(self):
        for _ in range(5):  # drena los after de los hilos antes de destruir
            self.root.update()
            time.sleep(0.01)
        self.root.update_idletasks()
        self.root.destroy()
        gc.collect()
        self.temp_dir.cleanup()

    def _esperar(self, cond, timeout: float = 3.0) -> bool:
        limite = time.time() + timeout
        while time.time() < limite:
            self.root.update()
            if cond():
                return True
            time.sleep(0.02)
        return bool(cond())

    def _restaurar_env_ia(self) -> None:
        for clave, valor in self._env_ia.items():
            if valor is None:
                os.environ.pop(clave, None)
            else:
                os.environ[clave] = valor

    def test_la_pestana_esta_registrada(self):
        claves = [clase.key for clase in PESTANIAS]
        self.assertIn("configuracion", claves)
        self.assertEqual(claves, ["crudos", "perfil", "vacantes", "scraping",
                                  "configuracion"])

    def test_monta_las_cinco_tarjetas_y_lista_las_sondas(self):
        self.root.update()
        for clave in ("ia_estado", "ia_proveedor", "tabla", "paleta",
                      "sondas_hint"):
            with self.subTest(widget=clave):
                self.assertIn(clave, self.pestana._widgets)
        self.assertEqual(len(self.pestana._widgets["tabla"].get_children()), 2)
        self.assertEqual(self.pestana._widgets["sondas_hint"].cget("text"),
                         "2 de 2 activas")
        # El estado de la IA local se pinta desde el hilo (servidor_arriba
        # parcheado a False → "apagado"); si no llega, el after nunca corre.
        self.assertTrue(self._esperar(
            lambda: "apagado" in self.pestana._widgets["ia_estado"].cget("text")
            or "ARRIBA" in self.pestana._widgets["ia_estado"].cget("text")))

    def test_pausar_seleccion_persiste_y_muestra_el_aviso(self):
        self.root.update()
        tabla = self.pestana._widgets["tabla"]
        tabla.selection_set(*tabla.get_children())
        self.pestana.pausar_seleccion()
        self.root.update()
        self.assertEqual(self.pestana._widgets["sondas_hint"].cget("text"),
                         "0 de 2 activas")
        # Ninguna corrida verá estas fuentes: select_sites() las excluye.
        self.assertEqual(
            {s["site_id"]: s["enabled"] for s in self.repository.list_sites()},
            {"intel-cr": 0, "acme-cr": 0})
        aviso = self.pestana._widgets["sondas_aviso"]
        self.assertTrue(aviso.grid_info())  # visible (grid_remove → grid())

    def test_pausar_todas_respeta_la_confirmacion(self):
        self.root.update()
        with unittest.mock.patch.object(config_mod, "confirmar",
                                        return_value=False):
            self.pestana.pausar_todas()
        self.root.update()
        self.assertEqual(self.pestana._widgets["sondas_hint"].cget("text"),
                         "2 de 2 activas")
        with unittest.mock.patch.object(config_mod, "confirmar",
                                        return_value=True):
            self.pestana.pausar_todas()
        self.root.update()
        self.assertEqual(self.pestana._widgets["sondas_hint"].cget("text"),
                         "0 de 2 activas")
        self.pestana.activar_todas()
        self.root.update()
        self.assertEqual(self.pestana._widgets["sondas_hint"].cget("text"),
                         "2 de 2 activas")
        self.assertFalse(self.pestana._widgets["sondas_aviso"].grid_info())

    def test_filtro_por_plataforma_acota_la_tabla(self):
        self.root.update()
        self.pestana._widgets["sondas_filtro"].set("Workday")
        self.pestana.refresh()
        self.root.update()
        hijos = self.pestana._widgets["tabla"].get_children()
        self.assertEqual(hijos, ("intel-cr",))

    def test_guardar_ia_escribe_el_env_y_valida_los_limites(self):
        self.root.update()
        with unittest.mock.patch.object(config_ui, "guardar_env") as guardar:
            self.pestana._widgets["ia_proveedor"].set("Ollama (local)")
            self.pestana._on_proveedor()
            # El preset rellena base_url/modelo (combo muestra nombres).
            self.assertEqual(self.pestana._get("ia_base_url"),
                             "http://localhost:11434/v1")
            self.pestana._set("ia_max", "100")
            self.pestana._set("ia_rpm", "")
            self.pestana.guardar_ia()
        self.assertTrue(guardar.called)
        valores = guardar.call_args.args[0]
        self.assertEqual(valores["IA_PROVEEDOR"], "ollama")  # clave, no nombre
        self.assertEqual(valores["IA_MAX_LLAMADAS"], "100")
        self.assertEqual(valores["IA_RPM"], "")  # vacío = sin tope

        with unittest.mock.patch.object(config_ui, "guardar_env") as guardar:
            self.pestana._set("ia_max", "no-es-numero")
            self.pestana.guardar_ia()
        self.assertFalse(guardar.called)
        self.assertTrue(self.showwarning.called)

    def test_guardar_ia_toma_effecto_en_la_misma_sesion(self):
        """load_dotenv NO pisa variables ya presentes: se actualiza os.environ."""
        self.root.update()
        with unittest.mock.patch.object(config_ui, "guardar_env"):
            self.pestana._widgets["ia_proveedor"].set("NVIDIA NIM")
            self.pestana._on_proveedor()
            self.pestana.guardar_ia()
        self.assertEqual(os.environ.get("IA_PROVEEDOR"), "nvidia")
        self.assertEqual(os.environ.get("IA_BASE_URL"),
                         "https://integrate.api.nvidia.com/v1")

    def test_listar_modelos_devuelve_la_lista_del_endpoint(self):
        self.root.update()

        class ClienteFalso:
            def __init__(self, config):
                self.config = config

            async def listar_modelos(self):
                return ["modelo-a", "modelo-b"]

        with unittest.mock.patch("jobpulse_v15.ia_api.IAClient", ClienteFalso):
            self.pestana.listar_modelos()
            self.assertTrue(self._esperar(lambda: self.showinfo.called))
        texto = self.showinfo.call_args.args[1]
        self.assertIn("modelo-a", texto)
        self.assertIn("modelo-b", texto)

    def test_cambiar_el_esquema_guarda_y_reconstruye_la_app(self):
        self.root.update()
        self.pestana._widgets["paleta"].set("Oscuro")
        self.pestana.aplicar_paleta()
        self.assertTrue(self._esperar(
            lambda: self.shell.theme.color("bg") == PALETAS["oscuro"].bg),
            "la app no se reconstruyó con la paleta oscura")
        datos = config_ui.cargar()
        self.assertEqual(datos.get("paleta"), "oscuro")
        # Sigue siendo la misma app: 4 pestañas y la activa conservada.
        self.assertEqual(len(self.shell.instancias), len(PESTANIAS))
        self.assertEqual(self.shell.pestana_activa().key, "configuracion")
        # La nueva instancia ya arranca con la paleta elegida.
        self.assertEqual(
            self.shell.pestana_activa()._widgets["paleta"].get(), "Oscuro")

    def test_directorio_csv_se_guarda_y_se_puede_limpiar(self):
        self.root.update()
        carpeta = Path(self.temp_dir.name) / "exports"
        carpeta.mkdir()
        with unittest.mock.patch.object(
                config_mod.filedialog, "askdirectory",
                return_value=str(carpeta)):
            self.pestana._elegir_directorio()
        self.root.update()
        self.assertEqual(self.pestana._csv_var.get(), str(carpeta))
        self.assertEqual(config_ui.directorio_csv(), str(carpeta))
        self.pestana._usar_predeterminado()
        self.assertEqual(config_ui.cargar().get("csv_dir"), "")

    def test_arrancar_y_detener_la_ia_local(self):
        """O7.3: se guarda SOLO el handle que arrancó esta UI y se detiene."""
        self.root.update()
        handle = unittest.mock.MagicMock()
        with unittest.mock.patch.object(config_mod, "asegurar_servidor",
                                        return_value=handle) as asegurar:
            self.pestana.arrancar_ia_local()
            self.assertTrue(self._esperar(
                lambda: config_mod._HANDLE_SERVIDOR is not None))
        asegurar.assert_called_once()
        self.assertIs(config_mod._HANDLE_SERVIDOR, handle)

        self.pestana.detener_ia_local()
        self.assertTrue(self._esperar(
            lambda: config_mod._HANDLE_SERVIDOR is None))
        handle.detener.assert_called_once()

    def test_detener_sin_handle_propio_es_noop(self):
        """Si la IA la arrancó otro, esta UI jamás la apaga (O7.3)."""
        self.root.update()
        self.assertIsNone(config_mod._HANDLE_SERVIDOR)
        self.pestana.detener_ia_local()  # no debe lanzar ni lanzar hilos
        self.assertIsNone(config_mod._HANDLE_SERVIDOR)
        self.assertFalse(self.showerror.called)


class TestScrapingTab(unittest.TestCase):
    """La pestaña de Scraping monta, filtra por grupo y lanza el barrido."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        temp = Path(self.temp_dir.name)
        self.database = Database(temp / "scraping-ui.db")
        self.database.initialize()
        self.repository = Repository(self.database)
        self.repository.register_platform("workday", "Workday", "api")
        self.repository.register_platform("greenhouse", "Greenhouse", "api")
        self.repository.register_site(
            "intel-cr", "workday", "Intel Careers CR",
            "https://intel.example.test", company_name="Intel", country="CR",
            run_groups=("directos",), site_config={"pages": 3},
        )
        self.repository.register_site(
            "acme-cr", "greenhouse", "Acme CR",
            "https://acme.example.test", company_name="Acme", country="CR",
            run_groups=("cr-gov",),
        )
        self.root = _tkroot_reintentos()
        self.theme = apply_theme(self.root)
        self.shell = AppShell(self.root, self.repository, theme=self.theme)
        self.shell.mostrar(3)  # pestaña "scraping"
        self.pestana = self.shell.pestana_activa()
        self.assertEqual(self.pestana.key, "scraping")

    def tearDown(self):
        for _ in range(5):
            self.root.update()
            time.sleep(0.01)
        self.root.update_idletasks()
        self.root.destroy()
        gc.collect()
        self.temp_dir.cleanup()

    def _esperar(self, cond, timeout: float = 3.0) -> bool:
        limite = time.time() + timeout
        while time.time() < limite:
            self.root.update()
            if cond():
                return True
            time.sleep(0.02)
        return bool(cond())

    def test_la_pestana_esta_registrada(self):
        self.assertIn("scraping", [clase.key for clase in PESTANIAS])

    def test_monta_y_lista_las_fuentes(self):
        self.root.update()
        tabla = self.pestana._widgets["tabla"]
        self.assertEqual(set(tabla.get_children()), {"intel-cr", "acme-cr"})
        valores = tabla.item("intel-cr", "values")
        self.assertIn("Intel Careers CR", valores)
        self.assertIn("3", valores)  # páginas del site_config

    def test_el_filtro_por_grupo_acota_la_tabla(self):
        self.root.update()
        self.pestana._widgets["grupo"].set("cr-gov")
        self.pestana._pintar_tabla()
        self.root.update()
        self.assertEqual(self.pestana._widgets["tabla"].get_children(),
                         ("acme-cr",))

    def test_ejecutar_seleccionados_pinta_el_resumen(self):
        self.root.update()
        tabla = self.pestana._widgets["tabla"]
        tabla.selection_set("intel-cr")
        resumen = scraper.ResumenBarrido(resultados=[
            scraper.ResultadoSitio("intel-cr", "Workday", scraper.ESTADO_OK,
                                    jobs_found=7, jobs_new=2, jobs_duplicate=5,
                                    jobs_skipped=1),
        ])
        with unittest.mock.patch.object(
                scraping_mod.scraper, "ejecutar_barrido",
                return_value=resumen) as ejecutar:
            self.pestana.ejecutar_seleccion()
            self.assertTrue(self._esperar(
                lambda: self.pestana._widgets["resumen_nuevas"].cget("text") == "2"))
        ejecutar.assert_called_once()
        self.assertEqual(ejecutar.call_args.args[0], ["intel-cr"])
        self.assertEqual(self.pestana._widgets["resumen_encontradas"].cget("text"),
                         "7")
        self.assertEqual(self.pestana._widgets["resumen_duplicadas"].cget("text"),
                         "5")
        log = self.pestana._widgets["log"].get("1.0", "end")
        self.assertIn("Barrido", log)

    def test_sin_seleccion_no_lanza_nada(self):
        self.root.update()
        with unittest.mock.patch.object(scraping_mod.scraper,
                                        "ejecutar_barrido") as ejecutar:
            self.pestana.ejecutar_seleccion()
        self.assertFalse(ejecutar.called)

    def test_cancelar_pide_el_fin(self):
        self.root.update()
        self.pestana._corriendo = True
        self.pestana.cancelar()
        self.assertTrue(self.pestana._cancelar.is_set())


if __name__ == "__main__":
    unittest.main()
