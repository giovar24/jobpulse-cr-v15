# Handoff — Sesión 2026-11-04 (tarde)

**TL;DR**: Cerrado el bloque de **ALINEACIÓN**: los **campos estructurados del
aviso** (`jobs.skills` + `jobs.languages`) ahora son **requisitos
comparables** con el perfil, y la taxonomía creció (migraciones `020`/`021`).
Tres **bugs silenciosos** corregidos (niveles de idioma, resolver sin
`value_code`, extractores de licencia). Nuevo comando
`enrich requirements-source`. **Postulaciones = REGISTRO** (el silencio NO es
rechazo). Suite: **922 tests verdes + 241 subtests** (antes 846). Commits
**pusheados** a `origin/main` (con confirmación del usuario). La **BD real NO
se tocó**: sigue en esquema 19; todo se midió sobre **COPIAS**.

> ⚠️ **La BD real sigue intacta** (esquema 19, 535 avisos). Las migraciones
> `020` y `021` **no** se han aplicado ahí: falta la confirmación del usuario
> (ver §8, pendiente 1). Todo lo que se reporta como "antes/después" en este
> handoff está medido sobre copias en `%TEMP%`.

---

## 1. La decisión que ordena todo lo demás (no cambió)

> **Ser rechazado de un trabajo NO significa que no se es apto para él.**
> (decisión del usuario, 2026-11-04)

Se mantiene la separación del sesión del mediodía:

| | Qué es | Módulo |
|---|---|---|
| **Ajuste técnico** | ¿el perfil cumple lo que pide el aviso? | `viabilidad.py` |
| **Estado del proceso** | ¿qué decidió el reclutador? | `postulaciones.py` |

**Nuevo matiz de esta tarde**: las postulaciones son **REGISTRO**, no señal.
`applied` = "postulada, sin respuesta o en proceso"; el rechazo **solo** se
registra si el portal/correo lo dice explícitamente; **el silencio NO es
rechazo** (muchos sistemas de RH no responden).

---

## 2. Lo que se hizo

### 2.1 Diagnóstico: el hueco era de DATOS, no de motor

El objetivo del software es encontrar, entre **TODOS** los puestos, los que
tienen los requisitos más compatibles con el CV. Para comparar un requisito
del aviso con un hecho del perfil, los dos tienen que hablar el mismo idioma:
la tabla `concepto` (variante → `codigo_canonico`). El motor **solo compara
los requisitos con código** (`AND codigo_canonico IS NOT NULL`): los demás se
ignoran **en silencio**.

Auditoría del corpus real (535 avisos):

| Hallazgo | Dato |
|---|---|
| Avisos sin **ningún** requisito comparable (banda `sin_datos`) | **135** |
| …de esos, los que **sí** tenían `jobs.skills` informado | **133** |
| Avisos con `jobs.languages` (el idioma que **piden**, con nivel CEFR) | **511 / 535** |
| Menciones de skills de la fuente que **resolvían** a concepto (con la 020) | **45 de 2438** (1.8 %) |

**Conclusión**: el dato existía; el sistema no lo usaba. El extractor por
reglas (`analysis.py`) solo lee el **texto**, y el texto de los tableros no
trae las skills ni los idiomas que el aviso exige.

### 2.2 Módulo nuevo `skills_fuente.py` (tests: `tests/test_skills_fuente.py`, 24)

Convierte los campos estructurados del aviso en requisitos comparables, con
cinco **reglas duras**:

1. **solo lo que resuelve a un concepto canónico** — lo que no resuelve va a
   la cola `concepto_no_normalizado` (`origen='oferta'`): la taxonomía crece
   con datos reales, nunca con códigos inventados;
2. **las frases de tarea no son competencias** (`ats.es_frase_de_tarea`):
   "soporte a equipos Dell" es tarea; "apertura de caja" es competencia;
3. **el nivel es `inferred`**: el campo dice QUÉ pide el aviso, no si es
   obligatorio → nunca bloquea ni activa el tope de banda;
4. **la evidencia es literal** (la etiqueta que trae el campo);
5. **no se duplica** lo que el texto del aviso ya dio (mismo código canónico).

Normalización: la clave de búsqueda es `ats._normalize_skill` (minúsculas, sin
acentos, sin `/`), pero la `value_code` emitida es la **variante cruda** de la
tabla `concepto` (el resolutor busca `LOWER(TRIM(value_code))`: si se emitiera
la etiqueta normalizada, el requisito quedaría SIN código → invisible).

### 2.3 `analysis_flow.py` = implementación ÚNICA del análisis

Antes la lógica estaba triplicada (CLI / UI clásica / `run_full_flow`); ahora
`extract_job_analysis` (texto + campos estructurados) es la única, y la usan
la CLI, las dos UI y `run_full_flow`. Se le añadió `preparar_analisis`
(calcula SIN guardar → sirve de dry-run) y `VERSION_ANALISIS =
"rules-2+fuente"` (distinta de `analysis.EXTRACTOR_VERSION`: las revisiones
viejas quedan como historial en `job_analysis`).

Ajuste de estados (respeta la invariante de `Repository.save_analysis`: estado
`ambiguous` ⟺ **todos** los requisitos de la categoría `ambiguous`):

- la categoría ya era `ambiguous`/`unknown` (el texto dejó duda) → los
  requisitos de la fuente pasan a `ambiguous`;
- si no → la categoría pasa a `found`.

### 2.4 Tres bugs silenciosos corregidos

| Bug | Síntoma | Fix |
|---|---|---|
| **Niveles de idioma** | La escala `IDIOMA_ORDEN` tenía las claves en MAYÚSCULAS ("B2") y los requisitos traen el nivel en minúsculas ("b2") → la comparación caía **siempre** en `no_verificable`: el gap de idioma no se veía | `idiomas.normalizar_nivel` ("B2", "b2", "B2+", "C1-C2", "fluent", "intermedio", "nativo") + `orden_nivel`; `matching.cumple_language` normaliza |
| **Resolver sin `value_code`** | Las licencias sin clase ("Driver's license") perdían el código al re-analizar → quedaban invisibles | `conceptos.resolver` cae a `value_text` |
| **Extractor de licencias** | "licencia de conducir B1" / "licencia para conducir D3" perdían la clase | `_LICENSE_CODE` reconoce la clase |

### 2.5 Taxonomía: migraciones `020` y `021`

- **`020_conceptos_alineacion.sql`** — conceptos que el corpus pedía y no
  existían: `java`, `tableau`, `six_sigma`, `c++`, `c#`, `typescript`,
  `autocad`, `solidworks` + clases de licencia de CR (B1, B3, D3…).
- **`021_taxonomia_fuente.sql`** — idiomas que faltaban (alemán, italiano,
  chino, japonés, coreano, árabe, neerlandés) + alias de lo que ya existía
  ("consultas SQL" → `sql`, "Service Now" → `servicenow`, "Microsoft Office"
  → `microsoft-365`…) + **~180 conceptos nuevos** curados del corpus real
  (retail, manufactura, calidad, contabilidad, finanzas, IT/soporte, RRHH).

**Criterio de curación** (documentado en la cabecera de la 021): solo entra lo
que nombra una **competencia, herramienta, norma o método** concreto. Se
deja fuera lo que es una **función** ("ventas"), un **sector**
("construcción"), una **palabra vacía** ("analysis", "planning") o una
**tarea** ("despachar", "empacar"): contarlas como competencia penaliza a
todos los avisos por igual y esconde los gaps reales.

### 2.6 CLI: `enrich requirements-source`

```powershell
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 enrich requirements-source            # simulación
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 enrich requirements-source --apply    # re-analiza y guarda
```

Simula por omisión (dry-run). Devuelve: avisos analizados, avisos con
requisitos de la fuente, total de requisitos de la fuente, cola de
`sin_concepto` (top 50) y errores. Con `--apply` re-analiza (cada aviso
queda con un análisis **nuevo**; el viejo queda como historial).

Se añadió `Repository.list_analisis_records(platform_id)` para listar las
vacantes a re-analizar con sus campos estructurados.

### 2.7 Postulaciones = REGISTRO (no señal de aptitud)

`ETIQUETA_ESTADO`, `etiqueta_estado()`, `sin_respuesta()`;
`Repository.listar_postulaciones` devuelve `estado_texto`/`sin_respuesta` y el
CSV del CLI lleva esas columnas. `applied` = "postulada, sin respuesta o en
proceso".

---

## 3. Decisiones de diseño

| Tema | Decisión |
|---|---|
| Qué es un requisito | Lo que el aviso **pide** (texto + campos estructurados). El perfil se compara con eso. |
| Origen del requisito | `rule` (texto) vs `source_field` (campos estructurados): la diferencia queda auditable en la BD. |
| Nivel de la fuente | `inferred`: el campo dice QUÉ pide, no si es obligatorio. El **texto** sigue mandando (misma regla dura del Paso 5). |
| Qué NO es competencia | Las frases de tarea (`ats.es_frase_de_tarea`): son de todos los avisos y esconden los gaps reales. |
| Taxonomía | Solo lo que resuelve a concepto canónico; lo demás a la cola `concepto_no_normalizado`. **Nunca** se inventa un código. |
| Curry de la taxonomía | Criterio explícito: competencia/herramienta/norma/método; fuera función/sector/palabra vacía/tarea. |
| Duplicado texto↔fuente | Se deduplica por **código canónico**: contar dos veces infla el denominador y falsea el score. |
| Idioma de la fuente | `jobs.languages` = "lo que el aviso PIDE" → manda sobre la regla implícita del idioma del aviso. |
| Niveles | Siempre normalizados antes de comparar (el fallo original era un gap invisible). |
| `sin_datos` | Respuesta HONESTA: si el aviso no declara nada comparable, no se inventa. (Quedan 9 avisos así.) |
| Postulaciones | Registro/bitácora. El silencio NO es rechazo. Nunca se usan como etiqueta de aptitud. |

---

## 4. Estado de objetivos (tabla)

| Objetivo | Estado | Nota |
|---|---|---|
| O1–O6 (pipeline scrape → matching) | Hecho (sesiones previas) | — |
| O7 (IA local/browser) | Hecho | — |
| O8/O10 (retención + diagnóstico) | Hecho | — |
| O2.2 (Req. + filtro) | **Hecho** (2026-11-04) | — |
| O3 (salud de sitios) | **Hecho** (2026-11-04) | — |
| **Capa B (`codigo_canonico` del perfil)** | **Hecho y efectivo en la BD real** | El backfill sería un no-op |
| **Motor de viabilidad (ajuste técnico)** | **Hecho** | Pesos = priors; falta ground truth propio |
| **Postulaciones (correo + Workday)** | **Hecho en código** | Falta validación en vivo (CDP + app-password) |
| **Bloque de ALINEACIÓN (campos estructurados)** | **Hecho en código y MEDIDO sobre copias** | **Falta aplicarlo en la BD real** (ver §8.1) |
| `educacion_no_confirmada` | **ABIERTO** | Requiere firma de una 2ª persona (30 casos) |
| O5.3 (re-barrido descripciones basura) | Pendiente | — |
| O6.4 (dedupe slugs ES/EN) | Parcial | El resolver ya tolera slug↔texto |
| O4 | **Proponer cerrar como *superseded*** | El gate semántico ya no existe |
| O8.2 / O8.4 / O9 / pestañas nuevas UI v2 | Pendiente | — |

**Suite actual**: **922 passed + 241 subtests** (~4:15 min).

---

## 5. Cómo retomar (comandos)

```powershell
# Suite completa (python del SISTEMA)
python -m pytest tests/ -q

# Solo lo nuevo de esta sesión
python -m pytest tests/test_skills_fuente.py tests/test_requisitos_canonico.py `
  tests/test_idiomas.py tests/test_migraciones.py tests/test_cli_viabilidad.py -q

# ── SIMULAR sobre una COPIA de la BD (nunca la real) ─────────────────────
Copy-Item data\jobpulse_v15.db "$env:TEMP\opencode\alineacion.db" -Force
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 --db "$env:TEMP\opencode\alineacion.db" `
  enrich requirements-source
# (aplica 020/021 a la COPIA y lo dice: "[esquema] Se aplicaron las migraciones 20-21")
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 --db "$env:TEMP\opencode\alineacion.db" `
  enrich requirements-source --apply

# ── CUANDO EL USUERO LO APRUEBE: sobre la BD REAL (ver §8.1) ───────────
# .\jobpulse-v15.bat            # UI clásica
# .\jobpulse-v15-v2.bat         # UI v2
```

---

## 6. Archivos clave

| Archivo | Qué es |
|---|---|
| `src/jobpulse_v15/skills_fuente.py` | **(NUEVO)** Campos estructurados del aviso → requisitos comparables |
| `src/jobpulse_v15/analysis_flow.py` | Implementación ÚNICA del análisis (texto + campos estructurados) |
| `src/jobpulse_v15/idiomas.py` | `normalizar_nivel`, `orden_nivel`, `nombre_idioma_a_variante` (fix del bug de niveles) |
| `src/jobpulse_v15/matching.py` | `cumple_language` normalizado · `cumple_license` · `IDIOMA_ORDEN` desde `idiomas.ORDEN_NIVEL` |
| `src/jobpulse_v15/conceptos.py` | `mapa_conceptos` público + fallback a `value_text` en `resolver` |
| `src/jobpulse_v15/repository.py` | `backfill_requirements_canonico` · `list_analisis_records` · `listar_postulaciones` con `estado_texto`/`sin_respuesta` |
| `src/jobpulse_v15/analysis.py` | Extractor de licencias (reconoce la clase tras "licencia de conducir") |
| `src/jobpulse_v15/viabilidad.py` | Rama de licencias (`cumple_license`) + dos pasadas con imputación |
| `src/jobpulse_v15/postulaciones.py` | Núcleo puro del REGISTRO (`ETIQUETA_ESTADO`, `sin_respuesta`) |
| `src/jobpulse_v15/cli.py` | `enrich requirements-canonico` · **`enrich requirements-source`** · `viabilidad` · `postulaciones` |
| `src/jobpulse_v15/migrations/020_conceptos_alineacion.sql` | **(NUEVO)** Conceptos de alineación + clases de licencia CR |
| `src/jobpulse_v15/migrations/021_taxonomia_fuente.sql` | **(NUEVO)** Idiomas + alias + ~180 conceptos curados del corpus |
| `tests/test_skills_fuente.py` | **(NUEVO)** 24 tests del pipeline de campos estructurados |
| `tests/test_requisitos_canonico.py` | **(NUEVO)** 19 tests (taxonomía 020, extractor de licencias, backfill, licencias, idioma por nivel) |
| `tests/test_idiomas.py` | +12 tests (normalización de niveles) |
| `tests/test_migraciones.py` | +13 tests (021) · esquema esperado 21 |
| `tests/test_cli_viabilidad.py` | +4 tests (`enrich requirements-source`) |
| `docs/MOTOR_VIABILIDAD.md` | §2.1 (origen de los requisitos) + calibración actualizada + limitaciones |
| `AGENTS.md` | §"ALINEACIÓN" + comandos + estado de referencia |
| `DESARROLLO_v15.md` | §5 (próxima acción) + §8 (historial) + comandos |

---

## 7. Datos de contexto

- **BD real `data/jobpulse_v15.db`**: 535 avisos, **esquema 19** (017-019
  aplicadas; **020/021 NO aplicadas**), corrida Paso 5 vigente
  `20261103_155215` (calificada 173 · revisar 107 · sin_requisitos 129 ·
  descartada 87 · datos_insuf 39). **INTACTA** (todo lo medido fue sobre
  copias en `%TEMP%`).
- **Medición antes/después (COPIAS)**:

  | Métrica | Antes | Después |
  |---|---|---|
  | Requisitos vigentes con `codigo_canonico` | 1071/1071 | **2172/2172** (1101 de `source_field`) |
  | Viabilidad `sin_datos` | 133 | **9** |
  | Viabilidad `aplicar` / `revisar` / `no_prioritario` / `veto` | 4 / 4 / 307 / 87 | 4 / 2 / 433 / 87 |
  | Paso 5 `sin_requisitos` | 123 | **9** |
  | Paso 5 `revisar_a_mano` | 111 | 275 |
  | Top 4 `aplicar` | estables | Clerk III- Accounts Receivable (myhrabc), Rep HR Solutions (edwards), Sales Support Coordinator (LifeSync-Amphenol), Imaging Research Associate I (clarioclinical) |

- **Gaps que ahora se ven** (antes invisibles): bachelor 71, python 26,
  apertura de caja 26, facturación 22, cobro 21, transacciones de cobro 18,
  frenteos 16, aws 12, azure 12, cierre de caja 12, gcp 9, power_bi 9,
  tableau 8, six_sigma 8. Los "F5 BIG IP & Kubernetes" y "F5 Distributed
  Cloud" bajaron a `revisar` (30.6) con los gaps aws/azure/gcp a la vista
  (falso positivo de cloud corregido).
- **Los 9 que quedan `sin_datos`**: IT-Hardware & Networking, QA Tester
  (indeed), Technical Success Support Specialist (indeed), IT/OT Terminal
  Support Analyst (indeed) y 5 de Harvie (Bodeguero). Sus skills son frases
  de tarea o campos genéricos ("desarrollo", "computer hardware",
  "troubleshoot complex technical issues") → no hay competencia que comparar.
- **Perfil real**: 23 skills con código (javascript, git, excel, sql,
  servicenow, aws, azure, linux, active-directory, microsoft-365,
  google-workspace, power-bi, vpn, iam, cmdb, sccm, intune, okta, grafana,
  html, css, gcp, sap), 2 idiomas (espanol nativo, ingles B2), 2 educación
  (secundaria + técnica), 9 experience (títulos de puesto), 6 certificaciones
  (sin código), 16 años. **Sin título universitario** → 87 vetos.
- **Taxonomía**: 48 conceptos skill + 6 license + 13 language (antes de
  020/021) → 020/021 la amplían. Cola `concepto_no_normalizado`: 1507 skills
  sin concepto (siguiente tanda de curación; son la lista de trabajo).
- **Scripts de auditoría** (en `%TEMP%\opencode\`): `medir_pipeline.py`
  (antes/después completo), `medir_021.py`, `analizar_gaps.py`,
  `diag_codigos.py`, `diag_nodatos.py`, `audit_*.py`.
- **Tests**: `python -m pytest tests/ -q` (python del SISTEMA); app/CLI con
  `.\.venv\Scripts\python.exe -X utf8`.
- **Commits**: esta sesión (ver §9).

---

## 8. Pendiente inmediato

1. **APLICAR el bloque de alineación en la BD REAL** (pide confirmación
   explícita del usuario — **la BD real sigue en esquema 19**):
   ```powershell
   # 1. (el CLI auto-migra: aplica 020+021 y lo avisa por consola)
   .\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 enrich requirements-source
   # 2. aplicar (re-analiza los 535 avisos, ~22 s)
   .\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 enrich requirements-source --apply
   # 3. backfill de los requisitos viejos (idempotente, solo NULL)
   .\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 enrich requirements-canonico --apply
   # 4. corrida NUEVA del Paso 5 + evidencia
   .\.venv\Scripts\python.exe -X utf8 run_paso5.py
   .\.venv\Scripts\python.exe -X utf8 generar_evidencia_paso5.py
   .\.venv\Scripts\python.exe -X utf8 verificar_evidencia.py   # exit 0 = TODO CUADRA
   ```
   Ojo: el orden 2→3 es el que se midió (el backfill primero también vale:
   rellena los NULL de los requisitos viejos).
2. **Validación en vivo** de postulaciones (necesita al usuario): Brave con
   CDP 9222 (`postulaciones workday --apply`) y la app-password de Gmail en el
   keyring (`postulaciones correo --dias 90 --apply`).
3. **`educacion_no_confirmada`** (30 casos): solo las firma una **segunda
   persona** en `docs/PASO5_REVISION_PENDIENTES.md` (el veredicto del autor
   de la regla se descarta por sesgo). **NO** actualizar estados hasta la firma.
4. **Curar la cola de la taxonomía**: 1507 skills de la fuente sin concepto
   (`concepto_no_normalizado`) → cada tanda sube la cobertura y baja los
   `sin_datos`.
5. O5.3 (re-barrido de descripciones basura), O6.4 (slugs ES/EN), O8.2/O8.4,
   O9 y las pestañas nuevas de la UI v2.

---

## 9. Commits de esta sesión

- `feat(alineacion): los campos estructurados del aviso son requisitos` —
  `skills_fuente.py` (nuevo), `analysis_flow.py`, `idiomas.py`,
  `matching.py`, `conceptos.py`, `repository.py`, `cli.py`, `analysis.py`,
  `viabilidad.py`, `postulaciones.py`, migraciones `020`/`021`.
- `test(alineacion): 76 tests nuevos` — `test_skills_fuente.py` (nuevo),
  `test_requisitos_canonico.py` (nuevo), `test_idiomas.py`,
  `test_migraciones.py`, `test_cli_viabilidad.py`, `test_conceptos.py`,
  `test_postulaciones.py`.
- `docs(alineacion): AGENTS + DESARROLLO + MOTOR_VIABILIDAD + handoff` —
  **pusheados** a `origin/main` con la confirmación del usuario (2026-11-04).
