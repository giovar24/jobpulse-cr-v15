# -*- coding: utf-8 -*-
"""Pestaña "Datos crudos": el navegador de los registros tal como están.

Muestra cada aviso con sus valores ORIGINALES de la fuente (ubicación
cruda, salario crudo, texto de descripción y de requisitos) para poder
auditar la extracción sin interpretarla.
"""
from __future__ import annotations

import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk
from typing import Any

from jobpulse_v15.ui_v2 import configuracion
from jobpulse_v15.ui_v2.data.jobs import (
    JobsStore,
    RawDetail,
    RawQuery,
    RawRow,
    exportar_csv,
    idioma_texto,
    recortar,
    resumen_por_campo,
    salario_texto,
    ubicacion_texto,
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
    "fecha",
    "titulo",
    "empresa",
    "ubicacion",
    "idioma",
    "salario",
    "fuente",
    "chars",
)

TITULOS = {
    "fecha": "Fecha",
    "titulo": "Título",
    "empresa": "Empresa",
    "ubicacion": "Ubicación (cruda)",
    "idioma": "Idioma",
    "salario": "Salario",
    "fuente": "Fuente",
    "chars": "Desc.",
}

ANCHOS = {
    "fecha": 92,
    "titulo": 300,
    "empresa": 150,
    "ubicacion": 190,
    "idioma": 96,
    "salario": 150,
    "fuente": 120,
    "chars": 60,
}


class DatosCrudosTab(BaseTab):
    """Explorador de los datos crudos de los avisos."""

    key = "crudos"
    title = "Datos crudos"
    subtitle = "Cada aviso con los valores originales de la fuente"
    icon = "▤"

    def __init__(self, context) -> None:
        super().__init__(context)
        self.store: JobsStore = context.services.setdefault("jobs_store", JobsStore(context.repository))
        self.filas: list[RawRow] = []
        self.detalle: RawDetail | None = None
        self._plataformas: list[str] = []
        self._widgets: dict[str, Any] = {}

    # -- construcción --
    def build(self, parent: tk.Misc) -> tk.Frame:
        marco = super().build(parent)
        theme = self.theme
        marco.columnconfigure(0, weight=1)
        marco.rowconfigure(2, weight=1)

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
            barra, theme, placeholder=t("Buscar por título, empresa o texto…"),
            on_change=lambda _t: self.refresh(),
        )
        self._widgets["buscador"].grid(row=0, column=0, sticky="ew")

        self._plataformas = self.store.platforms()
        combo = ttk.Combobox(
            barra,
            values=["Todas las fuentes"] + self._plataformas,
            state="readonly",
            width=22,
            font=theme.font(9),
        )
        combo.current(0)
        combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        combo.grid(row=0, column=1, sticky="e", padx=(10, 0))
        self._widgets["plataforma"] = combo

        solo_desc = ttk.Checkbutton(
            barra, text=t("Solo con descripción completa"), variable=self._var_solo_desc(),
            command=self.refresh,
        )
        solo_desc.grid(row=0, column=2, padx=(12, 0))

        FlatButton(barra, theme, "Exportar CSV", command=self.exportar, variant="flat").grid(
            row=0, column=3, padx=(12, 0)
        )

    def _var_solo_desc(self) -> tk.BooleanVar:
        if "solo_desc" not in self._widgets:
            self._widgets["solo_desc"] = tk.BooleanVar(value=False)
        return self._widgets["solo_desc"]

    def _build_resumen(self, parent: tk.Misc) -> None:
        theme = self.theme
        franja = tk.Frame(parent, bg=theme.color("bg"))
        franja.grid(row=1, column=0, sticky="ew", padx=theme.metrics.pad, pady=(0, 10))
        for indice in range(5):
            franja.columnconfigure(indice, weight=1, uniform="tiles")

        definiciones = (
            ("total", "Avisos en vista"),
            ("descripcion", "Con descripción"),
            ("ubicacion", "Con ubicación"),
            ("salario", "Con salario"),
            ("fecha", "Con fecha"),
        )
        self._tiles = {}
        for indice, (clave, etiqueta) in enumerate(definiciones):
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

        # -- tabla --
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
        scroll = ttk.Scrollbar(marco_tabla, orient="vertical", command=self._widgets["tabla"].yview,
                               style="Flat.Vertical.TScrollbar")
        scroll.grid(row=0, column=1, sticky="ns")
        # Las columnas suman más que el ancho disponible: sin scrollbar
        # horizontal las últimas (idioma, salario, fuente) quedan inalcanzables.
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
            marco_tabla, theme, "Sin avisos",
            "Ajusta los filtros o ejecuta un barrido desde la UI principal.",
        )
        self._widgets["vacio"].grid(row=0, column=0, columnspan=2, sticky="nsew")
        self._widgets["vacio"].grid_remove()

        # -- detalle --
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
            parent, theme, "Ningún aviso seleccionado",
            "Elige una fila para ver sus datos crudos.",
        )
        self._widgets["detalle_vacio"].pack(fill="both", expand=True)

        self._widgets["detalle_cuerpo"] = tk.Frame(parent, bg=theme.color("surface"))

        def seccion(titulo: str) -> tk.Frame:
            marco = tk.Frame(self._widgets["detalle_cuerpo"], bg=theme.color("surface"))
            SectionTitle(marco, theme, titulo).pack(fill="x", pady=(16, 6))
            return marco

        self._widgets["kv"] = {}
        bloque_id = seccion("Identificación")
        for clave, etiqueta in (
            ("job_id", "Job ID"),
            ("titulo", "Título"),
            ("empresa", "Empresa"),
            ("fuente", "Fuente"),
        ):
            fila = KeyValue(bloque_id, theme, etiqueta, "—")
            fila.pack(fill="x", pady=2)
            self._widgets["kv"][clave] = fila

        bloque_ubi = seccion("Ubicación")
        for clave, etiqueta in (
            ("location_raw", "Original"),
            ("city", "Ciudad"),
            ("region", "Provincia"),
            ("country", "País"),
        ):
            fila = KeyValue(bloque_ubi, theme, etiqueta, "—")
            fila.pack(fill="x", pady=2)
            self._widgets["kv"][clave] = fila

        bloque_con = seccion("Condiciones")
        for clave, etiqueta in (
            ("work_mode", "Modalidad"),
            ("employment_type", "Tipo de empleo"),
            ("idioma", "Idioma del aviso"),
            ("fecha", "Publicada"),
            ("visto", "Visto por última vez"),
        ):
            fila = KeyValue(bloque_con, theme, etiqueta, "—")
            fila.pack(fill="x", pady=2)
            self._widgets["kv"][clave] = fila

        bloque_sal = seccion("Salario")
        for clave, etiqueta in (
            ("salary_raw", "Original"),
            ("salary_min", "Mínimo"),
            ("salary_max", "Máximo"),
            ("salary_period", "Periodo"),
        ):
            fila = KeyValue(bloque_sal, theme, etiqueta, "—")
            fila.pack(fill="x", pady=2)
            self._widgets["kv"][clave] = fila

        bloque_campos = seccion("Campos derivados")
        for clave, etiqueta in (
            ("skills", "Skills"),
            ("languages", "Idiomas"),
            ("estado", "Estado manual"),
            ("dup", "Duplicado de"),
        ):
            fila = KeyValue(bloque_campos, theme, etiqueta, "—")
            fila.pack(fill="x", pady=2)
            self._widgets["kv"][clave] = fila

        self._widgets["texto_requisitos"] = self._bloque_texto(
            self._widgets["detalle_cuerpo"], "Requisitos (texto crudo)", 9
        )
        self._widgets["texto_descripcion"] = self._bloque_texto(
            self._widgets["detalle_cuerpo"], "Descripción (texto crudo)", 12
        )

        self._widgets["fuentes"] = tk.Frame(self._widgets["detalle_cuerpo"], bg=theme.color("surface"))
        SectionTitle(self._widgets["fuentes"], theme, "Fuentes").pack(fill="x", pady=(16, 6))

        acciones = tk.Frame(self._widgets["detalle_cuerpo"], bg=theme.color("surface"))
        acciones.pack(fill="x", pady=(18, 6))
        self._widgets["abrir"] = FlatButton(
            acciones, theme, "Abrir aviso en el navegador", command=self._abrir_navegador,
            variant="flat",
        )
        self._widgets["abrir"].pack(side="left")

    def _bloque_texto(self, parent: tk.Misc, titulo: str, alto: int) -> tk.Text:
        theme = self.theme
        marco = tk.Frame(parent, bg=theme.color("surface"))
        marco.pack(fill="x", pady=(4, 4))
        SectionTitle(marco, theme, titulo).pack(fill="x", pady=(14, 6))
        contenedor = tk.Frame(marco, bg=theme.color("surface_alt"),
                              highlightbackground=theme.color("border"), highlightthickness=1)
        contenedor.pack(fill="x")
        texto = tk.Text(
            contenedor, height=alto, wrap="word", bd=0, relief="flat",
            bg=theme.color("surface_alt"), fg=theme.color("text"),
            font=theme.mono(9), padx=10, pady=8, state="disabled",
        )
        texto.pack(side="left", fill="both", expand=True)
        return texto

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
    def _query(self) -> RawQuery:
        combo = self._widgets.get("plataforma")
        plataforma = ""
        if combo is not None and combo.current() > 0:
            plataforma = self._plataformas[combo.current() - 1]
        buscador = self._widgets.get("buscador")
        return RawQuery(
            texto=buscador.value() if buscador is not None else "",
            plataforma=plataforma,
            solo_con_descripcion=bool(self._var_solo_desc().get()),
        )

    def on_show(self) -> None:
        """Carga los datos cada vez que la pestaña se hace visible."""
        self.refresh()

    def refresh(self) -> None:
        self.filas = self.store.load(self._query())
        self._pintar_tabla()
        self._pintar_resumen()
        self._pintar_estado()

    def _pintar_tabla(self) -> None:
        tabla = self._widgets["tabla"]
        tabla.delete(*tabla.get_children())
        for fila in self.filas:
            tabla.insert(
                "", "end", iid=fila.job_id,
                values=(
                    fila.date_published or "—",
                    fila.title or "—",
                    fila.company or "—",
                    recortar(ubicacion_texto(fila), 34),
                    idioma_texto(fila.posting_language),
                    recortar(salario_texto(fila), 22),
                    fila.platform or "—",
                    f"{fila.description_chars}",
                ),
            )
        vacio = self._widgets["vacio"]
        if self.filas:
            vacio.grid_remove()
        else:
            vacio.grid()

    def _pintar_resumen(self) -> None:
        resumen = resumen_por_campo(self.filas)
        if not resumen:
            return
        self._tiles["total"].update_values(str(resumen["total"]))
        self._tiles["descripcion"].update_values(
            str(resumen["con_descripcion"]),
            f"{_porcentaje(resumen['con_descripcion'], resumen['total'])} del total",
        )
        self._tiles["ubicacion"].update_values(
            str(resumen["con_ubicacion"]),
            f"{_porcentaje(resumen['con_ubicacion'], resumen['total'])} del total",
        )
        self._tiles["salario"].update_values(
            str(resumen["con_salario"]),
            f"{_porcentaje(resumen['con_salario'], resumen['total'])} del total",
        )
        self._tiles["fecha"].update_values(
            str(resumen["con_fecha"]),
            f"{_porcentaje(resumen['con_fecha'], resumen['total'])} del total",
        )

    def _pintar_estado(self) -> None:
        total = len(self.filas)
        self._widgets["estado"].configure(
            text=f"{total} aviso(s) en la vista · {self.store.sources_count()} sitio(s) configurado(s)"
        )
        badge = self._widgets["badge"]
        if total:
            badge.set_text(t("Con datos"))
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
        detalle = self.store.detail(job_id)
        if detalle is None:
            return
        self.detalle = detalle
        self._pintar_detalle(detalle)

    def _pintar_detalle(self, detalle: RawDetail) -> None:
        fila = detalle.row
        vacio = self._widgets["detalle_vacio"]
        cuerpo = self._widgets["detalle_cuerpo"]
        if vacio.winfo_ismapped():
            vacio.pack_forget()
        if not cuerpo.winfo_ismapped():
            cuerpo.pack(fill="both", expand=True)

        valores = {
            "job_id": fila.job_id,
            "titulo": fila.title or "—",
            "empresa": fila.company or "—",
            "fuente": f"{fila.platform or '—'} · {fila.site_id or '—'}",
            "location_raw": fila.location_raw or "—",
            "city": fila.city or "—",
            "region": fila.region or "—",
            "country": fila.country or "—",
            "work_mode": fila.work_mode or "unknown",
            "employment_type": fila.employment_type or "—",
            "idioma": idioma_texto(fila.posting_language),
            "fecha": fila.date_published or "—",
            "visto": fila.last_seen_at or "—",
            "salary_raw": fila.salary_raw or "—",
            "salary_min": _numero_texto(fila.salary_min),
            "salary_max": _numero_texto(fila.salary_max),
            "salary_period": fila.salary_period or "—",
            "skills": recortar(fila.skills, 120) or "—",
            "languages": recortar(fila.languages, 120) or "—",
            "estado": fila.user_status or "—",
            "dup": fila.dup_of or "—",
        }
        for clave, valor in valores.items():
            self._widgets["kv"][clave].set_value(valor)

        self._set_texto(self._widgets["texto_requisitos"], detalle.requirements_raw)
        self._set_texto(self._widgets["texto_descripcion"], detalle.description_raw)

        for hijo in self._widgets["fuentes"].winfo_children()[1:]:
            hijo.destroy()
        if detalle.sources:
            for fuente in detalle.sources:
                fila_fuente = KeyValue(
                    self._widgets["fuentes"], self.theme,
                    fuente.get("site_id") or "—",
                    texto_fuente(fuente),
                )
                fila_fuente.pack(fill="x", pady=2)
        else:
            tk.Label(
                self._widgets["fuentes"], text=t("Sin registros de fuente"),
                bg=self.theme.color("surface"), fg=self.theme.color("text_faint"),
                font=self.theme.font(9),
            ).pack(anchor="w")

        self._widgets["detalle"].scroll_to_top()

    def _set_texto(self, widget: tk.Text, contenido: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", contenido or "—")
        widget.configure(state="disabled")

    # -- acciones --
    def _abrir_navegador(self) -> None:
        if self.detalle and self.detalle.row.source_url:
            webbrowser.open(self.detalle.row.source_url)

    def exportar(self) -> None:
        if not self.filas:
            messagebox.showinfo(t("Exportar CSV"), t("No hay avisos en la vista para exportar."))
            return
        dir_csv = configuracion.directorio_csv()
        ruta = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Todos los archivos", "*.*")],
            initialfile="avisos_datos_crudos.csv",
            **({"initialdir": dir_csv} if dir_csv else {}),
        )
        if not ruta:
            return
        try:
            total = exportar_csv(self.filas, ruta)
        except OSError as error:
            messagebox.showerror(t("Exportar CSV"), t("No se pudo escribir el archivo:\n{}").format(error))
            return
        messagebox.showinfo(t("Exportar CSV"), t("Se exportaron {} aviso(s).").format(total))


def _porcentaje(parte: int, total: int) -> str:
    if not total:
        return "0 %"
    return f"{100 * parte / total:.0f} %"


def _numero_texto(valor: float | None) -> str:
    if valor is None:
        return "—"
    if float(valor).is_integer():
        return f"{int(valor):,}".replace(",", " ")
    return f"{valor:,.2f}".replace(",", " ").replace(".", ",")


def texto_fuente(fuente) -> str:
    """URL del registro de fuente (con el id del aviso en la fuente)."""
    url = fuente.get("source_url") or ""
    identificador = fuente.get("source_job_id") or ""
    if url and identificador:
        return f"{url}  [{identificador}]"
    return url or identificador or "—"
