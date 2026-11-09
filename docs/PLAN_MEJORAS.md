# Plan de mejoras — orden por impacto y esfuerzo

> Actualizado 2026-11-06. El orden va de **lo que más duele hoy** (y se
> arregla con poco código) a **lo que puede esperar** (mucho esfuerzo, poco
> efecto inmediato). Cada bloque dice qué se toca, por qué y cómo se sabe que
> quedó bien.

## A qué metas del proyecto pertenece cada ola

| Ola | Meta | Qué cierra |
|---|---|---|
| 0 (hecha) | **O11** IA externa · **O14** límites opt-in | La IA no está atada a la máquina del usuario |
| 1 (hecha) | **O12** paridad CLI/UI | La UI da los mismos números que la CLI (231 `sin_requisitos` → 11) |
| 2 (hecha) | **O12** paridad CLI/UI | Una sola implementación del pipeline (orquestador + botones) |
| 3 (hecha 2026-11-06) | **O13** cobertura de fuentes | LinkedIn 0 → 60 avisos · Elempleo 0 → 3 · `requires_login` · sesión de ANE entre arranques |
| 4 (4.1 hecha 2026-11-06) | O5.3 / taxonomía / métricas | Calidad del dato (parser de ANE + re-barrido de detalle, aplicada a la BD real) |
| 5 | O4, upsert, embeddings | Se pueden dejar de último |

## Contexto: el problema de fondo

El pipeline por CLI (el que produjo la corrida `20261104_231932`) y el de las
UI no hacen lo mismo. Medido sobre una **copia** de la BD real:

| Métrica | Flujo CLI | Flujo UI (simulado) | Δ |
|---|---:|---:|---:|
| Requisitos guardados | 2478 (1145 `rule` + 1333 `source_field`) | 1145 (solo `rule`) | −54 % |
| Avisos `sin_requisitos` | 11 | **231** | +220 invisibles |
| Avisos `calificada` | 239 | 207 | −32 |

Causa: `analysis_flow.extract_job_analysis` lee `jobs.skills`/`jobs.languages`
**en el momento del análisis**, y esos campos los produce el pase IA, que en
la UI corre *después*. El paso "re-análisis con campos estructurados"
(`enrich requirements-source --apply`) **no existe en ninguna UI**.

Todo el plan attack esa divergencia sin tocar las reglas de negocio
(umbrales 0.60/0.80 congelados, corridas nuevas, `educacion_no_confirmada`
solo con segunda firma).

---

## Ola 0 — YA HECHO: IA externa (Ollama / LM Studio / cloud gratis)

**Por qué:** otro usuario puede no tener GPU ni querer instalar llama.cpp;
Ollama Cloud y LM Studio dan acceso (a veces gratis) al mismo enriquecimiento.

| Cambio | Dónde | Estado |
|---|---|---|
| `ia_servidor.es_endpoint_local()` + `asegurar_servidor()` no arranca nada local con endpoint externo | `src/jobpulse_v15/ia_servidor.py` | ✅ |
| Degradación `json_schema` → `json_object` → sin `response_format` | `src/jobpulse_v15/ia_api.py` | ✅ |
| Presets unificados (`ollama`=Cloud, `ollama-local`, `lmstudio`, …) en las dos UIs | `ia_api.PRESETS` + `configuration_window.IA_PROVIDERS` | ✅ |
| Aviso de privacidad + confirmación (UI) / `--confirmar-externo` (CLI) | `ui.py`, `run_enriquecimiento.py` | ✅ |
| Tope de avisos **opt-in y ajustable** (`IA_MAX_VACANTES`, vacío = sin tope) | `ia_api.py`, `ia_enrichment.py`, ambas UIs | ✅ |
| Tests | `tests/test_ia_externa.py` (35 tests, incl. end-to-end HTTP) | ✅ |

**Lo que abre:** el mismo cliente sirve para el enriquecimiento y para las
tareas futuras (matching semántico, extracción de CV, summaries). Sin cambios
de código en el pipeline cuando se cambie de motor.

### Ola 0 · MEDIDO 2026-11-07/08: nube vs local sobre el MISMO corpus

Corrida limpia (736 avisos nuevos) + el pipeline completo dos veces, con el
mismo código y el mismo corpus crudo (la nube en la UI v2; la local restaurando
el respaldo crudo):

| Métrica | ☁️ Ollama Cloud `gemma4:31b` | 💻 Local `gemma4-e2b-qat` |
|---|---|---|
| Pase IA | **8,2 min** | 81,3 min |
| Coste | **6,7% del free usage** | **$0** |
| Campos llenados | 1335 | **2288** |
| skills / languages | 600 / **54** | **733 (99,6%) / 709 (96%)** |
| Requisitos en BD | 1948 | **2879** |
| Reqs de idioma (`espanol`/`ingles`) | 41 / 223 | **471 / 345** |
| Paso 5: calificada / sin_requisitos | 132 / 121 | **220 / 11** |
| `educacion_no_confirmada` | 0 | 29 (firma de 2ª persona) |

**Conclusión**: la IA local gana en **calidad del dato**; la nube gana en
**velocidad** (10×). Para el uso diario, la local (coste $0); la nube sirve
para iterar rápido o si no hay GPU. La **caché separa por proveedor+modelo**
(`ia_api._cache_key`), así que la comparación no está contaminada.

Además: el campo "Modelo:" de la UI v2 pasó a **combobox** y "Listar modelos"
lo **rellena** (`IA_MODEL=auto` cogía el primer modelo de la lista).

---

## Ola 1 — Cerrar el hueco de raíz (impacto ALTO, cambios chicos)

> Objetivo: que la UI produzca **los mismos números** que la CLI.
> Es la ola con mejor relación impacto/esfuerzo.
>
> **✅ COMPLETA (2026-11-05)** — 1.1 `reananalizar_con_campos_fuente` +
> cableado en CLI/UI clásica/UI v2 · 1.2 `cuenta_analisis_obsoletos` (exacto:
> confirma en seco; la SQL sola daba 67 y el re-análisis 0) + badge en ambas
> UIs + `tools/estado_bd.py` · 1.3 guarda `askyesnocancel` · 1.4
> `jobpulse_v15.evidencia` (scripts = envoltorios; botón/indicador en UI v2) ·
> 1.5 login ANE con cierre ordenado. **Medición sobre copia de la BD real
> (705 avisos): `sin_requisitos` 231 → 11 (−220).**

### 1.1 Re-análisis incremental tras la IA — `Ola 1 / paso 1`
- **Qué**: función nueva `reananalizar_con_campos_fuente(repository)` que
  re-analiza **solo** los avisos cuyo análisis vigente tiene 0 requisitos
  `origin='source_field'` pero ya tienen `jobs.skills`/`languages` (la IA los
  llenó después). Usa `analysis_flow.extract_job_analysis` (implementación
  única, no se duplica lógica).
- **Dónde**: `src/jobpulse_v15/analysis_flow.py` (o `pipeline.py` si ya existe).
- **Criterio de aceptación**: sobre la BD real, `sin_requisitos` baja de
  ~231 a ~11 y los `source_field` aparecen en los 705 avisos.
- **Esfuerzo**: bajo (1 función + test). **Riesgo**: bajo.

### 1.2 Detección de análisis obsoleto — `Ola 1 / paso 2`
- **Qué**: consulta barata
  `jobs.skills IS NOT NULL AND NOT EXISTS (req origin='source_field' del
  análisis vigente)` → contador. Se muestra como badge en ambas UIs y en
  `tools/estado_bd.py`.
- **Criterio**: el usuario ve "N avisos con campos estructurados sin
  integrar" antes de creer un resultado.
- **Esfuerzo**: bajo. **Riesgo**: bajo (solo lectura).

### 1.3 Guarda en el Paso 5 — `Ola 1 / paso 3`
- **Qué**: antes de "Ejecutar Paso 5" (UI v2) y del paso 4/5 del flujo
  completo (UI clásica), si hay análisis obsoletos → aviso y confirmación.
- **Criterio**: imposible lanzar un Paso 5 sobre datos obsoletos sin saberlo.
- **Esfuerzo**: bajo. **Riesgo**: bajo.

### 1.4 Evidencia como módulo — `Ola 1 / paso 4`
- **Qué**: mover la lógica de `generar_evidencia_paso5.py` y
  `verificar_evidencia.py` a `src/jobpulse_v15/evidencia.py` (funciones) y
  dejar los scripts como envoltorios thin. La UI puede así mostrar
  "evidencia: al día / desactualizada" tras cada Paso 5.
- **Criterio**: `verificar_evidencia.py` sigue dando exit 0 y la UI puede
  llamarlo sin subprocess.
- **Esfuerzo**: bajo-medio. **Riesgo**: bajo (los scripts quedan igual).

### 1.5 Login ANE sin cerrar Brave — `Ola 1 / paso 5`
- **Qué**: `login_ane.py` hoy cierra el Brave que abrió → la cookie de sesión
  no persiste → el barrido siguiente da "ANE: sin sesión de detalle" y
  **0 avisos**. Login sobre la instancia viva y raspar sin cerrar.
- **Criterio**: dos barridos seguidos con ANE dan avisos (no 0).
- **Esfuerzo**: bajo. **Riesgo**: bajo (es un flujo de login, no de datos).

---

## Ola 2 — Paridad CLI/UI (impacto ALTO, esfuerzo MEDIO)

> **✅ COMPLETA (2026-11-05)** — 2.1 `src/jobpulse_v15/pipeline.py` (etapas
> `scrape → analisis → ia → reanalisis → backfill → paso5 → evidencia`, una
> implementación por etapa) y `run_full_flow.py` pasa a ser un **envoltorio**
> del orquestador · 2.2 botón **"Procesar"** en la pestaña "Scraping" de la UI
> v2 (log + progreso + refresco de las demás pestañas) · 2.3 botón
> **"Enriquecer IA"** (pase IA + re-análisis; con IA externa pide confirmación
> de privacidad antes de enviar el texto) · 2.4 paso 3.5 en el flujo completo
> de la UI clásica (ya hecho en la Ola 1). **Test de paridad**: el camino UI
> (orquestador) y el camino CLI (etapas sueltas) dan el **mismo estado de
> `job_match`** sobre dos bases idénticas (`tests/test_pipeline.py`).
> **15 tests nuevos** + 3 de UI v2. La UI clásica mantiene su flujo (intacta
> por regla del repo); migrarla al orquestador queda como sugerencia 5 de
> `docs/FLUJO_CLI_VS_UI.md`.

### 2.1 Orquestador único `pipeline.py` — `Ola 2 / paso 1`
- **Qué**: `src/jobpulse_v15/pipeline.py` con
  `ejecutar(repository, *, etapas=..., progreso=..., evaluar_todo=False)`.
  Etapas: `scrape → analisis → ia → reanálisis → backfill → paso5 → evidencia`.
  Cada etapa **una sola implementación**, usada por CLI, UI clásica, UI v2 y
  los scripts de la raíz (mismo patrón que ya resolvió la triplicación de
  `analysis_flow`).
- **Criterio**: la UI y `run_full_flow.py` dan **el mismo estado de `job_match`**
  sobre la misma BD (test de paridad).
- **Esfuerzo**: medio. **Riesgo**: bajo (aditivo; no cambia reglas).

### 2.2 Botón "Procesar" en UI v2 — `Ola 2 / paso 2`
- **Qué**: en la pestaña de Scraping o Vacantes, botón que corre el pipeline
  completo con log y progreso (hoy UI v2 no tiene análisis ni enriquecimiento:
  los avisos nuevos quedan `not_analyzed`, `Req.`=0, banda `sin_datos`).
- **Esfuerzo**: bajo (con 2.1). **Riesgo**: bajo.

### 2.3 Botón "Enriquecer IA" en UI v2 — `Ola 2 / paso 3`
- **Qué**: hoy UI v2 solo arranca/apaga el servidor en Configuración; no
  ejecuta el pase. Reusa `ia_enrichment.pase_completo` (con el aviso de
  privacidad si el proveedor no es local).
- **Esfuerzo**: bajo-medio. **Riesgo**: bajo.

### 2.4 Paso 3.5 en el flujo completo de la UI clásica — `Ola 2 / paso 4`
- **Qué**: encadenar re-análisis + backfill entre el paso IA y el matching del
  "Flujo completo" (`ui.py:_post_flujo_completo`).
- **Esfuerzo**: bajo (con 1.1). **Riesgo**: bajo.

---

## Ola 3 — Recuperar plataformas (impacto ALTO, esfuerzo MEDIO, riesgo MEDIO) — **COMPLETADA 2026-11-06**

### 3.1 Selectores de LinkedIn — `Ola 3 / paso 1` — **HECHO**
- **Qué**: el listado que funciona es `/jobs/search/` (no `/jobs/search-results/`,
  que responde **999**) y sus tarjetas son `div.base-card` +
  `data-entity-urn="urn:li:jobPosting:<id>"`. Se reescribió `linkedin.py`:
  listado por **HTTP simple** (BeautifulSoup) con el JSON-LD `ItemList` como
  respaldo, y el navegador (Brave/CDP) como refuerzo que fusiona resultados.
- **Criterio**: ✅ **60 avisos en vivo** (antes 0).
- **Riesgo**: medio → mitigado: `jobs-guest` aguanta ~10 peticiones seguidas y
  luego da 429; con `request_delay` = **1,5 s** (medido: 19 OK / 0 429) y
  reintento con espera ante 429.

### 3.2 Selectores de Elempleo — `Ola 3 / paso 2` — **HECHO**
- **Qué**: `.ee_list-item` NO son las ofertas (es el menú lateral). Los 3 bugs
  reales eran: (1) `_es_login_wall` veía el botón "Inicia sesión" del
  encabezado y cortaba en la página 1; (2) la empresa ya no viene en
  `datalayertag` sino en `.js-offer-company`; (3) el filtro de país miraba solo
  el cantón ("San José") y no "Costa Rica" → descartaba todas. Se añade
  `site_config["max_ofertas"]` (cada oferta abre su ficha).
- **Criterio**: ✅ **3 avisos en vivo** (antes 0), con descripción, empresa,
  ubicación y fecha.

### 3.3 Estado `requiere_login` en la salud de sitios — `Ola 3 / paso 3` — **HECHO**
- **Qué**: hoy un login-wall (ANE dio 0) se contabiliza como `zero_results` y
  genera una racha de "sitio muerto" que el usuario tiene que revisar a mano.
  Distinguir "0 avisos porque exige login" de "0 avisos porque el selector
  está roto".
- **Cómo**: migración **022** (`health_status='requiere_login'`,
  `source_run_sites.status='requires_login'`), `RequiereLoginError`
  (`jobpulse_v15.requiere_login`), `repository.record_site_result(status=…)`
  (no suma a la racha de ceros), UI v2 con 🔑 y lista de sitios que piden login.
- **Criterio**: ✅ la corrida queda `requires_login` (no `error`) y la salud del
  sitio lo dice.

### 3.4 Sesión de ANE entre arranques del navegador — `Ola 3 / paso 4` — **HECHO**
- **Qué**: la cookie de ANE (`ASP.NET_SessionId`) es de **sesión**
  (`expires = -1`): Chromium no la escribe en disco, así que al reabrir Brave
  se perdía (medido: login → 24 avisos; cerrar → reabrir → "sin sesión de
  detalle" → 0 avisos). El cierre ordenado de O12 · 1.5 no arregla esto.
- **Cómo**: `jobpulse_v15.sesion_navegador` guarda las cookies del sitio en
  `data/usuario/sesiones/<sitio>.json` (fuera del repo) tras un login
  exitoso y las restaura en el contexto cuando falta la sesión.
- **Criterio**: ✅ **24 avisos con Brave recién abierto** (antes `requires_login`).

---

## Ola 4 — Calidad del dato (impacto MEDIO)

| # | Mejora | Esfuerzo | Criterio de aceptación |
|---|---|---|---|
| 4.1 | Re-barrido de detalle (O5.3) + parser de ANE completo | medio | endpoint de detalle en vez de listado; descripción completa |
| 4.2 | Curación de la taxonomía: 1988 variantes en `concepto_no_normalizado` (mayoría frases de tarea) | medio | filtrar antes de encolar + curar en tandas |
| 4.3 | Métricas por etapa (`pipeline_etapa`: tiempo, avisos, requisitos, errores) | bajo | auditar por qué una corrida dio menos |

### 4.1 Re-barrido de detalle + parser completo de ANE — **MEDIDO 2026-11-06**

**Lo que decía el plan**: re-barrer 43 descripciones <200 chars (35 de ANE).

**Lo que se midió primero (y cambió el plan)**: de esos 43, solo **10** tienen
texto total <200 chars (descripción + requisitos): los otros 33 tenían el
texto en `requirements_raw`, no en `description_raw`. Y comparando el texto
guardado con el detalle **en vivo**, el corpus **ya coincidía** con la fuente:
la descripción corta era real, no un fallo de guardado.

**El hueco real**: el parser de la ficha de ANE **descartaba campos**:

| Campo que se perdía | Por qué importa |
|---|---|
| `Nivel académico` | Lo que la empresa PIDE: sin esto no hay dimensión educativa |
| `Experiencia laboral` | Lo que la empresa PIDE: sin esto no hay dimensión de experiencia |
| `Estudio técnico` | Técnico (salvo valores negados: "No se especifica estudios técnicos") |
| `Ocupación`, `Horario`, `Tipo contratación` | Contexto del aviso (no requisitos) |

**Lo que se hizo**:

1. **Parser ampliado** (`ane.py`): lee los campos de arriba; un valor
   **negado** ("No se especifica…") NO se copia (no es un requisito); el
   **correo del empleador NO se guarda** (dato personal de un tercero).
2. **Re-barrido de detalle** (`scrape ane --site ane-cr --revisitar`): vuelve a
   bajar el detalle de los avisos **ya guardados** (por su URL, no por el
   listado). Hace falta porque el listado de ANE solo muestra lo nuevo: un
   aviso viejo guardado con un parser viejo **nunca** vuelve a pasar por el
   listado, así que su texto se quedaba para siempre incompleto. Si la
   vacante ya no está en la web, se **omite** (no se borra nada).
   El re-barrido usa la **misma** construcción de oferta que el barrido
   (`AneFetcher._oferta`): si construyera el dict aparte, el texto guardado
   sería distinto y el re-análisis no detectaría el cambio.
3. **Re-análisis por texto nuevo** (`analysis_flow.avisos_con_texto_cambiado`
   / `reananalizar_texto_cambiado`): si el `text_hash` del análisis vigente ya
   no cuadra con el texto del aviso, el aviso está obsoleto → se re-analiza.
   Es la señal que faltaba (la de la Ola 1.1 solo miraba `skills`/`languages`).
   Va enganchado en la etapa `reanalisis` del orquestador (`pipeline.py`).

**Medición (sobre una COPIA de la BD real, `%TEMP%\opencode\ola4.db`)**:

| Métrica | Antes | Después |
|---|---|---|
| Avisos en el corpus | 705 | **729** (+24 nuevos de ANE) |
| `calificada` | 239 | 242 |
| `descartada / titulo_universitario_requerido` | 67 | 76 |
| `sin_requisitos` | 11 | 24 (+13: los 24 nuevos aún sin enriquecimiento IA) |
| **`educacion_no_confirmada`** | 31 | **31 (sin cambios)** |
| Avisos que **cambian de estado** | — | **9 de 705** |

Los 9 cambios (con evidencia literal, revisada uno a uno):

| Aviso | Antes | Después | Evidencia |
|---|---|---|---|
| `ane-121783/121784/121786/121788` | `revisar_a_mano/educacion_no_cumple` | `descartada/titulo_universitario_requerido` | "Bachillerato Universitario en Economía Agrícola…" + "Nivel académico:…" |
| `ane-121789` (Audiólogo) | `revisar_a_mano/skill_faltante` | `descartada/titulo_universitario_requerido` | "Nivel académico: Licenciatura (Requerido)." |
| `ane-121804` (Gerente RRHH) | `revisar_a_mano/skill_faltante` | `descartada/titulo_universitario_requerido` | "Nivel académico: Licenciatura (Requerido)." |
| `ane-121911` (Abogada Junior) | `datos_insuficientes/cobertura_insuficiente` | `descartada/titulo_universitario_requerido` | "Nivel académico: Licenciatura (Requerido)." |
| `ane-121791` (Contador) | `calificada` | `revisar_a_mano/educacion_no_cumple` | "Nivel académico: Licenciatura." (sin "Requerido" → no se descarta) |
| `ane-121818` (Ingeniero de Proyecto) | `calificada` | `revisar_a_mano/educacion_no_cumple` | "Nivel académico: Licenciatura." (sin "Requerido") |

**Lo importante**: los 4 avisos que pasan a `descartada` dicen
**"Licenciatura (Requerido)"** (o el texto del aviso ya exigía bachillerato
universitario) → el texto **confirma** el título obligatorio, que es lo único
que permite descartar. Los 2 que dicen solo "Nivel académico: Licenciatura"
**no** se descartan: quedan en `revisar_a_mano` (ante la duda, revisar).
**`educacion_no_confirmada` no se tocó** (31 → 31): lo firma una segunda
persona.

**Pendiente**: ~~aplicar el re-barrido + re-análisis + Paso 5 **a la BD real**~~

### 4.1 APLICADO A LA BD REAL (2026-11-06, con OK del usuario)

Se aplicó **solo a los 120 avisos ANE ya guardados** (decisión del usuario: los
24 avisos nuevos se dejan para el barrido normal, con su pase de IA):

| Paso | Comando | Resultado |
|---|---|---|
| Respaldo | `… backup --output data\backups\pre_ola4_20261106_151857.db` | 18,7 MB |
| Re-barrido de detalle | `… scrape ane --site ane-cr --revisitar` | 120 revisados, 0 nuevos, 0 omitidos |
| Re-análisis + backfill + Paso 5 + evidencia | `pipeline.ejecutar(…, etapas=("reanalisis","backfill","paso5","evidencia"))` | 120 re-analizados · backfill 0 · **corrida `20261106_152304`** · evidencia OK (137 verificaciones) |

**Resultado en la BD real** (idéntico a la medición sobre la copia):

| Métrica | Antes (`20261104_231932`) | Ahora (`20261106_152304`) |
|---|---|---|
| Avisos | 705 | 705 (sin scrape: solo texto corregido) |
| Texto total de los avisos ANE | 115.601 chars | **141.967 chars** (+23 %; los 120 con más texto) |
| `calificada` | 239 | 237 |
| `descartada` | 89 | 96 |
| `datos_insuficientes` | 42 | 41 |
| `revisar_a_mano` | 324 | 320 |
| `sin_requisitos` | 11 | 11 |
| **`educacion_no_confirmada`** | 31 | **31 (sin cambios)** |
| Avisos que cambian de estado | — | **9** (7 → `descartada` con evidencia literal, 2 → `revisar_a_mano`) |

`db check` → `integrity_check ok`, 0 violaciones de FK. `verificar_evidencia.py`
→ **137 verificaciones con frase LITERAL, 0 fallos**. La hoja de firma
(`docs/PASO5_REVISION_PENDIENTES.md`) se regeneró para la corrida vigente
(31 casos, sin veredictos: los firma una segunda persona).

### 4.2 Curación de la taxonomía — **MEDIDO 2026-11-06**

**Lo que decía el plan**: 1988 variantes en `concepto_no_normalizado`
(la mayoría frases de tarea) → filtrar antes de encolar + curar en tandas.

**Lo que se midió primero** (audit del corpus real, sobre una copia):

| Dato | Valor |
|---|---|
| Skills distintas en `jobs.skills` | 3397 (5199 menciones) |
| Resolvían a un concepto | **241** (877 menciones: el 17 %) |
| Frases de tarea (`ats.es_frase_de_tarea`) | 1180 (1950 menciones) |
| NO resolvían | 1976 (2372 menciones) |
| Conceptos canónicos en `concepto` | 392 |

Y la **cola estaba obsoleta**: 10 filas ya tenían concepto (las migraciones 020
y 021 los añadieron después y la cola nunca se re-evaluó), y 1976 filas no
resolvían a nada. La causa del ruido: `jobs.skills` mezcla **herramientas**
("ServiceNow") con **tareas** ("despachar", "empacar"), **palabras vacías**
("analysis", "planning") y **sectores** ("construccion", "ventas") — el
criterio que la propia migración 021 aplicó a mano, pero que nadie automatizó.

**Lo que se hizo**:

1. **Filtro antes de encolar** (`conceptos.es_variante_encolable`): descarta
   lo que no es competencia — una **actividad** ("despachar", "revisar
   equipos"), una **palabra vacía** ("analysis") o un **sector**
   ("construccion") — y lo que son frases de más de tres palabras. El filtro
   vive en `encolar_sin_concepto`, el **único punto de entrada** de la cola,
   así que aplica a todos los orígenes (oferta y CV). Es **conservador**: lo
   que no cae en las reglas se queda en la cola; nunca se descarta en
   silencio.
2. **Curación por tandas** (datos, no código): la migración **023**
   (`023_taxonomia_curacion_tanda_1.sql`) añade **alias** de conceptos que ya
   existían ("office 365 basico" → Office 365, "mantenimiento correctivo" →
   mantenimiento) y **conceptos nuevos** para las herramientas y métodos que
   el corpus pide (Mulesoft, PowerShell, MFA, ISO 9001, lectura de planos,
   metrología, cableado estructurado…).
3. **Herramienta de curación** (`jobpulse-v15 taxonomy curate`): audita el
   corpus frente a la taxonomía (resuelto / ruido / pendiente) y, con
   `--apply`, **reconstruye la cola** desde `jobs.skills` / `jobs.languages`:
   borra lo que ya resolvió y lo que es ruido, y reescribe `veces` con el
   número de **avisos** que piden cada variante (antes contaba encolados).

**Medición sobre una COPIA de la BD real** (`%TEMP%\opencode\ola42_full.db`):

| Métrica | Antes | Después |
|---|---|---|
| Etiquetas del corpus que resuelven | 241 | **560** (877 → 2064 menciones) |
| Ruido descartado | — | 1623 variantes (2582 menciones) |
| Cola `concepto_no_normalizado` | 1988 filas | **1225 filas** (pendientes reales) |
| Requisitos vigentes | 2483 (1 sin código) | **2857 (0 sin código)** |
| Requisitos medios por aviso | 3,53 | **4,07** (232 avisos con más, 0 con menos) |

**Lo que cambia en el matching (medido, no supuesto)**: 58 avisos cambian de
estado — 47 `calificada → revisar_a_mano`, 7 `datos_insuficientes →
revisar_a_mano`, 2 `sin_requisitos → revisar_a_mano`, 1 `calificada →
datos_insuficientes`, 1 `datos_insuficientes → calificada`. En bandas de
viabilidad: `aplicar` 270 → **217**, `no_prioritario` 323 → **376**, `revisar`
2 → 4, `sin_datos` 14 → 12, `veto` 96 → 96 (sin cambios).

**Por qué es correcto** (ejemplos literales del motor): los avisos ANE
`ane-121787`, `ane-121797`… se evaluaban con **un solo requisito** (el
idioma) y salían `calificada/cumple_umbral`; ahora además piden
"inventario" (`codigo_canonico='inventarios'`), `ane-121790` pide además
"fontanería" y "electricidad", `ane-121807` pide además ISO 19011, PCAOB,
ICFR, SEC SOX y COSO → el perfil no los tiene → `revisar_a_mano/skill_faltante`.
Antes esos requisitos eran **invisibles** (sin `codigo_canonico` el motor los
ignora en silencio) y las vacantes parecían más compatibles de lo que son.

**Pendiente**: ~~aplicar a la BD real~~ → **APLICADA A LA BD REAL
(2026-11-06, con OK del usuario)**: respaldo
`data/backups/pre_ola42_20261106_182411.db` (`integrity_check ok`, esquema 22,
705 avisos) → apertura (aplica la **023**, esquema 23) → `taxonomy curate
--apply` (cola 1988 → **1225**) → re-análisis de los **705** avisos (la etapa
`reanalisis` del pipeline solo rehace los que nunca integraron `jobs.skills`)
→ requisitos vigentes 2483 (1 sin código) → **2857 (0 sin código)** → backfill
(0) → **corrida `20261106_182554`** → evidencia OK (137 verificaciones
literales, `no_confirmada=31`) → `db check` ok (`integrity ok`, 0 violaciones
de FK).

**El resultado real fue IDÉNTICO al medido en la copia**: 58 avisos cambian de
estado (47 `calificada → revisar_a_mano`, 7 `datos_insuficientes →
revisar_a_mano`, 2 `sin_requisitos → revisar_a_mano`, 1 `calificada →
datos_insuficientes`, 1 `datos_insuficientes → calificada`), requisitos
medios 3,53 → **4,07** (232 avisos con más, 0 con menos) y
`educacion_no_confirmada` 31 → **31 (intacto)**. La hoja de firma
(`docs/PASO5_REVISION_PENDIENTES.md`) se regeneró para la corrida vigente
(31 casos, sin veredictos: los firma una segunda persona).

**Segunda tanda de curación — APLICADA A LA BD REAL 2026-11-07 (medida en
copia, con OK del usuario)**

**Alcance**: las **28 variantes que varios avisos piden** (≥ 2 avisos, medida
con `taxonomia.demanda_corpus`; el contador `veces` de la cola está duplicado
×2 tras el re-análisis, no sirve como medida). Migración **025**
(`025_taxonomia_curacion_tanda_2.sql`), mismo patrón que la 023:

- **8 alias** a conceptos existentes: `power brakes` → `tooling-especializado`
  (es una máquina-herramienta de la **misma lista** que ya curó la 023),
  `html css` → html, `nc capas` → acciones-correctivas, `service operations`
  → operational-support, `supply chain engineering` → abastecimiento,
  `informe de ventas` → reporting, `almacenamiento al vacio` y `preliminado de
  alimentos` → manipulacion-alimentos;
- **10 códigos nuevos** (13 variantes): `tuv`, `b2b`, `macos`,
  `sistemas-operativos`, `r`, `servidores` (servers/servidores),
  `organizacion`, `comunicacion` (comunicacion/listening skills),
  `validacion` (validacion/validation), `variance-analysis`;
- **9 variantes se dejan en la cola a propósito** (documentado en la cabecera
  de la migración): `data driven settings`, `external services`, `upgrades`,
  `website`, `four seasons` (nombre de la empresa), `providing product
  information` (tarea, no competencia) y los 3 **fantasmas** de
  `demanda_corpus` — `espanol c1`, `ingles c1`, `english target language`:
  el extractor YA los crea como requisito de **idioma** con su nivel (0 filas
  tipo `%c1%` en `job_requirements` como skill, verificado); curarlos como
  skills daría un falso "faltante" porque el perfil registra `espanol` como
  idioma. **El arreglo de código se hizo el mismo día (ver abajo)**.

**Medición (copia → real, resultado IDÉNTICO)**:

| Métrica | Antes | Después |
|---|---|---|
| Cola `concepto_no_normalizado` | 1225 | **1204** (−21) |
| Taxonomía (filas `concepto`) | 706 | **727** (+21) |
| Requisitos vigentes | 2858 (0 sin código) | **2900 (0 sin código)** (+42: 39 skill, 3 language) |
| Variantes distintas con código | 546 | 566 (+20) |
| Códigos canónicos usados | 281 | 291 (+10) |
| Matching: calificada / revisar | 191 / 376 | **188 / 380** |
| datos_insuficientes / descartada / sin_requisitos | 34 / 96 / 8 | 33 / 96 / 8 |
| `educacion_no_confirmada` | 31 | **31 (intacto)** |

El −3 de `calificada` es el efecto esperado: los +42 requisitos recién
visibles hacen que 3 avisos que parecían cubiertos del todo muestren un
`required` real que faltaba (tope `revisar`) y 1 pase de `datos_insuficientes`
a `revisar`. El motor ve más requisitos, no peor matching.

**Aplicación a la BD real (2026-11-07, con OK del usuario)**: respaldo
`data/backups/pre_tanda2_20261107_133858.db` → apertura (aplica la **025**,
esquema **25**) → `taxonomy curate --apply` (cola 1225 → **1204**) →
`enrich requirements-source --apply` (705 avisos, 1750 requisitos fuente, 0
errores) → `enrich requirements-canonico --apply` (0) → corrida
**`20261107_133939`** (705 evaluadas, 2906 requisitos) → evidencia
`docs/PASO5_EVIDENCIA_2026-11-07.md` OK (**137 verificaciones literales**,
`no_confirmada=31`) → hoja de firma regenerada (31 casos) → `db check` ok
(esquema 25, integridad ok, 0 FK).

**Lo que queda para la Ola 4.2**: curar el resto de la cola (1199
pendientes; 1192 los pide UN solo aviso → siguiente tanda cuando entre corpus
nuevo).

### 4.2 · TANDA 3 — APLICADA A LA BD REAL (2026-11-08)

Migración **`026_taxonomia_curacion_tanda_3.sql`** (esquema **26**). Con el
corpus de la corrida local (`20261107_225916`) la cola tenía **1198**
variantes pendientes; la tanda cura las **57 que varios avisos piden**
(≥ 2 avisos reales, medido con `taxonomia.demanda_corpus` — el contador
`veces` de la cola ya no sirve como medida).

División de la tanda:

- **25 alias** a conceptos que ya existían: las tres formas de leer planos
  (`interpretacion de planos` / `interpretacion de diagramas` / `planos` /
  `drawings` → `lectura-planos`), `diagnostico` / `investigate technical
  problems` / `network diagnostics` → `troubleshooting`, `business analysis` →
  `analisis-negocio`, `invoicing` → `facturacion`, `collections` →
  `cuentas-por-cobrar`, `supply chain` → `abastecimiento`, `timelines` →
  `project-planning`, `seleccion` → `reclutamiento`, `sap basico` → `sap`,
  `iis` / `web server technologies` → `servidores`, `digitacion` →
  `data-entry`, `destrezas electricas` → `electricidad`, `destrezas mecanicas`
  → `mecanica-industrial`, `almacenamiento de alimentos` /
  `conservacion de alimentos` → `manipulacion-alimentos`, `protocolos de
  higiene` → `seguridad-alimentaria`, `phone` / `phone calls` /
  `llamadas salientes outbound` → `atencion-al-cliente`;
- **23 variantes con 19 códigos nuevos**: `negociacion`, `cierre-ventas`,
  `marketing-automation`, `evaluacion-riesgos`, `order-to-cash`,
  `containerization`, `ich`, `onq`, `reservaciones`, `cocteleria`
  (cocteleria + técnicas de mixología), `preparacion-alimentos` (técnicas
  culinarias básicas + cortes + ensaladas + guarniciones), `tecnicas-coccion`,
  `tecnicas-montaje`, `moto`, `vehiculo-propio`, `ventaneria`, `alarma`,
  `paneles-control`, `tarjetas-acceso`;
- **9 variantes se dejan en la cola a propósito** (documentado en la cabecera
  de la migración): `website` (canal/activo del empleador), `data driven
  settings` y `upgrades` (ajustes del producto), `four seasons` (nombre de la
  empresa), `explore products` y `providing product information` (tareas),
  `buenas practicas` (vaga), `asesor` (el cargo repetido como skill) y
  `liviano` (calificador ambiguo: "vehículo liviano").

**Medición (copia → real, resultado IDÉNTICO)**:

| Métrica | Antes | Después |
|---|---|---|
| Cola `concepto_no_normalizado` | 1198 | **1150** (−48) |
| Taxonomía (filas `concepto`) | 727 | **775** (+48) |
| Códigos canónicos | 317 | **336** (+19) |
| Requisitos vigentes | 2879 (0 sin código) | **2956 (0 sin código)** (+77) |
| Matching: calificada / revisar | 220 / 365 | **202 / 389** |
| datos_insuficientes / descartada / sin_requisitos | 42 / 97 / 11 | 36 / 97 / 11 |
| `educacion_no_confirmada` | 29 | **29 (intacto)** |

El −18 de `calificada` es el efecto esperado: los +77 requisitos recién
visibles hacen que avisos que parecían cubiertos del todo muestren un
`required` real que faltaba (tope `revisar`). El motor ve más requisitos, no
peor matching. Los 29 `educacion_no_confirmada` siguen **intactos** (la firma
es de una segunda persona).

**Aplicación a la BD real (2026-11-08)**: respaldo
`data/backups/pre_tanda3_20261108_131212.db` → apertura (aplica la **026**,
esquema **26**) → `enrich requirements-source --apply` (736 avisos, 735
analizados, 1756 requisitos de fuente; 1 aviso sin descripción:
`linkedin-4476184789`) → `enrich requirements-canonico --apply` (0) →
`taxonomy curate --apply` (cola 1202 → **1150**) → corrida
**`20261108_131343`** (735 evaluadas, 2956 requisitos) → evidencia
`docs/PASO5_EVIDENCIA_2026-11-08.md` OK (**136 verificaciones literales**,
`no_confirmada=29`) → hoja de firma regenerada (29 casos) → `db check` ok
(esquema 26, integridad ok, 0 FK).

**Lo que queda para la Ola 4.2**: curar el resto de la cola (**1150**
pendientes; 1141 las pide UN solo aviso → siguiente tanda cuando entre corpus
nuevo).

**Arreglo de código de los fantasmas + bug "IT" → italiano — APLICADO A LA
BD REAL el mismo día (2026-11-07, con OK del usuario, medido en copia
fresca)**:

- **Bug real de matching**: `indeed-d4b1295866756a8c` (soporte técnico) pide
  **"IT"** entre sus skills y `clasificar` lo resolvía por la categoría
  language (la 021 insertó el código "it" como variante de `italiano` y
  prueba language antes que skill) → el motor evaluaba el aviso pidiendo
  **ITALIANO**.
- **El arreglo (solo código; esquema sigue en 25)**: `idiomas.idioma_en_skill`
  reconoce la etiqueta-skill que empieza por un NOMBRE de idioma ("Inglés -
  C1", "English <> Target Language") y `demanda_corpus` la cuenta en el lado
  idioma de la demanda → la cola deja de pedir curarla como skill (salieron
  los 3 fantasmas `* c1`/`target language` y 3 hermanos de 1 aviso). Y
  `skills_fuente.clasificar` ya no resuelve una etiqueta natural de ≤2
  letras por la categoría language — mata el bug "IT". Los códigos 'en'/'es'
  que emite el extractor de reglas siguen resolviendo por
  `conceptos.resolver`.
- **Lección de la medición**: la primera versión — migración 026 que borraba
  las variantes de 2 letras — rompía **218 requisitos** del extractor de
  reglas (183 'en' + 35 'es' sin `codigo_canonico`: invisibles). Detectado
  midiendo en copia; **026 eliminada, nunca llegó a la BD real**. Las
  variantes 'en'/'es' son **load-bearing**.
- **Resultado (copia == real)**: requisitos 2900 → **2899 (0 sin código)**
  (−1 = el italiano falso), cola 1204 → **1199** (−6 fantasmas, +1
  `skill 'it'` honesta), **bandas idénticas** (188/380/33/96/8),
  `educacion_no_confirmada` 31 intacto. Respaldo
  `data/backups/pre_fantasma_20261107_171605.db`, corrida vigente
  **`20261107_171903`**, evidencia OK (137 verificaciones), `db check` ok.

### 4.3 Métricas por etapa — **HECHO 2026-11-06**

**Lo que decía el plan**: `pipeline_etapa` con tiempo, avisos, requisitos y
errores → auditar por qué una corrida dio menos.

**El hueco real (medido)**: las siete etapas del pipeline devuelven contadores
**propios y en formatos distintos** (`analizados`, `jobs_found`, `ciclos`,
`candidatos`, `actualizados`, `por_estado`, `verificaciones`…). Acabada la
corrida solo quedaba un estado final (`calificada`/`revisar_a_mano`/…), y no
se podía responder a la pregunta que de verdad importa: **de todos los avisos
que entraron, ¿cuántos llegaron al Paso 5, cuántos tenían requisitos y en qué
etapa se perdieron?**

Caso real que lo motivó (Ola 4.2): 705 avisos entraron al análisis, pero 9
acabaron en `sin_requisitos` y 58 cambiaron de estado porque sus requisitos
(skills de ANE) no tenían `codigo_canonico`. Sin este registro, ese hueco solo
se descubría mirando los estados finales.

**Lo que se hizo**:

1. **Tabla `pipeline_etapa`** (migración **024**, esquema 23 → **24**): una
   fila por **etapa y por ejecución** del pipeline. Columnas: `corrida_id`,
   `etapa`, `ok`, `duracion_ms`, `avisos`, `requisitos`, `errores`,
   `detalle_json`, `iniciado_en`, `terminado_en`. Índices por `(corrida_id, id)`
   y `(etapa, id)`. **Sin claves foráneas** a propósito: el `corrida_id` del
   pipeline es un id **lógico** (`pipe_<timestamp>`), no el `corrida_id` del
   `job_match` (el del Paso 5 va en el `detalle_json` de la etapa `paso5`).
2. **Módulo `jobpulse_v15.pipeline_metricas`**: traduce el resultado de cada
   etapa a tres números **comparables** (`avisos` / `requisitos` / `errores`) y
   guarda además los contadores **específicos** de la etapa en `detalle_json`
   (por estado del Paso 5, por campo rellenado por la IA, por sitio del
   barrido…).
3. **Instrumentación en el orquestador** (`pipeline.ejecutar`): es el **único**
   punto donde se cronometran las etapas, así que CLI, UI v2 y
   `run_full_flow.py` dejan la misma métrica. La instrumentación es
   **puramente aditiva**: si falla (BD bloqueada, tabla que no existe), la
   corrida **sigue** — una métrica nunca rompe un pipeline.
4. **Contadores que faltaban** (añadidos a las etapas que no los exponían):
   `analisis.requisitos_guardados`, `paso5.requisitos_evaluados` (suma de
   `Resultado.total_req`) y `reanalisis.texto_errores`.
5. **Consulta**: `jobpulse-v15 pipeline etapas [--limite N] [--corrida ID]
   [--json]`, más una línea de métricas en la UI v2 (la UI clásica queda
   intacta).

**Medición sobre una COPIA de la BD real** (`%TEMP%\opencode\ola43_copia.db`):

```
=== pipe_20261106_202905 ===
etapa        ok           ms   avisos  requisitos  errores
analisis     OK          227        0           0        0
reanalisis   OK         1248        0           0        0
backfill     OK            7        0           0        0
paso5        OK          597      705        2866        0
evidencia    OK         1293      705           0        0
  TOTAL 3372 ms | 1410 aviso(s) | 2866 requisito(s) | 0 error(es)
```

Los contadores cuadran con el estado real: 705 avisos evaluados, 2866
requisitos evaluados, evidencia con 137 verificaciones literales y
`no_confirmada=31` (intacto). El `detalle_json` de la etapa `paso5` guarda el
desglose por estado y por motivo (`calificada=190`, `revisar_a_mano=376`,
`descartada=96`, `datos_insuficientes=34`, `sin_requisitos=9`).

**Lo que NO hace**: no toca `job_match`, ni `job_analysis`, ni los umbrales del
motor, ni borra ni funde datos. Es una tabla de **auditoría**.

**APLICADA A LA BD REAL (2026-11-06, con OK del usuario)**: **solo la
migración 024** (la tabla de auditoría), **sin** tocar el matching: respaldo
`data/backups/pre_ola43_20261106_210124.db` (19,4 MB) → `db check` previo
(esquema 23, `integrity ok`, 0 violaciones de FK) → apertura (aplica la 024,
esquema **24**) → `db check` posterior (`integrity ok`, 0 violaciones de FK).
Estado **sin cambios**: 705 avisos · 706 conceptos · cola 1225 · 825
`job_analysis` · **0 requisitos sin código** · 2669 filas de `job_match` ·
corrida vigente **`20261106_182554`** · `educacion_no_confirmada` **31
(intacto)**. `pipeline_etapa` queda vacía (0 filas) hasta la próxima corrida
real del pipeline.

---

## Ola 5 — Se puede dejar de último (impacto bajo o esfuerzo alto)

| # | Mejora | Por qué al final |
|---|---|---|
| 5.1 | Re-análisis **sin inflar el historial** (`save_analysis` marca `is_current=0` y crea fila nueva): hacer upsert cuando el texto no cambió pero sí los campos | Toca la auditoría del análisis (riesgo medio); el beneficio es disco/tiempo, no resultados |
| 5.2 | Semántica/embeddings en el motor de **viabilidad** (hoy solo el ranking ATS los usa) | El percentile es el único componente ruidoso; overhaul grande (alto) y el motor ya es conservador |
| 5.3 | IA externa para **tareas futuras** (matching semántico, resumen de vacantes, extracción de CV) | Requiere primero la Ola 2 (orquestador) para que las tareas nuevas se puedan lanzar igual desde CLI y UI |
| 5.4 | `ia_api`: streaming / reintentos por token / cache por proveedor | Optimizaciones; el flujo actual ya es estable |

### Ola 5 · dos extras del backlog 2026-11-08 — HECHOS

**5.5 Ciclos de IA que no rinden (HECHO 2026-11-08)** — el pase crítico
reintentaba en cada ciclo los avisos que el modelo NO puede enriquecer (el
ciclo 3 de la corrida local reintentó 433 avisos y llenó 0: el modelo es
determinista a temp 0.1 y devuelve lo mismo).

- `run_ia_enrichment(..., exclude_ids=Set[str])` salta los ids excluidos
  **antes de elegir lote** (ni una llamada).
- `run_ia_enrichment` devuelve **`ids_estancados`**: los avisos que no
  rindieron (`failed` = el modelo no halló el campo; `skipped` = devolvió lo
  que ya estaba).
- `pase_completo` acumula los estancados y los excluye del **siguiente ciclo
  y del pase completo**.
- Sin cambio de esquema; tests en `tests/test_ia_enrichment.py`.

**5.6 Persistir el consumo real de tokens (HECHO 2026-11-08)** — `IAClient.tokens_in/out`
vivían solo en memoria y se perdían al terminar el pase.

- `pase_completo` usa **un único cliente** para todo el pase (así los tokens
  se acumulan), lo **cierra al terminar** (pase lo que pase) y devuelve
  `resumen["uso"] = {llamadas, tokens_in, tokens_out}`.
- `pipeline_metricas.detalle_etapa("ia")` lo guarda en
  `pipeline_etapa.detalle_json` (clave `uso`) → el coste de cada corrida es
  consultable con `jobpulse-v15 pipeline etapas --json`.
- **Medido en copia** (25 avisos, caché IA nueva, IA local): 123 llamadas,
  52 827 tokens in / 3 901 tokens out; sin pérdida de datos (2 de 25 avisos
  con skills distintas por ser el modelo no determinista, no por el cambio).

### 5.7 La firma de `educacion_no_confirmada` — **HECHA 2026-11-08** (Paso 7)

La regla educativa es conservadora a propósito: `descartada` solo si el texto
confirma el título obligatorio **sin negación y sin alternativa**. Cuando el
texto deja una vía alternativa ("or equivalent experience"), el motor deja el
caso en `revisar_a_mano / educacion_no_confirmada` esperando el veredicto de
una **segunda persona** (la revisión previa la hizo el autor de la regla → se
descarta por sesgo). Hasta ahora esa firma vivía **solo en un documento**: el
motor no la podía leer, así que los casos firmados seguían contando como
"pendientes" para siempre.

- **Migración `027_job_match_decision.sql`** (esquema **27**): tabla
  `job_match_decision` con `veredicto` (`bloqueo_real` | `no_bloqueo` |
  `dudoso`), `criterio`, `revisor`, `fecha`, `text_hash` y `corrida_id`;
  `UNIQUE (job_id, dimension, text_hash)` y FK a `jobs` con `ON DELETE
  CASCADE`. **No toca `job_match`**: los estados los produce una corrida nueva.
- **Módulo canónico `decisiones.py`**: el **ancla** de la decisión es el
  sha256 del **texto exacto** que se leyó (`requirements_raw` +
  `description_raw`, el mismo que leen el motor y la hoja). Si el aviso se
  re-raspa y su texto cambia, la firma **deja de aplicar** y el caso vuelve a
  `educacion_no_confirmada`.
- **`matching.py`**: el evaluador carga las firmas y las aplica **solo cuando
  el motor no pudo decidir**: `bloqueo_real` → `bloqueante` (`descartada`),
  `no_bloqueo` → `faltante` (`revisar_a_mano / educacion_no_cumple`), `dudoso`
  → sin cambio (el caso sigue abierto). **Una firma nunca pisa un veredicto
  que el motor ya dio.**
- **`viabilidad.py`**: el veto educativo respeta la firma.
- **CLI**: `jobpulse-v15 decision list` y `decision sign --file <firma.json>`
  (`--dry-run` para comprobar sin escribir). La hoja firmada vive en
  `docs/PASO5_FIRMA_EDUCACION.json` (29 decisiones con su `text_hash`).
- **Evidencia**: sección nueva con las firmas y su efecto, y verificación que
  comprueba que **cada cita del criterio es literal del texto de la BD** y que
  **el estado de la corrida concuerda con el veredicto**.

**La firma (segunda persona, 2026-11-08)**: 25 `no_bloqueo` (el texto ofrece
vía alternativa explícita), 2 `bloqueo_real`
(`workday-Principal-Engineer--Quality_Req-51750` y
`workday-SharePoint-Application-Developer_R55630-1`) y 2 `dudoso`
(`workday-Credit---Collections-Specialist--2_R232432` y
`workday-Production-Supervisor-I_31163511`).

**Medición (copia → real, IDÉNTICA)**: en la copia, el motor **sin** firma
reproduce la corrida vigente **exactamente** (0 diferencias) → la firma es lo
único que cambia. 27 avisos cambian de estado y **ninguno** cambia de
cobertura o puntaje (solo `nc_count` 1 → 0), así que ninguno cae a
`datos_insuficientes`. Corrida real **`20261108_175932`**: `educacion_no_confirmada`
**29 → 2**, `descartada` 97 → **99**, `revisar` 389 → **391**; evidencia OK
(**140 verificaciones literales**) y `db check` ok (esquema 27, 0 FK).

**Lo que sigue abierto**: los 2 casos "dudoso" dependen de 2 decisiones de
**negocio** que hay que decidir **con una fuente** (no por impulso): si 2 años
de educación superior en CR cuentan como universitario (CONESUP) y si un
bachillerato parcial del 80 % cuenta como requisito universitario cumplido.

---

## Reglas que NO se tocan en ninguna ola

- Umbrales del Paso 5 (cobertura 0.60 / puntaje 0.80) congelados.
- `preferred` no bloquea; `codigo_canonico` obligatorio.
- Idioma del aviso = idioma en que está escrito, salvo que el aviso pida idiomas.
- Educación: `descartada` solo con título universitario obligatorio confirmado;
  nunca descartar por falta de información.
- `educacion_no_confirmada`: solo lo firma una segunda persona (la firma vive
  en `job_match_decision` y se aplica **solo** donde el motor no pudo decidir).
- Viabilidad ≠ contratación; el tope duro (1 `required` faltante ⇒ banda máxima
  `revisar`) sigue igual.
- Cada cambio de regla de matching ⇒ **corrida nueva** en `job_match`.
- Cambios de esquema ⇒ **migración nueva** (nunca `ALTER` manual).
- Nada de secretos ni datos personales en el repo; nada de push sin
  confirmación del usuario.
