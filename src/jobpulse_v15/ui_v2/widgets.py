# -*- coding: utf-8 -*-
"""Componentes reutilizables de la UI v2 (planos, sin relieve).

Cada componente es un widget "contenedor" que recibe `theme` y expone un
constructor estable. Las pestañas componen estos piezas; nunca crean
widgets con colores sueltos.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Iterable, Sequence

from jobpulse_v15.ui_v2.theme import Theme


class Card(tk.Frame):
    """Tarjeta plana: fondo blanco, borde de 1 px y padding uniforme."""

    def __init__(self, parent: tk.Misc, theme: Theme, *, padding: int | None = None,
                 background: str | None = None) -> None:
        self.theme = theme
        super().__init__(
            parent,
            bg=background or theme.color("surface"),
            highlightbackground=theme.color("border"),
            highlightcolor=theme.color("border"),
            highlightthickness=1,
            bd=0,
        )
        self.pad = theme.metrics.pad if padding is None else padding
        self.body = tk.Frame(self, bg=self.cget("bg"))
        self.body.pack(fill="both", expand=True, padx=self.pad, pady=self.pad)


class SectionTitle(tk.Frame):
    """Rótulo de sección + textoSecondary opcional."""

    def __init__(self, parent: tk.Misc, theme: Theme, title: str,
                 hint: str | None = None, *, background: str | None = None) -> None:
        self.theme = theme
        super().__init__(parent, bg=background or theme.color("surface"))
        tk.Label(
            self,
            text=title.upper(),
            bg=self.cget("bg"),
            fg=theme.color("text_faint"),
            font=theme.font(8, "bold"),
            anchor="w",
        ).pack(side="left")
        if hint:
            tk.Label(
                self,
                text=hint,
                bg=self.cget("bg"),
                fg=theme.color("text_faint"),
                font=theme.font(8),
                anchor="e",
            ).pack(side="right")


class StatTile(tk.Frame):
    """Métrica grande (valor + etiqueta + pista) para la franja de resumen."""

    def __init__(self, parent: tk.Misc, theme: Theme, label: str, value: str = "—",
                 hint: str | None = None) -> None:
        self.theme = theme
        super().__init__(parent, bg=theme.color("surface"))
        self._value_label = tk.Label(
            self, text=value, bg=self.cget("bg"), fg=theme.color("text"),
            font=theme.font(20, "bold"), anchor="w",
        )
        self._value_label.pack(anchor="w")
        tk.Label(
            self, text=label.upper(), bg=self.cget("bg"), fg=theme.color("text_muted"),
            font=theme.font(8, "bold"), anchor="w",
        ).pack(anchor="w", pady=(2, 0))
        self._hint_label = tk.Label(
            self, text=hint or "", bg=self.cget("bg"), fg=theme.color("text_faint"),
            font=theme.font(8), anchor="w",
        )
        if hint:
            self._hint_label.pack(anchor="w", pady=(2, 0))

    def update_values(self, value: str, hint: str | None = None) -> None:
        self._value_label.configure(text=value)
        if hint is not None:
            self._hint_label.configure(text=hint)
            if not self._hint_label.winfo_ismapped():
                self._hint_label.pack(anchor="w", pady=(2, 0))


class Badge(tk.Label):
    """Etiqueta de estado con fondo tintado (tonos: accent/success/warning/danger/neutral)."""

    TONES = {
        "accent": ("accent_soft", "accent"),
        "success": ("success_soft", "success"),
        "warning": ("warning_soft", "warning"),
        "danger": ("danger_soft", "danger"),
        "neutral": ("neutral_soft", "text_muted"),
    }

    def __init__(self, parent: tk.Misc, theme: Theme, text: str = "",
                 tone: str = "neutral") -> None:
        self.theme = theme
        self._tone = tone
        super().__init__(parent, text=text, bg=theme.color("neutral_soft"),
                         fg=theme.color("text_muted"), font=theme.font(8, "bold"),
                         padx=8, pady=3, bd=0)
        self.set_tone(tone)

    def set_tone(self, tone: str) -> None:
        self._tone = tone if tone in self.TONES else "neutral"
        fondo, texto = self.TONES[self._tone]
        self.configure(bg=self.theme.color(fondo), fg=self.theme.color(texto))

    def set_text(self, text: str) -> None:
        self.configure(text=text)


class SearchField(tk.Frame):
    """Campo de búsqueda plano con icono de lupa y botón de limpiar."""

    def __init__(self, parent: tk.Misc, theme: Theme, *,
                 placeholder: str = "Buscar…", width: int = 32,
                 on_change: Callable[[str], None] | None = None) -> None:
        self.theme = theme
        self._on_change = on_change
        self._placeholder = placeholder
        super().__init__(parent, bg=theme.color("surface"))
        self._inner = tk.Frame(
            self, bg=theme.color("surface"),
            highlightbackground=theme.color("border_strong"),
            highlightcolor=theme.color("accent"),
            highlightthickness=1,
        )
        self._inner.pack(fill="x")
        tk.Label(
            self._inner, text="⌕", bg=theme.color("surface"),
            fg=theme.color("text_faint"), font=theme.font(12),
        ).pack(side="left", padx=(10, 4))
        self.var = tk.StringVar()
        self.entry = tk.Entry(
            self._inner, textvariable=self.var, bd=0, relief="flat",
            bg=theme.color("surface"), fg=theme.color("text"),
            insertbackground=theme.color("text"), width=width,
            font=theme.font(10),
        )
        self.entry.pack(side="left", fill="both", expand=True, pady=8)
        self._clear = tk.Label(
            self._inner, text="✕", bg=theme.color("surface"),
            fg=theme.color("text_faint"), cursor="hand2", font=theme.font(9),
        )
        self._clear.pack(side="right", padx=10)
        self._clear.bind("<Button-1>", lambda _e: self.clear())
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
        self.entry.bind("<Return>", self._on_return)
        self.entry.bind("<Escape>", lambda _e: self.clear())
        self._show_placeholder()

    # -- comportamiento --
    def _show_placeholder(self) -> None:
        if not self.var.get():
            self.entry.configure(fg=self.theme.color("text_faint"))
            self.entry.insert(0, self._placeholder)

    def _on_focus_in(self, _event=None) -> None:
        if self.entry.get() == self._placeholder:
            self.entry.delete(0, "end")
            self.entry.configure(fg=self.theme.color("text"))

    def _on_focus_out(self, _event=None) -> None:
        if not self.var.get().strip():
            self._show_placeholder()

    def _on_return(self, _event=None) -> None:
        if self._on_change:
            self._on_change(self.value())

    def value(self) -> str:
        texto = self.var.get().strip()
        return "" if texto == self._placeholder else texto

    def clear(self) -> None:
        self.var.set("")
        self.entry.delete(0, "end")
        self.entry.configure(fg=self.theme.color("text_faint"))
        self.entry.insert(0, self._placeholder)
        self.entry.focus_set()
        if self._on_change:
            self._on_change("")


class FlatButton(ttk.Button):
    """Botón plano con estilos del tema ("flat", "accent" o "ghost")."""

    def __init__(self, parent: tk.Misc, theme: Theme, text: str, command=None,
                 *, variant: str = "flat", width: int | None = None) -> None:
        estilos = {"flat": "Flat.TButton", "accent": "Accent.TButton", "ghost": "Ghost.TButton"}
        super().__init__(parent, text=text, command=command,
                         style=estilos.get(variant, "Flat.TButton"), width=width)


class EmptyState(tk.Frame):
    """Estado vacío (sin datos) centrado y discreto."""

    def __init__(self, parent: tk.Misc, theme: Theme, title: str, message: str = "",
                 *, background: str | None = None) -> None:
        self.theme = theme
        super().__init__(parent, bg=background or theme.color("surface"))
        tk.Label(
            self, text=title, bg=self.cget("bg"), fg=theme.color("text"),
            font=theme.font(12, "bold"),
        ).pack(pady=(24, 6))
        if message:
            tk.Label(
                self, text=message, bg=self.cget("bg"), fg=theme.color("text_muted"),
                font=theme.font(9), wraplength=420, justify="center",
            ).pack(pady=(0, 24))


class ScrollFrame(tk.Frame):
    """Marco con scroll vertical (para paneles laterales largos).

    PATRÓN IMPORTANTE: el callback de `yscrollcommand` SOLO actualiza el
    scrollbar (via `bar.set`). Tocar el canvas dentro de ese callback
    dispara de nuevo el callback y entra en reentrada infinita.
    """

    def __init__(self, parent: tk.Misc, theme: Theme, *,
                 background: str | None = None) -> None:
        self.theme = theme
        self._bg = background or theme.color("surface")
        super().__init__(parent, bg=self._bg)
        self.canvas = tk.Canvas(self, bg=self._bg, highlightthickness=0, bd=0)
        self.bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview,
                                 style="Flat.Vertical.TScrollbar")
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.inner = tk.Frame(self.canvas, bg=self._bg)
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.bind("<Enter>", self._activa_rueda)
        self.bind("<Leave>", self._desactiva_rueda)
        self._rueda_activa = False
        self.canvas.pack(side="left", fill="both", expand=True)

    def _on_inner_configure(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._ajusta_barra()

    def _on_canvas_configure(self, event) -> None:
        self.canvas.itemconfigure(self._window, width=event.width)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._ajusta_barra()

    def _ajusta_barra(self) -> None:
        """Muestra el scrollbar solo si el contenido no cabe."""
        visible = self.canvas.winfo_height()
        if visible <= 1:  # aún sin layout
            return
        contenido = self.inner.winfo_reqheight()
        if contenido <= visible:
            if self.bar.winfo_ismapped():
                self.bar.pack_forget()
        elif not self.bar.winfo_ismapped():
            self.bar.pack(side="right", fill="y")

    def _activa_rueda(self, _event=None) -> None:
        if not self._rueda_activa:
            self._rueda_activa = True
            self.canvas.bind_all("<MouseWheel>", self._rueda)

    def _desactiva_rueda(self, _event=None) -> None:
        if self._rueda_activa:
            self._rueda_activa = False
            self.canvas.unbind_all("<MouseWheel>")

    def _rueda(self, event) -> None:
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def scroll_to_top(self) -> None:
        self.canvas.yview_moveto(0)


class KeyValue(tk.Frame):
    """Par etiqueta/valor para el panel de detalle."""

    def __init__(self, parent: tk.Misc, theme: Theme, label: str, value: str,
                 *, background: str | None = None, mono: bool = False) -> None:
        self.theme = theme
        self._bg = background or theme.color("surface")
        super().__init__(parent, bg=self._bg)
        tk.Label(
            self, text=label, bg=self._bg, fg=theme.color("text_faint"),
            font=theme.font(8, "bold"), width=18, anchor="w",
        ).pack(side="left", fill="x")
        self.value_label = tk.Label(
            self, text=value or "—", bg=self._bg, fg=theme.color("text"),
            font=theme.mono(9) if mono else theme.font(9), anchor="w",
            justify="left", wraplength=280,
        )
        self.value_label.pack(side="left", fill="x", expand=True)

    def set_value(self, value: str) -> None:
        self.value_label.configure(text=value or "—")


def separador(parent: tk.Misc, theme: Theme, *, background: str | None = None) -> tk.Frame:
    """Línea horizontal de 1 px."""
    return tk.Frame(parent, height=1, bg=theme.color("border"),
                    bd=0, highlightthickness=0)
