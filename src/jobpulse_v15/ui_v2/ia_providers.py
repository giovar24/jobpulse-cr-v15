# -*- coding: utf-8 -*-
"""Adaptador de los proveedores de IA para la UI v2.

La FUENTE UNICA de los presets es ``jobpulse_v15.ia_api.PRESETS`` (la usan
el cliente, la CLI y las dos UIs). Este módulo solo adapta ese diccionario a
la forma que necesita la UI v2 (nombre / base_url / modelo por defecto), de
modo que la UI no dependa de la ventana de configuracion de la version
anterior de la interfaz.

Los presets:
  - ``ollama``       -> Ollama Cloud   (https://ollama.com/v1, cuenta gratis)
  - ``ollama-local`` -> Ollama local    (http://localhost:11434/v1)
  - ``lmstudio``     -> LM Studio local (http://localhost:1234/v1)
  - mas ``openrouter``, ``nvidia``, ``google`` y ``custom``.

El ``base_url`` y el modelo siempre se pueden sobreescribir a mano (campo
Custom).
"""
from __future__ import annotations

from typing import Any, Dict

from jobpulse_v15.ia_api import PRESETS


def proveedores_ia() -> Dict[str, Dict[str, str]]:
    """Los proveedores de IA disponibles, en la forma que usa la UI v2."""
    return {
        clave: {
            "nombre": preset.nombre,
            "base_url": preset.base_url,
            "modelo_def": preset.modelo_default,
        }
        for clave, preset in PRESETS.items()
    }


#: Tabla de proveedores (mismo nombre que usaba la ventana de la UI
#: anterior, para no cambiar el codigo de la pestana de Configuracion).
IA_PROVIDERS: Dict[str, Dict[str, Any]] = proveedores_ia()
