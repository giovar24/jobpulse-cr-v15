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

import queue
import threading
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
        # Hilos: el worker NUNCA toca Tk; mete callbacks en una cola y el
        # vigilante (hilo principal) los ejecuta. Llamar a Tk desde otro
        # hilo no es seguro (y en los tests `root.update()` no cuenta como
        # "main loop"), de ahí el patrón.
        self._cola: queue.Queue = queue.Queue()
        self._hilos_activos = 0

    def build(self, parent: tk.Misc) -> tk.Frame:
        """Crea el contenido de la pestaña y devuelve su marco."""
        marco = tk.Frame(parent, bg=self.theme.color("bg"))
        self.frame = marco
        return marco

    def on_show(self) -> None:
        """Se llama cada vez que la pestaña pasa a ser visible."""

    def refresh(self) -> None:
        """Recarga los datos de la pestaña."""

    # ================================================================
    # Hilos (cola + vigilante en el hilo principal)
    # ================================================================
    def _programar(self, callback) -> None:
        """Encola un callback para el hilo principal (un hilo NUNCA toca Tk)."""
        self._cola.put(callback)

    def _lanzar_hilo(self, funcion) -> None:
        """Arranca un worker y activa el vigilante de la cola."""
        self._hilos_activos += 1

        def envoltorio() -> None:
            try:
                funcion()
            finally:
                self._hilos_activos -= 1
                self._cola.put(None)  # centinela: el worker terminó

        threading.Thread(target=envoltorio, daemon=True).start()
        self._after(60, self._vigilar)

    def _after(self, milisegundos: int, callback) -> None:
        """Programa un callback en el hilo principal (SIEMPRE desde él)."""
        marco = self.frame
        if marco is None:
            return
        try:
            marco.after(milisegundos, callback)
        except tk.TclError:
            pass

    def _vigilar(self) -> None:
        """Vacía la cola y ejecuta los callbacks (hilo principal)."""
        marco = self.frame
        if marco is None:
            return
        try:
            if not marco.winfo_exists():
                return  # la pestaña se destruyó (cambio de esquema)
        except tk.TclError:
            return
        while True:
            try:
                callback = self._cola.get_nowait()
            except queue.Empty:
                break
            if callback is None:
                continue
            try:
                callback()
            except tk.TclError:
                pass
        if self._hilos_activos > 0 or not self._cola.empty():
            self._after(80, self._vigilar)
