# -*- coding: utf-8 -*-
"""Diálogos (Toplevel) reutilizables de la UI v2.

Los diálogos reciben `theme` y datos planos; no hablan con el repositorio.
Así una pestaña nueva puede reutilizarlos sin acoplarse.
"""
from __future__ import annotations

import tkinter as tk
from typing import Any, Sequence

from jobpulse_v15.ui_v2.data.profile import etiqueta_categoria, fact_desde_sugerencia
from jobpulse_v15.ui_v2.theme import Theme
from jobpulse_v15.ui_v2.widgets import FlatButton, ScrollFrame
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
