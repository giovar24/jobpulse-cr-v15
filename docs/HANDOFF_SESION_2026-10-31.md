# Handoff — Sesión 2026-10-31: catálogo territorial CR + tabla de lugares, `work_mode` determinista, **reset de BD + scrape desde cero (553 vacantes)** y **clasificación de cada hueco (lógica vs. dato inexistente)**; 3 reglas nuevas de ubicación

## TL;DR

Sesión en **siete bloques**:

1. **Mejoras pedidas (a) y (b)** con tests: `work_mode` **determinista**
   (patrones `#LI-*`, "hybrid work arrangement", …) y **normalizador de
   ubicación de Workday**.
2. **Limpieza de BD conservando lo necesario** (perfil, config de fuentes,
   taxonomías) y **arreglo de los bugs que aparecieron** al raspar en limpio:
   `run_full_flow.py` hacía `await`/`no-await` al revés, la UI pasaba `pages=`
   a tableros que no lo aceptan, `ElempleoFetcher.fetch` tenía doble envoltura
   de `asyncio.run`, `run_full_flow.run_analysis` llamaba a un método
   inexistente y la evidencia reventaba con avisos purgados.
3. **Corrida limpia end-to-end**: scrape (129 sitios) → análisis por reglas →
   enriquecimiento IA → Paso 5 → evidencia, sobre la BD limpia.
4. **Verificación**: transferencia a la BD por etapas, % de llenado por campo
   y **causa de cada hueco** (falta de información real vs. bug de lógica),
   más el documento `docs/FLUJO_CLI_VS_UI.md`.
5. **Catálogo territorial CR completo** (nuevo módulo `ubicaciones_cr` +
   2 semillas versionadas): jerarquía **país → provincia → cantón → distrito**,
   **tabla de lugares** (Ultra Park I/II, AFZ, Coyol Free Zone, Península
   Papagayo, Control Fronterizo Peñas Blancas), normalización **centralizada
   en `Repository.save_job`** (todos los adaptadores, no solo Workday) y
   comando `location normalize` con backfill **aplicado** a la BD real.
6. **Cierre del gap de `work_mode`**: patrones deterministas nuevos (los casos
   reales que la IA dejó pasar) + comando `enrich work-mode` (sin IA) con
   backfill **aplicado** (7 avisos) y **clasificación de cada hueco**:
   falta real vs. bug vs. por diseño.
7. **RESET de la BD + scrape desde cero + auditoría de huecos** (petición del
   usuario): `clean_run.py SI` (conserva perfil/config/taxonomías), **cachés IA
   vaciadas** para no falsear la medición, scrape de **129 sitios** (0 errores),
   análisis por reglas, **3 reglas nuevas de ubicación** (repetición =
   "ciudad, cantón, país"; provincia aunque venga pegada a otra palabra; un
   compuesto de lugares de provincias distintas **no** es una ciudad) con
   backfill aplicado, backfill determinista de `work_mode` (41 avisos) y el
   **informe campo por campo de por qué falta cada dato**.

**Estado de la BD**: **553 vacantes** (rescateadas de cero), esquema **16**,
`db check` → integrity **ok**, **0 violaciones FK**. Corrida vigente del Paso 5
**`20261031_214155`** (`valida=1`) y `GROUP BY estado` **cuadra** con 553:
calificada **177** · sin_requisitos **138** · revisar_a_mano **106** ·
descartada **89** · datos_insuficientes **43**. **30 `educacion_no_confirmada`
ABIERTAS** (hoja de firma regenerada; las firma una segunda persona).

**Llenado de campos (553, SIN pase de IA)**: `date_published` 100 % ·
`description≥200` 96.0 % · `region` **77.8 %** · `employment_type` 50.8 % ·
`work_mode` **48.3 %** · `city` **47.9 %** · `requirements_raw` 3.1 % ·
`salary_min` **0 %** · `skills`/`languages` **0 %** (los llena solo la IA).
Comparado con el bloque 7 (antes de los backfills): `city` 43.0 → **47.9 %**,
`region` 75.6 → **77.8 %**, `work_mode` 40.9 → **48.3 %**.

**Evidencia**: `docs/PASO5_EVIDENCIA_2026-10-31.md` (1776 líneas) y
`verificar_evidencia.py` → **TODO CUADRA (130 verificaciones con frase
literal)**.

Suite completa: **471 tests verdes** (+179 subtests). Todo **commiteado en
`main`**, **sin pushear**. La **IA local quedó APAGADA** y **Brave quedó
CERRADO** (la corrida de navegador abrió y cerró el que abrió).

## Lo que se hizo

### Bloque 1 — Mejoras (a) y (b)

- **(a) `work_mode` determinista** (`ia_enrichment.work_mode_por_patrones`):
  se ejecuta **antes** del modelo y sobre el texto **completo**, no sobre el
  recorte de 2000 chars que ve la IA (las etiquetas `#LI-Onsite` /
  `#LI-Hybrid` / `#RPOCRA` van al final del aviso y el modelo no llegaba a
  verlas). Solo acepta marcas inequívocas: **rechaza** "on-site fitness
  center", "hybrid identity (Azure AD)", "hybrid project environments".
  Medición de la sesión previa: 22 llenados, 0 llamadas al modelo, 22/22
  correctos.
- **(b) `normalize_location` (Workday)**: acepta cualquier separador (`,` `-`
  `/` `_`), descarta el país y los términos de modalidad (evita
  `city="Remote"`) y mantiene la regla de **no adivinar**.

### Bloque 2 — Limpieza + bugs de wiring

- **`clean_run.py`**: borra lo derivado del scrape **incluido `job_match` y
  `job_area`** (colgaban de `jobs` con FK NO ACTION y quedaban huérfanos) y
  **verifica/sostiene lo conservado**: perfil (48 facts), 129 sitios, 14
  plataformas, 20 áreas, 51 reglas, 70 conceptos, 10 escalas.
- **`scrape_dispatch.construir_llamada`**: **fuente única** de la firma de cada
  fetcher (async/sync, `pages`, `port`, `dias`), usada por UI y CLI. Arregló
  dos bugs reales: el CLI no resolvía los fetchers `async` (cinde/procomer
  reventaban con "asyncio.run() cannot be called from a running event loop")
  y la UI pasaba `pages=` a greenhouse/ashby/lever/recruitee/successfactors/
  harvie (**TypeError**).
- **`analysis_flow.extract_job_analysis`**: implementación **única** del
  análisis por reglas (antes triplicada; la de `run_full_flow` llamaba a
  `IngestionService.analyze_job`, que **no existe** → fallaba en las 552).
- **`elempleo.py`**: `fetch` es `async def` pero terminaba en
  `asyncio.run(_run())` → `await _run()`; test **AST** que prohíbe
  `asyncio.run` dentro de un `async def` en **todos** los adaptadores.

### Bloque 3 — Corrida limpia

- **Backup** `data/backups/antes_limpieza_20261031_095734.db`.
- **Scrape API** (125 sitios): 529 encontradas / **498 nuevas** / **0
  errores**; browser: indeed-cr **15**, linkedin-cr **7**, elempleo-cr **1**,
  **ane-cr 0** ("sin sesión de detalle; barrido omitido" — no es error).
- **Total BD: 552** (workday 269 · harvie 189 · cinde 15 · workable 13 ·
  recruitee 13 · greenhouse 11 · ashby 11 · successfactors 7 · procomer 1 ·
  indeed 15 · linkedin 7 · elempleo 1).
- **Análisis**: 552/552, 0 fallos. **IA**: pase completo (167 lotes).
  **Paso 5**: corrida nueva. **Evidencia**: generada y verificada.
- **Brave**: cerrado y relanzado con CDP 9222 + `--user-data-dir=<root User
  Data>` + `--profile-directory=Default` (regla O7.1); pestañas restauradas.

### Bloque 4 — Verificación y jerarquía de ubicación

- **Transferencia a la BD** verificada por etapas: 552 jobs · 552
  `job_source_records` · 552 `source_job_memory` · 552 `job_area` · 552
  `job_analysis (is_current=1)` · 552 `job_match`; **0 sin registro, 0 sin
  memoria, 0 sin área, 0 sin análisis, 0 sin matching**. 1065 requisitos (985
  con `codigo_canonico`).
- **Causa de los huecos** (con verificación manual de los "con señal"):
  - **falta de información real**: `salary` 520/552 no publican (las "señales"
    eran falsos positivos: "$200 million", "$140M Series D"…); `work_mode`
    169/205 sin señal; `city`/`region` casi todos sin lugar en el texto.
  - **por diseño**: la ciudad ambigua no se guarda; "Lagunilla" (14) es
    ambigua entre Alajuela y Heredia.
  - **bugs corregidos**: provincia descartada por ambigüedad (ver abajo),
    ciudad-basura y la evidencia que reventaba.
  - **taxonomía incompleta**: 80 requisitos sin `codigo_canonico` (→ 138
    `sin_requisitos`) y tabla cantón→provincia de 6 entradas.
  - **descripción basura** (irrecuperable por IA): 22 (<200 chars; 15 Indeed
    login-wall) → O5.3.
- **Jerarquía de direcciones** (`normalize_location`): la dirección
  costarricense va de lo más específico a lo más general (**distrito →
  cantón → provincia → país**): `"San Antonio, Belen, Heredia, Costa Rica"` =
  distrito San Antonio, cantón Belen, provincia Heredia. Reglas nuevas:
  **la provincia nombrada es un dato CIERTO** (aunque su nombre también sea
  ciudad) → región; **la ciudad NO se adivina** si el único lugar es la
  provincia; se descartan planta/zona/sede (`Wet Plant`, `BSC`,
  `Local Office`, `-H`, `GCG`, `Alajuela Coyol`). Región de Workday en el
  fetcher: **62/269 → 206/269** sin inventar ninguna ciudad.
- **Corrección de ciudad-basura**: 9 filas con `city='GCG_Costa Rica_San
  Jose'` (firma del parser viejo) se corrigen con `replace_city=True` (el
  `COALESCE` de `save_job` las habría conservado **para siempre**).
- **`docs/FLUJO_CLI_VS_UI.md`**: qué comparte el CLI con la UI y qué no.

### Bloque 5 — Catálogo territorial CR + tabla de lugares

- **Nuevo módulo `src/jobpulse_v15/ubicaciones_cr.py`**: catálogo geográfico
  **único** (país → provincia → cantón → distrito) con la división territorial
  **completa** y la **tabla de lugares**; las dos semillas son versionadas y
  editables sin tocar código:
  - `seeds/division_territorial_cr.csv` — **490 distritos / 84 cantones / 7
    provincias** (copia del CSV del usuario).
  - `seeds/lugares_cr.csv` — `Lugar,Alias,Ciudad,Provincia,Pais`:
    Ultra Park I/II y AFZ → Lagunilla/Heredia · Coyol Free Zone →
    Coyol/Alajuela · Península Papagayo → Sardinal/Guanacaste · Control
    Fronterizo Peñas Blancas → Peñas Blancas/Guanacaste.
- **Reglas duras** (decididas con el usuario):
  - La jerarquía se busca **siempre de mayor a menor** (país → provincia →
    cantón → distrito).
  - La regla aplica **solo a Costa Rica**, **no** a los avisos remotos y **sí**
    a los híbridos.
  - La **provincia** nombrada es un dato **cierto** (aunque su nombre también
    sea ciudad); la **ciudad** solo se toma de un lugar concreto e
    inequívoco: **nunca se adivina**.
  - Nombres **homónimos** entre cantón/distrito en provincias distintas
    ("Belén", "Santo Domingo", "San José") se descartan, salvo que el texto
    nombre la provincia o el cantón/distrito que los desambigua
    ("San Antonio de Belén" → distrito San Antonio, cantón Belén → Heredia).
  - La **tabla de lugares** se consulta en la ubicación **y** en la
    descripción del aviso, y **tiene prioridad** sobre el homónimo de la
    división territorial ("Peñas Blancas" es distrito en Alajuela, pero el
    control fronterizo está en Guanacaste).
  - El fallback por texto **solo rellena lo que falta**, nunca contradice una
    provincia ya resuelta y **nunca se aplica en avisos remotos**.
- **`location_utils.normalize_cr_location` delegó en el catálogo compartido**:
  su tabla de cantones escrita a mano tenía erratas y **no tenía distritos**
  (producía basura —"Lagar", "Lagarte", "Cr"— y **regiones equivocadas**:
  "Tres Ríos" → San José cuando es Cartago, "Jacó" → San José cuando es
  Puntarenas).
- **Normalización centralizada en `Repository.save_job`**: ahora **todos** los
  adaptadores (no solo Workday) guardan `city`/`region` con el catálogo
  (la ingesta Workday pasa además la descripción para el fallback de lugares).
- **Nuevo comando CLI `location normalize`** (todas las plataformas,
  *dry-run* por defecto, `--apply`): **completa y corrige** lo que el catálogo
  reconoce como erróneo (el `COALESCE` de `save_job` conservaría para siempre
  la ciudad-basura del parser viejo). `location normalize-workday` se
  conserva (tests existentes).
- **Backfill APLICADO a la BD real**: `location normalize --apply` →
  **190 filas actualizadas** (25 ciudades rellenadas, 18 regiones rellenadas,
  137 ciudades corregidas, 84 regiones corregidas, 362 sin cambio). Segunda
  corrida → **0 cambios** (idempotente).
- **Correcciones auditables**: 9 `GCG_Costa Rica_San Jose` → San José ·
  `BSC` → NULL · `Alajuela Coyol` → Coyol · `CSI Escazu` → Escazú ·
  `Lagarte`/`Lagarte` → Santa Ana · `Toyota` → Uruca · `Lagarde` → Sardinal ·
  `Lagar La Uruca` → Uruca (región Alajuela → **San José**) · `Tres Ríos`
  (región San José → **Cartago**) · `Jacó` (región → **Puntarenas**) ·
  `Peñas Blancas` (región → **Guanacaste**).

### Bloque 6 — `work_mode`: cierre del gap y clasificación de los huecos

- **Patrones deterministas nuevos** (`ia_enrichment._PATRONES_WORK_MODE`),
  todos con casos reales de la BD:
  - `#LI-Híbrido` (etiqueta **con tilde**; Kimberly-Clark escribe en español)
    → `hybrid`. Antes solo se aceptaba `#LI-Hybrid`.
  - `Working Conditions: Remote / Work-from-home` → `remote`;
    `Working Conditions: Professional environment (Hybrid)` → `hybrid`.
  - `Hybrid Work : Candidates will be expected to work from the office at
    least 50% of the time` → `hybrid`.
  - `This is a remote role based out of Costa Rica` → `remote` (el **puesto**,
    no el servicio).
  - `Multiple office days with some remote flexibility` → `hybrid`
    (oficina + algo de remoto).
- **Falsos positivos que NO se tocaron** (con test de no-regresión):
  `onsite campaigns` (marketing) · `hybrid-friendly culture` ·
  `Video Remote Interpreter (VRI)` · `on-site or remote` (capacitación) ·
  `remote flexibility` como **beneficio** de un puesto 100 % remoto ·
  `trabajo remoto con colaboración presencial` y `Flex Work` (política
  general de la empresa, **no** una declaración del puesto) ·
  `Experience working with remote locations`.
- **Nuevo comando CLI `enrich work-mode`** (determinista, **sin IA**,
  *dry-run* por defecto, `--apply`): rellena solo los **huecos** de
  `work_mode` (`NULL`/`''`/`unknown`) y **nunca** sobreescribe un valor ya
  conocido ni uno editado a mano (`Repository.set_job_work_mode`).
- **Backfill APLICADO**: 205 huecos revisados → **7 detectadas** y guardadas
  (**3 remote**, **4 hybrid**); 198 sin marca literal (se quedan `unknown`).
- **Contraste con lo ya guardado**: la regla coincide con la modalidad
  guardada en **49/49** avisos con marca literal → **0 contradicciones**.
- **Clasificación de los 198 huecos que quedan**:
  - **falta de información real (169)**: el aviso no declara la modalidad.
  - **por diseño (15)**: el texto habla de la modalidad de la *empresa* o del
    *servicio*, no del puesto (boilerplate "Flex Work", "Video Remote
    Interpreter", "hybrid-friendly culture", "onsite campaigns").
  - **sin descripción utilizable (14)**: no hay texto del que deducirla.

### Bloque 7 — Reset de la BD, scrape desde cero y auditoría de huecos

**Petición**: borrar los datos scrapeados dejando lo necesario para que el
sistema funcione, hacer una corrida limpia y revisar si los datos faltantes son
**fallo de lógica** o **dato que no existe**.

- **Reset**: `clean_run.py SI` (12 tablas de vacantes borradas: `jobs`,
  `job_analysis`, `job_requirements`, `job_field_status`, `job_source_records`,
  `source_runs`, `source_job_memory`, `job_match`, `job_area`, …). Se
  conservaron **perfil (48 hechos), config de fuentes (129 sitios / 14
  plataformas), áreas (20), conceptos y escalas**. **Cachés IA vaciadas**
  (`data/usuario/ia_cache/`, `ia_cache_run2/`: 4 923 ficheros) porque la caché
  en disco falsea cualquier medición.
- **Scrape desde cero** (0 errores en los 129 sitios):
  - **125 tableros API** (Workday 51, Workable 46, Greenhouse 8, Ashby 7,
    SuccessFactors 4, Lever 3, Recruitee 3, CINDE, Harvie, Procomer) →
    **530 vacantes**.
  - **Browser** (`run_full_flow.py --only-scrape` abre Brave con CDP 9222 y lo
    cierra al terminar): **ANE 0** (sin sesión → el barrido se omite limpio),
    **Indeed 15**, **LinkedIn 7**, **Elempleo 1** → **23 vacantes**.
  - Total **553**; `jobs_new` = 553 (nada duplicado: la BD estaba vacía).
- **Análisis por reglas**: 553/553 (`partial` 509, `complete` 44) y **1 066
  requisitos** (80 sin `codigo_canonico` = 7.5 % → cola de taxonomía).
- **Tres reglas nuevas de ubicación** (`ubicaciones_cr`), todas nacidas de la
  BD nueva:
  1. **La repetición es el idioma "ciudad, cantón, país"**: "Heredia, Heredia,
     Costa Rica" (22 avisos) y "San José, San José, Costa Rica" → ciudad =
     Heredia/San José. Sin repetir ("Alajuela, Costa Rica") **sigue** sin
     adivinar: la política conservadora no cambia.
  2. **La provincia es cierta aunque venga pegada a otra palabra**: "HCLTech,
     Belen Heredia" (sin coma) → region Heredia (antes `None`).
  3. **Un compuesto de lugares de provincias distintas NO es una ciudad**:
     "Gravilias Tres Ríos" (Gravilias=San José + Tres Ríos=Cartago) y
     "Sucursal Toyota Zapote" dejan de guardarse como ciudad (basura) — y a
     igual nivel se prefiere el nombre que **no** es el de la provincia
     ("Lagar San Ramón de Alajuela" → San Ramón, región Alajuela).
  - Además: prefijos genéricos ("barrio", "sucursal", "local", "tienda",
    "bodega", "agencia") ya no se guardan como ciudad, y la **tabla de lugares**
    creció con **Santa Teresa (Puntarenas)** y **Los Yoses (San Pedro, San
    José)**.
- **Backfills aplicados**: `location normalize --apply` → **54 cambios**
  (35 ciudades rellenadas, **12 ciudades corregidas**, 12 regiones rellenadas);
  `enrich work-mode --apply` → **41 avisos** (19 hybrid, 13 remote, 9 onsite).
  **Idempotentes**: la segunda pasada da **0 cambios**.
- **Auditoría de huecos (por campo, con el corpus nuevo)**:

  | campo | llenos | huecos | causa de los huecos |
  |---|---|---|---|
  | `city` | 265 (47.9 %) | 288 | **129 por diseño** (la ubicación solo dice la provincia y su nombre es también el de la ciudad: "San Jose, Costa Rica", "Heredia, Costa Rica", "Alajuela, Costa Rica") · **93 no existe** (solo "Costa Rica", "multi-loc", "Remote", "GAM") · **40 etiqueta de sucursal** ("Lagar Alajuela", "Gravilias Tres Ríos") · **17 planta/sede** ("Costa Rica-Cartago-Wet Plant") |
  | `region` | 430 (77.8 %) | 123 | **93 no existe** (país/remoto/multi-loc: "Costa Rica", "GAM") · 16 con nombre de sucursal/empresa · 14 "Lagunilla, Costa Rica" (la tabla de lugares lo resuelve solo si el texto nombra Ultra Park/AFZ) |
  | `work_mode` | 267 (48.3 %) | 286 | **falta real**: el aviso no declara modalidad (286 revisados por la regla determinista, 0 marcas) |
  | `employment_type` | 281 (50.8 %) | 272 | **falta real**: solo 26 con señal (el resto no declara tipo de contrato) |
  | `salary_min` | 0 (0 %) | 553 | **falta real**: 12 "señales" y **11 son falsos positivos** ("$200 million in fees", "$140M Series D"); solo 1 aviso publica un rango real → **no hay extractor de salario** |
  | `languages` | 0 (0 %) | 553 | **IA**: 59 avisos tienen idioma + nivel en el texto ("inglés intermedio"); el campo lo llena solo el pase de IA |
  | `skills` | 0 (0 %) | 553 | **IA**: campo 100 % IA |
  | descripción | 531 (96 %) | 22 | **basura**: 15 Indeed (login-wall), 3 Harvie, 2 CINDE, 1 Workday, 1 Recruitee → irrecuperable por IA (re-barrido, O5.3) |

- **Causa de los 138 `sin_requisitos`**: **112 con descripción utilizable y
  NINGÚN requisito extraído** (Harvie 64, Workday 38, Ashby 5, Workable 3,
  CINDE 2) — revisado a mano: son avisos que **no cuantifican** requisitos
  ("gaining hands-on experience", sin "X años"); 18 con descripción basura;
  8 con requisito extraído pero **sin `codigo_canonico`** (taxonomía: "B3",
  primaria, etc.). Es decir: **no es un fallo del extractor**, es que el aviso
  no dice el requisito (o dice uno que la taxonomía no tiene).

## Decisiones de diseño (esta sesión)
1. **`work_mode` determinista ANTES del modelo y sobre el texto completo**: el
   recorte de la IA (2000 chars) deja fuera las etiquetas `#LI-*` del final;
   solo se aceptan marcas inequívocas.
2. **La provincia es cierta; la ciudad se adivina solo si es un lugar
   concreto.** La ambigüedad "Alajuela = provincia y ciudad" afecta a la
   ciudad, no a la provincia.
3. **Catálogo territorial COMPLETO y versionado** (490 distritos, 84 cantones,
   7 provincias) en `seeds/division_territorial_cr.csv`: un homónimo entre
   cantón/distrito en provincias distintas **se descarta** salvo que el texto
   nombre la provincia o el cantón/distrito que lo desambigua. **Lagunilla**
   (Alajuela y Heredia) sigue ambigua en la división territorial, pero la
   **tabla de lugares** la resuelve (Ultra Park I/II, AFZ → Lagunilla/Heredia).
4. **`scrape_dispatch` y `analysis_flow` son la única fuente** de la firma de
   los fetchers y del análisis por reglas: UI y CLI no vuelven a duplicar esa
   lógica (los tres bugs de wiring salieron de esa duplicación).
5. **`clean_run.py` conserva perfil, configuración y taxonomías**; borra lo
   derivado por vacante (incluidas `job_match` y `job_area`).
6. **La muestra histórica de la evidencia** (43 avisos de una corrida previa)
   se conserva, pero si un aviso ya no existe se marca **`purgado`** y se
   excluye del cómputo, en vez de romper el generador.
7. **Corregir una ciudad que no puede ser un lugar es explícito y auditable**
   (`replace_city` se ve en el dry-run); no se tocan otros campos con datos
   existentes.
8. **Los umbrales siguen congelados** (cobertura 0.60 / puntaje 0.80) y las
   reglas del Paso 5 no se tocaron.
9. **Un solo catálogo geográfico** (`ubicaciones_cr`) y **normalización
   centralizada** en `Repository.save_job`: ningún adaptador vuelve a tener su
   propia tabla de cantones (el normalizador legacy produjo regiones
   equivocadas).
10. **La tabla de lugares es el ÚLTIMO recurso** y **solo para los campos de
    ciudad** que las regex no pueden resolver; **prioriza** sobre el homónimo
    de la división territorial.
11. **La modalidad se deduce solo de una declaración del PUESTO**: el
    boilerplate de la empresa ("Flex Work", "modelo de trabajo flexible") y el
    lenguaje del servicio ("Video Remote Interpreter") **no** cuentan, aunque
    mezclen remoto y presencial.
12. **El backfill determinista de `work_mode` es idempotente y no pisa**: solo
    rellena huecos; el de ubicación **sí corrige** lo que el catálogo reconoce
    como erróneo (y el dry-run lo deja auditable).
13. **La repetición de un nombre de provincia ES el contexto** que
    desambigua el homónimo ("Heredia, Heredia, Costa Rica"): es el idioma
    "ciudad, cantón, país" y se resuelve; **una sola** mención sigue **sin**
    adivinar la ciudad (la política del punto 2 no cambia).
14. **La provincia es un dato cierto aunque el texto la pegue a otra
    palabra** ("Belen Heredia"): se buscan n-gramas de hasta tres palabras.
15. **Un compuesto de lugares de provincias distintas no es un lugar**
    ("Gravilias Tres Ríos"): no se guarda como ciudad y, si ya estaba guardada,
    se corrige. Ojo: "San José" **sí** es un lugar (la capital) aunque tenga
    distritos homónimos en otras provincias → la regla exige que el nombre
    **no** sea un lugar del catálogo para marcarlo como basura.
16. **El reset conserva perfil, configuración y taxonomías** y borra solo lo
    derivado por vacante: la **caché de IA en disco también se vacía** cuando
    la corrida sirve para medir (falsea los resultados).

## Estado de objetivos (tabla O1–O10)

| Objetivo | Estado |
|---|---|
| O1 enriquecimiento IA | ✅ completo (servidor local, veredicto IA) + **(a) `work_mode` determinista (31-10)** + **patrones nuevos + backfill `enrich work-mode` (31-10)** |
| O2 búsqueda data-first | 🟡 O2.1 locations Indeed + O2.2 filtro “Req.” |
| O3 fetchers ATS | 🟢 7/7 plataformas validadas; **scrape limpio de 129 sitios con 0 errores (31-10)**, repetido tras el reset (31-10) |
| O4 calibración gate-vs-IA | ⏳ redefinir (sin gate semántico no hay contra-qué) |
| O5 higiene de datos | 🟡 **O5.3 pendiente con 22 descripciones basura (15 Indeed login-wall)** · **(b) normalizador de ubicación (31-10)** · **catálogo territorial CR + tabla de lugares + normalización central (31-10)** · **corrección de ciudad-basura (31-10)** · **3 reglas nuevas de ubicación + backfill (31-10)** |
| O6 perfil del candidato | 🟡 O6.3 regla + mecánicas M1–M4 ✅; **30 `educacion_no_confirmada` ABIERTAS (firma de 2.ª persona)** · Paso 7 pendiente |
| O7 operación UI-first | ✅ completo (Brave auto-gestionado O7.2 verificado en la corrida limpia) |
| O8 ciclo de vida | 🟡 O8.1 ✅ (áreas) · O8.2 pendiente |
| O9 optimización UI | ⏳ placeholder |
| O10 mejorar filtros | 🟡 `elegir_filtro_compatibilidad` + filtro por área ✅ · **comparación CLI vs. UI documentada (31-10)** |

## Cómo retomar

```powershell
# Limpieza (requiere el argumento literal SI; conserva perfil/config/taxonomias)
.\.venv\Scripts\python.exe -X utf8 clean_run.py SI

# Scrape (API, sin browser) — el dispatcher decide la firma de cada fetcher
.\.venv\Scripts\python.exe -X utf8 run_full_flow.py --only-scrape <site_id...>
# Browser (requiere Brave con CDP 9222; lo abre y lo cierra solo si lo abrio)
.\.venv\Scripts\python.exe -X utf8 run_full_flow.py --only-scrape ane-cr indeed-cr linkedin-cr elempleo-cr

# Analisis por reglas (implementacion unica) + IA + Paso 5 + evidencia
.\.venv\Scripts\python.exe -X utf8 run_enriquecimiento.py
.\.venv\Scripts\python.exe -X utf8 run_paso5.py [--dry] [--evaluar-todo]
.\.venv\Scripts\python.exe -X utf8 generar_evidencia_paso5.py
.\.venv\Scripts\python.exe -X utf8 verificar_evidencia.py      # exit 0 = TODO CUADRA
.\.venv\Scripts\python.exe -X utf8 generar_revision_pendientes.py

# Ubicacion: ver que completaria/corrigiria y aplicarlo (todas las plataformas)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 location normalize
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 location normalize --apply

# Modalidad: backfill determinista, SIN IA (solo rellena huecos)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 enrich work-mode
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 enrich work-mode --apply

# Tests (python del SISTEMA; el venv NO tiene pytest)
python -m pytest tests/ -q

# UI
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15.ui
```

## Archivos clave

| Archivo | Qué hace |
|---|---|
| `src/jobpulse_v15/ubicaciones_cr.py` | **Catálogo geográfico único**: división territorial (país→provincia→cantón→distrito), tabla de lugares, `resolver_direccion`, `resolver_lugar`, `ciudad_es_basura`, `nombre_canonico` |
| `src/jobpulse_v15/seeds/division_territorial_cr.csv` | Semilla: 490 distritos / 84 cantones / 7 provincias |
| `src/jobpulse_v15/seeds/lugares_cr.csv` | Semilla: tabla de lugares (Ultra Park, AFZ, Coyol Free Zone, Península Papagayo, Peñas Blancas, **Santa Teresa**, **Los Yoses**) |
| `src/jobpulse_v15/location_utils.py` | Fachada `normalize_cr_location` → catálogo compartido (+ fecha/modalidad/contrato) |
| `src/jobpulse_v15/repository.py` | Normalización **central** en `save_job` · `list_location_records`/`set_job_location` · `list_work_mode_records`/`set_job_work_mode` |
| `src/jobpulse_v15/cli.py` | `location normalize` (todas las plataformas) y `enrich work-mode` (determinista, sin IA) |
| `src/jobpulse_v15/workday.py` | `normalize_location` (delega en el catálogo) + helpers reexportados |
| `src/jobpulse_v15/ia_enrichment.py` | `work_mode_por_patrones` (regla determinista antes del modelo, ampliada el 31-10) |
| `src/jobpulse_v15/scrape_dispatch.py` | **Fuente única** de cómo se llama a cada fetcher |
| `src/jobpulse_v15/analysis_flow.py` | **Implementación única** del análisis por reglas |
| `src/jobpulse_v15/elempleo.py` | Fix de la doble envoltura `asyncio.run` |
| `clean_run.py` | Limpieza de BD (borra derivados, conserva perfil/config/taxonomías, verifica huérfanos) |
| `run_full_flow.py` | Scrape síncrono correcto + Brave auto-gestionado (O7.2) |
| `src/jobpulse_v15/ui.py` | Usa `scrape_dispatch` y `analysis_flow` |
| `generar_evidencia_paso5.py` / `verificar_evidencia.py` | Evidencia por corrida vigente y tolerante a avisos purgados |
| `tests/test_ubicaciones_cr.py` | Tests del catálogo (28 casos + 13 subtests) |
| `tests/test_workday.py` / `test_repository.py` / `test_ia_enrichment.py` | Expectativas actualizadas + patrones nuevos de modalidad |
| `docs/FLUJO_CLI_VS_UI.md` | Comparación del flujo CLI con el de la UI |
| `docs/PASO5_EVIDENCIA_2026-10-31.md` · `docs/PASO5_REVISION_PENDIENTES.md` | Evidencia (GENERADO) y hoja de firma (30 casos) |

## Datos de contexto

- **DB**: `data/jobpulse_v15.db`, esquema **16**, **553 jobs**, 129 sitios
  habilitados, `integrity_check` **ok**, 0 violaciones FK.
- **Corrida vigente `20261031_214155`** (`valida=1`): calificada 177 ·
  sin_requisitos 138 · revisar_a_mano 106 · descartada 89 ·
  datos_insuficientes 43 (= **553**, verificado por `GROUP BY estado`).
  Motivos: 68 `titulo_universitario_requerido` + 21
  `titulo_universitario_en_curso_requerido` (descartada) · 30
  `educacion_no_confirmada` + 44 `educacion_no_cumple` + 20 `skill_faltante` +
  7 `licencia_no_comparable` + 5 `experiencia_no_verificable`
  (revisar_a_mano) · 138 `sin_requisitos_mapeados`.
- **Áreas (553)**: otros 98 · ventas 97 · informática 89 · producción 44 ·
  almacén 35 · administración 35 · ingeniería 34 · servicio al cliente 23 · …
- **Huecos por campo (553, sin IA)** — después del bloque 7: `city` **288** ·
  `region` **123** · `work_mode` **286** · `employment_type` **272** ·
  `languages` **553** · `skills` **553** · `salary_min` **553** (sin extractor).
  Antes del bloque 7: `city` 315 · `region` 135 · `work_mode` 327.
- **Causa de los huecos que quedan** (verificada a mano, corpus nuevo — la
  tabla completa está en el **Bloque 7**):
  - `salary_min` 553 → **falta real**: 12 "señales" y 11 son falsos positivos
    ("$200 million in fees", "$140M Series D"); solo 1 aviso publica un rango
    real y no hay extractor.
  - `work_mode` 286 → **falta real**: la regla determinista revisó los 286 y
    no encontró ninguna marca de modalidad.
  - `city` 288 → **129 por diseño** (la ubicación solo dice la provincia, cuyo
    nombre es también el de la ciudad: "San Jose, Costa Rica") · **93 no
    existe** (país/remoto/multi-loc) · **40 etiqueta de sucursal** (Harvie) ·
    **17 planta/sede** ("Wet Plant", "BSC").
  - `region` 123 → **93 no existe** (país/remoto/multi-loc: "Costa Rica",
    "GAM") · 16 con nombre de sucursal/empresa · 14 "Lagunilla, Costa Rica"
    (la tabla de lugares lo resuelve si el texto nombra Ultra Park/AFZ).
  - `employment_type` 272 (26 con señal) · `languages` 553 (59 con señal de
    idioma+nivel) · `skills` 553 (100 % IA).
  - **Los 138 `sin_requisitos`**: 112 con descripción utilizable y **ningún
    requisito extraído** (el aviso no cuantifica requisitos), 18 con
    descripción basura, 8 con requisito sin `codigo_canonico` (taxonomía).
- **Plataformas con más huecos de ubicación**: las que **no traen** un lugar
  concreto ("Costa Rica - Alajuela") y las de dirección ambigua; **Harvie**
  tiene la peor caso (el campo de ubicación es la sede corporativa y la
  sucursal va en el título).
- **Scripts de medición** (fuera del repo, en
  `C:\Users\giova\AppData\Local\Temp\opencode`): `relleno_por_plataforma.py`
  (llenado global + por plataforma + áreas + análisis), `medicion_final.py`
  (informe campo por campo con la **causa** de cada hueco), `huecos_agrupados.py`
  (huecos de city/region agrupados por `location_raw`), `clasificar_huecos.py`
  (clasificación automática de la causa), `diag_sin_requisitos.py` +
  `muestra_sin_requisitos.py` (por qué el extractor no vio requisitos),
  `dbg_lugares.py` / `sonda_lugares.py` (qué devuelve el catálogo con cada
  `location_raw`), `verificar.py`, `causa_huecos.py`, `wm_scan.py`/`wm_check.py`.
- **Gotchas nuevas**:
  - **Regex de modalidad**: "hybrid" es `h`+`y`+`brid` y "remote" es `r`+`e`+`mot`:
    los patrones correctos son `h(?:y|[ií])brid[oa]?` y `remot[eo]a?` (con
    `remot[oa]` **no** matchea "remote" y con `h[ií]brid[oa]` **no** matchea
    "Hybrid": dos bugs encontrados al ampliar los patrones, ambos con test).
  - **Python con la salida redirigida a un archivo no muestra nada hasta el
    final** (buffer): usar `-u` (`python -u ... | Out-File`) si se quiere ver
    el progreso.
  - **`Out-File -Encoding utf8` sí funciona**; el `>` de PowerShell escribe
    **UTF-16** (leer con `encoding="utf-16"`).
  - `ciudad_es_basura` **no** puede marcar como basura un nombre con palabras
    de 2 provincias sin comprobar antes que **no** sea un lugar del catálogo:
    "San José" tiene distritos homónimos en Alajuela y Heredia y **sí** es un
    lugar (la capital).
  - `analysis extract-pending` tiene `--limit` **máximo 500**: para todas las
    pendientes usar `run_full_flow.run_analysis()` (sin límite) o repetirlo.
  - El generador de evidencia usa una **muestra histórica con `job_id` a
    mano**; si una limpieza borra esos avisos, hoy se marcan `purgado`.
  - `run_full_flow.run_analysis()` devuelve el **nº de análisis** (no un
    código de error): "exit=552" no es un fallo.
  - Brave: si corre **sin** CDP, la app no puede abrir el puerto (Chromium
    delega en la instancia viva) → cerrarlo del todo y relanzar con
    `--remote-debugging-port=9222` sobre la raíz `User Data`.
  - La salida redirigida con `>` en PowerShell queda en **UTF-16** (leer con
    `encoding="utf-16"`).
- v1.x congelado en `D:\Proyectos\jobpulse_cr` — SOLO lectura.
- La **IA local quedó APAGADA** y **Brave quedó CERRADO** (la corrida de
  navegador abrió y cerró el suyo).
- `main` va **sin pushear** (no pushear sin confirmación del usuario).

## Pendiente inmediato

1. **Las 30 `revisar_a_mano / educacion_no_confirmada` siguen ABIERTAS**: las
   firma una **segunda persona** en `docs/PASO5_REVISION_PENDIENTES.md`. NO
   actualizar estados hasta esa firma.
2. **Capa B — taxonomía educativa**: migración **`017`** (master/MBA/
   associate/técnico superior) y crecer `concepto` para los **80 requisitos sin
   `codigo_canonico`** (31 con `value_code` NULL, 11 `tableau`, 9 `six_sigma`,
   7 `java`, 5 `typescript`, 5 `c#`, 4 `c++`, 3 `autocad`, 3 `B3`, …).
   Hoy 138 vacantes caen en `sin_requisitos` sin avisar.
3. **Extractor de salario**: no existe (0 % de llenado). En el corpus nuevo
   solo **1** aviso publica un rango real ("$4,000 to $6,000"); las otras 11
   "señales" son falsos positivos ("$200 million", "$140M Series D"). Decisión +
   tests + Paso 5 nuevo.
4. **Ubicación**: (i) los **129 `city` que solo traen "provincia + ciudad"**
   ("San Jose, Costa Rica", "Heredia, Costa Rica", "Alajuela, Costa Rica") son
   huecos **por diseño** (decidir si se relajan es política del negocio, no un
   bug); (ii) **40 son etiquetas de sucursal** de Harvie ("Lagar Alajuela",
   "Gravilias Tres Ríos"): la **sucursal real va en el TÍTULO** del aviso, no
   en el campo de ubicación → parsear el título es la vía (decisión pendiente);
   (iii) los 14 "Lagunilla, Costa Rica" se resuelven solo si el texto nombra
   Ultra Park/AFZ (¿añadir "Lagunilla" a la tabla de lugares?).
5. **`work_mode`**: los 286 huecos que quedan son **falta real** (ningún aviso
   declara modalidad). Si se quiere cerrarlos, la vía es la **IA con prompt
   específico** (no la regla determinista) o aceptar el `unknown`.
6. **UI**: poder correr el **Paso 5** desde la UI y mostrar `estado`/`motivo`
   de `job_match` (hoy la UI compara con otra función y no persiste) — ver
   `docs/FLUJO_CLI_VS_UI.md` §4.
7. **O5.3**: re-barrido de las **22 descripciones basura** (15 Indeed por
   login-wall).
8. **Paso 7** (`job_match_decision`) y **O8.2** ciclo de vida; O2.1/O2.2 · O4
   (redefinir) · O6.4 · O9.
9. **No tocar los umbrales** (cobertura 0.60 / puntaje 0.80) sin acuerdo
   explícito. **No pushear sin confirmación del usuario.**
10. **ANE**: la corrida del bloque 7 no raspó nada (sin sesión en Brave). Para
    cubrirlo hay que iniciar sesión en ANE (UI o `login_ane.py`) y re-raspar.
