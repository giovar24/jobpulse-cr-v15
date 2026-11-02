# -*- coding: utf-8 -*-
"""Sistema de diseño de la UI v2 (plana y modular).

Este módulo es la ÚNICA fuente de color, tipografía y espaciado de la UI v2.
Las pestañas no inventan estilos: usan `theme` y los componentes de
:mod:`jobpulse_v15.ui_v2.widgets`.

REGLA DE ORO
------------
Si un valor visual (color, radio, padding, fuente) aparece escrito a mano en
una pestaña, está mal: se añade aquí. Así una pestaña nueva hereda el
diseño y un cambio de paleta se aplica a toda la app de un solo golpe.
"""
from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import font as tkfont
from tkinter import ttk


@dataclass(frozen=True)
class Palette:
    """Colores de la interfaz (plana, sin relieve ni sombras)."""

    bg: str = "#F4F6FA"
    surface: str = "#FFFFFF"
    surface_alt: str = "#F8FAFC"
    surface_hover: str = "#F1F5F9"
    border: str = "#E2E8F0"
    border_strong: str = "#CBD5E1"

    text: str = "#0F172A"
    text_muted: str = "#64748B"
    text_faint: str = "#94A3B8"
    text_inverse: str = "#FFFFFF"

    accent: str = "#2563EB"
    accent_hover: str = "#1D4ED8"
    accent_soft: str = "#E8F0FE"
    accent_border: str = "#BFDBFE"

    success: str = "#047857"
    success_soft: str = "#D1FAE5"
    warning: str = "#B45309"
    warning_soft: str = "#FEF3C7"
    danger: str = "#B91C1C"
    danger_soft: str = "#FEE2E2"
    neutral_soft: str = "#E2E8F0"

    sidebar_bg: str = "#0F172A"
    sidebar_hover: str = "#1E293B"
    sidebar_active: str = "#1D4ED8"
    sidebar_text: str = "#94A3B8"
    sidebar_text_active: str = "#FFFFFF"

    selection: str = "#DBEAFE"
    row_alt: str = "#FBFCFE"


@dataclass(frozen=True)
class Metrics:
    """Medidas del diseño (unidades en píxeles)."""

    sidebar_width: int = 236
    header_height: int = 76
    row_height: int = 30
    radius: int = 10
    pad: int = 18
    gap: int = 14
    pad_small: int = 10
    pad_tiny: int = 6
    detail_width: int = 460
    font_family: str = "Segoe UI"
    font_mono: str = "Consolas"


@dataclass(frozen=True)
class Theme:
    """Paleta + medidas + estilos ttk listos para usar."""

    palette: Palette
    metrics: Metrics
    styles: ttk.Style

    def color(self, nombre: str) -> str:
        return getattr(self.palette, nombre)

    def font(self, size: int = 10, weight: str = "normal") -> str:
        """Especificación de fuente para Tk.

        OJO: la familia va entre LLAVES. Tk parte la especificación por
        espacios: "Segoe UI 10" se lee como familia "Segoe", tamaño "UI"
        -> "expected integer but got 'UI'". Con llaves: `{Segoe UI} 10`.
        """
        return f"{{{self.metrics.font_family}}} {size} {weight}"

    def mono(self, size: int = 9) -> str:
        return f"{{{self.metrics.font_mono}}} {size}"


def _configurar_fuentes(root: tk.Misc, metrics: Metrics) -> None:
    """Fuente por defecto de toda la app (Windows: Segoe UI)."""
    try:
        default = tkfont.nametofont("TkDefaultFont")
    except tk.TclError:  # pragma: no cover - depende del SO
        return
    default.configure(family=metrics.font_family, size=10)
    named = tkfont.nametofont("TkTextFont")
    named.configure(family=metrics.font_family, size=10)


def apply_theme(root: tk.Misc, palette: Palette | None = None,
                metrics: Metrics | None = None) -> Theme:
    """Aplica el tema plano a `root` y devuelve el `Theme` para reutilizarlo."""
    paleta = palette or Palette()
    medidas = metrics or Metrics()
    estilos = ttk.Style(root)
    try:
        estilos.theme_use("clam")
    except tk.TclError:  # pragma: no cover - clam viene con Tk
        pass

    _configurar_fuentes(root, medidas)

    # La fuente por defecto va CON LLAVES y con tamaño: "Segoe UI" a secas
    # lo parsea Tk como familia "Segoe" + tamaño "UI" (error al crear
    # cualquier widget que no lleve fuente explícita).
    fuente = f"{{{medidas.font_family}}} 10"
    fuente_mono = f"{{{medidas.font_mono}}} 9"
    root.option_add("*Font", fuente)
    root.configure(background=paleta.bg)

    estilos.configure("TFrame", background=paleta.bg)
    estilos.configure("Surface.TFrame", background=paleta.surface)
    estilos.configure("Sidebar.TFrame", background=paleta.sidebar_bg)
    estilos.configure("Header.TFrame", background=paleta.surface)
    estilos.configure("Card.TFrame", background=paleta.surface)
    estilos.configure("Muted.TFrame", background=paleta.surface_alt)

    estilos.configure(
        "TLabel",
        background=paleta.bg,
        foreground=paleta.text,
        font=fuente,
    )
    estilos.configure(
        "Surface.TLabel",
        background=paleta.surface,
        foreground=paleta.text,
    )
    estilos.configure(
        "Muted.TLabel",
        background=paleta.surface_alt,
        foreground=paleta.text_muted,
    )
    estilos.configure(
        "Sidebar.TLabel",
        background=paleta.sidebar_bg,
        foreground=paleta.sidebar_text,
    )
    estilos.configure(
        "SidebarActive.TLabel",
        background=paleta.sidebar_active,
        foreground=paleta.sidebar_text_active,
    )
    estilos.configure(
        "Title.TLabel",
        background=paleta.surface,
        foreground=paleta.text,
        font=f'{{{medidas.font_family}}} 16 bold',
    )
    estilos.configure(
        "Subtitle.TLabel",
        background=paleta.surface,
        foreground=paleta.text_muted,
        font=f'{{{medidas.font_family}}} 9',
    )
    estilos.configure(
        "Section.TLabel",
        background=paleta.surface,
        foreground=paleta.text_faint,
        font=f'{{{medidas.font_family}}} 8 bold',
    )

    # --- Botones planos ---
    estilos.configure(
        "Flat.TButton",
        background=paleta.surface,
        foreground=paleta.text,
        bordercolor=paleta.border_strong,
        focuscolor=paleta.surface,
        borderwidth=1,
        relief="flat",
        padding=(14, 8),
        font=fuente,
    )
    estilos.map(
        "Flat.TButton",
        background=[("active", paleta.surface_hover), ("disabled", paleta.surface_alt)],
        foreground=[("disabled", paleta.text_faint)],
    )
    estilos.configure(
        "Accent.TButton",
        background=paleta.accent,
        foreground=paleta.text_inverse,
        bordercolor=paleta.accent,
        focuscolor=paleta.accent,
        borderwidth=0,
        relief="flat",
        padding=(16, 9),
        font=f'{{{medidas.font_family}}} 10 bold',
    )
    estilos.map(
        "Accent.TButton",
        background=[("active", paleta.accent_hover), ("disabled", paleta.border_strong)],
        foreground=[("disabled", paleta.text_faint)],
    )
    estilos.configure(
        "Ghost.TButton",
        background=paleta.surface,
        foreground=paleta.text_muted,
        borderwidth=0,
        relief="flat",
        padding=(10, 6),
        font=fuente,
    )
    estilos.map(
        "Ghost.TButton",
        background=[("active", paleta.surface_hover)],
        foreground=[("active", paleta.text)],
    )
    estilos.configure(
        "Sidebar.TButton",
        background=paleta.sidebar_bg,
        foreground=paleta.sidebar_text,
        borderwidth=0,
        relief="flat",
        padding=(18, 11),
        anchor="w",
        font=fuente,
    )
    estilos.map(
        "Sidebar.TButton",
        background=[("active", paleta.sidebar_hover)],
        foreground=[("active", paleta.sidebar_text_active)],
    )

    # --- Campos ---
    estilos.configure(
        "TEntry",
        fieldbackground=paleta.surface,
        foreground=paleta.text,
        bordercolor=paleta.border_strong,
        lightcolor=paleta.border_strong,
        darkcolor=paleta.border_strong,
        insertcolor=paleta.text,
        borderwidth=1,
        relief="flat",
        padding=8,
    )
    estilos.map(
        "TEntry",
        bordercolor=[("focus", paleta.accent)],
        lightcolor=[("focus", paleta.accent)],
        darkcolor=[("focus", paleta.accent)],
    )
    estilos.configure(
        "TCombobox",
        fieldbackground=paleta.surface,
        background=paleta.surface,
        foreground=paleta.text,
        arrowcolor=paleta.text_muted,
        bordercolor=paleta.border_strong,
        lightcolor=paleta.border_strong,
        darkcolor=paleta.border_strong,
        borderwidth=1,
        relief="flat",
        padding=6,
    )
    estilos.map(
        "TCombobox",
        fieldbackground=[("readonly", paleta.surface)],
        bordercolor=[("focus", paleta.accent)],
        lightcolor=[("focus", paleta.accent)],
        darkcolor=[("focus", paleta.accent)],
    )
    root.option_add("*TCombobox*Listbox.background", paleta.surface)
    root.option_add("*TCombobox*Listbox.foreground", paleta.text)
    root.option_add("*TCombobox*Listbox.selectBackground", paleta.accent)
    root.option_add("*TCombobox*Listbox.selectForeground", paleta.text_inverse)

    # --- Tabla ---
    estilos.configure(
        "Flat.Treeview",
        background=paleta.surface,
        fieldbackground=paleta.surface,
        foreground=paleta.text,
        borderwidth=0,
        relief="flat",
        rowheight=medidas.row_height,
        font=fuente,
    )
    estilos.map(
        "Flat.Treeview",
        background=[("selected", paleta.selection)],
        foreground=[("selected", paleta.text)],
    )
    estilos.configure(
        "Flat.Treeview.Heading",
        background=paleta.surface_alt,
        foreground=paleta.text_muted,
        borderwidth=0,
        relief="flat",
        padding=(8, 9),
        font=f'{{{medidas.font_family}}} 8 bold',
    )
    estilos.map(
        "Flat.Treeview.Heading",
        background=[("active", paleta.surface_hover)],
        foreground=[("active", paleta.text)],
    )

    # --- Scrollbar ---
    estilos.configure(
        "Flat.Vertical.TScrollbar",
        background=paleta.border_strong,
        troughcolor=paleta.bg,
        bordercolor=paleta.bg,
        arrowcolor=paleta.text_muted,
        relief="flat",
        borderwidth=0,
        arrowsize=12,
    )
    estilos.map(
        "Flat.Vertical.TScrollbar",
        background=[("active", paleta.text_faint)],
    )
    estilos.configure(
        "Flat.Horizontal.TScrollbar",
        background=paleta.border_strong,
        troughcolor=paleta.bg,
        bordercolor=paleta.bg,
        arrowcolor=paleta.text_muted,
        relief="flat",
        borderwidth=0,
        arrowsize=12,
    )

    # --- Checks y separadores ---
    estilos.configure(
        "TCheckbutton",
        background=paleta.surface,
        foreground=paleta.text_muted,
        focuscolor=paleta.surface,
        font=fuente,
    )
    estilos.map("TCheckbutton", background=[("active", paleta.surface)])
    estilos.configure("TSeparator", background=paleta.border)

    return Theme(palette=paleta, metrics=medidas, styles=estilos)




