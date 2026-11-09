# -*- coding: utf-8 -*-
"""Tests del soporte de IA EXTERNA (Ollama Cloud, LM Studio, OpenRouter…).

Sin red y sin modelo real: todo se simula con fakes y dobles de prueba.

Cubren:
- detección de endpoint local vs. externo (`ia_servidor.es_endpoint_local`);
- `asegurar_servidor()` con proveedor externo (NO arranca nada local);
- degradación de `chat_json` (json_schema → json_object → sin response_format);
- preflight con mensaje distinto para local y externo;
- aviso de privacidad (obligatorio con IA no local);
- tope de avisos OPT-IN y ajustable (`IA_MAX_VACANTES`).
"""
import asyncio
import http.server
import json
import os
import tempfile
import threading
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from jobpulse_v15 import ia_enrichment as iae
from jobpulse_v15 import ia_servidor as ias
from jobpulse_v15 import ia_api
from jobpulse_v15.db import Database
from jobpulse_v15.repository import Repository
from jobpulse_v15.ia_api import (
    IAClient,
    IAError,
    IACuotaError,
    IAPeticionError,
    PRESETS,
    opt_int,
)


SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}},
          "required": ["ok"], "additionalProperties": False}


def _cliente(base_url="http://localhost:1234/v1", modelo="m"):
    return IAClient({"proveedor": "custom", "base_url": base_url, "modelo": modelo})


@contextmanager
def _sin_tope_env():
    """Quita ``IA_MAX_VACANTES`` del entorno.

    Otro test (la UI v2) deja la variable puesta en ``os.environ`` al
    guardar la configuración; sin este aislamiento los tests que esperan
    "sin tope" dependerían del orden de ejecución.
    """
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("IA_MAX_VACANTES", None)
        yield


class _ClienteSimulado:
    """Cliente IA mínimo: sabe si es local y puede fallar."""

    def __init__(self, es_local=False, falla=True, base_url="http://x.test/v1"):
        self.es_local = es_local
        self.base_url = base_url
        self.modelo = "modelo-x"
        self.proveedor = "ollama"
        self.falla = falla
        self.llamadas = 0

    async def chat_json(self, *args, **kwargs):
        self.llamadas += 1
        if self.falla:
            raise RuntimeError("sin conexión")
        return {"ok": True}


class TestEndpointLocal(unittest.TestCase):
    def test_hosts_de_esta_maquina_son_locales(self):
        self.assertTrue(ias.es_endpoint_local("http://127.0.0.1:8081/v1"))
        self.assertTrue(ias.es_endpoint_local("http://localhost:1234/v1"))
        self.assertTrue(ias.es_endpoint_local("http://127.0.0.2:11434/v1"))

    def test_proveedores_en_la_nube_no_son_locales(self):
        self.assertFalse(ias.es_endpoint_local("https://ollama.com/v1"))
        self.assertFalse(ias.es_endpoint_local("https://openrouter.ai/api/v1"))
        self.assertFalse(
            ias.es_endpoint_local(
                "https://generativelanguage.googleapis.com/v1beta/openai/"))

    def test_otra_maquina_de_la_red_no_es_local(self):
        self.assertFalse(ias.es_endpoint_local("http://192.168.1.20:1234/v1"))


class TestAsegurarServidorConProveedorExterno(unittest.TestCase):
    def test_no_arranca_nada_local_si_el_endpoint_es_externo(self):
        with patch.dict(os.environ, {"IA_BASE_URL": "https://ollama.com/v1"}), \
             patch.object(ias, "arrancar_servidor") as arrancar:
            self.assertIsNone(ias.asegurar_servidor())
            arrancar.assert_not_called()

    def test_con_endpoint_local_arranca_como_antes(self):
        with patch.dict(os.environ, {"IA_BASE_URL": "http://127.0.0.1:8081/v1"}), \
             patch.object(ias, "servidor_arriba", return_value=False), \
             patch.object(ias, "arrancar_servidor",
                          return_value="ARRANCADO") as arrancar:
            self.assertEqual(ias.asegurar_servidor(), "ARRANCADO")
            arrancar.assert_called_once()

    def test_servidor_ya_arriba_no_se_toca(self):
        with patch.dict(os.environ, {"IA_BASE_URL": "http://127.0.0.1:8081/v1"}), \
             patch.object(ias, "servidor_arriba", return_value=True), \
             patch.object(ias, "arrancar_servidor") as arrancar:
            self.assertIsNone(ias.asegurar_servidor())
            arrancar.assert_not_called()


class TestPresetsOllamaYLMStudio(unittest.TestCase):
    def test_existen_ollama_cloud_ollama_local_y_lmstudio(self):
        self.assertIn("ollama", PRESETS)
        self.assertIn("ollama-local", PRESETS)
        self.assertIn("lmstudio", PRESETS)

    def test_ollama_cloud_apunta_a_la_nube(self):
        self.assertTrue(PRESETS["ollama"].base_url.startswith("https://ollama.com"))

    def test_ollama_local_apunta_a_esta_maquina(self):
        self.assertTrue(
            ias.es_endpoint_local(PRESETS["ollama-local"].base_url))
        self.assertTrue(ias.es_endpoint_local(PRESETS["lmstudio"].base_url))

    def test_lmstudio_no_pide_api_key(self):
        self.assertFalse(PRESETS["lmstudio"].requiere_key)


class TestChatJsonDegrada(unittest.TestCase):
    """Muchos OpenAI-compatible externos NO aceptan json_schema estricto."""

    def test_degrada_de_json_schema_a_json_object(self):
        cliente = _cliente()
        modos = []

        async def fake_achat(messages, *, temperature=0.1, max_tokens=4000,
                             response_format=None, use_cache=True):
            modos.append(response_format)
            if response_format and response_format.get("type") == "json_schema":
                raise IAPeticionError("400 unsupported response_format")
            return {"choices": [{"message": {"content": '{"ok": true}'}}]}

        with patch.object(cliente, "achat", fake_achat):
            r = asyncio.run(cliente.chat_json(
                [{"role": "user", "content": "hola"}], schema=SCHEMA))
        self.assertEqual(r, {"ok": True})
        self.assertEqual(modos[0]["type"], "json_schema")
        self.assertEqual(modos[1]["type"], "json_object")

    def test_degrada_hasta_sin_response_format(self):
        cliente = _cliente()
        modos = []

        async def fake_achat(messages, *, temperature=0.1, max_tokens=4000,
                             response_format=None, use_cache=True):
            modos.append(response_format)
            if response_format is not None:
                raise IAPeticionError("400 no lo acepta")
            return {"choices": [{"message": {"content": '{"ok": true}'}}]}

        with patch.object(cliente, "achat", fake_achat):
            r = asyncio.run(cliente.chat_json(
                [{"role": "user", "content": "hola"}], schema=SCHEMA))
        self.assertEqual(r, {"ok": True})
        self.assertIsNone(modos[-1])

    def test_no_degrada_un_429_de_cuota(self):
        cliente = _cliente()
        llamadas = []

        async def fake_achat(messages, *, temperature=0.1, max_tokens=4000,
                             response_format=None, use_cache=True):
            llamadas.append(response_format)
            raise IACuotaError("429 cuota agotada")

        with patch.object(cliente, "achat", fake_achat):
            with self.assertRaises(IACuotaError):
                asyncio.run(cliente.chat_json(
                    [{"role": "user", "content": "hola"}], schema=SCHEMA))
        self.assertEqual(len(llamadas), 1)

    def test_error_final_si_el_proveedor_rechaza_todo(self):
        cliente = _cliente()

        async def fake_achat(messages, *, temperature=0.1, max_tokens=4000,
                             response_format=None, use_cache=True):
            raise IAPeticionError("400 no lo acepta de ninguna forma")

        with patch.object(cliente, "achat", fake_achat):
            with self.assertRaises(IAError):
                asyncio.run(cliente.chat_json(
                    [{"role": "user", "content": "hola"}], schema=SCHEMA))


class TestPreflight(unittest.TestCase):
    def test_mensaje_para_proveedor_externo(self):
        cliente = _ClienteSimulado(es_local=False)
        error = asyncio.run(iae.verificar_servidor_ia(cliente))
        self.assertIsNotNone(error)
        self.assertIn("externo", error)

    def test_mensaje_para_servidor_local(self):
        cliente = _ClienteSimulado(es_local=True)
        error = asyncio.run(iae.verificar_servidor_ia(cliente))
        self.assertIsNotNone(error)
        self.assertIn("local", error)

    def test_sin_error_si_responde(self):
        cliente = _ClienteSimulado(es_local=False, falla=False)
        self.assertIsNone(asyncio.run(iae.verificar_servidor_ia(cliente)))


class TestAvisoPrivacidad(unittest.TestCase):
    def test_sin_aviso_para_ia_local(self):
        self.assertIsNone(
            iae.aviso_privacidad(_ClienteSimulado(es_local=True, falla=False)))

    def test_aviso_para_ia_externa(self):
        aviso = iae.aviso_privacidad(_ClienteSimulado(es_local=False))
        self.assertIsNotNone(aviso)
        self.assertIn("extern", aviso.lower())

    def test_sin_cliente_no_hay_aviso(self):
        self.assertIsNone(iae.aviso_privacidad(None))


class TestTopeVacantes(unittest.TestCase):
    """El tope de avisos es OPT-IN y el usuario lo sube o lo baja."""

    def test_sin_variable_no_hay_tope(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("IA_MAX_VACANTES", None)
            self.assertIsNone(iae.tope_vacantes())

    def test_variable_vacia_no_hay_tope(self):
        with patch.dict(os.environ, {"IA_MAX_VACANTES": ""}):
            self.assertIsNone(iae.tope_vacantes())

    def test_el_usuario_pone_el_tope_que_quiera(self):
        for valor in ("1", "25", "5000"):
            with patch.dict(os.environ, {"IA_MAX_VACANTES": valor}):
                self.assertEqual(iae.tope_vacantes(), int(valor))

    def test_cero_es_sin_tope(self):
        with patch.dict(os.environ, {"IA_MAX_VACANTES": "0"}):
            self.assertIsNone(iae.tope_vacantes())

    def test_valor_no_numerico_se_ignora(self):
        with patch.dict(os.environ, {"IA_MAX_VACANTES": "muchos"}):
            self.assertIsNone(iae.tope_vacantes())

    def test_explicito_gana_sobre_el_env(self):
        with patch.dict(os.environ, {"IA_MAX_VACANTES": "100"}):
            self.assertEqual(iae.tope_vacantes(7), 7)

    def test_opt_int_trata_vacio_y_no_numerico(self):
        self.assertIsNone(opt_int(None, ""))
        self.assertIsNone(opt_int(None, None))
        self.assertIsNone(opt_int(None, "abc"))
        self.assertEqual(opt_int(None, "12"), 12)
        self.assertEqual(opt_int(5, "12"), 5)
        self.assertIsNone(opt_int(0, "12"))


class TestClienteTopeYLimites(unittest.TestCase):
    def test_el_cliente_toma_el_tope_del_env(self):
        with patch.dict(os.environ, {"IA_MAX_VACANTES": "12"}):
            cliente = _cliente()
            self.assertEqual(cliente.max_vacantes, 12)

    def test_sin_env_no_hay_tope_de_avisos(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("IA_MAX_VACANTES", None)
            self.assertIsNone(_cliente().max_vacantes)

    def test_limites_de_llamadas_son_opt_in(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("IA_MAX_LLAMADAS", None)
            os.environ.pop("IA_RPM", None)
            cliente = _cliente()
            self.assertIsNone(cliente.max_llamadas)
            self.assertIsNone(cliente.rpm)


class TestPaseCompletoRespetaElTope(unittest.TestCase):
    @staticmethod
    def _stats(**kw):
        base = {"total": 0, "seleccionados": 0, "enriched": 0, "failed": 0,
                "skipped": 0, "fields_filled": {}}
        base.update(kw)
        return base

    async def _verificar_ok(self, cliente):
        return None

    def _fake_run(self, llamadas):
        async def fake_run(limit=50, only_critical=True, db_path=None, **kw):
            criticos = [c for c in llamadas if c[0] == "crit"]
            llamadas.append(("crit" if only_critical else "full", limit))
            if only_critical:
                if len(criticos) == 0:
                    return {"stats": self._stats(total=4, seleccionados=4,
                                                enriched=4)}
                return {"stats": self._stats()}
            return {"stats": self._stats(total=2, seleccionados=2, enriched=2)}
        return fake_run

    def test_sin_tope_no_limita(self):
        llamadas = []
        with _sin_tope_env(), \
             patch.object(iae, "run_ia_enrichment", self._fake_run(llamadas)), \
             patch.object(iae, "get_ia_client",
                          lambda: _ClienteSimulado(falla=False)), \
             patch.object(iae, "verificar_servidor_ia", self._verificar_ok):
            asyncio.run(iae.pase_completo())
        self.assertIn(("crit", 500), llamadas)
        self.assertIn(("full", 2000), llamadas)

    def test_con_tope_el_presupuesto_se_agota(self):
        llamadas = []
        with patch.object(iae, "run_ia_enrichment", self._fake_run(llamadas)), \
             patch.object(iae, "get_ia_client",
                          lambda: _ClienteSimulado(falla=False)), \
             patch.object(iae, "verificar_servidor_ia", self._verificar_ok):
            r = asyncio.run(iae.pase_completo(max_vacantes=10))
        self.assertIn(("crit", 10), llamadas)   # primer ciclo: todo el tope
        self.assertIn(("crit", 6), llamadas)    # quedan 6 tras gastar 4
        self.assertIn(("full", 6), llamadas)    # el pase completo hereda el resto
        self.assertEqual(r.get("tope_vacantes"), 10)

    def test_el_tope_tambien_se_lee_del_env(self):
        llamadas = []
        with patch.dict(os.environ, {"IA_MAX_VACANTES": "8"}), \
             patch.object(iae, "run_ia_enrichment", self._fake_run(llamadas)), \
             patch.object(iae, "get_ia_client",
                          lambda: _ClienteSimulado(falla=False)), \
             patch.object(iae, "verificar_servidor_ia", self._verificar_ok):
            asyncio.run(iae.pase_completo())
        self.assertIn(("crit", 8), llamadas)

    def test_avisa_de_que_el_texto_sale_de_la_maquina(self):
        eventos = []
        llamadas = []
        with _sin_tope_env(), \
             patch.object(iae, "run_ia_enrichment", self._fake_run(llamadas)), \
             patch.object(iae, "get_ia_client",
                          lambda: _ClienteSimulado(falla=False)), \
             patch.object(iae, "verificar_servidor_ia", self._verificar_ok):
            asyncio.run(iae.pase_completo(on_event=eventos.append))
        self.assertTrue(any("texto" in e.lower() for e in eventos))


#: Respuestas por prompt (como en `test_ia_enrichment`).
RESPUESTAS = {
    iae.LOCATION_PROMPT: {"city": "Heredia", "region": "Heredia"},
    iae.WORK_MODE_PROMPT: {"work_mode": "onsite"},
    iae.DATE_PROMPT: {"date_published": "2026-10-20"},
    iae.EMPLOYMENT_PROMPT: {"employment_type": "Full-time"},
    iae.SALARY_PROMPT: {
        "salary_min": 1000000, "salary_max": 1500000,
        "salary_currency": "CRC", "salary_period": "monthly",
    },
    iae.SKILLS_PROMPT: {"skills": ["SQL", "Active Directory"]},
    iae.LANGUAGES_PROMPT: {"languages": {"ingles": "B2"}},
}


class _HandlerOpenAI(http.server.BaseHTTPRequestHandler):
    """Proveedor OpenAI-compatible mínimo que RECHAZA ``json_schema`` (400).

    Es el caso real de LM Studio / Ollama / varios gateways: el cliente
    tiene que degradar a ``json_object`` y seguir.
    """

    payloads: list = []

    def _json(self, obj, status=200):
        cuerpo = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        if self.path.endswith("/models"):
            self._json({"data": [{"id": "modelo-falso"}]})
        else:
            self._json({"error": "no encontrado"}, 404)

    def do_POST(self):
        largo = int(self.headers.get("Content-Length") or 0)
        payload = json.loads(self.rfile.read(largo) or b"{}")
        type(self).payloads.append(payload)
        formato = payload.get("response_format") or {}
        if formato.get("type") == "json_schema":
            self._json(
                {"error": {"message": "response_format json_schema no soportado"}},
                400,
            )
            return
        sistema = next(
            (m.get("content", "") for m in payload.get("messages", [])
             if m.get("role") == "system"),
            "",
        )
        contenido = json.dumps(
            RESPUESTAS.get(sistema, {"ok": True}), ensure_ascii=False)
        self._json({
            "choices": [{"message": {"role": "assistant", "content": contenido}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        })

    def log_message(self, *args):
        pass


class TestAutoModelo(unittest.TestCase):
    """``IA_MODEL=auto`` (Ollama, LM Studio) debe resolverse con /models."""

    def test_el_cliente_deja_el_modelo_vacio_con_auto(self):
        cliente = IAClient({"proveedor": "ollama-local", "modelo": "auto"})
        self.assertEqual(cliente.modelo, "")

    def test_achat_resuelve_el_modelo_por_models(self):
        cliente = IAClient({"proveedor": "ollama-local", "modelo": "auto"})
        enviados = []

        async def fake_post(endpoint, payload):
            enviados.append(payload)
            return {"choices": [{"message": {"content": '{"ok": true}'}}]}

        async def fake_models():
            return ["gemma3:4b", "llama3.2:3b"]

        with patch.object(cliente, "_post", fake_post), \
             patch.object(cliente, "listar_modelos", fake_models):
            # use_cache=False: la caché en disco haría que el POST no se
            # ejecute (y el test dependería del orden de la suite).
            r = asyncio.run(cliente.achat(
                [{"role": "user", "content": "hola"}], use_cache=False))
        self.assertEqual(r["choices"][0]["message"]["content"], '{"ok": true}')
        self.assertEqual(enviados[0]["model"], "gemma3:4b")

    def test_error_claro_si_no_hay_modelos(self):
        cliente = IAClient({"proveedor": "ollama-local", "modelo": "auto"})

        async def fake_models():
            return []

        with patch.object(cliente, "listar_modelos", fake_models):
            with self.assertRaises(IAError) as ctx:
                asyncio.run(cliente.achat(
                    [{"role": "user", "content": "hola"}], use_cache=False))
        self.assertIn("IA_MODEL", str(ctx.exception))


class TestProveedorExternoExtremo_a_Extremo(unittest.TestCase):
    """El camino completo contra un endpoint OpenAI-compatible de verdad."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test.db")
        db = Database(self.db_path)
        db.initialize()
        repo = Repository(db)
        repo.register_platform("test", "Test", "directos")
        repo.register_site(
            "test-site", "test", "Sitio test",
            "https://example.test/jobs", run_groups=("all",),
        )
        repo.save_job(
            {
                "job_id": "T-1", "title": "IT Support Specialist",
                "company": "Test Corp", "location_raw": "San Jose, Heredia",
                "work_mode": "unknown", "date_published": "2026-10-20",
                "description_raw": "Soporte IT con Active Directory y SQL.",
            },
            site_id="test-site", source_job_id="T-1",
            source_url="https://example.test/jobs/T-1",
        )
        _HandlerOpenAI.payloads = []
        self.httpd = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), _HandlerOpenAI)
        self.puerto = self.httpd.server_address[1]
        self.hilo = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.hilo.start()
        self.cache = Path(self.temp_dir.name) / "cache"
        self.cache.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.temp_dir.cleanup()

    def test_enriquece_contra_un_proveedor_externo(self):
        base = f"http://127.0.0.1:{self.puerto}/v1"
        env = {
            "IA_PROVEEDOR": "custom",
            "IA_BASE_URL": base,
            "IA_MODEL": "modelo-falso",
            "IA_API_KEY": "",
        }
        with patch.dict(os.environ, env, clear=False), \
             patch.object(ia_api, "CACHE_DIR", self.cache):
            os.environ.pop("IA_MAX_VACANTES", None)
            r = asyncio.run(iae.run_ia_enrichment(
                db_path=self.db_path, limit=5, only_critical=True))
        self.assertNotIn("error", r)
        self.assertEqual(r["stats"]["enriched"], 1)
        job = Repository(Database(self.db_path)).get_job("T-1")
        self.assertEqual(job["work_mode"], "onsite")
        self.assertEqual(job["city"], "Heredia")
        # El proveedor recibió primero json_schema (rechazado) y después
        # json_object (aceptado): la degradación ocurre de verdad.
        formatos = [p.get("response_format", {}).get("type")
                    for p in _HandlerOpenAI.payloads]
        self.assertIn("json_schema", formatos)
        self.assertIn("json_object", formatos)


if __name__ == "__main__":
    unittest.main()