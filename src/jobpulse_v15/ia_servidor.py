# -*- coding: utf-8 -*-
"""Ciclo de vida del servidor IA local (llama.cpp) — única fuente del comando.

Política O7.3 (acordada 2026-10-27): el servidor se arranca SOLO cuando se
necesita (enriquecimiento, pase IA de CV) y se apaga al terminar. "Apagar"
significa: solo se detiene el proceso que ESTE módulo arrancó. Si el servidor
ya estaba arriba (usuario, launcher), ``asegurar_servidor()`` devuelve None y
nadie lo toca.

Uso típico (UI/scripts):

    from jobpulse_v15.ia_servidor import asegurar_servidor

    servidor = asegurar_servidor()      # None = ya estaba arriba
    try:
        ...                              # enriquecer / pase IA de CV
    finally:
        if servidor:
            servidor.detener()

Equivalentes CLI (raíz del repo):
    python start_ia_server.py            # verifica; si no responde, arranca
    python start_ia_server.py --check     # solo verifica (exit 1 si apagado)

Servidor EXTERNO: si IA_BASE_URL no es 127.0.0.1/localhost, jamás se intenta
arrancar nada local — solo se reporta si responde o no.
"""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Callable, Optional

import httpx
from dotenv import load_dotenv

from jobpulse_v15.instalacion_ia import modelo_dir, ruta_llama_server

# Raíz del repo (src/jobpulse_v15/ia_servidor.py -> parents[2] = raíz).
RAIZ = Path(__file__).resolve().parents[2]


def _config() -> tuple[str, bool, str]:
    """(base_url, es_local, puerto) según .env/env — se lee en cada llamada."""
    load_dotenv(RAIZ / ".env")
    base_url = (os.getenv("IA_BASE_URL") or "http://127.0.0.1:8081/v1").rstrip("/")
    es_local = "127.0.0.1" in base_url or "localhost" in base_url
    if ":" in base_url.split("/")[-2]:
        puerto = base_url.split("/")[-2].split(":")[-1]
    else:
        puerto = "8081"
    return base_url, es_local, puerto


def _log_path() -> Path:
    ruta = RAIZ / "data" / "ia_server.log"
    ruta.parent.mkdir(exist_ok=True)
    return ruta


def comando_llama() -> list[str]:
    """Comando completo del llama-server (Gemma 4 E2B QAT, --metrics activo)."""
    modelo = modelo_dir()
    _, _, puerto = _config()
    return [
        str(ruta_llama_server()),
        "-m", rf"{modelo}\gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf",
        "--mmproj", rf"{modelo}\mmproj-BF16.gguf",
        "--model-draft", rf"{modelo}\mtp-gemma-4-E2B-it-Q4_0.gguf",
        "--spec-type", "draft-mtp", "--spec-draft-n-max", "2", "--spec-draft-ngl", "all",
        "--alias", "gemma4-e2b-qat",
        "--port", puerto,
        "--host", "127.0.0.1",
        "--gpu-layers", "all", "--flash-attn", "on",
        "--cache-type-k", "q8_0", "--cache-type-v", "q8_0", "--kv-unified",
        "--ctx-size", "8192", "--parallel", "1",
        "--threads", "4", "--threads-batch", "8",
        "--jinja", "--chat-template-kwargs", '{"enable_thinking":false}',
        "--temp", "1.0", "--top-p", "0.95", "--top-k", "64", "--min-p", "0.0",
        "--metrics", "--log-verbosity", "3",
    ]


def servidor_arriba(timeout: float = 3.0) -> bool:
    """True si ``/health`` del servidor IA responde."""
    base_url, _, _ = _config()
    health_url = base_url.rsplit("/", 1)[0] if "/v1" in base_url else base_url
    try:
        r = httpx.get(f"{health_url}/health", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def _esperar(
    intentos: int = 180, on_log: Optional[Callable[[str], None]] = None
) -> bool:
    """Espera a que el servidor responda (1 intento/segundo)."""
    for i in range(intentos):
        if servidor_arriba():
            return True
        if on_log and i and i % 30 == 0:
            on_log(f"  ... esperando al modelo ({i}s)...")
        time.sleep(1.0)
    return False


class ServidorIA:
    """Handle del proceso llama-server que ESTE módulo arrancó."""

    def __init__(self, process: "subprocess.Popen[bytes]") -> None:
        self._process = process
        self.base_url, _, self.puerto = _config()

    def detener(self) -> None:
        """Termina el proceso arrancado por este módulo (idempotente)."""
        if self._process is None:
            return
        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
        self._process = None


def arrancar_servidor(
    on_log: Optional[Callable[[str], None]] = None,
    espera_s: int = 180,
) -> ServidorIA:
    """Arranca llama-server detached y espera a que responda ``/health``.

    Lanza RuntimeError si no se puede (llama-server ausente, servidor externo
    caído o el modelo no carga a tiempo) — nunca devuelve un servidor a medias.
    """
    base_url, es_local, puerto = _config()
    if not es_local:
        raise RuntimeError(
            f"Servidor EXTERNO {base_url} no responde. Verifica IA_BASE_URL "
            "en .env y que el servicio esté corriendo."
        )
    cmd = comando_llama()
    llama = Path(cmd[0])
    if not llama.exists():
        raise RuntimeError(
            f"No se encuentra llama-server: {llama}. Ejecuta instalar-modelo-ia.bat "
            "o define IA_LLAMA_SERVER en .env."
        )
    if on_log:
        on_log(f"Arrancando llama-server en puerto {puerto} (carga el modelo)...")
    with open(_log_path(), "ab") as log:
        # DETACHED: el proceso sigue vivo aunque el caller (UI) se cierre.
        process = subprocess.Popen(
            cmd,
            stdout=log,
            stderr=subprocess.STDOUT,
            cwd=str(llama.parent),
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    if not _esperar(espera_s, on_log):
        process.terminate()
        raise RuntimeError(
            f"El servidor IA no respondió en {espera_s}s — revisa {_log_path()}"
        )
    if on_log:
        on_log(f"Servidor IA arriba ({base_url}) — log: {_log_path()}")
    return ServidorIA(process)


def asegurar_servidor(
    on_log: Optional[Callable[[str], None]] = None,
) -> Optional[ServidorIA]:
    """Devuelve ``ServidorIA`` si esta función lo arrancó; ``None`` si ya estaba arriba.

    El caller SOLO debe detener lo que reciba (política O7.3: el servidor
    preexistente del usuario nunca se toca).
    """
    if servidor_arriba():
        return None
    return arrancar_servidor(on_log=on_log)
