# -*- coding: utf-8 -*-
"""Contrato de las pestañas de la UI v2.

Una pestaña es una clase con `key`, `title`, `subtitle` y dos métodos:
`build(parent)` (crea sus widgets) y `on_show()` (se llama cada vez que el
usuario la abre). El shell (`app.py`) no sabe nada del contenido de la
pestaña: solo la monta, la muestra y le pide que se refresque.

PARA AGREGAR UNA PESTAÑA NUEVA
-------------------------------
1. Crear `ui_v2/tabs/<nombre>.py` con una clase que herede de `BaseTab`.
2. Registrarla en la lista `PESTANIAS` de `ui_v2/app.py`.
Nada más: no hay que tocar el shell, el tema ni los componentes.
"""
from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass, field
from typing import Any

from jobpulse_v15.repository import Repository
from jobpulse_v15.ui_v2.theme import Theme


@dataclass
class TabContext:
    """Lo que una pestaña puede necesitar del shell."""

    repository: Repository
    theme: Theme
    services: dict[str, Any] = field(default_factory=dict)


class BaseTab:
    """Base de todas las pestañas."""

    key: str = ""
    title: str = ""
    subtitle: str = ""
    icon: str = "•"

    def __init__(self, context: TabContext) -> None:
        self.context = context
        self.theme = context.theme
        self.frame: tk.Frame | None = None

    def build(self, parent: tk.Misc) -> tk.Frame:
        """Crea el contenido de la pestaña y devuelve su marco."""
        marco = tk.Frame(parent, bg=self.theme.color("bg"))
        self.frame = marco
        return marco

    def on_show(self) -> None:
        """Se llama cada vez que la pestaña pasa a ser visible."""

    def refresh(self) -> None:
        """Recarga los datos de la pestaña."""
