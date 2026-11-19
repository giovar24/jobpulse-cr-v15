# data (capa de datos de la UI v2)

> Stores **sin Tkinter** que envuelven `Repository` y devuelven modelos de
> vista planos (dataclasses), para poder probar la lógica sin abrir ventana.

**Tipo:** Peanut (contrato de directorio hoja)
**Padre:** [`../README.md`](../README.md)

## Propósito

Separar la UI de la persistencia. Las pestañas de
[`../tabs/`](../tabs/README.md) no hablan con SQLite: hablan con un **store**
que recibe el `Repository` (o el dominio puro, en el caso de cuentas y
retención) y devuelve dataclasses o diccionarios planos. Cambiar el esquema o
la consulta no obliga a tocar los widgets, y la lógica se testea sin ventana.

## Interfaz pública

`__init__.py` re-exporta **solo** los nombres de `jobs` y `profile` (los usan
más consumidores). El resto de módulos se importa por su ruta completa.

### `jobs.py` — avisos crudos

| Símbolo | Contrato |
|---|---|
| `RawQuery(texto="", plataforma="", solo_con_descripcion=False, limite=5000)` | Filtros de la pestaña "Datos crudos". |
| `RawRow` | Una fila cruda: identidad, ubicación, condiciones, salario, `skills`/`languages`, plataforma, `source_url`, largos de texto, estado manual y `dup_of`. |
| `RawDetail` | `RawRow` + `description_raw`, `requirements_raw`, `sources`, `analysis_status`, `requirement_count`, `field_statuses`. |
| `JobsStore(repository, retencion_store=None)` | `load(query) -> list[RawRow]`, `detail(job_id) -> RawDetail \| None`, `platforms() -> list[str]`, `sources_count() -> int`. |
| `recortar(texto, largo=80)` | Texto de una línea con puntos suspensivos. |
| `idioma_texto(codigo)` | Nombre legible del código (`es`, `en`, `mixed`, `undetermined` → "Sin determinar"). |
| `ubicacion_texto(row)` / `salario_texto(row)` | Texto legible, prefiriendo el dato crudo de la fuente. |
| `resumen_por_campo(filas)` | `{total, con_descripcion, con_ubicacion, con_salario, con_requisitos, con_fecha}`; devuelve `{}` vacío si la entrada no tiene filas (`data/jobs.py:313-314`). |
| `estado_truncado(estado)` | Estado manual legible (`"—"` si viene vacío). |
| `CAMPOS_CSV` | Tupla de columnas exportadas por `exportar_csv`. |
| `exportar_csv(filas, ruta) -> int` | Escribe `CAMPOS_CSV` en UTF-8 con BOM; devuelve cuántas filas escribió. |

### `profile.py` — perfil del candidato

| Símbolo | Contrato |
|---|---|
| `ProfileStore(repository)` | `load(query)`, `resumen(hechos)`, `save(...)`, `delete(fact_id)`, `import_from_cv(path, *, texto=None)`, `import_facts(source_name, facts)`, `importaciones(*, limit=20)`, `revertir_ultima()`. |
| `ProfileQuery(texto="", categoria="")` | Filtros de la pestaña. |
| `ProfileFact` | Hecho tal como está en la base; propiedades `categoria_legible`, `nivel_legible`, `origen_legible`. |
| `ProfileResumen` | `total`, `importados`, `manuales`, `con_canonico`, `por_categoria`, `categorias_cubiertas`. |
| `CATEGORIAS` (14) / `ETIQUETAS_CATEGORIA` | Espejo de `repository.PROFILE_FACT_CATEGORIES`: `contact`, `summary`, `education`, `experience`, `project`, `skill`, `certification`, `language`, `license`, `work_authorization`, `schedule`, `availability`, `other`, `area`. |
| `ESTADOS_EDUCACION` (`""`, `completed`, `pursuing`, `unspecified`) / `NIVELES_CEFR` | Vocabularios de los campos de estado y de idioma. |
| `CATEGORIAS_CON_ESTADO = {education}` / `CATEGORIAS_CON_NUMERO = {experience}` | Solo esas categorías aceptan `education_status` y `numeric_value`. |
| `etiqueta_categoria`, `etiqueta_estado_educacion`, `origen_texto` | Etiquetas legibles. |
| `fact_desde_sugerencia(sugerencia)` | Convierte una sugerencia de CV en un Mapping guardable. |
| `exportar_csv(hechos, ruta) -> int` | Exporta `CAMPOS_CSV` (incluye `codigo_canonico`). |

### `vacantes.py` — ranking ATS + ajuste técnico

| Símbolo | Contrato |
|---|---|
| `AtsStore(repository, retencion_store=None)` | `perfil()`, `avisos(limite=5000)`, `areas_por_aviso()`, `areas_del_perfil()`, `estados_paso5()`, `calcular(*, limite=5000, progreso=None) -> list[VacanteAts]`. |
| `VacanteAts` | `score` (0-100), `veredicto`, componentes (`skills_pct`, `experiencia_pct`, `educacion_pct`, `idiomas_pct`), `skills_cubiertas`/`skills_faltantes`, `req_obligatorios`, `estado_paso5`, y el bloque de ajuste técnico (`ajuste`, `banda`, `veto`, `faltantes_obligatorios`); propiedades `banda_legible`, `veredicto_legible`, `tiene_score`. |
| `VEREDICTOS` (`fuerte`, `ajustable`, `debil`, `sin_datos`) y `BANDAS_VIABILIDAD` (`aplicar`, `revisar`, `no_prioritario`, `sin_datos`, `veto`) | Vocabularios; `ETIQUETAS_VEREDICTO` / `ETIQUETAS_BANDA` traducen. |
| `filtrar(filas, *, texto, veredicto, solo_mi_perfil, areas_perfil, solo_requisitos, banda, solo_aplicar)` | Filtros de presentación. |
| `resumen(filas)` / `resumen_bandas(filas)` | Conteos por veredicto ATS / por banda de ajuste. |
| `skills_de_aviso(valor)` | Lee `jobs.skills` (JSON o lista) y devuelve la lista de skills. |
| `exportar_csv(filas, ruta) -> int` | Exporta `CAMPOS_CSV` (score, veredicto, ajuste, banda, componentes, faltantes, url…). |

### `paso5.py` — matching persistido

| Símbolo | Contrato |
|---|---|
| `Paso5Store(repository)` | `analisis_obsoletos() -> int`, `corrida_vigente() -> str`, `estado_vigente() -> dict[job_id, estado]`, `ejecutar(*, aplicar_filtro_areas=True, progreso=None) -> ResumenPaso5`, `resumen_de_corrida(corrida_id)`. |
| `ResumenPaso5(corrida_id, evaluadas, conteo)` | `conteo` es una tupla `(estado, motivo, n)`; `por_estado` agrega por estado y `texto(maximo=20)` da el resumen legible estilo CLI. |

### `scraping.py` — selección de barrido

| Símbolo | Contrato |
|---|---|
| `ScrapingStore(repository)` | `sitios(grupo=None) -> list[SitioScrape]`, `grupos() -> list[str]`, `sitios_para_barrer(grupo=None) -> list[str]` (solo activos), `resumen(grupo=None) -> {total, activos, por_plataforma}`. |
| `SitioScrape` | `site_id`, `nombre`, `plataforma`, `grupos`, `activo`, `paginas` (de `site_config`). |
| `TODOS = "Todos los grupos"` | Valor centinela del filtro de grupo. |

### `fuentes.py` — sondas de scraping

| Símbolo | Contrato |
|---|---|
| `FuentesStore(repository)` | `sitios() -> list[SitioFila]`, `plataformas() -> list[str]`, `conteo() -> (activas, total)`, `alternar(site_ids, activo) -> int`. |
| `SitioFila` | `site_id`, `nombre`, `plataforma`, `tipo` (`api`/`rss`/`browser`), `grupos` (texto), `activo`, `revision` (`review_required`), `requiere_login` (derivado de `health_status == "requiere_login"`), `salud`. |

### `cuentas.py` — credenciales de login

| Símbolo | Contrato |
|---|---|
| `CuentasStore()` | `sitios() -> list[SitioCuenta]`, `resumen() -> dict`, `guardar(...)`, `borrar(empresa)`, `agregar(empresa, url, motivo, grupo, obligatorio)`, `quitar(empresa)`, `auto_login(empresa, valor)`. |
| `SitioCuenta` | Estado de un sitio que pide login **sin la contraseña**; `SitioCuenta.desde(item)` construye desde el dict de `credenciales`; propiedad `estado` → "Con credencial" / "Pendiente" / "Sin credencial". |

### `retencion.py` — vigencia (O8/O10)

| Símbolo | Contrato |
|---|---|
| `RetencionStore()` | `retencion() -> Retencion`, `solo_vigentes(datos=None) -> bool`, `guardar_meses(meses) -> Retencion`, `guardar_solo_vigentes(valor) -> bool`, `ventana_consulta() -> (solo_vigentes, meses)` — devuelve solo `(solo_vigentes, retencion.meses)`: la ventana de republicaciones no se expone por este helper ni la usa ninguna consulta de la capa (`data/retencion.py:100-103`). |
| `Retencion(meses, ventana_republicaciones, solo_vigentes, corte)` | Propiedad `texto_corte` ("vigentes desde el …"). `ventana_republicaciones` se carga pero no se usa en las consultas de esta capa. |
| `CLAVE_SOLO_VIGENTES = "solo_vigentes"` / `DEFAULT_SOLO_VIGENTES = True` | Preferencia en `ui_config.json`; por defecto se ocultan los avisos vencidos. |

## Invariantes

1. **Ningún módulo de este directorio importa `tkinter`.** Es la frontera que
   permite testear sin ventana.
2. **Los stores devuelven dataclasses o dicts planos**, nunca cursores ni filas
   de SQLite.
3. **El perfil es un singleton**: no hay `candidate_id`; los hechos viven en
   `candidate_profile_facts` y se identifican por `(category, value_code)`.
4. **`ProfileStore.save` SÍ escribe `codigo_canonico`.**
   `Repository.save_candidate_profile_facts` resuelve el código canónico **en
   el momento de guardar**, vía `conceptos.resolver`, y lo persiste
   (`repository.py:2784,2793,2802-2805,2835-2856`); lo mismo aplica a
   `ProfileStore.import_facts` (`data/profile.py:276`,
   `repository.py:3043-3047,3062-3065`). El motor del Paso 5 exige
   `codigo_canonico IS NOT NULL` para skill/idioma/educación: un hecho sin
   resolver sigue siendo invisible, pero la resolución ocurre al guardar, no
   como paso posterior. La UI lo muestra sin ocultarlo (columna "Canónico").
5. **La contraseña nunca se lee ni se devuelve** (`CuentasStore`): la UI solo
   puede escribirla; dejarla vacía significa "conserva la guardada".
6. **Retención = ocultar, nunca borrar.** `JobsStore` y `AtsStore` aplican
   `solo_vigentes` + `ventana_retencion_meses` al consultar.
7. **El score ATS es un ranking, no una calificación**: no toca los umbrales
   congelados del Paso 5 (cobertura 0.60 / puntaje 0.80) ni sus estados. Se
   calcula en **dos pasadas** (componentes por aviso → promedio del corpus →
   total con pesos fijos e imputación) porque un score sin imputación es
   degenerado (una vacante con un solo requisito cubierto sacaría 100).
8. **El ajuste técnico es otro índice**: `ajuste`/`banda`/`veto` vienen de
   `viabilidad` (¿el perfil cumple lo que el aviso pide?), no del ranking ATS.
   Un fallo al calcularlo deja la banda en `sin_datos`, no rompe el ranking.
9. **`Paso5Store.ejecutar` escribe una corrida NUEVA** (`invalidar_previas=True`);
   nunca hace `UPDATE` de la corrida anterior, que queda con `valida = 0`.
10. **`Paso5Store` abre su propia conexión `sqlite3` con `row_factory = Row`**
    y la cierra en `finally`: el worker corre en un hilo y `matching` indexa
    las filas por nombre de columna.
11. **`RetencionStore` valida contra `ciclo_vida.MESES_PERMITIDOS`**: un valor
    fuera de la lista es `ValueError` al guardar y cae al defecto al leer.
12. **La lista de grupos de `scraping.py` viene del repositorio.**
    `ScrapingStore` **no** usa `run_groups_json`: lee la lista ya parseada
    `run_groups` que devuelve `Repository.list_sites` (`data/scraping.py:38-41,55-60`),
    y el parseo del JSON ocurre dentro del repositorio
    (`repository.py:323,347`). Es la misma fuente que usa el CLI
    (`--group directos|cr-gov|cr-jobs`).

## Efectos secundarios

- **Lecturas de base**: `JobsStore`, `AtsStore`, `Paso5Store`, `ScrapingStore`,
  `FuentesStore` y `ProfileStore.load` consultan `Repository` (y, en `jobs`/
  `vacantes`, `repository.database.connection()` directo para el mapa de
  plataformas y las áreas; además `vacantes.py` ejecuta `SELECT` crudos sobre
  `job_match` para los estados de la corrida vigente
  (`data/vacantes.py:175-190`) y `jobs.py` consulta `source_sites` para su
  conteo de fuentes (`data/jobs.py:216-219`)).
- **Escrituras de base**: `ProfileStore.save/delete/import_facts/revertir_ultima`
  persisten en `candidate_profile_facts` (con snapshot para poder revertir);
  `Paso5Store.ejecutar` escribe `job_match`; `FuentesStore.alternar` cambia
  `source_sites.enabled`.
- **Escrituras de archivo**: `cuentas.CuentasStore.guardar/borrar` escriben
  metadatos en `data/empresas/credenciales.json` (gitignored) **y la contraseña
  en el Administrador de Credenciales de Windows** (keyring); `retencion`
  escribe `~/.jobpulse_v15/ui_config.json` vía `configuracion.guardar`.
- **Acceso externo**: `ProfileStore.import_from_cv` lee un PDF/DOCX/TXT local;
  `exportar_csv` escribe en disco.
- **Nada de red**: este directorio no hace peticiones HTTP.

## Dependencias

- `jobpulse_v15.repository.Repository` — acceso a la base.
- Dominio reutilizado: `areas`, `ats` (`componentes_ats`,
  `perfil_ats_desde_facts`, `promedios_componentes`, `ranking_ats`),
  `viabilidad.calcular_viabilidades`, `matching.ejecutar_paso5`,
  `analysis_flow.cuenta_analisis_obsoletos` /
  `reananalizar_con_campos_fuente`, `candidate_profile`, `credenciales`,
  `ciclo_vida`.
- UI propia: `ui_v2.configuracion` (persistencia de preferencias) y
  `ui_v2.i18n` (etiquetas de `vacantes.py`).

## Verificación

```powershell
python -m pytest tests/test_ui_v2.py -q
python -m pytest tests/ -q
```

Los tests importan los stores con bases temporales: no requieren red, perfil ni
credenciales. Para probar la lógica de un store sin montar widgets basta
construirlo con un `Repository` sobre una base temporal y llamar a sus métodos
de lectura.

## Documentos relacionados

- [`../README.md`](../README.md) — UI v2 completa (shell, tema, componentes).
- [`../tabs/README.md`](../tabs/README.md) — consumidores de estos stores.
- `AGENTS.md` — reglas de negocio del Paso 5, viabilidad y retención (O8/O10).
