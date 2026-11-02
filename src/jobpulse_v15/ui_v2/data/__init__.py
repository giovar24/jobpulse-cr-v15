# -*- coding: utf-8 -*-
"""Capa de datos de la UI v2 (sin Tkinter)."""
from __future__ import annotations

from jobpulse_v15.ui_v2.data.jobs import (
    JobsStore,
    RawDetail,
    RawQuery,
    RawRow,
    exportar_csv,
    idioma_texto,
    recortar,
    resumen_por_campo,
    salario_texto,
    ubicacion_texto,
)
from jobpulse_v15.ui_v2.data.profile import (
    CATEGORIAS,
    ETIQUETAS_CATEGORIA,
    ProfileFact,
    ProfileQuery,
    ProfileResumen,
    ProfileStore,
    etiqueta_categoria,
    fact_desde_sugerencia,
    origen_texto,
)

__all__ = [
    # avisos
    "JobsStore",
    "RawDetail",
    "RawQuery",
    "RawRow",
    "exportar_csv",
    "idioma_texto",
    "recortar",
    "resumen_por_campo",
    "salario_texto",
    "ubicacion_texto",
    # perfil
    "CATEGORIAS",
    "ETIQUETAS_CATEGORIA",
    "ProfileFact",
    "ProfileQuery",
    "ProfileResumen",
    "ProfileStore",
    "etiqueta_categoria",
    "fact_desde_sugerencia",
    "origen_texto",
]
