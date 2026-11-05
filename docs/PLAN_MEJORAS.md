# Plan de mejoras — orden por impacto y esfuerzo

> Actualizado 2026-11-05. El orden va de **lo que más duele hoy** (y se
> arregla con poco código) a **lo que puede esperar** (mucho esfuerzo, poco
> efecto inmediato). Cada bloque dice qué se toca, por qué y cómo se sabe que
> quedó bien.

## A qué metas del proyecto pertenece cada ola

| Ola | Meta | Qué cierra |
|---|---|---|
| 0 (hecha) | **O11** IA externa · **O14** límites opt-in | La IA no está atada a la máquina del usuario |
| 1 | **O12** paridad CLI/UI | La UI da los mismos números que la CLI (231 `sin_requisitos` → 11) |
| 2 | **O12** paridad CLI/UI | Una sola implementación del pipeline (orquestador + botones) |
| 3 | **O13** cobertura de fuentes | LinkedIn/Elempleo (0 avisos) + login-wall de ANE |
| 4 | O5.3 / taxonomía / métricas | Calidad del dato |
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

---

## Ola 1 — Cerrar el hueco de raíz (impacto ALTO, cambios chicos)

> Objetivo: que la UI produzca **los mismos números** que la CLI.
> Es la ola con mejor relación impacto/esfuerzo.

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

## Ola 3 — Recuperar plataformas (impacto ALTO, esfuerzo MEDIO, riesgo MEDIO)

### 3.1 Selectores de LinkedIn — `Ola 3 / paso 1`
- **Qué**: LinkedIn sirve `/jobs/search-results/` con clases ofuscadas
  (`fa4afe…`), sin `div.base-card` ni `li[data-occludable-job-id]` ni enlaces
  `/jobs/view/`. No es login-wall. Actualizar `linkedin.py` **y** su test.
- **Criterio**: el barrido de LinkedIn deja de dar 0 avisos.
- **Riesgo**: medio (rate-limit 429 → bajar `pages`).

### 3.2 Selectores de Elempleo — `Ola 3 / paso 2`
- **Qué**: ahora usa `.ee_list-item` en vez de `.result-item` /
  `.js-area-bind.area-bind`. Actualizar `elempleo.py` + test.
- **Criterio**: idem (0 → >0 avisos).

### 3.3 Estado `requiere_login` en la salud de sitios — `Ola 3 / paso 3`
- **Qué**: hoy un login-wall (ANE dio 0) se contabiliza como `zero_results` y
  genera una racha de "sitio muerto" que el usuario tiene que revisar a mano.
  Distinguir "0 avisos porque exige login" de "0 avisos porque el selector
  está roto".
- **Esfuerzo**: bajo-medio. **Riesgo**: bajo.

---

## Ola 4 — Calidad del dato (impacto MEDIO)

| # | Mejora | Esfuerzo | Criterio de aceptación |
|---|---|---|---|
| 4.1 | Re-barrido de detalle (O5.3) para las 43 descripciones <200 chars (35 de ANE) | medio | endpoint de detalle en vez de listado; descripción completa |
| 4.2 | Curación de la taxonomía: 1988 variantes en `concepto_no_normalizado` (mayoría frases de tarea) | medio | filtrar antes de encolar + curar en tandas |
| 4.3 | Métricas por etapa (`pipeline_etapa`: tiempo, avisos, requisitos, errores) | bajo | auditar por qué una corrida dio menos |

---

## Ola 5 — Se puede dejar de último (impacto bajo o esfuerzo alto)

| # | Mejora | Por qué al final |
|---|---|---|
| 5.1 | Re-análisis **sin inflar el historial** (`save_analysis` marca `is_current=0` y crea fila nueva): hacer upsert cuando el texto no cambió pero sí los campos | Toca la auditoría del análisis (riesgo medio); el beneficio es disco/tiempo, no resultados |
| 5.2 | Semántica/embeddings en el motor de **viabilidad** (hoy solo el ranking ATS los usa) | El percentile es el único componente ruidoso; overhaul grande (alto) y el motor ya es conservador |
| 5.3 | IA externa para **tareas futuras** (matching semántico, resumen de vacantes, extracción de CV) | Requiere primero la Ola 2 (orquestador) para que las tareas nuevas se puedan lanzar igual desde CLI y UI |
| 5.4 | `ia_api`: streaming / reintentos por token / cache por proveedor | Optimizaciones; el flujo actual ya es estable |

---

## Reglas que NO se tocan en ninguna ola

- Umbrales del Paso 5 (cobertura 0.60 / puntaje 0.80) congelados.
- `preferred` no bloquea; `codigo_canonico` obligatorio.
- Idioma del aviso = idioma en que está escrito, salvo que el aviso pida idiomas.
- Educación: `descartada` solo con título universitario obligatorio confirmado;
  nunca descartar por falta de información.
- `educacion_no_confirmada`: solo lo firma una segunda persona.
- Viabilidad ≠ contratación; el tope duro (1 `required` faltante ⇒ banda máxima
  `revisar`) sigue igual.
- Cada cambio de regla de matching ⇒ **corrida nueva** en `job_match`.
- Cambios de esquema ⇒ **migración nueva** (nunca `ALTER` manual).
- Nada de secretos ni datos personales en el repo; nada de push sin
  confirmación del usuario.
