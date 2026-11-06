"""Pase completo de enriquecimiento IA sobre la BD v1.5.

La orquestación vive en ``jobpulse_v15.ia_enrichment.pase_completo``
(compartida con el botón "Enriquecer" de la UI, O7.3):
1) Pase CRÍTICO (city/region/work_mode/date_published) en ciclos hasta que
   deje de avanzar (los 'unknown' irresolubles no se reintentan eternamente).
2) Pase COMPLETO (incluye secundarios: employment_type, salary, skills,
   languages) para los jobs que les falte algo.

O7.3: el servidor IA local se arranca si hace falta y se APAGA al terminar
(solo el proceso que este script abrió; si ya estaba arriba, no se toca).
Si la IA configurada es EXTERNA (Ollama Cloud, OpenRouter, Gemini, LM Studio
remoto…) no hay nada local que arrancar: se usa el endpoint del proveedor y
el script AVISA de que el texto de los avisos sale de la máquina.

Tope de avisos: OPT-IN y ajustable con IA_MAX_VACANTES (.env). Sin esa
variable no hay tope: se procesa todo lo pendiente.

Uso: python run_enriquecimiento.py [--solo-criticos] [--confirmar-externo]
"""
import asyncio
import sys
import time

from dotenv import load_dotenv

from jobpulse_v15 import ia_enrichment as iae
from jobpulse_v15.ia_servidor import asegurar_servidor


def _confirmar_externo(aviso: str) -> bool:
    """Pide confirmación antes de enviar texto de avisos a un proveedor externo.

    ``--confirmar-externo`` omite la pregunta (corridas no interactivas).
    """
    print(f"AVISO: {aviso}")
    if "--confirmar-externo" in sys.argv:
        print("Confirmado por --confirmar-externo.")
        return True
    try:
        respuesta = input(
            "¿Continuar enviando el texto de los avisos a este proveedor? [s/N] "
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return respuesta in ("s", "si", "sí", "y", "yes")


async def main() -> int:
    load_dotenv()
    cliente = iae.get_ia_client()
    if not cliente:
        print("ERROR: IA no configurada (.env)")
        return 1

    aviso = iae.aviso_privacidad(cliente)
    if aviso and not _confirmar_externo(aviso):
        print("Cancelado: no se envió nada al proveedor externo.")
        return 3

    tope = iae.tope_vacantes()
    print(
        "Tope de avisos por corrida: "
        + (str(tope) if tope else "sin tope (todo lo pendiente)")
    )

    servidor = asegurar_servidor(on_log=print)
    if servidor is None:
        if getattr(cliente, "es_local", False):
            print(f"Servidor IA ya arriba: {cliente.base_url} (no se toca)")
        else:
            print(
                f"Proveedor IA externo: {cliente.base_url} "
                "(no hay servidor local que arrancar)"
            )
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
    # Los campos estructurados que la IA acaba de llenar (skills/languages)
    # solo son requisitos comparables si el aviso se re-analiza (O12 · 1.1).
    # Es idempotente: la segunda vez no hay nada que hacer.
    print("\n=== RE-ANALISIS CON LOS CAMPOS DE LA IA ===")
    iae.reananalizar_tras_ia(on_event=print)
    print(f"\nDURACIÓN: {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    sys.exit(asyncio.run(main()))
