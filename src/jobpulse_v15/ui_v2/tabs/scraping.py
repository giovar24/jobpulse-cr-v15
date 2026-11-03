# -*- coding: utf-8 -*-
"""Pestaña "Scraping": lanzar un barrido de las fuentes del sistema.

Es la operación que hasta ahora solo se podía hacer por CLI
(`run_scrapes.py`, `run_full_flow.py`, `jobpulse_v15 scrape ...`).

- **Selección**: por grupo de corrida (`directos`, `cr-gov`, `cr-jobs`) o
  por selección directa en la tabla. Solo entran los sitios **activos**: lo
  que pausó la tarjeta "Sondas de scraping" de Configuración.
- **Ejecución**: en un hilo (el worker NUNCA toca Tk: encola en la cola de
  `BaseTab` y el vigilante la drena en el hilo principal).
- **Brave**: `scraper.ejecutar_barrido` abre el navegador solo si hace falta
  y lo cierra solo si él lo abrió (O7.2).
- **Cancelar**: termina **después** del sitio en curso (no se corta un fetch
  a medias, para no dejar la corrida a medias en la BD).
"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk
from typing import Any

from jobpulse_v15 import scraper
from jobpulse_v15.ui_v2 import configuracion
from jobpulse_v15.ui_v2.data.scraping import TODOS, ScrapingStore
from jobpulse_v15.ui_v2.tabs.base import BaseTab
from jobpulse_v15.ui_v2.widgets import Card, FlatButton, SectionTitle

MAX_PAGINAS = 10
# El puerto CDP sale de la configuración (BRAVE_CDP_PORT en el .env), que es
# la misma que usan el CLI y los scripts; si no hay, 9222.


class ScrapingTab(BaseTab):
    """Ejecuta y sigue un barrido de scraping."""

    key = "scraping"
    title = "Scraping"
    subtitle = "Ejecutar un barrido de las fuentes del sistema"
    icon = "⟳"

    def __init__(self, context) -> None:
        super().__init__(context)
        self.store: ScrapingStore = context.services.setdefault(
            "scraping_store", ScrapingStore(context.repository)
        )
        self._widgets: dict[str, Any] = {}
        self._cancelar = threading.Event()
        self._corriendo = False

    # ================================================================
    # Construcción
    # ================================================================
    def build(self, parent: tk.Misc) -> tk.Frame:
        marco = super().build(parent)
        theme = self.theme
        marco.rowconfigure(2, weight=1)
        marco.columnconfigure(0, weight=1)

        self._card_controles(marco)
        self._card_resumen(marco)
        self._card_tabla(marco)
        self._card_log(marco)
        return marco

    # -- controles --------------------------------------------------
    def _card_controles(self, parent: tk.Misc) -> None:
        theme = self.theme
        card = Card(parent, theme, padding=theme.metrics.pad // 2)
        card.grid(row=0, column=0, sticky="ew", padx=theme.metrics.pad,
                  pady=(theme.metrics.pad, 0))

        fila = tk.Frame(card.body, bg=theme.color("surface"))
        fila.pack(fill="x")

        tk.Label(fila, text="Grupo:", bg=theme.color("surface"),
                 fg=theme.color("text_muted"), font=theme.font(9)).pack(side="left")
        combo = ttk.Combobox(
            fila, values=[TODOS] + self.store.grupos(), state="readonly",
            width=18, font=theme.font(9),
        )
        combo.current(0)
        combo.bind("<<ComboboxSelected>>", lambda _e: self._pintar_tabla())
        combo.pack(side="left", padx=(6, 0))
        self._widgets["grupo"] = combo

        tk.Label(fila, text="Páginas:", bg=theme.color("surface"),
                 fg=theme.color("text_muted"), font=theme.font(9)).pack(
            side="left", padx=(16, 0))
        self._widgets["paginas"] = tk.IntVar(value=2)
        spin = ttk.Spinbox(fila, from_=1, to=MAX_PAGINAS, width=5,
                           textvariable=self._widgets["paginas"],
                           font=theme.font(9))
        spin.pack(side="left", padx=(6, 0))

        tk.Label(fila, text="Puerto CDP:", bg=theme.color("surface"),
                 fg=theme.color("text_muted"), font=theme.font(9)).pack(
            side="left", padx=(16, 0))
        self._widgets["puerto"] = tk.StringVar(
            value=str(configuracion.puerto_cdp()))
        tk.Entry(fila, textvariable=self._widgets["puerto"], width=7,
                 font=theme.font(9)).pack(side="left", padx=(6, 0))

        botones = tk.Frame(fila, bg=theme.color("surface"))
        botones.pack(side="right")
        self._widgets["cancelar"] = FlatButton(
            botones, theme, "Cancelar", command=self.cancelar, variant="ghost")
        self._widgets["cancelar"].pack(side="left", padx=(6, 0))
        self._widgets["cancelar"].configure(state="disabled")
        FlatButton(botones, theme, "Ejecutar grupo",
                   command=self.ejecutar_grupo).pack(side="left")
        self._widgets["ejecutar"] = FlatButton(
            botones, theme, "Ejecutar seleccionados",
            command=self.ejecutar_seleccion, variant="accent")
        self._widgets["ejecutar"].pack(side="left", padx=(8, 0))

        tk.Label(
            card.body,
            text=("Solo se barren los sitios activos. «Páginas» es el valor "
                  "por defecto: cada sitio usa el suyo de site_config si lo "
                  "tiene. El puerto CDP solo afecta a ANE, Indeed, "
                  "LinkedIn y Elempleo."),
            bg=theme.color("surface"), fg=theme.color("text_faint"),
            font=theme.font(8), anchor="w",
        ).pack(fill="x", pady=(6, 0))

    # -- resumen ----------------------------------------------------
    def _card_resumen(self, parent: tk.Misc) -> None:
        theme = self.theme
        card = Card(parent, theme, padding=theme.metrics.pad // 2)
        card.grid(row=1, column=0, sticky="ew", padx=theme.metrics.pad,
                  pady=(theme.metrics.gap // 2, 0))
        fila = tk.Frame(card.body, bg=theme.color("surface"))
        fila.pack(fill="x")
        for clave, etiqueta in (("encontradas", "Encontradas"),
                                ("nuevas", "Nuevas"),
                                ("duplicadas", "Duplicadas"),
                                ("omitidas", "Omitidas"),
                                ("errores", "Errores")):
            marco = tk.Frame(fila, bg=theme.color("surface"))
            marco.pack(side="left", padx=(0, 24))
            valor = tk.Label(marco, text="0", bg=theme.color("surface"),
                             fg=theme.color("text"), font=theme.font(13, "bold"))
            valor.pack(anchor="w")
            tk.Label(marco, text=etiqueta, bg=theme.color("surface"),
                     fg=theme.color("text_faint"), font=theme.font(8)).pack(anchor="w")
            self._widgets[f"resumen_{clave}"] = valor
        self._widgets["estado"] = tk.Label(
            fila, text="Listo.", bg=theme.color("surface"),
            fg=theme.color("text_muted"), font=theme.font(9), anchor="e")
        self._widgets["estado"].pack(side="right")

    # -- tabla ------------------------------------------------------
    def _card_tabla(self, parent: tk.Misc) -> None:
        theme = self.theme
        card = Card(parent, theme, padding=theme.metrics.pad // 2)
        card.grid(row=2, column=0, sticky="nsew", padx=theme.metrics.pad,
                  pady=(theme.metrics.gap // 2, 0))
        card.body.columnconfigure(0, weight=1)
        card.body.rowconfigure(1, weight=1)

        SectionTitle(card.body, theme, "Fuentes",
                     hint="seleccioná las que quieras barrer").grid(
            row=0, column=0, sticky="ew")

        marco_tabla = tk.Frame(card.body, bg=theme.color("surface"))
        marco_tabla.grid(row=1, column=0, sticky="nsew")
        marco_tabla.columnconfigure(0, weight=1)
        marco_tabla.rowconfigure(0, weight=1)

        columnas = ("estado", "plataforma", "sitio", "paginas", "grupo")
        tree = ttk.Treeview(
            marco_tabla, columns=columnas, show="headings",
            selectmode="extended", style="Flat.Treeview",
        )
        anchos = {"estado": 90, "plataforma": 150, "sitio": 380,
                  "paginas": 70, "grupo": 130}
        for col in columnas:
            tree.heading(col, text=col.upper())
            tree.column(col, width=anchos[col], minwidth=60,
                        stretch=(col == "sitio"))
        tree.grid(row=0, column=0, sticky="nsew")
        barra = ttk.Scrollbar(marco_tabla, orient="vertical", command=tree.yview,
                               style="Flat.Vertical.TScrollbar")
        barra.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=barra.set)
        tree.tag_configure("pausado", foreground=theme.color("text_faint"))
        self._widgets["tabla"] = tree

    # -- log --------------------------------------------------------
    def _card_log(self, parent: tk.Misc) -> None:
        theme = self.theme
        card = Card(parent, theme, padding=theme.metrics.pad // 2)
        card.grid(row=3, column=0, sticky="ew", padx=theme.metrics.pad,
                  pady=(theme.metrics.gap // 2, theme.metrics.pad))
        card.body.columnconfigure(0, weight=1)

        SectionTitle(card.body, theme, "Bitácora").grid(row=0, column=0, sticky="ew")
        texto = tk.Text(
            card.body, height=7, bd=0, relief="flat", wrap="word",
            bg=theme.color("surface_alt"), fg=theme.color("text"),
            insertbackground=theme.color("text"), font=theme.font(9),
            highlightthickness=1, highlightbackground=theme.color("border"),
        )
        texto.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        texto.configure(state="disabled")
        self._widgets["log"] = texto

    # ================================================================
    # Ciclo de vida
    # ================================================================
    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        if "tabla" in self._widgets:
            self._pintar_tabla()

    # ================================================================
    # Tabla y resumen
    # ================================================================
    def _grupo_elegido(self) -> str | None:
        elegido = self._widgets["grupo"].get()
        return None if (not elegido or elegido == TODOS) else elegido

    def _pintar_tabla(self) -> None:
        tree: ttk.Treeview = self._widgets["tabla"]
        seleccion = set(tree.selection())
        for iid in tree.get_children():
            tree.delete(iid)
        for fila in self.store.sitios(self._grupo_elegido()):
            tree.insert(
                "", "end", iid=fila.site_id,
                values=("Activo" if fila.activo else "Pausado", fila.plataforma,
                        fila.nombre, fila.paginas or "—",
                        ", ".join(fila.grupos) or "—"),
                tags=() if fila.activo else ("pausado",),
            )
        if seleccion:
            tree.selection_set(*[i for i in seleccion if tree.exists(i)])

    def _log(self, linea: str) -> None:
        texto = self._widgets.get("log")
        if texto is None:
            return
        try:
            texto.configure(state="normal")
            texto.insert("end", linea.rstrip() + "\n")
            texto.see("end")
            texto.configure(state="disabled")
        except tk.TclError:
            pass

    def _estado(self, texto: str) -> None:
        etiqueta = self._widgets.get("estado")
        if etiqueta is not None:
            try:
                etiqueta.configure(text=texto)
            except tk.TclError:
                pass

    def _pintar_resumen(self, clave: str, valor: int) -> None:
        etiqueta = self._widgets.get(f"resumen_{clave}")
        if etiqueta is not None:
            try:
                etiqueta.configure(text=str(valor))
            except tk.TclError:
                pass

    # ================================================================
    # Ejecución
    # ================================================================
    def _ids_seleccionados(self) -> list[str]:
        tree: ttk.Treeview = self._widgets["tabla"]
        return [iid for iid in tree.selection()]

    def ejecutar_seleccion(self) -> None:
        ids = self._ids_seleccionados()
        if not ids:
            self._estado("Selecciona al menos un sitio en la tabla.")
            return
        self._ejecutar(ids)

    def ejecutar_grupo(self) -> None:
        grupo = self._grupo_elegido()
        ids = self.store.sitios_para_barrer(grupo)
        if not ids:
            self._estado("No hay sitios activos en ese grupo.")
            return
        self._ejecutar(ids)

    def _puerto(self) -> int:
        """Puerto CDP de la casilla; si no es válido, el configurado."""
        texto = str(self._widgets["puerto"].get() or "").strip()
        if not texto:
            return configuracion.puerto_cdp()
        try:
            puerto = int(texto)
        except ValueError:
            return configuracion.puerto_cdp()
        return puerto if 1024 <= puerto <= 65535 else configuracion.puerto_cdp()

    def _paginas(self) -> int:
        try:
            return max(1, min(MAX_PAGINAS, int(self._widgets["paginas"].get())))
        except (TypeError, ValueError):
            return 2

    def _ejecutar(self, site_ids: list[str]) -> None:
        if self._corriendo:
            self._estado("Ya hay un barrido en marcha.")
            return
        # Las variables Tk se leen AQUÍ (hilo principal): el worker no puede
        # tocar Tk (ni siquiera un IntVar.get()).
        paginas = self._paginas()
        puerto = self._puerto()
        ruta_db = self.context.repository.database.path

        self._corriendo = True
        self._cancelar.clear()
        self._widgets["ejecutar"].configure(state="disabled")
        self._widgets["cancelar"].configure(state="normal")
        for clave in ("encontradas", "nuevas", "duplicadas", "omitidas", "errores"):
            self._pintar_resumen(clave, 0)
        self._estado(f"Barrido en marcha ({len(site_ids)} sitio(s))…")
        self._log(f"— Barrido iniciado: {len(site_ids)} sitio(s) —")

        def trabajo() -> None:
            resumen = scraper.ejecutar_barrido(
                site_ids,
                pages=paginas,
                port=puerto,
                database_path=ruta_db,
                on_progress=self._progreso,
                should_stop=self._cancelar.is_set,
            )
            self._programar(lambda: self._final(resumen))

        self._lanzar_hilo(trabajo)

    def _progreso(self, progreso: scraper.Progreso) -> None:
        """Callback del worker: SOLO encola (nunca toca Tk aquí)."""
        etapa = {
            "inicio": "→",
            "fin": "✓",
            "error": "✗",
            "aviso": "·",
        }.get(progreso.etapa, "·")
        linea = (f"{etapa} [{progreso.indice}/{progreso.total}] "
                 f"{progreso.plataforma} · {progreso.site_id} {progreso.detalle}")
        self._programar(lambda: self._log(linea))

    def _final(self, resumen: scraper.ResumenBarrido) -> None:
        self._corriendo = False
        self._widgets["ejecutar"].configure(state="normal")
        self._widgets["cancelar"].configure(state="disabled")
        self._pintar_resumen("encontradas", resumen.jobs_found)
        self._pintar_resumen("nuevas", resumen.jobs_new)
        self._pintar_resumen("duplicadas", resumen.jobs_duplicate)
        self._pintar_resumen("omitidas", resumen.jobs_skipped)
        self._pintar_resumen("errores", resumen.errores)
        texto = (f"Barrido cancelado ({len(resumen.resultados)} sitio(s) procesado(s))."
                 if resumen.cancelado else
                 f"Barrido terminado: {resumen.sitios_ok}/{len(resumen.resultados)} "
                 f"sitio(s) sin error.")
        self._estado(texto)
        self._log(f"— {texto} Encontradas: {resumen.jobs_found} · "
                  f"Nuevas: {resumen.jobs_new} · Duplicadas: {resumen.jobs_duplicate}")

    def cancelar(self) -> None:
        """Pide terminar: el barrido corta **después** del sitio en curso."""
        if not self._corriendo:
            return
        self._cancelar.set()
        self._estado("Cancelando (termina el sitio en curso)…")
        self._log("— Cancelación solicitada.")
