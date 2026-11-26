# -*- coding: utf-8 -*-
"""Diálogos (Toplevel) reutilizables de la UI v2.

Los diálogos reciben `theme` y datos planos; no hablan con el repositorio.
Así una pestaña nueva puede reutilizarlos sin acoplarse.
"""
from __future__ import annotations

import tkinter as tk
from typing import Any, Mapping, Sequence

from jobpulse_v15.perfil_huecos import HuecosPerfil
from jobpulse_v15.ui_v2.data.profile import etiqueta_categoria, fact_desde_sugerencia
from jobpulse_v15.ui_v2.theme import Theme
from jobpulse_v15.ui_v2.widgets import FlatButton, ScrollFrame, SearchField, SectionTitle
from jobpulse_v15.ui_v2.i18n import t


class RevisionImportacionDialog(tk.Toplevel):
    """Revisión de los datos detectados en un CV: el usuario elige cuáles guardar.

    Uso::

        seleccionados = RevisionImportacionDialog.mostrar(parent, theme, importacion)
        if seleccionados is not None:
            store.import_facts(importacion.source_name, seleccionados)
    """

    def __init__(self, parent: tk.Misc, theme: Theme, importacion) -> None:
        super().__init__(parent)
        self.theme = theme
        self.importacion = importacion
        self.resultado: list[dict[str, Any]] | None = None
        self._variables: list[tuple[tk.BooleanVar, Any]] = []

        self.title(t("Revisar datos del CV"))
        self.configure(bg=theme.color("surface"))
        self.geometry("720x620")
        self.minsize(560, 420)
        self.transient(parent.winfo_toplevel())
        self._construir()
        self._centrar(parent)
        self.protocol("WM_DELETE_WINDOW", self._cancelar)

    # -- API de conveniencia --
    @classmethod
    def mostrar(cls, parent: tk.Misc, theme: Theme, importacion) -> list[dict[str, Any]] | None:
        dialogo = cls(parent, theme, importacion)
        dialogo.grab_set()
        dialogo.wait_window()
        return dialogo.resultado

    # -- construcción --
    def _construir(self) -> None:
        theme = self.theme
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        cabecera = tk.Frame(self, bg=theme.color("surface"))
        cabecera.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 8))
        tk.Label(
            cabecera, text=t("Datos detectados en el CV"), bg=theme.color("surface"),
            fg=theme.color("text"), font=theme.font(14, "bold"), anchor="w",
        ).pack(anchor="w")
        tk.Label(
            cabecera,
            text=f"Fuente: {self.importacion.source_name} · "
                 f"{len(self.importacion.suggestions)} dato(s) propuesto(s)",
            bg=theme.color("surface"), fg=theme.color("text_muted"),
            font=theme.font(9), anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        if self.importacion.warnings:
            avisos = tk.Frame(
                self, bg=theme.color("warning_soft"),
                highlightbackground=theme.color("warning"), highlightthickness=1,
            )
            avisos.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
            for advertencia in self.importacion.warnings:
                tk.Label(
                    avisos, text=f"• {advertencia}", bg=theme.color("warning_soft"),
                    fg=theme.color("warning"), font=theme.font(8),
                    wraplength=640, justify="left", anchor="w",
                ).pack(anchor="w", padx=10, pady=3)

        scroll = ScrollFrame(self, theme)
        scroll.grid(row=2, column=0, sticky="nsew", padx=20)
        if not self.importacion.suggestions:
            tk.Label(
                scroll.inner, text=t("No se detectaron datos compatibles."),
                bg=theme.color("surface"), fg=theme.color("text_muted"),
                font=theme.font(10),
            ).pack(pady=20)
        for sugerencia in self.importacion.suggestions:
            self._fila_sugerencia(scroll.inner, sugerencia)

        pie = tk.Frame(self, bg=theme.color("surface"))
        pie.grid(row=3, column=0, sticky="ew", padx=20, pady=16)
        FlatButton(pie, theme, "Seleccionar todo", command=lambda: self._marcar(True),
                   variant="ghost").pack(side="left")
        FlatButton(pie, theme, "Ninguno", command=lambda: self._marcar(False),
                   variant="ghost").pack(side="left", padx=(6, 0))
        FlatButton(pie, theme, "Cancelar", command=self._cancelar, variant="flat").pack(
            side="right"
        )
        FlatButton(pie, theme, "Importar seleccionados", command=self._aceptar,
                   variant="accent").pack(side="right", padx=(0, 8))

    def _fila_sugerencia(self, parent: tk.Misc, sugerencia) -> None:
        theme = self.theme
        marco = tk.Frame(
            parent, bg=theme.color("surface_alt"),
            highlightbackground=theme.color("border"), highlightthickness=1,
        )
        marco.pack(fill="x", pady=4)
        var = tk.BooleanVar(value=True)
        self._variables.append((var, sugerencia))
        tk.Checkbutton(
            marco, variable=var, bg=theme.color("surface_alt"),
            activebackground=theme.color("surface_alt"),
            highlightthickness=0, bd=0,
        ).pack(side="left", padx=(6, 2), pady=6)

        textos = tk.Frame(marco, bg=theme.color("surface_alt"))
        textos.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=6)
        tk.Label(
            textos,
            text=f"{etiqueta_categoria(sugerencia.category)} · {sugerencia.value_text}",
            bg=theme.color("surface_alt"), fg=theme.color("text"),
            font=theme.font(10, "bold"), anchor="w",
        ).pack(anchor="w")
        detalle = f"código: {sugerencia.value_code}"
        if sugerencia.qualifier:
            detalle += f" · nivel: {sugerencia.qualifier}"
        tk.Label(
            textos, text=detalle, bg=theme.color("surface_alt"),
            fg=theme.color("text_muted"), font=theme.font(8), anchor="w",
        ).pack(anchor="w")
        if sugerencia.evidence:
            tk.Label(
                textos, text=f"“{sugerencia.evidence.strip()[:160]}”",
                bg=theme.color("surface_alt"), fg=theme.color("text_faint"),
                font=theme.font(8), anchor="w", wraplength=560, justify="left",
            ).pack(anchor="w", pady=(2, 0))

    def _marcar(self, valor: bool) -> None:
        for var, _ in self._variables:
            var.set(valor)

    # -- acciones --
    def _aceptar(self) -> None:
        seleccionados = [
            fact_desde_sugerencia(sugerencia)
            for var, sugerencia in self._variables
            if var.get()
        ]
        self.resultado = seleccionados or None
        self.destroy()

    def _cancelar(self) -> None:
        self.resultado = None
        self.destroy()

    def _centrar(self, parent: tk.Misc) -> None:
        try:
            self.update_idletasks()
            raiz = parent.winfo_toplevel()
            x = raiz.winfo_rootx() + (raiz.winfo_width() - self.winfo_width()) // 2
            y = raiz.winfo_rooty() + (raiz.winfo_height() - self.winfo_height()) // 3
            self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        except tk.TclError:  # pragma: no cover - depende del SO
            pass


class CompletarPerfilDialog(tk.Toplevel):
    """«Completar perfil»: revisar los huecos del corpus y guardar los que SÍ se tienen.

    Los huecos salen de :func:`jobpulse_v15.perfil_huecos.calcular_huecos`
    (implementación única, agnóstica del titular): el diálogo solo los
    presenta y devuelve lo que el usuario marcó. **No toca SQLite.**

    Uso::

        datos = CompletarPerfilDialog.mostrar(parent, theme, huecos)
        if datos is not None:
            store.save_many(datos["facts"])   # hechos marcados
            store.sincronizar_areas(datos["areas"])  # conjunto final de áreas
    """

    def __init__(self, parent: tk.Misc, theme: Theme, huecos: HuecosPerfil) -> None:
        super().__init__(parent)
        self.theme = theme
        self.huecos = huecos
        self.resultado: dict[str, Any] | None = None
        #: (var, hecho_dict) de los huecos marcados
        self._variables: list[tuple[tk.BooleanVar, dict[str, Any]]] = []
        #: código -> BooleanVar de las áreas del catálogo
        self._areas: dict[str, tk.BooleanVar] = {}
        #: (seccion_frame, [(fila, texto_busqueda)]) para filtrar
        self._secciones: list[tuple[tk.Frame, list[tuple[tk.Frame, str]]]] = []
        self._boton_guardar: FlatButton | None = None

        self.title(t("Completar perfil"))
        self.configure(bg=theme.color("surface"))
        self.geometry("780x640")
        self.minsize(600, 440)
        self.transient(parent.winfo_toplevel())
        self._construir()
        self._centrar(parent)
        self.protocol("WM_DELETE_WINDOW", self._cancelar)

    # -- API de conveniencia --
    @classmethod
    def mostrar(
        cls, parent: tk.Misc, theme: Theme, huecos: HuecosPerfil
    ) -> dict[str, Any] | None:
        dialogo = cls(parent, theme, huecos)
        dialogo.grab_set()
        dialogo.wait_window()
        return dialogo.resultado

    # -- construcción --
    def _construir(self) -> None:
        theme = self.theme
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        cabecera = tk.Frame(self, bg=theme.color("surface"))
        cabecera.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 6))
        tk.Label(
            cabecera, text=t("Completar perfil"), bg=theme.color("surface"),
            fg=theme.color("text"), font=theme.font(14, "bold"), anchor="w",
        ).pack(anchor="w")
        tk.Label(
            cabecera,
            text=(
                f"Lo que el corpus pide y aún no registras: "
                f"{self.huecos.resumen_linea()} · "
                f"{self.huecos.avisos_evaluables} aviso(s) evaluables"
            ),
            bg=theme.color("surface"), fg=theme.color("text_muted"),
            font=theme.font(9), anchor="w", wraplength=720, justify="left",
        ).pack(anchor="w", pady=(2, 0))
        tk.Label(
            cabecera,
            text=t(
                "Marca solo lo que SÍ tienes: lo que no marques seguirá "
                "siendo un hueco (se vuelve a calcular y no se pregunta dos veces)."
            ),
            bg=theme.color("surface"), fg=theme.color("text_faint"),
            font=theme.font(8), anchor="w", wraplength=720, justify="left",
        ).pack(anchor="w", pady=(4, 0))

        if self.huecos.sin_canonico:
            aviso = tk.Frame(
                self, bg=theme.color("warning_soft"),
                highlightbackground=theme.color("warning"), highlightthickness=1,
            )
            aviso.grid(row=1, column=0, sticky="ew", padx=20, pady=(6, 0))
            tk.Label(
                aviso,
                text=(
                    f"⚠ {len(self.huecos.sin_canonico)} dato(s) guardados sin código "
                    "canónico: el motor los ignora. Re-regístralos desde el formulario."
                ),
                bg=theme.color("warning_soft"), fg=theme.color("warning"),
                font=theme.font(8), anchor="w", wraplength=700, justify="left",
            ).pack(anchor="w", padx=10, pady=5)

        filtro = tk.Frame(self, bg=theme.color("surface"))
        filtro.grid(row=2, column=0, sticky="ew", padx=20, pady=(8, 6))
        filtro.columnconfigure(0, weight=1)
        SearchField(
            filtro, theme, placeholder=t("Filtrar por código…"),
            on_change=self._filtrar,
        ).grid(row=0, column=0, sticky="ew")
        FlatButton(
            filtro, theme, t("Marcar visibles"),
            command=lambda: self._marcar_visibles(True), variant="flat",
        ).grid(row=0, column=1, padx=(8, 0))
        FlatButton(
            filtro, theme, t("Ninguno"),
            command=lambda: self._marcar_visibles(False), variant="ghost",
        ).grid(row=0, column=2, padx=(4, 0))

        scroll = ScrollFrame(self, theme)
        scroll.grid(row=3, column=0, sticky="nsew", padx=20)
        self._scroll = scroll
        self._pintar_listado(scroll.inner)

        pie = tk.Frame(self, bg=theme.color("surface"))
        pie.grid(row=4, column=0, sticky="ew", padx=20, pady=16)
        FlatButton(pie, theme, t("Cancelar"), command=self._cancelar,
                   variant="flat").pack(side="right")
        self._boton_guardar = FlatButton(
            pie, theme, t("Guardar marcados"), command=self._aceptar,
            variant="accent",
        )
        self._boton_guardar.pack(side="right", padx=(0, 8))
        self._actualizar_contador()

    def _pintar_listado(self, padre: tk.Misc) -> None:
        theme = self.theme
        # -- áreas de empleo (catálogo completo; sin marcadas se evalúa TODO) --
        if self.huecos.areas_catalogo:
            seccion = self._nueva_seccion(padre, t("Áreas de empleo"))
            if not self.huecos.areas_marcadas:
                tk.Label(
                    seccion, text=t(
                        "Ninguna marcada → se evalúan todas las áreas. "
                        "Marca las que te interesan."
                    ),
                    bg=theme.color("surface"), fg=theme.color("warning"),
                    font=theme.font(8), anchor="w", wraplength=680,
                    justify="left",
                ).pack(fill="x", padx=10, pady=(0, 4))
            marcas = set(self.huecos.areas_marcadas)
            for codigo, nombre in self.huecos.areas_catalogo:
                var = tk.BooleanVar(value=codigo in marcas)
                self._areas[codigo] = var
                fila = tk.Frame(seccion, bg=theme.color("surface_alt"),
                                highlightbackground=theme.color("border"),
                                highlightthickness=1)
                fila.pack(fill="x", pady=2, padx=10)
                tk.Checkbutton(
                    fila, variable=var, text=f"{nombre}  ({codigo})",
                    bg=theme.color("surface_alt"), fg=theme.color("text"),
                    activebackground=theme.color("surface_alt"),
                    highlightthickness=0, bd=0, font=theme.font(9),
                    command=self._actualizar_contador,
                ).pack(side="left", padx=6, pady=5)
                self._secciones[-1][1].append(
                    (fila, f"{codigo} {nombre}".casefold())
                )

        # -- huecos por categoría --
        por_categoria = self.huecos.por_categoria()
        for categoria, huecos in por_categoria.items():
            cerrada = categoria in ("education", "license")
            seccion = self._nueva_seccion(
                padre,
                f"{etiqueta_categoria(categoria)} · {len(huecos)}"
                + (f" — {t('categoría cerrada: elige entre las opciones')}"
                   if cerrada else ""),
            )
            for hueco in huecos:
                hecho = {
                    "category": hueco.categoria,
                    "value_code": hueco.codigo,
                    "value_text": hueco.codigo.replace("-", " "),
                }
                var = tk.BooleanVar(value=False)
                self._variables.append((var, hecho))

                fila = tk.Frame(seccion, bg=theme.color("surface_alt"),
                                highlightbackground=theme.color("border"),
                                highlightthickness=1)
                fila.pack(fill="x", pady=2, padx=10)
                tk.Checkbutton(
                    fila, variable=var, bg=theme.color("surface_alt"),
                    activebackground=theme.color("surface_alt"),
                    highlightthickness=0, bd=0,
                    command=self._actualizar_contador,
                ).pack(side="left", padx=(6, 2), pady=5)

                textos = tk.Frame(fila, bg=theme.color("surface_alt"))
                textos.pack(side="left", fill="x", expand=True, padx=(0, 8),
                            pady=4)
                tk.Label(
                    textos, text=hueco.codigo, bg=theme.color("surface_alt"),
                    fg=theme.color("text"), font=theme.font(9, "bold"),
                    anchor="w",
                ).pack(anchor="w")
                detalle = f"lo piden {hueco.avisos} aviso(s)"
                if hueco.niveles:
                    detalle += " · niveles: " + ", ".join(hueco.niveles)
                tk.Label(
                    textos, text=detalle, bg=theme.color("surface_alt"),
                    fg=theme.color("text_muted"), font=theme.font(8),
                    anchor="w",
                ).pack(anchor="w")
                # Registrar la fila para el filtrado (texto buscable = código).
                self._secciones[-1][1].append((fila, hueco.codigo.casefold()))

        if not self._variables and not self._areas:
            tk.Label(
                padre, text=t("El perfil ya cubre todo lo que el corpus pide."),
                bg=theme.color("surface"), fg=theme.color("text_muted"),
                font=theme.font(10),
            ).pack(pady=24)

    def _nueva_seccion(self, padre: tk.Misc, titulo: str) -> tk.Frame:
        theme = self.theme
        marco = tk.Frame(padre, bg=theme.color("surface"))
        marco.pack(fill="x", pady=(10, 2))
        SectionTitle(marco, theme, titulo).pack(fill="x", padx=10)
        # Las filas van en un contenedor aparte para poder ocultarlas al filtrar
        # sin perder la cabecera de la sección.
        contenedor = tk.Frame(marco, bg=theme.color("surface"))
        contenedor.pack(fill="x")
        self._secciones.append((marco, []))
        return contenedor

    # -- filtrado y marcado --
    def _filtrar(self, texto: str) -> None:
        consulta = texto.strip().casefold()
        for marco, filas in self._secciones:
            visible = False
            for fila, busqueda in filas:
                coincide = not consulta or consulta in busqueda
                if coincide:
                    fila.pack(fill="x", pady=2, padx=10)
                    visible = True
                else:
                    fila.pack_forget()
            # La sección entera desaparece si no queda ninguna fila visible.
            if visible or not filas:
                marco.pack(fill="x", pady=(10, 2))
            else:
                marco.pack_forget()

    def _marcar_visibles(self, valor: bool) -> None:
        for var, _ in self._variables:
            var.set(valor)
        for var in self._areas.values():
            var.set(valor)
        self._actualizar_contador()

    def _actualizar_contador(self) -> None:
        if self._boton_guardar is None:
            return
        hechos = sum(1 for var, _ in self._variables if var.get())
        areas = sum(1 for var in self._areas.values() if var.get())
        self._boton_guardar.configure(
            text=t("Guardar marcados") + f" ({hechos} dato(s), {areas} área(s))"
        )

    # -- acciones --
    def _aceptar(self) -> None:
        hechos = [hecho for var, hecho in self._variables if var.get()]
        areas = [codigo for codigo, var in self._areas.items() if var.get()]
        self.resultado = {
            "facts": hechos,
            "areas": areas,
        }
        self.destroy()

    def _cancelar(self) -> None:
        self.resultado = None
        self.destroy()

    def _centrar(self, parent: tk.Misc) -> None:
        try:
            self.update_idletasks()
            raiz = parent.winfo_toplevel()
            x = raiz.winfo_rootx() + (raiz.winfo_width() - self.winfo_width()) // 2
            y = raiz.winfo_rooty() + (raiz.winfo_height() - self.winfo_height()) // 3
            self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        except tk.TclError:  # pragma: no cover - depende del SO
            pass


def confirmar(parent: tk.Misc, titulo: str, mensaje: str) -> bool:
    """Confirmación simple (sí/no) con el estilo del sistema."""
    from tkinter import messagebox

    return bool(messagebox.askyesno(titulo, mensaje, parent=parent.winfo_toplevel()))


def pedir_texto(parent: tk.Misc, titulo: str, mensaje: str,
                valor_inicial: str = "", *, password: bool = False) -> str:
    """Pide una línea de texto (modal). Devuelve "" si se cancela.

    Es el equivalente plano de `simpledialog.askstring` pero con el estilo
    de la UI v2 (plano, sin Toplevel_tk feo).
    """
    from tkinter import simpledialog

    try:
        raiz = parent.winfo_toplevel()
    except tk.TclError:  # pragma: no cover - depende del SO
        raiz = parent
    valor = simpledialog.askstring(
        titulo, mensaje, initialvalue=valor_inicial, parent=raiz,
        show="*" if password else "",
    )
    return str(valor or "").strip()
