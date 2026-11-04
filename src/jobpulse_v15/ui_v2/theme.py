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


# --- Paletas (esquemas de color) ---------------------------------------------
# La elegida se guarda en ui_config.json (clave "paleta"); `crear_app()` la
# aplica al arrancar y ConfiguracionTab puede reconstruir la app en caliente
# (ver app.reconstruir_con_paleta). Agregar un esquema = 1 entrada aquí.

PALETA_CLARO_AZUL = Palette()

PALETA_CLARO_VERDE = Palette(
    accent="#047857",
    accent_hover="#065F46",
    accent_soft="#D1FAE5",
    accent_border="#A7F3D0",
    selection="#D1FAE5",
    sidebar_active="#047857",
)

PALETA_OSCURO = Palette(
    bg="#0F172A",
    surface="#1E293B",
    surface_alt="#22304A",
    surface_hover="#334155",
    border="#26344A",
    border_strong="#3B4A61",
    text="#E2E8F0",
    text_muted="#94A3B8",
    text_faint="#64748B",
    text_inverse="#FFFFFF",
    accent="#3B82F6",
    accent_hover="#2563EB",
    accent_soft="#1E3A8A",
    accent_border="#2563EB",
    success="#34D399",
    success_soft="#065F46",
    warning="#FBBF24",
    warning_soft="#92400E",
    danger="#F87171",
    danger_soft="#991B1B",
    neutral_soft="#334155",
    sidebar_bg="#020617",
    sidebar_hover="#0F172A",
    sidebar_active="#1D4ED8",
    sidebar_text="#94A3B8",
    sidebar_text_active="#FFFFFF",
    selection="#1E40AF",
    row_alt="#1A2436",
)

PALETAS: dict[str, Palette] = {
    "claro_azul": PALETA_CLARO_AZUL,
    "claro_verde": PALETA_CLARO_VERDE,
    "oscuro": PALETA_OSCURO,
}

# Nombre visible (lo que muestra el combo de Configuración).
NOMBRES_PALETA: dict[str, str] = {
    "claro_azul": "Claro · azul",
    "claro_verde": "Claro · verde",
    "oscuro": "Oscuro",
}

PALETA_DEFECTO = "claro_azul"


def paleta_por_nombre(nombre: str | None) -> Palette:
    """Paleta por nombre; cualquier valor desconocido cae al defecto."""
    return PALETAS.get(nombre or "", PALETAS[PALETA_DEFECTO])


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
    # Escala tipográfica: multiplica TODOS los tamaños pedidos a
    # `Theme.font`/`Theme.mono` y a los estilos de `apply_theme`. Es lo que
    # hace que "compacta" y "amplia" cambien de verdad el aspecto.
    font_scale: float = 1.0


# --- Densidades (compacta / normal / amplia) ---------------------------------
# La elegida se guarda en ui_config.json (clave "densidad"); `crear_app()` la
# aplica al arrancar y la tarjeta "Apariencia" la cambia en caliente junto
# con el esquema de color (misma reconstrucción). Agregar una densidad =
# 1 entrada aquí (y su nombre visible en NOMBRES_DENSIDAD).

DENSIDADES: dict[str, Metrics] = {
    "compacta": Metrics(
        sidebar_width=210,
        header_height=62,
        row_height=24,
        radius=8,
        pad=12,
        gap=10,
        pad_small=8,
        pad_tiny=4,
        detail_width=420,
        font_scale=0.92,
    ),
    "normal": Metrics(),
    "amplia": Metrics(
        sidebar_width=258,
        header_height=92,
        row_height=38,
        radius=12,
        pad=26,
        gap=20,
        pad_small=14,
        pad_tiny=8,
        detail_width=540,
        font_scale=1.1,
    ),
}

# Nombre visible (lo que muestra el combo de Configuración).
NOMBRES_DENSIDAD: dict[str, str] = {
    "compacta": "Compacta",
    "normal": "Normal",
    "amplia": "Amplia",
}

DENSIDAD_DEFECTO = "normal"


def metrics_por_nombre(nombre: str | None) -> Metrics:
    """Densidad por nombre; cualquier valor desconocido cae al defecto."""
    return DENSIDADES.get(nombre or "", DENSIDADES[DENSIDAD_DEFECTO])


@dataclass(frozen=True)
class Theme:
    """Paleta + medidas + estilos ttk listos para usar."""

    palette: Palette
    metrics: Metrics
    styles: ttk.Style

    def color(self, nombre: str) -> str:
        return getattr(self.palette, nombre)

    def font(self, size: int = 10, weight: str = "normal") -> str:
        """Especificación de fuente para Tk (el tamaño va escalado por la
        densidad: `metrics.font_scale`).

        OJO: la familia va entre LLAVES. Tk parte la especificación por
        espacios: "Segoe UI 10" se lee como familia "Segoe", tamaño "UI"
        -> "expected integer but got 'UI'". Con llaves: `{Segoe UI} 10`.
        """
        return f"{{{self.metrics.font_family}}} {self.escalar(size)} {weight}"

    def mono(self, size: int = 9) -> str:
        return f"{{{self.metrics.font_mono}}} {self.escalar(size)}"

    def escalar(self, size: int) -> int:
        """Tamaño pedido convertido al de la densidad vigente."""
        return max(6, int(round(size * self.metrics.font_scale)))


def _configurar_fuentes(root: tk.Misc, metrics: Metrics) -> None:
    """Fuente por defecto de toda la app (Windows: Segoe UI)."""
    try:
        default = tkfont.nametofont("TkDefaultFont")
    except tk.TclError:  # pragma: no cover - depende del SO
        return
    tam = max(6, int(round(10 * metrics.font_scale)))
    default.configure(family=metrics.font_family, size=tam)
    named = tkfont.nametofont("TkTextFont")
    named.configure(family=metrics.font_family, size=tam)


def apply_theme(root: tk.Misc, palette: Palette | None = None,
                metrics: Metrics | None = None) -> Theme:
    """Aplica el tema plano a `root` y devuelve el `Theme` para reutilizarlo."""
    paleta = palette or Palette()
    medidas = metrics or Metrics()
    k = medidas.font_scale  # escala de la densidad (padding de controles)

    def _fu(base: int, peso: str = "") -> str:
        """Especificación de fuente escalada por la densidad vigente."""
        tam = max(6, int(round(base * medidas.font_scale)))
        return f"{{{medidas.font_family}}} {tam}" + (f" {peso}" if peso else "")

    def _pad(ancho: int, alto: int) -> tuple[int, int]:
        return (int(round(ancho * k)), int(round(alto * k)))

    estilos = ttk.Style(root)
    try:
        estilos.theme_use("clam")
    except tk.TclError:  # pragma: no cover - clam viene con Tk
        pass

    _configurar_fuentes(root, medidas)

    # La fuente por defecto va CON LLAVES y con tamaño: "Segoe UI" a secas
    # lo parsea Tk como familia "Segoe" + tamaño "UI" (error al crear
    # cualquier widget que no lleve fuente explícita).
    fuente = _fu(10)
    fuente_mono = _fu(9)
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
        font=_fu(16, "bold"),
    )
    estilos.configure(
        "Subtitle.TLabel",
        background=paleta.surface,
        foreground=paleta.text_muted,
        font=_fu(9),
    )
    estilos.configure(
        "Section.TLabel",
        background=paleta.surface,
        foreground=paleta.text_faint,
        font=_fu(8, "bold"),
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
        padding=_pad(14, 8),
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
        padding=_pad(16, 9),
        font=_fu(10, "bold"),
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
        padding=_pad(10, 6),
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
        padding=_pad(18, 11),
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
        padding=int(round(8 * k)),
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
        padding=int(round(6 * k)),
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
        padding=_pad(8, 9),
        font=_fu(8, "bold"),
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




