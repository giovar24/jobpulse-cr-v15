# -*- coding: utf-8 -*-
"""Los adaptadores no pueden meter ``asyncio.run`` dentro de un ``async def``.

Bug real (2026-10-31): ``ElempleoFetcher.fetch`` era ``async def`` pero
terminaba en ``return asyncio.run(_run())``. El caller envuelve la corrutina
con ``asyncio.run`` (IngestionService), asi que al entrar en ``fetch`` ya
habia un loop corriendo y ``asyncio.run`` reventaba con
"asyncio.run() cannot be called from a running event loop".

Los fetchers SYNC (ane, browser_sites) si pueden usar ``asyncio.run``: ahi
crean el loop desde cero, que es justo lo que quieren.
"""
import ast
import unittest
from pathlib import Path

from jobpulse_v15.ane import AneFetcher
from jobpulse_v15.cinde import CindeFetcher
from jobpulse_v15.elempleo import ElempleoFetcher
from jobpulse_v15.harvie import HarvieFetcher
from jobpulse_v15.indeed import IndeedFetcher
from jobpulse_v15.linkedin import LinkedInFetcher
from jobpulse_v15.procomer import ProcomerFetcher

RAIZ = Path(__file__).resolve().parents[1] / "src" / "jobpulse_v15"

ADAPTADORES = [
    AneFetcher, CindeFetcher, ElempleoFetcher, HarvieFetcher,
    IndeedFetcher, LinkedInFetcher, ProcomerFetcher,
]


def _calls_asyncio_run(dentro_de_async: bool):
    """Devuelve las rutas de archivo donde ``asyncio.run`` se usa mal."""
    hallazgos = []
    for archivo in RAIZ.rglob("*.py"):
        try:
            arbol = ast.parse(archivo.read_text(encoding="utf-8"), str(archivo))
        except (OSError, SyntaxError):
            continue
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, (ast.AsyncFunctionDef, ast.FunctionDef)):
                continue
            es_async = isinstance(nodo, ast.AsyncFunctionDef)
            if es_async != dentro_de_async:
                continue
            for hijo in ast.walk(nodo):
                if (
                    isinstance(hijo, ast.Call)
                    and isinstance(hijo.func, ast.Attribute)
                    and hijo.func.attr == "run"
                    and isinstance(hijo.func.value, ast.Name)
                    and hijo.func.value.id == "asyncio"
                ):
                    hallazgos.append(f"{archivo.name}:{nodo.lineno} ({nodo.name})")
    return hallazgos


class TestAdaptadoresAsync(unittest.TestCase):
    def test_ningun_async_def_usa_asyncio_run(self):
        hallazgos = _calls_asyncio_run(dentro_de_async=True)
        self.assertEqual(
            hallazgos, [],
            "asyncio.run() dentro de un async def (doble envoltura): "
            + ", ".join(hallazgos),
        )

    def test_los_sync_si_pueden_usar_asyncio_run(self):
        # ane y providers/login/browser_sites son sync: usan asyncio.run a
        # proposito. Este test documenta que la regla NO se aplica a ellos.
        hallazgos = _calls_asyncio_run(dentro_de_async=False)
        self.assertTrue(
            any("ane.py" in h for h in hallazgos),
            "ane.py deberia seguir usando asyncio.run (fetch es sync)",
        )

    def test_cual_es_async_y_cual_no(self):
        esperados_async = {
            CindeFetcher, ElempleoFetcher, IndeedFetcher, LinkedInFetcher,
            ProcomerFetcher,
        }
        for clase in ADAPTADORES:
            with self.subTest(clase=clase.__name__):
                es_async = asyncio_is_coroutine(clase.fetch)
                self.assertEqual(es_async, clase in esperados_async)


def asyncio_is_coroutine(funcion) -> bool:
    import asyncio
    return asyncio.iscoroutinefunction(funcion)


if __name__ == "__main__":
    unittest.main()
