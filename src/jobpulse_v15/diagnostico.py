# -*- coding: utf-8 -*-
"""Diagnóstico del sistema: integridad de la BD, calidad de los datos y
huecos del enriquecimiento (SIN Tk).

Reúne en un solo informe las tres preguntas que siempre se hacen:

1. **¿La BD está sana?** → `Database.check_integrity()` (PRAGMA
   integrity_check + foreign_key_check + versión del esquema).
2. **¿Qué le falta a los avisos?** → `ia_estado.snapshot_enriquecimiento()`
   (los huecos que el pase IA podría rellenar).
3. **¿Qué calidad tienen los datos?** →
   `Repository.get_data_quality_summary()` (empresa/país/ubicación/analysis).

El informe es de **solo lectura**: no modifica nada. La UI lo pinta en una
tarjeta de Configuración (el diagnóstico corre en un hilo: la BD real tiene
535 avisos y las consultas no son instantáneas).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jobpulse_v15.repository import Repository


@dataclass(frozen=True)
class ReporteDiagnostico:
    """Resultado del diagnóstico (todo de solo lectura)."""

    ok: bool = True
    base: str = ""
    esquema: int = 0
    integridad: str = ""
    fk: int = 0
    total_jobs: int = 0
    analizados: int = 0
    requisitos: int = 0
    huecos_criticos: int = 0
    huecos_criticos_recuperables: int = 0
    huecos_secundarios: int = 0
    calidad: dict[str, int] = field(default_factory=dict)
    error: str = ""

    # -- vista -------------------------------------------------------
    @property
    def estado_integridad(self) -> str:
        """Texto corto del estado de la BD."""
        if self.error:
            return f"Error: {self.error}"
        if self.integridad == "ok" and self.fk == 0:
            return "BD sana (integridad y claves foráneas correctas)"
        if self.integridad != "ok":
            return f"Integridad: {self.integridad}"
        return f"{self.fk} violate(s) de clave foránea"

    def lineas(self) -> list[str]:
        """Informe en líneas (para el panel de texto de la UI)."""
        if self.error:
            return [f"NO SE PUDO DIAGNOSTICAR: {self.error}"]
        lineas = [
            f"Base de datos: {self.base}",
            f"Versión del esquema: {self.esquema}",
            f"Integridad: {self.integridad}",
            f"Claves foráneas rotas: {self.fk}",
            "",
            f"Avisos: {self.total_jobs}",
            f"Análisis: {self.analizados}  ·  requisitos: {self.requisitos}",
            f"Huecos críticos: {self.huecos_criticos} "
            f"(recuperables por la IA: {self.huecos_criticos_recuperables})",
            f"Huecos secundarios: {self.huecos_secundarios}",
            "",
            "Calidad de los datos:",
        ]
        for clave, valor in self.calidad.items():
            lineas.append(f"  · {clave.replace('_', ' ')}: {valor}")
        lineas.append("")
        lineas.append("Todo: OK" if self.ok else "Revisar los puntos anteriores")
        return lineas

    def texto(self) -> str:
        """El informe completo como texto."""
        return "\n".join(self.lineas())


def diagnostico(repository: Repository) -> ReporteDiagnostico:
    """Reúne el informe de diagnóstico de la BD que usa ``repository``."""
    from jobpulse_v15 import ia_estado

    base = Path(repository.database.path)
    try:
        integridad = repository.database.check_integrity()
    except Exception as exc:  # noqa: BLE001 - el informe lo reporta
        return ReporteDiagnostico(ok=False, base=str(base), error=str(exc))

    try:
        snapshot = ia_estado.snapshot_enriquecimiento(base)
    except Exception as exc:  # noqa: BLE001
        snapshot = {"existe_bd": False, "total": 0, "analizados": 0,
                    "requisitos": 0, "huecos_criticos": 0,
                    "criticos_pendientes_rec": 0,
                    "huecos_secundarios": 0}

    try:
        calidad = dict(repository.get_data_quality_summary())
    except Exception as exc:  # noqa: BLE001
        calidad = {"error_calidad": str(exc)}

    resultados = list(integridad.get("integrity_check") or [])
    texto_integridad = resultados[0] if resultados else "desconocido"
    fk = len(integridad.get("foreign_key_violations") or [])
    return ReporteDiagnostico(
        ok=bool(integridad.get("ok")),
        base=str(integridad.get("database") or base),
        esquema=int(integridad.get("schema_version") or 0),
        integridad=str(texto_integridad),
        fk=fk,
        total_jobs=int(snapshot.get("total") or 0),
        analizados=int(snapshot.get("analizados") or 0),
        requisitos=int(snapshot.get("requisitos") or 0),
        huecos_criticos=int(snapshot.get("huecos_criticos") or 0),
        huecos_criticos_recuperables=int(snapshot.get("criticos_pendientes_rec") or 0),
        huecos_secundarios=int(snapshot.get("huecos_secundarios") or 0),
        calidad=calidad,
    )


def resumen_corto(repository: Repository) -> dict[str, Any]:
    """Resumen en dict (para las métricas de la UI)."""
    reporte = diagnostico(repository)
    return {
        "ok": reporte.ok,
        "estado": reporte.estado_integridad,
        "total_jobs": reporte.total_jobs,
        "analizados": reporte.analizados,
        "huecos_criticos": reporte.huecos_criticos,
        "huecos_secundarios": reporte.huecos_secundarios,
        "esquema": reporte.esquema,
    }
