# Goldfish Annotated Review Report

**Target:** `README.md` (`1-822`, full file)
**Ronda:** 1
**Revisores:** `codebase_details` (completed, 8 hallazgos) · `style` (completed, 15 hallazgos) · `comprehension` (completed, 8 hallazgos)
**Total:** 31 hallazgos — 2 Blocker · 18 Major · 11 Nit

> Nota: `comprehension` no pudo leer su persona/estándar del bundle
> (`external_directory` denegado por el sandbox) y auditó con los criterios
> replicados en el prompt. Sus hallazgos se tratan como válidos; la calibración
> de severidad puede diferir del rubric canónico.

## Prioritized Findings & AI Suggestions

### Interfaz de escritorio obsoleta: describe la UI clásica ya eliminada [`codebase_details`] - Severity: High
*   **Affected Scope:** [161-263](README.md#L161-L263) (`## Interfaz de escritorio`)
*   **Discrepancy Description:** La sección presenta como vigente una UI con pestañas «Calidad de datos», «Revisar duplicados», «Analizar pendientes», «Editar datos», «Restaurar datos de fuente», «Seguimiento», «Comparar perfil», «Compatibilidad», «Motivo de revisión», «Max. resultados», «Publicada desde/hasta», «Tipo de empleo», «Horario» y filtros salariales. La UI real (`ui_v2/app.py:39-45`) registra solo `DatosCrudosTab`, `PerfilTab`, `VacantesTab`, `ScrapingTab`, `CuentasTab`, `ConfiguracionTab`. La UI clásica (`ui.py`) se retiró el 2026-11-11.
*   **Rationale:** Todo el capítulo induce a buscar interfaces y filtros inexistentes.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Verificado: `PESTANIAS` tiene exactamente 6 pestañas y ningún módulo de `ui_v2` implementa los controles descritos. El contenido es histórico.
*   ***Proposed Edit:***
    *   Location: `## Interfaz de escritorio` (línea 161)
    *   Change: Añadir bajo el encabezado el aviso: «> **Histórico.** Esta sección describe la UI clásica (`ui.py`), retirada el 2026-11-11. La única interfaz vigente es la UI v2: ver [`src/jobpulse_v15/ui_v2/README.md`](src/jobpulse_v15/ui_v2/README.md) (6 pestañas: Datos crudos, Perfil, Vacantes, Scraping, Cuentas, Configuración).»

### Workable: localización y modalidad contradictorias [`codebase_details`] - Severity: High
*   **Affected Scope:** [481-490](README.md#L481-L490) (`### Workable`)
*   **Discrepancy Description:** El doc atribuye a Workable la variante `<country_query> (multi-loc)` y la detección de modalidad solo como «telecommuting». El código usa `country_query` directa (`workable.py:55-57,86`, sin `multi-loc`) y mapea `remote`/`hybrid`/`onsite` desde `**Workplace:** ` (`workable.py:210-219`).
*   **Rationale:** Afirmaciones falsas sobre el fetcher y sobre quién normaliza la geografía.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Verificado por grep en `workable.py`.
*   ***Proposed Edit:***
    *   Location: `### Workable` (481-490)
    *   Change: Sustituir la variante multi-loc por la consulta de país directa; documentar `remote`/`hybrid`/`onsite` desde `**Workplace:**`; aclarar que la normalización geográfica la hace el pipeline de ubicaciones, no el fetcher.

### Solo `corrida_medicion.py` y `limpiar_null.py` escriben en la BD [`codebase_details`] - Severity: Medium
*   **Affected Scope:** [50-51](README.md#L50-L51) (`## Subdirectories & System Boundaries`)
*   **Discrepancy Description:** El doc dice que solo esos dos escriben. Además, `tools/ver_sitio.py:7`, `estado_bd.py:8`, `comparar_ia.py:72` y `cobertura_campos.py:5` llaman `Database.initialize()`, que aplica migraciones y mueve `PRAGMA user_version`.
*   **Rationale:** Herramientas presentadas como de solo lectura pueden alterar el esquema.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Verificado; ya corregido en `tools/README.md` y `AGENTS.md`, falta en el contrato raíz.
*   ***Proposed Edit:***
    *   Location: líneas 50-51
    *   Change: «…dos escriben **datos** en la BD: `corrida_medicion.py` y `limpiar_null.py`; además `estado_bd.py`, `cobertura_campos.py`, `ver_sitio.py` y `comparar_ia.py` llaman `Database.initialize()` y pueden **aplicar migraciones** pendientes.»

### Extractor declarado como `rules-1` pero el código usa `rules-2` [`codebase_details`] - Severity: Medium
*   **Affected Scope:** [639](README.md#L639), [771](README.md#L771) (`## Analisis estructurado y busqueda`, `## Extractor inicial de requisitos`)
*   **Discrepancy Description:** El doc cita `rules-1`; el código define `EXTRACTOR_VERSION = "rules-2"` (`analysis.py:8`) y `VERSION_ANALISIS = "rules-2+fuente"` (`analysis_flow.py:29`). `rules-1` solo sobrevive como literal en tests.
*   **Rationale:** Un lector concluiría que el analizador activo es el limitado `rules-1`.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Verificado por grep.
*   ***Proposed Edit:***
    *   Location: 639 y 771
    *   Change: `rules-1` → `rules-2` (análisis por reglas) y `rules-2+fuente` (integrado con campos estructurados); mencionar que `rules-2` extrae `skills` y clases de licencia.

### `normalize-workday --apply` no solo rellena: corrige ciudades existentes [`codebase_details`] - Severity: Medium
*   **Affected Scope:** [529-539](README.md#L529-L539) (`### Normalización de ubicaciones`)
*   **Discrepancy Description:** El doc dice que «solo rellena» campos vacíos. El código detecta ciudades basura con `ciudad_es_basura`, las **sustituye** (`replace_city=True`) y cuenta `report["corrected_cities"]` (`cli.py:3102-3205`).
*   **Rationale:** Es una escritura destructiva sobre `jobs.city` presentada como aditiva.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Verificado.
*   ***Proposed Edit:***
    *   Location: 529-539
    *   Change: Documentar que `--apply` también **corrige ciudades existentes** clasificadas como basura (`ciudad_es_basura`), expone `corrected_cities` y modifica datos existentes (respaldar antes).

### Cobertura ausente de subsistemas y comandos vigentes [`codebase_details`] - Severity: Medium
*   **Affected Scope:** [101-160](README.md#L101-L160), [605-618](README.md#L605-L618), [768-821](README.md#L768-L821)
*   **Discrepancy Description:** Faltan: `viabilidad list|top` (bandas `aplicar`/`revisar`/`no_prioritario`/`sin_datos`/`veto`); `decision list|sign` y tabla `job_match_decision`; `pipeline etapas` y tabla `pipeline_etapa`; `postulaciones correo|workday` y tablas `postulacion*`; `taxonomy curate`; `enrich posting-language|profile-canonico|requirements-canonico|requirements-source`; `init-areas`/`areas list|classify` y tablas `area*`; `init-sources`/`site seed-cr`/`credenciales`/`login`; estado `requiere_login`; retención; y la sección «Esquema inicial» solo lista un subconjunto de tablas.
*   **Rationale:** El contrato raíz no permite saber qué comandos existen sin leer el código.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Todos los comandos y tablas citados existen (verificado en `cli.py`, `migrations/` y `migrations/README.md`). No se reescribe el manual: se añade un índice de subsistemas con enlaces al contrato del paquete.
*   ***Proposed Edit:***
    *   Location: tras la línea 97 (antes de `---`)
    *   Change: Nueva sección `## Subsistemas y comandos no detallados aquí` con una tabla de 10 filas (subsistema → comando(s) → tabla(s) → enlace a `src/jobpulse_v15/README.md`), y nota de que «Esquema inicial» documenta solo el núcleo y el listado completo está en `migrations/README.md`.

### Contadores de `location normalize` mal atribuidos [`codebase_details`] - Severity: Low
*   **Affected Scope:** [546-548](README.md#L546-L548)
*   **Discrepancy Description:** El doc lista «no reconocidas» y «fuentes conflictivas» como contadores genéricos. `normalize` expone `skipped_no_location` y `skipped_unchanged` (`cli.py:1339-1354`); los otros dos son de la variante `normalize-workday`.
*   **Rationale:** Confunde los dos comandos.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Verificado.
*   ***Proposed Edit:***
    *   Location: 546-548
    *   Change: Separar los contadores por comando.

### Cierre de Brave en `login_ane.py` mal descrito [`codebase_details`] - Severity: Low
*   **Affected Scope:** [32](README.md#L32)
*   **Discrepancy Description:** El doc dice que «cierra Brave al terminar». El código cierra por CDP **solo si él lo abrió**; `--mantener-abierto` lo deja vivo; un Brave preexistente no se toca (`login_ane.py:50-79`).
*   **Rationale:** Omite dos de las tres variantes.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Verificado.
*   ***Proposed Edit:***
    *   Location: línea 32
    *   Change: «…cierra **solo el Brave que él abrió** (ordenado, por CDP); `--mantener-abierto` lo deja vivo; un Brave preexistente no se toca.»

### Lenguaje de fase obsoleto y referencia a `data/jobs.db` [`style`] - Severity: Medium
*   **Affected Scope:** [101-114](README.md#L101-L114) (`## Documentación funcional`, `## Alcance de esta fase`)
*   **Discrepancy Description:** «Esta carpeta inicia el desarrollo aislado de la version 1.5» y «`data/jobs.db` no se modifican ni se migran» son enunciados de arranque presentados como documentación vigente; `data/jobs.db` no se define en ningún otro punto.
*   **Rationale:** Un lector nuevo no sabe si eso sigue siendo cierto.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Válido: la BD vigente es `data/jobpulse_v15.db` y el proyecto ya está en v1.5 con CLI, IA y matching.
*   ***Proposed Edit:***
    *   Location: 103-104
    *   Change: «JobPulse CR v1.5 usa una base independiente en `data/jobpulse_v15.db`; no modifica ni migra las bases de versiones anteriores (v1.x, `data/jobs.db`).»

### Rutas personales dentro del contrato de interfaz [`style`] - Severity: Medium
*   **Affected Scope:** [35](README.md#L35), [65-70](README.md#L65-L70)
*   **Discrepancy Description:** La tabla fija `D:\Proyectos\jobpulse_cr\data\usuario\profile.json` y los invariantes citan `C:\Users\giova\...\Brave\User Data`.
*   **Rationale:** Mezcla hechos durables con diagnóstico local.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Los datos son correctos y útiles al mantenedor (los añadió la pasada de deriva), pero su sitio no es una tabla de contrato ni una invariante global. Se conservan, reubicados.
*   ***Proposed Edit:***
    *   Location: 35 y 65-70
    *   Change: En la tabla, usar `<repo-v1x>\data\usuario\profile.json` con nota «por defecto apunta al repo v1.x archivado». Mover el detalle de lanzadores a una subsección `### Problemas conocidos de los lanzadores` al final del blueprint (mismo texto, con `file:line`).

### La invariante «General, no "para mí"» contiene una excepción contradictoria [`style`] - Severity: Medium
*   **Affected Scope:** [63-70](README.md#L63-L70) (`## Global Invariants`)
*   **Discrepancy Description:** La excepción (auditoría de lanzadores con rutas y líneas) es más larga que la invariante y la convierte en bitácora.
*   **Rationale:** Degrada el escaneo de una sección de contrato.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Mismo arreglo que el hallazgo anterior: la invariante queda declarativa y el defecto se mueve a «Problemas conocidos».
*   ***Proposed Edit:***
    *   Location: 63-70
    *   Change: Dejar solo «Las rutas y preferencias del usuario no están fijadas en el código: perfil = hechos en BD, filtros = `site_config`, credenciales = keyring de Windows.» y mover el resto.

### Terminología del blueprint no coincide con el manual [`style`] - Severity: Medium
*   **Affected Scope:** [8-14](README.md#L8-L14), [25](README.md#L25), [73](README.md#L73) vs [274-350](README.md#L274-L350), [625](README.md#L625), [769-789](README.md#L769-L789)
*   **Discrepancy Description:** Blueprint: «Paso 5», «análisis por reglas», «re-análisis», «corrida», «UI v2». Manual: «analysis extract», «busqueda», «reanaliza», «run start/site-result/finish», «interfaz Tkinter», «aplicación».
*   **Rationale:** Dos vocabularios para los mismos conceptos.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Válido; el manual es heredado, así que se fija el vocabulario en un bloque de terminología en el blueprint en lugar de reescribir 700 líneas.
*   ***Proposed Edit:***
    *   Location: tras `## System Overview`
    *   Change: `## Terminología` con tabla canónica: `Paso 5` = `matching`/`job_match`; `corrida` = fila de `job_match`/`source_runs` con `corrida_id`; `análisis` = `job_analysis`; `re-análisis` = reejecución tras IA o cambio de texto; `UI v2` = única interfaz gráfica (el manual la llama «interfaz Tkinter»/«aplicación»).

### Categorías de plataformas presentadas como exhaustivas [`style`] - Severity: Medium
*   **Affected Scope:** [26-27](README.md#L26-L27)
*   **Discrepancy Description:** «`cinde` y `procomer`… y `ane`, `indeed`, `linkedin`…» y «tableros ATS» se leen como listas completas de transporte.
*   **Rationale:** Hay 14 fetchers con transportes mixtos.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Precisión: `FETCHERS` mapea 14 plataformas; el ATS group incluye API/RSS, no un único mecanismo.
*   ***Proposed Edit:***
    *   Location: 26-27
    *   Change: «incluyen» en lugar de «y»; cerrar con «Los adaptadores combinan API pública, RSS y navegador (este último requiere CDP).»

### La sección de efectos secundarios mezcla archivos, rutas y transportes [`style`] - Severity: Low
*   **Affected Scope:** [76-87](README.md#L76-L87) (`## Global Side Effects`)
*   **Discrepancy Description:** Bajo «Archivos» hay directorios (`data/usuario/sesiones/`) y «documentos en `docs/`»; bajo «Red» hay un componente («cliente IA») y un protocolo («IMAP»).
*   **Rationale:** Categorías inconsistentes.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Arreglo barato y verificable.
*   ***Proposed Edit:***
    *   Location: 76-87
    *   Change: Renombrar viñetas a «Archivos escritos», «Directorios y cachés», «Procesos», «Red (peticiones salientes)» con verbos concretos.

### Los comandos de verificación no declaran el intérprete [`style`] - Severity: Medium
*   **Affected Scope:** [89-97](README.md#L89-L97) (`## System Verification`)
*   **Discrepancy Description:** Se dice «corre en el python del sistema» pero los comandos empiezan con `python`, sin advertir que **no** debe usarse el venv.
*   **Rationale:** Es la distinción central del contrato y se puede ejecutar mal.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Válido y de una línea.
*   ***Proposed Edit:***
    *   Location: 91-93
    *   Change: «Ejecutar **fuera** de `.venv` (el venv no incluye `pytest`): `python -m pytest …` con el intérprete del sistema.»

### Prosa compacta en el capítulo de UI del manual [`style`] - Severity: Medium
*   **Affected Scope:** [161-259](README.md#L161-L259)
*   **Discrepancy Description:** Filtrado, salario, CSV, edición de fuentes, seguimiento, importación de CV, comparación de perfil, evidencia, compatibilidad y administración de fuentes se comprimen en párrafos continuos.
*   **Rationale:** Dificulta localizar un control.
*   ***AI Suggestion:*** DECLINE
*   ***Justification:*** El capítulo es documentación histórica preservada (además describe la UI clásica retirada, ver Blocker 1). Reestructurarlo es un proyecto editorial aparte y el riesgo de perder detalle es alto; el Blocker 1 ya marca la sección como histórica y redirige a la UI v2.
*   ***Proposed Edit:*** Ninguno (cubierto por el Blocker 1).

### Secciones ATS repiten el mismo boilerplate [`style`] - Severity: Medium
*   **Affected Scope:** [325-518](README.md#L325-L518)
*   **Discrepancy Description:** Workday, Greenhouse, Ashby, Lever, Recruitee, Workable y SuccessFactors repiten registro, ejecución y «la UI permite…».
*   **Rationale:** Las diferencias reales quedan enterradas.
*   ***AI Suggestion:*** DECLINE
*   ***Justification:*** Mismo criterio: manual heredado; el contrato del paquete ya consolida los ATS en una fila (`src/jobpulse_v15/README.md`) y `tools/`/`cli --help` son la referencia operativa. Consolidar aquí duplicaría trabajo ya hecho en la capa de contrato.
*   ***Proposed Edit:*** Ninguno.

### El material de Workday está partido entre secciones [`style`] - Severity: Medium
*   **Affected Scope:** [325-357](README.md#L325-L357), [520-548](README.md#L520-L548)
*   **Discrepancy Description:** «Consulta explícita de tableros Workday» termina en 357, pero su normalización de ubicaciones continúa bajo SuccessFactors.
*   **Rationale:** Encabezado engañoso.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Arreglo pequeño y de bajo riesgo: basta un encabezado propio para la normalización.
*   ***Proposed Edit:***
    *   Location: línea 520
    *   Change: Insertar `## Normalización de ubicaciones (Workday y catálogo CR)` antes del bloque de `location normalize-workday`, con nota de que `location normalize --platform` aplica a todas las plataformas.

### Encabezado sin contenido y bloque de instalación mal ubicado [`style`] - Severity: Medium
*   **Affected Scope:** [260-269](README.md#L260-L269)
*   **Discrepancy Description:** Un párrafo termina en «con su estado, conteos y errores:» y el bloque siguiente solo reinstala el paquete y lanza la UI.
*   **Rationale:** El bloque no ilustra lo anunciado.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Válido; el comando correcto existe (`run start`/UI).
*   ***Proposed Edit:***
    *   Location: 260-269
    *   Change: Sustituir el bloque por el comando que muestra el historial de la fuente, o quitar los dos puntos y el bloque.

### Prosa repetida en la gestión de fuentes [`style`] - Severity: Low
*   **Affected Scope:** [558-603](README.md#L558-L603)
*   **Discrepancy Description:** Se solapa con la descripción de corridas por sitio de la sección ATS.
*   **Rationale:** Redundancia.
*   ***AI Suggestion:*** DECLINE
*   ***Justification:*** Nit en manual heredado; el coste de reestructurar supera el beneficio y el contenido es correcto.
*   ***Proposed Edit:*** Ninguno.

### Semántica de búsqueda repartida en párrafos largos [`style`] - Severity: Medium
*   **Affected Scope:** [684-767](README.md#L684-L767)
*   **Discrepancy Description:** AND de criterios, niveles de requisito, escape SQL, formatos, orden, fechas, motivos de revisión, compatibilidad de perfil, descartes manuales y comportamiento Workday se mezclan.
*   **Rationale:** Cada párrafo combina varios comportamientos configurables.
*   ***AI Suggestion:*** DECLINE
*   ***Justification:*** Manual heredado; el detalle operativo vive en `search --help` y en el contrato del paquete. Reorganizarlo es editorial, no correctivo.
*   ***Proposed Edit:*** Ninguno.

### La descripción del extractor mezcla el inicial con el actual [`style`] - Severity: Medium
*   **Affected Scope:** [769-789](README.md#L769-L789)
*   **Discrepancy Description:** «Extractor inicial» y `rules-1` conviven con el flujo vigente «análisis por reglas → IA → re-análisis».
*   **Rationale:** Se lee como si `rules-1` siguiera activo.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Coincide con el hallazgo de `codebase_details` sobre `rules-2`; un solo arreglo resuelve ambos.
*   ***Proposed Edit:***
    *   Location: 769
    *   Change: `## Extractor de requisitos` + «Versión vigente `rules-2` (`analysis.py`); el análisis integrado con campos de la fuente es `rules-2+fuente` (`analysis_flow.py`).»

### Detalle personal y operativo excede el registro de contrato [`style`] - Severity: Low
*   **Affected Scope:** [3-4](README.md#L3-L4), [31](README.md#L31), [35](README.md#L35), [53](README.md#L53), [65-70](README.md#L65-L70), [78-83](README.md#L78-L83)
*   **Discrepancy Description:** Rutas personales, referencias a líneas internas y notas incidentales («tabla que ninguna migración crea»).
*   **Rationale:** Mezcla invariantes con diagnóstico local.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Se resuelve con la sección «Problemas conocidos» propuesta arriba; la nota de `source_sites_review_log` se conserva allí porque es un hallazgo de deriva real.
*   ***Proposed Edit:***
    *   Location: 31 y 65-70
    *   Change: Mover a `### Problemas conocidos` (ver Blocker/Major de rutas).

### Falta un glosario de términos del proyecto [`comprehension`] - Severity: Medium
*   **Affected Scope:** [3](README.md#L3), [12](README.md#L12), [25](README.md#L25), [26-27](README.md#L26-L27), [31](README.md#L31), [65](README.md#L65), [73](README.md#L73), [86](README.md#L86), [328](README.md#L328), [354](README.md#L354)
*   **Discrepancy Description:** `EGM "Hay"`, `CDP`, `ATS`, `CR`, `corpus`, `taxonomía`, `viabilidad`, `keyring`, `IMAP`, `tenant`, `IngestionService`, `VACUUM`, `payload` se usan sin expansión ni definición. `ATS` además choca con «ranking ATS» (concepto distinto).
*   **Rationale:** Un lector sin contexto institucional no puede resolver el vocabulario.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Válido y de alto valor: el repo declara que el README sirve a agentes IA sin contexto previo.
*   ***Proposed Edit:***
    *   Location: tras `## Terminología` (nueva sección del arreglo de estilo)
    *   Change: Expandir en la tabla: CDP = Chrome DevTools Protocol; ATS = Applicant Tracking System (y «ranking ATS» = puntuación propia, distinta); CR = Costa Rica; corpus = BD SQLite local `data/jobpulse_v15.db`; taxonomía = registro de conceptos que asigna `codigo_canonico`; viabilidad = banda de ajuste técnico (no probabilidad de contratación); keyring = Administrador de credenciales de Windows; IMAP = protocolo del buzón de `postulaciones`; tenant = espacio de empresa en la URL de Workday; `IngestionService` = capa única de ingesta/validación; VACUUM = compactación de SQLite; payload = respuesta cruda de la fuente; EGM «Hay» = convención de contratos por directorio del bundle EGM.

### El orden del pipeline se enuncia pero no se justifica [`comprehension`] - Severity: Medium
*   **Affected Scope:** [11](README.md#L11), [23-30](README.md#L23-L30), [25](README.md#L25)
*   **Discrepancy Description:** No se explica por qué el orden es obligatorio, qué hace `backfill`, qué produce una «corrida nueva» del Paso 5 (tabla, estados) ni qué son las «áreas marcadas en el perfil»; tampoco hay una secuencia de comandos ejecutable de las 7 etapas.
*   **Rationale:** Sin la razón, el orden parece arbitrario y se puede romper.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Válido; los hechos están en `AGENTS.md` y `pipeline.py` y basta resumirlos.
*   ***Proposed Edit:***
    *   Location: tras la línea 14
    *   Change: Añadir 4 viñetas: (1) sin re-análisis los campos IA no se integran; (2) `backfill` rellena `job_requirements.codigo_canonico` (solo vacíos) y sin código el motor **ignora** el requisito; (3) el Paso 5 escribe una corrida nueva en `job_match` (la anterior `valida=0`) con estados `calificada`/`revisar_a_mano`/`descartada`/…; (4) «áreas» = clasificación de `job_area` desde `seeds/areas.json` (`init-areas`, `areas classify`); y el comando único: `run_full_flow.py`.

### Blueprint y manual son dos documentos sin transición [`comprehension`] - Severity: Medium
*   **Affected Scope:** [1-99](README.md#L1-L99) vs [99-114](README.md#L99-L114)
*   **Discrepancy Description:** Tras un `---` seco cambia la voz y el alcance; nada dice qué parte es autoritativa ni si el manual describe la misma v1.5.
*   **Rationale:** El lector no sabe a cuál creer en caso de conflicto.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Válido.
*   ***Proposed Edit:***
    *   Location: tras la línea 99
    *   Change: «> **Jerarquía:** las secciones de arriba son el contrato vigente (manda en caso de conflicto). Lo que sigue es el manual funcional heredado de la fase de arranque; se conserva por su detalle operativo y puede citar interfaces ya retiradas.»

### Prerrequisitos de los dos Pythons insuficientemente especificados [`comprehension`] - Severity: Medium
*   **Affected Scope:** [18-19](README.md#L18-L19), [91-97](README.md#L91-L97), [116-129](README.md#L116-L129), [550-556](README.md#L550-L556)
*   **Discrepancy Description:** No se dice cómo instalar `pytest` en el intérprete del sistema, qué versión usar, ni qué hacer si `python` resuelve a otro intérprete; el `.bat` instala además chromium de Playwright sin explicarlo.
*   **Rationale:** Un lector nuevo no puede poner la verificación en marcha.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Válido; son datos verificables de `pyproject.toml` y del launcher.
*   ***Proposed Edit:***
    *   Location: tras la línea 97
    *   Change: `### Prerrequisitos` — app: venv con Python 3.11 (`py -3.11 -m venv .venv`); tests: intérprete del sistema con `pytest` (`py -3.11 -m pip install pytest`), porque pytest no es dependencia de runtime; chromium de Playwright es opcional, solo para scrapers de navegador.

### Los capítulos de ingesta no se conectan con el pipeline [`comprehension`] - Severity: Medium
*   **Affected Scope:** [274-548](README.md#L274-L548) vs [8-14](README.md#L8-L14)
*   **Discrepancy Description:** Se documentan 7 proveedores uno a uno sin declarar el contrato común (registro → sitio habilitado → `scrape` → análisis → matching) ni qué garantiza `IngestionService`; `location normalize --apply` no advierte que muta filas.
*   **Rationale:** El lector no ubica las piezas en el flujo global.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Válido; el contrato común está en `scraper.py` + `ingestion.py`.
*   ***Proposed Edit:***
    *   Location: tras la línea 274
    *   Change: Párrafo único con el flujo común y las garantías (registro de plataforma/sitio, sitio habilitado, import idempotente vía `IngestionService`, contadores de salud), y advertencia de que `--apply` en `location normalize` **escribe** `jobs.city` (respaldar antes).

### Inventario de efectos secundarios incompleto frente al manual [`comprehension`] - Severity: Low
*   **Affected Scope:** [76-87](README.md#L76-L87) vs [207-230](README.md#L207-L230)
*   **Discrepancy Description:** No lista los hechos de perfil/import history ni las filas de seguimiento de postulaciones; no dice dónde se configura el buzón de `postulaciones`.
*   **Rationale:** Se nombra un efecto (IMAP) sin la feature que lo posee.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Válido y pequeño.
*   ***Proposed Edit:***
    *   Location: 81-87
    *   Change: Añadir: escritura de `candidate_profile_facts` + `candidate_profile_imports` (importación de CV, con reversión) y de `postulacion`/`postulacion_senal` (seguimiento); credenciales del buzón en keyring/`.env`.

### Prerrequisito no documentado: el repo v1.x «congelado» [`comprehension`] - Severity: Low
*   **Affected Scope:** [35](README.md#L35), [38](README.md#L38), [103-104](README.md#L103-L104), [206](README.md#L206)
*   **Discrepancy Description:** Dos scripts apuntan a `D:\Proyectos\jobpulse_cr\...` sin explicar qué es ese repo, que es de solo lectura, ni qué hacer si no existe; «repo congelado», «legacy» y «la aplicacion actual» se alternan.
*   **Rationale:** El comando falla sin explicación en otra máquina.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Válido; unifica con el arreglo de rutas.
*   ***Proposed Edit:***
    *   Location: 35
    *   Change: Nota: «`D:\Proyectos\jobpulse_cr` es el repositorio v1.x **archivado** (solo lectura); estos scripts fallan si no existe — pásales una ruta explícita.» Un solo término: «repositorio v1.x archivado».

### El verificador no pudo cargar su persona y estándar [`comprehension`] - Severity: Low
*   **Affected Scope:** Bundle `assets/egm/agents/comprehension.md`, `assets/egm/resources/document_standards/zoom-out-standard.md`
*   **Discrepancy Description:** El sandbox denegó `external_directory`; los hallazgos se emitieron con criterios replicados en el prompt.
*   **Rationale:** Afecta a la calibración del rubric, no al documento.
*   ***AI Suggestion:*** DECLINE
*   ***Justification:*** Es una limitación de herramienta, no un defecto del README; se registra aquí y en el reporte final del loop.
*   ***Proposed Edit:*** Ninguno (nota de proceso).

---

## Estado de aplicación (ronda 1)

Aprobado por el usuario: **los 24 PROPOSE FIX**. Aplicados en `README.md`
(822 → 980 líneas). Los 6 DECLINE se mantienen sin cambios.

| Área | Cambio aplicado |
|---|---|
| Blocker 1 | Aviso `> **Histórico.**` en `## Interfaz de escritorio` + redirección a la UI v2 (6 pestañas) |
| Blocker 2 | Reescrito el párrafo de Workable: `jobs.md`/`jobs/view/<id>.md` por `urllib`, `country_query` sobre título+ubicación, `location_raw` sin `(multi-loc)`, `work_mode` desde `**Workplace:**` |
| Blueprint | Nueva sección `## Terminología` (tabla canónica + glosario de siglas), bloque «Por qué el orden no se puede alterar», `## Subsistemas y comandos no detallados aquí`, `### Prerrequisitos`, `### Problemas conocidos de los lanzadores` |
| Invariantes | Retirada la excepción de lanzadores de «General, no para mí» (movida a problemas conocidos); `tools/` documenta los 4 scripts que llaman `Database.initialize()` |
| Efectos secundarios | Reagrupados en archivos / directorios / datos de perfil y seguimiento / procesos / red, con IMAP y keyring explicados |
| Verificación | Se advierte ejecutar pytest **fuera** de `.venv`; se añade el comando por patrón |
| Transición | Nota de jerarquía blueprint vs manual tras el `---`; «Alcance de esta fase» reescrito en presente |
| Código | `rules-1` → `rules-2` (dos apariciones: ejemplo de `save_analysis` y sección del extractor) |
| Ubicaciones | Encabezado propio `## Normalizacion de ubicaciones (Workday y catalogo CR)`; `--apply` documentado como **mutante** (corrige ciudades basura, `corrected_cities`) y contadores de `normalize` separados de `normalize-workday` |
| Otros | `login_ane.py` (cierra solo el Brave que abrió), rutas personales → `<repo-v1x>`, bloque de instalación sustituido por `run list`/`run show`, nota de que «Esquema inicial» es solo el núcleo |

**Pendiente**: ronda 2 de revisión (no ejecutada; requiere confirmación del
usuario). Criterio de convergencia: 2 rondas limpias consecutivas; tope 5.

---

# Ronda 2

**Target:** `README.md` (1-1040 tras las reparaciones)
**Revisores:** `codebase_details` (**not run** — 3 fallos del proveedor) · `style` (**not run** — 3 fallos del proveedor) · `comprehension` (completed, 9 hallazgos)
**Total:** 9 hallazgos — 7 Major · 2 Nit. Aprobados y aplicados: **8 PROPOSE FIX + 2 Nits incorporados**.

> **Ronda NO limpia:** dos revisores quedaron `not run` por fallos del proveedor
> (HTTP 429 y «content safety screening is temporarily unavailable»). Sus dos
> lentes se compensaron con verificación mecánica propia: 27 subcomandos y sus
> flags, 43 rutas citadas, 7 estados de `job_match`, 5 bandas con umbrales, 2
> firmas de API (`save_analysis`, `search_jobs`), 4 límites numéricos, y
> homogeneidad de columnas en las 3 tablas.

## Hallazgos de `comprehension` (ronda 2)

| # | Hallazgo | Sev. | Verificación | Estado |
|---|---|---|---|---|
| 1 | Glosario no cubre el vocabulario load-bearing (scraper/fetcher, orquestador, evidencia, `codigo_canonico`, `educacion_no_confirmada`, Paso 7, huella, salud de sitios, idempotente) | Major | Confirmado: 9 términos añadidos a `## Terminología` | **Aplicado** |
| 2 | «Siete etapas» sin numerar; los bullets usan «el paso 3 / el paso 4» sin esquema; el Paso 5 es la etapa 6 | Major | Confirmado: `pipeline_metricas.ETAPAS` = `scrape, analisis, ia, reanalisis, backfill, paso5, evidencia` (`pipeline_metricas.py:55-63`). **Defecto introducido en la ronda 1** | **Aplicado** — flujo numerado `1 scrape → … → 7 evidencia` + nota de que el Paso 5 es la etapa 6 + aclaración de que `run_enriquecimiento.py` es un atajo, no un segundo re-análisis |
| 3 | ~20 referencias a «la UI» en presente fuera del capítulo marcado como histórico | Major | Confirmado: `review_reasons` no existe en `ui_v2`; «Agregar sitio» y «Exportar CSV» sí | **Aplicado** — nota de jerarquía con la regla «existe hoy → UI v2 / no existe → UI clásica retirada»; 5 referencias normalizadas a «UI v2»; «Calidad de datos», «Motivo de revisión» y `skip_automatic` marcados como UI clásica |
| 4 | «Paso 7» sin explicar (no está en el flujo de 7 etapas) | Major | Confirmado: es numeración de hitos del proyecto, no de etapas | **Aplicado** — entrada en `## Terminología` + fila de la tabla con su efecto (`bloqueo_real` / `no_bloqueo` / `dudoso`) y la regla de que nunca pisa un veredicto del motor |
| 5 | Los 5 comandos `enrich` sin mapear a función/etapa | Major | Confirmado | **Aplicado** — cada `enrich` ocupa su fila con «Qué hace / etapa»; `requirements-source` = etapa 4, `requirements-canonico` = etapa 5, `profile-canonico` = fuera del flujo |
| 6 | «Salud de sitios» sin definir; `review_required` nunca nombrado | Major | Confirmado | **Aplicado** — entrada en `## Terminología` (estados `ok`/`zero_results`/`error`/`requires_login`, regla de 3 ceros) + fila de la tabla |
| 7 | Prerrequisitos no separan chromium de Playwright y Brave con CDP | Major | Confirmado: `asegurar_brave(cdp_port)` y `puerto_cdp_configurado()` existen (`browser_manager.py:27,300`) | **Aplicado** — los dos componentes por separado, con el comando del CLI |
| 8 | «Idempotente» sin explicar su consecuencia operativa | Nit | Confirmado | **Aplicado** — entrada en `## Terminología` |
| 9 | `review_reasons` y «Calidad de datos»: dos vocabularios sin relación | Nit | Confirmado | **Aplicado** — se declara que los códigos son la forma actual del resumen clásico y quién los calcula (`repository.search_jobs`) |
| 10 | «Esquema inicial» describe un «núcleo» sin decir qué queda fuera | Nit | Confirmado | **Aplicado** — capítulo renombrado a «Esquema: tablas del núcleo (manual heredado)» + nota con los dos inventarios que particionan el esquema |

## Defectos detectados por verificación propia (no por los revisores)

| # | Defecto | Origen | Estado |
|---|---|---|---|
| A | Tabla de subsistemas con filas de 6 columnas frente a 5 de la cabecera | Ronda 1 (mío) | **Corregido** — nombre del subsistema replicado en cada fila de `enrich` |
| B | `credenciales list\|set\|...` rompía la tabla en 11 columnas (los `\|` no escapan dentro de *code spans*) | Ronda 1 (mío) | **Corregido** — reescrito como `` `credenciales` (`list`, `set`, …) `` |
| C | Glosario decía «consultado con `urllib`» cuando la dependencia real es `httpx[http2]` | Ronda 2 (mío) | **Corregido** — `httpx` añadida y `urllib` matizado |
| D | `RSS`, `Playwright`, `urllib` usados sin expandir | Ronda 2 (mío) | **Corregido** — añadidos al glosario |
| E | Errata `la_ui clásica` en un párrafo | Ronda 2 (mío) | **Corregido** |

## Estado del loop

- Rondas ejecutadas: **2**. Ninguna es «limpia» en el sentido estricto de la
  skill (ambas tienen revisores `not run` por fallos del proveedor).
- Convergencia (2 rondas limpias consecutivas): **no acreditada**.
- Tope: 5 rondas. Quedan 3.
- ~~Todo el trabajo queda **sin commitear**~~ → **commiteado y pusheado** en
  `39a55a0` (14 archivos, +2685/−55).

---

# Ronda 3

**Target:** `README.md` (1-1040 al lanzar; 1065 tras aplicar)
**Revisores:** `codebase_details` (completed, 11 hallazgos) · `style` (pendiente) · `comprehension` (pendiente)
**Total parcial:** 11 hallazgos — 2 Blocker · 7 Major · 2 Nit. Aprobados y aplicados: **9 PROPOSE FIX + 2 Nits**.

> Los tres revisores se despachan **secuencialmente y con prompt corto** (el
> prompt largo dispara el screening del proveedor), decisión del usuario en
> la ronda 3.

## Hallazgos de `codebase_details` (ronda 3)

| # | Hallazgo | Sev. | Verificación | Estado |
|---|---|---|---|---|
| 1 | «La UI v2 permite agregar tableros X … siempre tras confirmar» (6 pasajes) + ventana `Administrar fuentes` inexistente | **Blocker** | `ui_v2` no tiene alta de tableros (el único «Agregar» es `cuentas.py:381`, sitios con login); el único `confirmar` de `scraping.py` es el de IA externa; `Administrar fuentes`/`Consultar seleccionadas` existían solo en `ui.py:441,2561` | **Aplicado** — los 6 pasajes reescritos (alta por CLI `site add`, UI v2 solo ejecuta) + la ventana marcada como UI clásica |
| 2 | `Respaldar DB` (l. 315) y `Marcar revisada` (l. 791) no existen en `ui_v2` | **Blocker** | Ambos existían en la UI clásica (`ui.py:461,2570`); el de l. 791 estaba fuera del aviso histórico | **Aplicado** — ambos marcados como UI clásica con su equivalente CLI (`backup`, `site mark-reviewed`) |
| 3 | «Procesar» ejecuta **6 etapas sin `scrape`**; la tabla no daba comandos de las etapas 1-3 | Major | `scraping.py:411` → `("analisis","ia","reanalisis","backfill","paso5","evidencia")` | **Aplicado** — texto corregido + comandos de etapas 1-3 apuntando a la tabla «Local Interface» |
| 4 | `run_enriquecimiento.py` solo hace la mitad de la etapa 4; la justificación era errónea | Major | `reananalizar_tras_ia` llama solo a `reananalizar_con_campos_fuente` (no `reananalizar_texto_cambiado`, `analysis_flow.py:287,321`) | **Aplicado** — nota y fila de la tabla reescritas: hace el grupo «campos sin integrar», no el de texto cambiado |
| 5 | `viabilidad` **no lee `job_match`** | Major | `calcular_viabilidades` construye `EvaluadorPaso5` sobre `job_analysis` (`viabilidad.py:536-559`); `job_match` solo en un comentario | **Aplicado** — celda corregida: recalcula al vuelo; tablas `job_analysis`+`job_requirements`+`candidate_profile_facts` |
| 6 | `enrich work-mode` sin `[--apply]` (es dry-run por defecto) | Major | `cli.py:1377-1381` lo define; `cli.py:3299` → `"dry_run"` sin él | **Aplicado** — `[--apply]` añadido + aviso «Sin `--apply` es dry-run» |
| 7 | Versión vigente `rules-2+fuente`, no `rules-2` | Major | `analysis_flow.py:29` → `VERSION_ANALISIS = f"{EXTRACTOR_VERSION}+fuente"`; único llamador en producción `analysis_flow.py:382` | **Aplicado** — glosario, ejemplo de código (`save_analysis`) y sección «Extractor de requisitos» corregidos |
| 8 | Playwright nunca lanza Chromium | Major | Cero `.launch(` en `src/`; solo `subprocess.Popen` de Brave + `connect_over_cdp` (`browser_manager.py:181,216`). **Las citas del revisor no existían en el README**; sí eran engañosos el glosario (l. 89) y el prerrequisito (l. 208), **míos de la ronda 2** | **Aplicado (derivado)** — ambos reescritos: Playwright = solo cliente CDP, sin chromium propio; el `.bat` sí ejecuta `playwright install chromium` (`jobpulse-v15.bat:29`) pero el código no lo usa |
| 9 | No existe valor `OK` en motivos de revisión | Major | JSON `[]` y CSV `""` (`exports.py:70-72`); el `OK` era el render de la UI clásica (`ui.py:164`) | **Aplicado** — frase corregida con el comportamiento real de cada formato |
| 10 | Estados de `source_run_sites` incompletos (4 de 7) | Nit | `CHECK` de la migración 022: `running`, `ok`, `zero_results`, `error`, `skipped`, `unsupported`, `requires_login` | **Aplicado** — los 7 estados en la entrada de glosario |
| 11 | Omisiones: `scrape ane --revisitar`, `postulaciones list`, `search --solo-requisitos-obligatorios`, `ElempleoFetcher` | Nit | Existen en `cli.py:1137,1543,1287` y `scraper.py:30`; ausentes del README | **Aplicado** — fila nueva «Scraping por plataforma» (con Elempleo como CLI-less), `postulaciones list` y el flag de `search` |

## Defectos propios detectados al aplicar la ronda 3

| # | Defecto | Estado |
|---|---|---|
| F | Referencia colgante a «Esquema inicial» (renombrado en la ronda 2) | **Corregida** |
| G | Descripción imprecisa de `--solo-requisitos-obligatorios` (la escribí yo al añadirla) | **Corregida** contra `cli.py:1289-1292` («al menos un requisito obligatorio», no «sobre el resultado») |

## Hallazgos de `style` (ronda 3b)

26 hallazgos (13 Major · 13 Nit · 0 Blocker). **Todos verificados contra el
archivo/código: 0 DECLINE. Aprobados y aplicados: los 26** (decisión del
usuario en la puerta de la ronda 3b).

### Major (13)

| # | Hallazgo | Verificación | Estado |
|---|---|---|---|
| 1 | Cross-ref erróneo: «los comandos de las etapas 4 a 7 en *Subsistemas*» (la 6-7 están en *Local Interface*) | `run_paso5.py`, evidencia en la tabla de scripts de raíz (110-127); solo `enrich requirements-*` (4-5) en *Subsistemas* (235-236) | **Aplicado** — ahora el texto lista los comandos de las 7 etapas y dice dónde vive cada grupo (defecto **mío, ronda 3**) |
| 2 | Lista de pipeline sin `→ evidencia` (contrato de ingesta, l. 471) | El propio doc define 7 etapas canónicas | **Aplicado** |
| 3 | Tres redacciones contradictorias de quién abre Brave (l. 134 «verifica», l. 216 ps1 «que ya lo hace», l. 312 «abre») | `jobpulse-v15.bat:40-45` verifica y **abre si no responde** | **Aplicado** — las 3 unificadas |
| 4 | Ortografía: manual sin tildes vs blueprint con tildes; híbridos introducidos por las reparaciones («misma accion», «activó») | Confirmado | **Aplicado** — normalización mecánica de 227+17+25 reemplazos, protegida fuera de fences/código inline; etiquetas verbatim de la UI clásica se conservan sin tildes (verificadas en `ui.py:554,297`) |
| 5 | Muro de texto sin párrafos en «Interfaz de escritorio» (~60 y ~40 líneas) | Confirmado | **Aplicado** — 8 subsecciones temáticas |
| 6 | UI clásica en presente + contradicción «agregar tableros» (449-451) vs «alta es por CLI» (557+) | Confirmado | **Aplicado** — todo el bloque a pasado + nota «Hoy el alta es por CLI» |
| 7 | Repetición de «única interfaz»/6 pestañas (4×) | L. 71, 279, 351, 486 | **Aplicado** — la lista queda solo en el bloque jerárquico |
| 8 | Plantilla repetida 7× («El alta es de la CLI…») + «Las pruebas usan…» 5× | Confirmado | **Aplicado** — subida a «Consulta explicita de tableros ATS» introductorio |
| 9 | Duplicación blueprint↔manual (venv/pytest) | L. 189-196 ≡ 303-309 ≡ 779-784 | **Aplicado** — el manual remite a «System Verification» |
| 10 | Glosario sin aviso/oferta/vacante; «0 avisos» (81,250) vs «cero ofertas» (804) | Confirmado | **Aplicado** — fila nueva **aviso** + unificación a «0 avisos» |
| 11 | Typo «lo.describe» (l. 834) | Confirmado (defecto **mío, ronda 3**) | **Aplicado** |
| 12 | «Este filtro de busqueda» con antecedente ambiguo: mezcla `skip_automatic` con la omisión de detalle del adaptador Workday | Confirmado | **Aplicado** — dos afirmaciones separadas con sujeto nombrado |
| 13 | `pip install -e .` a secas contradice la regla `python -m pip` (l. 258) | Confirmado | **Aplicado** |

### Nit (13)

| # | Hallazgo | Estado |
|---|---|---|
| 1 | Solape de bandas en el 85 (`aplicar ≥85` / `revisar 80-85`) | **Aplicado** — `revisar` ≥80 y <85 (verificado contra `viabilidad.py:49-50,469-474`) |
| 2 | Ruta mezclada `data/backups\X.db` | **Aplicado** |
| 3 | Botón «Enriquecer» vs real «Enriquecer IA» (`scraping.py:124`) | **Aplicado** |
| 4 | Bloque `run_enriquecimiento.py` que se resume a sí mismo | **Aplicado** — última oración eliminada |
| 5 | Razonamiento de la suite pegado al comando individual (l. 198-200) | **Aplicado** — justificación movida al bloque de la suite, cifra unificada (~20-25 min) |
| 6 | Duplicados internos: `source_sites_review_log` (121 vs 267), `auditoria_db.py` (125 vs 131), idempotencia (477 vs 542), racha de 3 corridas | **Aplicado** — remisiones cruzadas, redacción unificada |
| 7 | «La UI clásica mostraba» dos veces en un párrafo (965-979) | **Aplicado** — comprimido |
| 8 | «nueva versión del extractor» + `Analizar seleccionada` sin marcar | **Aplicado** — «versión actual» + control marcado como retirado |
| 9 | «de la UI» ambiguo (l. 1062) | **Aplicado** — «`Max. resultados` de la interfaz» |
| 10 | «delata como basura» (l. 742) | **Aplicado** — «marca como inválidas» |
| 11 | «v1.5 incluye» en minúscula a inicio de párrafo | **Aplicado** — «El paquete incluye» |
| 12 | «Sin `sites` toma los activos» sin antecedente | **Aplicado** — «usa los sitios activos» |
| 13 | Párrafos fusionados (l. 332-333) | **Aplicado** |

### Defectos propios cazados durante la aplicación

| # | Defecto | Estado |
|---|---|---|
| H | Pase de tildes por stdin corrompió la codificación (`ubicaci?n` ×16, `ah?` ×1) | **Reparado** (pase de reparación; corrupción residual: 0) |
| I | 3 palabras sin tildes restantes en backticks (`Revertir ultima importacion`, `Motivo de revision`, `analisis → ia`) | **Correctas tal cual**: son etiquetas verbatim de la UI clásica (sin tildes también en `ui.py:554,297`) y nombres de etapa del orquestador |

## Hallazgos de `comprehension` (ronda 3c)

16 hallazgos (6 Major · 10 Nit · 0 Blocker). **Todos verificados contra el
archivo/código: 0 DECLINE. Aprobados y aplicados: los 16** (decisión del
usuario en la puerta de la ronda 3c). Nota: el sandbox bloqueó la lectura de
persona/estándar EGM (`external_directory`); auditó con los criterios del
prompt (mismo trato que en la ronda 1).

### Major (6)

| # | Hallazgo | Verificación | Estado |
|---|---|---|---|
| 1 | «Las migraciones solo modifican la ruta de base configurada» (l. 298-299) — frase incomprensible | Redacción original: no puede significar eso | **Aplicado** — «se aplican únicamente al archivo de BD configurado (por defecto `data/jobpulse_v15.db`); nunca tocan las bases de v1.x» |
| 2 | Instrucción en imperativo presente que remite al control retirado `Analizar seleccionada` (l. 465-468) | El sustituto vivo es `analysis extract --job <id>` («Local Interface»). Defecto parcial **mío, ronda 3b** (marqué el control como retirado sin cambiar el verbo) | **Aplicado** — la instrucción actual usa la CLI; el botón queda como historia |
| 3 | `perfil` sin fila en Terminología; su única narrativa de creación está en pasado en la sección UI clásica | grep: sin fila; `candidate_profile_facts` solo en líneas sueltas | **Aplicado** — fila nueva **perfil** (qué es, dónde vive, cómo se carga hoy) |
| 4 | «Retención»/«purga» referidas 4 veces (l. 177, 410, 840, 845) sin definir mecanismo | `ui_v2/data/retencion.py` existe; la política vive en `ui_config.json` | **Aplicado** — definición en «Global Side Effects»: oculta avisos antiguos, **nunca los borra** |
| 5 | Fuentes `harvie`, `cinde`, `procomer`, `elempleo` sin identificar | `harvie` = HeyHarvie API (`harvie.py`); `cinde` = `cindejobs.com` GraphQL (`cinde.py`); `procomer` = `talento.procomer.com` (`cli.py:305`); `elempleo` = `elempleo.com/cr` | **Aplicado** — 4 entradas nuevas en el glosario |
| 6 | Historia de credenciales incompleta (`data/empresas/*.json` vs keyring vs `credenciales`) | `credenciales set` → keyring (contraseña) + `data/empresas/credenciales.json` (metadatos) (`credenciales.py:126`, `ui_v2/data/cuentas.py:9`) | **Aplicado** — glosario «keyring» + «Global Side Effects» |

### Nit (10)

| # | Hallazgo | Estado |
|---|---|---|
| 1 | Flags sin contrato: `--no-notify`, `--solo-criticos`, `--confirmar-externo` | **Aplicado** — efecto de cada uno (verificado: `run_full_flow.py:154`, `ia_estado.CRITICOS`, privacidad IA externa) |
| 2 | «Firma de segunda persona» sin decir segunda respecto de quién | **Aplicado** — «persona distinta del autor de la regla/motor, para no autoconfirmar» (Terminología + subsistemas) |
| 3 | Bandas `veto`/`sin_datos` sin criterio | **Aplicado** — `veto` = fuera de área o requisito educativo bloqueante (`viabilidad.py:395,418`); `sin_datos` = sin requisitos evaluables (`:404,427`) |
| 4 | Ruta contradictoria `v1_5/data/jobpulse_v15.db` (l. 324) | **Aplicado** — `data/jobpulse_v15.db` relativa a la raíz |
| 5 | Placeholder `<repo-v1x>` nunca resuelto | **Aplicado** — resuelto en su primer uso (`D:\Proyectos\jobpulse_cr`) |
| 6 | `country_query` sin lugar de configuración | **Aplicado** — `site_config_json` del sitio (verificado: `greenhouse.py:72`, `cli.py:3136`) |
| 7 | Ejemplo `run start/site-result/finish` sin encuadrar | **Aplicado** — «registra una corrida a mano (p. ej. para pruebas); el scraping normal la registra solo» |
| 8 | `ejecutar_barrido` citado sin vía de invocación | **Aplicado** — «etapa `scrape` del orquestador: `run_full_flow.py` o botón «Procesar»» |
| 9 | `llama-server` sin definición en el glosario | **Aplicado** — entrada nueva (llama.cpp, lo arranca/apaga quien lo usa) |
| 10 | «Pase IA de CV» en presente sin ubicación actual (l. 316) | **Aplicado** — `cv_ia.py` existe pero **nada lo importa** fuera de tests: queda como módulo sin botón en la UI v2 |

### Defectos propios cazados durante la aplicación

| # | Defecto | Estado |
|---|---|---|
| J | Barrida final de tildes: 6 palabras sin tilde en prosa se escaparon de los pases 3b (`abria`, `postulacion`, `requeria`, `maximo`, `minima/retencion`, `nucleo`) | **Corregidas** (las de `retencion.py`/`postulacion*` en backticks son rutas/tablas y quedan tal cual) |

## Ronda 4

### Hallazgos de `codebase_details` (ronda 4a)

3 hallazgos (3 Major · 0 Nit · 0 Blocker). **Todos verificados contra el
código: 0 DECLINE. Aprobados y aplicados: los 3** (decisión del usuario).
Primer intento falló por cuota del proveedor; el reintento (protocolo: 1
reintento) funcionó.

| # | Hallazgo | Verificación | Estado |
|---|---|---|---|
| 1 | `health_status` (acumulado) confundido con `source_run_sites.status` (por corrida) | `migrations/001:22-26` y `022:41-45` (valores de `health_status`), `repository.py:514-567` (actualización por corrida) | **Aplicado** — la fila «salud de sitios» del glosario ahora describe los **dos campos** |
| 2 | El botón «Procesar» atribuido al scraping | `ui_v2/tabs/scraping.py:114-136,403-408`: «Procesar» = pipeline sin `scrape`; el scraping lo lanzan «Ejecutar grupo»/«Ejecutar seleccionados» | **Aplicado** — Elempleo atribuido a esas acciones (defecto **mío, ronda 3c**) |
| 3 | La UI v2 no ofrece alta de tableros ni consulta manual | `ui_v2/tabs/cuentas.py:107,381` (solo «Agregar sitio» con login); no hay alta de ATS ni consulta de tablero | **Aplicado** — el bloque de jerarquía lo dice: alta y consulta **solo por CLI** (defecto **mío, ronda 3b**) |

### Hallazgos de `style` (ronda 4b)

10 hallazgos (5 Major · 5 Nit · 0 Blocker). **Todos verificados leyendo los
pasajes citados: 0 DECLINE. Aprobados y aplicados: los 10**, con N3 acotado por
decisión del usuario (se recorta lo redundante del glosario, sin quitar las
entradas exigidas por `comprehension`).

#### Major (5)

| # | Hallazgo | Estado |
|---|---|---|
| 1 | Tabla de subsistemas con celdas desiguales | **Aplicado** — filas «Viabilidad» divididas en 3 (comando / bandas / filtro de áreas) y fila propia para Elempleo |
| 2 | Repetición del contrato de los 7 tableros ATS | **Aplicado** — tabla «Contrato común» (consulta, alta, filtrado, persistencia, corridas, modalidad) + cada proveedor queda con sus **variantes** |
| 3 | Muros de texto en la interfaz heredada | **Aplicado** — «Filtros de fecha…» pasa a tabla (Control/Comportamiento/Excepción); el resto a viñetas |
| 4 | Bloque CLI entrelazado de párrafos (963-1036) | **Aplicado** — fragmentos sueltos («Muestra», «por») unidos y bloques separados |
| 5 | Repetición de advertencias sobre la UI clásica (8 sitios) | **Aplicado** — regla de lectura única en el bloque de jerarquía; avisos posteriores reducidos a «UI clásica (retirada)» + vía vigente |

#### Nit (5)

| # | Hallazgo | Estado |
|---|---|---|
| 1 | Redundancia entre el resumen de etapas y la tabla de scripts | **Aplicado** — el resumen pasa a tabla de 7 etapas |
| 2 | Exceso de negrita («mostraba», «permitía», «podían») | **Aplicado** — negrita reservada a términos de interfaz, estados, rutas y advertencias |
| 3 | Glosario sobredimensionado | **Aplicado (acotado)** — se quitan `httpx` y `urllib` (ya explicados en «API pública»); se conservan el resto, incluidas las entradas exigidas por `comprehension` (CINDE, Elempleo, Procomer, harvie, keyring, llama-server) |
| 4 | Degradación entre documento vigente y manual heredado | **Aplicado** — «## Documentación funcional» → «## Manual funcional heredado» + nota de estado |

### Defectos propios cazados durante la aplicación

| # | Defecto | Estado |
|---|---|---|
| K | La tabla «Contrato común» (M2) llevaba un pipe sin escapar en `api\|rss` → rompía la tabla (columnas 4/5) | **Corregido** antes de cerrar la ronda |
| L | 6 palabras sin tilde en prosa (`abría`, `postulación`, `requería`, `máximo`, `mínima/retención`, `núcleo`) | **Corregidas** |
| M | Dos bloques con el mismo nombre «Contrato común» (todos los fetchers vs. 7 tableros) | **Desambiguado** — el nuevo pasa a «Contrato común de los tableros ATS» |
| N | Typo `platforma` en 2 entradas nuevas del glosario | **Corregido** |
| O | 3 palabras sin tilde en prosa (`existian`, `categoria` ×2) | **Corregidas** |
| P | **Encabezado con caracteres CJK** (`首选`) al dividir la fila de Viabilidad | **Corregido**; barrido: 0 caracteres CJK en README e informe (lo cazó `comprehension`, ronda 4c) |

### Hallazgos de `comprehension` (ronda 4c)

2 hallazgos (2 Major · 0 Blocker). **Ambos verificados: 0 DECLINE. Aplicados los 2.**

| # | Hallazgo | Verificación | Estado |
|---|---|---|---|
| 1 | Encabezado corrupto «Viabilidad —首选 área» (l. 254) | **Defecto mío de la ronda 4a**: al dividir la fila de Viabilidad se colaron caracteres CJK | **Corregido** — «Viabilidad — filtro de áreas»; barrido defensivo: 0 caracteres CJK en README e informe |
| 2 | «Datos guardados y aprobados del perfil» sin definir qué es «aprobado» | `candidate_profile_facts` **no tiene columna de aprobación** (`016_areas.sql:56-85`): solo `origin` (`manual`/`imported`); la revisión ocurre antes de guardar | **Corregido** — «los hechos guardados del perfil (la importación ya pasó por revisión antes de guardarse, así que no hay un estado «aprobado» aparte)» |

### Resumen de la ronda 4

- `codebase_details` (3 Major) · `style` (5 Major + 5 Nit) · `comprehension` (2 Major) = **15 hallazgos, 0 Blocker, 0 DECLINE, 15 aplicados**.
- **Tendencia:** 31 → 8 → 53 → 15 hallazgos. La ronda 4 es la primera en la que **ningún revisor encontró un problema de fondo nuevo** (los 4 defectos de esta ronda eran míos: `health_status`, «Procesar», consulta de tableros y el encabezado CJK, todos introducidos en rondas 3b/3c/4a).

## Estado del loop tras la ronda 4

- Rondas ejecutadas: **4 de 5** (tope).
- Ninguna ronda ha salido «limpia» en sentido estricto (todas trajeron hallazgos, todos asentados).
- **Convergencia (2 rondas limpias consecutivas): no acreditada**, y con el tope en 5 ya no es alcanzable en sentido estricto.
- Trabajo de las rondas 1-2 commiteado en `39a55a0`; el de las rondas 3-5 se
  commiteó al cierre de la sesión del 2026-11-23 (`0ee82a5`).

## Ronda 5 (última, tope)

### `codebase_details` (5a)

- **Intentos 1 y 2**: fallos del proveedor (cuota agotada; después, el subagente
  terminó sin emitir informe).
- **Intento 3**: reintento sobre la misma sesión → informe entregado.
- Resultado: **3 hallazgos (1 Blocker + 2 Major). Los 3 verificados contra el
  código: 0 DECLINE, aplicados los 3.**

| # | Hallazgo | Verificación | Estado |
|---|---|---|---|
| 1 | **Blocker** — el README afirmaba que `search --format csv` produce «el mismo CSV que la UI v2». **Falso** | La UI v2 tiene **dos** CSV propios: `ui_v2/data/jobs.py:271` (datos crudos) y `ui_v2/data/vacantes.py:342` (ranking ATS); **ninguno** lleva `compatibilidad_perfil` ni `motivos_revision`. Esas columnas solo existen en `exports.write_job_search_csv` (`exports.py:45-47`), que la UI v2 nunca invoca | **Corregido** — se describe el export propio de la CLI y se aclara que las dos exportaciones de la UI v2 son distintas, sin equivalencia de esquema |
| 2 | **Major** — la fila «Filtrado» del contrato común prometía `<country_query> (multi-loc)` y filtro por título a los **7** adaptadores | `multi-loc` existe solo en **3**: `ashby.py:130`, `lever.py:131`, `recruitee.py:136`. Greenhouse solo mira `location.name` + oficinas (`greenhouse.py:104-125`); SuccessFactors guarda `location_raw = country_query` (`successfactors.py:139`); Workday normaliza con `ubicaciones_cr` (`workday.py:224`); Workable no fabrica el marcador (`workable.py:85`) | **Corregido** — la fila «Filtrado» queda solo con lo común (filtro por `country_query`, oferta omitida si no aparece); nota nueva con el comportamiento de los 4 restantes; el marcador se documenta en las subsecciones de Ashby, Lever y Recruitee |
| 3 | **Major** — `review_required` «se activa tras 3 corridas con 0 avisos» | **Tres** disparadores: `error` (`repository.py:518`), `requires_login` (`repository.py:532`) y la racha de ceros (`repository.py:538-562`); `site list --needs-review` filtra por `review_required = 1` (`repository.py:312`); `mark_site_reviewed` (`repository.py:277-282`) limpia la bandera y reinicia la racha pero conserva `health_status`; una corrida correcta limpia la bandera (`repository.py:564-568`) | **Corregido** en el glosario y en la tabla de subsistemas, con los tres disparadores y el efecto de `mark-reviewed` |

### `style` (5b)

- **Un solo intento**: informe entregado.
- Resultado: **30 hallazgos (18 Major + 12 Nit). Los 30 verificados y
  aplicados (0 DECLINE).**

| Grupo | Hallazgos | Verificación / corrección |
|---|---|---|
| Errores factuales | `--revisitar` documentado con `--dias` (el flag real es `--limite`); «los 7 adaptadores» ignoraba harvie; «activar o pausar sitios» aparecía como capacidad retirada (sigue en la UI v2); remisión «ver «Local Interface»» a una sección que no documenta `analysis extract` | `scrape ane --help`: `--dias` = ventana del listado, `--limite` = tope del re-barrido. `run_ats_scrapes.py` incluye harvie en `PLATFORM_ORDER`; `ui_v2/tabs/configuracion.py:1410-1443` activa/pausa sitios; el comando se documenta en «Extractor de requisitos». **Los 4 corregidos** |
| Jerga sin definir | `<country_query> (multi-loc)` usado 5 veces sin definir; «export controlado» sin definir | `exports._safe_csv_cell` neutraliza fórmulas (`=`, `+`, `-`, `@`): se definió el marcador (texto literal en `location_raw`, no es ciudad) y el export |
| Repetición / consistencia | regla de salud enunciada 4 veces; dos blockquotes seguidos idénticos; `mark-reviewed` descrito distinto en 2 sitios; tiempos verbales mezclados en el manual | Glosario reducido a definición + remisión; segundo blockquote eliminado; los dos enunciados de `mark-reviewed` unificados; tabla de filtros y «Postulaciones» pasadas a pretérito |
| Claridad | etiqueta «Variantes:» ×7 para contenido que no son variantes; «consulta» con dos sentidos (lanzar vs. mostrar); heurística `ciudad_es_basura` opaca; «Respalda la base» sin sujeto; `last_seen` mal descrito | «Variantes:» → «Comportamiento:»; «lanzar el scrape» vs. «mostrar los resultados»; criterio de `ciudad_es_basura` descrito (Costa Rica, `_`, dígitos, país, empresa, provincia+zona); respaldo atribuido al operador con `backup --output`; orden descendente explícito |
| Nits | «Numeração» (portugués); «un API» ×4; «la interfaz» ambiguo; Playwright duplicado; sección que solo remite; números de línea en la cita; «siempre» desmentido 3 líneas después; «solo lectura» que escribe; frase con dos predicados; etiquetas de estado inventadas; formulación telegráfica | **Los 12 corregidos** |

**Defecto propio cazado al aplicar:** `Respaldá` (voseo rioplatense) → `Respalda`,
corregido antes de la verificación final.

### `comprehension` (5c)

- **Un solo intento**: informe entregado.
- Resultado: **13 hallazgos (10 Major + 3 Nit). Los 13 verificados y
  aplicados (0 DECLINE).**

| # | Hallazgo | Verificación / corrección |
|---|---|---|
| 1 | Contradicción UI/CLI: la transición decía que el scrape ATS era «solo por CLI», pero el manual y la sección ATS dicen que la UI v2 lo lanza | **Real**: `scraper.ejecutar_barrido` es la etapa `scrape` que usan UI v2 y orquestador. **Corregido**: «el alta» es solo CLI; «el scrape de sitios ya registrados» se lanza desde «Scraping» o por CLI |
| 2 | La justificación 4→5 decía que «no existen filas que normalizar» antes de la 4, pero la 2 ya crea requisitos | **Real**: la 4 añade requisitos nuevos que la 5 normaliza; invertirlo deja requisitos sin `codigo_canonico` (ignorados en silencio). **Reescrito** |
| 3 | No se aclaraba quién abre Brave en cada vía de scraping | **Verificado**: `scrape <plataforma>` y `run_scrapes.py` exigen CDP; `scraper.ejecutar_barrido` abre bajo demanda y cierra solo lo suyo (O7.2). **Añadido** párrafo «Quién abre Brave» con cada punto de entrada |
| 4 | `bloqueante`/`faltante`/`educacion_no_cumple` usados sin definir su escala | **Verificado** en `matching.py`: estados **por requisito** (la vacante tiene los suyos). **Añadida** la escala y el motivo |
| 5 | Dos «compatibilidades» sin distinguir (Paso 5 vs. `search`) y cabecera CSV mal descrita | **Verificado**: JSON `profile_compatibility`, CSV `compatibilidad_perfil` (mismos valores, cabecera distinta); es cálculo informativo del motor de búsqueda. **Corregido** y desambiguado |
| 6 | `normalize-workday` y `normalize` mezclados (payload/conflictos atribuidos al general) | **Verificado** en `cli.py:3060-3284`: `normalize-workday` lee `raw_payload` y cuenta `corrected_cities`/`skipped_conflicting_sources`; `normalize` lee `location_raw`/descripción y cuenta `filled_*`/`corrected_*`. **Separados** ambos contratos y enlazado `ubicaciones_cr` |
| 7 | `inferred` listado como estado de campo | **Verificado** (`001:159-193`): `inferred` es **nivel**; los estados de campo son `found`/`not_mentioned`/`unknown`/`ambiguous`. **Corregido** con los dos vocabularios ortogonales |
| 8 | «Umbrales del Paso 5» citados sin regla | **Verificado** en `matching.py:72-80` y `112-113`. **Añadida** la precedencia mínima (cobertura 0.60, puntaje 0.80, etc.) |
| 9 | Ciclo de vida de postulaciones y «purga» sin definir; tres almacenes sin jerarquía | **Verificado**: `postulacion` (vigente, FK `ON DELETE SET NULL`), `postulacion_senal`; `user_job_state`/`applications` (legado, cascada). **Aclarado** qué purga (`clean_run.py`) y qué sobrevive |
| 10 | Remisión a «Salud de sitios» sin sección | **Real**: es una fila de la tabla de subsistemas. **Corregida** la remisión |
| 11 | «0 avisos» ambiguo (¿nuevos?) y estados intermedios sin definir | **Verificado** en `repository.record_site_result`: solo `zero_results` incrementa; `ok` reinicia; `error`/`requires_login` no modifican. **Corregido** a `jobs_found = 0` |
| 12 | `ia-server.bat` «delega en el script homónimo» (no existe `ia_server.py`) | **Corregido**: `ia-server.bat` → `start_ia_server.py`; `instalar-modelo-ia.bat` → `instalar_modelo_ia.py` |
| 13 | «Procesar» ejecuta la etapa `ia` pero el texto solo atribuía el arranque del servidor a «Enriquecer IA» | **Verificado** en `pipeline.py:350`: la etapa `ia` llama `asegurar_servidor`. **Corregido**: cualquier ejecución con `ia` y proveedor local lo levanta |

### Resumen de la ronda 5

- `codebase_details` (3) · `style` (30) · `comprehension` (13) = **46 hallazgos,
  0 Blocker tras la corrección del CSV, 0 DECLINE, 46 aplicados**.
- **Tendencia:** 31 → 8 → 53 → 15 → **46**. La subida no indica regresión: la
  ronda 5 reescribió zonas nuevas (contrato ATS, export CSV, transición al
  manual) y los revisores auditaron esas zonas; 10 de los 13 hallazgos de
  `comprehension` fueron consecuencia directa de los cambios de la 5a/5b.

## Estado del loop tras la ronda 5

- Rondas ejecutadas: **5 de 5** (tope alcanzado).
- **Convergencia estricta (2 rondas limpias consecutivas): no acreditada.**
  Ninguna ronda salió sin hallazgos y el tope impide ya alcanzarla.
- **Estabilización:** la ronda 4 fue la primera sin problemas de fondo nuevos de
  los revisores (los 4 defectos eran del autor); la ronda 5 encontró un
  **Blocker real** (equivalencia CSV CLI↔UI v2 inexistente) y varios errores de
  contenido introducidos en las rondas previas, todos corregidos.
- **Cierre:** por **tope**, con verificación mecánica completa (tablas, enlaces,
  esquema 28, 7 valores de salud, 24 grupos de comando, default de BD). El README
  queda íntegro: **1187 líneas, 6 tablas homogéneas, 0 corrupción, 0 CJK**.
- **Loop cerrado el 2026-11-23** (sesión `HANDOFF_SESION_2026-11-23.md`).
  Trabajo de las rondas 1-2 commiteado en `39a55a0`; las rondas 3-5 y el
  `git mv` del informe de deriva, en **`0ee82a5`** (4 archivos, +840/−396).

### Verificación mecánica (ronda 5, independiente de los subagentes)

Barrido de `--help` y de esquema contra el README (el método que en la sesión
anterior detectó defectos que los revisores no vieron):

| Afirmación del README | Comprobación | Veredicto |
|---|---|---|
| Los 24 grupos de comando citados existen | `jobpulse-v15 --help` | ✅ los 24 aparecen |
| BD por defecto en `data/jobpulse_v15.db` (raíz del repo) | `db.py:32` (`parents[2]/data/jobpulse_v15.db`) y `schema-version` en vivo | ✅ el README acierta |
| Texto de ayuda del CLI | `cli.py:659` aún dice «por defecto usa `v1_5/data/jobpulse_v15.db`» | ⚠️ **defecto de CÓDIGO**, no del doc: el README documenta la ruta real; el help quedó obsoleto (no se toca: esta tarea es solo documentación) |
| Esquema vigente = 28 | `schema-version` en la BD real | ✅ |
| `source_run_sites.status` con 7 valores | `001:116-119` + `022:76` | ✅ |
| `source_sites.health_status` con 7 valores | `001:22-26` + `022:41-45` | ✅ |



