# -*- coding: utf-8 -*-
"""Login de ANE en Brave real (CDP 9222) con credenciales guardadas.

Wrapper CLI del paquete (la UI tiene su botón "Re-login ANE", O7.4). La lógica
vive en ``jobpulse_v15.ane_login``; este script solo garantiza Brave con CDP
(lo abre con ``BraveManager`` si hace falta) y lo deja como lo encontró.

O12 · Ola 1.5 — la trampa que esto corrige (verificada 2026-11-05): antes, si
este script tenía que abrir Brave, al terminar lo mataba con
``terminate()``/``kill()``; Chromium **no alcanzaba a volcar las cookies** al
perfil en disco y el barrido siguiente decía "ANE: sin sesión de detalle" con
**0 avisos**. Ahora el cierre es ORDENADO (``Browser.close`` por CDP) y, si se
pide ``--mantener-abierto``, el navegador se queda vivo para raspar de
inmediato sin volver a loguearse.

Las credenciales NUNCA viven en este archivo (regla del proyecto): se leen del
almacén con ``credencial("ANE")`` — keyring de Windows + fallback .env
(ANE_USER/ANE_PASSWORD).

Guardar/actualizar la credencial:
    .\\.venv\\Scripts\\python.exe -m jobpulse_v15 credenciales set --empresa ANE --usuario <u> --password <p>

Uso:
    .\\.venv\\Scripts\\python.exe -X utf8 login_ane.py
    .\\.venv\\Scripts\\python.exe -X utf8 login_ane.py --mantener-abierto   # raspa a continuación
"""
import argparse
import sys
import time

from jobpulse_v15.ane_login import cerrar_brave_ordenado, login_ane
from jobpulse_v15.browser_manager import asegurar_brave, cdp_vivo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Login de ANE sobre Brave (CDP).")
    parser.add_argument("--port", type=int, default=9222,
                        help="puerto CDP (por defecto 9222)")
    parser.add_argument(
        "--mantener-abierto",
        action="store_true",
        help=(
            "no cerrar Brave al terminar: la sesión queda viva para raspear "
            "a continuación (recomendado; es el flujo que evita el "
            "'sin sesión de detalle')"
        ),
    )
    args = parser.parse_args(argv)

    mgr = asegurar_brave(args.port)
    lo_abrimos = mgr is not None
    resultado = {"estado": "error", "detalle": "no se intentó el login"}
    try:
        if lo_abrimos:
            print("Brave abierto para el login.")
        resultado = login_ane(args.port)
    finally:
        if lo_abrimos:
            if args.mantener_abierto:
                print(
                    "Brave queda ABIERTO (--mantener-abierto): raspa ahora sin "
                    "volver a loguearte."
                )
            else:
                # Cierre ordenado: Chromium vuelca las cookies al perfil. Con
                # terminate()/kill() la sesión NO persistía.
                tiempo = 3.0 if resultado.get("estado") == "ok" else 0.0
                if tiempo:
                    time.sleep(tiempo)
                if cerrar_brave_ordenado(args.port):
                    print("Brave cerrado de forma ordenada (sesión persistida).")
                    # Margen para que el proceso salga solo y libere el puerto.
                    for _ in range(20):
                        if not cdp_vivo(args.port, timeout=0.2):
                            break
                        time.sleep(0.25)
                else:
                    mgr.stop_brave_sync()
                    print("Brave cerrado por proceso (no respondió a Browser.close).")

    estado = resultado["estado"]
    print(f"LOGIN ANE: {estado.upper()} — {resultado['detalle']}")
    if estado == "ok" and args.mantener_abierto:
        print("Siguiente paso: -m jobpulse_v15 scrape ane --site ane-cr")
    return 0 if estado == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
