# -*- coding: utf-8 -*-
"""Retención y vigencia de las vacantes (O8/O10) — SIN Tk.

Dos cosas que viven en el MISMO archivo de preferencias del sistema
(`~/.jobpulse_v15/ui_config.json`, el que también usa la UI clásica):

- **Retención** (`retencion_puestos_meses`): ventana de meses que define
  qué sigue siendo "vigente" (1, 2, 3, 6 o 12). La usa
  `Repository.search_jobs(solo_vigentes=True, ventana_retencion_meses=...)`.
- **Solo vigentes** (`solo_vigentes`): si la UI oculta los avisos
  vencidos/pasados de ventana. **Oculta, nunca borra** (regla O8).

REGLA: la UI v2 y la clásica comparten este archivo. Todo se escribe con
**cargar → update → guardar** (`configuracion.guardar()` lo hace así:
sobrescribir el dict completo perdería las claves ajenas — gotcha del
handoff). Los meses permitidos y el cálculo del corte son los de
`ciclo_vida` (la única verdad del dominio O8).
"""
from __future__ import annotations

from dataclasses import dataclass

from jobpulse_v15 import ciclo_vida
from jobpulse_v15.ui_v2 import configuracion

# Clave de la preferencia "solo vigentes" (en `ui_config.json`).
CLAVE_SOLO_VIGENTES = "solo_vigentes"

# Por defecto se ocultan los avisos vencidos: es lo que hace la UI clásica
# (`ui.py`: `solo_vigentes=True`) y lo que espera la regla O8.
DEFAULT_SOLO_VIGENTES = True


@dataclass(frozen=True)
class Retencion:
    """La política de retención/vigencia vigente."""

    meses: int
    ventana_republicaciones: int
    solo_vigentes: bool
    corte: str

    @property
    def texto_corte(self) -> str:
        """El corte en palabras ('vigentes desde el 2026-05-06')."""
        return f"vigentes desde el {self.corte}"


class RetencionStore:
    """Lee y guarda la política de retención (sin Tk)."""

    # -- lectura --
    def retencion(self) -> Retencion:
        """La política vigente (con valores por defecto si falta algo)."""
        datos = configuracion.cargar()
        meses = self._meses_validos(
            datos.get(ciclo_vida.CLAVE_RETENCION_PUESTOS))
        ventana = self._meses_validos(
            datos.get(ciclo_vida.CLAVE_VENTANA_REPUBLICACIONES),
            ciclo_vida.DEFAULT_VENTANA_REPUBLICACIONES)
        try:
            corte = ciclo_vida.corte_de_retencion(meses)
        except ValueError:  # pragma: no cover - los meses ya están validados
            corte = ciclo_vida.corte_de_retencion(
                ciclo_vida.DEFAULT_RETENCION_PUESTOS)
        return Retencion(
            meses=meses,
            ventana_republicaciones=ventana,
            solo_vigentes=self.solo_vigentes(datos),
            corte=corte,
        )

    def solo_vigentes(self, datos: dict | None = None) -> bool:
        """¿La UI oculta los avisos vencidos?"""
        if datos is None:
            datos = configuracion.cargar()
        valor = datos.get(CLAVE_SOLO_VIGENTES)
        if valor is None:
            return DEFAULT_SOLO_VIGENTES
        return bool(valor)

    # -- escritura --
    def guardar_meses(self, meses: int) -> Retencion:
        """Guarda la ventana de retención (conserva la de republicaciones)."""
        valor = int(meses)
        if valor not in ciclo_vida.MESES_PERMITIDOS:
            raise ValueError(
                "La retención debe ser uno de: "
                + ", ".join(str(m) for m in ciclo_vida.MESES_PERMITIDOS)
                + " meses.")
        configuracion.guardar({ciclo_vida.CLAVE_RETENCION_PUESTOS: valor})
        return self.retencion()

    def guardar_solo_vigentes(self, valor: bool) -> bool:
        """Guarda la preferencia "solo vacantes vigentes"."""
        configuracion.guardar({CLAVE_SOLO_VIGENTES: bool(valor)})
        return bool(valor)

    # -- ayuda para las consultas --
    def ventana_consulta(self) -> tuple[bool, int | None]:
        """``(solo_vigentes, ventana_retencion_meses)`` para `search_jobs`."""
        retencion = self.retencion()
        return retencion.solo_vigentes, retencion.meses

    # -- interno --
    @staticmethod
    def _meses_validos(valor: object,
                        defecto: int = ciclo_vida.DEFAULT_RETENCION_PUESTOS
                        ) -> int:
        """Meses permitidos; un valor inválido cae al defecto."""
        try:
            meses = int(valor)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return defecto
        return meses if meses in ciclo_vida.MESES_PERMITIDOS else defecto
