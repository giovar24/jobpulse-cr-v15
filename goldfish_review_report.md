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
- Todo el trabajo queda **sin commitear**.

