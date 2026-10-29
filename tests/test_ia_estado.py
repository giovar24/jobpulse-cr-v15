# -*- coding: utf-8 -*-
"""Tests de jobpulse_v15.ia_estado — evaluación éxito/fallo del enriquecimiento."""
from __future__ import annotations

import pytest

from jobpulse_v15 import ia_estado as ie


def _snap(total=100, huecos=None, rec=None, **extra):
    """Snapshot falso para pruebas (no toca la BD)."""
    huecos = dict(huecos or {})
    return {
        "existe_bd": True,
        "ts": 0.0,
        "total": total,
        "analizados": total,
        "requisitos": 0,
        "huecos": huecos,
        "huecos_recuperables": dict(rec if rec is not None else huecos),
        "huecos_criticos": sum(huecos.get(k, 0) for k in ie.CRITICOS),
        "huecos_secundarios": sum(huecos.get(k, 0) for k in ie.SECUNDARIOS),
        "criticos_pendientes_rec": sum(
            (rec if rec is not None else huecos).get(k, 0) for k in ie.CRITICOS
        ),
        "secundarios_pendientes_rec": sum(
            (rec if rec is not None else huecos).get(k, 0) for k in ie.SECUNDARIOS
        ),
        **extra,
    }


class TestAvance:
    def test_cero_si_no_hay_snapshots(self):
        vacio = {"existe_bd": False}
        assert ie.avance(vacio, vacio)["campos_llenados"] == 0

    def test_suma_los_campos_llenados(self):
        antes = _snap(huecos={"city": 10, "skills": 5, "languages": 3})
        despues = _snap(huecos={"city": 4, "skills": 5, "languages": 0})
        av = ie.avance(antes, despues)
        assert av["campos_llenados"] == 6 + 3
        assert av["por_campo"] == {"city": 6, "languages": 3}

    def test_no_cuenta_regresiones_como_avance_negativo_cero(self):
        # Si un campo se "pierde", el delta es negativo y no suma
        antes = _snap(huecos={"city": 0})
        despues = _snap(huecos={"city": 5})
        assert ie.avance(antes, despues)["campos_llenados"] == 0

    def test_jobs_nuevos(self):
        antes = _snap(total=10)
        despues = _snap(total=30)
        assert ie.avance(antes, despues)["jobs_nuevos"] == 20


class TestEvaluar:
    def test_error_del_pase_es_fallido(self):
        antes = _snap(huecos={"city": 5})
        despues = _snap(huecos={"city": 5})
        v = ie.evaluar_ia(antes, despues, {"error": "CRÍTICO ciclo 1: timeout"})
        assert v["estado"] == "fallido"
        assert v["ok"] is False
        assert "timeout" in v["motivo"]

    def test_sin_progreso_con_pendientes_es_atascado(self):
        antes = _snap(huecos={"city": 5})
        despues = _snap(huecos={"city": 5})
        v = ie.evaluar_ia(antes, despues, {"ciclos": [], "completo": None})
        assert v["estado"] == "atascado"
        assert v["ok"] is False

    def test_progreso_y_criticos_llenos_es_completado(self):
        antes = _snap(huecos={"city": 10, "skills": 8})
        despues = _snap(huecos={"city": 0, "skills": 8})
        v = ie.evaluar_ia(antes, despues, {"ciclos": []})
        assert v["estado"] == "completado"
        assert v["ok"] is True
        assert v["avance"]["campos_llenados"] == 10

    def test_progreso_con_criticos_pendientes_es_parcial(self):
        antes = _snap(huecos={"city": 10, "skills": 8})
        despues = _snap(huecos={"city": 4, "skills": 0})
        v = ie.evaluar_ia(antes, despues, {"ciclos": []})
        assert v["estado"] == "parcial"
        assert v["ok"] is True
        assert v["avance"]["campos_llenados"] == 6 + 8

    def test_bd_vacia_es_sin_trabajo(self):
        antes = _snap(total=0, huecos={})
        despues = _snap(total=0, huecos={})
        v = ie.evaluar_ia(antes, despues, None)
        assert v["estado"] == "sin_trabajo"
        assert v["ok"] is True

    def test_huecos_solo_de_basura_no_es_fallo(self):
        # 10 huecos totales pero 0 recuperables (desc. basura) -> completado
        antes = _snap(huecos={"city": 10}, rec={"city": 0})
        despues = _snap(huecos={"city": 10}, rec={"city": 0})
        v = ie.evaluar_ia(antes, despues, {"ciclos": []})
        assert v["estado"] == "completado"
        assert v["ok"] is True

    def test_conserva_stats_ia(self):
        antes = _snap(huecos={"city": 10})
        despues = _snap(huecos={"city": 0})
        stats = {"ciclos": [{"total": 10, "enriched": 5}], "completo": {"total": 3}}
        v = ie.evaluar_ia(antes, despues, stats)
        assert v["stats_ia"]["ciclos"] == stats["ciclos"]
        assert v["stats_ia"]["completo"] == stats["completo"]


class TestResumen:
    def test_iconos_por_estado(self):
        antes = _snap(huecos={"city": 10})
        ok = ie.evaluar_ia(antes, _snap(huecos={"city": 0}), {})
        fallo = ie.evaluar_ia(antes, antes, {"error": "x"})
        assert "[OK]" in ie.resumen_linea(ok)
        assert "[FALLO]" in ie.resumen_linea(fallo)


def test_snapshot_real_no_revienta():
    """El snapshot contra la BD real debe ser válido (corre en cualquier estado)."""
    s = ie.snapshot_enriquecimiento()
    assert "total" in s and "huecos" in s and "huecos_recuperables" in s
    assert isinstance(s["huecos"], dict)
    # Ningún hueco recuperable puede superar al total de huecos
    for campo, n in s["huecos"].items():
        assert s["huecos_recuperables"][campo] <= n, campo
