# -*- coding: utf-8 -*-
"""Shell de la UI v2: sidebar + cabecera + área de contenido.

El shell NO conoce el contenido de las pestañas: sólo las monta, las
muestra y les pide que se refresquen. Agregar una pestaña es agregar un
módulo en `ui_v2/tabs/` y registrarla en `PESTANIAS` (abajo).
"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import Sequence, Type

from jobpulse_v15.db import Database
from jobpulse_v15.repository import Repository
from jobpulse_v15.ui_v2 import configuracion
from jobpulse_v15.ui_v2.configuracion import paleta_actual
from jobpulse_v15.ui_v2.data.jobs import JobsStore
from jobpulse_v15.ui_v2.data.paso5 import Paso5Store
from jobpulse_v15.ui_v2.data.profile import ProfileStore
from jobpulse_v15.ui_v2.data.retencion import RetencionStore
from jobpulse_v15.ui_v2.tabs.base import BaseTab, TabContext
from jobpulse_v15.ui_v2.tabs.configuracion import ConfiguracionTab
from jobpulse_v15.ui_v2.tabs.crudos import DatosCrudosTab
from jobpulse_v15.ui_v2.tabs.cuentas import CuentasTab
from jobpulse_v15.ui_v2.tabs.perfil import PerfilTab
from jobpulse_v15.ui_v2.tabs.scraping import ScrapingTab
from jobpulse_v15.ui_v2.tabs.vacantes import VacantesTab
from jobpulse_v15.ui_v2.theme import (
    Metrics,
    Theme,
    apply_theme,
    paleta_por_nombre,
)
from jobpulse_v15.ui_v2.widgets import FlatButton

# --- REGISTRO DE PESTAÑAS (único lugar que hay que tocar al agregar una) ---
PESTANIAS: tuple[Type[BaseTab], ...] = (
    DatosCrudosTab,
    PerfilTab,
    VacantesTab,
    ScrapingTab,
    CuentasTab,
    ConfiguracionTab,
)


class AppShell:
    """Ventana principal de la UI v2."""

    def __init__(self, root: tk.Tk, repository: Repository, *,
                 theme: Theme | None = None,
                 pestanias: Sequence[Type[BaseTab]] = PESTANIAS) -> None:
        self.root = root
        self.repository = repository
        self.theme = theme or apply_theme(root)
        self.pestanias = list(pestanias)
        # La politica de retencion (O8/O10) la comparten los stores de
        # avisos y la pestana de Configuracion (misma instancia).
        retencion_store = RetencionStore()
        self.contexto = TabContext(
            repository=repository,
            theme=self.theme,
            services={
                "retencion_store": retencion_store,
                "jobs_store": JobsStore(repository, retencion_store),
                "profile_store": ProfileStore(repository),
                "paso5_store": Paso5Store(repository),
                # Servicio que ConfiguracionTab usa para cambiar el
                # esquema de color en caliente (reconstruye la app entera).
                "reconstruir_ui": self.reconstruir_con_paleta,
            },
        )
        self.instancias: list[BaseTab] = []
        self._marcos: dict[str, tk.Frame] = {}
        self._botones: dict[str, tk.Button] = {}
        self._indice_activo = 0

        root.title("JobPulse CR · v2")
        root.geometry("1440x880")
        root.minsize(1120, 700)
        root.configure(bg=self.theme.color("bg"))
        self._construir()
        if self.instancias:
            self.mostrar(0)

    # -- construcción --
    def _construir(self) -> None:
        theme = self.theme
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        self._construir_sidebar()
        self._construir_cabecera()

        self.contenido = tk.Frame(self.root, bg=theme.color("bg"))
        self.contenido.grid(row=0, column=1, sticky="nsew")
        self.contenido.rowconfigure(0, weight=1)
        self.contenido.columnconfigure(0, weight=1)

    def _construir_sidebar(self) -> None:
        theme = self.theme
        self.sidebar = tk.Frame(self.root, bg=theme.color("sidebar_bg"),
                                width=theme.metrics.sidebar_width)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        marca = tk.Frame(self.sidebar, bg=theme.color("sidebar_bg"))
        marca.pack(fill="x", padx=20, pady=(24, 28))
        tk.Label(
            marca, text="JobPulse", bg=theme.color("sidebar_bg"), fg="#F8FAFC",
            font=theme.font(15, "bold"),
        ).pack(anchor="w")
        tk.Label(
            marca, text="Costa Rica · v2", bg=theme.color("sidebar_bg"),
            fg=theme.color("sidebar_text"), font=theme.font(8),
        ).pack(anchor="w", pady=(2, 0))

        nav = tk.Frame(self.sidebar, bg=theme.color("sidebar_bg"))
        nav.pack(fill="x")
        for indice, clase in enumerate(self.pestanias):
            instancia = clase(self.contexto)
            self.instancias.append(instancia)
            boton = tk.Button(
                nav,
                text=f"  {instancia.icon}  {instancia.title}",
                command=lambda i=indice: self.mostrar(i),
                anchor="w",
                bd=0,
                relief="flat",
                bg=theme.color("sidebar_bg"),
                fg=theme.color("sidebar_text"),
                activebackground=theme.color("sidebar_hover"),
                activeforeground=theme.color("sidebar_text_active"),
                font=theme.font(10),
                cursor="hand2",
                padx=6,
                pady=9,
            )
            boton.pack(fill="x", padx=10)
            self._botones[instancia.key] = boton

        pie = tk.Frame(self.sidebar, bg=theme.color("sidebar_bg"))
        pie.pack(side="bottom", fill="x", padx=20, pady=20)
        tk.Label(
            pie, text="UI v2", bg=theme.color("sidebar_bg"),
            fg=theme.color("sidebar_text"), font=theme.font(8, "bold"),
        ).pack(anchor="w")
        tk.Label(
            pie, text="La UI clásica sigue disponible:\npython -m jobpulse_v15.ui",
            bg=theme.color("sidebar_bg"), fg=theme.color("sidebar_text"),
            font=theme.font(8), justify="left", wraplength=180,
        ).pack(anchor="w", pady=(4, 0))

    def _construir_cabecera(self) -> None:
        theme = self.theme
        self.cabecera = tk.Frame(self.root, bg=theme.color("surface"),
                                 height=theme.metrics.header_height)
        self.cabecera.grid(row=0, column=1, sticky="new")
        self.cabecera.grid_propagate(False)
        self.cabecera.grid_columnconfigure(0, weight=1)

        textos = tk.Frame(self.cabecera, bg=theme.color("surface"))
        textos.grid(row=0, column=0, sticky="w", padx=theme.metrics.pad, pady=(14, 12))
        self._titulo = tk.Label(
            textos, text="", bg=theme.color("surface"), fg=theme.color("text"),
            font=theme.font(16, "bold"), anchor="w",
        )
        self._titulo.pack(anchor="w")
        self._subtitulo = tk.Label(
            textos, text="", bg=theme.color("surface"), fg=theme.color("text_muted"),
            font=theme.font(9), anchor="w",
        )
        self._subtitulo.pack(anchor="w", pady=(2, 0))

        acciones = tk.Frame(self.cabecera, bg=theme.color("surface"))
        acciones.grid(row=0, column=1, sticky="e", padx=theme.metrics.pad)
        self.boton_refrescar = FlatButton(
            acciones, theme, "Actualizar", command=self.refrescar, variant="flat"
        )
        self.boton_refrescar.pack(side="right")

        tk.Frame(self.root, height=1, bg=theme.color("border")).grid(
            row=0, column=1, sticky="sew"
        )

    # -- navegación --
    def mostrar(self, indice: int) -> None:
        """Muestra la pestaña `indice` (montándola la primera vez)."""
        if not self.instancias:
            return
        self._indice_activo = indice
        instancia = self.instancias[indice]
        marco = self._marcos.get(instancia.key)
        if marco is None:
            marco = instancia.build(self.contenido)
            marco.grid(row=0, column=0, sticky="nsew")
            self._marcos[instancia.key] = marco
        for clave, otro in self._marcos.items():
            if clave == instancia.key:
                otro.grid(row=0, column=0, sticky="nsew")
            else:
                otro.grid_forget()

        for clave, boton in self._botones.items():
            activo = clave == instancia.key
            boton.configure(
                bg=self.theme.color("sidebar_active") if activo else self.theme.color("sidebar_bg"),
                fg=self.theme.color("sidebar_text_active") if activo else self.theme.color("sidebar_text"),
            )

        self._titulo.configure(text=instancia.title)
        self._subtitulo.configure(text=instancia.subtitle)
        instancia.on_show()

    def refrescar(self) -> None:
        """Pide a la pestaña activa que recargue sus datos."""
        if not self.instancias:
            return
        instancia = self.instancias[self._indice_activo]
        instancia.refresh()

    def reconstruir_con_paleta(self, nombre: str) -> None:
        """Reconstruye la app entera con la paleta `nombre` (caliente).

        Es el servicio `reconstruir_ui` que invoca ConfiguracionTab tras
        guardar el nombre en ui_config.json: destruye los widgets viejos,
        re-aplica el tema al root y vuelve a montar las pestañas (se
        conserva la activa y los stores del contexto). El handle del
        servidor IA vive en `tabs.configuracion` (módulo) y por eso
        sobrevive a este rebuild.
        """
        theme = apply_theme(self.root, paleta_por_nombre(nombre), Metrics())
        self.theme = theme
        self.contexto.theme = theme
        for widget in self.root.winfo_children():
            widget.destroy()
        self.instancias.clear()
        self._marcos.clear()
        self._botones.clear()
        indice = self._indice_activo
        self._construir()
        if self.instancias:
            self.mostrar(min(indice, len(self.instancias) - 1))

    def pestana_activa(self) -> BaseTab | None:
        if not self.instancias:
            return None
        return self.instancias[self._indice_activo]


def crear_app(root: tk.Tk | None = None, database_path: str | Path | None = None,
              *, pestanias: Sequence[Type[BaseTab]] = PESTANIAS):
    """Crea la app v2 completa (tema + shell) y devuelve (root, shell).

    Aplica la paleta guardada en ui_config.json (clave «paleta»); si no
    hay ninguna o es desconocido, cae al esquema por defecto.

    Antes de montar nada carga el `.env` del proyecto (override=False: lo
    que el usuario exportó en la sesión manda) para que la configuración
    de la IA y del navegador (BRAVE_*) esté disponible desde el arranque.
    """
    configuracion.cargar_env()
    base = Database(database_path) if database_path else Database()
    base.initialize()
    root = root or tk.Tk()
    theme = apply_theme(root, paleta_por_nombre(paleta_actual()), Metrics())
    shell = AppShell(root, Repository(base), theme=theme, pestanias=pestanias)
    return root, shell


def main() -> int:
    root, _shell = crear_app()
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
