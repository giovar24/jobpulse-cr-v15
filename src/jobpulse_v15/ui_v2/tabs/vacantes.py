# -*- coding: utf-8 -*-
"""Pestaña "Vacantes": el RANKING ATS de los avisos contra tu perfil.

Simula lo que haría un ATS real, pero en la dirección útil: en vez de ordenar
candidatos para un puesto, ordena las vacantes para el perfil de la persona
que tiene el CV cargado. Cada fila trae el score 0-100, el veredicto
(fuerte / ajustable / débil) y el desglose de los componentes.

El cálculo pesado (embeddings) corre en un HILO DE SEGUUNDO PLANO: la UI no
se congela y los resultados se entregan por una cola (Tk solo se toca desde
el hilo principal).
"""
from __future__ import annotations

import queue
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk
from typing import Any

from jobpulse_v15.ui_v2.data.vacantes import (
    AtsStore,
    ETIQUETAS_VEREDICTO,
    VacanteAts,
    exportar_csv,
    filtrar,
    resumen,
)
from jobpulse_v15.ui_v2.tabs.base import BaseTab
from jobpulse_v15.ui_v2.widgets import (
    Badge,
    Card,
    EmptyState,
    FlatButton,
    KeyValue,
    ScrollFrame,
    SearchField,
    SectionTitle,
    StatTile,
)

COLUMNAS = (
    "score",
    "veredicto",
    "titulo",
    "empresa",
    "area",
    "semantica",
    "skills",
    "experiencia",
    "idiomas",
    "paso5",
)

TITULOS = {
    "score": "Score",
    "veredicto": "Veredicto",
    "titulo": "Puesto",
    "empresa": "Empresa",
    "area": "Área",
    "semantica": "Sem.",
    "skills": "Skills",
    "experiencia": "Exp.",
    "idiomas": "Idiomas",
    "paso5": "Paso 5",
}

ANCHOS = {
    "score": 70,
    "veredicto": 100,
    "titulo": 300,
    "empresa": 160,
    "area": 150,
    "semantica": 70,
    "skills": 70,
    "experiencia": 70,
    "idiomas": 80,
    "paso5": 130,
}

TONOS = {
    "fuerte": "success",
    "ajustable": "warning",
    "debil": "danger",
    "sin_datos": "neutral",
}


class VacantesTab(BaseTab):
    """Ranking ATS de las vacantes contra el perfil del candidato."""

    key = "vacantes"
    title = "Vacantes"
    subtitle = "Ranking ATS: las vacantes que mejor encajan con tu perfil"
    icon = "★"

    def __init__(self, context) -> None:
        super().__init__(context)
        self.store: AtsStore = context.services.setdefault(
            "ats_store", AtsStore(context.repository)
        )
        self.filas: list[VacanteAts] = []
        self.detalle: VacanteAts | None = None
        self._widgets: dict[str, Any] = {}
        self._cola: queue.Queue = queue.Queue()
        self._calculando = False
        self._areas_perfil: set[str] = set()

    # -- construcción --
    def build(self, parent: tk.Misc) -> tk.Frame:
        marco = super().build(parent)
        theme = self.theme
        marco.columnconfigure(0, weight=1)
        marco.rowconfigure(2, weight=1)

        self._build_toolbar(marco)
        self._build_resumen(marco)
        self._build_cuerpo(marco)
        self._build_estado(marco)
        return marco

    def _build_toolbar(self, parent: tk.Misc) -> None:
        theme = self.theme
        barra = tk.Frame(parent, bg=theme.color("bg"))
        barra.grid(row=0, column=0, sticky="ew", padx=theme.metrics.pad, pady=(theme.metrics.pad, 8))
        barra.columnconfigure(1, weight=1)

        self._widgets["buscador"] = SearchField(
            barra, theme, placeholder="Buscar por puesto o empresa…",
            on_change=lambda _t: self._pintar_tabla(),
        )
        self._widgets["buscador"].grid(row=0, column=0, sticky="ew")

        combo = ttk.Combobox(
            barra,
            values=["Todos los veredictos"] + [
                ETIQUETAS_VEREDICTO[clave] for clave in ETIQUETAS_VEREDICTO
            ],
            state="readonly",
            width=18,
            font=theme.font(9),
        )
        combo.current(0)
        combo.bind("<<ComboboxSelected>>", lambda _e: self._pintar_tabla())
        combo.grid(row=0, column=1, sticky="e", padx=(10, 0))
        self._widgets["veredicto"] = combo

        self._widgets["solo_miperfil"] = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            barra, text="Solo áreas de mi perfil",
            variable=self._widgets["solo_miperfil"],
            command=self._pintar_tabla,
        ).grid(row=0, column=2, padx=(12, 0))

        FlatButton(barra, theme, "Recalcular", command=self.recalcular, variant="flat").grid(
            row=0, column=3, padx=(12, 0)
        )
        FlatButton(barra, theme, "Exportar CSV", command=self.exportar, variant="flat").grid(
            row=0, column=4, padx=(8, 0)
        )

    def _build_resumen(self, parent: tk.Misc) -> None:
        theme = self.theme
        franja = tk.Frame(parent, bg=theme.color("bg"))
        franja.grid(row=1, column=0, sticky="ew", padx=theme.metrics.pad, pady=(0, 10))
        definiciones = (
            ("total", "Avisos"),
            ("fuerte", "Fuerte"),
            ("ajustable", "Ajustable"),
            ("debil", "Débil"),
            ("sin_datos", "Sin datos"),
        )
        self._tiles = {}
        for indice, (clave, etiqueta) in enumerate(definiciones):
            franja.columnconfigure(indice, weight=1, uniform="tiles")
            tarjeta = Card(franja, theme, padding=14)
            tarjeta.grid(row=0, column=indice, sticky="nsew", padx=(0 if indice == 0 else 6, 6))
            # OJO: el StatTile debe empaquetarse dentro de la tarjeta; si solo
            # se crea como hijo, queda con geometría 1x1 y no se ve.
            tile = StatTile(tarjeta.body, theme, etiqueta)
            tile.pack(fill="both", expand=True)
            self._tiles[clave] = tile

    def _build_cuerpo(self, parent: tk.Misc) -> None:
        theme = self.theme
        cuerpo = tk.Frame(parent, bg=theme.color("bg"))
        cuerpo.grid(row=2, column=0, sticky="nsew", padx=theme.metrics.pad)
        cuerpo.columnconfigure(0, weight=1)
        cuerpo.rowconfigure(0, weight=1)

        tarjeta = Card(cuerpo, theme, padding=0)
        tarjeta.grid(row=0, column=0, sticky="nsew")
        marco_tabla = tk.Frame(tarjeta.body, bg=theme.color("surface"))
        marco_tabla.pack(fill="both", expand=True)
        marco_tabla.columnconfigure(0, weight=1)
        marco_tabla.rowconfigure(0, weight=1)

        self._widgets["tabla"] = ttk.Treeview(
            marco_tabla,
            columns=list(COLUMNAS),
            show="headings",
            selectmode="browse",
            style="Flat.Treeview",
        )
        for columna in COLUMNAS:
            self._widgets["tabla"].heading(columna, text=TITULOS[columna])
            self._widgets["tabla"].column(
                columna, width=ANCHOS[columna], anchor="w", stretch=(columna == "titulo")
            )
        self._widgets["tabla"].grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(marco_tabla, orient="vertical",
                               command=self._widgets["tabla"].yview,
                               style="Flat.Vertical.TScrollbar")
        scroll.grid(row=0, column=1, sticky="ns")
        scroll_x = ttk.Scrollbar(marco_tabla, orient="horizontal",
                                 command=self._widgets["tabla"].xview,
                                 style="Flat.Horizontal.TScrollbar")
        scroll_x.grid(row=1, column=0, sticky="ew")
        self._widgets["tabla"].configure(yscrollcommand=scroll.set, xscrollcommand=scroll_x.set)
        self._widgets["tabla"].bind("<<TreeviewSelect>>", self._on_seleccion)

        # El estado vacío se posiciona con GRID (el mismo gestor que usa el
        # marco de la tabla): mezclar pack y grid en un mismo padre es error
        # de Tk. Se crea DESPUÉS de la tabla para quedar por encima.
        self._widgets["vacio"] = EmptyState(
            marco_tabla, theme, "Sin ranking",
            "Pulsa «Recalcular» para calcular el score ATS de los avisos.",
        )
        self._widgets["vacio"].grid(row=0, column=0, columnspan=2, sticky="nsew")
        self._widgets["vacio"].grid_remove()

        panel = Card(cuerpo, theme, padding=0)
        panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        cuerpo.columnconfigure(1, weight=0, minsize=theme.metrics.detail_width)
        panel.body.pack_propagate(False)

        scroll_frame = ScrollFrame(panel.body, theme)
        scroll_frame.pack(fill="both", expand=True)
        self._widgets["detalle"] = scroll_frame
        self._construir_detalle(scroll_frame.inner)

    def _construir_detalle(self, parent: tk.Misc) -> None:
        theme = self.theme
        self._widgets["detalle_vacio"] = EmptyState(
            parent, theme, "Ninguna vacante seleccionada",
            "Elige una fila para ver el desglose del score ATS.",
        )
        self._widgets["detalle_vacio"].pack(fill="both", expand=True)

        self._widgets["detalle_cuerpo"] = tk.Frame(parent, bg=theme.color("surface"))

        def seccion(titulo: str) -> tk.Frame:
            marco = tk.Frame(self._widgets["detalle_cuerpo"], bg=theme.color("surface"))
            SectionTitle(marco, theme, titulo).pack(fill="x", pady=(16, 6))
            return marco

        bloque_id = seccion("Vacante")
        self._widgets["kv"] = {}
        for clave, etiqueta in (
            ("titulo", "Puesto"),
            ("empresa", "Empresa"),
            ("area", "Área"),
            ("score", "Score ATS"),
            ("veredicto", "Veredicto"),
            ("paso5", "Estado Paso 5"),
            ("analisis", "Análisis"),
            ("idioma_aviso", "Idioma del aviso"),
        ):
            fila = KeyValue(bloque_id, theme, etiqueta, "—")
            fila.pack(fill="x", pady=2)
            self._widgets["kv"][clave] = fila

        bloque_comp = seccion("Componentes")
        for clave, etiqueta in (
            ("semantica", "Semántica"),
            ("skills", "Skills"),
            ("experiencia", "Experiencia"),
            ("educacion", "Educación"),
            ("idiomas", "Idiomas"),
        ):
            fila = KeyValue(bloque_comp, theme, etiqueta, "—")
            fila.pack(fill="x", pady=2)
            self._widgets["kv"][clave] = fila

        self._widgets["bloque_cubiertas"] = seccion("Skills cubiertas por tu perfil")
        self._widgets["bloque_faltantes"] = seccion("Skills que te faltan")

        acciones = tk.Frame(self._widgets["detalle_cuerpo"], bg=theme.color("surface"))
        acciones.pack(fill="x", pady=(18, 6))
        self._widgets["abrir"] = FlatButton(
            acciones, theme, "Abrir aviso en el navegador",
            command=self._abrir_navegador, variant="flat",
        )
        self._widgets["abrir"].pack(side="left")

    def _build_estado(self, parent: tk.Misc) -> None:
        theme = self.theme
        marco = tk.Frame(parent, bg=theme.color("bg"))
        marco.grid(row=3, column=0, sticky="ew", padx=theme.metrics.pad, pady=(8, 12))
        self._widgets["estado"] = tk.Label(
            marco, text="", bg=theme.color("bg"), fg=theme.color("text_muted"),
            font=theme.font(9), anchor="w",
        )
        self._widgets["estado"].pack(side="left")
        self._widgets["badge"] = Badge(marco, theme, "", "neutral")
        self._widgets["badge"].pack(side="right")

    # -- datos --
    def on_show(self) -> None:
        """Al abrir la pestaña: calcula el ranking si aún no se tiene."""
        try:
            self._areas_perfil = self.store.areas_del_perfil()
        except Exception:  # pragma: no cover - defensivo
            self._areas_perfil = set()
        if not self.filas and not self._calculando:
            self.recalcular()

    def refresh(self) -> None:
        """Repinta la vista con los filtros actuales (no recalcula el score)."""
        self._pintar_tabla()
        self._pintar_resumen()
        self._pintar_estado()

    def recalcular(self) -> None:
        """Lanza el cálculo en segundo plano (nunca bloquea la UI)."""
        if self._calculando:
            return
        if not self.store.avisos(limite=1):
            self.filas = []
            self._widgets["estado"].configure(text="No hay avisos guardados para rankear.")
            self._widgets["badge"].set_text("Vacío")
            self._widgets["badge"].set_tone("neutral")
            self._pintar_tabla()
            self._pintar_resumen()
            self._pintar_estado()
            return
        if self.frame is None:
            # La pestaña todavía no está montada: no hay a quién avisar con
            # `after`, así que el cálculo va en línea.
            self._calcular_en_linea()
            return
        self._calculando = True
        self._widgets["estado"].configure(text="Calculando el ranking ATS…")
        self._widgets["badge"].set_text("Calculando")
        self._widgets["badge"].set_tone("warning")

        def trabajo() -> None:
            try:
                engine = self._crear_engine()
                filas = self.store.calcular(
                    engine=engine,
                    progreso=lambda texto: self._cola.put(("progreso", texto)),
                )
            except Exception as error:  # pragma: no cover - defensivo
                self._cola.put(("error", str(error)))
                return
            self._cola.put(("listo", filas))

        threading.Thread(target=trabajo, daemon=True).start()
        self._after(120, self._vigilar)

    def _calcular_en_linea(self) -> None:
        """Calculo sincronico (pestana no montada)."""
        try:
            filas = self.store.calcular(engine=self._crear_engine())
        except Exception as error:  # pragma: no cover - defensivo
            self._widgets["estado"].configure(text=f"Error al calcular: {error}")
            return
        self.filas = list(filas)
        self._pintar_tabla()
        self._pintar_resumen()
        self._pintar_estado()

    def _after(self, milisegundos: int, callback) -> None:
        """Programa un callback en el hilo principal de Tk.

        La pestaña NO es un widget: el `after` va por el marco que devolvio
        `build()` (o su toplevel), nunca por `self`.
        """
        widget = self.frame
        if widget is None:
            return
        widget.after(milisegundos, callback)

    @staticmethod
    def _crear_engine() -> Any:
        """Motor de embeddings local (opcional: sin él, el score funciona igual)."""
        from jobpulse_v15.search_engine import SemanticSearchEngine

        return SemanticSearchEngine()

    def _vigilar(self) -> None:
        """Vacía la cola y actualiza la UI (siempre en el hilo principal)."""
        terminado = False
        while True:
            try:
                tipo, dato = self._cola.get_nowait()
            except queue.Empty:
                break
            if tipo == "progreso":
                self._widgets["estado"].configure(text=str(dato))
            elif tipo == "listo":
                self.filas = list(dato)
                self._calculando = False
                self._pintar_tabla()
                self._pintar_resumen()
                self._pintar_estado()
                terminado = True
            elif tipo == "error":
                self._calculando = False
                self._widgets["estado"].configure(text=f"Error al calcular: {dato}")
                self._widgets["badge"].set_text("Error")
                self._widgets["badge"].set_tone("danger")
                messagebox.showerror("Ranking ATS", f"No se pudo calcular el score:\n{dato}")
                terminado = True
        if not terminado and self._calculando:
            self._after(120, self._vigilar)

    def _filas_visibles(self) -> list[VacanteAts]:
        combo = self._widgets.get("veredicto")
        veredicto = ""
        if combo is not None and combo.current() > 0:
            claves = list(ETIQUETAS_VEREDICTO)
            veredicto = claves[combo.current() - 1]
        buscador = self._widgets.get("buscador")
        solo_miperfil = bool(self._widgets["solo_miperfil"].get())
        return filtrar(
            self.filas,
            texto=buscador.value() if buscador is not None else "",
            veredicto=veredicto,
            solo_mi_perfil=solo_miperfil,
            areas_perfil=self._areas_perfil,
        )

    def _pintar_tabla(self) -> None:
        filas = self._filas_visibles()
        tabla = self._widgets["tabla"]
        tabla.delete(*tabla.get_children())
        for fila in filas:
            tabla.insert(
                "", "end", iid=fila.job_id,
                values=(
                    f"{fila.score:.0f}" if fila.score is not None else "n/d",
                    fila.veredicto_legible,
                    fila.title,
                    fila.company,
                    fila.area,
                    _pct(fila.semantica_pct),
                    _pct(fila.skills_pct),
                    _pct(fila.experiencia_pct),
                    _pct(fila.idiomas_pct),
                    fila.estado_paso5 or "—",
                ),
            )
        vacio = self._widgets["vacio"]
        if filas:
            vacio.grid_remove()
        else:
            vacio.grid()
        self._widgets["conteo"] = len(filas)

    def _pintar_resumen(self) -> None:
        cifras = resumen(self._filas_visibles())
        self._tiles["total"].update_values(str(cifras["total"]))
        self._tiles["fuerte"].update_values(str(cifras["fuerte"]))
        self._tiles["ajustable"].update_values(str(cifras["ajustable"]))
        self._tiles["debil"].update_values(str(cifras["debil"]))
        self._tiles["sin_datos"].update_values(str(cifras["sin_datos"]))

    def _pintar_estado(self) -> None:
        total = len(self.filas)
        visibles = self._widgets.get("conteo", 0)
        if total:
            self._widgets["estado"].configure(
                text=f"{total} aviso(s) rankeados · {visibles} en la vista"
            )
        else:
            self._widgets["estado"].configure(
                text="No hay avisos guardados para rankear."
            )
        badge = self._widgets["badge"]
        if total:
            badge.set_text("Listo")
            badge.set_tone("success")
        else:
            badge.set_text("Vacío")
            badge.set_tone("neutral")

    # -- detalle --
    def _on_seleccion(self, _event=None) -> None:
        seleccion = self._widgets["tabla"].selection()
        if not seleccion:
            return
        job_id = seleccion[0]
        for fila in self.filas:
            if fila.job_id == job_id:
                self.detalle = fila
                self._pintar_detalle(fila)
                break

    def _pintar_detalle(self, fila: VacanteAts) -> None:
        vacio = self._widgets["detalle_vacio"]
        cuerpo = self._widgets["detalle_cuerpo"]
        if vacio.winfo_ismapped():
            vacio.pack_forget()
        if not cuerpo.winfo_ismapped():
            cuerpo.pack(fill="both", expand=True)

        valores = {
            "titulo": fila.title,
            "empresa": fila.company,
            "area": fila.area,
            "score": f"{fila.score:.1f} / 100" if fila.score is not None else "n/d",
            "veredicto": fila.veredicto_legible,
            "paso5": fila.estado_paso5 or "sin correr",
            "analisis": fila.analysis_status or "not_analyzed",
            "idioma_aviso": fila.posting_language or "—",
            "semantica": _detalle(fila.semantica_pct, fila.componentes.get("semantica", "")),
            "skills": _detalle(fila.skills_pct, fila.componentes.get("skills", "")),
            "experiencia": _detalle(fila.experiencia_pct, fila.componentes.get("experiencia", "")),
            "educacion": _detalle(fila.educacion_pct, fila.componentes.get("educacion", "")),
            "idiomas": _detalle(fila.idiomas_pct, fila.componentes.get("idiomas", "")),
        }
        for clave, valor in valores.items():
            self._widgets["kv"][clave].set_value(valor)

        self._pintar_lista(self._widgets["bloque_cubiertas"], fila.skills_cubiertas, "Ninguna")
        self._pintar_lista(self._widgets["bloque_faltantes"], fila.skills_faltantes, "Ninguna")
        self._widgets["detalle"].scroll_to_top()

    def _pintar_lista(self, marco: tk.Frame, elementos: tuple[str, ...], vacio: str) -> None:
        for hijo in marco.winfo_children()[1:]:
            hijo.destroy()
        if not elementos:
            tk.Label(
                marco, text=vacio, bg=self.theme.color("surface"),
                fg=self.theme.color("text_faint"), font=self.theme.font(9),
            ).pack(anchor="w")
            return
        for elemento in elementos:
            tk.Label(
                marco, text=f"• {elemento}", bg=self.theme.color("surface"),
                fg=self.theme.color("text"), font=self.theme.font(9), anchor="w",
            ).pack(anchor="w")

    # -- acciones --
    def _abrir_navegador(self) -> None:
        if self.detalle and self.detalle.source_url:
            webbrowser.open(self.detalle.source_url)

    def exportar(self) -> None:
        filas = self._filas_visibles()
        if not filas:
            messagebox.showinfo("Exportar CSV", "No hay vacantes en la vista para exportar.")
            return
        ruta = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Todos los archivos", "*.*")],
            initialfile="vacantes_ranking_ats.csv",
        )
        if not ruta:
            return
        try:
            total = exportar_csv(filas, ruta)
        except OSError as error:
            messagebox.showerror("Exportar CSV", f"No se pudo escribir el archivo:\n{error}")
            return
        messagebox.showinfo("Exportar CSV", f"Se exportaron {total} vacante(s).")


def _pct(valor: float | None) -> str:
    if valor is None:
        return "n/d"
    return f"{valor:.0f}%"


def _detalle(pct: float | None, texto: str) -> str:
    if pct is None:
        return texto or "n/d"
    # El componente semantico ya trae su propio texto ("percentil 87 del
    # corpus"): no se repite el porcentaje.
    if texto and "%" in texto:
        return texto
    return f"{pct:.0f} % · {texto}" if texto else f"{pct:.0f} %"
