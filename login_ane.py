# -*- coding: utf-8 -*-
"""Login de ANE en Brave real (CDP 9222) con credenciales guardadas.

Wrapper CLI del paquete (la UI tiene su botón "Re-login ANE", O7.4). La lógica
vive en ``jobpulse_v15.ane_login``; este script solo garantiza Brave con CDP
(lo abre con ``BraveManager`` si hace falta y lo cierra si lo abrió él).

Las credenciales NUNCA viven en este archivo (regla del proyecto): se leen del
almacén con ``credencial("ANE")`` — keyring de Windows + fallback .env
(ANE_USER/ANE_PASSWORD).

Guardar/actualizar la credencial:
    .\.venv\Scripts\python.exe -m jobpulse_v15 credenciales set --empresa ANE --usuario <u> --password <p>
"""
import sys
import time

from jobpulse_v15.ane_login import login_ane
from jobpulse_v15.browser_manager import asegurar_brave


def main() -> int:
    mgr = asegurar_brave(9222)
    try:
        if mgr is not None:
            print("Brave abierto para el login (se cerrará al terminar).")
        resultado = login_ane(9222)
        if resultado["estado"] == "ok":
            # Margen para que Chromium persista la cookie de sesión ANE en el
            # perfil antes de un cierre forzado del proceso.
            time.sleep(3)
    finally:
        if mgr is not None:
            mgr.stop_brave_sync()
            print("Brave cerrado (lo abrió este script).")

    estado = resultado["estado"]
    print(f"LOGIN ANE: {estado.upper()} — {resultado['detalle']}")
    return 0 if estado == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
