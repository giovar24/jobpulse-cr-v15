# -*- coding: utf-8 -*-
"""Pestañas de la UI v2."""
from __future__ import annotations

from jobpulse_v15.ui_v2.tabs.base import BaseTab, TabContext
from jobpulse_v15.ui_v2.tabs.configuracion import ConfiguracionTab
from jobpulse_v15.ui_v2.tabs.crudos import DatosCrudosTab
from jobpulse_v15.ui_v2.tabs.perfil import PerfilTab
from jobpulse_v15.ui_v2.tabs.vacantes import VacantesTab

__all__ = [
    "BaseTab",
    "TabContext",
    "ConfiguracionTab",
    "DatosCrudosTab",
    "PerfilTab",
    "VacantesTab",
]
