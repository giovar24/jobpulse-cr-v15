# -*- coding: utf-8 -*-
"""Tests del ciclo de vida del servidor IA (O7.3) con health stub.

Sin modelo real: un http.server responde /health para simular "arriba";
puertos muertos simulan "apagado". Nunca se llama a arrancar_servidor con
llama-server real."""
import http.server
import os
import socket
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from jobpulse_v15 import ia_servidor as ias


class _HealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


class _StubServidor:
    """Servidor /health en un puerto efímero."""

    def __init__(self):
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _HealthHandler)
        self.puerto = self.httpd.server_address[1]
        self.hilo = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.hilo.start()

    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.puerto}/v1"

    def detener(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class _ProcFake:
    def __init__(self):
        self.vivo = True

    def poll(self):
        return None if self.vivo else 0

    def terminate(self):
        self.vivo = False

    def kill(self):
        self.vivo = False

    def wait(self, timeout=None):
        return None


class TestServidorArriba(unittest.TestCase):
    def test_arriba_con_health_ok(self):
        stub = _StubServidor()
        try:
            with patch.dict(os.environ, {"IA_BASE_URL": stub.base_url()}):
                self.assertTrue(ias.servidor_arriba(timeout=5))
                # ya estaba arriba: nadie debe arrancar/detener nada
                self.assertIsNone(ias.asegurar_servidor())
        finally:
            stub.detener()

    def test_abajo_en_puerto_muerto(self):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        muerto = s.getsockname()[1]
        s.close()
        with patch.dict(os.environ, {"IA_BASE_URL": f"http://127.0.0.1:{muerto}/v1"}):
            self.assertFalse(ias.servidor_arriba(timeout=1))


class TestArrancar(unittest.TestCase):
    def test_falla_rapido_si_no_hay_llama_server(self):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        muerto = s.getsockname()[1]
        s.close()
        with tempfile.TemporaryDirectory() as tmp:
            llama_fantasma = Path(tmp) / "llama-server.exe"
            with patch.dict(os.environ, {
                "IA_BASE_URL": f"http://127.0.0.1:{muerto}/v1",
                "IA_LLAMA_SERVER": str(llama_fantasma),
            }):
                with self.assertRaisesRegex(RuntimeError, "llama-server"):
                    ias.arrancar_servidor(espera_s=1)

    def test_servidor_externo_nunca_se_arranca_local(self):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        muerto = s.getsockname()[1]
        s.close()
        with patch.dict(os.environ, {
            "IA_BASE_URL": f"http://127.0.0.1:{muerto}/v1",
            "IA_LLAMA_SERVER": "no-importa",
        }):
            with patch.object(ias, "_config", lambda: ("https://externo.test/v1", False, "443")):
                with self.assertRaisesRegex(RuntimeError, "EXTERNO"):
                    ias.arrancar_servidor(espera_s=1)


class TestComandoYDetener(unittest.TestCase):
    def test_comando_llama_usa_puerto_del_env(self):
        with patch.dict(os.environ, {"IA_BASE_URL": "http://127.0.0.1:8099/v1"}):
            cmd = ias.comando_llama()
            self.assertEqual(cmd[cmd.index("--port") + 1], "8099")
            self.assertIn("--metrics", cmd)

    def test_detener_termina_proceso_y_es_idempotente(self):
        stub = _StubServidor()
        try:
            with patch.dict(os.environ, {"IA_BASE_URL": stub.base_url()}):
                proc = _ProcFake()
                servidor = ias.ServidorIA(proc)
                servidor.detener()
                self.assertFalse(proc.vivo)
                servidor.detener()  # segunda llamada: no debe fallar
        finally:
            stub.detener()


if __name__ == "__main__":
    unittest.main()
