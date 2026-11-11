# -*- coding: utf-8 -*-
"""Pestaña "Perfil": datos del candidato (importar CV + alta manual).

Dos formas de llenar el perfil, en la misma pantalla:
1. **Importar CV…** — lee un PDF/DOCX/TXT local, propone datos y abre un
   diálogo de revisión donde el usuario elige cuáles guardar.
2. **Alta/edición manual** — el formulario de la derecha crea o actualiza
   un dato identificado por (categoría, código).

La pestaña NO toca SQLite: usa :class:`ProfileStore`.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from jobpulse_v15.ui_v2 import configuracion
from jobpulse_v15.ui_v2.data.profile import (
    CATEGORIAS,
    CATEGORIAS_CON_ESTADO,
    CATEGORIAS_CON_NUMERO,
    ESTADOS_EDUCACION,
    ProfileFact,
    ProfileQuery,
    ProfileStore,
    etiqueta_categoria,
    etiqueta_estado_educacion,
    exportar_csv,
    recortar,
)
from jobpulse_v15.ui_v2.dialogs import RevisionImportacionDialog
from jobpulse_v15.ui_v2.tabs.base import BaseTab
from jobpulse_v15.ui_v2.widgets import (
    Badge,
    Card,
    EmptyState,
    FlatButton,
    ScrollFrame,
    SearchField,
    SectionTitle,
    StatTile,
)
from jobpulse_v15.ui_v2.i18n import t

COLUMNAS = ("categoria", "codigo", "valor", "nivel", "origen", "canonico")
TITULOS = {
    "categoria": "Categoría",
    "codigo": "Código",
    "valor": "Valor",
    "nivel": "Nivel / detalle",
    "origen": "Origen",
    "canonico": "Canónico",
}
ANCHOS = {
    "categoria": 130,
    "codigo": 150,
    "valor": 260,
    "nivel": 130,
    "origen": 90,
    "canonico": 110,
}
SIN_CATEGORIA = "Todas las categorías"


class PerfilTab(BaseTab):
    """Datos del candidato: importar desde CV y alta manual."""

    key = "perfil"
    title = "Perfil"
    subtitle = "Datos del candidato que alimentan la evaluación"
    icon = "◉"

    def __init__(self, context) -> None:
        super().__init__(context)
        self.store: ProfileStore = context.services.setdefault(
            "profile_store", ProfileStore(context.repository)
        )
        self.hechos: list[ProfileFact] = []
        self._widgets: dict[str, Any] = {}
        self._editando_id: int | None = None
        self._raiz: tk.Misc | None = None

    # -- construcción --
    def build(self, parent: tk.Misc) -> tk.Frame:
        marco = super().build(parent)
        self._raiz = marco.winfo_toplevel()
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
        barra.grid(row=0, column=0, sticky="ew", padx=theme.metrics.pad,
                   pady=(theme.metrics.pad, 8))
        barra.columnconfigure(2, weight=1)

        FlatButton(barra, theme, "Importar CV…", command=self.importar_cv,
                   variant="accent").grid(row=0, column=0)
        self._widgets["revertir"] = FlatButton(
            barra, theme, "Revertir importación", command=self.revertir_importacion,
            variant="flat",
        )
        self._widgets["revertir"].grid(row=0, column=1, padx=(8, 0))

        FlatButton(barra, theme, "Exportar CSV", command=self.exportar,
                   variant="flat").grid(row=0, column=3, padx=(8, 0))
        FlatButton(barra, theme, "Actualizar", command=self.refresh,
                   variant="flat").grid(row=0, column=4, padx=(8, 0))

    def _build_resumen(self, parent: tk.Misc) -> None:
        theme = self.theme
        franja = tk.Frame(parent, bg=theme.color("bg"))
        franja.grid(row=1, column=0, sticky="ew", padx=theme.metrics.pad, pady=(0, 10))
        for indice in range(5):
            franja.columnconfigure(indice, weight=1, uniform="tiles")

        definiciones = (
            ("total", "Datos registrados"),
            ("categorias", "Categorías cubiertas"),
            ("importados", "De CV (importados)"),
            ("manuales", "Manuales"),
            ("areas", "Áreas de empleo"),
        )
        self._tiles: dict[str, StatTile] = {}
        for indice, (clave, etiqueta) in enumerate(definiciones):
            tarjeta = Card(franja, theme, padding=14)
            tarjeta.grid(row=0, column=indice, sticky="nsew",
                         padx=(0 if indice == 0 else 6, 6))
            tile = StatTile(tarjeta.body, theme, etiqueta)
            tile.pack(fill="both", expand=True)
            self._tiles[clave] = tile

    def _build_cuerpo(self, parent: tk.Misc) -> None:
        theme = self.theme
        cuerpo = tk.Frame(parent, bg=theme.color("bg"))
        cuerpo.grid(row=2, column=0, sticky="nsew", padx=theme.metrics.pad)
        cuerpo.columnconfigure(0, weight=1)
        cuerpo.rowconfigure(0, weight=1)
        self._build_tabla(cuerpo)
        self._build_formulario(cuerpo)

    def _build_tabla(self, parent: tk.Misc) -> None:
        theme = self.theme
        tarjeta = Card(parent, theme, padding=12)
        tarjeta.grid(row=0, column=0, sticky="nsew")
        cuerpo = tarjeta.body
        cuerpo.columnconfigure(0, weight=1)
        cuerpo.rowconfigure(1, weight=1)

        filtros = tk.Frame(cuerpo, bg=theme.color("surface"))
        filtros.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        filtros.columnconfigure(0, weight=1)
        self._widgets["buscador"] = SearchField(
            filtros, theme, placeholder=t("Buscar por valor o código…"),
            on_change=lambda _t: self.refresh(),
        )
        self._widgets["buscador"].grid(row=0, column=0, sticky="ew")

        combo = ttk.Combobox(
            filtros,
            values=[SIN_CATEGORIA] + [etiqueta_categoria(c) for c in CATEGORIAS],
            state="readonly", width=22, font=theme.font(9),
        )
        combo.current(0)
        combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        combo.grid(row=0, column=1, sticky="e", padx=(10, 0))
        self._widgets["filtro_categoria"] = combo

        marco_tabla = tk.Frame(cuerpo, bg=theme.color("surface"))
        marco_tabla.grid(row=1, column=0, sticky="nsew")
        marco_tabla.columnconfigure(0, weight=1)
        marco_tabla.rowconfigure(0, weight=1)

        tabla = ttk.Treeview(
            marco_tabla, columns=list(COLUMNAS), show="headings",
            selectmode="browse", style="Flat.Treeview",
        )
        for columna in COLUMNAS:
            tabla.heading(columna, text=TITULOS[columna])
            tabla.column(columna, width=ANCHOS[columna], anchor="w",
                         stretch=(columna == "valor"))
        tabla.grid(row=0, column=0, sticky="nsew")
        barra_y = ttk.Scrollbar(marco_tabla, orient="vertical", command=tabla.yview,
                                style="Flat.Vertical.TScrollbar")
        barra_y.grid(row=0, column=1, sticky="ns")
        barra_x = ttk.Scrollbar(marco_tabla, orient="horizontal", command=tabla.xview,
                                style="Flat.Horizontal.TScrollbar")
        barra_x.grid(row=1, column=0, sticky="ew")
        tabla.configure(yscrollcommand=barra_y.set, xscrollcommand=barra_x.set)
        tabla.bind("<<TreeviewSelect>>", self._on_seleccion)
        self._widgets["tabla"] = tabla

        self._widgets["vacio"] = EmptyState(
            marco_tabla, theme, "Sin datos de perfil",
            "Importa un CV o registra el primer dato con el formulario.",
        )
        self._widgets["vacio"].grid(row=0, column=0, columnspan=2, sticky="nsew")
        self._widgets["vacio"].grid_remove()

    def _build_formulario(self, parent: tk.Misc) -> None:
        theme = self.theme
        parent.columnconfigure(1, weight=0, minsize=theme.metrics.detail_width)
        tarjeta = Card(parent, theme, padding=0)
        tarjeta.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        scroll = ScrollFrame(tarjeta.body, theme)
        scroll.pack(fill="both", expand=True)
        self._widgets["form_scroll"] = scroll
        form = scroll.inner

        encabezado = tk.Frame(form, bg=theme.color("surface"))
        encabezado.pack(fill="x", pady=(4, 8))
        self._widgets["form_titulo"] = tk.Label(
            encabezado, text=t("Nuevo dato de perfil"), bg=theme.color("surface"),
            fg=theme.color("text"), font=theme.font(12, "bold"), anchor="w",
        )
        self._widgets["form_titulo"].pack(anchor="w")

        SectionTitle(form, theme, "Identificación").pack(fill="x", pady=(6, 6))
        self._widgets["categoria"] = self._combo(
            form, "Categoría", [etiqueta_categoria(c) for c in CATEGORIAS],
        )
        self._widgets["codigo"] = self._entrada(form, "Código (clave única)")
        self._widgets["valor"] = self._entrada(form, "Valor (texto a mostrar)")

        SectionTitle(form, theme, "Detalle").pack(fill="x", pady=(14, 6))
        self._widgets["qualifier"] = self._entrada(
            form,
            "Nivel / calificador",
            pista=(
                "Educación en curso: escribe aquí el avance, p. ej. "
                "'80 % de créditos completados' (el motor exige el 80 %+ "
                "para el escalón 'estudiante avanzado')"
            ),
        )
        self._widgets["estado_educacion"] = self._combo(
            form, "Estado de educación",
            [etiqueta_estado_educacion(e) for e in ESTADOS_EDUCACION],
        )
        self._widgets["numerico"] = self._entrada(form, "Cantidad (solo experiencia)")
        self._widgets["unidad"] = self._entrada(form, "Unidad (p. ej. years)")

        SectionTitle(form, theme, "Notas").pack(fill="x", pady=(14, 6))
        contenedor = tk.Frame(form, bg=theme.color("surface_alt"),
                              highlightbackground=theme.color("border"),
                              highlightthickness=1)
        contenedor.pack(fill="x")
        notas = tk.Text(
            contenedor, height=4, wrap="word", bd=0, relief="flat",
            bg=theme.color("surface_alt"), fg=theme.color("text"),
            font=theme.font(9), padx=8, pady=6,
        )
        notas.pack(fill="both", expand=True)
        self._widgets["notas"] = notas

        self._widgets["canonico"] = tk.Label(
            form, text="", bg=theme.color("surface"), fg=theme.color("text_faint"),
            font=theme.font(8), anchor="w", wraplength=280, justify="left",
        )
        self._widgets["canonico"].pack(fill="x", pady=(12, 0))

        acciones = tk.Frame(form, bg=theme.color("surface"))
        acciones.pack(fill="x", pady=(14, 6))
        FlatButton(acciones, theme, "Guardar dato", command=self.guardar,
                   variant="accent").pack(side="left")
        FlatButton(acciones, theme, "Eliminar", command=self.eliminar,
                   variant="flat").pack(side="left", padx=(8, 0))
        FlatButton(acciones, theme, "Limpiar", command=self.limpiar_formulario,
                   variant="ghost").pack(side="left", padx=(8, 0))

        self._widgets["categoria"].bind("<<ComboboxSelected>>", self._on_categoria)
        self._aplicar_categoria()

    def _entrada(
        self,
        parent: tk.Misc,
        etiqueta: str,
        pista: str = "",
    ) -> ttk.Entry:
        theme = self.theme
        marco = tk.Frame(parent, bg=theme.color("surface"))
        marco.pack(fill="x", pady=(0, 8))
        tk.Label(
            marco, text=etiqueta, bg=theme.color("surface"),
            fg=theme.color("text_faint"), font=theme.font(8, "bold"), anchor="w",
        ).pack(anchor="w", pady=(0, 2))
        entrada = ttk.Entry(marco, font=theme.font(9))
        entrada.pack(fill="x")
        if pista:
            tk.Label(
                marco, text=pista, bg=theme.color("surface"),
                fg=theme.color("text_faint"), font=theme.font(7), anchor="w",
                wraplength=280, justify="left",
            ).pack(anchor="w", pady=(2, 0))
        return entrada

    def _combo(self, parent: tk.Misc, etiqueta: str, valores: list[str]) -> ttk.Combobox:
        theme = self.theme
        marco = tk.Frame(parent, bg=theme.color("surface"))
        marco.pack(fill="x", pady=(0, 8))
        tk.Label(
            marco, text=etiqueta, bg=theme.color("surface"),
            fg=theme.color("text_faint"), font=theme.font(8, "bold"), anchor="w",
        ).pack(anchor="w", pady=(0, 2))
        combo = ttk.Combobox(marco, values=valores, state="readonly",
                             font=theme.font(9))
        combo.pack(fill="x")
        return combo

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

    # -- categoría del formulario --
    def _categoria_actual(self) -> str:
        combo = self._widgets["categoria"]
        indice = combo.current()
        return CATEGORIAS[indice] if 0 <= indice < len(CATEGORIAS) else CATEGORIAS[0]

    def _on_categoria(self, _event=None) -> None:
        self._aplicar_categoria()

    def _aplicar_categoria(self) -> None:
        categoria = self._categoria_actual()
        self._habilitar(
            self._widgets["estado_educacion"], categoria in CATEGORIAS_CON_ESTADO
        )
        self._habilitar(self._widgets["numerico"], categoria in CATEGORIAS_CON_NUMERO)
        self._habilitar(self._widgets["unidad"], categoria in CATEGORIAS_CON_NUMERO)

    @staticmethod
    def _habilitar(widget: ttk.Widget, activo: bool) -> None:
        if isinstance(widget, ttk.Combobox):
            widget.configure(state="readonly" if activo else "disabled")
        else:
            widget.configure(state="normal" if activo else "disabled")

    # -- datos --
    def _query(self) -> ProfileQuery:
        combo = self._widgets.get("filtro_categoria")
        categoria = ""
        if combo is not None and combo.current() > 0:
            categoria = CATEGORIAS[combo.current() - 1]
        buscador = self._widgets.get("buscador")
        return ProfileQuery(
            texto=buscador.value() if buscador is not None else "",
            categoria=categoria,
        )

    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        self.hechos = self.store.load(self._query())
        self._pintar_tabla()
        self._pintar_resumen()
        self._pintar_estado()

    def _pintar_tabla(self) -> None:
        tabla = self._widgets["tabla"]
        seleccion = self._editando_id
        tabla.delete(*tabla.get_children())
        for hecho in self.hechos:
            tabla.insert(
                "", "end", iid=str(hecho.fact_id),
                values=(
                    hecho.categoria_legible,
                    hecho.value_code,
                    recortar(hecho.value_text, 48),
                    recortar(hecho.nivel_legible, 24),
                    hecho.origen_legible,
                    hecho.codigo_canonico or "—",
                ),
            )
        vacio = self._widgets["vacio"]
        if self.hechos:
            vacio.grid_remove()
        else:
            vacio.grid()
        if seleccion is not None and str(seleccion) in tabla.get_children():
            tabla.selection_set(str(seleccion))

    def _pintar_resumen(self) -> None:
        resumen = self.store.resumen(self.hechos)
        self._tiles["total"].update_values(str(resumen.total))
        self._tiles["categorias"].update_values(str(resumen.categorias_cubiertas))
        self._tiles["importados"].update_values(str(resumen.importados))
        self._tiles["manuales"].update_values(str(resumen.manuales))
        self._tiles["areas"].update_values(str(resumen.por_categoria.get("area", 0)))

    def _pintar_estado(self) -> None:
        total = len(self.hechos)
        importaciones = self.store.importaciones(limit=50)
        self._widgets["estado"].configure(
            text=f"{total} dato(s) en la vista · {len(importaciones)} importación(es) registrada(s)"
        )
        badge = self._widgets["badge"]
        if total:
            badge.set_text(t("Con perfil"))
            badge.set_tone("success")
        else:
            badge.set_text(t("Sin datos"))
            badge.set_tone("warning")
        self._widgets["revertir"].configure(
            state="normal" if importaciones else "disabled"
        )

    # -- formulario --
    def _on_seleccion(self, _event=None) -> None:
        seleccion = self._widgets["tabla"].selection()
        if not seleccion:
            return
        fact_id = int(seleccion[0])
        hecho = next((h for h in self.hechos if h.fact_id == fact_id), None)
        if hecho is None:
            return
        self._cargar_en_formulario(hecho)

    def _cargar_en_formulario(self, hecho: ProfileFact) -> None:
        self._editando_id = hecho.fact_id
        self._widgets["form_titulo"].configure(text=t("Editar dato de perfil"))
        combo = self._widgets["categoria"]
        combo.current(CATEGORIAS.index(hecho.category) if hecho.category in CATEGORIAS else 0)
        self._set_entry("codigo", hecho.value_code)
        self._set_entry("valor", hecho.value_text)
        self._set_entry("qualifier", hecho.qualifier)
        self._widgets["estado_educacion"].current(
            ESTADOS_EDUCACION.index(hecho.education_status)
            if hecho.education_status in ESTADOS_EDUCACION else 0
        )
        self._set_entry("numerico",
                        "" if hecho.numeric_value is None else f"{hecho.numeric_value:g}")
        self._set_entry("unidad", hecho.unit)
        self._set_texto("notas", hecho.notes)
        self._widgets["canonico"].configure(
            text=(
                f"Origen: {hecho.origen_legible}"
                + (f" · importado de {hecho.import_source_name}"
                   if hecho.import_source_name else "")
                + f"\nCódigo canónico: {hecho.codigo_canonico or 'no resuelto'}"
            )
        )
        self._aplicar_categoria()

    def _set_entry(self, clave: str, valor: str) -> None:
        entrada = self._widgets[clave]
        entrada.configure(state="normal")
        entrada.delete(0, "end")
        entrada.insert(0, valor or "")

    def _get_entry(self, clave: str) -> str:
        return self._widgets[clave].get().strip()

    def _set_texto(self, clave: str, valor: str) -> None:
        widget = self._widgets[clave]
        widget.delete("1.0", "end")
        widget.insert("1.0", valor or "")

    def _get_texto(self, clave: str) -> str:
        return self._widgets[clave].get("1.0", "end").strip()

    def limpiar_formulario(self) -> None:
        self._editando_id = None
        self._widgets["form_titulo"].configure(text=t("Nuevo dato de perfil"))
        self._widgets["categoria"].current(0)
        for clave in ("codigo", "valor", "qualifier", "numerico", "unidad"):
            self._set_entry(clave, "")
        self._widgets["estado_educacion"].current(0)
        self._set_texto("notas", "")
        self._widgets["canonico"].configure(text="")
        tabla = self._widgets["tabla"]
        tabla.selection_remove(*tabla.selection())
        self._widgets["form_scroll"].scroll_to_top()
        self._aplicar_categoria()

    def guardar(self) -> None:
        categoria = self._categoria_actual()
        codigo = self._get_entry("codigo")
        valor = self._get_entry("valor")
        if not codigo or not valor:
            messagebox.showinfo(
                t("Dato de perfil"),
                t("El código y el valor son obligatorios."),
                parent=self._toplevel(),
            )
            return
        try:
            self.store.save(
                categoria,
                codigo,
                valor,
                qualifier=self._get_entry("qualifier"),
                education_status=(
                    ESTADOS_EDUCACION[self._widgets["estado_educacion"].current()]
                    if categoria in CATEGORIAS_CON_ESTADO else ""
                ),
                numeric_value=(
                    self._get_entry("numerico") or None
                    if categoria in CATEGORIAS_CON_NUMERO else None
                ),
                unit=self._get_entry("unidad") if categoria in CATEGORIAS_CON_NUMERO else "",
                notes=self._get_texto("notas"),
                fact_id_viejo=self._editando_id,
            )
        except ValueError as error:
            messagebox.showerror(t("Dato de perfil"), str(error), parent=self._toplevel())
            return
        self.refresh()
        self.limpiar_formulario()
        messagebox.showinfo(t("Dato de perfil"), t("Dato guardado."),
                            parent=self._toplevel())

    def eliminar(self) -> None:
        if self._editando_id is None:
            messagebox.showinfo(t("Dato de perfil"),
                                t("Selecciona un dato de la lista para eliminarlo."),
                                parent=self._toplevel())
            return
        hecho = next((h for h in self.hechos if h.fact_id == self._editando_id), None)
        etiqueta = f"{hecho.categoria_legible} · {hecho.value_text}" if hecho else "el dato"
        if not messagebox.askyesno(
            t("Eliminar dato"), f"¿Eliminar {etiqueta}?", parent=self._toplevel()
        ):
            return
        if self.store.delete(self._editando_id):
            self.refresh()
            self.limpiar_formulario()

    # -- importación --
    def importar_cv(self) -> None:
        ruta = filedialog.askopenfilename(
            title=t("Seleccionar CV"),
            filetypes=[("CV (PDF, DOCX, TXT)", "*.pdf *.docx *.txt"),
                       ("Todos los archivos", "*.*")],
            parent=self._toplevel(),
        )
        if not ruta:
            return
        try:
            importacion = self.store.import_from_cv(ruta)
        except ValueError as error:
            messagebox.showerror("Importar CV", str(error), parent=self._toplevel())
            return
        except Exception as error:  # pragma: no cover - dependencia de archivo
            messagebox.showerror(t("Importar CV"),
                                 t("No se pudo procesar el CV:\n{}").format(error),
                                 parent=self._toplevel())
            return

        seleccionados = RevisionImportacionDialog.mostrar(self._toplevel(), self.theme, importacion)
        if not seleccionados:
            return
        try:
            total = self.store.import_facts(importacion.source_name, seleccionados)
        except ValueError as error:
            messagebox.showerror(t("Importar CV"), str(error), parent=self._toplevel())
            return
        self.refresh()
        messagebox.showinfo(
            t("Importar CV"),
            t("Se importaron {} dato(s) desde {}.\nPuedes revertir la importación con el botón del mismo nombre.").format(
                total, importacion.source_name),
            parent=self._toplevel(),
        )

    def revertir_importacion(self) -> None:
        importaciones = self.store.importaciones(limit=1)
        if not importaciones:
            return
        ultima = importaciones[0]
        if not messagebox.askyesno(
            t("Revertir importación"),
            t("¿Revertir la importación de {} ({})? Se conservan tus ediciones manuales.").format(
                ultima['source_name'], ultima['imported_at']),
            parent=self._toplevel(),
        ):
            return
        resultado = self.store.revertir_ultima()
        self.refresh()
        if resultado:
            messagebox.showinfo(
                t("Revertir importación"),
                t("Restaurados: {} · Eliminados: {} · Manuales conservados: {}").format(
                    resultado['restored'], resultado['removed'], resultado['preserved_manual']),
                parent=self._toplevel(),
            )

    def exportar(self) -> None:
        if not self.hechos:
            messagebox.showinfo(t("Exportar perfil"), t("No hay datos en la vista."),
                                parent=self._toplevel())
            return
        dir_csv = configuracion.directorio_csv()
        ruta = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Todos los archivos", "*.*")],
            initialfile="perfil_candidato.csv",
            parent=self._toplevel(),
            **({"initialdir": dir_csv} if dir_csv else {}),
        )
        if not ruta:
            return
        try:
            total = exportar_csv(self.hechos, ruta)
        except OSError as error:
            messagebox.showerror(t("Exportar perfil"),
                                 t("No se pudo escribir el archivo:\n{}").format(error),
                                 parent=self._toplevel())
            return
        messagebox.showinfo(t("Exportar perfil"), t("Se exportaron {} dato(s).").format(total),
                            parent=self._toplevel())

    def _toplevel(self) -> tk.Misc:
        """Ventana raíz, para que los diálogos se anclen bien."""
        if self._raiz is not None:
            return self._raiz
        return self.frame.winfo_toplevel() if self.frame is not None else self.context.theme.styles.master
