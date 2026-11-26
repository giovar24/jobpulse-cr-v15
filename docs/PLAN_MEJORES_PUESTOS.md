# Plan — encontrar los mejores puestos para el perfil cargado

> Creado **2026-11-26**. Este es el **plan operativo** de la meta general
> («encontrar los mejores puestos para el perfil cargado»); el backlog de
> *código* sigue en `docs/PLAN_MEJORAS.md`. Cada paso lleva su comando y cada
> **objetivo secundario (S1–S8)** su criterio de cierre verificable, para que
> una sesión que se quede sin tokens pueda retomar sin re-descubrir nada.
> El estado base de este plan se mide con
> `python tools\checkpoint_objetivos.py` (solo lectura).

> **Requisito de diseño (2026-11-26)** — todo lo que este plan pide
> implementar debe ser **una sola implementación general**, expuesta como
> **flujo en la UI v2**, no como scripts CLI sueltos. Vale para **cualquier
> perfil cargado**: los huecos y las preguntas se **calculan de forma
> determinista desde la BD** (lo que el corpus pide vs. lo que el perfil
> registra); no los redacta la IA sesión a sesión. Los comandos CLI de este
> documento quedan como **verificación/desarrollo**, no como vía principal.

---

## 1. Objetivo general y cómo se mide

**Objetivo**: que `viabilidad top` / la UI v2 devuelvan una lista corta de
vacantes que el usuario **quiera aplicar de verdad**, con ajuste alto,
requisitos cubiertos y datos frescos.

**Se cumple cuando** (todas juntas):

1. El perfil refleja lo que el usuario **realmente** tiene (skills, idiomas,
   licencia, educación, áreas) y todo hecho relevante tiene `codigo_canonico`.
2. El corpus está fresco (sin vacantes vencidas mostrándose, fuentes
   re-scrapeadas, ubicación normalizada).
3. Hay una **corrida nueva** del Paso 5 con evidencia verificada
   (`verificar_evidencia.py` → exit 0).
4. La banda `aplicar`/`revisar` creció de forma honesta (no por aflojar
   umbrales — están congelados) y `no_prioritario` bajó.
5. El usuario registra sus postulaciones (hoy: **0**), para que el sistema
   empiece a tener retroalimentación real.

---

## 2. Estado base — medido 2026-11-26 (corrida `20261111_074200`)

Reproducir con `.\.venv\Scripts\python.exe -X utf8 tools\checkpoint_objetivos.py`
y `… -m jobpulse_v15 viabilidad top --limit 1` (clave `bandas`).

| Dimensión | Valor base |
|---|---|
| Paso 5 (corrida vigente) | revisar_a_mano **385** · calificada **202** · descartada 101 · datos_insuficientes 36 · sin_requisitos 11 |
| Bandas de viabilidad | aplicar **4** · revisar **16** · no_prioritario **600** · veto **101** · sin_datos 15 |
| Perfil | 48 facts · skill 23 (todos con código) · education 2 · language 2 · **áreas 0** · **licencias 0** |
| Perfil sin código | 21 facts (9 experience, 6 certification, 5 contact, 1 summary) → **no leídos por el motor** (solo lee skill/language/education/license) |
| Cobertura de skills | 283 evaluables en corpus · **11 en perfil** · 272 ausentes |
| Top skills ausentes | python(31), frenteos(25), troubleshooting(24), apertura-caja(23), analisis-de-datos(22), facturacion(22), power-bi(20), atencion-al-cliente(19), aws(17), cobro(17) |
| Vetos de educación | 101 = 78 `titulo_universitario_requerido` + 23 `titulo_universitario_en_curso_requerido` (el perfil NO tiene título universitario) |
| Licencia de conducir | 68 avisos la piden (14 `required`) · taxonomía ya tiene `licencia-conducir` · perfil: 0 |
| Corpus | 736 jobs · **27 vencidos** · 166 sin ciudad · 87 loc sin normalizar |
| Fuentes | LinkedIn **1** aviso · Indeed 30 · Procomer 1 (colapso de LinkedIn sin explicar) |
| Análisis | obsoletos **0** · requisitos sin código **0** · analysis_missing 1 · extract-pending 0 |
| Evidencia Paso 5 | **al día** (corrida `20261111_074200`, doc `PASO5_EVIDENCIA_2026-11-11.md`) |
| Postulaciones | **0** |
| Salud sitios | needs_review 0 · cola taxonomía 1150 (ruido de baja frecuencia, no bloquea) |

---

## 3. Fase A — Completar el perfil (prioridad 1)

**Por qué primero**: el motor ignora en silencio lo que el perfil no tiene;
con 11 de 283 skills, `skill_faltante` = 306 y la banda `aplicar` está en 4.

**Principio**: el flujo es **agnóstico del titular** y **se implementa una
sola vez, expuesto en la UI v2**. No asume qué tiene la persona: los huecos
se **calculan de forma determinista** comparando lo que el **corpus** pide
(requisitos evaluables con `codigo_canonico`) contra lo que el **perfil**
registra, por categoría que el motor lee (`skill`, `language`, `education`,
`license`) + el catálogo de áreas + los hechos sin código.

> **Estado de implementación (2026-11-26)**: ✅ **implementado**.
> La lógica vive en el paquete, en `src/jobpulse_v15/perfil_huecos.py`
> (implementación única, sin Tk, como `analysis_flow`); la UI v2 la expone en
> la pestaña **Perfil** con el botón **«Completar perfil…»**
> (`ui_v2/dialogs.py::CompletarPerfilDialog` + `ui_v2/tabs/perfil.py`).
> `tools/perfil_preguntas.py` quedó como **envoltorio de verificación** de esa
> misma implementación (no hay dos copias de la lógica).

| # | Paso (flujo en la UI v2) | Cómo | Verificación |
|---|---|---|---|
| A1 | Pestaña **Perfil** → «Completar perfil…»: la UI lista, por categoría, lo que el corpus pide y el perfil no tiene (priorizado por nº de avisos), el catálogo de áreas y los hechos sin `codigo_canonico` | ✅ `PerfilTab.completar_perfil()` → `ProfileStore.huecos()` → `CompletarPerfilDialog` | la lista sale de la BD; 0 datos hardcodeados (`tests/test_perfil_huecos.py`) |
| A2 | El titular confirma **en ese mismo flujo**: skills reales, idiomas + nivel CEFR, licencia + tipo, educación (regla O6.5), áreas | ✅ casillas en el diálogo + «Marcar visibles» / filtro por código | `tools\checkpoint_objetivos.py` → «en perfil» sube; `areas`/`licencias` > 0 |
| A3 | Al guardar, el flujo resuelve `codigo_canonico` (misma implementación que `enrich profile-canonico`) | ✅ `Repository.save_candidate_profile_facts` → `conceptos.resolver` (con fallback: un `value_code` que **ya es** código canónico se resuelve a sí mismo) | 0 facts de categorías motor sin código |
| A4 | **NO** ejecutar el Paso 5 aún: primero Fase B (si no, hay que repetir la corrida) | — | — |

> La **educación** (O6.5) y las **áreas** son decisiones del titular con
> reglas propias (≥80 % de créditos documentados; marcar áreas *reduce* el
> corpus evaluado — hoy 0 = se evalúa todo). Los hechos de categorías que el
> motor **no** lee (experience/certification/contact/summary) no bloquean
> nada: dejarlos así salvo que otra categoría pase a leerse.

### 3.1 Dónde se ejecuta cada fase en la UI (la UI es la vía principal)

| Fase | UI v2 |
|---|---|
| A — perfil | pestaña **Perfil** → botón **«Completar perfil…»** (✅ implementado 2026-11-26) |
| B — corpus | pestaña **Scraping**: «Ejecutar grupo» (scrape) |
| B/C — análisis, IA, re-análisis, backfill, Paso 5, evidencia | pestaña **Scraping**: «Procesar» / «Enriquecer IA» · pestaña **Vacantes**: «Ejecutar Paso 5» + evidencia |
| D — postulaciones | **sin UI hoy** (solo CLI): única parte que falta exponer |
| revisión de resultados | pestaña **Vacantes**: bandas, viabilidad, faltantes |

Los comandos de las tablas siguientes son la **verificación** equivalente
(para scripts y sesiones); la ejecución diaria del usuario es la UI.

## 4. Fase B — Corpus fresco y limpio (prioridad 2)

| # | Paso | Comando |
|---|---|---|
| B0 | Backup (barato, antes de tocar datos) | `& $py -X utf8 -m jobpulse_v15 backup --output data\backups\plan-mejores-puestos.db` |
| B1 | **Re-scrape LinkedIn** (colapsado a 1 aviso) e Indeed. Si el scraper es de navegador, CDP primero: `python -c "from jobpulse_v15.browser_manager import asegurar_brave; asegurar_brave(9222)"`. | `& $py -X utf8 run_full_flow.py --only-scrape --pages 1` (o `-m jobpulse_v15 scrape <plataforma> --site <id>`) |
| B2 | Análisis de lo nuevo (idempotente) | `& $py -X utf8 -m jobpulse_v15 analysis extract-pending --limit 500` |
| B3 | Enriquecimiento IA + integración de campos estructurados + backfill (orden obligatorio: 3 → 4 → 5) | `& $py -X utf8 run_enriquecimiento.py` · `… enrich requirements-source --apply` · `… enrich requirements-canonico --apply` |
| B4 | Normalizar ubicación (87 → 0) | `& $py -X utf8 -m jobpulse_v15 location normalize` |
| B5 | Revisar los **27 vencidos**: decidir si se ocultan (ver E4) y los 19 grupos de duplicados (`quality report`) → dedupe **manual**, nunca automerge | `& $py -X utf8 -m jobpulse_v15 quality report` |

## 5. Fase C — Corrida nueva del Paso 5 + evidencia (prioridad 3)

**Nunca** un `UPDATE` de la corrida anterior: siempre corrida nueva.

| # | Paso | Comando |
|---|---|---|
| C1 | Ensayo (no escribe) | `& $py -X utf8 run_paso5.py --dry` |
| C2 | Corrida real (por defecto evalúa solo las áreas del perfil; `--evaluar-todo` si se marcó alguna) | `& $py -X utf8 run_paso5.py` |
| C3 | Evidencia + verificación (**exit 0 = todo cuadra**) | `& $py -X utf8 generar_evidencia_paso5.py` · `& $py -X utf8 verificar_evidencia.py` |
| C4 | Hoja de firma si queda algún `educacion_no_confirmada` (hoy: 0 abiertos) | `& $py -X utf8 generar_revision_pendientes.py` |
| C5 | Comparar contra §2: bandas y estados | `tools\checkpoint_objetivos.py` · `… viabilidad top --limit 1` |

## 6. Fase D — Registro de postulaciones (prioridad 4)

Sin registro no hay retroalimentación ni historial de qué se aplicó.

| # | Paso | Comando |
|---|---|---|
| D1 | Importar señales históricas (correo 90 días / Workday) | `& $py -X utf8 -m jobpulse_v15 postulaciones correo --dias 90 --apply` · `… postulaciones workday --apply` |
| D2 | A partir de ahí, registrar **cada** postulación que el usuario haga desde la lista de `aplicar`/`revisar` | `… postulaciones list` (verificación: deja de ser 0) |

## 7. Fase E — Decisiones que solo puede tomar el usuario

Ninguna bloquea las fases A–D; todas quedan **pendientes de decisión**
registrada en el handoff.

| # | Decisión | Dónde se documenta |
|---|---|---|
| E1 | **O6.5**: ¿el usuario está en realidad estudiando con ≥80 % de créditos? (A3 depende de esto) | `docs/REGLAS_NEGOCIO_EDUCACION.md` |
| E2 | **O6.4**: slugs ES/EN de conceptos — ¿se hace o se cierra? | `docs/PLAN_MEJORAS.md` §6 |
| E3 | **Ola 6.1**: RAG consultivo + carta de presentación — ¿se arranca? | `docs/PLAN_MEJORAS.md` §6.1 |
| E4 | **O8.2 / O10**: ocultar vencidas y recurrentes/aplicadas (`solo_vigentes`); hoy los 27 vencidos siguen en la lista | `docs/PLAN_MEJORAS.md` |

---

## 8. Objetivos secundarios (checkpoints S1–S8)

**Regla de uso**: cada sesión nueva corre `tools\checkpoint_objetivos.py`,
compara con §2 y retoma **el primero de la tabla que esté ⬜**. Si un paso no
se pudo cerrar, se anota *por qué* en el handoff (no se salta en silencio).

| ID | Objetivo secundario | Criterio de cierre | Verificación (una sola línea) | Estado |
|---|---|---|---|---|
| **S1** | Perfil completo y honesto | El flujo «Completar perfil» (UI) no muestra preguntas pendientes (o solo las que el titular decidió no aplicar); 0 facts de categorías motor sin código | UI → **Perfil** (o `… tools\perfil_preguntas.py` como sustituto) + `… tools\checkpoint_objetivos.py` | ⬜ |
| **S2** | Corpus fresco | LinkedIn e Indeed re-scrapeados (LinkedIn > 1 aviso) | `… -X utf8 tools\estado_bd.py` (recuento por plataforma) | ⬜ |
| **S3** | Ubicación normalizada | `location_not_normalized` de 87 → 0 | `… -m jobpulse_v15 quality report` | ⬜ |
| **S4** | Análisis al día | `analysis_missing` = 0, obsoletos = 0, extract-pending = 0 | `quality report` + `tools\estado_bd.py` | ⬜ |
| **S5** | Corrida nueva con evidencia | `corrida_id` ≠ `20261111_074200`, estados suman el total evaluable, `verificar_evidencia.py` exit 0 | `tools\checkpoint_objetivos.py` + `… verificar_evidencia.py` | ⬜ |
| **S6** | Mejores puestos visibles | `bandas`: `aplicar`+`revisar` > 20 (base 4+16) y `no_prioritario` < 600, **sin tocar umbrales** | `… -m jobpulse_v15 viabilidad top --limit 1` | ⬜ |
| **S7** | Postulaciones registradas | `postulaciones` > 0 | `… -m jobpulse_v15 postulaciones list` | ⬜ |
| **S8** | Decisiones E1–E4 cerradas o explícitamente diferidas | Cada decisión con veredicto escrito en el handoff/PLAN_MEJORAS | `grep` de la decisión en `docs/` | ⬜ |

---

## 9. Protocolo de reanudación (sesión nueva, tokens limitados)

1. Leer el **handoff más reciente** `docs/HANDOFF_SESION_*.md` (pendiente inmediato).
2. Leer **este plan**: §2 (base) y §8 (tabla de estados).
3. Correr:
   ```powershell
   $py = ".\.venv\Scripts\python.exe"
   & $py -X utf8 tools\checkpoint_objetivos.py
   & $py -X utf8 tools\perfil_preguntas.py --top 15
   & $py -X utf8 -m jobpulse_v15 viabilidad top --limit 1
   ```
   (mediciones **solo lectura**. El **camino del usuario** es la UI v2:
   Perfil → Scraping → Vacantes; el botón **«Completar perfil…»** de la
   pestaña Perfil es el flujo real — `perfil_preguntas.py` es solo su
   envoltorio de verificación.)
4. Comparar con §2 → actualizar la columna **Estado** de S1–S8 → retomar el
   primer ⬜ (si la Fase A está a medias, seguir ahí; no saltar a C).
5. Duda de regla → `docs/REGLAS_NEGOCIO_EDUCACION.md` y `AGENTS.md`.
6. Al cerrar sesión: handoff nuevo + **commit** (no push sin confirmación).

---

## 10. Reglas duras que este plan no toca

- Umbrales del Paso 5 **congelados** (0.60 / 0.80): el crecimiento de
  `aplicar` viene de **datos**, no de aflojar.
- Estados solo con **corrida nueva** (nunca `UPDATE`).
- Hechos de perfil solo si son **reales** (nada hardcodeado, perfil = facts
  en BD) y con `codigo_canonico` (sin él, el motor lo ignora en silencio).
- Educación: nunca descartar por falta de información; «en curso» exige
  ≥80 % documentado; `educacion_no_confirmada` solo lo firma una segunda
  persona.
- Dedupe conservador: nunca borrar ni fusionar automáticamente.
- Backup antes de operaciones sobre el corpus; BD no está en git;
  **no pushear sin confirmación del usuario**.
- Dos Pythons: app/CLI → `.\.venv\Scripts\python.exe -X utf8` ·
  tests → `python -m pytest tests/ -q` (python del sistema).
