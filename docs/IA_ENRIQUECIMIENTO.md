# Enriquecimiento IA (O1) — operación y configuración

Cómo funciona el enriquecimiento de ofertas con IA (local llama.cpp **o**
externa: Ollama, LM Studio, gateways cloud) y cómo operarlo/depurarlo. Todo
configurable desde `.env` (sin tocar código).

## Arquitectura

```
BD jobs ──> ia_enrichment.run_ia_enrichment ──> IAClient (OpenAI-compat)
                                               ├─> llama-server local (8081)
                                               └─> proveedor externo (Ollama Cloud,
                                                   LM Studio, OpenRouter, Gemini…)
```

- Campos **críticos**: `city`, `region`, `work_mode`, `date_published`.
- Campos **secundarios**: `employment_type`, `salary_*`, `skills`, `languages`.
- Guardado selectivo: solo se escriben las columnas que la IA realmente
  tocó (nunca se sobre-escriben skills/languages existentes).

## Arranque del servidor

| Modo | Qué hacer |
|---|---|
| Bajo demanda (O7.3, recomendado) | La UI lo gestiona: el botón **"Enriquecer"** y el pase IA de CV arrancan el servidor si hace falta y lo APAGAN al terminar (solo el proceso que ellos abrieron; si ya estaba arriba, no se toca). `run_enriquecimiento.py` hace lo mismo. El launcher `jobpulse-v15.bat` ya NO pre-arranca la IA. |
| Manual | `ia-server.bat` o `python start_ia_server.py` (verifica/arranca/espera el modelo). El comando replica el build Vulkan del usuario (`D:\llama-b11662-bin-win-vulkan-x64`, modelo `D:\Models\gemma-4-E2B-it-qat-UD-Q4_K_XL`, 8k ctx + MTP draft). Log: `data/ia_server.log`. |
| **Servidor externo** | Ponga `IA_BASE_URL` del `.env` a la URL remota (p. ej. `http://192.168.1.10:8081/v1`). El preflight lo detecta como no-local y **no** intenta arrancar nada local. |

Verificación rápida:
```powershell
python start_ia_server.py --check     # exit 0 = arriba / 1 = apagado
```

## IA externa: Ollama, LM Studio y cloud gratis

La IA local (Gemma/llama.cpp) y la IA externa usan **el mismo cliente y el
mismo pase**: no hay dos implementaciones. Lo único que cambia es el
proveedor del `.env`.

### Proveedores (presets)

| `IA_PROVEEDOR` | Qué es | `IA_BASE_URL` por defecto | API key |
|---|---|---|---|
| `custom` | llama.cpp / vLLM / cualquier OpenAI-compatible | (la del `.env`) | no hace falta |
| `ollama` | **Ollama Cloud** (cuenta gratis en la nube) | `https://ollama.com/v1` | `OLLAMA_API_KEY` (opcional) |
| `ollama-local` | Ollama instalado en esta máquina | `http://localhost:11434/v1` | no |
| `lmstudio` | LM Studio (servidor local) | `http://localhost:1234/v1` | no |
| `openrouter` | OpenRouter | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` |
| `nvidia` | NVIDIA NIM | `https://integrate.api.nvidia.com/v1` | `NVIDIA_API_KEY` |
| `google` | Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` | `GEMINI_API_KEY` |

La lista vive en `ia_api.PRESETS` (fuente única): las dos UIs la muestran y
la guardan en el `.env`.

### Ejemplo: Ollama Cloud (acceso gratis)

```env
IA_PROVEEDOR=ollama
IA_BASE_URL=https://ollama.com/v1
IA_MODEL=<modelo del endpoint>     # o "auto" si el proveedor lo resuelve
OLLAMA_API_KEY=...                 # si la cuenta lo exige
```

### Ollama Cloud en la práctica (medido 2026-11-08)

- **"Gratis" son créditos, no tokens**: pay as you go = $0 de cuota pero se
  paga **por token** (comprar créditos); Pro $20/mes = $60 de créditos, Max
  $100 = $300. Los tokens se miden en **$ a la tasa del modelo**
  (ollama.com/pricing). Sin saldo, las llamadas se rechazan.
- **No escribas `IA_MODEL=auto`**: `auto` coge el **primer** modelo de
  `GET /models` (en la cuenta medida era `gpt-oss:120b`). En la UI v2 el campo
  "Modelo:" es un **desplegable** y "Listar modelos" lo rellena con los del
  endpoint.
- **Medido sobre 736 avisos** (mismo corpus y código, pipeline completo):

  | | Nube `gemma4:31b` | Local `gemma4-e2b-qat` |
  |---|---|---|
  | Tiempo del pase IA | 8,2 min | 81,3 min |
  | Coste | 6,7% del free usage | $0 |
  | Campos / requisitos | 1335 / 1948 | **2288 / 2879** |
  | Paso 5 (calificada / sin_requisitos) | 132 / 121 | **220 / 11** |

  La **local gana en calidad de dato**, la nube en velocidad. La caché de IA
  separa por **proveedor+modelo** (`ia_api._cache_key`) → comparar es seguro.

### Qué cambia al usar un proveedor externo

1. **No se arranca nada local**: `ia_servidor.asegurar_servidor()` devuelve
   `None` si el endpoint no es de esta máquina (antes fallaba con
   *"Servidor EXTERNO no responde"* porque buscaba `/health`).
2. **Degradación del formato de respuesta**: muchos OpenAI-compatible no
   aceptan `response_format: json_schema` estricto (→ HTTP 400). El cliente
   degrada solo: `json_schema` → `json_object` → sin `response_format`
   (el prompt ya pide JSON). Un 429/404 **no** degrada: son errores reales.
3. **Preflight con el mensaje correcto**: si no responde, el error dice qué
   revisar (URL, modelo, API key) en vez de "arranca llama-server".
4. **Privacidad**: el texto de los avisos (descripción, requisitos y perfil)
   **sale de la máquina**. Por eso:
   - la UI pide confirmación antes de enrichcer con IA no local
     (botón "Enriquecer" y "Flujo completo");
   - el CLI pide confirmación por consola (`--confirmar-externo` la omite
     para corridas no interactivas);
   - el pase deja el aviso en el log de la corrida.

### Límites (opt-in y ajustables)

| Variable | Qué limita | Vacío |
|---|---|---|
| `IA_MAX_LLAMADAS` | llamadas HTTP por corrida | sin tope |
| `IA_RPM` | requests por minuto | sin rate limit |
| `IA_MAX_VACANTES` | **avisos a enriquecer por corrida** | sin tope (todo lo pendiente) |

Ningún límite tiene valor fijo: el usuario los sube o los baja cuando
quiere (Configuración → IA externa, en ambas UIs, o editando el `.env`).
`IA_MAX_VACANTES=0` también significa "sin tope".

## Ejecutar el pase

```powershell
python run_enriquecimiento.py
python run_enriquecimiento.py --solo-criticos   # sin campos secundarios
```
El script hace **preflight** (aborta de inmediato con error claro si el
servidor está apagado — antes esto se traducía en más de 150 fallos falso),
luego pases de críticos en ciclos (para hasta cuando deja de avanzar) y
finalmente un pase completo con secundarios.

### Avisos estancados: no se reintentan (2026-11-08)

El modelo es **determinista a temp 0.1**: un aviso al que el modelo no le
puede extraer el campo devuelve SIEMPRE lo mismo. Reintentarlo en el siguiente
ciclo es trabajo tirado (en la corrida local, el ciclo 3 reintentó **433
avisos y llenó 0**).

- `run_ia_enrichment(..., exclude_ids=...)` salta esos ids **antes de elegir
  lote** → ni una llamada de IA.
- `run_ia_enrichment` devuelve **`ids_estancados`**: los avisos que no
  rindieron (`failed` = el modelo no halló el campo; `skipped` = devolvió lo
  que ya estaba).
- `pase_completo` los acumula y los excluye del **siguiente ciclo y del pase
  completo** (no se reintentan ni ahí).

### El consumo real queda guardado (2026-11-08)

`IAClient.tokens_in/out` vivían solo en memoria y se perdían al terminar el
pase. Ahora:

- `pase_completo` usa **un único cliente** para todo el pase (los tokens se
  acumulan), lo **cierra al terminar** y devuelve
  `resumen["uso"] = {llamadas, tokens_in, tokens_out}`.
- `pipeline_metricas.detalle_etapa("ia")` guarda ese `uso` en
  `pipeline_etapa.detalle_json` → se consulta con
  `jobpulse-v15 pipeline etapas --json` (clave `uso`).
- Ejemplo medido (25 avisos, IA local, caché nueva): **123 llamadas**,
  **52 827 tokens in / 3 901 tokens out**.

## Configuración .env

```
IA_PROVEEDOR=custom
IA_BASE_URL=http://127.0.0.1:8081/v1
IA_MODEL=gemma4-e2b-qat
IA_API_KEY=...            # llama.cpp acepta cualquier valor

# IA externa (alternativas a la local): Ollama Cloud, Ollama local,
# LM Studio, OpenRouter, NVIDIA, Gemini o cualquier OpenAI-compatible.
# IA_PROVEEDOR=ollama
# IA_BASE_URL=https://ollama.com/v1
# IA_MODEL=gpt-oss:120b
# OLLAMA_API_KEY=...

# Límites (opt-in, vacío = sin tope):
# IA_MAX_LLAMADAS=
# IA_RPM=
# IA_MAX_VACANTES=
```

Variables de rutas (compartidas por `start_ia_server.py` y el instalador):

```
IA_MODEL_DIR=D:\Models\gemma-4-E2B-it-qat-UD-Q4_K_XL
IA_LLAMA_SERVER=D:\llama-b11662-bin-win-vulkan-x64\llama-server.exe
IA_LLAMA_RELEASE=...       # opcional: URL del zip de otro build/etiqueta
```

## Instalación en equipo nuevo (requisitos mínimos)

Un solo comando instala y verifica todo. Es idempotente: re-ejecutarlo
reanuda descargas donde quedaron.

```powershell
instalar-modelo-ia.bat                 # instala lo que falte
instalar-modelo-ia.bat --check         # solo verifica (modelo + llama-server)
python instalar_modelo_ia.py --solo-modelo   # solo los 3 GGUF
python instalar_modelo_ia.py --solo-llama    # solo llama.cpp
```

Qué instala, en orden:

| Paso | Qué | Fuente |
|---|---|---|
| 1 | `huggingface_hub` (descarga con reanudación) | pip (`pip install -e .[ia]` lo declara) |
| 2 | Modelo **Gemma 4 E2B QAT**: main (2.62 GB) + mmproj BF16 (987 MB) + MTP draft Q4_0 (59 MB) | **Unsloth** `unsloth/gemma-4-E2B-it-qat-GGUF` (hashes SHA256 fijados en `src/jobpulse_v15/instalacion_ia.py` y verificados con `--check`) |
| 3 | `llama-server.exe` build Vulkan (solo si no existe) | release de `ggml-org/llama.cpp` |

Requisitos mínimos para correr: Windows x64, GPU con Vulkan y **≥ 4 GB de
VRAM libres** (o CPU: corre, mucho más lento), **~5 GB de disco** y
Python 3.11+ con `pip install -e .[ia]`. Tras instalar, arrancar con
`ia-server.bat` (verifica, carga el modelo y espera health en el 8081).

## Extraccion de perfil desde CV (capa IA, O6.2)

`src/jobpulse_v15/cv_ia.py`: convierte el texto de un CV (PDF/DOCX/TXT via
`read_cv_text`) en un perfil **harvard-ats-v1** usando el modelo del `.env`.
El extractor de reglas (`candidate_profile.py`) queda para ofertas; para CVs
solo sacaba idiomas/anios.

Flujo completo probado (2026-10-25, 2 motores x 4 formatos):

```
read_cv_text -> extraer_cv_ia (IAClient del .env) -> sanea_harvard
             -> facts_desde_perfil_dict (profile_model) -> dialogo revision UI
             -> import_candidate_profile_facts (import revertible)
```

- **Agnostico al motor**: mismo codigo con Gemma local (`IA_PROVEEDOR=custom`,
  puerto 8081) y Gemini (`IA_PROVEEDOR=google` + `GEMINI_API_KEY`, modelo
  explicito porque `IA_MODEL` del .env es el local). Ambos extrajeron 39 facts
  identicos en estructura (39 = 5 contact + 1 summary + 3 education + 7
  experience + 19 skill + 2 certification + 2 language).
- **El modelo no inventa**: prompt exige solo datos presentes (null si falta);
  `sanea_harvard` normaliza tipos sin lanzar (la revision UI es la puerta final).
- **Caché IA**: re-corridas del mismo CV responden instantaneo (0.0s) — no
  confundir con lentitud/exito real en benchmarks.
- Dedupe: los slugs dependen del idioma/nombre del CV (ES vs EN generan codes
  distintos para el mismo hecho). El diff vs BD marca "nuevo" y el usuario
  decide en el dialogo (dedupe conservador, sin automerge).
- El import es **revertible**: probado import 26 nuevos + 13 updates y
  `revert_last_candidate_profile_import` restauro la BD exactamente (48 facts).

## Modelo local: Gemma 4 E2B QAT (A/B 2026-10-25)

**Canónico desde el 2026-10-25.** Qwen 3.5 2B quedó descartado como modelo de
enriquecimiento:

| Métrica | **Gemma 4 E2B QAT** | Qwen 3.5 2B |
|---|---|---|
| Pase completo (175 jobs) | **10.3 min** (618s) | ~67 min |
| A/B 5 jobs crudos, misma caché vacía | **50.9s / 11 campos llenados** | 90.0s / 2 campos |
| Resultado del pase | skills 100%, languages 97.7% | languages quedaba en 23% |

Config del servidor (comando vivo en `start_ia_server.py`): modelo
`gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf` + mmproj + **MTP draft** (`--spec-type
draft-mtp`, decoding especulativo), **8k ctx** (suficiente: el pipeline trunca
a ~1.2k tokens de entrada + 600 de salida), KV q8_0, `--metrics`.

Lecciones operativas del A/B:

- **La caché en disco falsea benchmarks**: Qwen "respondió" en 3.1s pegando a
  entradas del pase anterior. Todo benchmark debe aislar caché con
  `JOBPULSE_IA_CACHE` — `tools/comparar_ia.py` ya lo hace.
- **Contexto**: 8k es el punto dulce para este pipeline (4k alcanzaría; 16k era
  desperdicio de VRAM de KV). Subir a 16k solo si O6 manda CVs completos.
- **Flanco conocido**: si el modelo lista >10 skills el JSON se trunca a los
  600 tokens de `max_tokens` (falla tras 3 reintentos). Si reaparece a menudo,
  subir skills a 900.

Resultado del pase con Gemma (2026-10-25): skills 15→**0**, languages
135→**4**, city 28→24, region 14→13. Quedan 23 `work_mode='unknown'` (el texto
no menciona modalidad — honesto) y 82 salary sin texto en la fuente (no
extraíble). Los 24 sin city son en su mayoría postings "Virtual/Remote" o de
LATAM genérico — ver `tools/huecos_restantes.py`.

## Depuración (guía rápida)

| Síntoma | Causa | Solución |
|---|---|---|
| `servidor no responde` en preflight | llama-server apagado | `python start_ia_server.py` o arrancarlo a mano |
| `No se pudo parsear JSON ... Unterminated string` | modelo verboso + `max_tokens` bajo | skills ahora pide 600; si vuelve a pasar, sube tokens o cambia a un modelo mayor |
| `work_mode` queda `unknown` para siempre | el texto de la oferta no menciona modalidad | correcto: se registra `unknown` de verdad (la IA dice 'unknown'), no reintenta al infinito |
| jobs con `skills='null'` en BD | bug viejo del guardado (GET) | ya corregido + script `limpiar_null.py` |

## Estado tras los fixes

- Preflight de servidor antes de cada pase (`verificar_servidor_ia`).
- Reintentos por campo: 3 intentos con backoff (1s, 2s).
- `only_critical=False` ahora SÍ incluye jobs que solo le faltan campos
  secundarios (antes el filtro descartaba y el pase completo era imposible).
- Guardado dinámico: UPDATE solo de columnas tocadas; corregidos los bugs
  que seteaban `salary_max`/`salary_currency`/`salary_period` a NULL.
- Tests: `tests/test_ia_enrichment.py` (11 tests con IA simulada).
