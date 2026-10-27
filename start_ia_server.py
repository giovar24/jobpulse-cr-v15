# -*- coding: utf-8 -*-
"""Verifica y arranca el servidor IA local (llama.cpp) para v1.5.

Wrapper CLI del paquete: la lógica vive en ``jobpulse_v15.ia_servidor``
(única fuente del comando y del ciclo de vida, O7.3).

Uso:
    python start_ia_server.py          # verifica; si no responde, lo arranca y espera
    python start_ia_server.py --check  # solo verifica (exit 0 ok / 1 apagado)

El launcher ya NO pre-arranca el servidor: la UI lo levanta bajo demanda
(botón "Enriquecer" / pase IA de CV) y lo apaga al terminar. Este script
queda para arranque manual (ia-server.bat) y para sesiones de agente.
"""
import sys

from jobpulse_v15.ia_servidor import asegurar_servidor, servidor_arriba


def main() -> int:
    if servidor_arriba():
        from jobpulse_v15.ia_servidor import _config
        print(f"Servidor IA YA ARRIBA en {_config()[0]}")
        return 0

    if "--check" in sys.argv:
        from jobpulse_v15.ia_servidor import _config
        print(f"Servidor IA APAGADO: {_config()[0]}")
        return 1

    servidor = asegurar_servidor(on_log=print)
    # asegurar_servidor solo devuelve handle si LO ARRANCÓ; con el health ya
    # respondiendo arriba, aqui servidor no es None salvo carrera improbable.
    print("Servidor IA listo (queda corriendo; este script NO lo detiene —")
    print("lo detiene quien lo use bajo demanda: UI o run_enriquecimiento.py).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
