# Handoff — Sesión 2026-11-26 (turno 1)

**TL;DR**: sesión centrada en el **objetivo principal** del usuario («encontrar
los puestos más compatibles con el perfil cargado»). Se **(1) verificó en vivo
cómo funciona hoy el sistema** (scrape → skills → comparación → revisión) y se
**(2) implementó la Fase A completa del plan: el flujo «Completar perfil» en
la UI v2**, con implementación única en el paquete. De paso se encontró y
corrigió un **bug latente que hacía invisibles 78 de 291 skills** al guardarlas
como hechos de perfil. Además se creó `docs/ESTRUCTURA_BD.md` (mapa de las 27
tablas) con la regla de **mantenerlo actualizado en cada migración**.

Todo está **commiteado en `37ff80c` pero NO pusheado** (falta confirmación del
usuario).

**Verificación**: suite completa `python -m pytest tests/ -q` →
**1191 passed + 2648 subtests** en 9:28 (baseline: 1164 + 2648).

---

## 1. Lo hecho

### 1.1 Verificación en vivo del sistema (respuesta al usuario)

Resumen de cómo funciona hoy (cifras verificadas contra
`data/jobpulse_v15.db`, corrida `20261111_074200`):

| Paso del usuario | Mecanismo | Estado |
|---|---|---|
| 1. Scrapear páginas registradas | `source_platforms` → `source_sites` → `source_runs`; botón **«Ejecutar grupo»** | 14 plataformas · 129 sitios (129 activos) · 736 avisos |
| 2. Core skills de cada puesto | `job_requirements(category='skill')` (reglas, con `evidence`) + pase IA → `jobs.skills` | 1490 requisitos skill en 496 avisos · 283 códigos · **0 sin resolver** · `jobs.skills` en 733/736 |
| 3. Comparar con los skills del usuario | Paso 5 (`matching.py`) cruza `candidate_profile_facts` vs `job_requirements` | perfil 22 skills · corpus 283 · **solape 11** · 272 que no tiene |
| 4. Revisión de qué encaja | Estados del Paso 5 + bandas de `viabilidad` (pestaña Vacantes) | `calificada` 202 · `revisar_a_mano` 385 · `descartada` 101 · bandas: **aplicar 4 · revisar 16** |

Motivos que mandan en la corrida vigente: `skill_faltante` 306 ·
`cumple_umbral` 202 · `educacion_no_cumple` 81 ·
`titulo_universitario_requerido` 78 · `cobertura_insuficiente` 30 ·
`titulo_universitario_en_curso_requerido` 23.

**Diagnóstico**: la maquinaria funciona de punta a punta; lo que falta son los
**datos de entrada** (perfil corto, corpus sin refrescar, áreas sin marcar).

### 1.2 Fase A implementada: flujo «Completar perfil» en la UI v2

**Restricciones pedidas por el usuario** (cumplidas):

| Restricción | Cómo se cumple |
|---|---|
| Relleno **una sola vez** | Los huecos se **recalculan en cada llamada** desde la BD → lo ya registrado deja de aparecer (idempotente) |
| **Enfoque en la UI** | Botón **«Completar perfil…»** en la pestaña **Perfil** (`ui_v2/tabs/perfil.py`) |
| El sistema **extrae** de lo que da el usuario | No se redacta nada: los huecos son una **consulta determinista** al corpus; las respuestas se guardan y el motor las lee |
| **No es un solo usuario** | Cero datos hardcodeados: todo sale de la BD cargada. Cambian los datos → cambian los huecos |
| Cambio de persona | Decidido: **reemplazar** el perfil (`Repository.clear_candidate_profile_facts()`), sin migración |

**Archivos nuevos**

| Archivo | Qué es |
|---|---|
| `src/jobpulse_v15/perfil_huecos.py` | **Implementación única** de los huecos (`calcular_huecos`, sin Tk, solo lectura). Compara `job_requirements` (con `codigo_canonico`) vs `candidate_profile_facts`, solo en las categorías que el motor lee (`skill`, `language`, `education`, `license`) + áreas + hechos sin código |
| `tests/test_perfil_huecos.py` | 17 tests: detección, relleno una sola vez, `preferred` no cuenta, agnóstico del titular, solo lectura, categorías cerradas, reemplazo de perfil |
| `tools/esquema_bd.py` | Volcado de estructura (tablas/columnas/FK/índices/recuentos) en **modo lectura**; sirve para mantener `docs/ESTRUCTURA_BD.md` al día |
| `docs/ESTRUCTURA_BD.md` | Mapa de las **27 tablas**, cadena FK por capas, recuentos, 6 alertas y **regla de mantenimiento** (actualizar con cada migración) |

**Archivos modificados**

| Archivo | Cambio |
|---|---|
| `src/jobpulse_v15/ui_v2/dialogs.py` | Nuevo `CompletarPerfilDialog`: lista los huecos por categoría (priorizados por nº de avisos), el catálogo de áreas, filtro por código, «Marcar visibles» / «Ninguno», contador. Devuelve `{"facts": [...], "areas": [...]}`; **no toca SQLite** |
| `src/jobpulse_v15/ui_v2/tabs/perfil.py` | Botón «Completar perfil…» + `completar_perfil()`; docstring actualizado (3 formas de llenar el perfil) |
| `src/jobpulse_v15/ui_v2/data/profile.py` | `ProfileStore.huecos()`, `save_many()`, `sincronizar_areas()`; docstring corregido (el repositorio **sí** escribe `codigo_canonico`) |
| `src/jobpulse_v15/repository.py` | `clear_candidate_profile_facts()` (reemplazo de perfil, borra facts + imports + snapshots, **no** toca el corpus) |
| `src/jobpulse_v15/conceptos.py` | **Fix**: fallback en `resolver` (ver §2) |
| `tools/perfil_preguntas.py` | Convertido en **envoltorio** de `perfil_huecos` (ya no hay dos implementaciones) |

### 1.3 Fix: 78 de 291 skills quedaban invisibles para el motor

**Bug** (latente, encontrado al implementar el flujo): al guardar un hueco del
corpus como hecho de perfil, `codigo_canonico` quedaba en **NULL** → el motor
lo **ignoraba en silencio** (la trampa #1 de `AGENTS.md`).

**Causa**: `conceptos.resolver` solo buscaba la variante (`concepto.variante`).
Los huecos llegan ya como **código canónico** (`microsoft-365`, `dotnet`,
`educacion-universitaria`), y esos códigos no siempre tienen variante propia.

**Fix**: en `conceptos.resolver`, si el `value_code` **ya es** un código canónico
activo de esa categoría, se resuelve a sí mismo.

```
antes:  213/291 resuelven  → 78 invisibles para el motor
ahora:  291/291 resuelven  → 0 invisibles
```

**Test**: `tests/test_conceptos.py::test_value_code_que_ya_es_codigo_canonico`.
El test `test_no_usa_conceptos_inactivos` se ajustó: desactivar **una variante**
no desactiva el **código** (otras variantes activas lo mantienen) → ahora
desactiva el código completo.

### 1.4 Documentación

| Archivo | Cambio |
|---|---|
| `docs/PLAN_MEJORES_PUESTOS.md` | Fase A marcada ✅ implementada (con los archivos y el método exactos); §3.1 y §9 actualizados |
| `AGENTS.md` | Módulo `perfil_huecos.py` en el mapa del núcleo; sección nueva **«Flujo «Completar perfil»»**; regla del fallback de `resolver` en la sección de matching; regla de actualizar `docs/ESTRUCTURA_BD.md` en cada migración |
| `docs/ESTRUCTURA_BD.md` | Creado (§7 actualizado con el flujo de la UI) |

---

## 2. Decisiones de esta sesión

| # | Decisión | Motivo |
|---|---|---|
| D1 | El flujo «Completar perfil» es un **diálogo**launchado desde la pestaña Perfil, no otra pestaña | La pestaña Perfil ya tiene tabla + formulario; otra pestaña duplicaría la navegación. El diálogo recibe **datos planos** (sin Tk) → testeable |
| D2 | `perfil_huecos.py` **sin Tk** en el paquete (no en `ui_v2/`) | Es lógica de negocio compartida: la usan la UI y la verificación CLI. Igual patrón que `diagnostico.py` |
| D3 | Los huecos se calculan **contra el corpus**, no contra una lista fija de skills | Es lo que hace que el flujo sea **agnóstico del titular** y se adapte a cualquier BD |
| D4 | Cambiar de persona = **reemplazar** (limpiar y cargar) | El perfil es singleton y el matching lo lee así; una migración `candidate_id` tocaría reglas duras del Paso 5 |
| D5 | Fallback en `conceptos.resolver` (no un caso especial en el perfil) | El bug era **de la resolución de códigos**, no del flujo; arreglarlo en el punto único cubre requisitos y hechos |
| D6 | `tools/perfil_preguntas.py` queda como **envoltorio**, no se borra | Sirve de verificación en sesiones sin GUI, pero **sin duplicar lógica** |

---

## 3. Estado de los objetivos (O1–O14 + Ola 6) y checkpoints S1–S8

### 3.1 Checkpoints del plan operativo (`docs/PLAN_MEJORES_PUESTOS.md`)

| Checkpoint | Estado | Nota |
|---|---|---|
| **S1** Perfil completo y honesto | 🟡 **parcial** | El flujo existe y es funcional; falta que la persona lo **use** (277 huecos + 20 áreas) y que el corpus se refresque antes del Paso 5 |
| S2 Corpus fresco | ⬜ | LinkedIn colapsado a 1 aviso |
| S3 Ubicación normalizada | ⬜ | 87 pendientes |
| S4 Análisis al día | ⬜ | — |
| S5 Corrida nueva con evidencia | ⬜ | sigue `20261111_074200` |
| S6 Mejores puestos visibles | ⬜ | aplicar 4 + revisar 16 (base) |
| S7 Postulaciones registradas | ⬜ | 0 |
| S8 Decisiones E1–E4 | ⬜ | — |

### 3.2 Fases

| Fase | Estado |
|---|---|
| **A — Completar el perfil** | ✅ **implementada** (falta usarla) |
| B — Corpus fresco y limpio | ⬜ pendiente |
| C — Paso 5 + revisión | ⬜ pendiente (espera a B) |
| D — Postulaciones | ⬜ pendiente (**sin UI**: es lo que falta exponer) |
| Revisión | ⬜ pendiente |

### 3.3 O1–O14 / Ola 6

Sin cambios en esta sesión: el trabajo fue sobre el flujo de perfil y su
infraestructura, sin tocar reglas duras del matching.

---

## 4. Cómo retomar

```powershell
$py = ".\.venv\Scripts\python.exe"

# 1. Abrir la UI y usar el flujo (el camino del usuario)
.\jobpulse-v15-v2.bat
#   → pestaña Perfil → «Completar perfil…»

# 2. Verificación equivalente (solo lectura)
& $py -X utf8 tools\perfil_preguntas.py --top 15
& $py -X utf8 tools\checkpoint_objetivos.py
& $py -X utf8 tools\esquema_bd.py --solo-tablas

# 3. Tests (python del SISTEMA, no el venv)
python -m pytest tests/test_perfil_huecos.py tests/test_conceptos.py -q
```

**Siguiente paso natural**: que el usuario use el flujo «Completar perfil»
(rellena las 277 skills que faltan + marca las áreas) y luego **Fase B**
(refrescar el corpus) antes de una corrida nueva del Paso 5.

---

## 5. Archivos clave

| Archivo | Rol |
|---|---|
| `src/jobpulse_v15/perfil_huecos.py` | **Implementación única** de los huecos (sin Tk) |
| `src/jobpulse_v15/ui_v2/dialogs.py` | `CompletarPerfilDialog` (presenta los huecos, no toca la BD) |
| `src/jobpulse_v15/ui_v2/tabs/perfil.py` | Botón + `completar_perfil()` |
| `src/jobpulse_v15/ui_v2/data/profile.py` | `ProfileStore.huecos()` / `save_many()` / `sincronizar_areas()` / `reemplazar()` |
| `src/jobpulse_v15/repository.py` | `clear_candidate_profile_facts()` |
| `src/jobpulse_v15/conceptos.py` | `resolver()` con fallback de código canónico |
| `docs/PLAN_MEJORORES_PUESTOS.md` | Plan operativo (Fases A–E, S1–S8) |
| `docs/ESTRUCTURA_BD.md` | Mapa de la BD (**actualizar con cada migración**) |
| `tools/perfil_preguntas.py` · `tools/checkpoint_objetivos.py` · `tools/esquema_bd.py` | Verificación (solo lectura) |

---

## 6. Contexto / trampas de esta sesión

1. **`conceptos.resolver`**: la variable de bucle `for (categoria, _variante), ...`
   **sombreaba la función `_variante`** del módulo → `TypeError: 'str' object is
   not callable`. Renombrada a `_variante_mapa`.
2. **`save_analysis` valida coherencia `field_status` ↔ `requirement_level`**:
   un requisito `ambiguous` exige `field_status='ambiguous'` (y al revés). En
   los tests hay que derivar los estados de los requisitos.
3. **El catálogo de áreas no lo siembra la migración**: lo siembra
   `areas.sembrar_taxonomia(connection)` (la CLI `init-areas`). En tests hay
   que llamarlo o `areas_catalogo` viene vacío.
4. **Parchear un diálogo en los tests**: la pestaña hace
   `from ... import CompletarPerfilDialog`, así que hay que parchear
   **`perfil_mod.CompletarPerfilDialog`**, no `dialogs_mod.CompletarPerfilDialog`
   — si no, se abre el diálogo real (modal) y **el test se cuelga**.
5. **`PowerShell >` escribe UTF-16** y `python -c` con comillas anidadas falla →
   usar scripts temporales en `C:\Users\giova\AppData\Local\Temp\opencode`.
6. **No hay migración nueva**: el esquema sigue en **28** y las 27 tablas no
   cambian → `docs/ESTRUCTURA_BD.md` no requiere cambios de estructura (solo la
   nota del flujo en §7).
7. **Los 9 facts con `codigo_canonico` NULL** del perfil real son de categoría
   `experience` (títulos de puesto: 'Soporte Técnico', 'total') → **correcto**:
   no son conceptos y el motor no los lee. Con el fix siguen en NULL (0/9).

---

## 7. Pendiente inmediato

1. **El usuario usa el flujo**: abrir la UI → Perfil → «Completar perfil…» y
   marcar lo que realmente tiene (no se rellena solo: los hechos deben ser
   **reales**).
2. **Luego Fase B** (corpus fresco) y **después** la corrida nueva del Paso 5.
3. **Fase D sigue sin UI** (`postulaciones`): es lo único del plan que aún no
   está expuesto en la UI v2.
4. **Commit pendiente de push**: todo el trabajo de esta sesión está commiteado
   en local (`37ff80c`). **No pushear sin confirmación del usuario.**
