# Handoff — Sesión 2026-11-01: **regla de idioma del aviso en el matching** (idioma detectado + backfill + corrida nueva del Paso 5)

## TL;DR

Sesión corta y de una sola pieza, continuación del bloque 7 del 31-10:

**Regla nueva de negocio (pedida por el usuario):** *el requisito de idioma de un
aviso es **el idioma en que está escrito el aviso**, salvo que el aviso **pida**
uno o varios idiomas como requisito; en ese caso, los que pide el aviso son los
requisitos.*

Para aplicarla hizo falta un dato que la BD no tenía en 331 de las 553 vacantes
(`posting_language='undetermined'` en los tableros): un **detector
determinista** del idioma del aviso (sin IA, cuenta palabras funcionales) y un
**backfill** idempotente. Después, la regla se cableó en **el motor del Paso 5**
y en **la comparación de la UI** (para que no diverjan).

- Nuevo módulo `src/jobpulse_v15/idiomas.py` (detector + `CODIGO_IDIOMA`).
- `Repository.save_job` detecta el idioma **al guardar** (origin `detected`);
  comando nuevo `enrich posting-language` (dry-run por defecto).
- Backfill **aplicado**: 331 registros → **267 en · 41 es · 23 mixed · 0
  undetermined**; 2.ª pasada **0** (idempotente).
- Regla en `matching.py` (`requisitos_efectivos`, `cumple_idioma_del_aviso`,
  `Requisito.implicito`) y en `repository._requisitos_con_regla_de_idioma`.
- **Corrida NUEVA** del Paso 5: **`20261101_084012`** (`valida=1`) →
  calificada **179** · sin_requisitos **140** · revisar_a_mano **106** ·
  descartada **89** · datos_insuficientes **39** (= **553**, cuadra por
  `GROUP BY estado`).
- Efecto medido vs. la corrida anterior `20261031_214155`: `total_req`
  **986 → 1242** y **4 avisos cambian de estado** (2 `datos_insuficientes` →
  `sin_requisitos`, 2 → `calificada`); **0** avisos con motivo de idioma (el
  perfil tiene español **y** inglés, así que el idioma del aviso se cumple).
- Suite: **486 tests verdes** + **179 subtests** (`test_matching.py` 87,
  `test_idiomas.py` 7, `test_repository.py` 42).
- Evidencia regenerada para la corrida vigente:
  `docs/PASO5_EVIDENCIA_2026-11-01.md` (1801 líneas) y
  `verificar_evidencia.py` → **TODO CUADRA (130 verificaciones con frase
  literal)**; hoja de firma `docs/PASO5_REVISION_PENDIENTES.md` con **30**
  `educacion_no_confirmada`.
- **IA local APAGADA** (puerto 8081 libre). Brave sigue abierto **sin CDP**
  (es el Brave diario del usuario; la app no lo abrió, así que no se cerró).

## Lo que se hizo

### 1. El dato que faltaba: idioma del aviso

- **`src/jobpulse_v15/idiomas.py`** (nuevo):
  - `detectar_idioma_del_aviso(*textos)` → `es` / `en` / `mixed` /
    `undetermined`. Cuenta **palabras funcionales** de cada idioma (señal más
    estable que el vocabulario técnico, idéntico en ambos), normaliza acentos
    y exige un mínimo de **10** marcas; si no llega, o si la proporción cae
    entre 25 % y 75 %, **no adivina** (`mixed`/`undetermined`).
  - `CODIGO_IDIOMA` / `codigo_canonico_del_idioma`: `es`→`espanol`,
    `en`→`ingles` (los `codigo_canonico` que ya existen en `concepto`).
- **`Repository.save_job`**: si la fuente **no declara** idioma
  (`None`/`undetermined`), se detecta con el texto del aviso (título +
  `description_raw` + `requirements_raw`) y se guarda con
  `posting_language_origin='detected'`. Un idioma declarado por la fuente
  (`origin='source'`) **nunca** se pisa.
- **`Repository.list_posting_language_records` / `set_job_posting_language`**:
  backfill que solo rellena huecos (el `UPDATE` lleva
  `AND (posting_language IS NULL OR posting_language='undetermined')`).
- **CLI `enrich posting-language`** (`--platform`, `--limit`, `--apply`):
  misma forma que `enrich work-mode` (dry-run por defecto, informe JSON con
  `records_scanned`/`detected`/`updated`/`undetermined`/`by_language`).

**Validación del detector contra la verdad de campo** (las 222 vacantes que la
fuente declara en español): **193 es · 15 en · 14 undetermined**. Los 15 "en"
son avisos de **CINDE escritos en inglés** con la metadata en español (el
detector acierta: el aviso está en inglés); los 14 "undetermined" son avisos
con texto demasiado corto o muy técnico. Ningún falso positivo en `mixed`.

### 2. La regla en el motor (Paso 5)

`matching.EvaluadorPaso5`:

- `_cargar_idioma_aviso()`: idioma declarado/detectado por `job_id`.
- `Requisito.implicito` (nuevo campo): marca el requisito que **no** pide el
  aviso sino que se **deduce** de la regla.
- `requisitos_efectivos(job_id)`:
  1. Los idiomas que el aviso **pide** (`required`/`inferred`/`ambiguous`) son
     los requisitos de idioma. Un idioma solo **`preferred` NO es requisito**.
  2. Si el aviso **no pide** ningún idioma → se agrega **el idioma del aviso**
     como requisito `required` (evidencia `idioma del aviso`).
  3. Si el aviso **no tiene otros requisitos**, **no** se agrega el idioma
     implícito: la oferta se queda en `sin_requisitos` (no se califica una
     oferta solo por su idioma).
  4. `mixed` / `undetermined` **no** generan requisito (no hay un idioma único
     del aviso).
- `cumple_idioma_del_aviso(codigo)`: `True` si el perfil registra ese idioma ·
  `"no_verificable"` si el perfil **no registra ningún idioma** (nunca se
  afirma que no cumple) · `False` si registra otros idiomas pero no ese
  (→ `revisar_a_mano` con motivo `idioma_no_comparable`).
- `evaluar_job` usa `requisitos_efectivos` (en vez de los requisitos crudos) y
  distingue el requisito implícito en la rama de idioma.

### 3. La misma regla en la comparación de la UI

`Repository.compare_job_to_candidate_profile` /
`compare_jobs_to_candidate_profile` pasan `posting_language` a
`_compare_candidate_profile`, que aplica
`_requisitos_con_regla_de_idioma(...)` — **misma** regla que el Paso 5
(idioma del aviso si no pide idiomas; `preferred` no cuenta). Se añadió para
que la pestaña de la UI no muestre una compatibilidad distinta a la que firma
el Paso 5.

### 4. Tests

- **`tests/test_idiomas.py`** (nuevo, 7 casos): detecta es/en/mixto, texto
  corto → `undetermined`, texto vacío → `undetermined`, varios textos del
  aviso, mapeo a `codigo_canonico`.
- **`tests/test_matching.py`** → `TestReglaIdiomaDelAviso` (8 casos): el
  idioma del aviso es el requisito; cubierto no falla (`total_req=2`,
  `faltantes=[]`); si el aviso pide otro idioma manda el que pide;
  `preferred` no es requisito (se usa el del aviso, `implicito=True`); aviso
  sin otros requisitos → `sin_requisitos`; perfil sin idiomas → no
  verificable; idioma del aviso que el perfil no tiene → `revisar_a_mano` +
  `idioma_no_comparable`; `mixed` no da requisito. El helper
  `_insertar_job` acepta `posting_language` (por defecto `undetermined`,
  porque la columna es NOT NULL).
- **`tests/test_repository.py`** (+1): la comparación de la UI aplica la
  regla (aviso en español sin idiomas pedidos → requisito `espanol`
  `matched`).
- **Suite completa**: `python -m pytest tests/ -q` → **486 passed, 179
  subtests passed** (3 min 29 s).

### 5. Backfill + corrida nueva

- `enrich posting-language` (dry-run) → 331 registros, todos con idioma
  detectable → **en 267 · es 41 · mixed 23**.
- `--apply` → **331 actualizados**; 2.ª pasada → **0** (idempotente).
- Distribución final de `jobs.posting_language` (553): **es/source 222 ·
  en/detected 267 · es/detected 41 · mixed/detected 23**.
- **Corrida nueva** `run_paso5.py` (sin `--dry`): `20261101_084012`
  (`valida=1`, 553 filas).
- Comparación con la corrida anterior (script
  `Temp\opencode\comparar_corridas.py`):

| | `20261031_214155` (pre-regla) | `20261101_084012` (con la regla) |
|---|---|---|
| calificada | 177 | **179** |
| sin_requisitos | 138 | **140** |
| revisar_a_mano | 106 | 106 |
| descartada | 89 | 89 |
| datos_insuficientes | 43 | **39** |
| `total_req` (suma) | 986 | **1242** |

Cambios puntuales (4): `harvie-2022` (Vendedor de Repuestos, **es**) y
`workday-QA-Tester_REQ575669` (**mixed**) pasan de `datos_insuficientes` a
`sin_requisitos`; `workday-Functional-Technical-Analyst---Future-Project` y
`workday-Soporte-y-Mantenimiento-de-Aplicaciones---Future-Project` (**mixed**)
pasan de `datos_insuficientes` a `calificada` (el idioma del aviso entra en
`total_req` y sube la cobertura).

**Motivos con "idioma": 0** en ambas corridas — el perfil registra español
(Nativo) e inglés (B2), así que el idioma del aviso se cumple y la regla no
descarta nada en este corpus. El efecto real es de **cobertura** (entra un
requisito más por aviso) y de **estado** en 4 avisos.

### 6. Evidencia y cierre

- `generar_evidencia_paso5.py` → `docs/PASO5_EVIDENCIA_2026-11-01.md`
  (1801 líneas, corrida `20261101_084012`, descartada 89, no_confirmada 30).
- `verificar_evidencia.py` → **exit 0**, «TODO CUADRA: 130 verificaciones con
  frase LITERAL» (elige el doc de la corrida vigente, no el de nombre más
  alto).
- `generar_revision_pendientes.py` → `docs/PASO5_REVISION_PENDIENTES.md`
  (572 líneas, **30** casos, sin veredictos).
- `db check` → `integrity_check: ok`, 0 violaciones FK, esquema **16**.

## Decisiones de diseño (esta sesión)

1. **El detector es determinista y conservador**: cuenta palabras funcionales
   (no IA, no dependencia nueva) y ante la duda devuelve `mixed`/`undetermined`
   **en vez de adivinar**. Un idioma mal adivinado se convertiría en un
   requisito falso que descarta ofertas.
2. **`mixed` y `undetermined` no generan requisito**: si el aviso no tiene un
   idioma único, no hay un "idioma en que hay que poder trabajar" que afirmar.
3. **El idioma del aviso solo cuenta si el aviso tiene otros requisitos**: no
   se califica (ni se cuenta como cobertura) una oferta **solo** porque su
   idioma se cumple. Si no hay más requisitos, sigue siendo
   `sin_requisitos`.
4. **`preferred` no es requisito** (coherente con la regla dura del repo,
   §Matching de `AGENTS.md`): "Spanish preferred" deja de bloquear y manda el
   idioma del aviso.
5. **Perfil sin idiomas → `no_verificable`, no `faltante`**: nunca se afirma
   que no cumple por falta de información (misma regla que educación).
6. **El idioma declarado por la fuente no se pisa**: la detección solo cubre
   `undetermined` (origin `detected`), y queda auditable el origen.
7. **Detección al guardar + backfill**: `save_job` detecta desde el primer
   día (ninguna vacante nueva nace sin idioma) y `enrich posting-language`
   rellena lo ya guardado, idempotente y con dry-run por defecto.
8. **UI y Paso 5 con la MISMA regla, explícita en un solo método**
   (`_requisitos_con_regla_de_idioma`): la lección del 31-10 (lógica
   duplicada = divergencia) aplicada antes de que ocurra.
9. **Nueva corrida del Paso 5, nunca `UPDATE` de una corrida emitida**
   (convención del repo): queda `20261031_214155` con `valida=0` para poder
   comparar el efecto de la regla.
10. **Umbrales intactos** (cobertura 0.60 / puntaje 0.80).

## Estado de objetivos (tabla O1–O10)

| Objetivo | Estado |
|---|---|
| O1 enriquecimiento IA | ✅ completo (servidor local, veredicto IA) + `work_mode` determinista · **+ idioma del aviso determinista + `enrich posting-language` (01-11, sin IA)** |
| O2 búsqueda data-first | 🟡 O2.1 locations Indeed + O2.2 filtro “Req.” |
| O3 fetchers ATS | 🟢 7/7 plataformas validadas; scrape de 129 sitios con 0 errores (31-10) |
| O4 calibración gate-vs-IA | ⏳ redefinir (sin gate semántico no hay contra-qué) |
| O5 higiene de datos | 🟡 **O5.3 pendiente con 22 descripciones basura (15 Indeed login-wall)** · catálogo territorial CR + 3 reglas de ubicación (31-10) · **idioma del aviso: 0 `undetermined` en la BD (01-11)** |
| O6 perfil del candidato | 🟡 regla + mecánicas M1–M4 ✅; **30 `educacion_no_confirmada` ABIERTAS** · **regla de idioma del aviso ✅ (01-11)** · Paso 7 pendiente |
| O7 operación UI-first | ✅ completo (Brave auto-gestionado O7.2) |
| O8 ciclo de vida | 🟡 O8.1 ✅ (áreas) · O8.2 pendiente |
| O9 optimización UI | ⏳ placeholder |
| O10 mejorar filtros | 🟡 `elegir_filtro_compatibilidad` + filtro por área ✅ · **filtro “Idioma anuncio” con datos reales (es 263 / en 267 / mixed 23) (01-11)** |

## Cómo retomar

```powershell
# Idioma del aviso: ver que detectaria y aplicarlo (idempotente, solo huecos)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 enrich posting-language
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 enrich posting-language --apply

# Paso 5: corrida NUEVA (nunca UPDATE de una corrida emitida)
.\.venv\Scripts\python.exe -X utf8 run_paso5.py [--dry] [--evaluar-todo]

# Evidencia de la corrida VIGENTE (el generador nombra el archivo por corrida;
# el verificador elige el doc de esa corrida, no el de nombre mas alto)
.\.venv\Scripts\python.exe -X utf8 generar_evidencia_paso5.py
.\.venv\Scripts\python.exe -X utf8 verificar_evidencia.py        # exit 0 = TODO CUADRA
.\.venv\Scripts\python.exe -X utf8 generar_revision_pendientes.py

# Tests (python del SISTEMA; el venv NO tiene pytest)
python -m pytest tests/ -q

# UI (la corrida de la regla por la UI: la IA no se pre-arranca)
.\jobpulse-v15.bat
```

## Archivos clave

| Archivo | Qué hace |
|---|---|
| `src/jobpulse_v15/idiomas.py` | **NUEVO**: detector determinista del idioma del aviso (`es`/`en`/`mixed`/`undetermined`) + `CODIGO_IDIOMA`/`codigo_canonico_del_idioma` |
| `src/jobpulse_v15/matching.py` | **REGLA**: `requisitos_efectivos`, `cumple_idioma_del_aviso`, `codigo_idioma_del_aviso`, `_cargar_idioma_aviso`, `Requisito.implicito`, `IDIOMA_POR_POSTING`, `EVIDENCIA_IDIOMA_DEL_AVISO` |
| `src/jobpulse_v15/repository.py` | Detección en `save_job` · `list_posting_language_records` / `set_job_posting_language` · `_requisitos_con_regla_de_idioma` (comparación UI) |
| `src/jobpulse_v15/cli.py` | Comando `enrich posting-language` (`--platform`, `--limit`, `--apply`) |
| `tests/test_idiomas.py` | **NUEVO**: 7 tests del detector |
| `tests/test_matching.py` | `TestReglaIdiomaDelAviso` (8 casos) + `_insertar_job(posting_language=...)` |
| `tests/test_repository.py` | Test de la regla en la comparación de la UI |
| `docs/PASO5_EVIDENCIA_2026-11-01.md` | Evidencia de la corrida `20261101_084012` (GENERADO, no editar) |
| `docs/PASO5_REVISION_PENDIENTES.md` | Hoja de firma (30 `educacion_no_confirmada`, regenerable) |
| `AGENTS.md` | Estado de referencia actualizado (corrida `20261101_084012`, 486 tests, regla de idioma) |

## Datos de contexto

- **DB**: `data/jobpulse_v15.db`, esquema **16**, **553 jobs**, 129 sitios
  habilitados, `integrity_check` **ok**, 0 violaciones FK.
- **Corridas del Paso 5**: `20261031_214155` (`valida=0`, pre-regla) y
  **`20261101_084012` (`valida=1`, vigente)**.
- **`posting_language` (553)**: `es`/source **222** · `en`/detected **267** ·
  `es`/detected **41** · `mixed`/detected **23** · `undetermined` **0**.
  Sin idioma útil para la regla (mixed) → **23** avisos.
- **Requisitos vigentes**: **1066** (196 de idioma; **80 sin
  `codigo_canonico`** → siguen en la cola de taxonomía).
- **Perfil**: idioma = español (Nativo) + inglés (B2) → el idioma del aviso se
  cumple siempre en este corpus; la regla no produce descartes, sube
  cobertura.
- **Motivos de la corrida vigente**: 68 `titulo_universitario_requerido` + 21
  `titulo_universitario_en_curso_requerido` (descartada 89) · 30
  `educacion_no_confirmada` + 44 `educacion_no_cumple` + 20 `skill_faltante` +
  7 `licencia_no_comparable` + 5 `experiencia_no_verificable`
  (revisar_a_mano 106) · 140 `sin_requisitos_mapeados` · 35
  `cobertura_insuficiente` + 3 `educacion_no_cumple` + 1 `skill_faltante`
  (datos_insuficientes 39).
- **Scripts de medición** (fuera del repo, en
  `C:\Users\giova\AppData\Local\Temp\opencode`): `comparar_corridas.py`
  (diferencia de estados/`total_req` entre dos corridas),
  `validar_idioma.py` (matriz declarado→detectado contra la verdad de campo),
  `casos_idioma.py` / `casos_mixed.py` (muestras de los casos dudosos),
  `diag_idiomas.py` (conceptos y requisitos de idioma), `stats_idioma.py`.
- **Gotchas nuevas**:
  - **`jobs.posting_language` es NOT NULL**: en tests hay que pasar un valor
    (`undetermined` si no se quiere idioma). Un `INSERT` sin él revienta con
    `IntegrityError` y arrastra 29 tests.
  - **`concepto` no tiene columna `nombre`**: es `codigo_canonico` +
    `variante` (+ `tipo`, `nivel_orden`, `activa`).
  - **La columna `posting_language` acepta `undetermined` en el CHECK**: el
    detector nunca escribe ese valor (solo `es`/`en`/`mixed`), pero existe
    para las fuentes que no lo declaran.
  - **`mixed` sí se guarda** en `posting_language` (es información real: el
    aviso mezcla idiomas); simplemente **no** genera requisito.
  - El dry-run de `enrich posting-language` devuelve **exit 1** (como los
    otros `enrich`): el informe se imprime igual — no confundirlo con un
    fallo.
  - Orden de los pasos al medir el efecto de una regla: backfill → corrida
    nueva (`run_paso5.py`) → evidencia **de esa corrida**. Regenerar la
    evidencia antes de la corrida deja el doc apuntando a la anterior.
- v1.x congelado en `D:\Proyectos\jobpulse_cr` — SOLO lectura.
- **IA local APAGADA** (puerto 8081 libre). Brave abierto **sin CDP 9222**
  (instancia diaria del usuario; la app no lo abrió, no se cerró). Para el
  barrido con navegador, la UI necesita **cerrarlo del todo** para poder
  abrir el puerto.
- `main` va **sin pushear** (no pushear sin confirmación del usuario).

## Pendiente inmediato

1. **Corrida por la UI** (lo pidió el usuario): tras el cierre, hacer el
   barrido desde la UI y **comprobar** que el filtro “Idioma anuncio”
   (es/en/mixed/undetermined) y los estados del Paso 5 salen como en la
   corrida `20261101_084012`. Ojo: si el Brave diario está abierto sin CDP, la
   UI no puede abrir 9222 → cerrarlo del todo primero.
2. **Las 30 `revisar_a_mano / educacion_no_confirmada` siguen ABIERTAS**: las
   firma una **segunda persona** en `docs/PASO5_REVISION_PENDIENTES.md`. NO
   actualizar estados hasta esa firma.
3. **Capa B — taxonomía educativa**: migración **`017`** (master/MBA/
   associate/técnico superior) + crecer `concepto` para los **80 requisitos
   sin `codigo_canonico`** (incluidos idiomas con `value_code` fuera de
   catálogo, si aparecen): hoy esas vacantes se evalúan con menos requisitos.
4. **Extractor de salario**: no existe (0 % de llenado; en el corpus nuevo
   solo **1** aviso publica un rango real).
5. **Ubicación**: 129 `city` “por diseño” (solo provincia+ciudad), 40
   etiquetas de sucursal de Harvie (la sucursal va en el título), 14
   “Lagunilla, Costa Rica”.
6. **`work_mode`**: 286 huecos = falta real (ningún aviso declara modalidad).
7. **UI**: correr el **Paso 5** desde la UI y mostrar `estado`/`motivo` de
   `job_match` (hoy la UI compara con otra función) — `docs/FLUJO_CLI_VS_UI.md`
   §4. **Nota 01-11**: la comparación de la UI ya aplica la regla de idioma,
   pero sigue **sin persistir** `job_match`.
8. **O5.3**: re-barrido de las **22 descripciones basura** (15 Indeed por
   login-wall). **Paso 7** (`job_match_decision`) y **O8.2** ciclo de vida;
   O2.1/O2.2 · O4 (redefinir) · O6.4 · O9.
9. **No tocar los umbrales** (cobertura 0.60 / puntaje 0.80) sin acuerdo
   explícito. **No pushear sin confirmación del usuario.**
10. **ANE**: sigue sin sesión iniciada → el barrido de ANE se omite limpio
    (no es error). Para cubrirlo: `login_ane.py` (o botón “Re-login ANE”) y
    re-barrido.
