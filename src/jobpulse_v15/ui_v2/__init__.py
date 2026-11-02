# -*- coding: utf-8 -*-
"""UI v2 de JobPulse CR: interfaz **plana** (flat) y **modular**.

La UI clásica (`jobpulse_v15.ui`) NO se toca: esta versión vive aparte y
se puede abrir al mismo tiempo.

CÓMO AGREGAR UNA PESTAÑA
-------------------------
1. Crear `ui_v2/tabs/<nombre>.py` con una clase que herede de `BaseTab`:

       class MiPestana(BaseTab):
           key = "mi_pestana"
           title = "Mi pestaña"
           subtitle = "Qué se ve aquí"
           icon = "◆"

           def build(self, parent):
               marco = super().build(parent)
               # ... widgets ...
               return marco

           def on_show(self):
               # se llama cada vez que el usuario abre la pestaña
               pass

2. Registrarla en `PESTANIAS` (en `ui_v2/app.py`).

Nada más: el shell, el tema y los componentes ya están hechos.

REGLAS
------
- Las pestañas no tocan SQLite: usan el store de `ui_v2/data/`.
- Ningún color, fuente o espaciado escrito a mano: todo sale de `theme`.
- Los componentes reutilizables viven en `ui_v2/widgets.py`.
"""
from __future__ import annotations

from jobpulse_v15.ui_v2.app import AppShell, crear_app, main

__all__ = ["AppShell", "crear_app", "main"]
