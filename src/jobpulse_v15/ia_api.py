"""Cliente IA externa compatible OpenAI para v1.5.

Soporta múltiples proveedores vía presets:
- openrouter  -> openrouter.ai/api/v1
- nvidia      -> integrate.api.nvidia.com/v1
- google      -> generativelanguage.googleapis.com/v1beta/openai/
- ollama      -> ollama.com/v1 (cloud) o localhost:11434/v1 (local)
- lmstudio    -> localhost:1234/v1 (LM Studio local)
- custom      -> cualquier endpoint OpenAI-compatible (llama.cpp, vLLM, etc.)

Uso:
    client = IAClient({"proveedor": "custom", "base_url": "http://localhost:8080/v1", "modelo": "mi-modelo"})
    modelos = client.listar_modelos()
    resp = client.chat_json([{"role": "user", "content": "Hola"}])
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from jobpulse_v15.ia_servidor import es_endpoint_local

logger = logging.getLogger("jobpulse.ia")

# ──────────────────────────────────────────────────────────────
# Configuración de presets
# ──────────────────────────────────────────────────────────────

@dataclass
class ProviderPreset:
    nombre: str
    base_url: str
    env_key: str                    # variable de entorno para la API key
    modelo_default: str
    requiere_key: bool = True
    headers_extra: Dict[str, str] = field(default_factory=dict)


PRESETS: Dict[str, ProviderPreset] = {
    "openrouter": ProviderPreset(
        nombre="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        env_key="OPENROUTER_API_KEY",
        modelo_default="~openai/gpt-latest",
        headers_extra={"HTTP-Referer": "https://github.com/giovar24/jobpulse-cr", "X-Title": "JobPulse CR"},
    ),
    "nvidia": ProviderPreset(
        nombre="NVIDIA NIM",
        base_url="https://integrate.api.nvidia.com/v1",
        env_key="NVIDIA_API_KEY",
        modelo_default="openai/gpt-oss-20b",
    ),
    "google": ProviderPreset(
        nombre="Google Gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        env_key="GEMINI_API_KEY",
        modelo_default="gemini-2.5-flash",
    ),
    "ollama": ProviderPreset(
        nombre="Ollama Cloud",
        base_url="https://ollama.com/v1",
        env_key="OLLAMA_API_KEY",
        modelo_default="auto",
        requiere_key=False,
    ),
    "ollama-local": ProviderPreset(
        nombre="Ollama (local)",
        base_url="http://localhost:11434/v1",
        env_key="OLLAMA_API_KEY",
        modelo_default="auto",
        requiere_key=False,
    ),
    "lmstudio": ProviderPreset(
        nombre="LM Studio (local)",
        base_url="http://localhost:1234/v1",
        env_key="LMSTUDIO_API_KEY",
        modelo_default="auto",  # placeholder; se resuelve via /models
        requiere_key=False,
    ),
    "custom": ProviderPreset(
        nombre="Custom (llama.cpp, vLLM, etc.)",
        base_url="",        # obligatorio vía config
        env_key="IA_API_KEY",
        modelo_default="",  # obligatorio vía config
        requiere_key=False,
    ),
}

PROVEEDOR_NOMBRES = {k: v.nombre for k, v in PRESETS.items()}

PROMPT_VERSION = "v3"  # invalida cache al cambiar


def opt_int(explicito: Optional[int], env: Optional[str]) -> Optional[int]:
    """Resuelve un límite OPT-IN: explícito > variable de entorno > sin tope.

    ``None`` significa SIN TOPE (se procesa todo). Una cadena vacía (así
    queda en el ``.env`` cuando la UI deja el campo en blanco) también
    significa "sin tope", y un valor no numérico se descarta con aviso en
    vez de reventar el arranque.
    """
    if explicito is not None:
        return explicito if explicito > 0 else None
    if env is None:
        return None
    texto = str(env).strip()
    if not texto:
        return None
    try:
        valor = int(texto)
    except ValueError:
        logger.warning("IA: límite ignorado, no es un número: %r", env)
        return None
    return valor if valor > 0 else None

# ──────────────────────────────────────────────────────────────
# Errores
# ──────────────────────────────────────────────────────────────

class IAError(Exception):
    """Error base del cliente IA."""
    pass


class IAModeloError(IAError):
    """Modelo no encontrado (404/410) - fatal, no reintentar."""
    pass


class IACuotaError(IAError):
    """429 / 402 - cuota agotada."""


class IAPeticionError(IAError):
    """400 / 422 - el proveedor RECHAZÓ la petición (p.ej. no soporta
    ``response_format: json_schema``). Es la unica clase de error que
    justifica reintentar con otro modo de respuesta (fallback)."""
    pass


# ──────────────────────────────────────────────────────────────
# Cache de respuestas (persistente en disco)
# ──────────────────────────────────────────────────────────────

CACHE_DIR = Path(os.getenv("JOBPULSE_IA_CACHE", "data/usuario/ia_cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_key(proveedor: str, modelo: str, messages: List[Dict], **kwargs) -> str:
    """Hash determinista de la petición para cache."""
    payload = json.dumps({
        "prov": proveedor,
        "model": modelo,
        "msg": messages,
        "kw": sorted(kwargs.items()),
        "pv": PROMPT_VERSION,
    }, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def _cache_get(key: str) -> Optional[Dict]:
    path = CACHE_DIR / f"{key}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def _cache_set(key: str, data: Dict) -> None:
    path = CACHE_DIR / f"{key}.json"
    try:
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────
# Cliente principal
# ──────────────────────────────────────────────────────────────

class IAClient:
    """Cliente HTTP para endpoints OpenAI-compatible."""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        *,
        timeout: float = 120.0,
        lote: int = 8,
        max_vacantes: Optional[int] = None,
        max_llamadas: Optional[int] = None,
        rpm: Optional[int] = None,
    ) -> None:
        """
        Args:
            config: dict con claves opcionales:
                - proveedor: "openrouter" | "nvidia" | "google" | "ollama" |
                  "ollama-local" | "lmstudio" | "custom"
                - base_url: override (requerido si proveedor="custom")
                - modelo: override del default del preset
                - api_key: override (si no, usa env var del preset)
            timeout: timeout por request (segundos)
            lote: tamano de lote para procesamiento batch
            max_vacantes: tope de avisos a procesar por corrida.
                None (default) -> toma IA_MAX_VACANTES; si no hay env var:
                SIN TOPE (se procesa todo lo pendiente). Un int explicito
                siempre gana. 0 o negativo = sin tope.
            max_llamadas: tope de llamadas HTTP por corrida.
                None (default) -> toma IA_MAX_LLAMADAS; si no hay env var:
                SIN TOPE (regla del proyecto: los limites son opt-in).
                Un int explicito siempre gana.
            rpm: requests por minuto (rate limit).
                None (default) -> toma IA_RPM; si no hay env var: SIN tope.
        """
        config = config or {}

        # Resolver proveedor
        self.proveedor = config.get("proveedor") or os.getenv("IA_PROVEEDOR") or "custom"
        if self.proveedor not in PRESETS:
            raise IAError(f"Proveedor desconocido: {self.proveedor}. Válidos: {list(PRESETS)}")

        preset = PRESETS[self.proveedor]

        # base_url: config > env > preset
        self.base_url = (
            config.get("base_url")
            or os.getenv("IA_BASE_URL")
            or preset.base_url
        ).rstrip("/")
        if not self.base_url:
            raise IAError(f"base_url requerido para proveedor '{self.proveedor}'")

        # api_key: config > env específico > env genérico > preset.env_key
        self.api_key = (
            config.get("api_key")
            or os.getenv(preset.env_key)
            or os.getenv("IA_API_KEY")
            or ""
        )
        if preset.requiere_key and not self.api_key:
            raise IAError(f"Falta API key para {preset.nombre}. Define {preset.env_key} o IA_API_KEY en .env")

        # modelo: config > env > preset.default
        self.modelo = (
            config.get("modelo")
            or os.getenv("IA_MODEL")
            or preset.modelo_default
        )
        # Permitir modelo vacío para proveedores con auto-detección (lmstudio, ollama)
        # Se resolverá llamando a listar_models() antes de chat()
        auto_detect_proveedores = {"lmstudio", "ollama"}
        if self.modelo == "auto" or (self.proveedor in auto_detect_proveedores and not self.modelo):
            self.modelo = ""
        elif not self.modelo:
            raise IAError(f"modelo requerido para proveedor '{self.proveedor}'")

        # Parámetros de control.
        # POR DEFECTO NO HAY TOPE (salir corriendo no es gratis en una API
        # externa y el usuario decide si pone limites). Los limites son
        # OPT-IN, via .env (IA_MAX_LLAMADAS / IA_RPM / IA_MAX_VACANTES) o
        # via argumento explicito. Un int explicito siempre gana.
        self.timeout = timeout
        self.lote = lote
        self.max_vacantes = opt_int(max_vacantes, os.getenv("IA_MAX_VACANTES"))
        # Mismo criterio que `ia_servidor`: de esto depende el aviso de
        # privacidad (si el texto sale de la máquina o no).
        self._es_local = es_endpoint_local(self.base_url)
        if max_llamadas is not None:
            self.max_llamadas = max_llamadas            # explicito gana
        else:
            self.max_llamadas = opt_int(None, os.getenv("IA_MAX_LLAMADAS"))
        if rpm is not None:
            self.rpm = rpm
        else:
            self.rpm = opt_int(None, os.getenv("IA_RPM"))

        # Estado runtime
        self.llamadas = 0
        self.tokens_in = 0
        self.tokens_out = 0
        self._min_interval = 0.0 if self.rpm is None else 60.0 / max(1, self.rpm)
        self._last_call = 0.0

        # Cliente HTTP
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={
                "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
                "Content-Type": "application/json",
                **preset.headers_extra,
            },
        )

    @property
    def disponible(self) -> bool:
        return bool(self.base_url and (self.api_key or not PRESETS[self.proveedor].requiere_key))

    @property
    def es_local(self) -> bool:
        """True si el endpoint corre en 127.0.0.1/localhost.

        Los servidores locales (Gemma/llama.cpp, LM Studio) no sacan texto de
        la maquina; un motor externo (google/nvidia/openrouter/ollama cloud)
        si viaja el prompt completo -> la UI debe avisar privacidad.
        """
        return self._es_local

    def motivo_no_disponible(self) -> str:
        if not self.base_url:
            return "base_url no configurado"
        if PRESETS[self.proveedor].requiere_key and not self.api_key:
            return f"falta API key ({PRESETS[self.proveedor].env_key})"
        return "desconocido"

    # ──────────────────────────────────────────────────────────
    # Utilidades de rate limiting y request
    # ──────────────────────────────────────────────────────────

    async def _rate_limit(self) -> None:
        now = time.monotonic()
        wait = self._last_call + self._min_interval - now
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_call = time.monotonic()

    async def _post(self, endpoint: str, payload: Dict) -> Dict:
        """POST con reintento único en 429/5xx."""
        await self._rate_limit()
        url = f"{self.base_url}{endpoint}"

        for intento in range(2):
            try:
                resp = await self._client.post(url, json=payload)
            except httpx.TimeoutException as e:
                raise IAError(f"Timeout ({self.timeout}s) en {endpoint}") from e
            except httpx.RequestError as e:
                raise IAError(f"Error de red: {e}") from e

            if resp.status_code == 404:
                # Modelo no encontrado (404/410) -> fatal
                raise IAModeloError(
                    f"Modelo '{self.modelo}' no encontrado (404) en {self.proveedor}. "
                    f"Verifica con --ia-listar-modelos y elige otro con --ia-modelo."
                )
            if resp.status_code == 401:
                raise IAError("API key inválida o expirada (401)")
            if resp.status_code in (402, 429):
                if intento == 0:
                    await asyncio.sleep(5)
                    continue
                raise IACuotaError(f"Cuota agotada o rate limit ({resp.status_code})")
            if resp.status_code in (400, 422):
                # El proveedor rechazo la peticion (formato, modelo, schema).
                # NO se reintenta igual: hay que degradar el modo de respuesta.
                raise IAPeticionError(
                    f"El proveedor rechazo la peticion ({resp.status_code}): "
                    f"{resp.text[:300]}"
                )
            if resp.status_code == 403:
                raise IAError(f"Acceso denegado (403): {resp.text[:200]}")
            if resp.status_code >= 500:
                if intento == 0:
                    await asyncio.sleep(3)
                    continue
                raise IAError(f"Error servidor {resp.status_code}: {resp.text[:200]}")

            try:
                return resp.json()
            except json.JSONDecodeError as e:
                raise IAError(f"Respuesta no es JSON válido: {resp.text[:200]}") from e

        raise IAError("Máximo de reintentos alcanzado")

    # ──────────────────────────────────────────────────────────
    # API pública
    # ──────────────────────────────────────────────────────────

    async def listar_modelos(self) -> List[str]:
        """GET /models en vivo. Devuelve lista de IDs de modelos."""
        await self._rate_limit()
        url = f"{self.base_url}/models"
        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return [m.get("id", "") for m in data.get("data", []) if m.get("id")]
        except Exception as e:
            logger.warning("IA listar_modelos falló (%s): %s", self.proveedor, e)
            return []

    async def _resolver_modelo(self) -> str:
        """Resuelve el modelo cuando está en "auto" (Ollama, LM Studio…).

        ``IA_MODEL=auto`` (o vacío) hace que el cliente pregunte ``GET /models``
        y use el primer modelo disponible. Si el endpoint no expone modelos,
        el error es explícito: hay que definir ``IA_MODEL`` en el ``.env``.
        """
        if self.modelo:
            return self.modelo
        modelos = await self.listar_modelos()
        if not modelos:
            raise IAModeloError(
                f"No se pudo autodetectar el modelo en {self.base_url} "
                f"({self.proveedor}): el endpoint no devolvió /models. "
                "Define IA_MODEL en el .env."
            )
        self.modelo = modelos[0]
        logger.info("IA: modelo autodetectado (%s): %s", self.proveedor, self.modelo)
        return self.modelo

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 4000,
        response_format: Optional[Dict] = None,
        use_cache: bool = True,
    ) -> Dict:
        """
        Chat completion síncrono (usa asyncio.run internamente).
        Para uso en CLI/scripts que no son async.
        """
        import asyncio
        return asyncio.run(self.achat(messages, temperature=temperature, max_tokens=max_tokens,
                                       response_format=response_format, use_cache=use_cache))

    async def achat(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 4000,
        response_format: Optional[Dict] = None,
        use_cache: bool = True,
    ) -> Dict:
        """Chat completion asíncrono con cache opcional."""
        if self.max_llamadas is not None and self.llamadas >= self.max_llamadas:
            raise IAError(f"Límite de llamadas alcanzado ({self.max_llamadas})")

        # "auto" (Ollama, LM Studio): se resuelve con GET /models antes de
        # armar la caché (la clave depende del modelo).
        modelo = await self._resolver_modelo()

        # Cache key
        cache_key = _cache_key(self.proveedor, modelo, messages,
                               temperature=temperature, max_tokens=max_tokens,
                               response_format=response_format)
        if use_cache:
            cached = _cache_get(cache_key)
            if cached:
                logger.debug("IA cache hit: %s", cache_key[:8])
                return cached

        payload = {
            "model": modelo,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        # OpenRouter requiere max_tokens explícito para validar presupuesto
        if self.proveedor == "openrouter" and "max_tokens" not in payload:
            payload["max_tokens"] = 3000

        result = await self._post("/chat/completions", payload)
        self.llamadas += 1

        # Contar tokens si vienen en response
        usage = result.get("usage") or {}
        self.tokens_in += usage.get("prompt_tokens", 0)
        self.tokens_out += usage.get("completion_tokens", 0)

        if use_cache:
            _cache_set(cache_key, result)

        return result

    async def chat_json(
        self,
        messages: List[Dict[str, str]],
        *,
        schema: Optional[Dict] = None,
        temperature: float = 0.1,
        max_tokens: int = 4000,
        use_cache: bool = True,
    ) -> Dict:
        """
        Chat completion que exige respuesta JSON válido.

        Modos de respuesta, en orden de preferencia y con DEGRADACION
        automatica si el proveedor los rechaza (400/422):

        1. ``json_schema`` estricto (llama.cpp, OpenAI, OpenRouter);
        2. ``json_object`` (Gemini/OpenAI-compat, LM Studio, Ollama…);
        3. sin ``response_format`` (el prompt ya pide JSON; el cliente
           limpia la respuesta con ``_json_de_texto``).

        Solo se degrada ante un rechazo del PROVEEDOR (``IAPeticionError``):
        un 429, un 404 de modelo o el tope de llamadas se propagan tal cual
        (degradar ahi gastaria dinero y esconderia el error real).
        """
        modos: List[Optional[Dict]] = []
        if schema:
            modos.append({
                "type": "json_schema",
                "json_schema": {"name": "response", "schema": schema, "strict": True},
            })
        modos.append({"type": "json_object"})
        modos.append(None)

        ultimo_error: Optional[Exception] = None
        for modo in modos:
            try:
                resp = await self.achat(
                    messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=modo,
                    use_cache=use_cache,
                )
            except IAPeticionError as exc:
                ultimo_error = exc
                logger.info(
                    "IA: el proveedor rechazo el modo de respuesta (%s); "
                    "se degrada a %s",
                    str(exc)[:120],
                    "json_object" if modo and modo.get("type") == "json_schema"
                    else "sin response_format",
                )
                continue
            content = resp["choices"][0]["message"]["content"]
            return self._json_de_texto(content)

        raise IAError(
            "El proveedor no acepto ningun modo de respuesta JSON: "
            f"{ultimo_error}"
        )

    @staticmethod
    def _json_de_texto(texto: str) -> Dict:
        """Extrae JSON válido de texto que puede tener basura alrededor."""
        import re
        # 1. Buscar ```json ... ```
        m = re.search(r"```json\s*(\{.*?\})\s*```", texto, re.DOTALL)
        if m:
            texto = m.group(1)
        else:
            # 2. Buscar primer { ... } balanceado
            m = re.search(r"(\{.*\})", texto, re.DOTALL)
            if m:
                texto = m.group(1)

        # 3. Intentar json.loads, si falla probar raw_decode para objetos múltiples
        try:
            return json.loads(texto)
        except json.JSONDecodeError:
            try:
                decoder = json.JSONDecoder()
                obj, _ = decoder.raw_decode(texto)
                return obj
            except Exception as e:
                raise IAError(f"No se pudo parsear JSON de la respuesta: {e}\nTexto: {texto[:500]}")

    # ──────────────────────────────────────────────────────────
    # Hash de vacante/CV para cache
    # ──────────────────────────────────────────────────────────

    def hash_vacante(self, vacante: Dict, perfil_hash: str) -> str:
        """Hash único de vacante + perfil + versión de prompt."""
        contenido = json.dumps({
            "titulo": vacante.get("title", ""),
            "empresa": vacante.get("company", ""),
            "desc": (vacante.get("description_raw", "") or "")[:3000],
            "reqs": (vacante.get("requirements_raw", "") or "")[:1500],
            "perfil": perfil_hash,
            "pv": PROMPT_VERSION,
        }, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(contenido.encode()).hexdigest()[:16]

    def hash_cv(self, cv_texto: str) -> str:
        return hashlib.sha256(cv_texto.encode()).hexdigest()[:16]

    def resumen_uso(self) -> str:
        return f"{self.llamadas} llamadas, {self.tokens_in} tok in, {self.tokens_out} tok out"

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> IAClient:
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()


# ──────────────────────────────────────────────────────────────
# Funciones de conveniencia para CLI
# ──────────────────────────────────────────────────────────────

import asyncio


async def _listar_modelos_cli(proveedor: str = "", modelo: str = "") -> None:
    """Lista modelos del proveedor y sale."""
    cfg = {}
    if proveedor:
        cfg["proveedor"] = proveedor
    if modelo:
        cfg["modelo"] = modelo
    client = IAClient(cfg)
    try:
        modelos = await client.listar_modelos()
        actual = modelo or client.modelo
        print(f"{len(modelos)} modelo(s) en {client.proveedor} ({client.base_url}):")
        for m in modelos:
            print(("  * " if m == actual else "    ") + m)
        if actual not in modelos:
            print(f"\n⚠ El modelo actual '{actual}' no aparece en la lista; puede haber sido retirado.")
        print(f"\nUsa: python -m jobpulse_v15 --ia --ia-modelo \"<modelo>\"")
    finally:
        await client.close()


def listar_modelos_cli(proveedor: str = "", modelo: str = "") -> None:
    asyncio.run(_listar_modelos_cli(proveedor, modelo))