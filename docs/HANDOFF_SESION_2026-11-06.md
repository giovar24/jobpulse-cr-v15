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

**Después (Ola 4.2, curación de la taxonomía)**: la cola
`concepto_no_normalizado` tenía **1988 filas y estaba obsoleta** (10 ya
resolvían; 1976 no). Medido el corpus real: de **3397 skills** distintas en
`jobs.skills` solo **241 resolvían** a un concepto (el 17 %); el resto eran
**actividades** ("despachar", "empacar"), **palabras vacías** ("analysis",
"planning") o **sectores** ("construccion", "ventas") — el criterio que la
migración 021 aplicó a mano pero que nadie automatizó. Se añadió (1) el
**filtro antes de encolar** (`conceptos.es_variante_encolable`, en el único
punto de entrada de la cola), (2) la **curación por tandas**: la migración
**023** (alias de conceptos existentes + conceptos nuevos), y (3) la
herramienta `jobpulse-v15 taxonomy curate` (audita el corpus y reconstruye la
cola). Medido sobre una **copia** de la BD real: las etiquetas que resuelven
suben de 241 a **560**, la cola baja de 1988 a **1225** filas (las pendientes
reales), los requisitos vigentes suben de 2483 (1 sin código) a **2857 (0 sin
código)** y **58 avisos cambian de estado** (47 `calificada → revisar_a_mano`):
los avisos ANE se evaluaban con **un solo requisito** (el idioma) y ahora
también con las skills que realmente piden ("inventario", "fontanería",
"electricidad", ISO 19011, PCAOB…) → el perfil no las tiene →
`revisar_a_mano/skill_faltante`. Bandas: `aplicar` 270 → **217**,
`no_prioritario` 323 → **376**, `veto` 96 → 96 (sin cambios),
`educacion_no_confirmada` 31 → **31 (intacto)**. **Aplicada a la BD real con
OK del usuario**: respaldo `data/backups/pre_ola42_20261106_182411.db`
(`integrity ok`, esquema 22) → migración **023** (esquema 23) → `taxonomy
curate --apply` (cola 1988 → **1225**) → re-análisis de los **705** avisos →
**2857 requisitos (0 sin código)** → **corrida `20261106_182554`** → evidencia
OK (137 verificaciones) → `db check` ok. El resultado real fue **idéntico al
medido en la copia** (58 cambios, 3,53 → 4,07 requisitos medios).

**Después (Ola 4.3, métricas por etapa)**: las siete etapas del pipeline
devuelven contadores **propios y en formatos distintos**, así que acabada la
corrida no se podía responder a la pregunta que importa (¿cuántos avisos
llegaron al Paso 5 y **en qué etapa se perdieron**?). Se añadió la tabla
**`pipeline_etapa`** (migración **024**, esquema 24) con una fila por etapa y
por ejecución, el módulo `jobpulse_v15.pipeline_metricas` (traduce cada etapa
a los contadores comparables `avisos`/`requisitos`/`errores`), la
instrumentación en el **único** punto del orquestador (`pipeline.ejecutar`,
puramente aditiva: si falla, la corrida sigue) y el comando de consulta
`… pipeline etapas [--limite N] [--corrida ID] [--json]`. Medido sobre una
**copia** de la BD real: paso5 **705 avisos / 2866 requisitos evaluados**,
evidencia 705 con 137 verificaciones, 0 errores. **Aplicada a la BD real con
OK del usuario** (solo la migración 024: respaldo
`pre_ola43_20261106_210124.db`, esquema 23 → **24**, `db check` ok; **nada del
matching cambió**: 705 avisos, corrida vigente `20261106_182554`,
`educacion_no_confirmada` 31 intacto).

**Después (corrida real con IA, 2026-11-06)**: se corrió el orquestador
completo sobre la **BD real** (`analisis → ia → reanalisis → backfill → paso5
→ evidencia`, con respaldo previo `pre_ia_20261106_215042.db`) para medir si
la IA sobre los **datos crudos que ya existen** mejoraba la extracción de
código. Resultado: **la mejora fue mínima** — requisitos 2857 → **2858** (+1),
todos con `codigo_canonico` (**100 %**, ya lo estaba), avisos sin requisito
8 → **7**, matching: calificada 190 → **191**, `sin_requisitos` 9 → **8**,
`educacion_no_confirmada` **31 (intacto)**. El pase de IA llenó **29 campos**
(`work_mode` +13, `employment_type` +12, `languages` +4) y **no** halló nada en
1.051 casos ("el aviso no lo dice", no son errores). Corrida vigente
**`20261106_220243`** · evidencia OK (137 verificaciones) · `db check` ok. El
único aviso que cambió fue `ane-121815` (`sin_requisitos` → `calificada`,
+1 requisito: el idioma del propio aviso). **Conclusión: el cuello de botella
ya no es la extracción** (está al 100 %) sino **el corpus** (705 avisos, los
24 de ANE sin entrar) y la **interpretación** (`ambiguous`/`unknown` en
`job_field_status`).

**Estado final de la BD real**: **esquema 24**, 705 avisos, 129 sitios,
706 conceptos canónicos, cola de taxonomía **1225** (las pendientes reales),
**2858 requisitos vigentes sin huecos** (100 % con `codigo_canonico`), corrida
Paso 5 vigente **`20261106_220243`** (calificada 191 · revisar 376 ·
descartada 96 · datos_insuf 34 · sin_requisitos 8 ·
`educacion_no_confirmada` **31**, sin cambios), `integrity_check ok` y 0
violaciones de FK. `pipeline_etapa` con **1 corrida** (`pipe_20261106_215235`,
6 etapas).

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

### 2.6 Ola 4.2 — curación de la taxonomía (`concepto_no_normalizado`)

**El problema medido** (sobre una copia de la BD real):

| Dato | Valor |
|---|---|
| Filas en la cola | **1988** (10 ya resolví­an; 1976 no) |
| Skills distintas en `jobs.skills` | 3397 (5199 menciones) |
| Resolvían a un concepto | **241** (877 menciones: el 17 %) |
| Ruido (actividad / palabra vacía / sector) | 1634 variantes (2594 menciones) |
| Conceptos canónicos | 392 |

La cola era una lista de trabajo **inútil**: mezclaba herramientas ("Mulesoft")
con tareas ("despachar", "empacar"), palabras vacías ("analysis", "planning")
y sectores ("construccion", "ventas"). El criterio ya existía (migración 021:
*"se deja fuera lo que es una funcion ('ventas'), un sector ('construccion'),
una palabra vacia ('analysis', 'planning') o una tarea ('despachar',
'empacar')"*) pero estaba escrito a mano en el SQL: la cola se llenaba de
todo.

**Lo que se hizo**:

1. **Filtro antes de encolar** (`conceptos.es_variante_encolable`): descarta
   actividad, palabra vacía, sector y frases de más de tres palabras. Vive en
   `encolar_sin_concepto`, el **único punto de entrada** de la cola → aplica a
   todos los orígenes. Es **conservador**: lo que no cae en las reglas se
   queda en la cola (nunca se descarta en silencio).
2. **Curación por tandas** (datos): la migración **023**
   (`023_taxonomia_curacion_tanda_1.sql`) añade **alias** de conceptos que ya
   existían ("office 365 basico" → Office 365, "mantenimiento correctivo" →
   mantenimiento, "cierre de cajas" → cierre de caja) y **conceptos nuevos**
   para lo que el corpus pide y no existía (Mulesoft, PowerShell, MFA, SAML,
   ISO 9001/19011, lectura de planos, metrología, cableado estructurado,
   fontanería, electricidad…).
3. **Herramienta de curación** (`jobpulse-v15 taxonomy curate [--apply]`):
   audita el corpus (resuelto / ruido / pendiente) y reconstruye la cola
   desde `jobs.skills`/`jobs.languages`: borra lo ya resuelto y lo que es
   ruido, y reescribe `veces` con el nº de **avisos** que piden cada variante
   (antes contaba encolados: un número que se inflaba con cada re-análisis).

**Medición sobre una COPIA** (`%TEMP%\opencode\ola42_full.db`):

| Métrica | Antes | Después |
|---|---|---|
| Etiquetas que resuelven | 241 | **560** (877 → 2064 menciones) |
| Cola | 1988 | **1225** (pendientes reales) |
| Requisitos vigentes | 2483 (1 sin código) | **2857 (0 sin código)** |
| Requisitos medios por aviso | 3,53 | **4,07** (232 con más, 0 con menos) |
| `calificada` / `revisar_a_mano` | 237 / 320 | **190 / 376** |
| `datos_insuf` / `sin_requisitos` | 41 / 11 | **34 / 9** |
| `descartada` / `educacion_no_confirmada` | 96 / 31 | **96 / 31 (intacto)** |
| Bandas `aplicar` / `no_prioritario` | 270 / 323 | **217 / 376** |

**Por qué cambian 58 avisos** (esto es la calidad del dato, no un bug):
`ane-121787` se evaluaba con **un solo requisito** ("espanol") y salía
`calificada/cumple_umbral`; con la taxonomía curada además pide "Inventario"
→ `codigo_canonico='inventarios'` → el perfil no lo tiene →
`revisar_a_mano/skill_faltante`. Lo mismo con `ane-121790` ("fontanería",
"electricidad"), `ane-121807` (ISO 19011, PCAOB, ICFR, SEC SOX, COSO),
`ane-121822` ("asientos contables"). Antes esos requisitos eran **invisibles**
(sin `codigo_canonico` el motor los ignora en silencio) y las vacantes
parecían más compatibles de lo que son. `veto` (96) no cambia y
`educacion_no_confirmada` (31) tampoco.

**Ojo (para la siguiente tanda)**: la etapa `reanalisis` del pipeline solo
re-analiza los avisos que **nunca** integraron `jobs.skills`
(`avisos_con_campos_sin_integrar`): tras cambiar la taxonomía, los que ya
las integraron tienen un análisis **obsoleto** (les faltan requisitos) y hay
que re-analizarlos con `enrich requirements-source --apply` (o el equivalente
en el pipeline). Con eso los requisitos medios suben de 3,53 a 4,07.

### 2.7 Ola 4.3 — métricas por etapa (`pipeline_etapa`)

**El problema medido**: las siete etapas del pipeline devuelven contadores
**propios y en formatos distintos** (`analizados`, `jobs_found`, `ciclos`,
`candidatos`, `actualizados`, `por_estado`, `verificaciones`…). Acabada la
corrida solo quedaba el estado final, así que **no se podía responder a la
pregunta que importa**: de todos los avisos que entraron, ¿cuántos llegaron al
Paso 5, cuántos tenían requisitos y **en qué etapa se perdieron**? (Caso real
de la Ola 4.2: 705 avisos entraron al análisis, 9 acabaron en `sin_requisitos`
y 58 cambiaron de estado por requisitos sin `codigo_canonico` — sin el
registro, ese hueco solo se descubría mirando los estados finales.)

**Lo que se hizo**:

1. **Tabla `pipeline_etapa`** (migración **024**, esquema 23 → **24**): una
   fila por **etapa y por ejecución** del pipeline. Columnas: `corrida_id`
   (`pipe_<timestamp>`, **distinto** del `corrida_id` de `job_match` — el del
   Paso 5 va en el `detalle_json` de la etapa `paso5`), `etapa`, `ok`,
   `duracion_ms`, `avisos`, `requisitos`, `errores`, `detalle_json`,
   `iniciado_en`, `terminado_en`. Índices por `(corrida_id, id)` y
   `(etapa, id)`. **Sin claves foráneas** a propósito: el `corrida_id` del
   pipeline es un id **lógico** (no hay tabla de corridas del pipeline).
2. **Módulo `jobpulse_v15.pipeline_metricas`**: traduce el resultado de cada
   etapa a tres números **comparables** (`avisos` / `requisitos` / `errores`) y
   guarda los contadores **específicos** de la etapa en `detalle_json` (por
   estado y motivo del Paso 5, por campo rellenado por la IA, por sitio del
   barrido…).
3. **Instrumentación en el orquestador** (`pipeline.ejecutar`): es el **único**
   punto donde se cronometran las etapas → CLI, UI v2 y `run_full_flow.py`
   dejan la misma métrica. **Puramente aditiva**: si falla, la corrida
   **sigue** (una métrica nunca rompe un pipeline).
4. **Contadores que faltaban** (añadidos a las etapas que no los exponían):
   `analisis.requisitos_guardados`, `paso5.requisitos_evaluados` (suma de
   `Resultado.total_req`), `reanalisis.texto_errores` y
   `evidencia.documentados`.
5. **Consulta**: `… -m jobpulse_v15 pipeline etapas [--limite N] [--corrida ID]
   [--json]` + una línea "MÉTRICAS" en la UI v2 (la UI clásica queda intacta).

**Medición sobre una COPIA** (`%TEMP%\opencode\ola43_copia.db`):

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

Los contadores cuadran con el estado real (705 evaluados, 2866 requisitos,
evidencia con 137 verificaciones literales y `no_confirmada=31` intacto), y el
`detalle_json` del Paso 5 guarda el desglose por estado y por motivo.

**APLICADA A LA BD REAL (2026-11-06, con OK del usuario)**: solo la
**migración 024** (la tabla de auditoría), **sin** tocar el matching:
respaldo `data/backups/pre_ola43_20261106_210124.db` (19,4 MB) → `db check`
previo (esquema 23, `integrity ok`, 0 violaciones de FK) → apertura (aplica
la **024**, esquema **24**) → `db check` posterior (**esquema 24**, `integrity
ok`, 0 violaciones de FK). Estado **sin cambios**: 705 avisos · 706 conceptos
· cola 1225 · 825 `job_analysis` · **0 requisitos sin código** · 2669 filas de
`job_match` · corrida vigente **`20261106_182554`** (calificada 190 · revisar
376 · descartada 96 · datos_insuf 34 · sin_requisitos 9) ·
`educacion_no_confirmada` **31 (intacto)**. `pipeline_etapa` queda **vacía**
(0 filas): se llenará sola con la próxima corrida real del pipeline.

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
| Ola 4.2 (curación de la taxonomía) | Cola `concepto_no_normalizado`: 1988 filas, 1976 sin resolver | 🟢 **HECHO Y APLICADO (2026-11-06)**: filtro `es_variante_encolable` + migración 023 (tanda 1) + `taxonomy curate`. En la BD real: etiquetas que resuelven 241 → **560**, cola 1988 → **1225**, requisitos 2483 (1 sin código) → **2857 (0 sin código)**, **58 de 705 cambian de estado**, `educacion_no_confirmada` 31 → 31, corrida `20261106_182554` |
| Ola 4.3 (métricas por etapa) | Auditar por qué una corrida dio menos | 🟢 **HECHO Y APLICADO (2026-11-06)**: tabla `pipeline_etapa` (migración 024, esquema 24) + instrumentación en `pipeline.ejecutar` + `pipeline_metricas.py` + `… pipeline etapas`. Medido sobre copia: paso5 705 avisos / 2866 requisitos, evidencia 137 verificaciones, 0 errores. En la BD real: migración + **corrida real** (`pipe_20261106_215235`, 6 etapas) |
| O6.4 (dedupe slugs ES/EN) | — | ⏳ Parcial |
| O4 (calibración gate-vs-IA) | — | 🟡 Proponer cerrar como *superseded* |
| O8.2 / O8.4 / O9 / pestañas nuevas UI v2 | — | ⏳ Pendiente (Ola 4) |

**Siguiente ola** (plan en `docs/PLAN_MEJORAS.md`): **Ola 4 — calidad del
dato**: 4.1 (parser de ANE + re-barrido + re-análisis: **HECHO Y APLICADO**) ·
4.2 curación de la taxonomía (`concepto_no_normalizado`: **HECHO Y APLICADO**
— esquema 23, cola 1988 → **1225**, 2857 requisitos sin huecos, corrida
`20261106_182554`) · 4.3 métricas por etapa (**HECHO Y APLICADO** — esquema 24;
ya llenada con una **corrida real**: `pipe_20261106_215235`, 6 etapas, y la
corrida del Paso 5 `20261106_220243`) · 4.2 segunda tanda de
curación (`veces >= 2`) · **corrida en limpio con scrape → otro día** (la
medida de hoy sobre los datos crudos dio +1 requisito: la extracción ya
está al 100 %; lo que falta es **corpus** e **interpretación**).

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

# Solo la Ola 4.2
python -m pytest tests/test_conceptos.py tests/test_taxonomia.py `
  tests/test_matching.py tests/test_migraciones.py -q

# Taxonomia: auditar la cola / reconstruirla (NO toca la BD real sin --apply)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 taxonomy curate --limit 30
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 taxonomy curate --apply

# ANE: login + barrido (sesión guardada → funciona aunque Brave se cierre)
.\.venv\Scripts\python.exe -X utf8 login_ane.py --mantener-abierto
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 scrape ane --site ane-cr

# ANE: re-barrido de DETALLE (avisos ya guardados; corrige el texto viejo)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 scrape ane --site ane-cr --revisitar
#   (--limite N para revisar solo N)

# Estado de la BD y evidencia (exit 0 = todo cuadra)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 db check
.\.venv\Scripts\python.exe -X utf8 verificar_evidencia.py

# Métricas por etapa (Ola 4.3)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 pipeline etapas --limite 5
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 pipeline etapas --json

# Corrida real del pipeline (el MISMO orquestador que la CLI y la UI v2)
#   sin 'scrape' = sobre los datos crudos que ya existen
.\.venv\Scripts\python.exe -X utf8 -c "from jobpulse_v15 import pipeline; ..."

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
| `src/jobpulse_v15/conceptos.py` | **Ola 4.2**: `es_variante_encolable` (filtro de la cola) + `PALABRAS_DE_ACTIVIDAD`/`PALABRAS_GENERICAS`/`SECTORES`; `encolar_sin_concepto` es el único punto de entrada |
| `src/jobpulse_v15/taxonomia.py` | **NUEVO** (Ola 4.2): `demanda_corpus` (resuelto/ruido/pendiente) y `curar` (reconstruye la cola desde el corpus) |
| `src/jobpulse_v15/migrations/023_taxonomia_curacion_tanda_1.sql` | **NUEVO** — taxonomía curada, tanda 1: alias de conceptos existentes + conceptos nuevos |
| `src/jobpulse_v15/skills_fuente.py` | **Ola 4.2**: `normalizar` y `mapa_normalizado` públicos (los usa la curación) |
| `src/jobpulse_v15/cli.py` | **Ola 4.2**: `taxonomy curate [--apply] [--limit N]` |
| `tests/test_taxonomia.py` (4) · `tests/test_conceptos.py` (+7) | **NUEVOS** de la Ola 4.2 |
| `src/jobpulse_v15/pipeline_metricas.py` | **NUEVO** (Ola 4.3): contadores comparables por etapa, `registrar_etapa`, consultas |
| `src/jobpulse_v15/migrations/024_pipeline_etapa.sql` | **NUEVO** — tabla `pipeline_etapa` (métricas por etapa; esquema 24) |
| `src/jobpulse_v15/pipeline.py` | **Ola 4.3**: instrumentación (cronómetro + `registrar_etapa`) y contadores nuevos (`requisitos_guardados`, `requisitos_evaluados`, `texto_errores`, `documentados`) |
| `src/jobpulse_v15/cli.py` | **Ola 4.3**: `pipeline etapas [--limite N] [--corrida ID] [--json]` |
| `tests/test_pipeline_metricas.py` (nuevo) · `tests/test_pipeline.py` (+4) | **NUEVOS** de la Ola 4.3 |
| `docs/SITIOS_PROBLEMATICOS.md` | Reescrito: 4 sitios, `requires_login`, sesión de ANE, rate-limit de LinkedIn |
| `docs/PLAN_MEJORAS.md` · `DESARROLLO_v15.md` · `AGENTS.md` | Olas 4.1 y 4.2 aplicadas a la BD real (esquema 23); Ola 4.3 hecha (esquema 24 al abrir la BD) |
| `docs/FLUJO_CLI_VS_UI.md` | **§5** el flujo anotado de la corrida real (etapa por etapa) · **§6** comparación con el flujo de la UI (CLI ↔ UI v2 ↔ UI clásica), **sin tocar la UI** |

---

## 7. Contexto (estado de la BD real)

- **BD real `data/jobpulse_v15.db`**: **esquema 24** (tras la Ola 4.3; la 023
  fue la Ola 4.2), **705 avisos**, 129 sitios, 136 corridas de sitio, 825
  `job_analysis`
  (705 vigentes + 120 del re-análisis; el re-análisis de la Ola 4.2 **actualizó
  las filas vigentes en sitio**, no infla el historial), 706 conceptos
  canónicos, 2669 `job_match` (4 corridas; 1 válida).
  `integrity_check ok`, 0 violaciones de FK.
  **Requisitos vigentes**: 2483 (1 sin `codigo_canonico`) → **2857 (0 sin
  código)** → **2858 (0 sin código**, tras la corrida real con IA).
  **Cola `concepto_no_normalizado`**: 1988 → **1225** (las
  pendientes reales; `veces` = nº de avisos que piden cada variante).
  Corrida Paso 5 vigente **`20261106_220243`** (tras la corrida real con IA):
  calificada 191 · revisar 376 · descartada 96 · datos_insuf 34 ·
  sin_requisitos 8 · `educacion_no_confirmada` 31 (intacto).
  Corridas anteriores (siguen en la BD, `valida=0`): `20261106_182554`
  (Ola 4.2: calificada 190 · revisar 376 · descartada 96 · datos_insuf 34 ·
  sin_requisitos 9), `20261106_152304`
  (Ola 4.1: calificada 237 · revisar 320 · descartada 96 · datos_insuf 41 ·
  sin_requisitos 11) y `20261104_231932`.
- **Respaldo**: `data/backups/pre_ia_20261106_215042.db` (antes de la corrida
  real con IA), `data/backups/pre_ola43_20261106_210124.db` (antes de la 024),
  `data/backups/pre_ola42_20261106_182411.db` (antes de la Ola
  4.2), `data/backups/pre_ola4_20261106_151857.db` (antes de la Ola
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
- **Medición de la Ola 4.3** (sobre `%TEMP%\opencode\ola43_copia.db`, copia de
  la BD real): la 024 se aplicó sola al abrir la copia (esquema 24) y el
  orquestador dejó sus filas: paso5 **705 avisos / 2866 requisitos
  evaluados**, evidencia 705 avisos con 137 verificaciones literales
  (`no_confirmada=31` intacto), 0 errores, corrida completa ≈ 3,4 s.
  **En la BD real se aplicó SOLO la migración 024** (con OK del usuario;
  respaldo `pre_ola43_20261106_210124.db`): esquema 23 → **24**, `db check` ok
  (`integrity ok`, 0 violaciones de FK) y **nada más cambió** (705 avisos,
  corrida vigente `20261106_182554`, `educacion_no_confirmada` 31).
  `pipeline_etapa` tiene **1 corrida** (`pipe_20261106_215235`, 6 etapas):
  la de la corrida real con IA (abajo).
- **Corrida real con IA (2026-11-06, aplicada)**: orquestador completo sobre
  la BD real (`analisis → ia → reanalisis → backfill → paso5 → evidencia`),
  respaldo `data/backups/pre_ia_20261106_215042.db`. **Qué mejoró** (medido
  antes/después con `estado_extraccion.py`): requisitos vigentes 2857 →
  **2858** (+1, todos con `codigo_canonico`: la cobertura estaba y sigue al
  **100 %**); variantes con código 546 → 546; cola de taxonomía 1225 → 1225
  (**+0**: la IA no aportó variantes nuevas); avisos sin ningún requisito 8 →
  **7**; campos `work_mode` 375 → **388** (+13), `employment_type` 648 → **660**
  (+12), `languages` 677 → **681** (+4), `city`/`region`/`skills`/`salary` +0.
  Matching: corrida `20261106_182554` → **`20261106_220243`**, calificada 190 →
  **191**, `sin_requisitos` 9 → **8**, resto igual, `educacion_no_confirmada`
  **31 (intacto)**; evidencia OK (137 verificaciones literales) y `db check`
  ok. El único cambio es `ane-121815` (`sin_requisitos` → `calificada`, con
  **un** requisito: "español nativo", `ambiguous`, `origin='source_field'` →
  es el caso degenerado que el propio repo avisa: 1 requisito cubierto saca
  100). **Diagnóstico del pase IA**: `enriched=25` · `failed=1051` (**"no
  mencionado", NO son errores**: en el log no hay ni un "IA extract {campo}
  fallo tras 3 intentos") · `skipped=198`. La 10 min de la etapa se las lleva
  el modelo local; el resto del pipeline, 2 s.
- **Corrección de la instrumentación (2026-11-06)**: la Ola 4.3 contaba el
  `failed` del pase IA como **errores** (1051), pero en el pase IA `failed` =
  "el modelo no halló el campo". Se corrigió `pipeline_metricas` (los errores
  reales vienen en `stats_ia["error"]`; el `failed` va al detalle como
  `no_encontrado`) y se corrigió la fila ya escrita de la corrida
  `pipe_20261106_215235` (1051 → 0, con nota en el `detalle_json`).

---

## 8. Pendiente inmediato

1. ~~**Aplicar la Ola 4.2 a la BD real**~~ → **HECHO (2026-11-06, con OK del
   usuario)**: respaldo `data/backups/pre_ola42_20261106_182411.db` →
   migración **023** (esquema 23) → `taxonomy curate --apply` (cola
   1988 → **1225**) → re-análisis de los **705** avisos → **2857 requisitos
   (0 sin código)** → backfill (0) → **corrida `20261106_182554`** → evidencia
   OK (137 verificaciones) → `db check` ok. Resultado **idéntico al medido en
   la copia** (58 avisos cambian de estado; `aplicar` 270 → 217;
   `educacion_no_confirmada` 31 → 31 intacto).
2. **Ola 4 — seguir** (`docs/PLAN_MEJORAS.md`): ~~4.3 métricas por etapa~~ →
   **HECHO Y APLICADO A LA BD REAL (2026-11-06)**: tabla `pipeline_etapa`
   (migración 024, esquema 24), instrumentación en `pipeline.ejecutar` +
   `pipeline_metricas.py`, comando `… pipeline etapas`. Ya se aplicó con una
   **corrida real** (`pipe_20261106_215235`): 6 etapas registradas, la IA
   corrijo su contador de "errores" (los 1051 `failed` son "no mencionado",
   no fallos) · 4.2 segunda tanda de curación (la cola tiene 1225
   pendientes: la siguiente tanda es la que cubre `veces >= 2`).
3. **Corrida en limpio con scrape → OTRO DÍA** (decisión del usuario): hoy se
   midió la IA sobre los datos crudos que ya existen (705 avisos, **sin**
   `scrape`) y la mejora fue mínima (+1 requisito). La corrida en limpio
   (barrido completo, incluidos los 24 ANE 122031+ que se detectaron) queda
   para otro día, **con el aviso de que el modelo local tarda ~10 min por
   700 avisos**. Si se quiere adelantar solo lo de ANE:
   `scrape ane --site ane-cr` (24 nuevos) → `analysis extract-pending` →
   `run_enriquecimiento.py` → re-análisis → backfill → `run_paso5.py`.
4. (Opcional, con permiso del usuario) migrar la **UI clásica** al orquestador
   `pipeline.py` (usa las mismas implementaciones por etapa, pero mantiene su
   propio flujo; la UI clásica no se toca sin pedirlo). La comparación
   completa CLI ↔ UI está en `docs/FLUJO_CLI_VS_UI.md` §6.
5. `educacion_no_confirmada` (31 casos): **NO** actualizar estados hasta que
   una **segunda persona** firme `docs/PASO5_REVISION_PENDIENTES.md` (ya
   regenerada para la corrida `20261106_220243`).
6. Decidir si el **rate-limit de LinkedIn** sube de 1,5 s según la carga real
   (medido: 10 peticiones sin espera → 429).

---

## 9. Commits de esta sesión

- `6afba1b` — `feat(o5.3): Ola 4.3 - metricas por etapa del pipeline (pipeline_etapa)` (pusheado) — tabla `pipeline_etapa` (migración 024, esquema 24), módulo `pipeline_metricas`, instrumentación en `pipeline.ejecutar`, comando `pipeline etapas`, línea de métricas en la UI v2; medido sobre copia (paso5 705 avisos / 2866 requisitos; evidencia 137 verificaciones; `educacion_no_confirmada` 31 → 31 intacto). Suite: **1159 passed + 980 subtests**.

- `84af033` — `docs(o5.3): Ola 4.2 aplicada a la BD real (taxonomia curada, corrida 20261106_182554)` — respaldo + migración 023 (esquema 23) + cola 1988 → **1225** + re-análisis de los 705 avisos + **2857 requisitos (0 sin código)** + evidencia OK (137) + `db check` ok; resultado **idéntico al medido en la copia** (58 avisos cambian de estado; `educacion_no_confirmada` 31 → 31).
- `df6a31d` — `feat(o5.3): Ola 4.2 - filtro de la cola de taxonomía, curacion en tandas y herramienta de curacion` — filtro `es_variante_encolable`, migración 023 (tanda 1), `taxonomia.py` + `taxonomy curate`, 19 tests nuevos; medido sobre copia (58 avisos cambian de estado; `educacion_no_confirmada` 31 → 31). Suite: **1127 passed + 980 subtests**.
- **HEAD (aplicación a la BD real)** — `docs(o5.3): Ola 4.1 aplicada a la BD real (texto de ANE corregido, corrida 20261106_152304)` — evidencia + hoja de firma regeneradas, docs actualizadas.
- `280b4e7` — `feat(o5.3): Ola 4.1 - parser de ANE completo, re-barrido de detalle y re-análisis por texto nuevo` (pusheado) — parser ampliado, `scrape ane --revisitar`, `reananalizar_texto_cambiado`, medición sobre copia (9 de 705 cambian de estado; `educacion_no_confirmada` 31 → 31).
- `14bba25` — `feat(o13): Ola 3 - cobertura de fuentes (LinkedIn, Elempleo, requires_login, sesión ANE)` — scrapers reescritos, migración 022, `requiere_login.py`, `sesion_navegador.py`, 52 tests nuevos + 2 de UI v2 + 2 de ANE, docs actualizadas. Suite: **1083 passed + 247 subtests**.
- `680024f` — `feat(o12): Ola 2 - orquestador único (pipeline.py) y botones "Procesar"/"Enriquecer IA" en la UI v2` (pusheado).
- `21af318` — `feat(o12): Ola 1 - paridad CLI/UI (re-análisis, evidencia, login ANE)` (pusheado).
