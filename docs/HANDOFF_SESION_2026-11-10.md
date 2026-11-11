# Handoff — Sesión 2026-11-10

**TL;DR**: se implementó y aplicó la **Ola 6 · R1** (el escalón "estudiante
avanzado" de la escalera educativa) y, a partir de las reglas que el usuario
enunció, se ajustó el motor en tres puntos: (a) el **80 % de los créditos pasó
de supuesto a UMBRAL EXIGIDO**; (b) el **nivel efectivo de un programa en
curso** ya no se deduce de una resta (`nominal − 1`) sino de lo que dice la
**tabla de EE. UU.** ("completion of each level is a prerequisite for access to
the next"): bachelor en curso → escalón 3 (solo con el 80 %+), associate en
curso → escalón 1 (no confiere el associate), master en curso → escalón 4 (el
bachelor es prerrequisito); (c) **"estudios avanzados" NO es postgrado**:
posgrado es el nivel 5 (título de posgrado) y "advanced university studies" es
la única vía que se trata como posgrado sin título (presupone el
universitario previo); "coursework/studies toward a university degree" es
nivel 3. La escalera del motor quedó en **cinco** escalones (1 secundaria <
2 ciclo corto < 3 estudiante avanzado < 4 universitario < 5 posgrado) con la
**migración de datos 028** (esquema **28**). La regla del 80 % se exige **en
las dos direcciones**: el aviso que pide "X % completeness" declara el escalón
3 solo si X ≥ 80 (si pide menos, escalón 2) y un hecho `pursuing` **solo**
alcanza el escalón 3 si documenta el avance (si no, no se da por hecho → la
dimensión queda *no verificable*). **Medición obligatoria en copia: 0
cambios** en Paso 5 y en viabilidad (735 avisos) en las tres mediciones — el
perfil no tiene ningún hecho `pursuing`, así que las reglas nuevas no tenían
sobre qué actuar. La **BD real** quedó migrada a 28, con **cuatro corridas nuevas** del Paso 5
(`20261110_204736`, `20261110_210220`, `20261110_222024` y `20261111_074200`),
evidencia regenerada (**TODO CUADRA: 140 verificaciones literales, 29/29
firmas con cita y efecto**) y `db check` ok (esquema 28, `integrity_check` ok,
**0 violaciones FK**). Suite completa: **1251 passed + 2650 subtests**.

**Abbott quedó CERRADO el 2026-11-11** (`workday-Production-Supervisor-I_31163511`):
la regla ya estaba decidida y el motor ya la aplicó (el requisito del 80 %
quedó `faltante`), así que lo que faltaba era el **veredicto de la segunda
persona**, no un dato: se re-firmó como `bloqueo_real` y la vacante pasó a
`descartada`. `educacion_no_confirmada` = **0 casos abiertos**. La firma está
anclada al sha256 del texto: si el perfil registra la licenciatura en curso con
su avance, el caso se reabre solo. **Regla operativa: no se le pide el dato
caso por caso** — el motor + la tabla derivan el veredicto.
---

## 0. Tabla de objetivos (estado al cierre del 2026-11-10)

| Objetivo | Qué es | Estado al cierre |
|---|---|---|
| **O1** Enriquecimiento IA | Pase IA (Gemma local) llenando huecos | ✅ COMPLETO (27-10) |
| **O2** Afinar la búsqueda | Filtros/req. obligatorios; la precisión viene de la data extraída | 🟡 O2.2 cerrado; la semántica queda como **ranking** (por defecto en viabilidad, 0 cambios de banda) |
| **O3** Fetchers ATS huérfanos | Validar los 7 fetchers + resolver la salud de los sitios | ✅ COMPLETO (04-11) |
| **O4** Calibración gate-vs-IA | Pearson/Spearman/MAE + umbral | ⏳ **superseded**: el `gate` ya no existe (el motor es `matching.py`) → proponer cerrarlo |
| **O5** Higiene de datos | Auditoría, re-barrido de los login-wall, identidad por huella | 🟢 solo queda **O5.3** |
| **O6** Perfil del candidato | Editor, capa IA de CVs, matching (niveles/CEFR), dedupe semántico | 🟢 O6.1/O6.2/O6.3 cerrados · **O6.4** (slugs ES/EN) pendiente de decisión · **O6.5**: registrar el hecho educativo "en curso" con 80 %+ de créditos → **AHORA CON POSIBILIDAD REAL**: el motor ya exige el dato (§4.1 de `docs/REGLAS_NEGOCIO_EDUCACION.md`) |
| **O7** Operación UI-first | La app arranca/detiene lo que necesita | ✅ COMPLETO (27-10) |
| **O8** Ciclo de vida de la vacante | Áreas (O8.1) + recurrentes/aplicadas ocultas (O8.2) | 🟡 O8.1 cerrado · **O8.2 pendiente** (tombstones/`dup_of` de v1.x, no portados) |
| **O9** Optimización de UI | Ajustes de interfaz pospuestos | ⏳ placeholder |
| **O10** Filtros de búsqueda | `elegir_filtro_compatibilidad`, filtro por área, columna "Req." | 🟡 los tres implementados · falta refinar `solo_vigentes` |
| **O11** IA externa / motor intercambiable | Cualquier motor OpenAI-compatible | ✅ COMPLETO (05-11) |
| **O12** Paridad CLI/UI | Una sola implementación del pipeline | ✅ COMPLETO (olas 1 y 2; **05-11**) |
| **O13** Cobertura de fuentes | Que el barrido traiga los avisos que existen | ✅ COMPLETO (ola 3; **06-11**) |
| **O14** Control del coste de la IA | Límites opt-in y ajustables | ✅ COMPLETO (05-11) |
| **Backlog de la sesión (5 puntos)** | 1 ciclos IA · 2 taxonomía · 3 firma · 4 tokens · 5 UI clásica | ✅ **CERRADO** (turnos 2-5) |
| **Ola 6 · R1** | Escalón "estudiante avanzado" en el motor | ✅ **HECHO Y APLICADO** (migración 028, esquema 28; 2 corridas nuevas; 0 cambios de estado) |
| **Ola 6 · 6.2.1** | El 80 % del escalón "estudiante avanzado" | ✅ **HECHO Y APLICADO** (umbral exigido en aviso y perfil; 0 cambios en el corpus) |
| **Ola 6 · 6.1 / 6.3** | RAG consultivo + carta; embeddings *gated* | ⏸ **DIFERIDAS** a decisión del usuario (documentadas en `docs/PLAN_MEJORAS.md` §6, sin código) |

---

## 1. Lo hecho

### 1.1 Ola 6 · R1 — el escalón "estudiante avanzado" (migración 028)

El motor tenía **cuatro** escalones (1 secundaria < 2 ciclo corto < 3
universitario < 4 posgrado) y un hecho `pursuing` contaba como universitario
completo, lo que contradecía R2 ("el estudiante avanzado no es un titulado").

Implementado:

- **Migración de datos** `src/jobpulse_v15/migrations/028_estudiante_avanzado.sql`
  (patrón de la 017): inserta `estudiante_avanzado` = 3 en `nivel_escala` y
  corre `concepto.nivel_orden` universitario 3→4 y posgrado 4→5. Esquema
  **28**.
- `matching.py`: escalera de 5 niveles, `NIVEL_ESTUDIANTE_AVANZADO = 3`,
  `nivel_efectivo_fact` (el `pursuing` baja un escalón), el aviso con "X %
  de completitud" declara el escalón 3, y las vías de coursework quedan
  disponibles para el estudiante en curso.
- Tests: `tests/test_migraciones.py::TestMigracion028` (5) + tests nuevos en
  `tests/test_matching.py`; versiones hardcodeadas 27→28 en
  `tests/test_migraciones.py` y `tests/test_pipeline_metricas.py`.

**Medición obligatoria en copia** (`medicion_r1.db`, 735 avisos, código
anterior vs 028):

| Dimensión | Cambios |
|---|---|
| Paso 5: estado, motivo, puntaje, cobertura | **0** |
| Paso 5: conteos internos | **1** aviso (Abbott): `faltantes` 8→9, `nc` 2→1 |
| Viabilidad: banda | **1** aviso (Abbott): `no_prioritario` → `revisar` (mismo ajuste 27,5) — el **tope duro** "≥1 `required` faltante ⇒ banda máxima `revisar`" |
| Vetos nuevos | **0** |

### 1.2 El 80 % del escalón "estudiante avanzado" → **UMBRAL EXIGIDO**

Regla enunciada por el usuario: *"si el puesto pide estudiante avanzado se
da por hecho que debe tener la mayor parte de la carrera finalizada, que
serían por lo menos un 80 % de los créditos"* (coherente con la tabla de
EE. UU. ya discutida). Implementado como **exigido en las dos direcciones**:

| Lado | Regla | Implementación |
|---|---|---|
| **El aviso** | "X % completeness of a bachelor's degree program": X ≥ 80 → escalón 3; X < 80 → escalón 2 | `porcentaje_estudios_parciales` + `nivel_efectivo_requisito` |
| **El perfil** | Un hecho `pursuing` de nivel universitario **solo** alcanza el escalón 3 si documenta el 80 %+; sin el dato → `None` (no verificable, nunca bloquea) | `porcentaje_avance_fact` + `nivel_efectivo_fact` |

- El avance se lee del texto libre del hecho (`qualifier`, `notes`,
  `value_text`) o de `numeric_value` + `unit` de porcentaje.
- Un `pursuing` de **posgrado** confiere el título universitario (4): el
  bachelor es el requisito de entrada del programa, no depende del avance.
- `_cargar_facts` ahora trae `value_text`, `numeric_value`, `unit` y `notes`
  (antes solo `qualifier` y `education_status`).
- **UI v2**: pista bajo el campo "Nivel / calificador" de Educación
  ("80 % de créditos completados"); la UI clásica **no se tocó** (regla del
  repo: solo con permiso explícito).
- Tests: 6 nuevos en `tests/test_matching.py` (sin avance → no escalón 3;
  50 % → no escalón 3; 80 % en `numeric_value` → escalón 3; posgrado en curso
  → nivel 4; aviso al 50 % → escalón 2; lectura del porcentaje) + 1 más en
  §1.3 (associate en curso → escalón 1).

**Medición en copia (735 avisos)**: **0 cambios** en Paso 5 y **0** en
viabilidad. Es lo esperado: el perfil **no tiene** hechos `pursuing` (sus 2
hechos educativos son `completed`) y el único aviso con avance parcial
(Abbott) ya pedía 80 %.

### 1.3 El nivel efectivo de un programa EN CURSO, corregido con la tabla de EE. UU.

El motor calculaba el nivel efectivo de un hecho `pursuing` como
`nominal − 1` (bachelor en curso → associate). Esa resta **suponía** una
equivalencia que la fuente no dice. La tabla de EE. UU. (*"Completion of each
level or stage is a prerequisite for access to the next"*) dice que cada etapa
**completada** es prerrequisito de la siguiente, no que el avance parcial de
una etapa valga como esa etapa.

Corregido (`matching.nivel_efectivo_fact`):

| Programa en curso | Escalón efectivo | Por qué |
|---|---|---|
| associate (ciclo corto) | **1** secundaria | no confiere el associate |
| bachelor (universitario) | **3** estudiante avanzado (**solo con 80 %+**) | ya tiene el associate (prerrequisito) y le falta el título |
| master (posgrado) | **4** universitario | el bachelor es prerrequisito y está terminado |

**Medición en copia (735 avisos)**: **0 cambios** en Paso 5 y en viabilidad
(el perfil no tiene hechos `pursuing`). Documentado en
`docs/REGLAS_NEGOCIO_EDUCACION.md` §1.1 y `docs/PLAN_MEJORAS.md` §6.2.2.

### 1.4 "Estudios avanzados" NO es postgrado (aclarado por el usuario)

Quedó explícito y documentado:

| Lo que dice el aviso | Nivel del motor |
|---|---|
| `master's degree`, `MBA`, `doctorate`, `PhD`, `postgraduate degree` | **5 · posgrado** |
| `Bachelor's degree` | **4 · universitario** |
| `80 % completeness of a bachelor's degree program` | **3 · estudiante avanzado** |
| `or coursework / studies toward a university degree` | **3 · estudiante avanzado** (vía) |
| `or advanced university studies` | **5 · posgrado** (vía) — **excepción**: presupone el título universitario previo, es posgrado *sin el título* |

### 1.5 Aplicación en la BD real (con backup)

| paso | resultado |
|---|---|
| backup previo | `data/backups/pre-028_2026-11-10.db`, `pre-umbral-80_2026-11-10.db`, `pre-tabla-eeuu_2026-11-10.db` |
| migración | `[esquema] Se aplicaron las migraciones 28-28` → esquema **28** |
| `run_paso5.py` (tras la 028) | corrida **`20261110_204736`** — 735 avisos, distribución idéntica a `20261108_214123` (0 cambios visibles, 1 cambio interno en Abbott) |
| `run_paso5.py` (tras el umbral del 80 %) | corrida **`20261110_210220`** — 735 avisos, **0 cambios** frente a la anterior |
| `run_paso5.py` (tras la corrección de la tabla) | corrida **`20261110_222024`** — 735 avisos, **0 cambios** frente a la anterior |
| `decision sign` (re-firma de Abbott) | backup `data/backups/pre_firma_abbott_2026-11-11.db` → Abbott `dudoso` → **`bloqueo_real`** (2026-11-11) |
| `run_paso5.py` (tras la firma) | corrida **`20261111_074200`** — 735 avisos · `descartada` 77→78 · `educacion_no_confirmada` 1→**0** |
| `generar_evidencia_paso5.py` | `docs/PASO5_EVIDENCIA_2026-11-11.md` (1698 líneas) · descartada 101 · no_confirmada **0** |
| `verificar_evidencia.py` | **TODO CUADRA: 140 verificaciones con frase LITERAL** · 29/29 firmas con cita y efecto · exit 0 |
| `generar_revision_pendientes.py` | `docs/PASO5_REVISION_PENDIENTES.md` — **0 casos abiertos**, 29 firmados |
| `db check` | esquema **28** · `integrity_check` **ok** · **0 violaciones FK** · exit 0 |

### 1.6 Suite de tests

- Suite completa tras la 028: **1244 passed + 2650 subtests** (1137,35 s).
- Suite completa tras el umbral del 80 %: **1250 passed + 2650 subtests**
  (755,92 s).
- Suite completa final (con la corrección de la tabla de EE. UU.): **1251
  passed + 2650 subtests** (1636,67 s).
- Suite completa final (tras la re-firma de Abbott y el guard de citas):
  **1255 passed + 2650 subtests** (571,38 s).
- Baseline actualizado en `AGENTS.md`.

---

## 2. Decisiones

1. **Escalón nuevo por migración de DATOS** (028), no por fractional level:
   el esquema es `nivel_escala`/`concepto.nivel_orden` y_requires el patrón de
   la 017 (nunca `UPDATE` a mano).
2. **El 80 % se EXIGE, no se supone.** Sin avance documentado, un `pursuing`
   no alcanza el escalón 3 y la dimensión queda **no verificable** (nunca se
   descarta por falta de información). Es la traducción literal de "no se da
   por hecho".
3. **Un aviso que pide menos del 80 %** queda en el escalón 2 (el motor no
   modela el avance parcial intermedio: el corpus real solo tiene el 80 %).
4. **"Estudios avanzados" ≠ posgrado.** Solo "advanced **university**
   studies" es posgrado sin título, porque presupone el universitario previo.
5. **La UI clásica no se tocó** (regla del repo): la ayuda para registrar el
   avance va en la **UI v2** y en la documentación.
6. **No se registró ningún hecho `pursuing` en el perfil**: es un dato del
   usuario, no del código. **Abbott se cerró el 2026-11-11** con la firma
   `bloqueo_real` (la regla ya estaba decidida y el motor ya la aplicó: el
   requisito del 80 % quedó `faltante`).
7. **No se le pregunta el dato caso por caso.** El motor + la tabla derivan el
   veredicto; lo único que la segunda persona aporta es la firma. La firma
   queda anclada al texto: si el perfil registra la licenciatura en curso con su
   avance, el caso se reabre solo.

### 2.1 El fallo de `verificar_evidencia.py` (y su corrección)

La primera re-firma de Abbott **no verificaba**: `verificar_evidencia.py`
falló con *«la cita firmada NO es literal del texto de la BD»*. La causa no
era el texto del aviso sino la **convención de citas** de la hoja:

- lo que va entre comillas angulares `«...»` en el `criterio` significa
  **cita literal del aviso** (lo comprueba `verificar_evidencia.py`);
- el criterio nombaba el escalón 3 como `«estudiante avanzado»` → el
  verificador, correctamente, dijo que eso no está en el aviso.

**Corrección**: el nombre del escalón va ahora entre comillas simples
(`'estudiante avanzado'`) y la única cita `«...»` es la frase real del aviso
(«80% completeness of a bachelor’s degree program from a four-year college or
university»).

Además, para que el fallo no vuelva a aparecer **tres etapas después**, la
firma ahora lo comprueba **al firmar**: `decisiones.validar_citas` +
`aplicar_firma` rechazan la hoja si una cita no es literal del aviso
(`decision sign` lo avisa y sale con error; `--dry-run` lo lista).

---

## 3. Estado de la BD real

- Esquema **28** · 736 avisos (735 con análisis) · 2956 requisitos (**0** sin
  código canónico) · 775 conceptos (336 códigos) · cola de taxonomía
  **1150** · **29** decisiones firmadas.
- Corrida vigente del Paso 5: **`20261111_074200`** (735 filas `valida=1`).
- `db check`: **ok** (integrity ok, 0 FK).
- Perfil educativo: 2 hechos, ambos `completed` (secundaria + técnico). **No
  hay** ningún `pursuing` → el escalón 3 no lo alcanza nadie todavía.
- **0 casos abiertos** de `educacion_no_confirmada` (29 firmas vigentes).

---

## 4. Pendiente inmediato (priorizado)

1. **Ola 6 · resto** (6.1 RAG consultivo + carta de presentación, 6.3
   embeddings *gated*): sigue **diferido** a decisión del usuario
   (`docs/PLAN_MEJORAS.md` §6).
2. **Cola de taxonomía 1150** → siguiente tanda de curación. **Ojo: la
   migración ya no puede ser `028`** (la usa R1) → sería `029`.
   Priorizar variantes con ≥2 avisos reales (`demanda_corpus`, no `veces`).
3. **Medir el efecto de los puntos 1 y 4 en una corrida real** (no solo en
   copia): el siguiente pipeline completo debe mostrar menos llamadas por
   aviso y el `uso` guardado en `pipeline_etapa.detalle_json`.
4. **`linkedin-4476184789`** sin descripción: re-scrape del aviso o dejarlo
   fuera (no es un bug del extractor).
5. **`espanol: nativo` es inferencia**, no texto literal (365 avisos): el
   modelo infiere el idioma del aviso. Inofensivo para el matching (el perfil
   lo cubre), pero a tener en cuenta al auditar.
6. **Decisiones de usuario pendientes**: **O4** (cerrar el objetivo
   *superseded*), **O6.4** (slugs ES/EN del perfil).

---

## 5. Archivos clave

| Archivo | Qué cambió |
|---|---|
| `src/jobpulse_v15/matching.py` | Escalera de 5 niveles, `nivel_efectivo_fact`, `porcentaje_avance_fact`, `porcentaje_estudios_parciales`, `nivel_efectivo_requisito`, `_cargar_facts` trae más columnas del perfil |
| `src/jobpulse_v15/migrations/028_estudiante_avanzado.sql` | **NUEVO**: migración de datos del escalón 3 |
| `src/jobpulse_v15/decisiones.py` | `citas_del_criterio`, `validar_citas`, `texto_aviso_en_base`; `aplicar_firma` **rechaza** una firma cuya cita `«...»` no es literal del aviso |
| `src/jobpulse_v15/cli.py` | `decision sign` reporta `citas_no_literal` (en `--dry-run` y al firmar) y sale con error |
| `src/jobpulse_v15/ui_v2/tabs/perfil.py` | Pista del avance de créditos en el campo "Nivel / calificador" (UI v2) |
| `tests/test_matching.py` | Tests de la escalera, del escalón 3, del umbral del 80 % y del aviso parcial |
| `tests/test_decisiones.py` | `TestCitasLiteralesDeLaFirma`: la firma rechaza citas no literales |
| `tests/test_migraciones.py` | `TestMigracion028` + versiones 27→28 |
| `tests/test_pipeline_metricas.py` | Versión del esquema 28 |
| `docs/REGLAS_NEGOCIO_EDUCACION.md` | **§1.1** (qué dice y qué no dice la tabla de EE. UU.), §4 (escalón 3), **§4.1 (el 80 % exigido)**, §5 (Abbott cerrado), §5.2 (la convención de citas), mediciones |
| `docs/PLAN_MEJORAS.md` | §6.2 HECHO + **§6.2.1** (el 80 %) + **§6.2.2** (nivel efectivo según la tabla) |
| `docs/PASO5_EVIDENCIA_2026-11-11.md` | **GENERADO** (no editar) |
| `docs/PASO5_FIRMA_EDUCACION.json` | Hoja firmada (29 decisiones; Abbott en `bloqueo_real` del 2026-11-11) + la convención de citas |
| `docs/PASO5_REVISION_PENDIENTES.md` | Hoja de firma regenerada (**0 casos abiertos**) |
| `AGENTS.md` | Escalera, esquema 28, baseline de tests, regla del 80 %, convención de citas, "no pedir el dato caso por caso" |

---

## 6. Contexto

- El **80 %** viene de la tabla de EE. UU. que el usuario entregó (U.S. Dept.
  of State / InfoUSA, *Structure of U.S. Education*): "associate" = ciclo
  corto, "bachelor" = universitario, y el avance parcial se expresa como
  "X % of completeness of a bachelor's degree program".
- La tabla tiene **4 etapas de título** (associate < bachelor's < master's <
  doctorate) con *"completion of each level or stage is a prerequisite for
  access to the next"*: lo que se **completa** habilita la etapa siguiente.
  De ahí se deriva el nivel efectivo de un programa en curso (§1.1 del doc de
  reglas): el bachelor en curso **ya tiene** el associate (por eso el escalón
  3 está por encima del 2), el associate en curso **no** tiene el associate
  (escalón 1) y el master en curso **tiene** el bachelor (escalón 4).
- El **CONESUP** queda como criterio de curación del perfil (qué título
  cuenta como académico superior), **sin fuente documental aportada**.
- La escalera del CONESUP y la de EE. UU. **coinciden en los niveles**;
  la diferencia es el escalón intermedio que se agregó en esta sesión.
- La regla de negocio completa (con todas sus fuentes) está en
  `docs/REGLAS_NEGOCIO_EDUCACION.md`; las firmas de la segunda persona en
  `docs/PASO5_FIRMA_EDUCACION.json` (29 decisiones, ancladas al sha256 del
  texto leído: si el aviso se re-raspa y cambia, la firma deja de aplicar).

---

## 7. Cómo retomar

```powershell
$py = ".\.venv\Scripts\python.exe"

# 1. Estado de la BD
& $py -X utf8 -m jobpulse_v15 db check
& $py -X utf8 tools\estado_bd.py

# 2. Ver el caso abierto de Abbott y las firmas
& $py -X utf8 -m jobpulse_v15 decision list
Get-Content docs\PASO5_REVISION_PENDIENTES.md

# 3. Si el usuario registra el hecho "pursuing" con 80 %+: nueva corrida
& $py -X utf8 run_paso5.py
& $py -X utf8 generar_evidencia_paso5.py
& $py -X utf8 verificar_evidencia.py
& $py -X utf8 generar_revision_pendientes.py
& $py -X utf8 -m jobpulse_v15 db check

# 4. Tests (pytest vive en el python del SISTEMA, no en el venv)
python -m pytest tests/test_matching.py -q
python -m pytest tests/ -q          # ~19 min

# 5. UI v2 (humo sin ventana)
& $py -X utf8 -c "from jobpulse_v15.ui_v2.app import crear_app; r,s=crear_app(); [r.update() for _ in range(20)]; t=s.pestana_activa(); t.refresh(); print(t.key); r.destroy()"
```

**Antes de cualquier operación destructiva**: backup
(`& $py -X utf8 -m jobpulse_v15 backup --output data\backups\X.db`).
