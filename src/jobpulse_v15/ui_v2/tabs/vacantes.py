# -*- coding: utf-8 -*-
"""Pestaña "Vacantes": el RANKING ATS de los avisos contra tu perfil.

Simula lo que haría un ATS real, pero en la dirección útil: en vez de ordenar
candidatos para un puesto, ordena las vacantes para el perfil de la persona
que tiene el CV cargado. Cada fila trae el score 0-100, el veredicto
(fuerte / ajustable / débil) y el desglose de los componentes.

El cálculo pesado (embeddings) corre en un HILO DE SEGUUNDO PLANO: la UI no
se congela y los resultados se entregan por una cola (Tk solo se toca desde
el hilo principal).

Además, el botón **Ejecutar Paso 5** corre el matching PERSISTIDO (la misma
corrida que `run_paso5.py` deja en `job_match`): al terminar, la columna
"Paso 5" de la tabla se puebla sola con los estados de esa corrida.
"""
from __future__ import annotations

import tkinter as tk
import webbrowser
from dataclasses import replace
from tkinter import filedialog, messagebox, ttk
from typing import Any

from jobpulse_v15.ui_v2 import configuracion
from jobpulse_v15.ui_v2.data.paso5 import Paso5Store, ResumenPaso5
from jobpulse_v15.ui_v2.data.vacantes import (
    AtsStore,
    BANDAS_VIABILIDAD,
    ETIQUETAS_BANDA,
    ETIQUETAS_VEREDICTO,
    VacanteAts,
    exportar_csv,
    filtrar,
    resumen,
    resumen_bandas,
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
from jobpulse_v15.ui_v2.i18n import t

COLUMNAS = (
    "score",
    "veredicto",
    "ajuste",
    "banda",
    "titulo",
    "empresa",
    "area",
    "skills",
    "experiencia",
    "idiomas",
    "req",
    "paso5",
)

TITULOS = {
    "score": "Score",
    "veredicto": "Veredicto",
    "ajuste": "Ajuste",
    "banda": "Banda",
    "titulo": "Puesto",
    "empresa": "Empresa",
    "area": "Área",
    "skills": "Skills",
    "experiencia": "Exp.",
    "idiomas": "Idiomas",
    "req": "Req.",
    "paso5": "Paso 5",
}

ANCHOS = {
    "score": 70,
    "veredicto": 100,
    "ajuste": 70,
    "banda": 110,
    "titulo": 300,
    "empresa": 160,
    "area": 150,
    "skills": 70,
    "experiencia": 70,
    "idiomas": 80,
    "req": 55,
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
            "ats_store",
            AtsStore(context.repository, context.services.get("retencion_store")),
        )
        self.paso5: Paso5Store = context.services.setdefault(
            "paso5_store", Paso5Store(context.repository)
        )
        self.filas: list[VacanteAts] = []
        self.detalle: VacanteAts | None = None
        self._widgets: dict[str, Any] = {}
        self._calculando = False
        self._corriendo_paso5 = False
        self._generando_evidencia = False
        self._areas_perfil: set[str] = set()

    # -- construcción --
    def build(self, parent: tk.Misc) -> tk.Frame:
        marco = super().build(parent)
        theme = self.theme
        marco.columnconfigure(0, weight=1)
        marco.rowconfigure(3, weight=1)

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
            barra, theme, placeholder=t("Buscar por puesto o empresa…"),
            on_change=lambda _t: self._pintar_tabla(),
        )
        self._widgets["buscador"].grid(row=0, column=0, sticky="ew")

        combo = ttk.Combobox(
            barra,
            values=[t("Todos los veredictos")] + [
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

        combo_banda = ttk.Combobox(
            barra,
            values=[t("Todas las bandas")] + [
                ETIQUETAS_BANDA[clave] for clave in BANDAS_VIABILIDAD
            ],
            state="readonly",
            width=18,
            font=theme.font(9),
        )
        combo_banda.current(0)
        combo_banda.bind("<<ComboboxSelected>>", lambda _e: self._pintar_tabla())
        combo_banda.grid(row=0, column=2, sticky="e", padx=(10, 0))
        self._widgets["banda"] = combo_banda

        self._widgets["solo_aplicar"] = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            barra, text=t("Solo aplicar"),
            variable=self._widgets["solo_aplicar"],
            command=self._pintar_tabla,
        ).grid(row=0, column=3, padx=(12, 0))

        self._widgets["solo_miperfil"] = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            barra, text=t("Solo áreas de mi perfil"),
            variable=self._widgets["solo_miperfil"],
            command=self._pintar_tabla,
        ).grid(row=0, column=4, padx=(12, 0))

        self._widgets["solo_requisitos"] = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            barra, text=t("Solo con requisitos obligatorios"),
            variable=self._widgets["solo_requisitos"],
            command=self._pintar_tabla,
        ).grid(row=0, column=5, padx=(12, 0))

        self._widgets["evaluar_todo"] = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            barra, text=t("Evaluar todo"),
            variable=self._widgets["evaluar_todo"],
        ).grid(row=0, column=6, padx=(12, 0))

        self._widgets["paso5"] = FlatButton(
            barra, theme, "Ejecutar Paso 5", command=self.ejecutar_paso5,
            variant="accent",
        )
        self._widgets["paso5"].grid(row=0, column=7, padx=(12, 0))

        FlatButton(barra, theme, "Recalcular", command=self.recalcular, variant="flat").grid(
            row=0, column=8, padx=(8, 0)
        )
        FlatButton(barra, theme, "Exportar CSV", command=self.exportar, variant="flat").grid(
            row=0, column=9, padx=(8, 0)
        )
        self._widgets["evidencia"] = FlatButton(
            barra, theme, "Evidencia", command=self.generar_evidencia, variant="flat"
        )
        self._widgets["evidencia"].grid(row=0, column=10, padx=(8, 0))

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

        # Franja del AJUSTE TECNICO (bandas del motor de viabilidad): es
        # otro indice que el ranking ATS (este dice si el perfil cumple lo
        # que el aviso pide).
        franja_bandas = tk.Frame(parent, bg=theme.color("bg"))
        franja_bandas.grid(row=2, column=0, sticky="ew", padx=theme.metrics.pad, pady=(0, 8))
        self._tiles_banda = {}
        for indice, banda in enumerate(BANDAS_VIABILIDAD):
            franja_bandas.columnconfigure(indice, weight=1, uniform="bandas")
            tarjeta = Card(franja_bandas, theme, padding=10)
            tarjeta.grid(row=0, column=indice, sticky="nsew", padx=(0 if indice == 0 else 6, 6))
            tile = StatTile(tarjeta.body, theme, ETIQUETAS_BANDA[banda])
            tile.pack(fill="both", expand=True)
            self._tiles_banda[banda] = tile

    def _build_cuerpo(self, parent: tk.Misc) -> None:
        theme = self.theme
        cuerpo = tk.Frame(parent, bg=theme.color("bg"))
        cuerpo.grid(row=3, column=0, sticky="nsew", padx=theme.metrics.pad)
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
            self._widgets["tabla"].heading(columna, text=t(TITULOS[columna]))
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
            ("ajuste", "Ajuste técnico"),
            ("banda", "Banda"),
            ("faltantes", "Faltantes obligatorios"),
            ("paso5", "Estado Paso 5"),
            ("analisis", "Análisis"),
            ("idioma_aviso", "Idioma del aviso"),
        ):
            fila = KeyValue(bloque_id, theme, etiqueta, "—")
            fila.pack(fill="x", pady=2)
            self._widgets["kv"][clave] = fila

        bloque_comp = seccion("Componentes")
        for clave, etiqueta in (
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
        marco.grid(row=4, column=0, sticky="ew", padx=theme.metrics.pad, pady=(8, 12))
        self._widgets["estado"] = tk.Label(
            marco, text="", bg=theme.color("bg"), fg=theme.color("text_muted"),
            font=theme.font(9), anchor="w",
        )
        self._widgets["estado"].pack(side="left")
        self._widgets["badge_obsoleto"] = Badge(marco, theme, "", "warning")
        self._widgets["badge_obsoleto"].pack(side="right", padx=(0, 8))
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
        self._pintar_badge_obsoleto()

    def refresh(self) -> None:
        """Repinta la vista con los filtros actuales (no recalcula el score)."""
        self._pintar_tabla()
        self._pintar_resumen()
        self._pintar_estado()
        self._pintar_badge_obsoleto()

    def _pintar_badge_obsoleto(self) -> int:
        """Badge de análisis obsoletos (O12 · Ola 1.2).

        Aviso para el usuario: hay avisos cuyas skills/idiomas (los produjo la
        IA) todavía no son requisitos comparables → saldrán ``sin_requisitos``
        aunque el perfil sí califique.
        """
        badge = self._widgets.get("badge_obsoleto")
        if badge is None:
            return 0
        try:
            obsoletos = self.paso5.analisis_obsoletos()
        except Exception:  # pragma: no cover - defensivo
            obsoletos = 0
        if obsoletos:
            badge.set_text(t("{} análisis obsoleto(s)").format(obsoletos))
            badge.set_tone("warning")
            if not badge.winfo_ismapped():
                badge.pack(side="right", padx=(0, 8))
        else:
            badge.set_text("")
            badge.set_tone("neutral")
            if badge.winfo_ismapped():
                badge.pack_forget()
        return obsoletos

    def recalcular(self) -> None:
        """Lanza el cálculo en segundo plano (nunca bloquea la UI)."""
        if self._calculando:
            return
        if not self.store.avisos(limite=1):
            self.filas = []
            self._widgets["estado"].configure(text=t("No hay avisos guardados para rankear."))
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
        self._widgets["estado"].configure(text=t("Calculando el ranking ATS…"))
        self._widgets["badge"].set_text("Calculando")
        self._widgets["badge"].set_tone("warning")

        def trabajo() -> None:
            try:
                filas = self.store.calcular(
                    progreso=lambda texto: self._programar(
                        lambda t=texto: self._pintar_progreso(str(t))),
                )
            except Exception as error:  # pragma: no cover - defensivo
                mensaje = str(error)
                self._programar(lambda: self._error_calculo(mensaje))
                return
            self._programar(lambda: self._listo(filas))

        self._lanzar_hilo(trabajo)

    def _calcular_en_linea(self) -> None:
        """Calculo sincronico (pestana no montada)."""
        try:
            filas = self.store.calcular()
        except Exception as error:  # pragma: no cover - defensivo
            self._widgets["estado"].configure(text=f"Error al calcular: {error}")
            return
        self.filas = list(filas)
        self._pintar_tabla()
        self._pintar_resumen()
        self._pintar_estado()

    def _pintar_progreso(self, texto: str) -> None:
        estado = self._widgets.get("estado")
        if estado is not None:
            try:
                estado.configure(text=texto)
            except tk.TclError:
                pass

    def _listo(self, filas: Any) -> None:
        self.filas = list(filas)
        self._calculando = False
        self._pintar_tabla()
        self._pintar_resumen()
        self._pintar_estado()

    def _error_calculo(self, mensaje: str) -> None:
        self._calculando = False
        self._widgets["estado"].configure(text=t("Error al calcular: {}").format(mensaje))
        self._widgets["badge"].set_text(t("Error"))
        self._widgets["badge"].set_tone("danger")
        messagebox.showerror(t("Ranking ATS"), t("No se pudo calcular el score:\n{}").format(mensaje))

    def _filas_visibles(self) -> list[VacanteAts]:
        combo = self._widgets.get("veredicto")
        veredicto = ""
        if combo is not None and combo.current() > 0:
            claves = list(ETIQUETAS_VEREDICTO)
            veredicto = claves[combo.current() - 1]
        combo_banda = self._widgets.get("banda")
        banda = ""
        if combo_banda is not None and combo_banda.current() > 0:
            banda = list(BANDAS_VIABILIDAD)[combo_banda.current() - 1]
        buscador = self._widgets.get("buscador")
        solo_miperfil = bool(self._widgets["solo_miperfil"].get())
        solo_requisitos = bool(self._widgets["solo_requisitos"].get())
        solo_aplicar = bool(self._widgets["solo_aplicar"].get())
        return filtrar(
            self.filas,
            texto=buscador.value() if buscador is not None else "",
            veredicto=veredicto,
            banda=banda,
            solo_aplicar=solo_aplicar,
            solo_mi_perfil=solo_miperfil,
            areas_perfil=self._areas_perfil,
            solo_requisitos=solo_requisitos,
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
                    f"{fila.ajuste:.0f}" if fila.ajuste is not None else "n/d",
                    fila.banda_legible,
                    fila.title,
                    fila.company,
                    fila.area,
                    _pct(fila.skills_pct),
                    _pct(fila.experiencia_pct),
                    _pct(fila.idiomas_pct),
                    str(fila.req_obligatorios),
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
        visibles = self._filas_visibles()
        cifras = resumen(visibles)
        self._tiles["total"].update_values(str(cifras["total"]))
        self._tiles["fuerte"].update_values(str(cifras["fuerte"]))
        self._tiles["ajustable"].update_values(str(cifras["ajustable"]))
        self._tiles["debil"].update_values(str(cifras["debil"]))
        self._tiles["sin_datos"].update_values(str(cifras["sin_datos"]))
        bandas = resumen_bandas(visibles)
        for banda, tile in self._tiles_banda.items():
            tile.update_values(str(bandas.get(banda, 0)))

    def _pintar_estado(self) -> None:
        total = len(self.filas)
        visibles = self._widgets.get("conteo", 0)
        if total:
            self._widgets["estado"].configure(
                text=f"{total} aviso(s) rankeados · {visibles} en la vista"
                + self._texto_evidencia()
            )
        else:
            self._widgets["estado"].configure(
                text=t("No hay avisos guardados para rankear.")
            )
        badge = self._widgets["badge"]
        if total:
            badge.set_text(t("Listo"))
            badge.set_tone("success")
        else:
            badge.set_text(t("Vacío"))
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
            "ajuste": f"{fila.ajuste:.1f} / 100" if fila.ajuste is not None else "n/d",
            "banda": fila.banda_legible,
            "faltantes": (
                "; ".join(fila.faltantes_obligatorios)
                if fila.faltantes_obligatorios
                else "—"
            ),
            "paso5": fila.estado_paso5 or "sin correr",
            "analisis": fila.analysis_status or "not_analyzed",
            "idioma_aviso": fila.posting_language or "—",
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

    # -- Paso 5 (matching persistido) --
    def ejecutar_paso5(self) -> None:
        """Corre el Paso 5 y deja la corrida GUARDADA en `job_match`.

        Es la misma corrida que escribe `run_paso5.py`: una corrida NUEVA
        (las anteriores quedan con `valida = 0`). Al terminar, la columna
        "Paso 5" de la tabla se puebla con los estados de esa corrida.
        """
        if self._corriendo_paso5:
            self._pintar_progreso("Ya hay un Paso 5 en marcha…")
            return
        # GUARDA (O12 · Ola 1.3): si hay avisos con análisis obsoleto, el
        # Paso 5 los evaluaría con requisitos VIEJOS (las skills/idiomas que
        # produjo la IA todavía no son requisitos) y saldrían "sin_requisitos".
        reanalizar = self._guarda_analisis_obsoleto()
        if reanalizar is None:
            return  # el usuario canceló
        evaluar_todo = bool(self._widgets["evaluar_todo"].get())
        self._corriendo_paso5 = True
        self._widgets["paso5"].configure(state="disabled")
        self._pintar_progreso("Paso 5: evaluando requisitos contra el perfil…")
        self._widgets["badge"].set_text("Paso 5")
        self._widgets["badge"].set_tone("warning")

        def trabajo() -> None:
            try:
                if reanalizar:
                    self._programar(
                        lambda: self._pintar_progreso(
                            "Re-analizando avisos con campos obsoletos…"
                        )
                    )
                    from jobpulse_v15.analysis_flow import reananalizar_con_campos_fuente

                    stats = reananalizar_con_campos_fuente(
                        self.context.repository,
                        on_progress=lambda texto: self._programar(
                            lambda t=texto: self._pintar_progreso(str(t))
                        ),
                    )
                    self._programar(
                        lambda: self._pintar_progreso(
                            "Re-analisis: {} aviso(s) actualizado(s).".format(
                                stats.get("reanalizados", 0)
                            )
                        )
                    )
                resumen = self.paso5.ejecutar(
                    aplicar_filtro_areas=not evaluar_todo,
                    progreso=lambda texto: self._programar(
                        lambda t=texto: self._pintar_progreso(str(t))),
                )
            except Exception as error:  # pragma: no cover - defensivo
                mensaje = str(error)
                self._programar(lambda: self._error_paso5(mensaje))
                return
            self._programar(lambda: self._fin_paso5(resumen))

        self._lanzar_hilo(trabajo)

    def _guarda_analisis_obsoleto(self) -> bool | None:
        """Pregunta qué hacer si hay análisis obsoletos (O12 · Ola 1.3).

        Devuelve ``True`` (re-analizar y seguir), ``False`` (seguir con los
        análisis actuales) o ``None`` (cancelar). Sin aviso previo, el
        matching daba números que no cuadraban con la CLI (231 avisos
        ``sin_requisitos`` frente a 11).
        """
        try:
            obsoletos = self.paso5.analisis_obsoletos()
        except Exception:  # pragma: no cover - defensivo
            return False
        if not obsoletos:
            return False
        respuesta = messagebox.askyesnocancel(
            t("Paso 5"),
            t(
                "Hay {} aviso(s) con análisis obsoleto: la IA ya llenó sus "
                "skills/idiomas, pero el análisis no los integró (así quedan "
                "«sin requisitos» en el matching).\n\n"
                "¿Re-analizarlos ahora antes de evaluar?"
            ).format(obsoletos),
        )
        if respuesta is None:
            return None
        if not respuesta:
            messagebox.showwarning(
                t("Paso 5"),
                t(
                    "Se evaluará con los análisis actuales: esos avisos pueden "
                    "salir «sin_requisitos» aunque el perfil sí califique."
                ),
            )
        return bool(respuesta)

    def _error_paso5(self, mensaje: str) -> None:
        self._corriendo_paso5 = False
        boton = self._widgets.get("paso5")
        if boton is not None:
            boton.configure(state="normal")
        self._widgets["estado"].configure(text=t("Error en el Paso 5: {}").format(mensaje))
        self._widgets["badge"].set_text(t("Error"))
        self._widgets["badge"].set_tone("danger")
        messagebox.showerror(t("Paso 5"), t("No se pudo correr el matching:\n{}").format(mensaje))

    def _fin_paso5(self, resumen: ResumenPaso5) -> None:
        self._corriendo_paso5 = False
        boton = self._widgets.get("paso5")
        if boton is not None:
            boton.configure(state="normal")
        # La columna "Paso 5" se puebla sola con la corrida recién guardada.
        self._actualizar_estados_paso5()
        self._pintar_tabla()
        if self.detalle is not None:
            self._pintar_detalle(self.detalle)
        por_estado = resumen.por_estado
        detalle = " · ".join(f"{estado}: {n}" for estado, n in
                             sorted(por_estado.items())) or "sin evaluables"
        self._widgets["estado"].configure(
            text=t("Paso 5 · corrida {} · {} evaluada(s) · {}").format(
                resumen.corrida_id, resumen.evaluadas, detalle)
            + self._texto_evidencia()
        )
        self._widgets["badge"].set_text(t("Paso 5 listo"))
        self._widgets["badge"].set_tone("success")
        self._pintar_badge_obsoleto()
        messagebox.showinfo(
            t("Paso 5"),
            t("Corrida {} guardada.\n{} vacante(s) evaluada(s).\n\n{}").format(
                resumen.corrida_id, resumen.evaluadas, resumen.texto()),
        )

    # -- evidencia (O12 · Ola 1.4) --
    def _texto_evidencia(self) -> str:
        """Sufijo "· evidencia al día / desactualizada" para la línea de estado."""
        try:
            from jobpulse_v15 import evidencia

            db = self.context.repository.database.path
            estado = evidencia.estado_evidencia(
                db_path=db, docs_dir=evidencia.docs_dir_para(db)
            )
        except Exception:  # pragma: no cover - defensivo
            return ""
        if estado.get("al_dia"):
            return " · evidencia al día"
        return " · evidencia: %s" % estado.get("motivo", "desactualizada")

    def generar_evidencia(self) -> None:
        """Genera y verifica la evidencia de la corrida vigente, sin subprocess."""
        if self._generando_evidencia:
            return
        self._generando_evidencia = True
        boton = self._widgets.get("evidencia")
        if boton is not None:
            boton.configure(state="disabled")
        self._pintar_progreso("Evidencia: generando el documento de la corrida vigente…")

        def trabajo() -> None:
            try:
                from jobpulse_v15 import evidencia

                db = self.context.repository.database.path
                docs = evidencia.docs_dir_para(db)
                generado = evidencia.generar_evidencia(
                    db_path=db, docs_dir=docs, log=lambda _t: None
                )
                verificado = evidencia.verificar_evidencia(
                    db_path=db, docs_dir=docs, log=lambda _t: None
                )
            except Exception as error:  # pragma: no cover - defensivo
                mensaje = str(error)
                self._programar(lambda: self._error_evidencia(mensaje))
                return
            self._programar(lambda: self._fin_evidencia(generado, verificado))

        self._lanzar_hilo(trabajo)

    def _fin_evidencia(self, generado: dict, verificado: dict) -> None:
        self._generando_evidencia = False
        boton = self._widgets.get("evidencia")
        if boton is not None:
            boton.configure(state="normal")
        self._pintar_estado()
        if verificado.get("ok"):
            self._widgets["badge"].set_text(t("Evidencia OK"))
            self._widgets["badge"].set_tone("success")
            messagebox.showinfo(
                t("Evidencia"),
                t("Generada {} ({}) y verificada: {} con frase literal.").format(
                    generado.get("ruta"), generado.get("corrida"),
                    verificado.get("verificaciones", 0),
                ),
            )
        else:
            self._widgets["badge"].set_text(t("Evidencia con fallos"))
            self._widgets["badge"].set_tone("danger")
            messagebox.showwarning(
                t("Evidencia"),
                t("Generada {}, pero la verificación tiene {} discrepancia(s):\n\n{}").format(
                    generado.get("ruta"),
                    len(verificado.get("fallos") or []),
                    "\n".join((verificado.get("fallos") or [])[:10]),
                ),
            )

    def _error_evidencia(self, mensaje: str) -> None:
        self._generando_evidencia = False
        boton = self._widgets.get("evidencia")
        if boton is not None:
            boton.configure(state="normal")
        self._widgets["badge"].set_text(t("Error"))
        self._widgets["badge"].set_tone("danger")
        messagebox.showerror(
            t("Evidencia"), t("No se pudo generar la evidencia:\n{}").format(mensaje)
        )

    def _actualizar_estados_paso5(self) -> None:
        """Pega en las filas los estados del Paso 5 de la corrida vigente."""
        try:
            estados = self.store.estados_paso5()
        except Exception:  # pragma: no cover - defensivo
            return
        self.filas = [
            replace(fila, estado_paso5=estados.get(fila.job_id, ""))
            for fila in self.filas
        ]
        if self.detalle is not None:
            self.detalle = replace(
                self.detalle,
                estado_paso5=estados.get(self.detalle.job_id, ""),
            )

    def exportar(self) -> None:
        filas = self._filas_visibles()
        if not filas:
            messagebox.showinfo(t("Exportar CSV"), t("No hay vacantes en la vista para exportar."))
            return
        dir_csv = configuracion.directorio_csv()
        ruta = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Todos los archivos", "*.*")],
            initialfile="vacantes_ranking_ats.csv",
            **({"initialdir": dir_csv} if dir_csv else {}),
        )
        if not ruta:
            return
        try:
            total = exportar_csv(filas, ruta)
        except OSError as error:
            messagebox.showerror(t("Exportar CSV"), t("No se pudo escribir el archivo:\n{}").format(error))
            return
        messagebox.showinfo(t("Exportar CSV"), t("Se exportaron {} vacante(s).").format(total))


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
