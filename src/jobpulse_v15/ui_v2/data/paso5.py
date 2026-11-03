# -*- coding: utf-8 -*-
"""Capa de datos del Paso 5 (matching persistido) para la UI v2 — SIN Tk.

Hasta ahora la UI **no persistía** el Paso 5: el ranking ATS se calculaba en
memoria y los estados del matching solo se veían si alguien corría
`run_paso5.py` por CLI. Con este store la UI puede lanzar la corrida y dejar
la corrida **guardada** en `job_match` (misma regla que el CLI: cada corrida
es NUEVA —nunca se actualiza una corrida emitida— y las anteriores quedan
con `valida = 0`).

El worker corre en un hilo: por eso el store abre **su propia conexión**
(`sqlite3.Row` es obligatorio: `matching` indexa las filas por nombre de
columna).
"""
from __future__ import annotations

import sqlite3
from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable

from jobpulse_v15.repository import Repository


@dataclass(frozen=True)
class ResumenPaso5:
    """Resultado de una corrida del Paso 5."""

    corrida_id: str
    evaluadas: int
    conteo: tuple[tuple[str, str, int], ...] = ()

    @property
    def por_estado(self) -> dict[str, int]:
        """Totales por estado (compatible, ajustado, sin_requisitos…)."""
        totales: dict[str, int] = {}
        for estado, _motivo, n in self.conteo:
            totales[estado] = totales.get(estado, 0) + n
        return totales

    def texto(self, maximo: int = 20) -> str:
        """Resumen legible (estado | motivo | n), como el del CLI."""
        if not self.conteo:
            return "Sin evaluables: ningún aviso tiene análisis vigente."
        lineas = [
            f"{estado:<22} | {motivo:<32} | {n}"
            for estado, motivo, n in self.conteo[:maximo]
        ]
        if len(self.conteo) > maximo:
            lineas.append(f"… y {len(self.conteo) - maximo} combinación(es) más")
        return "\n".join(lineas)


class Paso5Store:
    """Ejecuta y consulta las corridas del matching (Paso 5)."""

    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    # -- consultas --
    def corrida_vigente(self) -> str:
        """Identificador de la corrida vigente ("" si no hay ninguna)."""
        with self.repository.database.connection() as connection:
            fila = connection.execute(
                "SELECT DISTINCT corrida_id FROM job_match WHERE valida = 1 "
                "ORDER BY corrida_id DESC LIMIT 1"
            ).fetchone()
        return str(fila["corrida_id"]) if fila is not None else ""

    def estado_vigente(self) -> dict[str, str]:
        """job_id -> estado de la corrida vigente."""
        with self.repository.database.connection() as connection:
            corrida = connection.execute(
                "SELECT DISTINCT corrida_id FROM job_match WHERE valida = 1 "
                "ORDER BY corrida_id DESC LIMIT 1"
            ).fetchone()
            if corrida is None:
                return {}
            filas = connection.execute(
                "SELECT job_id, estado FROM job_match "
                "WHERE valida = 1 AND corrida_id = ?",
                (corrida["corrida_id"],),
            ).fetchall()
        return {str(f["job_id"]): str(f["estado"] or "") for f in filas}

    # -- ejecución --
    def ejecutar(
        self,
        *,
        aplicar_filtro_areas: bool = True,
        progreso: Callable[[str], None] | None = None,
    ) -> ResumenPaso5:
        """Corre el Paso 5 y **persiste** la corrida en `job_match`.

        ``aplicar_filtro_areas=False`` = "evaluar todo" (ignora las áreas
        marcadas en el perfil), igual que ``run_paso5.py --evaluar-todo``.
        """
        from jobpulse_v15 import matching

        ruta = self.repository.database.path
        # Conexión PROPIA (el worker corre en un hilo y `matching` necesita
        # `sqlite3.Row`).
        connection = sqlite3.connect(ruta, timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            if progreso:
                progreso("Evaluando los requisitos contra el perfil…")
            corrida, resultados = matching.ejecutar_paso5(
                connection,
                invalidar_previas=True,
                aplicar_filtro_areas=aplicar_filtro_areas,
            )
        finally:
            connection.close()
        if progreso:
            progreso(f"Corrida {corrida} guardada ({len(resultados)} evaluadas).")
        conteo = Counter((r.estado, r.motivo) for r in resultados)
        return ResumenPaso5(
            corrida_id=corrida,
            evaluadas=len(resultados),
            conteo=tuple(
                (estado, motivo, n)
                for (estado, motivo), n in sorted(conteo.items())
            ),
        )

    def resumen_de_corrida(self, corrida_id: str) -> dict[str, Any]:
        """Conteos por estado de una corrida concreta (para el histórico)."""
        with self.repository.database.connection() as connection:
            filas = connection.execute(
                "SELECT estado, COUNT(*) AS n FROM job_match "
                "WHERE corrida_id = ? GROUP BY estado",
                (corrida_id,),
            ).fetchall()
        return {str(f["estado"]): int(f["n"]) for f in filas}
