# Motor de VIABILIDAD — ajuste técnico del perfil con el aviso

> Módulo: `src/jobpulse_v15/viabilidad.py` · Tests: `tests/test_viabilidad.py`
> Creado: 2026-11-04 · Estado: **implementado y calibrado** (falta validación
> en vivo de los colectores de postulación).

---

## 1. Qué responde (y qué NO)

| Pregunta | Responde | Módulo |
|---|---|---|
| ¿El perfil **cumple lo que pide este aviso**? | **Sí** → índice 0-100 + banda | `viabilidad.py` |
| ¿Me van a contratar? | **No** (y no se intenta) | — |
| ¿Cómo va mi proceso de selección? | Estado del proceso | `postulaciones.py` |

### La regla dura (acordada con el usuario, 2026-11-04)

> **Ser rechazado de un trabajo NO significa que no se es apto para él.**

El reclutador humano decide por presupuesto, timing, competencia, sesgos y
azar. Por eso el score **nunca** se entrena con los rechazos, y los rechazos
**nunca** se usan como etiqueta de aptitud. El score es un índice de
**ajuste técnico**: determinista, auditable y explicable.

### Qué NO toca

- Los **umbrales congelados** del Paso 5 (cobertura 0.60 / puntaje 0.80).
- Los **estados** de `job_match` (`calificada`, `descartada`, `revisar_a_mano`…).
- El **ranking ATS** (que es otro índice: "qué vacante encaja más", no "¿cumplo
  lo que pide?").

Es un índice **paralelo**: se puede tener un aviso `calificada` en el Paso 5 y
`no_prioritario` en viabilidad, y viceversa. Son preguntas distintas.

---

## 2. Cómo se calcula

### 2.1 Requisitos evaluables

Reutiliza `matching.EvaluadorPaso5` (no duplica la regla dura del texto):

- `requisitos_efectivos(job_id)` → los requisitos que cuentan (con la regla
  del idioma del aviso ya aplicada).
- La obligatoriedad la decide el **TEXTO** del aviso, no el
  `requirement_level` del extractor (misma regla que el Paso 5).

### 2.2 Nivel interno de cada requisito

| `requirement_level` | Nivel interno | Peso | Activa el tope de banda |
|---|---|---|---|
| `required` | obligatorio | 2.0 | **Sí** (si falta) |
| `preferred` | deseable | 0.5 | No ("Preferred" no bloquea) |
| `ambiguous` / `inferred` / sin nivel | incierto | 1.0 | No |

El nivel `incierto` pesa como "deseable" pero **no** activa el tope: el texto
podría no exigirlo.

### 2.3 Estado de cada requisito frente al perfil

| Estado | Significado | Penaliza |
|---|---|---|
| `cumple` | el perfil lo cubre | — |
| `falta` | el perfil NO lo cubre | **Sí** |
| `no_verificable` | no hay cómo comparar (ej. licencia sin nivel) | No |
| `no_confirmado` | el texto no lo aclara | No |
| `bloqueante` | veto educativo (título universitario obligatorio confirmado) | **Veto** |

### 2.4 Componentes por categoría

Cada categoría se resume en una **fracción cubierta** (0-1) ponderada por el
peso interno de cada requisito:

```
componente[categoría] = Σ(peso de los cubiertos) / Σ(peso de todos)
```

Pesos por categoría (fijos → las vacantes son comparables entre sí):

| Categoría | Peso |
|---|---|
| skill | 0.40 |
| education | 0.25 |
| experience | 0.15 |
| language | 0.10 |
| license | 0.10 |
| *semántica* | 0.15 |

La **semántica** (percentil de la similitud cargo↔aviso) es la señal **más
ruidosa** (embeddings): ordena, pero no define la banda.

### 2.5 DOS PASADAS (imputación del corpus) — obligatorio

Sin esto el score es **degenerado**: una vacante con UN solo requisito
cubierto saca 100 y sube sola en el ranking (pasó en la calibración real:
50 de 50 vacantes con ajuste 100).

```
PASADA 1: componentes crudos de cada vacante → promedio del corpus por categoría
PASADA 2: puntaje con pesos FIJOS; los componentes SIN DATO toman el promedio
          del corpus (ni premian ni castigan la falta de información)
```

Es la misma regla del ranking ATS (gotcha 26 de `AGENTS.md`).

### 2.6 Bandas

| Banda | Condición | Significado |
|---|---|---|
| `aplicar` | ajuste ≥ 85 **y** ningún obligatorio faltante | encaje alto: postalo |
| `revisar` | 80 ≤ ajuste < 85 **o** falta ≥1 obligatorio | vale la pena mirarlo |
| `no_prioritario` | ajuste < 80 | bajo encaje técnico |
| `sin_datos` | sin requisitos evaluables / sin datos comparables | no se puede afirmar |
| `veto` | veto educativo o de área | descartado de entrada |

> **Tope duro**: si falta ≥1 requisito `required`, la banda máxima es
> `revisar` — **nunca** `aplicar`, aunque el score sea 100. Es el equivalente
> al *knockout* explícito de HireVue/Paradox.

### 2.7 Vetos

| Veto | Regla |
|---|---|
| `fuera_de_area` | el perfil no marcó el área de la oferta. Reutiliza `areas.es_fuera_de_area`: `otros` y las ofertas sin clasificar **nunca** se vetan (una clasificación dudosa no puede tapar ofertas). |
| `titulo_universitario_requerido` | el **texto** del aviso confirma título universitario obligatorio, sin negación ni alternativa (misma regla que el Paso 5). |
| `titulo_universitario_en_curso_requerido` | el aviso exige estudiante activo (criterio distinto del título completado). |

---

## 3. Uso

### CLI

```powershell
# Todas las vacantes, ordenadas por banda y ajuste
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 viabilidad list --limit 0

# Solo las de mejor banda
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 viabilidad list --banda aplicar

# Las 20 mejores
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 viabilidad top --limit 20

# CSV (con la lista de faltantes obligatorios)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 viabilidad list --format csv --output viab.csv

# Con el componente semántico (embeddings locales; vectoriza el corpus la 1ª vez)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 viabilidad list --semantica

# Ignorar el filtro por áreas del perfil (igual que el Paso 5 con --evaluar-todo)
.\.venv\Scripts\python.exe -X utf8 -m jobpulse_v15 viabilidad list --evaluar-todo
```

Salida JSON: `{"bandas": {...}, "vacantes": [{...}]}` con `ajuste`, `banda`,
`veto`, `motivos`, `cobertura_obligatorios`, `faltantes_obligatorios`,
`componentes`, `resumen`.

### UI v2 (pestaña "Vacantes")

- Columnas **"Ajuste"** (0-100) y **"Banda"**.
- Combo de bandas + casilla **"Solo aplicar"**.
- Franja de tiles con el conteo por banda.
- Detalle: "Ajuste técnico", "Banda", "Faltantes obligatorios".
- El CSV de exportación incluye `ajuste`, `banda` y `faltantes_obligatorios`.

CLI y UI comparten **el mismo motor** (`viabilidad.calcular_viabilidades`) y la
misma fórmula semántica (`ats.percentiles_semanticas`): una sola respuesta.

---

## 4. Calibración real (corpus de 535 avisos, copia de la BD)

Sin semántica:

| Banda | Vacantes |
|---|---|
| aplicar | 5 |
| revisar | 17 |
| no prioritario | 284 |
| sin datos | 142 |
| veto | 87 |

**Lectura honesta**: el corpus tiene poca señal por requisito — 49 skills y 29
licencias del corpus **no tienen `codigo_canonico`** (y el Paso 5 descarta los
requisitos sin código). El motor es correcto, pero los datos de entrada están
incompletos; por eso hay tantas vacantes en `sin_datos` y `veto`.

**Los pesos son priors documentados**, no pesos aprendidos: todavía no hay
ground truth propio (0 postulaciones registradas). Cuando haya postulaciones
reales, se pueden **calibrar** (comparar banda vs. resultado del proceso) —
pero **jamás reentrenar** el score con los rechazos.

---

## 5. Limitaciones conocidas

1. **El corpus tiene pocos requisitos con código canónico** → muchas vacantes
   quedan en `sin_datos` o se puntúan con la imputación del corpus.
2. **La semántica es un percentil, no una medida absoluta** (los cosenos viven
   comprimidos entre 0.1 y 0.6).
3. **No hay validación en vivo** del cruce con postulaciones (falta CDP y la
   app-password de Gmail).
4. **"Req. = 0" no significa "sin requisitos"**: el extractor puede no marcar
   nada como `required` aunque el texto sí exija cosas. El tope de banda usa
   el `requirement_level` del análisis vigente.
5. Los pesos y umbrales están en el **código** (`viabilidad.py`), no en la BD:
   se cambian ahí, no en cada UI.

---

## 6. Archivos relacionados

| Archivo | Qué es |
|---|---|
| `src/jobpulse_v15/viabilidad.py` | El motor (bandas, pesos, imputación, vetos) |
| `src/jobpulse_v15/postulaciones.py` | Estado del **proceso** (núcleo puro) |
| `src/jobpulse_v15/correo_postulaciones.py` | Lector IMAP (Gmail) |
| `src/jobpulse_v15/workday_postulaciones.py` | Parser + fetch de "Mis postulaciones" |
| `src/jobpulse_v15/ats.py` | `percentiles_semanticas` (semántica compartida) |
| `src/jobpulse_v15/matching.py` | `EvaluadorPaso5` (reglas duras reutilizadas) |
| `src/jobpulse_v15/areas.py` | `es_fuera_de_area` (veto de área) |
| `tests/test_viabilidad.py` | 12 tests del motor |
| `tests/test_postulaciones*.py`, `tests/test_correo_postulaciones.py`, `tests/test_workday_postulaciones.py` | Tests de las señales |
| `AGENTS.md` | §"Motor de VIABILIDAD" y §"POSTULACIONES" |
