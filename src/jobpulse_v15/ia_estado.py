# -*- coding: utf-8 -*-
"""Estado del enriquecimiento IA — parte del flujo para determinar éxito/fallo.

Uso (flujo/UI):
    antes = snapshot_enriquecimiento()
    r = await pase_completo()
    despues = snapshot_enriquecimiento()
    veredicto = evaluar_ia(antes, despues, r)   # -> {"estado": ...}

Estados posibles:
    ``completado``  progresó y no quedan huecos recuperables críticos
    ``parcial``     progresó pero quedan huecos (no es fallo)
    ``atascado``    no progresó habiendo trabajo pendiente  -> FALLO
    ``fallido``     ``pase_completo`` devolvió ``error``    -> FALLO
    ``sin_trabajo`` nada que enriquecer (BD limpia o todo lleno)

El criterio de "progresó" es la suma de campos llenados entre dos snapshots,
por eso ``pase_completo`` devuelve stats pero NUNCA se fía solo: la BD manda.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

BD = Path(__file__).resolve().parents[2] / "data" / "jobpulse_v15.db"

# Campos que el pase CRÍTICO debe llenar (city/region/work_mode/date_published)
CRITICOS = {
    "city": "city IS NULL OR TRIM(COALESCE(city,''))=''",
    "region": "region IS NULL OR TRIM(COALESCE(region,''))=''",
    "work_mode": "work_mode IS NULL OR work_mode='unknown'",
    "date_published": "date_published IS NULL",
}
# Campos del pase COMPLETO (secundarios)
SECUNDARIOS = {
    "employment_type": "employment_type IS NULL OR TRIM(COALESCE(employment_type,''))=''",
    "skills": "skills IS NULL OR skills='' OR skills='[]'",
    "languages": "languages IS NULL OR languages='' OR languages='{}'",
    "salary": "salary_min IS NULL AND TRIM(COALESCE(salary_raw,''))<>''",
}
# Descripción basura: la IA no puede extraer nada de eso (no es fallo de la IA)
BASURA = "LENGTH(COALESCE(description_raw,'')) < 200"


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(str(BD))
    con.row_factory = sqlite3.Row
    return con


def _cuenta(con: sqlite3.Connection, where: str) -> int:
    return int(con.execute(f"SELECT COUNT(*) FROM jobs WHERE {where}").fetchone()[0])


def snapshot_enriquecimiento() -> Dict[str, Any]:
    """Estado de los huecos de la BD en este momento.

    Devuelve ``huecos`` (pendientes), ``huecos_recuperables`` (excluyendo
    descripción basura) y ``llenos``/``total`` por familia de campos.
    """
    if not BD.exists():
        return {"existe_bd": False, "total": 0, "huecos": {}, "huecos_recuperables": {}}

    con = _connect()
    try:
        total = int(con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0])
        analizados = int(
            con.execute("SELECT COUNT(*) FROM job_analysis").fetchone()[0]
        )
        requisitos = int(
            con.execute("SELECT COUNT(*) FROM job_requirements").fetchone()[0]
        )

        huecos: Dict[str, int] = {}
        huecos_rec: Dict[str, int] = {}
        for nombre, where in {**CRITICOS, **SECUNDARIOS}.items():
            huecos[nombre] = _cuenta(con, where)
            huecos_rec[nombre] = _cuenta(
                con, f"({where}) AND NOT {BASURA}"
            )

        fam_cr = {k: huecos[k] for k in CRITICOS}
        fam_sec = {k: huecos[k] for k in SECUNDARIOS}
        return {
            "existe_bd": True,
            "ts": time.time(),
            "total": total,
            "analizados": analizados,
            "requisitos": requisitos,
            "huecos": huecos,                       # todos los jobs
            "huecos_recuperables": huecos_rec,      # sin contar desc. basura
            "huecos_criticos": sum(fam_cr.values()),
            "huecos_secundarios": sum(fam_sec.values()),
            "criticos_pendientes_rec": sum(huecos_rec[k] for k in CRITICOS),
            "secundarios_pendientes_rec": sum(huecos_rec[k] for k in SECUNDARIOS),
        }
    finally:
        con.close()


def avance(antes: Mapping[str, Any], despues: Mapping[str, Any]) -> Dict[str, int]:
    """Campos llenados entre dos snapshots (positivo = progresó)."""
    if not antes.get("existe_bd") or not despues.get("existe_bd"):
        return {"campos_llenados": 0, "por_campo": {}}

    por_campo: Dict[str, int] = {}
    for campo in set(antes.get("huecos", {})) | set(despues.get("huecos", {})):
        delta = antes.get("huecos", {}).get(campo, 0) - despues.get("huecos", {}).get(campo, 0)
        if delta > 0:  # solo campos que se LLENARON; una regresión no es avance
            por_campo[campo] = delta
    return {
        "campos_llenados": sum(por_campo.values()),
        "jobs_nuevos": max(0, despues.get("total", 0) - antes.get("total", 0)),
        "por_campo": por_campo,
    }


def evaluar_ia(
    antes: Mapping[str, Any],
    despues: Mapping[str, Any],
    resultado: Optional[Mapping[str, Any]],
    *,
    umbral_progreso: int = 1,
) -> Dict[str, Any]:
    """Determina si el enriquecimiento tuvo éxito, a partir de la BD.

    ``resultado`` es lo que devolvió ``pase_completo()`` (o ``None`` si no
    corrió). La BD es la fuente de verdad: ``resultado`` solo aporta el
    ``error`` explícito y las stats de ciclos.
    """
    resultado = dict(resultado or {})
    av = avance(antes, despues)

    if "error" in resultado:
        estado = "fallido"
        motivo = str(resultado["error"])
    elif not despues.get("existe_bd") or despues.get("total", 0) == 0:
        estado = "sin_trabajo"
        motivo = "No hay jobs en la BD (el scrape no trajo nada)."
    elif av["campos_llenados"] < umbral_progreso:
        pend = despues.get("criticos_pendientes_rec", 0) + despues.get(
            "secundarios_pendientes_rec", 0
        )
        if pend == 0:
            estado = "completado"
            motivo = "No quedaban huecos recuperables; nada que enriquecer."
        else:
            estado = "atascado"
            motivo = (
                f"Sin progreso ({av['campos_llenados']} campos) con "
                f"{pend} huecos recuperables pendientes."
            )
    elif despues.get("criticos_pendientes_rec", 0) == 0:
        estado = "completado"
        motivo = (
            f"Críticos completos; {av['campos_llenados']} campos llenados "
            f"(quedan {despues.get('secundarios_pendientes_rec', 0)} secundarios)."
        )
    else:
        estado = "parcial"
        motivo = (
            f"{av['campos_llenados']} campos llenados pero quedan "
            f"{despues.get('criticos_pendientes_rec', 0)} críticos recuperables."
        )

    return {
        "estado": estado,
        "ok": estado in ("completado", "parcial", "sin_trabajo"),
        "motivo": motivo,
        "avance": av,
        "antes": dict(antes),
        "despues": dict(despues),
        "stats_ia": {
            "ciclos": resultado.get("ciclos"),
            "completo": resultado.get("completo"),
            "error": resultado.get("error"),
        },
    }


def resumen_linea(v: Mapping[str, Any]) -> str:
    """Una línea legible para log/consola."""
    d = v.get("despues", {})
    av = v.get("avance", {})
    icono = {
        "completado": "OK",
        "parcial": "PARCIAL",
        "atascado": "FALLO",
        "fallido": "FALLO",
        "sin_trabajo": "VACIO",
    }.get(v.get("estado", "?"), "?")
    return (
        f"[{icono}] {v.get('estado')}: {v.get('motivo')} "
        f"| jobs={d.get('total', 0)} llenados={av.get('campos_llenados', 0)} "
        f"| críticos_pend={d.get('criticos_pendientes_rec', 0)} "
        f"| secundarios_pend={d.get('secundarios_pendientes_rec', 0)}"
    )


if __name__ == "__main__":
    import json

    sys_out = __import__("sys")
    sys_out.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(snapshot_enriquecimiento(), indent=2, ensure_ascii=False))
