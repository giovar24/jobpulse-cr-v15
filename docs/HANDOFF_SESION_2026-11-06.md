# Handoff — Sesión 2026-11-06

**TL;DR**: Cerrada la **Ola 3 de O13 (cobertura de fuentes)**. Las dos fuentes
que daban **0 avisos** ya dan: **LinkedIn 60 avisos** (el scraper se reescribió:
el listado público se pide por HTTP simple y las tarjetas son `div.base-card`,
no las clases ofuscadas) y **Elempleo 3 avisos** (el "muro de login" era el
botón "Inicia sesión" del encabezado; además la empresa ya no viene en
`datalayertag` y el filtro de país miraba el cantón en vez del país). Se añadió
el estado **`requires_login`** en la salud de sitios (migración **022**): un
sitio que pide iniciar sesión **no está roto** (no cuenta en la racha de ceros,
la UI v2 lo marca con 🔑). Y se descubrió (midiendo) que **la cookie de ANE es
de sesión**: Chromium no la escribe en disco, así que al reabrir Brave se
perdía → nuevo módulo `jobpulse_v15.sesion_navegador` que la guarda aparte
(`data/usuario/sesiones/`, fuera del repo) y la restaura. **ANE verificado con
dos barridos seguidos** (24 avisos cada uno) y también con Brave **cerrado y
reabierto** (24 avisos restaurando la sesión). La **BD real** quedó en
**esquema 22** (migración aplicada con respaldo previo: 705 avisos, 129 sitios,
134 corridas, `integrity_check ok`, 0 violaciones de FK). Suite completa:
**1083 passed + 247 subtests** (base 1021 → **+62**).

**Después (Ola 4.1, calidad del dato)**: se midió el "re-barrido de detalle" y
el hueco real resultó ser otro: **el parser de la ficha de ANE descartaba
campos** ("Nivel académico", "Experiencia laboral", "Estudio técnico") → el
motor no podía evaluar esas dimensiones. Se amplió el parser, se añadió el
**re-barrido de detalle** (`scrape ane --site ane-cr --revisitar`, que vuelve a
bajar el detalle de los avisos YA guardados, porque el listado de ANE solo
muestra lo nuevo) y el **re-análisis por texto nuevo** (si el `text_hash` del
análisis vigente ya no cuadra con el texto del aviso → se re-analiza).
Medido sobre una **copia** de la BD real: los 120 avisos ANE guardados tienen
**más texto** (+24 nuevos = 729), **9 de 705 cambian de estado** (7 a
`descartada` con evidencia literal "Licenciatura (Requerido)", 2 a
`revisar_a_mano` porque el texto NO dice "Requerido") y
**`educacion_no_confirmada` NO cambia** (31 → 31). **Aplicado a la BD real con
OK del usuario** (solo los 120 existentes): respaldo
`data/backups/pre_ola4_20261106_151857.db` → re-barrido (120 revisados, 0
omitidos) → re-análisis (120) → backfill → **corrida `20261106_152304`** →
evidencia OK (137 verificaciones, 0 fallos) → `db check` ok. Texto total de
los avisos ANE: 115.601 → **141.967 chars** (+23 %). `educacion_no_confirmada`
sigue en **31**.

> ℹ️ Esta sesión continúa la del **2026-11-05** (`docs/HANDOFF_SESION_2026-11-05.md`):
> Ola 1 y Ola 2 de O12 ya estaban hechas y pusheadas.

---

## 1. La decisión que ordena todo lo demás (no cambió)

> **Ser rechazado de un trabajo NO significa que no se es apto para él.**
> (decisión del usuario, 2026-10-27)

| | Qué es | Módulo |
|---|---|---|
| **Ajuste técnico** | ¿el perfil cumple lo que pide el aviso? | `viabilidad.py` |
| **Estado del proceso** | ¿qué decidió el reclutador? | `postulaciones.py` |

Y la regla que se aplicó hoy: **lo que el scraper devuelve tiene que existir en
la web**. Un scraper que da 0 avisos "sin decir por qué" es peor que uno que
falla: el usuario no sabe si el sitio cambió, si le falta sesión o si la
búsqueda no trae nada. Por eso el estado nuevo (`requires_login`) y los
mensajes del log dicen **qué** pasa.

---

## 2. Lo que se hizo (Ola 3 de O13)

### 2.1 LinkedIn — 0 → 60 avisos

El diagnóstico (medido en vivo, no de memoria):

| Lo que se creía | Lo que es |
|---|---|
| `/jobs/search-results/` sirve el listado | Responde **999**. El listado que funciona es `/jobs/search/?keywords=…&location=…` |
| Las clases están ofuscadas (`fa4afe…`) | El HTML trae `div.base-card` + `data-entity-urn="urn:li:jobPosting:<id>"` |
| Es un login-wall | El **navegador** sin sesión recibe authwall; por **HTTP simple** el listado responde 200 con 60 items |

- `linkedin.py` reescrito: `_listar_http` (BeautifulSoup) → `_json_ld`
  (respaldo) → `_listar_navegador` (CDP: fusiona resultados + cookies) →
  `_fusiona` → `_a_ofertas`; detalles por `jobs-guest` (`_fetch_details_guest`).
- **Rate-limit medido**: sin espera el endpoint aguanta **10** peticiones y
  luego da **429**; con **1,5 s** entre peticiones: **19 OK / 0 429** → por eso
  `request_delay` = 1,5 s por defecto y, ante un 429, se espera y se reintenta
  (sin probar la URL alternativa: sería el doble de tráfico).
- Tests: `tests/test_linkedin.py` (16) con el **HTML real** recortado.

### 2.2 Elempleo — 0 → 3 avisos

Los **3 bugs reales** (los tres dan 0 avisos juntos):

1. **Falso muro de login**: el encabezado **siempre** trae el enlace "Inicia
   sesión" (es el botón de entrar) → `_es_login_wall` cortaba el barrido en la
   página 1. Ahora un muro real es un **formulario de acceso**; si hay
   `.result-item`, no hay muro.
2. **`.ee_list-item` NO son las ofertas**: es el **menú lateral**. Las ofertas
   siguen en `.result-item` + `.js-area-bind.area-bind`.
3. **El filtro de país miraba el cantón**: la ubicación es "San José" y el país
   ("Costa Rica") va aparte → se descartaban **todas**.

Además: empresa en `.js-offer-company`, descripción en `.description-block`,
requisitos en las etiquetas `.requirements-content`, ciudad de la ficha en
`.js-offer-city`, y `site_config["max_ofertas"]` para acotar el barrido (cada
oferta abre su ficha). Tests: `tests/test_elempleo.py` (10).

### 2.3 `requires_login` — la salud de sitios distingue "login" de "roto"

| Pieza | Valor |
|---|---|
| Salud (`source_sites.health_status`) | `requiere_login` |
| Corrida (`source_run_sites.status`) | `requires_login` |
| Racha de ceros | **NO** cuenta este estado |
| `review_required` | **sí** |
| `site mark-reviewed` | Lo reconoce, pero la salud sigue diciendo `requires_login` |
| UI v2 | 🔑 en la fila de la sonda + lista de sitios que piden login en el log del barrido |

Migración **022** (SQLite no deja cambiar un `CHECK` con `ALTER` y
`PRAGMA foreign_keys` no se puede cambiar dentro de una transacción → la
migración **recrea** las dos tablas y gestiona su propia transacción; el
marcador en el SQL es `-- jobpulse:transaccion-propia` y lo respeta `db.py`).
El código: `jobpulse_v15.requiere_login.RequiereLoginError` → `ingestion.py` la
traduce → `repository.record_site_result(status=…)`.

### 2.4 La sesión de ANE entre arranques del navegador (hallazgo de la medición)

Flujo medido el 2026-11-06 (login → 24 avisos → cerrar Brave → reabrir → raspar):

| Situación | Resultado |
|---|---|
| Login → raspar con el Brave vivo | ✅ 24 avisos |
| Login → cerrar (ordenado) → reabrir → raspar | ❌ "ANE: sin sesión de detalle" → 0 avisos (`requires_login`) |
| Login → **guardar la sesión** → cerrar → reabrir → raspar | ✅ **24 avisos** (restaurando la sesión) |

**Causa**: `ASP.NET_SessionId` es una cookie de **sesión** (`expires = -1`).
Chromium **no** escribe las cookies de sesión en disco al salir: el cierre
ordenado de O12 · 1.5 no la salva (corrige el cierre *abrupt*, no este caso).

**Arreglo**: `jobpulse_v15.sesion_navegador` guarda las cookies del sitio tras
un login exitoso en `data/usuario/sesiones/<sitio>.json` (**fuera del repo**:
`data/usuario/` está gitignoreado; es un token de sesión, o sea un secret) y
las restaura en el contexto del navegador cuando falta la sesión. Si la sesión
del servidor caducó, el archivo se borra (no se reintenta para siempre).
Tests: `tests/test_sesion_navegador.py` (18) + 2 en `tests/test_ane_login.py`.

### 2.5 Lo que NO se tocó (a propósito)

- **La UI clásica** (`ui.py`): intacta. Ya muestra el `health_status` crudo
  ("requiere_login (revisar)") sin necesidad de tocarla.
- **Los umbrales 0.60 / 0.80** y el motor de matching: congelados.
- **`educacion_no_confirmada`**: sin tocar (lo firma una segunda persona).
- **La BD real**: solo se aplicó la migración 022 (con respaldo previo en
  `data/backups/pre_mig022_20261106_130349.db`). Ninguna medición la tocó:
  los barridos fueron sobre `%TEMP%\opencode\ane_check.db`.

---

## 3. Decisiones de diseño

| Tema | Decisión |
|---|---|
| LinkedIn: HTTP o navegador | **HTTP primero**, navegador como refuerzo que fusiona. El navegador sin sesión recibe authwall: pedir el listado por HTTP es lo que lo desbloquea |
| LinkedIn: rate-limit | 1,5 s entre peticiones (medido) y reintento con espera. Ante un 429 **no** se prueba la otra URL (doble tráfico → otro 429) |
| Elempleo: ¿muro de login? | Solo un **formulario** de acceso lo es. El botón del encabezado nunca lo es (siempre está) |
| `requires_login` | Es un estado **propio**, no un error ni un `zero_results`: no cuenta en la racha de ceros pero sí pide revisión |
| Migraciones que recrean tablas | El SQL se marca con `-- jobpulse:transaccion-propia` y `db.py` deja que la migración gestione su propia transacción (FK fuera → tabla nueva → copia → borrar → renombrar) |
| Sesión del navegador | Se guarda **fuera del repo** (`data/usuario/sesiones/`), solo del sitio (no todo el tarro de cookies) y sin `expires` en las cookies de sesión. Si el servidor la caduca, el archivo se borra |

---

## 4. Metas (tabla canónica O1–O14)

| Objetivo | Qué es | Estado |
|---|---|---|
| O1–O6 (pipeline scrape → matching) | — | ✅ Hecho (sesiones previas) |
| O7 (IA local/browser) | — | ✅ Hecho |
| O8/O10 (retención + diagnóstico + filtros) | — | ✅ Hecho |
| O2.2 (Req. + filtro) · O3 (salud de sitios) | — | ✅ Hecho (2026-11-04) |
| Capa B (`codigo_canonico` del perfil) | — | ✅ Hecho y efectivo en la BD real |
| Motor de viabilidad (ajuste técnico) | — | ✅ Hecho (pesos = priors; falta ground truth propio) |
| Postulaciones (correo + Workday) | — | ✅ Hecho en código; falta validación en vivo |
| Bloque de ALINEACIÓN (campos estructurados) | — | ✅ Hecho **y aplicado en la BD real** |
| **O11 IA externa / motor intercambiable** | — | ✅ Hecho (2026-11-05) |
| **O12 Paridad CLI/UI** | La UI debe dar los mismos números que la CLI | ✅ **Olas 1 y 2** (2026-11-05): 231 → 11 `sin_requisitos` |
| **O13 Cobertura de fuentes** | Que el barrido traiga los avisos que existen | 🟢 **Ola 3 COMPLETA (2026-11-06)**: LinkedIn 0 → 60 · Elempleo 0 → 3 · `requires_login` · sesión de ANE entre arranques · ANE con dos barridos seguidos |
| **O14 Control del coste de la IA** | Límites opt-in y ajustables | ✅ Hecho (2026-11-05) |
| `educacion_no_confirmada` | 31 casos | ⏳ **ABIERTO** (firma de una 2ª persona) |
| O5.3 (re-barrido de descripciones basura) | 43 descripciones <200 chars (35 de ANE) | 🟢 **HECHO Y APLICADO (2026-11-06)**: el corpus ya coincidía con la fuente; el hueco real era el **parser** (campos descartados). Parser ampliado + `scrape ane --revisitar` + re-análisis por texto nuevo. En la BD real: texto ANE 115.601 → 141.967 chars, **9 de 705 cambian de estado**, `educacion_no_confirmada` 31 → 31, corrida `20261106_152304` |
| O6.4 (dedupe slugs ES/EN) | — | ⏳ Parcial |
| O4 (calibración gate-vs-IA) | — | 🟡 Proponer cerrar como *superseded* |
| O8.2 / O8.4 / O9 / pestañas nuevas UI v2 | — | ⏳ Pendiente (Ola 4) |

**Siguiente ola** (plan en `docs/PLAN_MEJORAS.md`): **Ola 4 — calidad del
dato**: 4.1 (parser de ANE + re-barrido de detalle + re-análisis por texto
nuevo: **MEDIDO**, falta aplicar a la BD real) · 4.2 curación de la taxonomía
(`concepto_no_normalizado`) · 4.3 métricas por etapa.

---

## 5. Cómo retomar (comandos)

```powershell
# Suite completa (python del SISTEMA; ~11 min)
python -m pytest tests/ -q

# Solo la Ola 3
python -m pytest tests/test_linkedin.py tests/test_elempleo.py `
  tests/test_requiere_login.py tests/test_sesion_navegador.py `
  tests/test_ane_login.py tests/test_migraciones.py -q

# Solo la Ola 4.1
python -m pytest tests/test_ane_detalle.py tests/test_reanalisis.py `
  tests/test_pipeline.py tests/test_repository.py -q

# ANE: login + barrido (sesión guardada → funciona aunque Brave se cierre)
.\.venv\Scripts\python.exe -X utf8 login_ane.py --mantener-abierto
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 scrape ane --site ane-cr

# ANE: re-barrido de DETALLE (avisos ya guardados; corrige el texto viejo)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 scrape ane --site ane-cr --revisitar
#   (--limite N para revisar solo N)

# Estado de la BD y evidencia (exit 0 = todo cuadra)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 db check
.\.venv\Scripts\python.exe -X utf8 verificar_evidencia.py

# Health de los sitios (los que piden login)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 site list --needs-review
```

---

## 6. Archivos clave

| Archivo | Qué es |
|---|---|
| `src/jobpulse_v15/linkedin.py` | **Reescrito** — listado por HTTP (`div.base-card` + JSON-LD), refuerzo por navegador, rate-limit 1,5 s y reintento ante 429 |
| `src/jobpulse_v15/elempleo.py` | Muro de login real, `.result-item`, empresa `.js-offer-company`, filtro país+cantón, `max_ofertas` |
| `src/jobpulse_v15/requiere_login.py` | **NUEVO** — `RequiereLoginError` + `mensaje_requiere_login` |
| `src/jobpulse_v15/sesion_navegador.py` | **NUEVO** — guarda/restaura la sesión de un sitio (`data/usuario/sesiones/`) |
| `src/jobpulse_v15/migrations/022_site_requiere_login.sql` | **NUEVO** — `health_status='requiere_login'`, `source_run_sites.status='requires_login'` (recrea las tablas; transacción propia) |
| `src/jobpulse_v15/db.py` | Soporte de migraciones con `-- jobpulse:transaccion-propia` |
| `src/jobpulse_v15/repository.py` | `record_site_result(status=…)` + salud `requiere_login` + `mark_site_reviewed` |
| `src/jobpulse_v15/ingestion.py` | Traduce `RequiereLoginError` → `requires_login` |
| `src/jobpulse_v15/scraper.py` | `ESTADO_REQUIERE_LOGIN` y su mensaje |
| `src/jobpulse_v15/ane.py` | `_asegurar_sesion` + restauración de la sesión guardada |
| `src/jobpulse_v15/ane_login.py` | Guarda la sesión tras un login OK; docstring del cierre corregido |
| `src/jobpulse_v15/ui_v2/data/fuentes.py` · `ui_v2/tabs/configuracion.py` · `ui_v2/tabs/scraping.py` | 🔑 en la tabla de sondas y lista de sitios que piden login |
| `tests/test_linkedin.py` (16) · `test_elempleo.py` (10) · `test_requiere_login.py` (8) · `test_sesion_navegador.py` (18) | **NUEVOS** de la Ola 3 |
| `src/jobpulse_v15/ane.py` | **Ola 4.1**: `_parse_detalle` lee "Nivel académico"/"Experiencia laboral"/"Estudio técnico" (y el contexto) · `_oferta` (una sola implementación de la oferta) · `fetch_detalles_conocidos`/`_revisitar` (re-barrido de detalle) |
| `src/jobpulse_v15/analysis_flow.py` | **Ola 4.1**: `avisos_con_texto_cambiado` + `reananalizar_texto_cambiado` (señal por `text_hash`) |
| `src/jobpulse_v15/pipeline.py` | La etapa `reanalisis` ahora incluye el re-análisis por texto nuevo (`texto_candidatos`/`texto_reanalizados`) |
| `src/jobpulse_v15/repository.py` | `list_source_records(site_id)` (avisos guardados + su URL, para el re-barrido) |
| `src/jobpulse_v15/cli.py` | `scrape ane --revisitar [--limite N]` |
| `tests/test_ane_detalle.py` (14) · `tests/test_reanalisis.py` (21) | **NUEVOS** de la Ola 4.1 |
| `docs/SITIOS_PROBLEMATICOS.md` | Reescrito: 4 sitios, `requires_login`, sesión de ANE, rate-limit de LinkedIn |
| `docs/PLAN_MEJORAS.md` · `DESARROLLO_v15.md` · `AGENTS.md` | Ola 3 completada + Ola 4.1 medida; esquema 22 |

---

## 7. Contexto (estado de la BD real)

- **BD real `data/jobpulse_v15.db`**: **esquema 22**, **705 avisos**, 129 sitios,
  136 corridas de sitio, 825 `job_analysis` (705 vigentes + 120 del
  re-análisis), 1964 `job_match` (1 corrida válida). `integrity_check ok`,
  0 violaciones de FK.
  Corrida Paso 5 vigente `20261106_152304` (aplicada por la Ola 4.1):
  calificada 237 · revisar 320 · descartada 96 · datos_insuf 41 ·
  sin_requisitos 11 · `educacion_no_confirmada` 31.
  Corrida anterior (sigue en la BD, `valida=0`): `20261104_231932`
  (calificada 239 · revisar 324 · descartada 89 · datos_insuf 42 ·
  sin_requisitos 11).
- **Respaldo**: `data/backups/pre_ola4_20261106_151857.db` (antes de la Ola
  4.1), `data/backups/pre_mig022_20261106_130349.db` (antes de la 022) y
  `data/backups/pre_limpieza_20261104_211349.db`.
- **Mediciones de la Ola 3** (todas sobre `%TEMP%\opencode\ane_check.db`, copia
  de la BD real): ANE 24 avisos (1er barrido, 24 nuevos) → 24 avisos (2º
  barrido, 24 duplicados) → salud `healthy`, `review_required=False`,
  `consecutive_zero_runs=0`.
- **Salud de sitios en la BD real**: `ane-cr` está `healthy`; `linkedin-cr` y
  `elempleo-cr` siguen en `zero_results` con **2** ceros consecutivos (son las
  corridas del scraper **roto**, antes del arreglo). El próximo barrido
  exitoso los deja en `healthy` y reinicia el racho (no se tocaron a mano:
  la salud se recalcula con datos, no se edita).
- **Config de los sitios** (declarativa, en `source_sites.site_config_json`):
  `linkedin-cr` → `{"pages": 2, "search_text": "Soporte Técnico"}` ·
  `elempleo-cr` → `{"adapter": "elempleo", "country_query": "Costa Rica"}`.
  Si el barrido de Elempleo tarda demasiado (cada oferta abre su ficha),
  añadir `"max_ofertas": 20` a su config.
- **`.env`**: `IA_PROVEEDOR=custom`, `IA_BASE_URL=http://127.0.0.1:8081/v1`,
  `IA_MODEL=gemma4-e2b-qat` (sin `IA_MAX_VACANTES` → sin tope) ·
  `BRAVE_CDP_PORT=9222`, `BRAVE_PERFIL=Default`.
- **La sesión de ANE guardada** queda en `data/usuario/sesiones/ane.json`
  (gitignoreado). Si se borra, el siguiente barrido pide login otra vez.
- **Medición de la Ola 4.1** (sobre `%TEMP%\opencode\ola4.db`, copia de la BD
  real): barrido ANE → **24 avisos nuevos** (122031+) · re-barrido de detalle
  → los **120 avisos ANE guardados** con **más texto** (todos) · re-análisis
  por texto nuevo → **120 re-analizados**, 0 errores · backfill → 1 requisito
  sin concepto · Paso 5 nuevo (`ola4_final`) → **729 avisos**: calificada 242
  · revisar 336 · descartada 98 · datos_insuf 45 · sin_requisitos 24 ·
  **`educacion_no_confirmada` 31 (sin cambios)**. **9 de 705** cambian de
  estado (7 → `descartada/titulo_universitario_requerido` con evidencia
  "Nivel académico: Licenciatura (Requerido)." o "Bachillerato Universitario
  en …"; 2 → `revisar_a_mano/educacion_no_cumple` porque el texto NO dice
  "Requerido").

---

## 8. Pendiente inmediato

1. **Ola 4 — seguir** (`docs/PLAN_MEJORAS.md`): 4.2 curación de la taxonomía
   (`concepto_no_normalizado`: 1988 variantes; en la BD real la cola de
   requisitos sin `codigo_canonico` es **1**) · 4.3 métricas por etapa.
2. **Los 24 avisos ANE nuevos** (122031+) que se detectaron al medir: el
   usuario decidió **no** meterlos en la Ola 4.1 (entran en el barrido normal,
   con su pase de IA). Si se quieren ya: `scrape ane --site ane-cr` (24
   nuevos) → `analysis extract-pending` → `run_enriquecimiento.py` → re-análisis
   → backfill → `run_paso5.py`.
3. (Opcional, con permiso del usuario) migrar la **UI clásica** al orquestador
   `pipeline.py` (usa las mismas implementaciones por etapa, pero mantiene su
   propio flujo; la UI clásica no se toca sin pedirlo).
4. `educacion_no_confirmada` (31 casos): **NO** actualizar estados hasta que
   una **segunda persona** firme `docs/PASO5_REVISION_PENDIENTES.md` (ya
   regenerada para la corrida `20261106_152304`).
5. Decidir si el **rate-limit de LinkedIn** sube de 1,5 s según la carga real
   (medido: 10 peticiones sin espera → 429).

---

## 9. Commits de esta sesión

- **HEAD (aplicación a la BD real)** — `docs(o5.3): Ola 4.1 aplicada a la BD real (texto de ANE corregido, corrida 20261106_152304)` — evidencia + hoja de firma regeneradas, docs actualizadas.
- `280b4e7` — `feat(o5.3): Ola 4.1 - parser de ANE completo, re-barrido de detalle y re-análisis por texto nuevo` (pusheado) — parser ampliado, `scrape ane --revisitar`, `reananalizar_texto_cambiado`, medición sobre copia (9 de 705 cambian de estado; `educacion_no_confirmada` 31 → 31).
- `14bba25` — `feat(o13): Ola 3 - cobertura de fuentes (LinkedIn, Elempleo, requires_login, sesión ANE)` — scrapers reescritos, migración 022, `requiere_login.py`, `sesion_navegador.py`, 52 tests nuevos + 2 de UI v2 + 2 de ANE, docs actualizadas. Suite: **1083 passed + 247 subtests**.
- `680024f` — `feat(o12): Ola 2 - orquestador único (pipeline.py) y botones "Procesar"/"Enriquecer IA" en la UI v2` (pusheado).
- `21af318` — `feat(o12): Ola 1 - paridad CLI/UI (re-análisis, evidencia, login ANE)` (pusheado).
