# Handoff — Sesión 2026-11-03: **Ranking ATS (pestaña "Vacantes")**

## TL;DR

El usuario leyó el documento *"Arquitectura, Estándares de ATS"* (motor de
parseo + scoring tipo ATS) y pidió **simular un ATS**: dar un score a cada
vacante y mostrar, en una pestaña, **los empleos más aptos para el perfil de
la persona que tiene el CV cargado**.

Hallazgo clave: **el 80 % ya estaba escrito y dormido** en el repo
(`ats.py`, `search_engine.py` — sin callers; el gotcha 13 pedía "no borrar
sin redefinir O2/O4"). Esta sesión **cablea ese motor a la UI v2** y **calibra
el score contra el corpus real** (535 avisos) hasta que el ranking pone arriba
los avisos que de verdad encajan con el perfil (soporte TI).

- Nueva pestaña **"Vacantes"** en `src/jobpulse_v15/ui_v2/tabs/vacantes.py`
  (módulo + 1 línea en `PESTANIAS`, como manda `docs/UI_V2_ARQUITECTURA.md`).
- Nuevo store **sin Tk** `src/jobpulse_v15/ui_v2/data/vacantes.py`.
- `src/jobpulse_v15/ats.py` **extendido** (la API vieja queda intacta):
  perfil → ATS, cobertura de skills, `componentes_ats()`, `ranking_ats()`,
  `percentiles()`, `promedios_componentes()`.
- `src/jobpulse_v15/search_engine.py`: **dos bugs reales corregidos** (la caché
  nunca se guardaba y nunca se podía leer) + caché de títulos + texto
  normalizado.
- Cálculo pesado (embeddings) en **hilo de segundo plano** + caché en disco.
- Tests: `tests/test_ats_ranking.py` (**44 casos**) + 4 casos de la pestaña
  en `tests/test_ui_v2.py`. Suite completa: **592 tests + 204 subtests**
  (`python -m pytest tests/ -q`, ~1.4 min).

Decisiones del usuario (preguntadas): score principal = **requisitos reales +
semántica**; cálculo = **al abrir, en segundo plano + caché**.

## Lo que se hizo

### 1. Puente perfil → ATS (`ats.py::perfil_ats_desde_facts`)

Convierte los hechos de `candidate_profile_facts` al perfil que espera el
scoring. Verificado contra la BD real: **23 skills, 8 cargos, 16 años (el
fact `total` manda), nivel educativo 2 (el diplomado), idiomas
`{es: nativo, en: b2}`**. No depende de `codigo_canonico` (capa B pendiente):
el cotejo es por texto normalizado.

### 2. Cobertura de skills (`ats.py::cobertura_skills`)

Cotejo por **tokens con subconjunto**, con ruido de fabricante ("Microsoft
Excel" ≈ "Excel Avanzado") y alias ("Amazon Web Services" → AWS). Cada
**concepto cuenta una sola vez**: "Microsoft Excel" y "Excel avanzado" son la
misma competencia.

### 3. `componentes_ats()` + `ranking_ats()` — 5 componentes

| Componente | Peso | Fuente |
|---|---|---|
| Semántica (perfil ↔ aviso) | 35 % | percentil del corpus (embeddings locales) |
| Skills (gap) | 45 % | requisitos **obligatorios** ∪ skills **útiles** del aviso |
| Experiencia | 10 % | requisito `experience` (`minimum`, años) |
| Educación | 5 % | requisito `education` vs jerarquía del perfil |
| Idiomas | 5 % | requisito de idioma (regla del aviso) vs nivel del perfil |

Reglas duras heredadas del repo:
- **"Preferred" no bloquea**: no entra al denominador.
- **El idioma del aviso es el requisito de idioma** (lo aplica
  `Repository._requisitos_con_regla_de_idioma`; el store pasa los requisitos
  ya filtrados por esa regla).
- **Un componente sin dato NO penaliza**: en modo corpus se **imputa el
  promedio del corpus** (ni premia ni castiga) y los **pesos quedan fijos**
  → los avisos son comparables entre sí. (Redistribuir el peso hacía subir
  solos a los avisos con menos datos.)
- **El score es un RANKING, no una calificación**: no toca los umbrales
  congelados del Paso 5 (cobertura 0.60 / puntaje 0.80) ni sus estados.
- Veredictos (`UMBRALES_RANKING`): `>= 50` fuerte · `>= 42` ajustable ·
  resto débil · `sin_datos`. Calibrados sobre la distribución real
  (fuerte ≈ decil superior, ajustable ≈ primer tercio).

### 4. Fórmula semántica (calibrada, no inventada)

Se probaron 7 fórmulas sobre los 535 avisos con la detección estricta de los
26 avisos de soporte TI. Resultado (posición media de esos avisos):

| Fórmula | Posición media |
|---|---|
| **F5 = 0,65·coseno medio(cargos del perfil, TÍTULO) + 0,35·coseno medio(cargos del perfil, aviso completo)** | **28 / 535** ✅ |
| F7 = 0,5·F1 + 0,3·F2 + 0,2·F3 | 29 / 535 |
| F6 = 0,65·F1 + 0,35·F3 | 30 / 535 |
| F1 = solo títulos | 37 / 535 |
| F2 = solo documento | 81 / 535 |
| A/B/C/D (perfil completo o `max` entre cargos) | > 90 / 535 (basura) |

Doslearnings que cambiaron el código:
- **`max` entre los cargos del perfil es peor que la media**: un cargo
  aislado ("Customer Service Representative") enganchaba avisos de hotel.
- **El texto se codifica NORMALIZADO** (minúsculas, sin acentos): sin
  normalizar los avisos de soporte TI quedan en 59/535; normalizados, 37/535
  (`search_engine.normalizar_texto`).

El coseno crudo vive comprimido (0,1–0,6) → el componente usa el
**percentil dentro del corpus** (`ats.percentiles`), que reparte 0–100.

### 5. Ruido de `jobs.skills` (filtrado)

`jobs.skills` mezcla herramientas y frases de tarea ("elaborar cotizaciones",
"soporte a equipos Dell"). `ats.es_frase_de_tarea` descarta las frases de
tarea y las etiquetas de más de 3 palabras: de 3.962 skills del corpus quedan
2.475 útiles (62 %). El denominador del gap son los requisitos obligatorios
∪ las skills útiles del aviso; el numerador, las que cubre el perfil.

### 6. Store (`ui_v2/data/vacantes.py`)

`AtsStore.calcular(engine=...)` → lista de `VacanteAts` ordenada por score.
Trae también el área (`job_area`), el estado del **Paso 5** (si hay corrida
vigente) y el estado del análisis. Sin embeddings (modelo no disponible) el
score **igual sale**: solo el componente semántico queda `n/d`.

El cálculo va en **dos pasadas**: (1) componentes de cada aviso + promedio de
cada componente en el corpus; (2) score final con pesos fijos e imputación.

### 7. Pestaña "Vacantes" (`ui_v2/tabs/vacantes.py`)

Shell (sidebar + cabecera + contenido) + franja de 5 tiles + tabla (Score,
Veredicto, Puesto, Empresa, Área, Sem., Skills, Exp., Idiomas, Paso 5) +
panel de detalle con el desglose y **las skills que te faltan**. Filtros:
buscador, veredicto y "solo áreas de mi perfil". Export CSV.

El cálculo corre en **hilo de segundo plano**; los resultados llegan por una
`queue.Queue` y la UI solo se toca desde el hilo principal (`after`).

## Bugs reales encontrados y corregidos

1. **La caché de embeddings NUNCA se guardaba** (`search_engine.py`):
   `np.save` **agrega `.npy`** al nombre del temporal → se escribía
   `embeddings_cache.npy.tmp.npy` y el `replace()` fallaba. Cada arranque
   re-vectorizaba los 535 avisos (77–144 s).
2. **La caché de embeddings NUNCA se podía LEER**: el metadato se guarda como
   `{job_id: {...}}` pero el cargador buscaba `item["job_id"]` → `KeyError`.
   Las dos cachés ahora se versionan (`CACHE_VERSION`).
3. **El componente de idiomas daba 0 %**: en el corpus los requisitos de
   idioma vienen como `espanol` / `ingles` (no `es` / `en`), así que el perfil
   no casaba con ninguno. Se normaliza con `ats._codigo_idioma`.
4. **`import numpy as np` faltaba en `ats.py`** (NameError latente) y
   `Mapping` no estaba importado.
5. **La pestaña usaba `self.after(...)`**: la pestaña NO es un widget de Tk
   (es una clase normal con un marco) → `AttributeError` al abrirla. El
   `after` va por el marco (`VacantesTab._after`).

## Decisiones de diseño

1. **No se reimplementa lo que ya existe**: se extiende `ats.py` (API vieja
   intacta) y se reutiliza `search_engine.py` con su caché incremental.
2. **El skills usa los requisitos REALES, no el lexicon de `ats.py`**: el
   lexicon (inglés, genérico) no cubre Active Directory, ServiceNow, SCCM,
   Intune… del perfil real y daba "faltantes" falsos.
3. **Sin dependencias nuevas**: nada de spaCy/ChromaDB/FastAPI (el documento
   los propone; aquí no hacen falta: 535 avisos caben en un coseno en memoria
   y ya hay `sentence-transformers`).
4. **Sin migración de BD**: el score no se persiste (es regenerable). La
   capa B (`codigo_canonico` del perfil) sigue pendiente y **no bloquea** esta
   pestaña.
5. **Si no hay avisos, no se calcula** (guarda en `recalcular`): evita trabajo
   pesado en bases vacías y en los tests.

## Estado de objetivos (tabla)

| Objetivo | Estado tras esta sesión |
|---|---|
| **O2/O4 (búsqueda data-first / calibración)** | **Cerrados en lo funcional**: el motor semántico + el scoring ATS dejan de estar dormidos y se usan en la UI v2, con fórmula y pesos calibrados contra el corpus real |
| **O9 Optimización de UI** | **En curso**: tercera pestaña de la UI v2 (Datos crudos · Perfil · Vacantes) |
| O1 Enriquecimiento IA | Cerrado (sin cambios) |
| O3 Fetchers ATS huérfanos | Sin cambios |
| O5 Higiene de datos | Solo queda **O5.3** (re-barrido de descripciones basura) |
| O6 Perfil del candidato | O6.1–O6.3 cerrados; **O6.4** (dedupe de slugs ES/EN) pendiente |
| O7 UI-first | Completo (sin cambios) |
| O8 Ciclo de vida | O8.1 hecho; **O8.2** y **O8.4** pendientes de portar |
| O10 Filtros/compatibilidad | Filtro por área implementado; la pestaña nueva lo reutiliza |

## Cómo retomar

```powershell
# UI v2 con la pestaña nueva
.\jobpulse-v15-v2.bat
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15.ui_v2

# Humo SIN ventana (monta las 3 pestañas y espera el cálculo en 2º plano)
.\.venv\Scripts\python.exe -X utf8 -c "import time; from jobpulse_v15.ui_v2.app import crear_app; r,s=crear_app(); [s.mostrar(i) or r.update() for i in range(3)]; t=s.pestana_activa(); [r.update() or time.sleep(0.25) for _ in range(120)]; print(t.key, len(t._widgets['tabla'].get_children()), t.filas[0].title); r.destroy()"

# Ranking ATS sin abrir la UI (embeddings incluidos; la 1ª vez vectoriza)
.\.venv\Scripts\python.exe -X utf8 -c "import sys; sys.path.insert(0,'src'); from jobpulse_v15.db import Database; from jobpulse_v15.repository import Repository; from jobpulse_v15.ui_v2.data.vacantes import AtsStore; from jobpulse_v15.search_engine import SemanticSearchEngine; s=AtsStore(Repository(Database())); [print(round(f.score or 0,1), f.veredicto, f.title) for f in s.calcular(engine=SemanticSearchEngine())[:20]]"

# Tests
python -m pytest tests/test_ats_ranking.py -q   # 44 casos
python -m pytest tests/test_ui_v2.py -q          # 31 casos (4 nuevos)
python -m pytest tests/ -q                       # suite completa: 592 + 204 subtests
```

## Archivos clave

- `src/jobpulse_v15/ats.py` — `perfil_ats_desde_facts`, `cobertura_skills`,
  `componentes_ats`, `ranking_ats`, `percentiles`, `promedios_componentes`,
  `skills_utiles`, `PESOS_RANKING`, `UMBRALES_RANKING` (la API vieja queda
  intacta).
- `src/jobpulse_v15/ui_v2/data/vacantes.py` — `AtsStore`, `VacanteAts`,
  `filtrar`, `resumen`, `exportar_csv`.
- `src/jobpulse_v15/ui_v2/tabs/vacantes.py` — la pestaña (hilo + cola).
- `src/jobpulse_v15/ui_v2/app.py` — `PESTANIAS` (+ `VacantesTab`).
- `src/jobpulse_v15/search_engine.py` — `index_titulos`, `embed_texts`,
  `vectors`, `normalizar_texto`, caché versionada.
- `tests/test_ats_ranking.py` — 44 casos.
- `tests/test_ui_v2.py` — 4 casos nuevos (`TestVacantesTab`).

## Datos de contexto

- BD `data/jobpulse_v15.db`: 535 avisos · 48 facts de perfil (23 skills, 8
  cargos, 16 años, `{es: nativo, en: b2}`, nivel edu. 2) · 129 sitios · 20
  áreas. `job_match` sigue en **0** (no hay corrida vigente del Paso 5: la
  columna "Paso 5" de la pestaña sale "—" hasta correr `run_paso5.py`).
- **Embeddings**: modelo local `paraphrase-multilingual-mpnet-base-v2`
  (EmbeddingGemma está *gated*: da 401 y el motor cae al fallback). Cachés en
  `data/usuario/embeddings_cache.npy` y `embeddings_titulos.npy`
  (gitignoreados). La 1ª vez vectoriza los 535 avisos (~100 s); después son
  **~14 s** (modelo + caché + ranking).
- **Distribución real del score** (535 avisos): min 17,8 · p25 26,8 ·
  mediana 35,4 · p75 44,6 · p90 50,1 · máx 94,8 → 54 fuertes, ~185
  ajustables, el resto débiles.
- **Humo de la UI v2 verificado**: las 3 pestañas montan, el cálculo corre en
  2º plano y la tabla queda con 535 filas; top = "Técnico de soporte TI"
  (94,8).
- **Top del ranking medido**: "Técnico de soporte TI on site" (94,8 y 93,2,
  duplicado de fuente), "Técnico en Soporte" (75,0), "Technical Support
  Specialist - Web & Configurable" (60,7), "IT Security Engineer II" (57,3),
  "Soporte Técnico Senior TI" (56,4). **Últimos**: "Pasillero(a)" (18,1),
  "Misceláneo" (18,0), "PILERO" (17,8).
- De 333 requisitos de skill vigentes, solo **10 son `required`** (307 son
  `ambiguous`): por eso el gap de skills usa la unión de obligatorios y skills
  útiles extraídas.
- Los requisitos de idioma del corpus llegan como `espanol` / `ingles` (136 y
  129), no como `es` / `en`.
- Regla del repo respetada: **nada de `ALTER` manual**, migraciones solo como
  archivo nuevo; **no pushear sin confirmación**.

## Validación del usuario (2026-11-03, 09:38)

El usuario abrió la UI v2 y probó la pestaña: **"funciona bien"** (arranque,
cálculo en 2º plano y tabla OK). Queda **su revisión en curso** del contenido
(orden del ranking y desglose) antes de darlo por cerrado — no es un fallo
conocido, es validación pendiente. En este cierre se actualizó la documentación
a tres pestañas (`AGENTS.md` línea de comandos + baseline de tests **592**, y
`docs/UI_V2_ARQUITECTURA.md`: tabla de módulos y sección "Vacantes").

## Pendiente inmediato

1. **Revisar el ranking con el usuario** (EN CURSO: ya lo probó y "funciona
   bien"; falta su veredicto sobre el ORDEN — los avisos contables/analistas
   aparecen en el top 10 porque el componente de skills los favorece). Si hay
   que ajustar, cambiar `PESOS_RANKING` y `UMBRALES_RANKING` en `ats.py` y
   documentarlo aquí.
2. **Filtrar mejor el ruido de `jobs.skills`**: hoy el denominador incluye
   habilidades blandas ("PowerPoint", "administración"). Una stoplist de
   skills blandas mejoraría el componente de skills.
3. **Capa B `codigo_canonico` del perfil** (sigue pendiente, con la
   migración `017`): el ranking funciona sin ella, pero el cotejo por texto
   es más laxo que por código canónico.
4. Los pendientes de siempre: las **`educacion_no_confirmada`** (firma de
   segunda persona), **O5.3** (re-barrido de descripciones basura), **O6.4**
   (dedupe de slugs ES/EN al importar CV), Paso 7, O8.2/O8.4, O10
   `solo_vigentes`, y **persistir el Paso 5 desde la UI**.
5. **Confirmar con el usuario si se pushea** (los commits están en `main`
   local, sin subir).
