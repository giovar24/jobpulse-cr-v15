"""Pase completo de enriquecimiento IA sobre la BD v1.5.

La orquestación vive en ``jobpulse_v15.ia_enrichment.pase_completo``
(compartida con el botón "Enriquecer" de la UI, O7.3):
1) Pase CRÍTICO (city/region/work_mode/date_published) en ciclos hasta que
   deje de avanzar (los 'unknown' irresolubles no se reintentan eternamente).
2) Pase COMPLETO (incluye secundarios: employment_type, salary, skills,
   languages) para los jobs que les falte algo.

O7.3: el servidor IA local se arranca si hace falta y se APAGA al terminar
(solo el proceso que este script abrió; si ya estaba arriba, no se toca).

Uso: python run_enriquecimiento.py [--solo-criticos]
"""
import asyncio
import sys
import time

from dotenv import load_dotenv

from jobpulse_v15 import ia_enrichment as iae
from jobpulse_v15.ia_servidor import asegurar_servidor


async def main() -> int:
    load_dotenv()
    cliente = iae.get_ia_client()
    if not cliente:
        print("ERROR: IA no configurada (.env)")
        return 1

    servidor = asegurar_servidor(on_log=print)
    if servidor is None:
        print(f"Servidor IA ya arriba: {cliente.base_url} (no se toca)")
    t0 = time.time()
    try:
        r = await iae.pase_completo(
            solo_criticos="--solo-criticos" in sys.argv,
            on_event=print,
        )
    finally:
        if servidor is not None:
            servidor.detener()
            print("Servidor IA detenido (lo abrió este script).")

    if "error" in r:
        print(f"\nABORTADO/ERROR: {r['error']}")
        return 2
    print(f"\nDURACIÓN: {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    sys.exit(asyncio.run(main()))
