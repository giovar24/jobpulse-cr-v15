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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

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


if __name__ == "__main__":
    unittest.main()
